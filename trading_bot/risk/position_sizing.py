"""
Dynamic Position Sizing using ATR
"""
import logging
from typing import Optional
import pandas as pd
from trading_bot.config.settings import settings
from trading_bot.utils.indicators import calculate_atr

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculate position size based on ATR and risk percentage"""
    
    def __init__(
        self,
        capital: float,
        risk_per_trade_percent: Optional[float] = None
    ):
        self.capital = capital
        self.risk_per_trade_percent = risk_per_trade_percent or settings.RISK_PER_TRADE_PERCENT
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        atr_value: float,
        use_atr_stop: bool = True
    ) -> tuple[int, float]:
        """
        Calculate position size based on risk percentage and stop loss distance
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop loss price
            use_atr_stop: If True, use ATR-based stop distance instead of price difference
        
        Returns:
            tuple: (quantity, risk_amount)
        """
        # Calculate risk amount (1% of capital by default)
        risk_amount = (self.capital * self.risk_per_trade_percent) / 100
        
        # Calculate stop distance
        if use_atr_stop and atr_value > 0:
            stop_distance = atr_value * settings.ATR_STOP_MULTIPLIER
        else:
            stop_distance = abs(entry_price - stop_loss_price)
        
        if stop_distance <= 0:
            logger.warning("Invalid stop distance, using minimum risk")
            return 0, 0
        
        # Calculate quantity: risk_amount / stop_distance_per_share
        quantity = int(risk_amount / stop_distance)
        
        # Ensure minimum quantity of 1
        quantity = max(1, quantity)
        
        # Recalculate actual risk amount
        actual_risk = quantity * stop_distance
        
        logger.info(
            f"Position sizing: Entry={entry_price:.2f}, SL={stop_loss_price:.2f}, "
            f"ATR={atr_value:.2f}, Quantity={quantity}, Risk={actual_risk:.2f}"
        )
        
        return quantity, actual_risk
    
    def calculate_position_size_from_atr(
        self,
        entry_price: float,
        atr_value: float,
        atr_multiplier: Optional[float] = None
    ) -> tuple[int, float, float]:
        """
        Calculate position size using ATR directly
        
        Args:
            entry_price: Entry price
            atr_value: Current ATR value
            atr_multiplier: ATR multiplier for stop loss (default from settings)
        
        Returns:
            tuple: (quantity, risk_amount, stop_loss_price)
        """
        multiplier = atr_multiplier or settings.ATR_STOP_MULTIPLIER
        stop_distance = atr_value * multiplier
        
        # Determine stop loss price (below entry for long, above for short)
        # For now, assume long position
        stop_loss_price = entry_price - stop_distance
        
        quantity, risk_amount = self.calculate_position_size(
            entry_price,
            stop_loss_price,
            atr_value,
            use_atr_stop=True
        )
        
        return quantity, risk_amount, stop_loss_price
