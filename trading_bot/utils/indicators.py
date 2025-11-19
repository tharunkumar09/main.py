"""
Technical Indicators for Strategy Implementation
"""
import pandas as pd
import numpy as np
from typing import Optional


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(
    data: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average (EMA)"""
    return data.ewm(span=period, adjust=False).mean()


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average (SMA)"""
    return data.rolling(window=period).mean()


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Average True Range (ATR)"""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Average Directional Index (ADX)"""
    # Calculate True Range
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    
    # Calculate smoothed values
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # Calculate ADX
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx


def calculate_bollinger_bands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    sma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band


def calculate_bollinger_band_width(
    upper: pd.Series,
    lower: pd.Series,
    middle: pd.Series
) -> pd.Series:
    """Calculate Bollinger Band Width"""
    return (upper - lower) / middle * 100


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all technical indicators for a DataFrame"""
    result = df.copy()
    
    # Ensure we have required columns
    if 'close' not in result.columns:
        raise ValueError("DataFrame must have 'close' column")
    
    close = result['close']
    high = result.get('high', close)
    low = result.get('low', close)
    
    # RSI
    result['rsi'] = calculate_rsi(close, period=14)
    
    # MACD
    macd, signal, histogram = calculate_macd(close, fast=12, slow=26, signal=9)
    result['macd'] = macd
    result['macd_signal'] = signal
    result['macd_histogram'] = histogram
    
    # EMA
    result['ema_200'] = calculate_ema(close, period=200)
    result['ema_20'] = calculate_ema(close, period=20)
    
    # ATR
    result['atr'] = calculate_atr(high, low, close, period=14)
    
    # ADX
    result['adx'] = calculate_adx(high, low, close, period=14)
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close, period=20, std_dev=2.0)
    result['bb_upper'] = bb_upper
    result['bb_middle'] = bb_middle
    result['bb_lower'] = bb_lower
    result['bb_width'] = calculate_bollinger_band_width(bb_upper, bb_lower, bb_middle)
    
    return result
