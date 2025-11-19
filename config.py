"""
Configuration file for the algorithmic trading system.
All configuration parameters are centralized here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKTEST_RESULTS_DIR = BASE_DIR / "backtest_results"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
BACKTEST_RESULTS_DIR.mkdir(exist_ok=True)

# Upstox API Configuration
UPSTOX_SANDBOX_MODE = os.getenv("UPSTOX_SANDBOX_MODE", "true").lower() == "true"  # Default to sandbox for testing
UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")
UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:3000/callback")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")

# Upstox API URLs (sandbox uses same URLs but different app credentials)
UPSTOX_API_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_WS_BASE_URL = "wss://api.upstox.com/v2/feed/market-data-feed"
UPSTOX_AUTH_BASE_URL = "https://account.upstox.com"

# Trading Configuration
INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "100000"))  # ₹1,00,000
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.01"))  # 1% per trade
MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "0.03"))  # 3% daily loss limit
CIRCUIT_BREAKER_ENABLED = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"

# Strategy Parameters
RSI_PERIOD = int(os.getenv("RSI_PERIOD", "14"))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))

MACD_FAST = int(os.getenv("MACD_FAST", "12"))
MACD_SLOW = int(os.getenv("MACD_SLOW", "26"))
MACD_SIGNAL = int(os.getenv("MACD_SIGNAL", "9"))

EMA_PERIOD = int(os.getenv("EMA_PERIOD", "200"))
ADX_PERIOD = int(os.getenv("ADX_PERIOD", "14"))
ADX_TRENDING_THRESHOLD = float(os.getenv("ADX_TRENDING_THRESHOLD", "25"))
ADX_RANGING_THRESHOLD = float(os.getenv("ADX_RANGING_THRESHOLD", "20"))

BB_PERIOD = int(os.getenv("BB_PERIOD", "20"))
BB_STD = float(os.getenv("BB_STD", "2"))

ATR_PERIOD = int(os.getenv("ATR_PERIOD", "14"))
ATR_MULTIPLIER_SL = float(os.getenv("ATR_MULTIPLIER_SL", "3.0"))
ATR_MULTIPLIER_TSL = float(os.getenv("ATR_MULTIPLIER_TSL", "2.0"))

# Timeframe Configuration
PRIMARY_TIMEFRAME = os.getenv("PRIMARY_TIMEFRAME", "1min")  # 1-minute candles
CONFIRMATION_TIMEFRAME = os.getenv("CONFIRMATION_TIMEFRAME", "60min")  # 60-minute for MTF
CONFIRMATION_EMA_PERIOD = int(os.getenv("CONFIRMATION_EMA_PERIOD", "20"))

# Order Management
MAX_ORDER_SIZE = int(os.getenv("MAX_ORDER_SIZE", "1000"))  # Maximum shares per order
TWAP_DURATION_MINUTES = int(os.getenv("TWAP_DURATION_MINUTES", "30"))  # TWAP duration
VWAP_ENABLED = os.getenv("VWAP_ENABLED", "false").lower() == "true"

# Market Hours (IST)
MARKET_OPEN_TIME = "09:15"
MARKET_CLOSE_TIME = "15:30"
PRE_MARKET_START = "09:00"

# Reconnection & Resilience
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))
INITIAL_BACKOFF_SECONDS = float(os.getenv("INITIAL_BACKOFF_SECONDS", "1.0"))
MAX_BACKOFF_SECONDS = float(os.getenv("MAX_BACKOFF_SECONDS", "60.0"))
BACKOFF_MULTIPLIER = float(os.getenv("BACKOFF_MULTIPLIER", "2.0"))

# WebSocket Configuration
WS_RECONNECT_DELAY = int(os.getenv("WS_RECONNECT_DELAY", "5"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

# External Event Filter
EXTERNAL_EVENTS_FILE = BASE_DIR / "external_events.json"
TRADING_HALT_ON_EVENTS = os.getenv("TRADING_HALT_ON_EVENTS", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "trading_bot.log"

# Backtesting Configuration
BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE", "2008-01-01")
BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE", "2024-01-01")
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
    "ICICIBANK.NS", "BHARTIARTL.NS", "SBIN.NS", "BAJFINANCE.NS", "LICI.NS",
    "ITC.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "NTPC.NS",
    "ONGC.NS", "NESTLEIND.NS", "POWERGRID.NS", "M&M.NS", "WIPRO.NS",
    "ADANIENT.NS", "JSWSTEEL.NS", "TATAMOTORS.NS", "HDFCLIFE.NS", "COALINDIA.NS",
    "DIVISLAB.NS", "TATASTEEL.NS", "BAJAJFINSV.NS", "GRASIM.NS", "SBILIFE.NS",
    "HINDALCO.NS", "CIPLA.NS", "TECHM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS",
    "INDUSINDBK.NS", "EICHERMOT.NS", "DRREDDY.NS", "HEROMOTOCO.NS", "ADANIPORTS.NS",
    "BPCL.NS", "MARICO.NS", "GODREJCP.NS", "DABUR.NS", "PIDILITIND.NS"
]
