"""Risk controls including kill switch."""
from __future__ import annotations

from typing import Optional

from config.settings import Settings
from .logging_utils import get_logger
from .portfolio import PortfolioManager

logger = get_logger(__name__)


class RiskManager:
    """Evaluates portfolio-level risk and triggers kill switch."""

    def __init__(self, settings: Settings, portfolio: PortfolioManager):
        self.settings = settings
        self.portfolio = portfolio
        self.kill_switch_engaged = False
        self.daily_loss_limit = self.settings.capital_base * self.settings.max_daily_loss_pct
        self._kill_reason: Optional[str] = None

    def evaluate(self) -> None:
        """Check current P&L vs risk thresholds."""

        self.portfolio.refresh_positions()
        current_pnl = self.portfolio.get_total_pnl()
        if current_pnl <= -self.daily_loss_limit:
            self.trigger_kill_switch(f"Daily loss exceeded: {current_pnl:.2f}")

    def trigger_kill_switch(self, reason: str) -> None:
        if self.kill_switch_engaged:
            return
        self.kill_switch_engaged = True
        self._kill_reason = reason
        logger.critical("Kill switch engaged: %s", reason)
        self.portfolio.square_off_all()

    def allow_trading(self) -> bool:
        return not self.kill_switch_engaged

    @property
    def kill_reason(self) -> Optional[str]:
        return self._kill_reason


__all__ = ["RiskManager"]
