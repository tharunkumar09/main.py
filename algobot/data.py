"""Market data stream handling."""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
from websocket import WebSocketApp

from config.settings import Settings
from .event_filter import ExternalEventFilter
from .logging_utils import get_logger
from .models import TradeAction
from .orders import OrderManager
from .portfolio import PortfolioManager
from .risk import RiskManager
from .strategy import StrategyEngine
from .trade_logger import TradeLogger

logger = get_logger(__name__)


class CandleBuilder:
    """Aggregates ticks into 1-minute candles."""

    def __init__(self):
        self.buffers: Dict[str, dict] = {}

    def add_tick(self, symbol: str, tick: dict) -> Optional[dict]:
        timestamp = datetime.fromtimestamp(tick["timestamp"], tz=timezone.utc).replace(second=0, microsecond=0)
        buffer = self.buffers.get(symbol)
        price = float(tick["ltp"])
        volume = float(tick.get("volume", 0))

        if buffer is None or buffer["start"] != timestamp:
            completed = None
            if buffer:
                completed = buffer.copy()
            self.buffers[symbol] = {
                "symbol": symbol,
                "start": timestamp,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            return completed

        buffer["high"] = max(buffer["high"], price)
        buffer["low"] = min(buffer["low"], price)
        buffer["close"] = price
        buffer["volume"] += volume
        return None


class MarketDataStream:
    """Handles websocket connections and feeds the strategy."""

    def __init__(
        self,
        settings: Settings,
        strategy: StrategyEngine,
        order_manager: OrderManager,
        portfolio: PortfolioManager,
        risk_manager: RiskManager,
        trade_logger: TradeLogger,
        event_filter: ExternalEventFilter,
    ):
        self.settings = settings
        self.strategy = strategy
        self.order_manager = order_manager
        self.portfolio = portfolio
        self.risk_manager = risk_manager
        self.trade_logger = trade_logger
        self.event_filter = event_filter

        self.ws: Optional[WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._candle_builder = CandleBuilder()
        self._data: Dict[str, pd.DataFrame] = defaultdict(
            lambda: pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        )
        self._trail_state: Dict[str, dict] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("Market data stream already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        if self._thread:
            self._thread.join(timeout=5)

    def _run_forever(self) -> None:
        backoff = 2
        while not self._stop_event.is_set():
            try:
                self._connect()
                backoff = 2
            except Exception as exc:  # noqa: BLE001
                logger.exception("Websocket error: %s", exc)
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)

    def _connect(self) -> None:
        token = self.order_manager.session_manager.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
        }

        self.ws = WebSocketApp(
            self.settings.upstox_ws_url,
            header=[f"{k}: {v}" for k, v in headers.items()],
            on_message=self._on_message,
            on_open=self._on_open,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.ws.run_forever()

    def _on_open(self, ws):  # noqa: ANN001
        logger.info("Websocket connected. Subscribing to instruments.")
        subscribe_payload = {
            "type": "subscribe",
            "instruments": self.settings.instruments,
            "mode": "full",
        }
        ws.send(json.dumps(subscribe_payload))

    def _on_error(self, ws, error):  # noqa: ANN001
        logger.error("Websocket error: %s", error)

    def _on_close(self, ws, *_):  # noqa: ANN001
        logger.warning("Websocket closed. Attempting reconnect.")

    def _on_message(self, ws, message):  # noqa: ANN001
        payload = json.loads(message)
        symbol = payload.get("symbol")
        if symbol not in self.settings.instruments:
            return
        candle = self._candle_builder.add_tick(symbol, payload)
        if candle:
            self._process_candle(candle)

    def _process_candle(self, candle: dict) -> None:
        symbol = candle["symbol"]
        timestamp = candle["start"]
        df = self._data[symbol]
        row = pd.DataFrame(
            {
                "open": [candle["open"]],
                "high": [candle["high"]],
                "low": [candle["low"]],
                "close": [candle["close"]],
                "volume": [candle["volume"]],
            },
            index=pd.DatetimeIndex([timestamp]),
        )
        df = pd.concat([df, row]).last("3D")
        self._data[symbol] = df

        m1 = df
        m5 = df.resample("5T").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        m60 = df.resample("60T").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()

        self.risk_manager.evaluate()
        if not self.risk_manager.allow_trading():
            logger.critical("Trading halted: %s", self.risk_manager.kill_reason)
            return

        decision = self.strategy.evaluate(symbol, m1, m5, m60)
        if decision.action in {TradeAction.BUY, TradeAction.SELL}:
            if self.event_filter.should_halt(datetime.utcnow()):
                logger.warning("Skipping trade due to macro event filter.")
                return
            side = "BUY" if decision.action == TradeAction.BUY else "SELL"
            response = self.order_manager.place_order(
                symbol=symbol,
                side=side,
                quantity=decision.quantity,
                order_type="MARKET",
                stop_loss=decision.stop_config.stop_loss,
            )
            order_id = response.get("order_id")
            self._trail_state[symbol] = {
                "direction": 1 if decision.action == TradeAction.BUY else -1,
                "atr_distance": decision.stop_config.trailing_stop,
                "order_id": order_id,
                "extreme": decision.entry_price,
                "last_stop": decision.stop_config.stop_loss,
            }
            self.trade_logger.log(
                {
                    "symbol": symbol,
                    "action": decision.action.value,
                    "quantity": decision.quantity,
                    "entry_price": decision.entry_price,
                    "exit_price": "",
                    "pnl": "",
                    "reason": decision.reason,
                    "regime": decision.regime,
                    "higher_tf_trend": decision.higher_tf_trend,
                }
            )
            logger.info("Trade executed: %s", response)
        self._update_trailing_stop(symbol, m1)

    def _update_trailing_stop(self, symbol: str, df: pd.DataFrame) -> None:
        state = self._trail_state.get(symbol)
        if not state or df.empty:
            return
        order_id = state.get("order_id")
        atr_distance = state.get("atr_distance")
        if not order_id or not atr_distance:
            return

        latest = df.iloc[-1]
        direction = state["direction"]
        if direction == 1:
            extreme = max(state.get("extreme", latest["close"]), latest["high"])
            state["extreme"] = extreme
            new_stop = round(extreme - atr_distance, 2)
            if new_stop > state.get("last_stop", float("-inf")):
                try:
                    self.order_manager.modify_stop_loss(order_id, new_stop)
                    state["last_stop"] = new_stop
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to update trailing stop for %s", symbol)
        else:
            extreme = min(state.get("extreme", latest["close"]), latest["low"])
            state["extreme"] = extreme
            new_stop = round(extreme + atr_distance, 2)
            if state.get("last_stop") is None or new_stop < state["last_stop"]:
                try:
                    self.order_manager.modify_stop_loss(order_id, new_stop)
                    state["last_stop"] = new_stop
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to update trailing stop for %s", symbol)


__all__ = ["MarketDataStream"]
