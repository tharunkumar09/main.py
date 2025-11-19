"""
Market Regime Classifier
Uses ADX and Bollinger Band Width to classify market as Trending or Ranging
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from loguru import logger

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available, using pandas-ta fallback")

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning("pandas-ta not available")


class RegimeClassifier:
    """
    Classifies market regime as Trending or Ranging
    Uses ADX (14) and Bollinger Band Width
    """
    
    def __init__(self, adx_period: int = 14, adx_trending_threshold: float = 25.0,
                 adx_ranging_threshold: float = 20.0, bb_period: int = 20, bb_std: float = 2.0):
        """
        Initialize Regime Classifier
        
        Args:
            adx_period: ADX calculation period
            adx_trending_threshold: ADX threshold for trending market
            adx_ranging_threshold: ADX threshold for ranging market
            bb_period: Bollinger Band period
            bb_std: Bollinger Band standard deviation
        """
        self.adx_period = adx_period
        self.adx_trending_threshold = adx_trending_threshold
        self.adx_ranging_threshold = adx_ranging_threshold
        self.bb_period = bb_period
        self.bb_std = bb_std
    
    def calculate_adx(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate ADX (Average Directional Index)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            ADX series
        """
        if TALIB_AVAILABLE:
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            adx = talib.ADX(high, low, close, timeperiod=self.adx_period)
            return pd.Series(adx, index=df.index)
        elif PANDAS_TA_AVAILABLE:
            adx = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)
            if isinstance(adx, pd.DataFrame):
                return adx[f'ADX_{self.adx_period}']
            return adx
        else:
            # Manual ADX calculation
            return self._calculate_adx_manual(df)
    
    def _calculate_adx_manual(self, df: pd.DataFrame) -> pd.Series:
        """Manual ADX calculation"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # Calculate smoothed values
        atr = tr.rolling(window=self.adx_period).mean()
        plus_di = 100 * (plus_dm.rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=self.adx_period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.adx_period).mean()
        
        return adx
    
    def calculate_bb_width(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Bollinger Band Width
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Bollinger Band Width series
        """
        close = df['close']
        sma = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        
        upper_band = sma + (std * self.bb_std)
        lower_band = sma - (std * self.bb_std)
        
        # Band width as percentage of middle band
        bb_width = ((upper_band - lower_band) / sma) * 100
        
        return bb_width
    
    def classify_regime(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Classify market regime
        
        Args:
            df: DataFrame with OHLCV data (must have at least adx_period + bb_period rows)
            
        Returns:
            Dictionary with regime classification and metrics
        """
        if len(df) < max(self.adx_period, self.bb_period) + 1:
            return {
                'regime': 'UNKNOWN',
                'adx': None,
                'bb_width': None,
                'confidence': 0.0
            }
        
        # Calculate indicators
        adx = self.calculate_adx(df)
        bb_width = self.calculate_bb_width(df)
        
        current_adx = adx.iloc[-1]
        current_bb_width = bb_width.iloc[-1]
        
        # Classify regime
        if pd.isna(current_adx) or pd.isna(current_bb_width):
            regime = 'UNKNOWN'
            confidence = 0.0
        elif current_adx > self.adx_trending_threshold:
            regime = 'TRENDING'
            # Higher ADX = higher confidence
            confidence = min(1.0, current_adx / 50.0)
        elif current_adx < self.adx_ranging_threshold:
            regime = 'RANGING'
            # Lower ADX = higher confidence for ranging
            confidence = min(1.0, (self.adx_ranging_threshold - current_adx) / self.adx_ranging_threshold)
        else:
            # Ambiguous zone - use BB width as tiebreaker
            avg_bb_width = bb_width.rolling(window=20).mean().iloc[-1]
            if current_bb_width < avg_bb_width * 0.8:
                regime = 'RANGING'
                confidence = 0.6
            else:
                regime = 'TRENDING'
                confidence = 0.6
        
        return {
            'regime': regime,
            'adx': float(current_adx) if not pd.isna(current_adx) else None,
            'bb_width': float(current_bb_width) if not pd.isna(current_bb_width) else None,
            'confidence': confidence
        }
    
    def get_regime(self, df: pd.DataFrame) -> str:
        """
        Get current regime classification
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Regime string ('TRENDING', 'RANGING', or 'UNKNOWN')
        """
        result = self.classify_regime(df)
        return result['regime']
