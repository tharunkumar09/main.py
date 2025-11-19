"""Trade logging utilities."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config.settings import Settings


class TradeLogger:
    """Persists detailed trade logs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.log_path = self.settings.log_dir / "trades.csv"
        self.fieldnames = [
            "timestamp",
            "symbol",
            "action",
            "quantity",
            "entry_price",
            "exit_price",
            "pnl",
            "reason",
            "regime",
            "higher_tf_trend",
        ]
        self._ensure_headers()

    def _ensure_headers(self) -> None:
        if not self.log_path.exists():
            with self.log_path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()

    def log(self, payload: Dict[str, Any]) -> None:
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        for field in self.fieldnames:
            payload.setdefault(field, "")
        with self.log_path.open("a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writerow(payload)


__all__ = ["TradeLogger"]
