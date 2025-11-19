"""Shared dataclasses and enums."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    EXIT = "EXIT"


@dataclass
class StopConfig:
    stop_loss: float
    trailing_stop: Optional[float]
    atr_multiple: float


@dataclass
class TradeDecision:
    symbol: str
    action: TradeAction
    quantity: int
    entry_price: Optional[float]
    stop_config: StopConfig
    timestamp: datetime
    reason: str
    regime: str
    higher_tf_trend: str


__all__ = ["PositionSide", "TradeAction", "StopConfig", "TradeDecision"]
