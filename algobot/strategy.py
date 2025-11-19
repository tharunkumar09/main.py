"""Strategy layer with regime switching."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from config.settings import Settings
from .indicators import (
    add_core_indicators,
    classify_regime,
    compute_stop_levels,
    higher_timeframe_trend,
)
from .models import StopConfig, TradeAction, TradeDecision
from .position_sizing import PositionSizer


class StrategyEngine:
    """Decides trade actions based on current regime and indicators."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.position_sizer = PositionSizer(settings)

    def evaluate(
        self,
        symbol: str,
        m1: pd.DataFrame,
        m5: pd.DataFrame,
        m60: pd.DataFrame,
    ) -> TradeDecision:
        """Return trade decision for latest candle."""

        if m5 is None or len(m5) < 50:
            return self._hold(symbol, "Insufficient data")

        regime = classify_regime(m5)
        htf_trend = higher_timeframe_trend(m60) if m60 is not None and len(m60) >= 50 else "unknown"

        if regime == "trending":
            action, reason = self._strategy_trending(m5)
        elif regime == "ranging":
            action, reason = self._strategy_ranging(m5)
        else:
            return self._hold(symbol, f"Neutral regime ({regime})", htf_trend)

        if action in {TradeAction.BUY, TradeAction.SELL} and htf_trend != "unknown":
            if action == TradeAction.BUY and htf_trend != "bullish":
                return self._hold(symbol, f"HTF mismatch ({htf_trend})", htf_trend)
            if action == TradeAction.SELL and htf_trend != "bearish":
                return self._hold(symbol, f"HTF mismatch ({htf_trend})", htf_trend)

        if action == TradeAction.HOLD:
            return self._hold(symbol, reason, htf_trend, regime)

        enriched = add_core_indicators(m1)
        latest = enriched.dropna().iloc[-1]
        entry_price = float(latest["close"])

        stop_levels = compute_stop_levels(m1, self.settings.atr_multiple_sl)
        trail_levels = compute_stop_levels(m1, self.settings.atr_multiple_tsl)
        quantity, _ = self.position_sizer.size_position(symbol, m1, entry_price, stop_levels["stop_distance"])
        if quantity == 0:
            return self._hold(symbol, "Position size zero", htf_trend, regime)

        stop_price = entry_price - stop_levels["stop_distance"] if action == TradeAction.BUY else entry_price + stop_levels["stop_distance"]
        trailing_buffer = trail_levels["stop_distance"]
        stop_config = StopConfig(
            stop_loss=round(stop_price, 2),
            trailing_stop=round(trailing_buffer, 2),
            atr_multiple=self.settings.atr_multiple_sl,
        )

        return TradeDecision(
            symbol=symbol,
            action=action,
            quantity=quantity,
            entry_price=entry_price,
            stop_config=stop_config,
            timestamp=datetime.utcnow(),
            reason=reason,
            regime=regime,
            higher_tf_trend=htf_trend,
        )

    def _strategy_trending(self, df: pd.DataFrame) -> tuple[TradeAction, str]:
        enriched = add_core_indicators(df).dropna()
        latest = enriched.iloc[-1]
        if latest["close"] > latest["ema_200"] and latest["rsi_14"] > 55 and latest["macd_hist"] > 0:
            return TradeAction.BUY, "Trend-following long setup"
        if latest["close"] < latest["ema_200"] and latest["rsi_14"] < 45 and latest["macd_hist"] < 0:
            return TradeAction.SELL, "Trend-following short setup"
        return TradeAction.HOLD, "No trend signal"

    def _strategy_ranging(self, df: pd.DataFrame) -> tuple[TradeAction, str]:
        enriched = add_core_indicators(df).dropna()
        latest = enriched.iloc[-1]
        if latest["close"] <= latest["bb_lower"] and latest["rsi_14"] < 35:
            return TradeAction.BUY, "Mean-reversion long (lower band)"
        if latest["close"] >= latest["bb_upper"] and latest["rsi_14"] > 65:
            return TradeAction.SELL, "Mean-reversion short (upper band)"
        return TradeAction.HOLD, "No ranging signal"

    def _hold(
        self,
        symbol: str,
        reason: str,
        htf_trend: str = "unknown",
        regime: str = "neutral",
    ) -> TradeDecision:
        return TradeDecision(
            symbol=symbol,
            action=TradeAction.HOLD,
            quantity=0,
            entry_price=None,
            stop_config=StopConfig(stop_loss=0.0, trailing_stop=None, atr_multiple=0.0),
            timestamp=datetime.utcnow(),
            reason=reason,
            regime=regime,
            higher_tf_trend=htf_trend,
        )


__all__ = ["StrategyEngine"]
