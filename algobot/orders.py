"""Order management with resilience."""
from __future__ import annotations

import math
import time
from typing import Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from upstox_api.api import NetworkException, RequestException

from config.settings import Settings
from .auth import UpstoxSessionManager
from .logging_utils import get_logger

logger = get_logger(__name__)


class OrderManager:
    """Places and tracks orders with slicing helpers."""

    def __init__(self, settings: Settings, session_manager: UpstoxSessionManager):
        self.settings = settings
        self.session_manager = session_manager

    def _client(self):
        return self.session_manager.get_client()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=20),
    )
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "MARKET",
        product: str = "MIS",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict:
        """Generic order placement with retries."""

        client = self._client()
        payload = {
            "symbol": symbol,
            "transaction_type": side,
            "quantity": quantity,
            "order_type": order_type,
            "product": product,
        }
        if price:
            payload["price"] = price
        if stop_loss:
            payload["stop_loss"] = stop_loss
        if take_profit:
            payload["take_profit"] = take_profit

        try:
            response = client.place_order(**payload)
            logger.info("Order placed: %s", response)
            return response
        except RequestException as exc:
            if "401" in str(exc):
                logger.warning("Auth error while placing order, refreshing token.")
                self.session_manager.refresh_access_token()
            logger.exception("Order failed: %s", exc)
            raise
        except NetworkException as exc:  # noqa: PERF203
            logger.warning("Network issue while placing order: %s", exc)
            raise

    def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        trailing_stop: Optional[float] = None,
    ) -> Dict:
        """Place OCO/bracket order."""

        payload = self.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="LIMIT",
            price=entry_price,
            product="OCO",
            stop_loss=stop_loss,
            take_profit=target,
        )
        if trailing_stop:
            payload["trailing_stop_loss"] = trailing_stop
        return payload

    def execute_twap(
        self,
        symbol: str,
        side: str,
        quantity: int,
        window_minutes: int = 10,
        slice_interval_seconds: int = 30,
    ) -> None:
        """Slice large order using simple TWAP."""

        slices = max(1, (window_minutes * 60) // slice_interval_seconds)
        per_slice = math.ceil(quantity / slices)
        for batch in range(slices):
            remaining = quantity - batch * per_slice
            if remaining <= 0:
                break
            qty = min(per_slice, remaining)
            logger.info("TWAP slice %s/%s for %s", batch + 1, slices, symbol)
            self.place_order(symbol=symbol, side=side, quantity=qty)
            time.sleep(slice_interval_seconds)

    def modify_stop_loss(self, order_id: str, stop_price: float) -> Dict:
        """Adjust stop-loss for trailing logic."""

        client = self._client()
        try:
            response = client.modify_order(order_id=order_id, stop_loss=stop_price)
            logger.info("Updated stop loss for %s to %s", order_id, stop_price)
            return response
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to update trailing stop: %s", exc)
            raise


__all__ = ["OrderManager"]
