"""Centralized configuration and environment loading for the trading bot."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables or `.env` file."""

    # Upstox API credentials
    upstox_api_key: str = Field(..., env="UPSTOX_API_KEY")
    upstox_api_secret: str = Field(..., env="UPSTOX_API_SECRET")
    upstox_redirect_uri: str = Field(..., env="UPSTOX_REDIRECT_URI")
    upstox_api_base: str = Field("https://api.upstox.com/v2", env="UPSTOX_API_BASE")
    upstox_ws_url: str = Field("wss://api.upstox.com/feed/market-data", env="UPSTOX_WS_URL")

    # Trading configuration
    capital_base: float = Field(1_000_000.0, env="CAPITAL_BASE")
    max_daily_loss_pct: float = Field(0.03, env="MAX_DAILY_LOSS_PCT")
    risk_per_trade_pct: float = Field(0.01, env="RISK_PER_TRADE_PCT")
    atr_multiple_sl: float = Field(3.0, env="ATR_MULTIPLE_SL")
    atr_multiple_tsl: float = Field(2.0, env="ATR_MULTIPLE_TSL")

    # Universe and timeframe
    instruments: List[str] = Field(
        default_factory=lambda: ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"],
        env="INSTRUMENTS",
    )
    primary_timeframe: str = Field("1Min", env="PRIMARY_TIMEFRAME")
    higher_timeframe: str = Field("60Min", env="HIGHER_TIMEFRAME")

    # Logging and paths
    log_dir: Path = Field(Path("logs"), env="LOG_DIR")
    data_dir: Path = Field(Path("data"), env="DATA_DIR")

    # Automation
    trading_start_ist: str = Field("09:14", env="TRADING_START_IST")
    trading_end_ist: str = Field("15:30", env="TRADING_END_IST")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("instruments", pre=True)
    def split_instruments(cls, value):
        if isinstance(value, str):
            return [sym.strip().upper() for sym in value.split(",")]
        return value

    @validator("log_dir", "data_dir", pre=True)
    def ensure_path(cls, value):
        return Path(value).expanduser().resolve()


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""
    settings = Settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


__all__ = ["Settings", "get_settings"]
