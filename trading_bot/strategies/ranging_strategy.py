"""
Strategy B: Ranging Strategy using Mean-Reversion with Bollinger Bands
"""
import logging
from typing import Dict
import pandas as pd
from trading_bot.strategies.base_strategy import BaseStrategy, SignalType
from trading_bot.config.settings import settings
from trading_bot.utils.indicators import calculate_bollinger_bands, calculate_rsi

logger = logging.getLogger(__name__)


class RangingStrategy(BaseStrategy):
    """Mean-reversion strategy for ranging markets using Bollinger Bands"""
    
    def __init__(
        self,
        bb_period: int = None,
        bb_std: float = None,
        rsi_period: int = None,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0
    ):
        super().__init__("Ranging Strategy")
        self.bb_period = bb_period or settings.BB_PERIOD
        self.bb_std = bb_std or settings.BB_STD
        self.rsi_period = rsi_period or settings.RSI_PERIOD
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> tuple[SignalType, Dict]:
        """
        Generate signal for ranging market (mean-reversion)
        
        Entry Rules:
        - BUY: Price touches lower Bollinger Band + RSI < 30 (oversold)
        - SELL: Price touches upper Bollinger Band + RSI > 70 (overbought)
        """
        df = self.prepare_data(df)
        
        if df.empty or len(df) < self.bb_period:
            return "HOLD", {"reason": "Insufficient data"}
        
        # Calculate Bollinger Bands if not present
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
                df['close'], self.bb_period, self.bb_std
            )
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
        
        # Calculate RSI if not present
        if 'rsi' not in df.columns:
            df['rsi'] = calculate_rsi(df['close'], self.rsi_period)
        
        # Get latest values
        latest = df.iloc[-1]
        
        bb_upper = latest.get('bb_upper', current_price)
        bb_lower = latest.get('bb_lower', current_price)
        bb_middle = latest.get('bb_middle', current_price)
        rsi = latest.get('rsi', 50)
        
        # Check for NaN values
        if pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(rsi):
            return "HOLD", {"reason": "Missing indicator data"}
        
        signal_data = {
            "bb_upper": float(bb_upper),
            "bb_lower": float(bb_lower),
            "bb_middle": float(bb_middle),
            "rsi": float(rsi),
            "current_price": current_price,
            "confidence": 0.0
        }
        
        # Calculate distance to bands
        distance_to_lower = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0
        distance_to_upper = (bb_upper - current_price) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0
        
        # BUY Signal: Price near lower band + RSI oversold
        if distance_to_lower < 0.1 and rsi < self.rsi_oversold:
            confidence = self._calculate_confidence(df, "BUY", distance_to_lower, rsi)
            signal_data.update({
                "confidence": confidence,
                "reason": f"Price near lower BB ({distance_to_lower*100:.1f}%), RSI oversold ({rsi:.2f})"
            })
            logger.info(f"BUY signal generated: {signal_data['reason']}")
            return "BUY", signal_data
        
        # SELL Signal: Price near upper band + RSI overbought
        if distance_to_upper < 0.1 and rsi > self.rsi_overbought:
            confidence = self._calculate_confidence(df, "SELL", distance_to_upper, rsi)
            signal_data.update({
                "confidence": confidence,
                "reason": f"Price near upper BB ({distance_to_upper*100:.1f}%), RSI overbought ({rsi:.2f})"
            })
            logger.info(f"SELL signal generated: {signal_data['reason']}")
            return "SELL", signal_data
        
        return "HOLD", signal_data
    
    def _calculate_confidence(
        self,
        df: pd.DataFrame,
        signal_type: str,
        band_distance: float,
        rsi: float
    ) -> float:
        """Calculate signal confidence (0-1)"""
        confidence = 0.5
        
        # Band distance confidence (closer to band = higher confidence)
        if band_distance < 0.05:
            confidence += 0.3
        elif band_distance < 0.1:
            confidence += 0.2
        
        # RSI confidence
        if signal_type == "BUY":
            if rsi < 25:
                confidence += 0.2
            elif rsi < 30:
                confidence += 0.1
        else:  # SELL
            if rsi > 75:
                confidence += 0.2
            elif rsi > 70:
                confidence += 0.1
        
        return min(1.0, confidence)
