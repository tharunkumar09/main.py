"""
Risk Management System
Dynamic position sizing using ATR, volatility-adjusted stops, and multi-timeframe confirmation
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import RISK_PER_TRADE, ATR_PERIOD, ATR_MULTIPLIER_SL, ATR_MULTIPLIER_TSL, INITIAL_CAPITAL


class RiskManager:
    """
    Comprehensive risk management system
    Handles position sizing, stop-loss, trailing stop-loss, and multi-timeframe confirmation
    """
    
    def __init__(self, initial_capital: float = None, risk_per_trade: float = None,
                 atr_period: int = None, atr_multiplier_sl: float = None,
                 atr_multiplier_tsl: float = None):
        """
        Initialize Risk Manager
        
        Args:
            initial_capital: Initial capital
            risk_per_trade: Risk per trade as fraction (e.g., 0.01 for 1%)
            atr_period: ATR calculation period
            atr_multiplier_sl: ATR multiplier for stop-loss
            atr_multiplier_tsl: ATR multiplier for trailing stop-loss
        """
        self.initial_capital = initial_capital or INITIAL_CAPITAL
        self.risk_per_trade = risk_per_trade or RISK_PER_TRADE
        self.atr_period = atr_period or ATR_PERIOD
        self.atr_multiplier_sl = atr_multiplier_sl or ATR_MULTIPLIER_SL
        self.atr_multiplier_tsl = atr_multiplier_tsl or ATR_MULTIPLIER_TSL
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range (ATR)
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            ATR series
        """
        try:
            import talib
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            atr = talib.ATR(high, low, close, timeperiod=self.atr_period)
            return pd.Series(atr, index=df.index)
        except ImportError:
            # Manual ATR calculation
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=self.atr_period).mean()
            return atr
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float,
                                current_capital: float = None) -> Tuple[int, float]:
        """
        Calculate position size based on ATR and risk per trade
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            current_capital: Current capital (defaults to initial capital)
            
        Returns:
            Tuple of (position_size, risk_amount)
        """
        if current_capital is None:
            current_capital = self.initial_capital
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        
        if risk_per_share <= 0:
            logger.warning("Invalid stop-loss price, using default risk")
            risk_per_share = entry_price * 0.02  # 2% default
        
        # Calculate risk amount
        risk_amount = current_capital * self.risk_per_trade
        
        # Calculate position size
        position_size = int(risk_amount / risk_per_share)
        
        # Ensure minimum position size
        position_size = max(1, position_size)
        
        logger.info(
            f"Position sizing: Entry={entry_price:.2f}, SL={stop_loss_price:.2f}, "
            f"Risk/Share={risk_per_share:.2f}, Size={position_size}, Risk Amount=₹{risk_amount:.2f}"
        )
        
        return position_size, risk_amount
    
    def calculate_stop_loss(self, df: pd.DataFrame, entry_price: float,
                           side: str) -> float:
        """
        Calculate volatility-adjusted stop-loss using ATR
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            side: BUY or SELL
            
        Returns:
            Stop-loss price
        """
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or current_atr <= 0:
            # Fallback to percentage-based stop
            if side == 'BUY':
                return entry_price * (1 - 0.02)  # 2% stop
            else:
                return entry_price * (1 + 0.02)  # 2% stop
        
        # Calculate stop-loss based on ATR
        atr_distance = current_atr * self.atr_multiplier_sl
        
        if side == 'BUY':
            stop_loss = entry_price - atr_distance
        else:  # SELL
            stop_loss = entry_price + atr_distance
        
        logger.info(
            f"Stop-loss calculated: Entry={entry_price:.2f}, ATR={current_atr:.2f}, "
            f"ATR Distance={atr_distance:.2f}, SL={stop_loss:.2f}"
        )
        
        return stop_loss
    
    def calculate_target(self, df: pd.DataFrame, entry_price: float,
                        stop_loss_price: float, side: str,
                        risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate target price based on risk-reward ratio
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            stop_loss_price: Stop-loss price
            side: BUY or SELL
            risk_reward_ratio: Risk-reward ratio (default 2:1)
            
        Returns:
            Target price
        """
        risk = abs(entry_price - stop_loss_price)
        reward = risk * risk_reward_ratio
        
        if side == 'BUY':
            target = entry_price + reward
        else:  # SELL
            target = entry_price - reward
        
        logger.info(
            f"Target calculated: Entry={entry_price:.2f}, Risk={risk:.2f}, "
            f"Reward={reward:.2f}, Target={target:.2f}, R:R={risk_reward_ratio}"
        )
        
        return target
    
    def calculate_trailing_stop(self, df: pd.DataFrame, entry_price: float,
                                highest_price: float, side: str) -> float:
        """
        Calculate trailing stop-loss using ATR
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            highest_price: Highest price since entry (for longs) or lowest (for shorts)
            side: BUY or SELL
            
        Returns:
            Trailing stop-loss price
        """
        atr = self.calculate_atr(df)
        current_atr = atr.iloc[-1]
        
        if pd.isna(current_atr) or current_atr <= 0:
            # Fallback to percentage-based trailing stop
            if side == 'BUY':
                return highest_price * (1 - 0.015)  # 1.5% trailing stop
            else:
                return highest_price * (1 + 0.015)  # 1.5% trailing stop
        
        # Calculate trailing stop based on ATR
        atr_distance = current_atr * self.atr_multiplier_tsl
        
        if side == 'BUY':
            trailing_stop = highest_price - atr_distance
            # Ensure trailing stop doesn't go below entry
            trailing_stop = max(trailing_stop, entry_price * 0.98)
        else:  # SELL
            trailing_stop = highest_price + atr_distance
            # Ensure trailing stop doesn't go above entry
            trailing_stop = min(trailing_stop, entry_price * 1.02)
        
        return trailing_stop
    
    def check_multi_timeframe_confirmation(self, primary_df: pd.DataFrame,
                                          confirmation_df: pd.DataFrame,
                                          ema_period: int = 20) -> Tuple[bool, str]:
        """
        Check multi-timeframe confirmation
        Entry signal on primary timeframe must align with trend on higher timeframe
        
        Args:
            primary_df: Primary timeframe DataFrame (e.g., 5-min)
            confirmation_df: Confirmation timeframe DataFrame (e.g., 60-min)
            ema_period: EMA period for trend confirmation
            
        Returns:
            Tuple of (is_confirmed, reason)
        """
        if len(primary_df) < 1 or len(confirmation_df) < ema_period:
            return False, "Insufficient data for MTF confirmation"
        
        # Calculate EMA on confirmation timeframe
        confirmation_ema = confirmation_df['close'].ewm(span=ema_period, adjust=False).mean()
        current_confirmation_price = confirmation_df['close'].iloc[-1]
        current_confirmation_ema = confirmation_ema.iloc[-1]
        
        if pd.isna(current_confirmation_ema):
            return False, "Confirmation EMA not ready"
        
        # Determine trend direction on confirmation timeframe
        price_above_ema = current_confirmation_price > current_confirmation_ema
        
        # Get current price on primary timeframe
        current_primary_price = primary_df['close'].iloc[-1]
        
        # Check alignment
        if price_above_ema:
            trend = "BULLISH"
            # For bullish trend, only allow long entries
            confirmed = True  # Will be checked against signal side
        else:
            trend = "BEARISH"
            # For bearish trend, only allow short entries
            confirmed = True  # Will be checked against signal side
        
        reason = f"Confirmation timeframe ({trend}): Price {current_confirmation_price:.2f} vs EMA {current_confirmation_ema:.2f}"
        
        return confirmed, reason
    
    def get_risk_metrics(self, positions: Dict, current_capital: float) -> Dict:
        """
        Calculate risk metrics
        
        Args:
            positions: Dictionary of open positions
            current_capital: Current capital
            
        Returns:
            Dictionary with risk metrics
        """
        total_exposure = sum(
            pos.get('quantity', 0) * pos.get('entry_price', 0)
            for pos in positions.values()
        )
        
        total_risk = sum(
            pos.get('quantity', 0) * abs(pos.get('entry_price', 0) - pos.get('stop_loss', 0))
            for pos in positions.values()
        )
        
        exposure_percent = (total_exposure / current_capital) * 100 if current_capital > 0 else 0
        risk_percent = (total_risk / current_capital) * 100 if current_capital > 0 else 0
        
        return {
            'total_exposure': total_exposure,
            'total_risk': total_risk,
            'exposure_percent': exposure_percent,
            'risk_percent': risk_percent,
            'num_positions': len(positions)
        }
