"""
Volatility-Adjusted Stop Loss and Trailing Stop Loss
"""
import logging
from typing import Optional
import pandas as pd
from trading_bot.config.settings import settings
from trading_bot.utils.indicators import calculate_atr

logger = logging.getLogger(__name__)


class StopLossManager:
    """Manage stop loss and trailing stop loss using ATR"""
    
    def __init__(self, atr_multiplier: Optional[float] = None):
        self.atr_multiplier = atr_multiplier or settings.ATR_STOP_MULTIPLIER
    
    def calculate_initial_stop_loss(
        self,
        entry_price: float,
        atr_value: float,
        is_long: bool = True
    ) -> float:
        """
        Calculate initial stop loss using ATR
        
        Args:
            entry_price: Entry price
            atr_value: Current ATR value
            is_long: True for long position, False for short
        
        Returns:
            Stop loss price
        """
        stop_distance = atr_value * self.atr_multiplier
        
        if is_long:
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        logger.info(
            f"Initial SL: Entry={entry_price:.2f}, ATR={atr_value:.2f}, "
            f"Distance={stop_distance:.2f}, SL={stop_loss:.2f}"
        )
        
        return stop_loss
    
    def calculate_trailing_stop_loss(
        self,
        entry_price: float,
        current_price: float,
        highest_price: float,  # Highest price since entry (for long)
        lowest_price: float,   # Lowest price since entry (for short)
        atr_value: float,
        is_long: bool = True
    ) -> float:
        """
        Calculate trailing stop loss using ATR
        
        Args:
            entry_price: Original entry price
            current_price: Current market price
            highest_price: Highest price reached since entry (for long positions)
            lowest_price: Lowest price reached since entry (for short positions)
            atr_value: Current ATR value
            is_long: True for long position, False for short
        
        Returns:
            Trailing stop loss price
        """
        stop_distance = atr_value * self.atr_multiplier
        
        if is_long:
            # For long positions, trail below the highest price
            trailing_stop = highest_price - stop_distance
            
            # Never move stop loss down
            initial_stop = entry_price - stop_distance
            trailing_stop = max(trailing_stop, initial_stop)
        else:
            # For short positions, trail above the lowest price
            trailing_stop = lowest_price + stop_distance
            
            # Never move stop loss down (up for short)
            initial_stop = entry_price + stop_distance
            trailing_stop = min(trailing_stop, initial_stop)
        
        logger.debug(
            f"Trailing SL: Current={current_price:.2f}, Highest={highest_price:.2f}, "
            f"Lowest={lowest_price:.2f}, ATR={atr_value:.2f}, TSL={trailing_stop:.2f}"
        )
        
        return trailing_stop
    
    def should_exit_on_stop_loss(
        self,
        current_price: float,
        stop_loss: float,
        is_long: bool = True
    ) -> bool:
        """
        Check if stop loss should be triggered
        
        Args:
            current_price: Current market price
            stop_loss: Stop loss price
            is_long: True for long position, False for short
        
        Returns:
            True if stop loss should be triggered
        """
        if is_long:
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss
    
    def update_trailing_stop(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        atr_value: float,
        position_data: dict,
        is_long: bool = True
    ) -> Optional[float]:
        """
        Update trailing stop loss for a position
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            current_price: Current market price
            atr_value: Current ATR value
            position_data: Dictionary containing position tracking data
            is_long: True for long position, False for short
        
        Returns:
            Updated trailing stop price, or None if no update needed
        """
        # Initialize tracking if not present
        if 'highest_price' not in position_data:
            position_data['highest_price'] = entry_price
            position_data['lowest_price'] = entry_price
            position_data['trailing_stop'] = self.calculate_initial_stop_loss(
                entry_price, atr_value, is_long
            )
        
        # Update highest/lowest prices
        if is_long:
            if current_price > position_data['highest_price']:
                position_data['highest_price'] = current_price
                # Recalculate trailing stop
                new_trailing_stop = self.calculate_trailing_stop_loss(
                    entry_price, current_price,
                    position_data['highest_price'],
                    position_data['lowest_price'],
                    atr_value, is_long
                )
                
                if new_trailing_stop > position_data['trailing_stop']:
                    position_data['trailing_stop'] = new_trailing_stop
                    return new_trailing_stop
        else:
            if current_price < position_data['lowest_price']:
                position_data['lowest_price'] = current_price
                # Recalculate trailing stop
                new_trailing_stop = self.calculate_trailing_stop_loss(
                    entry_price, current_price,
                    position_data['highest_price'],
                    position_data['lowest_price'],
                    atr_value, is_long
                )
                
                if new_trailing_stop < position_data['trailing_stop']:
                    position_data['trailing_stop'] = new_trailing_stop
                    return new_trailing_stop
        
        return None
