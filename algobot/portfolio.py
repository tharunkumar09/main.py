"""Portfolio and position management."""
from __future__ import annotations

from typing import Dict

from config.settings import Settings
from .auth import UpstoxSessionManager
from .logging_utils import get_logger

logger = get_logger(__name__)


class PortfolioManager:
    """Tracks live positions, P&L, and exposure."""

    def __init__(self, settings: Settings, session_manager: UpstoxSessionManager):
        self.settings = settings
        self.session_manager = session_manager
        self.positions: Dict[str, dict] = {}
        self.open_pnl: float = 0.0

    def refresh_positions(self) -> None:
        """Pull positions from Upstox."""

        client = self.session_manager.get_client()
        try:
            data = client.get_positions()
            self.positions = {item["symbol"]: item for item in data}
            self._compute_open_pnl()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to refresh positions: %s", exc)

    def _compute_open_pnl(self) -> None:
        total = 0.0
        for position in self.positions.values():
            total += float(position.get("unrealised_profit_loss", 0.0))
        self.open_pnl = total

    def get_position(self, symbol: str) -> dict:
        return self.positions.get(symbol, {})

    def get_total_pnl(self) -> float:
        return self.open_pnl

    def square_off_all(self) -> None:
        """Close all open positions (used by kill switch)."""

        client = self.session_manager.get_client()
        for symbol, position in self.positions.items():
            quantity = position.get("quantity", 0)
            if quantity == 0:
                continue
            side = "SELL" if quantity > 0 else "BUY"
            try:
                client.place_order(
                    transaction_type=side,
                    quantity=abs(quantity),
                    instrument=symbol,
                    order_type="MARKET",
                    product="MIS",
                )
                logger.warning("Squared off %s for kill switch.", symbol)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to square off %s: %s", symbol, exc)


__all__ = ["PortfolioManager"]
