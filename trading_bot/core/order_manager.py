"""
Order Management System with Market, Limit, SL, Bracket Orders, and TWAP/VWAP
"""
import time
import logging
from typing import Dict, List, Optional, Tuple
import requests
from datetime import datetime
import pandas as pd
from trading_bot.core.auth import UpstoxAuth
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class OrderManager:
    """Comprehensive order management system"""
    
    def __init__(self, auth: UpstoxAuth):
        self.auth = auth
        self.base_url = settings.API_BASE_URL
        self.orders: Dict[str, Dict] = {}  # order_id -> order_data
    
    def _get_exponential_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(
            settings.RETRY_DELAY * (2 ** attempt),
            settings.MAX_RETRY_DELAY
        )
        return delay
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        max_retries: int = None
    ) -> Optional[Dict]:
        """Make API request with exponential backoff retry logic"""
        max_retries = max_retries or settings.MAX_RETRIES
        headers = self.auth.get_headers()
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=data, timeout=10)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Handle rate limiting
                if response.status_code == 429:
                    delay = self._get_exponential_backoff_delay(attempt)
                    logger.warning(f"Rate limited, waiting {delay:.2f} seconds")
                    time.sleep(delay)
                    continue
                
                # Handle authentication errors
                if response.status_code == 401:
                    logger.error("Authentication failed, attempting token refresh")
                    if self.auth.refresh_access_token():
                        headers = self.auth.get_headers()
                        continue
                    else:
                        raise ValueError("Failed to refresh authentication token")
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = self._get_exponential_backoff_delay(attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
        
        return None
    
    def place_market_order(
        self,
        symbol: str,
        quantity: int,
        transaction_type: str,  # 'BUY' or 'SELL'
        product: str = "D",  # 'D' for Delivery, 'I' for Intraday
        validity: str = "DAY"
    ) -> Optional[str]:
        """Place a market order"""
        try:
            order_data = {
                "quantity": quantity,
                "product": product,
                "validity": validity,
                "price": 0,  # Market order
                "tag": "TradingBot",
                "instrument_token": symbol,  # Should be actual instrument token
                "order_type": "MARKET",
                "transaction_type": transaction_type
            }
            
            response = self._make_request("POST", "order/place", order_data)
            if response and 'data' in response:
                order_id = response['data'].get('order_id')
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'type': 'MARKET',
                    'transaction_type': transaction_type,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Market order placed: {order_id} for {symbol}")
                return order_id
            
        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
        
        return None
    
    def place_limit_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
        transaction_type: str,
        product: str = "D",
        validity: str = "DAY"
    ) -> Optional[str]:
        """Place a limit order"""
        try:
            order_data = {
                "quantity": quantity,
                "product": product,
                "validity": validity,
                "price": price,
                "tag": "TradingBot",
                "instrument_token": symbol,
                "order_type": "LIMIT",
                "transaction_type": transaction_type
            }
            
            response = self._make_request("POST", "order/place", order_data)
            if response and 'data' in response:
                order_id = response['data'].get('order_id')
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'type': 'LIMIT',
                    'transaction_type': transaction_type,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Limit order placed: {order_id} for {symbol} at {price}")
                return order_id
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
        
        return None
    
    def place_stop_loss_order(
        self,
        symbol: str,
        quantity: int,
        trigger_price: float,
        transaction_type: str,
        product: str = "D"
    ) -> Optional[str]:
        """Place a stop loss order"""
        try:
            order_data = {
                "quantity": quantity,
                "product": product,
                "validity": "DAY",
                "price": trigger_price,
                "trigger_price": trigger_price,
                "tag": "TradingBot",
                "instrument_token": symbol,
                "order_type": "SL",
                "transaction_type": transaction_type
            }
            
            response = self._make_request("POST", "order/place", order_data)
            if response and 'data' in response:
                order_id = response['data'].get('order_id')
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'trigger_price': trigger_price,
                    'type': 'STOP_LOSS',
                    'transaction_type': transaction_type,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Stop loss order placed: {order_id} for {symbol} at {trigger_price}")
                return order_id
            
        except Exception as e:
            logger.error(f"Failed to place stop loss order: {e}")
        
        return None
    
    def place_bracket_order(
        self,
        symbol: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target: float,
        transaction_type: str
    ) -> Optional[str]:
        """Place a bracket order (BO)"""
        try:
            order_data = {
                "quantity": quantity,
                "product": "B",
                "validity": "DAY",
                "price": price,
                "tag": "TradingBot",
                "instrument_token": symbol,
                "order_type": "LIMIT",
                "transaction_type": transaction_type,
                "squareoff": target,
                "stoploss": stop_loss
            }
            
            response = self._make_request("POST", "order/place", order_data)
            if response and 'data' in response:
                order_id = response['data'].get('order_id')
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'type': 'BRACKET',
                    'transaction_type': transaction_type,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Bracket order placed: {order_id} for {symbol}")
                return order_id
            
        except Exception as e:
            logger.error(f"Failed to place bracket order: {e}")
        
        return None
    
    def place_twap_order(
        self,
        symbol: str,
        total_quantity: int,
        duration_minutes: int,
        transaction_type: str,
        price: Optional[float] = None
    ) -> List[str]:
        """
        Place TWAP (Time-Weighted Average Price) order by slicing into smaller orders
        Basic implementation: divides order into equal slices over time period
        """
        order_ids = []
        num_slices = max(1, duration_minutes // 5)  # One slice every 5 minutes
        slice_quantity = total_quantity // num_slices
        remaining_quantity = total_quantity - (slice_quantity * num_slices)
        
        slice_duration = duration_minutes / num_slices
        
        logger.info(f"TWAP: Slicing {total_quantity} into {num_slices} slices over {duration_minutes} minutes")
        
        for i in range(num_slices):
            # Adjust quantity for last slice to account for remainder
            qty = slice_quantity + (remaining_quantity if i == num_slices - 1 else 0)
            
            if price:
                order_id = self.place_limit_order(symbol, qty, price, transaction_type)
            else:
                order_id = self.place_market_order(symbol, qty, transaction_type)
            
            if order_id:
                order_ids.append(order_id)
            
            # Wait before placing next slice (except for last slice)
            if i < num_slices - 1:
                time.sleep(slice_duration * 60)
        
        return order_ids
    
    def place_vwap_order(
        self,
        symbol: str,
        total_quantity: int,
        duration_minutes: int,
        transaction_type: str,
        market_data: pd.DataFrame
    ) -> List[str]:
        """
        Place VWAP (Volume-Weighted Average Price) order
        Basic implementation: slices orders based on volume distribution
        """
        order_ids = []
        
        # Calculate volume-weighted time distribution
        if market_data.empty:
            # Fallback to TWAP if no market data
            return self.place_twap_order(symbol, total_quantity, duration_minutes, transaction_type)
        
        # Get recent volume data to estimate distribution
        recent_volume = market_data['volume'].tail(20).sum()
        if recent_volume == 0:
            return self.place_twap_order(symbol, total_quantity, duration_minutes, transaction_type)
        
        # Simple volume-based slicing (can be enhanced)
        num_slices = max(1, duration_minutes // 5)
        slice_quantity = total_quantity // num_slices
        remaining_quantity = total_quantity - (slice_quantity * num_slices)
        
        logger.info(f"VWAP: Slicing {total_quantity} into {num_slices} slices based on volume")
        
        for i in range(num_slices):
            qty = slice_quantity + (remaining_quantity if i == num_slices - 1 else 0)
            order_id = self.place_market_order(symbol, qty, transaction_type)
            
            if order_id:
                order_ids.append(order_id)
            
            if i < num_slices - 1:
                time.sleep((duration_minutes / num_slices) * 60)
        
        return order_ids
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            response = self._make_request("DELETE", f"order/cancel/{order_id}")
            if response:
                if order_id in self.orders:
                    self.orders[order_id]['status'] = 'CANCELLED'
                logger.info(f"Order cancelled: {order_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
        
        return False
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        validity: Optional[str] = None
    ) -> bool:
        """Modify an existing order"""
        try:
            modify_data = {}
            if quantity:
                modify_data['quantity'] = quantity
            if price:
                modify_data['price'] = price
            if validity:
                modify_data['validity'] = validity
            
            response = self._make_request("PUT", f"order/modify/{order_id}", modify_data)
            if response:
                if order_id in self.orders:
                    self.orders[order_id].update(modify_data)
                logger.info(f"Order modified: {order_id}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to modify order: {e}")
        
        return False
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order"""
        try:
            response = self._make_request("GET", f"order/history/{order_id}")
            if response and 'data' in response:
                order_data = response['data']
                if order_id in self.orders:
                    self.orders[order_id].update(order_data)
                return order_data
            
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
        
        return None
    
    def get_all_orders(self) -> List[Dict]:
        """Get all orders"""
        try:
            response = self._make_request("GET", "order/retrieve-all")
            if response and 'data' in response:
                return response['data']
            
        except Exception as e:
            logger.error(f"Failed to get all orders: {e}")
        
        return []
