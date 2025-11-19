"""
Multi-Regime Strategy Classifier using ADX and Bollinger Band Width
"""
import logging
from typing import Literal
import pandas as pd
from trading_bot.config.settings import settings
from trading_bot.utils.indicators import calculate_adx, calculate_bollinger_bands, calculate_bollinger_band_width

logger = logging.getLogger(__name__)

RegimeType = Literal["TRENDING", "RANGING", "UNCERTAIN"]


class RegimeClassifier:
    """Classify market regime as Trending or Ranging"""
    
    def __init__(
        self,
        adx_period: int = None,
        adx_trending_threshold: float = None,
        adx_ranging_threshold: float = None,
        bb_period: int = None,
        bb_std: float = None
    ):
        self.adx_period = adx_period or settings.ADX_PERIOD
        self.adx_trending_threshold = adx_trending_threshold or settings.ADX_TRENDING_THRESHOLD
        self.adx_ranging_threshold = adx_ranging_threshold or settings.ADX_RANGING_THRESHOLD
        self.bb_period = bb_period or settings.BB_PERIOD
        self.bb_std = bb_std or settings.BB_STD
    
    def classify_regime(self, df: pd.DataFrame) -> RegimeType:
        """
        Classify market regime based on ADX and Bollinger Band Width
        
        Args:
            df: DataFrame with OHLCV data and calculated indicators
        
        Returns:
            'TRENDING', 'RANGING', or 'UNCERTAIN'
        """
        if df.empty or len(df) < max(self.adx_period, self.bb_period):
            return "UNCERTAIN"
        
        # Calculate ADX if not present
        if 'adx' not in df.columns:
            df['adx'] = calculate_adx(
                df['high'], df['low'], df['close'], self.adx_period
            )
        
        # Calculate Bollinger Bands if not present
        if 'bb_width' not in df.columns:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
                df['close'], self.bb_period, self.bb_std
            )
            df['bb_width'] = calculate_bollinger_band_width(bb_upper, bb_lower, bb_middle)
        
        # Get latest values
        latest_adx = df['adx'].iloc[-1]
        latest_bb_width = df['bb_width'].iloc[-1]
        
        # Classification logic
        if pd.isna(latest_adx) or pd.isna(latest_bb_width):
            return "UNCERTAIN"
        
        # Primary classification: ADX
        if latest_adx > self.adx_trending_threshold:
            regime = "TRENDING"
        elif latest_adx < self.adx_ranging_threshold:
            regime = "RANGING"
        else:
            # In between thresholds, use BB width as confirmation
            # Low BB width suggests ranging, high suggests trending
            avg_bb_width = df['bb_width'].tail(20).mean()
            if latest_bb_width < avg_bb_width * 0.8:
                regime = "RANGING"
            elif latest_bb_width > avg_bb_width * 1.2:
                regime = "TRENDING"
            else:
                regime = "UNCERTAIN"
        
        logger.debug(
            f"Regime classification: ADX={latest_adx:.2f}, BB_Width={latest_bb_width:.2f}, "
            f"Regime={regime}"
        )
        
        return regime
    
    def get_regime_confidence(self, df: pd.DataFrame) -> float:
        """
        Get confidence score for regime classification (0-1)
        
        Returns:
            Confidence score where 1.0 is highest confidence
        """
        regime = self.classify_regime(df)
        
        if regime == "UNCERTAIN":
            return 0.5
        
        if 'adx' not in df.columns:
            return 0.5
        
        latest_adx = df['adx'].iloc[-1]
        
        if pd.isna(latest_adx):
            return 0.5
        
        if regime == "TRENDING":
            # Higher ADX = higher confidence
            confidence = min(1.0, latest_adx / 50.0)
        else:  # RANGING
            # Lower ADX = higher confidence for ranging
            confidence = min(1.0, (30 - latest_adx) / 20.0)
        
        return max(0.0, confidence)
