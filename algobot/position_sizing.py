"""Dynamic position sizing utilities."""
from __future__ import annotations

import math
from typing import Tuple

import pandas as pd

from config.settings import Settings
from .indicators import add_core_indicators


class PositionSizer:
    """Calculates position size based on ATR and risk budget."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def size_position(
        self,
        symbol: str,
        df: pd.DataFrame,
        entry_price: float,
        stop_distance: float,
    ) -> Tuple[int, float]:
        """Return (quantity, risk_amount)."""

        if df.empty:
            return 0, 0.0

        enriched = add_core_indicators(df)
        latest_atr = enriched["atr_14"].dropna()
        if latest_atr.empty:
            return 0, 0.0

        risk_capital = self.settings.capital_base * self.settings.risk_per_trade_pct
        per_unit_risk = stop_distance
        if per_unit_risk <= 0:
            return 0, 0.0

        raw_qty = risk_capital / per_unit_risk
        lot_size = 1  # placeholder, fetch from instrument master
        quantity = math.floor(raw_qty / lot_size) * lot_size
        allocated_capital = quantity * entry_price
        return max(quantity, 0), allocated_capital


__all__ = ["PositionSizer"]
