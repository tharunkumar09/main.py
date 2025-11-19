"""
Trending Strategy (Strategy A)
Uses RSI, MACD, and 200-Day EMA for trend-following entries
"""

import pandas as pd
from typing import Optional, Dict, Tuple
from loguru import logger
from enum import Enum

from .indicators import TechnicalIndicators


class Signal(Enum):
    """Trading signals"""
    BUY = "BUY"
    SELL = "SELL"
    NO_SIGNAL = "NO_SIGNAL"


class TrendingStrategy:
    """
    Trending Strategy Logic:
    
    BUY Conditions (all must be true):
    1. Price > 200 EMA (long-term uptrend)
    2. RSI < 70 (not overbought) and RSI > 30 (has momentum)
    3. MACD line crosses above signal line (bullish momentum)
    4. MACD histogram is positive
    
    SELL Conditions (all must be true):
    1. Price < 200 EMA (long-term downtrend)
    2. RSI > 30 (not oversold) and RSI < 70 (has momentum)
    3. MACD line crosses below signal line (bearish momentum)
    4. MACD histogram is negative
    """
    
    def __init__(self, config: dict):
        """
        Initialize trending strategy
        
        Args:
            config: Configuration dictionary
        """
        strategy_config = config.get('strategy', {}).get('trending_strategy', {})
        
        self.rsi_period = strategy_config.get('rsi_period', 14)
        self.rsi_oversold = strategy_config.get('rsi_oversold', 30)
        self.rsi_overbought = strategy_config.get('rsi_overbought', 70)
        
        self.macd_fast = strategy_config.get('macd_fast', 12)
        self.macd_slow = strategy_config.get('macd_slow', 26)
        self.macd_signal = strategy_config.get('macd_signal', 9)
        
        self.ema_period = strategy_config.get('ema_period', 200)
        
        self.name = "TrendingStrategy"
        
        logger.info(f"TrendingStrategy initialized: RSI({self.rsi_period}), "
                   f"MACD({self.macd_fast},{self.macd_slow},{self.macd_signal}), "
                   f"EMA({self.ema_period})")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate required indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with indicators
        """
        df = df.copy()
        
        # RSI
        if 'rsi' not in df.columns:
            df['rsi'] = TechnicalIndicators.calculate_rsi(df, self.rsi_period)
        
        # MACD
        if 'macd' not in df.columns:
            df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(
                df, self.macd_fast, self.macd_slow, self.macd_signal
            )
        
        # 200 EMA
        if 'ema_200' not in df.columns:
            df['ema_200'] = TechnicalIndicators.calculate_ema(df, self.ema_period)
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> Tuple[Signal, Dict]:
        """
        Generate trading signal
        
        Args:
            df: DataFrame with OHLCV data and indicators
            
        Returns:
            Tuple of (Signal, signal_info dict)
        """
        # Ensure we have enough data
        if len(df) < max(self.ema_period, self.macd_slow) + 10:
            return Signal.NO_SIGNAL, {'reason': 'Insufficient data'}
        
        # Calculate indicators if not present
        df = self.calculate_indicators(df)
        
        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Extract indicator values
        price = current['close']
        ema_200 = current['ema_200']
        rsi = current['rsi']
        macd = current['macd']
        macd_signal = current['macd_signal']
        macd_hist = current['macd_hist']
        
        prev_macd = previous['macd']
        prev_macd_signal = previous['macd_signal']
        
        # Check for NaN values
        if pd.isna([price, ema_200, rsi, macd, macd_signal, macd_hist]).any():
            return Signal.NO_SIGNAL, {'reason': 'NaN values in indicators'}
        
        signal_info = {
            'price': price,
            'ema_200': ema_200,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_hist': macd_hist,
            'conditions_met': []
        }
        
        # Check BUY conditions
        buy_conditions = {
            'price_above_ema': price > ema_200,
            'rsi_range': self.rsi_oversold < rsi < self.rsi_overbought,
            'macd_crossover': prev_macd <= prev_macd_signal and macd > macd_signal,
            'macd_hist_positive': macd_hist > 0
        }
        
        if all(buy_conditions.values()):
            signal_info['conditions_met'] = list(buy_conditions.keys())
            signal_info['reason'] = 'All BUY conditions met'
            logger.info(f"BUY signal generated: price={price:.2f}, ema_200={ema_200:.2f}, "
                       f"rsi={rsi:.2f}, macd_hist={macd_hist:.4f}")
            return Signal.BUY, signal_info
        
        # Check SELL conditions
        sell_conditions = {
            'price_below_ema': price < ema_200,
            'rsi_range': self.rsi_oversold < rsi < self.rsi_overbought,
            'macd_crossunder': prev_macd >= prev_macd_signal and macd < macd_signal,
            'macd_hist_negative': macd_hist < 0
        }
        
        if all(sell_conditions.values()):
            signal_info['conditions_met'] = list(sell_conditions.keys())
            signal_info['reason'] = 'All SELL conditions met'
            logger.info(f"SELL signal generated: price={price:.2f}, ema_200={ema_200:.2f}, "
                       f"rsi={rsi:.2f}, macd_hist={macd_hist:.4f}")
            return Signal.SELL, signal_info
        
        # No signal
        signal_info['reason'] = 'Conditions not met'
        signal_info['buy_conditions'] = {k: v for k, v in buy_conditions.items() if not v}
        signal_info['sell_conditions'] = {k: v for k, v in sell_conditions.items() if not v}
        
        return Signal.NO_SIGNAL, signal_info
    
    def get_exit_signal(self, df: pd.DataFrame, position_type: str) -> Tuple[bool, str]:
        """
        Check for exit signal for existing position
        
        Args:
            df: DataFrame with OHLCV data
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Tuple of (should_exit, reason)
        """
        df = self.calculate_indicators(df)
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        macd = current['macd']
        macd_signal = current['macd_signal']
        prev_macd = previous['macd']
        prev_macd_signal = previous['macd_signal']
        
        if position_type == 'LONG':
            # Exit long if MACD crosses below signal
            if prev_macd >= prev_macd_signal and macd < macd_signal:
                return True, "MACD bearish crossover"
            # Exit if price falls below 200 EMA
            if current['close'] < current['ema_200']:
                return True, "Price below 200 EMA"
        
        elif position_type == 'SHORT':
            # Exit short if MACD crosses above signal
            if prev_macd <= prev_macd_signal and macd > macd_signal:
                return True, "MACD bullish crossover"
            # Exit if price rises above 200 EMA
            if current['close'] > current['ema_200']:
                return True, "Price above 200 EMA"
        
        return False, ""
    
    def __repr__(self) -> str:
        return f"TrendingStrategy(RSI={self.rsi_period}, MACD={self.macd_fast}/{self.macd_slow}/{self.macd_signal})"
