"""
Market Regime Classifier
Detects market regime (Trending vs Ranging) using ADX and Bollinger Band Width
"""

import pandas as pd
from enum import Enum
from typing import Tuple, Optional
from loguru import logger

from .indicators import TechnicalIndicators


class MarketRegime(Enum):
    """Market regime types"""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    UNDEFINED = "UNDEFINED"


class RegimeClassifier:
    """
    Market Regime Classifier using:
    - ADX (Average Directional Index)
    - Bollinger Band Width
    
    Rules:
    - TRENDING: ADX > 25 (strong trend)
    - RANGING: ADX < 20 (weak/no trend)
    - UNDEFINED: 20 <= ADX <= 25 (transition zone)
    """
    
    def __init__(self, config: dict):
        """
        Initialize regime classifier
        
        Args:
            config: Configuration dictionary
        """
        regime_config = config.get('strategy', {}).get('regime_detection', {})
        
        self.adx_period = regime_config.get('adx_period', 14)
        self.adx_trending_threshold = regime_config.get('adx_trending_threshold', 25)
        self.adx_ranging_threshold = regime_config.get('adx_ranging_threshold', 20)
        self.bb_width_period = regime_config.get('bb_width_period', 20)
        
        # Additional thresholds for Bollinger Band Width
        self.bb_width_low_threshold = 0.02  # Low volatility
        self.bb_width_high_threshold = 0.10  # High volatility
        
        logger.info(f"RegimeClassifier initialized: ADX period={self.adx_period}, "
                   f"trending_threshold={self.adx_trending_threshold}, "
                   f"ranging_threshold={self.adx_ranging_threshold}")
    
    def classify(self, df: pd.DataFrame) -> MarketRegime:
        """
        Classify current market regime
        
        Args:
            df: DataFrame with OHLCV data and indicators
            
        Returns:
            MarketRegime enum value
        """
        if len(df) < max(self.adx_period, self.bb_width_period) + 1:
            return MarketRegime.UNDEFINED
        
        # Get latest ADX value
        if 'adx' not in df.columns:
            adx, _, _ = TechnicalIndicators.calculate_adx(df, self.adx_period)
            current_adx = adx.iloc[-1]
        else:
            current_adx = df['adx'].iloc[-1]
        
        # Get latest BB Width
        if 'bb_width' not in df.columns:
            bb_width = TechnicalIndicators.calculate_bb_width(df, self.bb_width_period)
            current_bb_width = bb_width.iloc[-1]
        else:
            current_bb_width = df['bb_width'].iloc[-1]
        
        # Classification logic
        if pd.isna(current_adx) or pd.isna(current_bb_width):
            return MarketRegime.UNDEFINED
        
        # Primary classification based on ADX
        if current_adx > self.adx_trending_threshold:
            regime = MarketRegime.TRENDING
            logger.debug(f"Regime: TRENDING (ADX={current_adx:.2f}, BB_Width={current_bb_width:.4f})")
        elif current_adx < self.adx_ranging_threshold:
            regime = MarketRegime.RANGING
            logger.debug(f"Regime: RANGING (ADX={current_adx:.2f}, BB_Width={current_bb_width:.4f})")
        else:
            regime = MarketRegime.UNDEFINED
            logger.debug(f"Regime: UNDEFINED (ADX={current_adx:.2f}, BB_Width={current_bb_width:.4f})")
        
        # Secondary confirmation using BB Width
        # High BB Width confirms trending, low BB Width confirms ranging
        if regime == MarketRegime.TRENDING and current_bb_width < self.bb_width_low_threshold:
            logger.debug("BB Width too low for trending - downgrading to UNDEFINED")
            regime = MarketRegime.UNDEFINED
        elif regime == MarketRegime.RANGING and current_bb_width > self.bb_width_high_threshold:
            logger.debug("BB Width too high for ranging - upgrading to UNDEFINED")
            regime = MarketRegime.UNDEFINED
        
        return regime
    
    def get_regime_strength(self, df: pd.DataFrame) -> float:
        """
        Get regime strength (0.0 to 1.0)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Regime strength (higher = stronger trend)
        """
        if 'adx' not in df.columns:
            adx, _, _ = TechnicalIndicators.calculate_adx(df, self.adx_period)
            current_adx = adx.iloc[-1]
        else:
            current_adx = df['adx'].iloc[-1]
        
        if pd.isna(current_adx):
            return 0.0
        
        # Normalize ADX to 0-1 scale (ADX typically ranges from 0-100)
        strength = min(current_adx / 100.0, 1.0)
        return strength
    
    def get_trend_direction(self, df: pd.DataFrame) -> int:
        """
        Get trend direction
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            1 for uptrend, -1 for downtrend, 0 for no clear trend
        """
        if 'plus_di' not in df.columns or 'minus_di' not in df.columns:
            _, plus_di, minus_di = TechnicalIndicators.calculate_adx(df, self.adx_period)
            current_plus_di = plus_di.iloc[-1]
            current_minus_di = minus_di.iloc[-1]
        else:
            current_plus_di = df['plus_di'].iloc[-1]
            current_minus_di = df['minus_di'].iloc[-1]
        
        if pd.isna(current_plus_di) or pd.isna(current_minus_di):
            return 0
        
        # +DI > -DI = Uptrend, -DI > +DI = Downtrend
        if current_plus_di > current_minus_di:
            return 1
        elif current_minus_di > current_plus_di:
            return -1
        else:
            return 0
    
    def get_regime_info(self, df: pd.DataFrame) -> dict:
        """
        Get comprehensive regime information
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with regime details
        """
        regime = self.classify(df)
        strength = self.get_regime_strength(df)
        direction = self.get_trend_direction(df)
        
        adx_value = df['adx'].iloc[-1] if 'adx' in df.columns else None
        bb_width_value = df['bb_width'].iloc[-1] if 'bb_width' in df.columns else None
        
        return {
            'regime': regime,
            'regime_name': regime.value,
            'strength': strength,
            'direction': direction,
            'direction_name': 'UP' if direction > 0 else 'DOWN' if direction < 0 else 'NEUTRAL',
            'adx': adx_value,
            'bb_width': bb_width_value,
            'confidence': self._calculate_confidence(adx_value, bb_width_value)
        }
    
    def _calculate_confidence(self, adx: Optional[float], bb_width: Optional[float]) -> float:
        """
        Calculate confidence level of regime classification
        
        Args:
            adx: ADX value
            bb_width: Bollinger Band Width value
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if adx is None or pd.isna(adx):
            return 0.0
        
        # Higher confidence when ADX is far from transition zone (20-25)
        if adx > self.adx_trending_threshold:
            # Trending regime
            confidence = min((adx - self.adx_trending_threshold) / 25.0, 1.0)
        elif adx < self.adx_ranging_threshold:
            # Ranging regime
            confidence = min((self.adx_ranging_threshold - adx) / 20.0, 1.0)
        else:
            # Transition zone - low confidence
            confidence = 0.0
        
        # Boost confidence if BB width confirms
        if bb_width is not None and not pd.isna(bb_width):
            if adx > self.adx_trending_threshold and bb_width > self.bb_width_low_threshold:
                confidence *= 1.2
            elif adx < self.adx_ranging_threshold and bb_width < self.bb_width_high_threshold:
                confidence *= 1.2
        
        return min(confidence, 1.0)
    
    def __repr__(self) -> str:
        return (f"RegimeClassifier(adx_period={self.adx_period}, "
                f"trending_threshold={self.adx_trending_threshold}, "
                f"ranging_threshold={self.adx_ranging_threshold})")
