"""
Strategy A: Trending Strategy using RSI, MACD, and 200-Day EMA
"""
import logging
from typing import Dict
import pandas as pd
from trading_bot.strategies.base_strategy import BaseStrategy, SignalType
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class TrendingStrategy(BaseStrategy):
    """Trending market strategy using RSI, MACD, and 200-EMA"""
    
    def __init__(
        self,
        rsi_period: int = None,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        macd_fast: int = None,
        macd_slow: int = None,
        macd_signal: int = None,
        ema_period: int = None
    ):
        super().__init__("Trending Strategy")
        self.rsi_period = rsi_period or settings.RSI_PERIOD
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast or settings.MACD_FAST
        self.macd_slow = macd_slow or settings.MACD_SLOW
        self.macd_signal = macd_signal or settings.MACD_SIGNAL
        self.ema_period = ema_period or settings.EMA_PERIOD
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> tuple[SignalType, Dict]:
        """
        Generate signal for trending market
        
        Entry Rules:
        - BUY: RSI < 30 (oversold), MACD line crosses above signal, Price > 200-EMA
        - SELL: RSI > 70 (overbought), MACD line crosses below signal, Price < 200-EMA
        """
        df = self.prepare_data(df)
        
        if df.empty or len(df) < max(self.ema_period, self.rsi_period, self.macd_slow):
            return "HOLD", {"reason": "Insufficient data"}
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        rsi = latest.get('rsi', 50)
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        macd_prev = prev.get('macd', 0)
        macd_signal_prev = prev.get('macd_signal', 0)
        ema_200 = latest.get('ema_200', current_price)
        
        # Check for NaN values
        if pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal) or pd.isna(ema_200):
            return "HOLD", {"reason": "Missing indicator data"}
        
        signal_data = {
            "rsi": float(rsi),
            "macd": float(macd),
            "macd_signal": float(macd_signal),
            "ema_200": float(ema_200),
            "current_price": current_price,
            "confidence": 0.0
        }
        
        # BUY Signal Conditions
        macd_bullish_cross = (macd > macd_signal) and (macd_prev <= macd_signal_prev)
        price_above_ema = current_price > ema_200
        rsi_oversold = rsi < self.rsi_oversold
        
        if macd_bullish_cross and price_above_ema and rsi_oversold:
            confidence = self._calculate_confidence(df, "BUY")
            signal_data.update({
                "confidence": confidence,
                "reason": f"MACD bullish cross, Price above 200-EMA, RSI oversold ({rsi:.2f})"
            })
            logger.info(f"BUY signal generated: {signal_data['reason']}")
            return "BUY", signal_data
        
        # SELL Signal Conditions
        macd_bearish_cross = (macd < macd_signal) and (macd_prev >= macd_signal_prev)
        price_below_ema = current_price < ema_200
        rsi_overbought = rsi > self.rsi_overbought
        
        if macd_bearish_cross and price_below_ema and rsi_overbought:
            confidence = self._calculate_confidence(df, "SELL")
            signal_data.update({
                "confidence": confidence,
                "reason": f"MACD bearish cross, Price below 200-EMA, RSI overbought ({rsi:.2f})"
            })
            logger.info(f"SELL signal generated: {signal_data['reason']}")
            return "SELL", signal_data
        
        return "HOLD", signal_data
    
    def _calculate_confidence(self, df: pd.DataFrame, signal_type: str) -> float:
        """Calculate signal confidence (0-1)"""
        if df.empty:
            return 0.5
        
        latest = df.iloc[-1]
        rsi = latest.get('rsi', 50)
        macd = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        
        confidence = 0.5
        
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
        
        # MACD confidence
        macd_diff = abs(macd - macd_signal)
        if macd_diff > 1.0:
            confidence += 0.2
        elif macd_diff > 0.5:
            confidence += 0.1
        
        return min(1.0, confidence)
