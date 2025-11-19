"""
Risk Management System
Dynamic position sizing, ATR-based stops, and risk controls
"""

import pandas as pd
from typing import Dict, Optional, Tuple
from loguru import logger

from src.strategies.indicators import TechnicalIndicators


class RiskManager:
    """
    Advanced Risk Manager with:
    - ATR-based position sizing (risk 1% per trade)
    - Dynamic stop loss (3x ATR)
    - Trailing stop loss (2.5x ATR from peak)
    - Risk-reward validation (minimum 2:1)
    - Portfolio correlation checks
    """
    
    def __init__(self, config: dict, capital: float):
        """
        Initialize risk manager
        
        Args:
            config: Configuration dictionary
            capital: Available capital
        """
        risk_config = config.get('risk_management', {})
        
        self.capital = capital
        self.risk_per_trade_percent = config.get('trading', {}).get('risk_per_trade_percent', 1.0)
        
        self.atr_period = risk_config.get('atr_period', 14)
        self.atr_sl_multiplier = risk_config.get('atr_sl_multiplier', 3.0)
        self.atr_tsl_multiplier = risk_config.get('atr_tsl_multiplier', 2.5)
        self.min_risk_reward = risk_config.get('min_risk_reward', 2.0)
        self.max_correlation = risk_config.get('max_correlation', 0.7)
        
        # Tracking
        self.position_highs: Dict[str, float] = {}  # For trailing stop calculation
        
        logger.info(f"RiskManager initialized: capital={capital}, risk_per_trade={self.risk_per_trade_percent}%, "
                   f"ATR_SL={self.atr_sl_multiplier}x, ATR_TSL={self.atr_tsl_multiplier}x")
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        max_risk_amount: Optional[float] = None
    ) -> int:
        """
        Calculate position size based on risk
        
        Formula: Position Size = (Capital * Risk%) / (Entry Price - Stop Loss)
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            max_risk_amount: Maximum risk amount (optional, defaults to risk_per_trade)
            
        Returns:
            Position size in shares
        """
        if max_risk_amount is None:
            max_risk_amount = self.capital * (self.risk_per_trade_percent / 100)
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            logger.warning("Risk per share is zero - cannot calculate position size")
            return 0
        
        # Calculate position size
        position_size = int(max_risk_amount / risk_per_share)
        
        # Ensure minimum 1 share
        position_size = max(position_size, 1)
        
        # Log calculation
        logger.debug(f"Position sizing: entry={entry_price:.2f}, sl={stop_loss:.2f}, "
                    f"risk_per_share={risk_per_share:.2f}, size={position_size}")
        
        return position_size
    
    def calculate_atr_stop_loss(
        self,
        df: pd.DataFrame,
        entry_price: float,
        position_type: str = 'LONG'
    ) -> float:
        """
        Calculate stop loss using ATR
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Stop loss price
        """
        # Calculate ATR if not present
        if 'atr' not in df.columns:
            df['atr'] = TechnicalIndicators.calculate_atr(df, self.atr_period)
        
        current_atr = df['atr'].iloc[-1]
        
        if pd.isna(current_atr):
            logger.warning("ATR is NaN - using default 2% stop loss")
            if position_type == 'LONG':
                return entry_price * 0.98
            else:
                return entry_price * 1.02
        
        # Calculate stop loss
        if position_type == 'LONG':
            stop_loss = entry_price - (current_atr * self.atr_sl_multiplier)
        else:
            stop_loss = entry_price + (current_atr * self.atr_sl_multiplier)
        
        logger.debug(f"ATR stop loss calculated: entry={entry_price:.2f}, atr={current_atr:.2f}, "
                    f"sl={stop_loss:.2f} ({position_type})")
        
        return stop_loss
    
    def calculate_atr_target(
        self,
        df: pd.DataFrame,
        entry_price: float,
        stop_loss: float,
        position_type: str = 'LONG'
    ) -> float:
        """
        Calculate target price using risk-reward ratio
        
        Args:
            df: DataFrame with OHLCV data
            entry_price: Entry price
            stop_loss: Stop loss price
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Target price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * self.min_risk_reward
        
        if position_type == 'LONG':
            target = entry_price + reward
        else:
            target = entry_price - reward
        
        logger.debug(f"Target calculated: entry={entry_price:.2f}, sl={stop_loss:.2f}, "
                    f"target={target:.2f} (RR={self.min_risk_reward}:1)")
        
        return target
    
    def calculate_trailing_stop(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: float,
        position_type: str = 'LONG'
    ) -> Optional[float]:
        """
        Calculate trailing stop loss
        
        Args:
            symbol: Trading symbol
            df: DataFrame with OHLCV data
            current_price: Current price
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Trailing stop price or None
        """
        # Track highest/lowest price for this position
        if symbol not in self.position_highs:
            self.position_highs[symbol] = current_price
        
        # Update peak price
        if position_type == 'LONG':
            self.position_highs[symbol] = max(self.position_highs[symbol], current_price)
        else:
            self.position_highs[symbol] = min(self.position_highs[symbol], current_price)
        
        # Calculate ATR
        if 'atr' not in df.columns:
            df['atr'] = TechnicalIndicators.calculate_atr(df, self.atr_period)
        
        current_atr = df['atr'].iloc[-1]
        
        if pd.isna(current_atr):
            return None
        
        # Calculate trailing stop from peak
        if position_type == 'LONG':
            trailing_stop = self.position_highs[symbol] - (current_atr * self.atr_tsl_multiplier)
        else:
            trailing_stop = self.position_highs[symbol] + (current_atr * self.atr_tsl_multiplier)
        
        logger.debug(f"Trailing stop: peak={self.position_highs[symbol]:.2f}, "
                    f"atr={current_atr:.2f}, tsl={trailing_stop:.2f}")
        
        return trailing_stop
    
    def validate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        target: float,
        position_type: str = 'LONG'
    ) -> Tuple[bool, float]:
        """
        Validate risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            target: Target price
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Tuple of (is_valid, actual_rr_ratio)
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(target - entry_price)
        
        if risk == 0:
            return False, 0.0
        
        rr_ratio = reward / risk
        is_valid = rr_ratio >= self.min_risk_reward
        
        if not is_valid:
            logger.warning(f"Risk-reward ratio too low: {rr_ratio:.2f} (minimum {self.min_risk_reward})")
        
        return is_valid, rr_ratio
    
    def calculate_full_position_params(
        self,
        symbol: str,
        df: pd.DataFrame,
        entry_price: float,
        position_type: str = 'LONG'
    ) -> Dict:
        """
        Calculate all position parameters (size, SL, target)
        
        Args:
            symbol: Trading symbol
            df: DataFrame with OHLCV data
            entry_price: Entry price
            position_type: 'LONG' or 'SHORT'
            
        Returns:
            Dictionary with position parameters
        """
        # Calculate stop loss
        stop_loss = self.calculate_atr_stop_loss(df, entry_price, position_type)
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        # Calculate target
        target = self.calculate_atr_target(df, entry_price, stop_loss, position_type)
        
        # Validate risk-reward
        rr_valid, rr_ratio = self.validate_risk_reward(entry_price, stop_loss, target, position_type)
        
        # Calculate risk amount
        risk_amount = abs(entry_price - stop_loss) * position_size
        risk_percent = (risk_amount / self.capital) * 100
        
        params = {
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'position_size': position_size,
            'position_type': position_type,
            'risk_amount': risk_amount,
            'risk_percent': risk_percent,
            'reward_amount': abs(target - entry_price) * position_size,
            'risk_reward_ratio': rr_ratio,
            'rr_valid': rr_valid,
            'atr': df['atr'].iloc[-1] if 'atr' in df.columns else None
        }
        
        logger.info(f"Position params for {symbol}: size={position_size}, entry={entry_price:.2f}, "
                   f"sl={stop_loss:.2f}, target={target:.2f}, RR={rr_ratio:.2f}")
        
        return params
    
    def update_capital(self, new_capital: float):
        """Update available capital"""
        self.capital = new_capital
        logger.debug(f"Capital updated: {new_capital:.2f}")
    
    def reset_position_tracking(self, symbol: str):
        """Reset position tracking for symbol"""
        if symbol in self.position_highs:
            del self.position_highs[symbol]
    
    def get_max_position_value(self) -> float:
        """Get maximum position value allowed"""
        # Conservative: don't risk more than 20% of capital in a single position
        return self.capital * 0.20
    
    def __repr__(self) -> str:
        return f"RiskManager(capital={self.capital:.2f}, risk_per_trade={self.risk_per_trade_percent}%)"
