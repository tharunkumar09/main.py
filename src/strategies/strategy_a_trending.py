"""
Strategy A: Trending Market Strategy
Uses RSI (14), MACD (12, 26, 9), and 200-Day EMA for entry signals
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False


class StrategyA_Trending:
    """
    Trending Market Strategy
    Entry Rules:
    - Long: RSI < 30 (oversold), MACD bullish crossover, Price > 200 EMA
    - Short: RSI > 70 (overbought), MACD bearish crossover, Price < 200 EMA
    """
    
    def __init__(self, rsi_period: int = 14, rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0, macd_fast: int = 12,
                 macd_slow: int = 26, macd_signal: int = 9,
                 ema_period: int = 200):
        """
        Initialize Strategy A
        
        Args:
            rsi_period: RSI period
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
            macd_fast: MACD fast period
            macd_slow: MACD slow period
            macd_signal: MACD signal period
            ema_period: EMA period
        """
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ema_period = ema_period
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI"""
        if TALIB_AVAILABLE:
            rsi = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
            return pd.Series(rsi, index=df.index)
        elif PANDAS_TA_AVAILABLE:
            rsi = ta.rsi(df['close'], length=self.rsi_period)
            return rsi
        else:
            # Manual RSI calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
    
    def calculate_macd(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD"""
        if TALIB_AVAILABLE:
            macd, signal, hist = talib.MACD(
                df['close'].values,
                fastperiod=self.macd_fast,
                slowperiod=self.macd_slow,
                signalperiod=self.macd_signal
            )
            return (
                pd.Series(macd, index=df.index),
                pd.Series(signal, index=df.index),
                pd.Series(hist, index=df.index)
            )
        elif PANDAS_TA_AVAILABLE:
            macd = ta.macd(df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
            if isinstance(macd, pd.DataFrame):
                return macd[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'], \
                       macd[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'], \
                       macd[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
            return macd
        else:
            # Manual MACD calculation
            ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
    
    def calculate_ema(self, df: pd.DataFrame) -> pd.Series:
        """Calculate EMA"""
        return df['close'].ewm(span=self.ema_period, adjust=False).mean()
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Generate trading signals
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal information
        """
        if len(df) < max(self.ema_period, self.macd_slow) + 1:
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'Insufficient data'
            }
        
        # Calculate indicators
        rsi = self.calculate_rsi(df)
        macd, signal, hist = self.calculate_macd(df)
        ema = self.calculate_ema(df)
        
        current_price = df['close'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_macd = macd.iloc[-1]
        prev_macd = macd.iloc[-2] if len(macd) > 1 else None
        current_signal = signal.iloc[-1]
        prev_signal = signal.iloc[-2] if len(signal) > 1 else None
        current_ema = ema.iloc[-1]
        current_hist = hist.iloc[-1]
        prev_hist = hist.iloc[-2] if len(hist) > 1 else None
        
        # Check for NaN values
        if pd.isna(current_rsi) or pd.isna(current_macd) or pd.isna(current_ema):
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'Indicators not ready'
            }
        
        # Long signal conditions
        bullish_macd_cross = (prev_macd is not None and prev_signal is not None and
                             prev_macd < prev_signal and current_macd > current_signal)
        bullish_macd_hist = (prev_hist is not None and prev_hist < 0 and current_hist > 0)
        price_above_ema = current_price > current_ema
        rsi_oversold = current_rsi < self.rsi_oversold
        
        # Short signal conditions
        bearish_macd_cross = (prev_macd is not None and prev_signal is not None and
                             prev_macd > prev_signal and current_macd < current_signal)
        bearish_macd_hist = (prev_hist is not None and prev_hist > 0 and current_hist < 0)
        price_below_ema = current_price < current_ema
        rsi_overbought = current_rsi > self.rsi_overbought
        
        # Generate signals
        long_conditions = [bullish_macd_cross or bullish_macd_hist, price_above_ema, rsi_oversold]
        short_conditions = [bearish_macd_cross or bearish_macd_hist, price_below_ema, rsi_overbought]
        
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        if long_score >= 2:
            strength = long_score / 3.0
            return {
                'signal': 'BUY',
                'side': 'BUY',
                'strength': strength,
                'reason': f'RSI: {current_rsi:.2f}, MACD Bullish, Price > EMA',
                'rsi': float(current_rsi),
                'macd': float(current_macd),
                'ema': float(current_ema)
            }
        elif short_score >= 2:
            strength = short_score / 3.0
            return {
                'signal': 'SELL',
                'side': 'SELL',
                'strength': strength,
                'reason': f'RSI: {current_rsi:.2f}, MACD Bearish, Price < EMA',
                'rsi': float(current_rsi),
                'macd': float(current_macd),
                'ema': float(current_ema)
            }
        else:
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'No clear signal',
                'rsi': float(current_rsi),
                'macd': float(current_macd),
                'ema': float(current_ema)
            }
