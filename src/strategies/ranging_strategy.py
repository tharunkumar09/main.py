"""
Ranging Strategy (Strategy B)
Mean-reversion strategy using Bollinger Bands for ranging markets
"""

import pandas as pd
from typing import Optional, Dict, Tuple
from loguru import logger

from .indicators import TechnicalIndicators
from .trending_strategy import Signal


class RangingStrategy:
    """
    Mean-Reversion Strategy Logic (for ranging markets):
    
    BUY Conditions:
    1. Price touches or falls below lower Bollinger Band
    2. Price > 95% of lower BB (within touch threshold)
    3. RSI < 30 (oversold confirmation)
    4. Expect bounce back to middle band
    
    SELL Conditions:
    1. Price touches or rises above upper Bollinger Band
    2. Price < 105% of upper BB (within touch threshold)
    3. RSI > 70 (overbought confirmation)
    4. Expect reversion back to middle band
    """
    
    def __init__(self, config: dict):
        """
        Initialize ranging strategy
        
        Args:
            config: Configuration dictionary
        """
        strategy_config = config.get('strategy', {}).get('ranging_strategy', {})
        
        self.bb_period = strategy_config.get('bb_period', 20)
        self.bb_std = strategy_config.get('bb_std', 2)
        self.mean_reversion_threshold = strategy_config.get('mean_reversion_threshold', 0.95)
        
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
        self.name = "RangingStrategy"
        
        logger.info(f"RangingStrategy initialized: BB({self.bb_period},{self.bb_std}), "
                   f"threshold={self.mean_reversion_threshold}")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate required indicators
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with indicators
        """
        df = df.copy()
        
        # Bollinger Bands
        if 'bb_upper' not in df.columns:
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalIndicators.calculate_bollinger_bands(
                df, self.bb_period, self.bb_std
            )
        
        # RSI for confirmation
        if 'rsi' not in df.columns:
            df['rsi'] = TechnicalIndicators.calculate_rsi(df, self.rsi_period)
        
        # Calculate BB position (where price is within the bands)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
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
        if len(df) < self.bb_period + 10:
            return Signal.NO_SIGNAL, {'reason': 'Insufficient data'}
        
        # Calculate indicators if not present
        df = self.calculate_indicators(df)
        
        # Get current values
        current = df.iloc[-1]
        
        price = current['close']
        bb_upper = current['bb_upper']
        bb_middle = current['bb_middle']
        bb_lower = current['bb_lower']
        rsi = current['rsi']
        bb_position = current['bb_position']
        
        # Check for NaN values
        if pd.isna([price, bb_upper, bb_middle, bb_lower, rsi]).any():
            return Signal.NO_SIGNAL, {'reason': 'NaN values in indicators'}
        
        signal_info = {
            'price': price,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'rsi': rsi,
            'bb_position': bb_position,
            'conditions_met': []
        }
        
        # Calculate touch thresholds
        lower_touch_threshold = bb_lower * (2 - self.mean_reversion_threshold)
        upper_touch_threshold = bb_upper * self.mean_reversion_threshold
        
        # Check BUY conditions (price near lower band)
        buy_conditions = {
            'price_near_lower_bb': price <= lower_touch_threshold,
            'rsi_oversold': rsi < self.rsi_oversold,
            'room_to_middle': price < bb_middle  # Ensure price is below middle
        }
        
        if all(buy_conditions.values()):
            signal_info['conditions_met'] = list(buy_conditions.keys())
            signal_info['reason'] = 'Mean reversion BUY - price near lower BB'
            signal_info['distance_to_target'] = ((bb_middle - price) / price) * 100
            logger.info(f"BUY signal (mean reversion): price={price:.2f}, bb_lower={bb_lower:.2f}, "
                       f"bb_middle={bb_middle:.2f}, rsi={rsi:.2f}")
            return Signal.BUY, signal_info
        
        # Check SELL conditions (price near upper band)
        sell_conditions = {
            'price_near_upper_bb': price >= upper_touch_threshold,
            'rsi_overbought': rsi > self.rsi_overbought,
            'room_to_middle': price > bb_middle  # Ensure price is above middle
        }
        
        if all(sell_conditions.values()):
            signal_info['conditions_met'] = list(sell_conditions.keys())
            signal_info['reason'] = 'Mean reversion SELL - price near upper BB'
            signal_info['distance_to_target'] = ((price - bb_middle) / price) * 100
            logger.info(f"SELL signal (mean reversion): price={price:.2f}, bb_upper={bb_upper:.2f}, "
                       f"bb_middle={bb_middle:.2f}, rsi={rsi:.2f}")
            return Signal.SELL, signal_info
        
        # No signal
        signal_info['reason'] = 'Mean reversion conditions not met'
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
        
        price = current['close']
        bb_middle = current['bb_middle']
        bb_upper = current['bb_upper']
        bb_lower = current['bb_lower']
        
        if position_type == 'LONG':
            # Exit long when price reaches middle band (target)
            if price >= bb_middle:
                return True, "Price reached middle band (target)"
            # Exit if price breaks below lower band significantly (failed mean reversion)
            if price < bb_lower * 0.98:
                return True, "Price broke below lower band"
        
        elif position_type == 'SHORT':
            # Exit short when price reaches middle band (target)
            if price <= bb_middle:
                return True, "Price reached middle band (target)"
            # Exit if price breaks above upper band significantly (failed mean reversion)
            if price > bb_upper * 1.02:
                return True, "Price broke above upper band"
        
        return False, ""
    
    def __repr__(self) -> str:
        return f"RangingStrategy(BB={self.bb_period}/{self.bb_std})"
