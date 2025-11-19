"""
Portfolio and Position Manager
Real-time P&L tracking, position management, and risk monitoring
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
from loguru import logger


@dataclass
class Position:
    """Position data structure"""
    symbol: str
    quantity: int  # Positive for long, negative for short
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop: Optional[float] = None
    
    # Tracking
    entry_time: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""
    realized_pnl: float = 0.0
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0
    
    @property
    def abs_quantity(self) -> int:
        """Absolute quantity"""
        return abs(self.quantity)
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L"""
        if self.is_long:
            return (self.current_price - self.entry_price) * self.abs_quantity
        else:
            return (self.entry_price - self.current_price) * self.abs_quantity
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Calculate unrealized P&L percentage"""
        if self.entry_price == 0:
            return 0.0
        return (self.unrealized_pnl / (self.entry_price * self.abs_quantity)) * 100
    
    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def position_value(self) -> float:
        """Current position value"""
        return self.current_price * self.abs_quantity
    
    def update_price(self, price: float):
        """Update current price"""
        self.current_price = price
    
    def update_trailing_stop(self, new_stop: float):
        """Update trailing stop loss"""
        if self.is_long:
            # For long positions, trailing stop can only move up
            if self.trailing_stop is None or new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
                logger.debug(f"Trailing stop updated for {self.symbol}: {new_stop}")
        else:
            # For short positions, trailing stop can only move down
            if self.trailing_stop is None or new_stop < self.trailing_stop:
                self.trailing_stop = new_stop
                logger.debug(f"Trailing stop updated for {self.symbol}: {new_stop}")
    
    def check_stop_loss_hit(self) -> bool:
        """Check if stop loss is hit"""
        if self.stop_loss is None:
            return False
        
        if self.is_long:
            return self.current_price <= self.stop_loss
        else:
            return self.current_price >= self.stop_loss
    
    def check_trailing_stop_hit(self) -> bool:
        """Check if trailing stop is hit"""
        if self.trailing_stop is None:
            return False
        
        if self.is_long:
            return self.current_price <= self.trailing_stop
        else:
            return self.current_price >= self.trailing_stop
    
    def check_target_hit(self) -> bool:
        """Check if target is hit"""
        if self.target is None:
            return False
        
        if self.is_long:
            return self.current_price >= self.target
        else:
            return self.current_price <= self.target
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'stop_loss': self.stop_loss,
            'target': self.target,
            'trailing_stop': self.trailing_stop,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_percent': self.unrealized_pnl_percent,
            'realized_pnl': self.realized_pnl,
            'total_pnl': self.total_pnl,
            'position_value': self.position_value,
            'entry_time': self.entry_time.isoformat(),
            'strategy_name': self.strategy_name
        }


@dataclass
class Trade:
    """Completed trade record"""
    symbol: str
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_percent: float
    strategy_name: str = ""
    exit_reason: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'strategy_name': self.strategy_name,
            'exit_reason': self.exit_reason,
            'duration': (self.exit_time - self.entry_time).total_seconds() / 60  # minutes
        }


class PortfolioManager:
    """
    Portfolio Manager with:
    - Real-time position tracking
    - P&L calculation (realized and unrealized)
    - Trade history logging
    - Risk monitoring
    - Portfolio-level metrics
    """
    
    def __init__(self, api_client, config, initial_capital: float):
        """
        Initialize portfolio manager
        
        Args:
            api_client: Upstox API client
            config: Configuration object
            initial_capital: Starting capital
        """
        self.api_client = api_client
        self.config = config
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Positions and trades
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_starting_capital = initial_capital
        self.trading_day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Risk limits
        self.max_positions = config.trading.max_positions
        self.max_daily_loss_percent = config.trading.max_daily_loss_percent
    
    def open_position(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        strategy_name: str = ""
    ) -> Optional[Position]:
        """
        Open new position
        
        Args:
            symbol: Trading symbol
            quantity: Position quantity (positive for long, negative for short)
            entry_price: Entry price
            stop_loss: Stop loss price
            target: Target price
            strategy_name: Strategy identifier
            
        Returns:
            Position object or None
        """
        try:
            # Check if already have position in this symbol
            if symbol in self.positions:
                logger.warning(f"Position already exists for {symbol}")
                return None
            
            # Check max positions limit
            if len(self.positions) >= self.max_positions:
                logger.warning(f"Max positions limit reached: {self.max_positions}")
                return None
            
            # Create position
            position = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                current_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                strategy_name=strategy_name
            )
            
            self.positions[symbol] = position
            
            # Update capital
            position_cost = abs(quantity) * entry_price
            self.current_capital -= position_cost
            
            logger.info(f"Position opened: {quantity} {symbol} @ {entry_price}, SL: {stop_loss}, Target: {target}")
            return position
            
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            return None
    
    def close_position(
        self,
        symbol: str,
        exit_price: Optional[float] = None,
        exit_reason: str = ""
    ) -> Optional[Trade]:
        """
        Close position
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price (uses current price if None)
            exit_reason: Reason for exit
            
        Returns:
            Trade object or None
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"No position found for {symbol}")
                return None
            
            position = self.positions[symbol]
            
            # Use current price if exit price not provided
            if exit_price is None:
                exit_price = position.current_price
            
            # Calculate P&L
            if position.is_long:
                pnl = (exit_price - position.entry_price) * position.abs_quantity
            else:
                pnl = (position.entry_price - exit_price) * position.abs_quantity
            
            pnl_percent = (pnl / (position.entry_price * position.abs_quantity)) * 100
            
            # Create trade record
            trade = Trade(
                symbol=symbol,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                entry_time=position.entry_time,
                exit_time=datetime.now(),
                pnl=pnl,
                pnl_percent=pnl_percent,
                strategy_name=position.strategy_name,
                exit_reason=exit_reason
            )
            
            self.trades.append(trade)
            
            # Update capital and daily P&L
            self.current_capital += (position.abs_quantity * position.entry_price) + pnl
            self.daily_pnl += pnl
            
            # Remove position
            del self.positions[symbol]
            
            logger.info(f"Position closed: {symbol} @ {exit_price}, P&L: {pnl:.2f} ({pnl_percent:.2f}%), Reason: {exit_reason}")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to close position for {symbol}: {e}")
            return None
    
    def update_position_price(self, symbol: str, price: float):
        """
        Update position with current market price
        
        Args:
            symbol: Trading symbol
            price: Current price
        """
        if symbol in self.positions:
            self.positions[symbol].update_price(price)
    
    def update_position_trailing_stop(self, symbol: str, new_stop: float):
        """
        Update trailing stop for position
        
        Args:
            symbol: Trading symbol
            new_stop: New trailing stop price
        """
        if symbol in self.positions:
            self.positions[symbol].update_trailing_stop(new_stop)
    
    def check_stops_and_targets(self) -> List[str]:
        """
        Check all positions for stop loss and target hits
        
        Returns:
            List of symbols that need to be closed
        """
        symbols_to_close = []
        
        for symbol, position in self.positions.items():
            # Check trailing stop first (higher priority)
            if position.check_trailing_stop_hit():
                logger.warning(f"Trailing stop hit for {symbol}: {position.current_price} <= {position.trailing_stop}")
                symbols_to_close.append((symbol, "Trailing Stop"))
                continue
            
            # Check regular stop loss
            if position.check_stop_loss_hit():
                logger.warning(f"Stop loss hit for {symbol}: {position.current_price} vs {position.stop_loss}")
                symbols_to_close.append((symbol, "Stop Loss"))
                continue
            
            # Check target
            if position.check_target_hit():
                logger.info(f"Target hit for {symbol}: {position.current_price} vs {position.target}")
                symbols_to_close.append((symbol, "Target"))
        
        return symbols_to_close
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists for symbol"""
        return symbol in self.positions
    
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        return list(self.positions.values())
    
    def get_portfolio_value(self) -> float:
        """
        Calculate total portfolio value
        
        Returns:
            Total portfolio value
        """
        positions_value = sum(pos.position_value for pos in self.positions.values())
        return self.current_capital + positions_value
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_total_pnl(self) -> float:
        """Get total P&L (realized + unrealized)"""
        return self.daily_pnl + self.get_total_unrealized_pnl()
    
    def get_daily_pnl_percent(self) -> float:
        """Get daily P&L percentage"""
        if self.daily_starting_capital == 0:
            return 0.0
        return (self.get_total_pnl() / self.daily_starting_capital) * 100
    
    def is_daily_loss_limit_hit(self) -> bool:
        """
        Check if daily loss limit is hit
        
        Returns:
            True if daily loss exceeds limit
        """
        daily_loss_percent = abs(min(self.get_daily_pnl_percent(), 0))
        return daily_loss_percent >= self.max_daily_loss_percent
    
    def can_open_new_position(self) -> bool:
        """Check if new position can be opened"""
        return len(self.positions) < self.max_positions
    
    def square_off_all_positions(self, reason: str = "Square Off"):
        """
        Close all open positions
        
        Args:
            reason: Reason for closing all positions
        """
        logger.warning(f"Squaring off all positions: {reason}")
        
        symbols = list(self.positions.keys())
        for symbol in symbols:
            self.close_position(symbol, exit_reason=reason)
        
        logger.info("All positions squared off")
    
    def sync_with_broker(self):
        """Synchronize positions with broker"""
        try:
            response = self.api_client.get_positions()
            broker_positions = response.get('data', [])
            
            # Update existing positions
            for broker_pos in broker_positions:
                symbol = broker_pos.get('tradingsymbol')
                if symbol in self.positions:
                    quantity = broker_pos.get('net_quantity', 0)
                    if quantity == 0:
                        # Position closed at broker
                        self.close_position(symbol, exit_reason="Synced from broker")
            
            logger.debug("Portfolio synced with broker")
            
        except Exception as e:
            logger.error(f"Failed to sync with broker: {e}")
    
    def reset_daily_tracking(self):
        """Reset daily tracking (call at start of new trading day)"""
        self.daily_pnl = 0.0
        self.daily_starting_capital = self.get_portfolio_value()
        self.trading_day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info("Daily tracking reset")
    
    def get_trade_statistics(self) -> Dict:
        """
        Calculate trade statistics
        
        Returns:
            Dictionary of statistics
        """
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'total_pnl': 0.0
            }
        
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100,
            'avg_win': total_wins / len(winning_trades) if winning_trades else 0.0,
            'avg_loss': total_losses / len(losing_trades) if losing_trades else 0.0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'total_pnl': sum(t.pnl for t in self.trades),
            'best_trade': max((t.pnl for t in self.trades), default=0),
            'worst_trade': min((t.pnl for t in self.trades), default=0)
        }
    
    def get_positions_df(self) -> pd.DataFrame:
        """Get positions as DataFrame"""
        if not self.positions:
            return pd.DataFrame()
        
        positions_data = [pos.to_dict() for pos in self.positions.values()]
        return pd.DataFrame(positions_data)
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trade history as DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = [trade.to_dict() for trade in self.trades]
        return pd.DataFrame(trades_data)
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get comprehensive portfolio summary
        
        Returns:
            Portfolio summary dictionary
        """
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'portfolio_value': self.get_portfolio_value(),
            'open_positions': len(self.positions),
            'total_unrealized_pnl': self.get_total_unrealized_pnl(),
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.get_total_pnl(),
            'daily_pnl_percent': self.get_daily_pnl_percent(),
            'total_return_percent': ((self.get_portfolio_value() - self.initial_capital) / self.initial_capital) * 100,
            **self.get_trade_statistics()
        }
    
    def __repr__(self) -> str:
        return f"PortfolioManager(positions={len(self.positions)}, capital={self.current_capital:.2f}, daily_pnl={self.daily_pnl:.2f})"
