"""
Multi-Timeframe Analysis
Confirms entry signals by checking trend alignment on higher timeframe
"""

import pandas as pd
from typing import Dict, Optional, Tuple
from loguru import logger

from .indicators import TechnicalIndicators


class MultiTimeframeAnalyzer:
    """
    Multi-Timeframe Confirmation System
    
    Logic:
    - Primary timeframe (e.g., 1-min): Generate entry signals
    - Secondary timeframe (e.g., 60-min): Confirm trend direction
    - Only take trades when both timeframes align
    
    Example:
    - 1-min shows BUY signal
    - Check if 60-min trend is UP (price > 20 EMA)
    - If yes, take the trade. If no, skip.
    """
    
    def __init__(self, config: dict):
        """
        Initialize multi-timeframe analyzer
        
        Args:
            config: Configuration dictionary
        """
        mtf_config = config.get('strategy', {}).get('multi_timeframe', {})
        
        self.enabled = mtf_config.get('enabled', True)
        self.primary_tf = mtf_config.get('primary_tf', '1min')
        self.secondary_tf = mtf_config.get('secondary_tf', '60min')
        self.trend_ema_period = mtf_config.get('trend_ema_period', 20)
        
        logger.info(f"MultiTimeframeAnalyzer initialized: primary={self.primary_tf}, "
                   f"secondary={self.secondary_tf}, trend_ema={self.trend_ema_period}")
    
    def get_higher_timeframe_trend(self, df: pd.DataFrame) -> int:
        """
        Determine trend direction on higher timeframe
        
        Args:
            df: DataFrame with OHLCV data (higher timeframe)
            
        Returns:
            1 for uptrend, -1 for downtrend, 0 for no clear trend
        """
        if len(df) < self.trend_ema_period + 5:
            logger.warning("Insufficient data for higher timeframe analysis")
            return 0
        
        # Calculate trend EMA if not present
        if 'ema_20' not in df.columns:
            df['ema_20'] = TechnicalIndicators.calculate_ema(df, self.trend_ema_period)
        
        current_price = df['close'].iloc[-1]
        current_ema = df['ema_20'].iloc[-1]
        
        if pd.isna(current_ema):
            return 0
        
        # Additional confirmation: EMA slope
        prev_ema = df['ema_20'].iloc[-2]
        ema_rising = current_ema > prev_ema
        
        # Determine trend
        if current_price > current_ema and ema_rising:
            logger.debug(f"Higher TF: UPTREND (price={current_price:.2f}, ema={current_ema:.2f})")
            return 1
        elif current_price < current_ema and not ema_rising:
            logger.debug(f"Higher TF: DOWNTREND (price={current_price:.2f}, ema={current_ema:.2f})")
            return -1
        else:
            logger.debug(f"Higher TF: NEUTRAL (price={current_price:.2f}, ema={current_ema:.2f})")
            return 0
    
    def confirm_signal(
        self,
        signal: str,
        primary_df: pd.DataFrame,
        secondary_df: pd.DataFrame
    ) -> Tuple[bool, str]:
        """
        Confirm signal with higher timeframe
        
        Args:
            signal: 'BUY' or 'SELL' from primary timeframe
            primary_df: Primary timeframe data
            secondary_df: Secondary (higher) timeframe data
            
        Returns:
            Tuple of (confirmed, reason)
        """
        if not self.enabled:
            return True, "Multi-timeframe disabled"
        
        if signal not in ['BUY', 'SELL']:
            return False, "Invalid signal"
        
        # Get higher timeframe trend
        htf_trend = self.get_higher_timeframe_trend(secondary_df)
        
        # Confirmation logic
        if signal == 'BUY':
            if htf_trend > 0:
                return True, "Higher TF confirms UPTREND"
            elif htf_trend == 0:
                return False, "Higher TF neutral - no confirmation"
            else:
                return False, "Higher TF in DOWNTREND - conflicts with BUY signal"
        
        elif signal == 'SELL':
            if htf_trend < 0:
                return True, "Higher TF confirms DOWNTREND"
            elif htf_trend == 0:
                return False, "Higher TF neutral - no confirmation"
            else:
                return False, "Higher TF in UPTREND - conflicts with SELL signal"
        
        return False, "Unknown error"
    
    def get_mtf_info(self, primary_df: pd.DataFrame, secondary_df: pd.DataFrame) -> Dict:
        """
        Get comprehensive multi-timeframe information
        
        Args:
            primary_df: Primary timeframe data
            secondary_df: Secondary timeframe data
            
        Returns:
            Dictionary with MTF analysis
        """
        htf_trend = self.get_higher_timeframe_trend(secondary_df)
        
        primary_price = primary_df['close'].iloc[-1] if len(primary_df) > 0 else None
        secondary_price = secondary_df['close'].iloc[-1] if len(secondary_df) > 0 else None
        secondary_ema = secondary_df.get('ema_20', pd.Series([None])).iloc[-1] if len(secondary_df) > 0 else None
        
        return {
            'enabled': self.enabled,
            'primary_tf': self.primary_tf,
            'secondary_tf': self.secondary_tf,
            'primary_price': primary_price,
            'secondary_price': secondary_price,
            'secondary_ema': secondary_ema,
            'htf_trend': htf_trend,
            'htf_trend_name': 'UP' if htf_trend > 0 else 'DOWN' if htf_trend < 0 else 'NEUTRAL'
        }
    
    def resample_to_higher_timeframe(
        self,
        df: pd.DataFrame,
        target_timeframe: str
    ) -> pd.DataFrame:
        """
        Resample data to higher timeframe
        
        Args:
            df: DataFrame with timestamp index and OHLCV data
            target_timeframe: Target timeframe (e.g., '5min', '60min', '1H')
            
        Returns:
            Resampled DataFrame
        """
        # Ensure index is datetime
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # Resample OHLCV data
        resampled = df.resample(target_timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Drop NaN rows
        resampled = resampled.dropna()
        
        logger.debug(f"Resampled from {len(df)} to {len(resampled)} candles ({target_timeframe})")
        
        return resampled
    
    def __repr__(self) -> str:
        return f"MultiTimeframeAnalyzer(enabled={self.enabled}, primary={self.primary_tf}, secondary={self.secondary_tf})"
