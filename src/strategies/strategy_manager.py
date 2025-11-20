"""
Strategy B: Ranging Market Strategy (Mean Reversion)
Uses Bollinger Bands for entry signals
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger


class StrategyB_Ranging:
    """
    Ranging Market Strategy (Mean Reversion)
    Entry Rules:
    - Long: Price touches lower Bollinger Band and starts reversing
    - Short: Price touches upper Bollinger Band and starts reversing
    """
    
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0,
                 rsi_period: int = 14, rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0):
        """
        Initialize Strategy B
        
        Args:
            bb_period: Bollinger Band period
            bb_std: Bollinger Band standard deviation
            rsi_period: RSI period for confirmation
            rsi_oversold: RSI oversold threshold
            rsi_overbought: RSI overbought threshold
        """
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        close = df['close']
        sma = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        
        upper_band = sma + (std * self.bb_std)
        lower_band = sma - (std * self.bb_std)
        
        return upper_band, sma, lower_band
    
    def calculate_rsi(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Generate trading signals
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with signal information
        """
        if len(df) < self.bb_period + 1:
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'Insufficient data'
            }
        
        # Calculate indicators
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(df)
        rsi = self.calculate_rsi(df)
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2] if len(df) > 1 else current_price
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_middle = middle_band.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Check for NaN values
        if pd.isna(current_upper) or pd.isna(current_lower) or pd.isna(current_rsi):
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'Indicators not ready'
            }
        
        # Calculate band positions
        band_width = current_upper - current_lower
        price_position = (current_price - current_lower) / band_width if band_width > 0 else 0.5
        
        # Long signal: Price near lower band and reversing up
        touched_lower = current_price <= current_lower * 1.01  # Within 1% of lower band
        reversing_up = current_price > prev_price
        rsi_confirmation = current_rsi < self.rsi_overbought  # Not overbought
        
        # Short signal: Price near upper band and reversing down
        touched_upper = current_price >= current_upper * 0.99  # Within 1% of upper band
        reversing_down = current_price < prev_price
        rsi_confirmation_short = current_rsi > self.rsi_oversold  # Not oversold
        
        # Generate signals
        long_conditions = [touched_lower, reversing_up, rsi_confirmation]
        short_conditions = [touched_upper, reversing_down, rsi_confirmation_short]
        
        long_score = sum(long_conditions)
        short_score = sum(short_conditions)
        
        if long_score >= 2:
            strength = long_score / 3.0
            return {
                'signal': 'BUY',
                'side': 'BUY',
                'strength': strength,
                'reason': f'Price touched lower BB and reversing, RSI: {current_rsi:.2f}',
                'rsi': float(current_rsi),
                'bb_position': float(price_position),
                'upper_band': float(current_upper),
                'lower_band': float(current_lower),
                'middle_band': float(current_middle)
            }
        elif short_score >= 2:
            strength = short_score / 3.0
            return {
                'signal': 'SELL',
                'side': 'SELL',
                'strength': strength,
                'reason': f'Price touched upper BB and reversing, RSI: {current_rsi:.2f}',
                'rsi': float(current_rsi),
                'bb_position': float(price_position),
                'upper_band': float(current_upper),
                'lower_band': float(current_lower),
                'middle_band': float(current_middle)
            }
        else:
            return {
                'signal': 'HOLD',
                'side': None,
                'strength': 0.0,
                'reason': 'No mean reversion signal',
                'rsi': float(current_rsi),
                'bb_position': float(price_position)
            }
