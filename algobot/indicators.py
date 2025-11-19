"""Indicator helper functions."""
from __future__ import annotations

from typing import Dict

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import AverageTrueRange, BollingerBands


def add_core_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich the dataframe with indicators used by the strategies."""

    if df.empty:
        return df

    indicator_df = df.copy()
    indicator_df["rsi_14"] = RSIIndicator(indicator_df["close"], window=14).rsi()
    macd = MACD(
        indicator_df["close"],
        window_slow=26,
        window_fast=12,
        window_sign=9,
    )
    indicator_df["macd"] = macd.macd()
    indicator_df["macd_signal"] = macd.macd_signal()
    indicator_df["macd_hist"] = macd.macd_diff()
    indicator_df["ema_200"] = EMAIndicator(indicator_df["close"], window=200).ema_indicator()
    indicator_df["ema_20"] = EMAIndicator(indicator_df["close"], window=20).ema_indicator()
    indicator_df["adx_14"] = ADXIndicator(
        indicator_df["high"],
        indicator_df["low"],
        indicator_df["close"],
        window=14,
    ).adx()

    bb = BollingerBands(
        indicator_df["close"],
        window=20,
        window_dev=2,
    )
    indicator_df["bb_upper"] = bb.bollinger_hband()
    indicator_df["bb_lower"] = bb.bollinger_lband()
    indicator_df["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / indicator_df["close"]

    atr = AverageTrueRange(
        indicator_df["high"],
        indicator_df["low"],
        indicator_df["close"],
        window=14,
    )
    indicator_df["atr_14"] = atr.average_true_range()

    return indicator_df


def classify_regime(df: pd.DataFrame) -> str:
    """Classify market regime based on ADX and Bollinger Band width."""

    enriched = add_core_indicators(df)
    latest = enriched.dropna().iloc[-1]

    if latest["adx_14"] > 25 and latest["bb_width"] > 0.02:
        return "trending"
    if latest["adx_14"] < 20 and latest["bb_width"] < 0.025:
        return "ranging"
    return "neutral"


def higher_timeframe_trend(df: pd.DataFrame) -> str:
    """Return higher timeframe trend based on 20 EMA slope."""

    enriched = add_core_indicators(df)
    recent = enriched["ema_20"].tail(5)
    if recent.isna().any():
        return "unknown"

    slope = recent.diff().mean()
    if slope > 0:
        return "bullish"
    if slope < 0:
        return "bearish"
    return "flat"


def compute_stop_levels(df: pd.DataFrame, atr_multiple: float) -> Dict[str, float]:
    """Return ATR-based stop levels."""

    enriched = add_core_indicators(df)
    latest = enriched.dropna().iloc[-1]
    atr_value = latest["atr_14"]
    return {
        "atr": atr_value,
        "stop_distance": atr_multiple * atr_value,
    }


__all__ = ["add_core_indicators", "classify_regime", "higher_timeframe_trend", "compute_stop_levels"]
