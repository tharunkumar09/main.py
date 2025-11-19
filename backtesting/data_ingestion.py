"""Download and clean historical data for backtesting."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
import yfinance as yf


def download_history(
    symbols: Iterable[str],
    start: str = "2005-01-01",
    end: str | None = None,
    cache_dir: Path | str = "data/history",
) -> Dict[str, pd.DataFrame]:
    """Fetch daily data for NSE symbols via yfinance and cache locally."""

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    history: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        ticker = f"{symbol}.NS"
        file_path = cache_path / f"{symbol}.parquet"
        df = None
        if file_path.exists():
            df = pd.read_parquet(file_path)
        else:
            raw = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
            raw.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adj_close",
                    "Volume": "volume",
                },
                inplace=True,
            )
            raw.index.name = "date"
            raw.dropna(inplace=True)
            raw.to_parquet(file_path)
            df = raw
        history[symbol] = df
    return history


__all__ = ["download_history"]
