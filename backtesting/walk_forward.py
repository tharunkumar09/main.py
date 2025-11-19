"""Walk-forward validation utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pandas as pd

from config.settings import Settings, get_settings
from .backtest_engine import BacktestEngine


@dataclass
class WalkForwardWindow:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


class WalkForwardOptimizer:
    """Performs rolling retraining/testing of the strategy."""

    def __init__(
        self,
        symbols: Iterable[str],
        data: Dict[str, pd.DataFrame],
        train_years: int = 5,
        test_years: int = 1,
        settings: Settings | None = None,
    ):
        self.symbols = list(symbols)
        self.data = data
        self.train_years = train_years
        self.test_years = test_years
        self.settings = settings or get_settings()

    def _generate_windows(self, df: pd.DataFrame) -> List[WalkForwardWindow]:
        windows: List[WalkForwardWindow] = []
        start = df.index.min()
        end = df.index.max()
        cursor = start
        while cursor + pd.DateOffset(years=self.train_years + self.test_years) < end:
            train_start = cursor
            train_end = cursor + pd.DateOffset(years=self.train_years)
            test_start = train_end
            test_end = test_start + pd.DateOffset(years=self.test_years)
            windows.append(
                WalkForwardWindow(
                    train_start=train_start,
                    train_end=train_end,
                    test_start=test_start,
                    test_end=test_end,
                )
            )
            cursor = cursor + pd.DateOffset(years=self.test_years)
        return windows

    def run(self) -> Dict[str, List[WalkForwardWindow]]:
        """Return performance stats for each walk-forward window."""

        summary: Dict[str, List[WalkForwardWindow]] = {}
        for symbol in self.symbols:
            df = self.data.get(symbol)
            if df is None or df.empty:
                continue
            windows = self._generate_windows(df)
            summary[symbol] = windows
            for window in windows:
                sliced = df.loc[window.test_start : window.test_end]
                backtester = BacktestEngine({symbol: sliced}, self.settings)
                backtester.run()
        return summary


__all__ = ["WalkForwardOptimizer", "WalkForwardWindow"]
