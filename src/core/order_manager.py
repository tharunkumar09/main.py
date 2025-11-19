"""
Order Management System
Handles order placement, modification, cancellation with TWAP/VWAP execution
"""

import time
from typing import Dict, Optional, List, Tuple
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from dataclasses import dataclass, field


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "PENDING"
    PLACED = "PLACED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class TransactionType(Enum):
    """Transaction types"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """Order data structure"""
    symbol: str
    quantity: int
    transaction_type: TransactionType
    order_type: OrderType
    price: float = 0.0
    trigger_price: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    
    # Order tracking
    order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    strategy_name: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'transaction_type': self.transaction_type.value,
            'order_type': self.order_type.value,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'stop_loss': self.stop_loss,
            'target': self.target,
            'order_id': self.order_id,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'timestamp': self.timestamp.isoformat(),
            'strategy_name': self.strategy_name,
            'notes': self.notes
        }


class TWAPExecutor:
    """
    Time-Weighted Average Price (TWAP) execution
    Splits large orders into smaller slices over time
    """
    
    def __init__(self, total_quantity: int, num_slices: int = 5, interval_seconds: int = 60):
        """
        Initialize TWAP executor
        
        Args:
            total_quantity: Total quantity to execute
            num_slices: Number of slices to split order into
            interval_seconds: Time interval between slices
        """
        self.total_quantity = total_quantity
        self.num_slices = num_slices
        self.interval_seconds = interval_seconds
        
        # Calculate slice sizes
        base_size = total_quantity // num_slices
        remainder = total_quantity % num_slices
        
        self.slices = [base_size] * num_slices
        # Distribute remainder
        for i in range(remainder):
            self.slices[i] += 1
        
        self.current_slice = 0
        self.executed_quantity = 0
        self.last_execution_time = None
    
    def get_next_slice(self) -> Optional[int]:
        """
        Get next slice quantity
        
        Returns:
            Slice quantity or None if complete
        """
        if self.current_slice >= len(self.slices):
            return None
        
        # Check timing
        if self.last_execution_time:
            elapsed = (datetime.now() - self.last_execution_time).total_seconds()
            if elapsed < self.interval_seconds:
                return None
        
        slice_qty = self.slices[self.current_slice]
        return slice_qty
    
    def mark_executed(self, quantity: int):
        """Mark slice as executed"""
        self.executed_quantity += quantity
        self.last_execution_time = datetime.now()
        self.current_slice += 1
    
    def is_complete(self) -> bool:
        """Check if execution is complete"""
        return self.executed_quantity >= self.total_quantity


class VWAPExecutor:
    """
    Volume-Weighted Average Price (VWAP) execution
    Executes orders based on market volume patterns
    """
    
    def __init__(
        self,
        total_quantity: int,
        participation_rate: float = 0.1,
        max_slice_size: int = 100
    ):
        """
        Initialize VWAP executor
        
        Args:
            total_quantity: Total quantity to execute
            participation_rate: Maximum market participation rate (0.0 to 1.0)
            max_slice_size: Maximum size per slice
        """
        self.total_quantity = total_quantity
        self.participation_rate = participation_rate
        self.max_slice_size = max_slice_size
        self.executed_quantity = 0
    
    def get_next_slice(self, recent_volume: int) -> Optional[int]:
        """
        Calculate next slice based on recent volume
        
        Args:
            recent_volume: Recent market volume
            
        Returns:
            Slice quantity or None if complete
        """
        if self.executed_quantity >= self.total_quantity:
            return None
        
        # Calculate slice size based on participation rate
        slice_qty = int(recent_volume * self.participation_rate)
        
        # Apply constraints
        slice_qty = min(slice_qty, self.max_slice_size)
        slice_qty = min(slice_qty, self.total_quantity - self.executed_quantity)
        
        return max(slice_qty, 1)  # Minimum 1 share
    
    def mark_executed(self, quantity: int):
        """Mark slice as executed"""
        self.executed_quantity += quantity
    
    def is_complete(self) -> bool:
        """Check if execution is complete"""
        return self.executed_quantity >= self.total_quantity


class OrderManager:
    """
    Advanced Order Manager with:
    - Multiple order types (Market, Limit, Stop Loss)
    - TWAP/VWAP execution for large orders
    - Bracket orders (with SL and Target)
    - Order tracking and history
    """
    
    def __init__(self, api_client, config):
        """
        Initialize order manager
        
        Args:
            api_client: Upstox API client
            config: Configuration object
        """
        self.api_client = api_client
        self.config = config
        
        # Order tracking
        self.orders: Dict[str, Order] = {}
        self.active_executions: Dict[str, TWAPExecutor] = {}
        
        # Slippage and execution settings
        self.max_slippage_percent = config.order_execution.get('slippage_percent', 0.1)
        self.order_timeout = config.order_execution.get('order_timeout_seconds', 30)
        self.max_retries = config.order_execution.get('max_retries', 3)
    
    def place_market_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: TransactionType,
        product: str = "I",
        strategy_name: str = ""
    ) -> Optional[Order]:
        """
        Place market order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            transaction_type: BUY or SELL
            product: Product type ('I' for intraday, 'D' for delivery)
            strategy_name: Strategy identifier
            
        Returns:
            Order object or None
        """
        try:
            order = Order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type,
                order_type=OrderType.MARKET,
                strategy_name=strategy_name
            )
            
            # Place order via API
            response = self.api_client.place_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type.value,
                order_type=OrderType.MARKET.value,
                product=product
            )
            
            order.order_id = response['data']['order_id']
            order.status = OrderStatus.PLACED
            self.orders[order.order_id] = order
            
            logger.info(f"Market order placed: {order.order_id} - {transaction_type.value} {quantity} {symbol}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            return None
    
    def place_limit_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
        transaction_type: TransactionType,
        product: str = "I",
        strategy_name: str = ""
    ) -> Optional[Order]:
        """
        Place limit order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price
            transaction_type: BUY or SELL
            product: Product type
            strategy_name: Strategy identifier
            
        Returns:
            Order object or None
        """
        try:
            order = Order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type,
                order_type=OrderType.LIMIT,
                price=price,
                strategy_name=strategy_name
            )
            
            response = self.api_client.place_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type.value,
                order_type=OrderType.LIMIT.value,
                product=product,
                price=price
            )
            
            order.order_id = response['data']['order_id']
            order.status = OrderStatus.PLACED
            self.orders[order.order_id] = order
            
            logger.info(f"Limit order placed: {order.order_id} - {transaction_type.value} {quantity} {symbol} @ {price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None
    
    def place_stop_loss_order(
        self,
        symbol: str,
        quantity: int,
        trigger_price: float,
        transaction_type: TransactionType,
        price: float = 0.0,
        product: str = "I",
        strategy_name: str = ""
    ) -> Optional[Order]:
        """
        Place stop loss order
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            trigger_price: Trigger price
            transaction_type: BUY or SELL
            price: Limit price (0 for SL-M)
            product: Product type
            strategy_name: Strategy identifier
            
        Returns:
            Order object or None
        """
        try:
            order_type = OrderType.STOP_LOSS if price > 0 else OrderType.STOP_LOSS_MARKET
            
            order = Order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type,
                order_type=order_type,
                price=price,
                trigger_price=trigger_price,
                strategy_name=strategy_name
            )
            
            response = self.api_client.place_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=transaction_type.value,
                order_type=order_type.value,
                product=product,
                price=price,
                trigger_price=trigger_price
            )
            
            order.order_id = response['data']['order_id']
            order.status = OrderStatus.PLACED
            self.orders[order.order_id] = order
            
            logger.info(f"Stop loss order placed: {order.order_id} - {transaction_type.value} {quantity} {symbol} @ trigger {trigger_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to place stop loss order: {e}")
            return None
    
    def place_bracket_order(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        transaction_type: TransactionType,
        product: str = "I",
        strategy_name: str = ""
    ) -> Optional[Tuple[Order, Order, Order]]:
        """
        Place bracket order (Entry + SL + Target)
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            entry_price: Entry limit price
            stop_loss: Stop loss price
            target: Target price
            transaction_type: BUY or SELL
            product: Product type
            strategy_name: Strategy identifier
            
        Returns:
            Tuple of (entry_order, sl_order, target_order) or None
        """
        try:
            # Place entry order
            entry_order = self.place_limit_order(
                symbol, quantity, entry_price, transaction_type, product, strategy_name
            )
            
            if not entry_order:
                return None
            
            # Determine SL and target transaction types
            sl_transaction = TransactionType.SELL if transaction_type == TransactionType.BUY else TransactionType.BUY
            
            # Place stop loss order
            sl_order = self.place_stop_loss_order(
                symbol, quantity, stop_loss, sl_transaction, 0.0, product, f"{strategy_name}_SL"
            )
            
            # Place target order
            target_order = self.place_limit_order(
                symbol, quantity, target, sl_transaction, product, f"{strategy_name}_TARGET"
            )
            
            if not sl_order or not target_order:
                logger.warning("Failed to place SL or Target - cancelling entry order")
                self.cancel_order(entry_order.order_id)
                return None
            
            entry_order.stop_loss = stop_loss
            entry_order.target = target
            entry_order.notes = f"Bracket: SL={sl_order.order_id}, Target={target_order.order_id}"
            
            logger.info(f"Bracket order placed: Entry={entry_order.order_id}, SL={sl_order.order_id}, Target={target_order.order_id}")
            return (entry_order, sl_order, target_order)
            
        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
            return None
    
    def execute_twap_order(
        self,
        symbol: str,
        total_quantity: int,
        transaction_type: TransactionType,
        num_slices: int = 5,
        interval_seconds: int = 60,
        product: str = "I",
        strategy_name: str = ""
    ) -> str:
        """
        Execute large order using TWAP
        
        Args:
            symbol: Trading symbol
            total_quantity: Total quantity to execute
            transaction_type: BUY or SELL
            num_slices: Number of slices
            interval_seconds: Interval between slices
            product: Product type
            strategy_name: Strategy identifier
            
        Returns:
            Execution ID
        """
        executor = TWAPExecutor(total_quantity, num_slices, interval_seconds)
        execution_id = f"TWAP_{symbol}_{datetime.now().timestamp()}"
        
        self.active_executions[execution_id] = {
            'executor': executor,
            'symbol': symbol,
            'transaction_type': transaction_type,
            'product': product,
            'strategy_name': strategy_name,
            'orders': []
        }
        
        logger.info(f"TWAP execution started: {execution_id} - {total_quantity} shares in {num_slices} slices")
        return execution_id
    
    def process_twap_executions(self):
        """Process active TWAP executions"""
        completed_executions = []
        
        for execution_id, execution_data in self.active_executions.items():
            executor = execution_data['executor']
            
            # Get next slice
            slice_qty = executor.get_next_slice()
            
            if slice_qty:
                # Place order for slice
                order = self.place_market_order(
                    symbol=execution_data['symbol'],
                    quantity=slice_qty,
                    transaction_type=execution_data['transaction_type'],
                    product=execution_data['product'],
                    strategy_name=f"{execution_data['strategy_name']}_TWAP"
                )
                
                if order:
                    executor.mark_executed(slice_qty)
                    execution_data['orders'].append(order.order_id)
                    logger.info(f"TWAP slice executed: {slice_qty} shares ({executor.executed_quantity}/{executor.total_quantity})")
            
            # Check if complete
            if executor.is_complete():
                completed_executions.append(execution_id)
                logger.info(f"TWAP execution completed: {execution_id}")
        
        # Remove completed executions
        for execution_id in completed_executions:
            del self.active_executions[execution_id]
    
    def modify_order(self, order_id: str, **kwargs) -> bool:
        """
        Modify existing order
        
        Args:
            order_id: Order ID to modify
            **kwargs: Fields to modify (quantity, price, trigger_price)
            
        Returns:
            True if successful
        """
        try:
            response = self.api_client.modify_order(order_id, **kwargs)
            
            if order_id in self.orders:
                order = self.orders[order_id]
                for key, value in kwargs.items():
                    if hasattr(order, key):
                        setattr(order, key, value)
            
            logger.info(f"Order modified: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            True if successful
        """
        try:
            response = self.api_client.cancel_order(order_id)
            
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def update_order_status(self, order_id: str):
        """
        Update order status from API
        
        Args:
            order_id: Order ID to update
        """
        try:
            response = self.api_client.get_order_history(order_id)
            order_data = response['data'][0]
            
            if order_id in self.orders:
                order = self.orders[order_id]
                order.filled_quantity = order_data.get('filled_quantity', 0)
                order.average_price = order_data.get('average_price', 0.0)
                
                status_map = {
                    'complete': OrderStatus.FILLED,
                    'cancelled': OrderStatus.CANCELLED,
                    'rejected': OrderStatus.REJECTED,
                    'open': OrderStatus.PLACED
                }
                order.status = status_map.get(order_data.get('status', 'open').lower(), OrderStatus.PLACED)
                
        except Exception as e:
            logger.error(f"Failed to update order status for {order_id}: {e}")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol"""
        return [order for order in self.orders.values() if order.symbol == symbol]
    
    def get_active_orders(self) -> List[Order]:
        """Get all active (non-filled, non-cancelled) orders"""
        return [
            order for order in self.orders.values()
            if order.status in [OrderStatus.PENDING, OrderStatus.PLACED, OrderStatus.PARTIALLY_FILLED]
        ]
    
    def get_order_history_df(self) -> pd.DataFrame:
        """Get order history as DataFrame"""
        if not self.orders:
            return pd.DataFrame()
        
        orders_data = [order.to_dict() for order in self.orders.values()]
        df = pd.DataFrame(orders_data)
        return df
    
    def __repr__(self) -> str:
        active_count = len(self.get_active_orders())
        total_count = len(self.orders)
        return f"OrderManager(active_orders={active_count}, total_orders={total_count})"
