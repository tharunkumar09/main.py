"""
Base Strategy Class
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Literal
import pandas as pd
from trading_bot.utils.indicators import calculate_all_indicators


SignalType = Literal["BUY", "SELL", "HOLD"]


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> tuple[SignalType, Dict]:
        """
        Generate trading signal
        
        Args:
            df: DataFrame with OHLCV data and indicators
            current_price: Current market price
        
        Returns:
            tuple: (signal, signal_data)
            signal: 'BUY', 'SELL', or 'HOLD'
            signal_data: Dictionary with signal details (reason, confidence, etc.)
        """
        pass
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data with all required indicators"""
        if df.empty:
            return df
        
        # Calculate indicators if not present
        required_indicators = ['rsi', 'macd', 'ema_200', 'atr']
        missing_indicators = [ind for ind in required_indicators if ind not in df.columns]
        
        if missing_indicators:
            df = calculate_all_indicators(df)
        
        return df
    
    def check_multi_timeframe_confirmation(
        self,
        higher_tf_df: pd.DataFrame,
        trend_alignment: str = "BULLISH"  # "BULLISH" or "BEARISH"
    ) -> bool:
        """
        Check if higher timeframe trend is aligned
        
        Args:
            higher_tf_df: DataFrame from higher timeframe (e.g., 60-min)
            trend_alignment: Required trend direction
        
        Returns:
            True if trend is aligned
        """
        if higher_tf_df.empty or 'ema_20' not in higher_tf_df.columns:
            return False
        
        current_price = higher_tf_df['close'].iloc[-1]
        ema_20 = higher_tf_df['ema_20'].iloc[-1]
        
        if pd.isna(ema_20):
            return False
        
        if trend_alignment == "BULLISH":
            return current_price > ema_20
        else:  # BEARISH
            return current_price < ema_20
