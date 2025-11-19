"""
Helper utilities for the trading bot
"""
import pytz
from datetime import datetime, time
from typing import Optional
from trading_bot.config.settings import settings


def is_market_open() -> bool:
    """Check if market is currently open (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    current_time = now.time()
    
    market_open = time(settings.MARKET_OPEN_HOUR, settings.MARKET_OPEN_MINUTE)
    market_close = time(settings.MARKET_CLOSE_HOUR, settings.MARKET_CLOSE_MINUTE)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    
    return market_open <= current_time <= market_close


def get_ist_time() -> datetime:
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)


def format_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Format symbol for Upstox API"""
    # Convert symbol to instrument key format
    # This is a placeholder - actual implementation needs instrument key mapping
    return f"{exchange}_EQ:{symbol}"


def round_to_lot_size(quantity: float, lot_size: int = 1) -> int:
    """Round quantity to nearest lot size"""
    return int((quantity // lot_size) * lot_size)


def calculate_percentage(value: float, total: float) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    return (value / total) * 100
