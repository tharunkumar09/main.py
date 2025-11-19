"""
Configuration settings for the trading bot
"""
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""
    
    # Upstox API Credentials
    UPSTOX_API_KEY: str = os.getenv("UPSTOX_API_KEY", "")
    UPSTOX_API_SECRET: str = os.getenv("UPSTOX_API_SECRET", "")
    UPSTOX_REDIRECT_URI: str = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:3000/callback")
    UPSTOX_ACCESS_TOKEN: Optional[str] = os.getenv("UPSTOX_API_ACCESS_TOKEN", None)
    
    # Risk Parameters
    MAX_DAILY_LOSS_PERCENT: float = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "3.0"))
    RISK_PER_TRADE_PERCENT: float = float(os.getenv("RISK_PER_TRADE_PERCENT", "1.0"))
    INITIAL_CAPITAL: float = float(os.getenv("INITIAL_CAPITAL", "100000"))
    
    # Trading Hours (IST)
    MARKET_OPEN_HOUR: int = int(os.getenv("MARKET_OPEN_HOUR", "9"))
    MARKET_OPEN_MINUTE: int = int(os.getenv("MARKET_OPEN_MINUTE", "15"))
    MARKET_CLOSE_HOUR: int = int(os.getenv("MARKET_CLOSE_HOUR", "15"))
    MARKET_CLOSE_MINUTE: int = int(os.getenv("MARKET_CLOSE_MINUTE", "30"))
    
    # Strategy Parameters
    ADX_PERIOD: int = 14
    ADX_TRENDING_THRESHOLD: float = 25.0
    ADX_RANGING_THRESHOLD: float = 20.0
    RSI_PERIOD: int = 14
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    EMA_PERIOD: int = 200
    ATR_PERIOD: int = 14
    ATR_STOP_MULTIPLIER: float = 3.0
    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    
    # Multi-Timeframe
    ENTRY_TIMEFRAME: str = "5min"  # 5-minute for entry signals
    CONFIRMATION_TIMEFRAME: str = "60min"  # 60-minute for trend confirmation
    
    # API Settings
    API_BASE_URL: str = "https://api.upstox.com/v2"
    WS_BASE_URL: str = "wss://api.upstox.com/v2/feed"
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # Initial delay in seconds
    MAX_RETRY_DELAY: float = 60.0  # Maximum delay in seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "trading_bot.log")
    
    # Data Storage
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    TRADES_LOG_DIR: str = os.getenv("TRADES_LOG_DIR", "./logs/trades")


# Global settings instance
settings = Settings()
