"""vectorbt-based backtesting for the regime-switching strategy."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import vectorbt as vbt

from config.settings import Settings, get_settings
from algobot.indicators import add_core_indicators


@dataclass
class BacktestResult:
    symbol: str
    metrics: Dict[str, float]
    equity_curve_path: Path
    drawdown_curve_path: Path


class BacktestEngine:
    """Runs the live strategy logic inside vectorbt for validation."""

    def __init__(self, data: Dict[str, pd.DataFrame], settings: Settings | None = None):
        self.data = data
        self.settings = settings or get_settings()
        self.output_dir = Path("data/backtests")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _prepare_signals(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.DataFrame]:
        enriched = add_core_indicators(df)
        enriched.dropna(inplace=True)
        regime_trending = (enriched["adx_14"] > 25) & (enriched["bb_width"] > 0.02)
        regime_ranging = (enriched["adx_14"] < 20) & (enriched["bb_width"] < 0.025)

        ema_slope = enriched["ema_20"].diff().rolling(5).mean()
        htf_bull = ema_slope > 0
        htf_bear = ema_slope < 0

        long_trend = (
            regime_trending
            & htf_bull
            & (enriched["close"] > enriched["ema_200"])
            & (enriched["rsi_14"] > 55)
            & (enriched["macd_hist"] > 0)
        )
        short_trend = (
            regime_trending
            & htf_bear
            & (enriched["close"] < enriched["ema_200"])
            & (enriched["rsi_14"] < 45)
            & (enriched["macd_hist"] < 0)
        )

        long_range = regime_ranging & (enriched["close"] <= enriched["bb_lower"]) & (enriched["rsi_14"] < 35)
        short_range = regime_ranging & (enriched["close"] >= enriched["bb_upper"]) & (enriched["rsi_14"] > 65)

        entries = long_trend | long_range
        exits = short_trend | short_range

        atr = enriched["atr_14"]
        stop_distance = atr * self.settings.atr_multiple_sl
        trail_distance = atr * self.settings.atr_multiple_tsl
        risk_capital = self.settings.capital_base * self.settings.risk_per_trade_pct
        size = (risk_capital / stop_distance.replace(0, np.nan)).apply(np.floor).fillna(0)
        size = size.clip(lower=0)

        return entries, exits, size, stop_distance, trail_distance, enriched

    def run_symbol(self, symbol: str, df: pd.DataFrame) -> BacktestResult:
        entries, exits, size, stop_distance, trail_distance, enriched = self._prepare_signals(df)
        close = enriched["close"]

        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            size=size,
            fees=0.0005,
            sl_stop=stop_distance,
            tsl_stop=trail_distance,
            freq="1D",
        )

        metrics = self._compute_metrics(pf)
        equity_path = self.output_dir / f"{symbol}_equity.html"
        drawdown_path = self.output_dir / f"{symbol}_drawdown.html"
        self._plot_equity(pf, equity_path)
        self._plot_drawdown(pf, drawdown_path)
        return BacktestResult(symbol, metrics, equity_path, drawdown_path)

    def run(self) -> Dict[str, BacktestResult]:
        results: Dict[str, BacktestResult] = {}
        for symbol, df in self.data.items():
            if df is None or len(df) < 300:
                continue
            results[symbol] = self.run_symbol(symbol, df)
        return results

    def _plot_equity(self, pf: vbt.Portfolio, output_file: Path) -> None:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pf.value().index, y=pf.value(), name="Equity"))
        fig.update_layout(title="Equity Curve", xaxis_title="Date", yaxis_title="Portfolio Value")
        fig.write_html(str(output_file))

    def _plot_drawdown(self, pf: vbt.Portfolio, output_file: Path) -> None:
        dd = pf.drawdown_series()
        fig = go.Figure()
        fig.add_bar(x=dd.index, y=dd, name="Drawdown")
        fig.update_layout(title="Drawdown Curve", xaxis_title="Date", yaxis_title="Drawdown")
        fig.write_html(str(output_file))

    def _compute_metrics(self, pf: vbt.Portfolio) -> Dict[str, float]:
        cagr = float(pf.annualized_return())
        max_drawdown = float(pf.max_drawdown())
        dd_duration = pf.drawdown_duration().max()
        dd_days = float(dd_duration.days) if hasattr(dd_duration, "days") else float(dd_duration)
        sharpe = float(pf.sharpe_ratio())
        sortino = float(pf.sortino_ratio())

        pnl = pf.trades.records_readonly["pnl"] if pf.trades.count() > 0 else pd.Series(dtype=float)
        win_rate = float((pnl > 0).sum()) / float(len(pnl)) if len(pnl) else 0.0
        gross_profit = float(pnl[pnl > 0].sum()) if len(pnl) else 0.0
        gross_loss = float(abs(pnl[pnl < 0].sum())) if len(pnl) else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

        return {
            "CAGR": cagr,
            "Max Drawdown": max_drawdown,
            "Drawdown Duration (days)": dd_days,
            "Sharpe Ratio": sharpe,
            "Sortino Ratio": sortino,
            "Win Rate": win_rate,
            "Profit Factor": profit_factor,
        }


__all__ = ["BacktestEngine", "BacktestResult"]
