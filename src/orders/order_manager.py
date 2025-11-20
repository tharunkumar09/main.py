"""
Order Management System
Handles Market, Limit, SL, Bracket Orders, and large order slicing via TWAP/VWAP
"""

import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from loguru import logger
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import (
    MAX_ORDER_SIZE, TWAP_DURATION_MINUTES, VWAP_ENABLED,
    INITIAL_BACKOFF_SECONDS, MAX_BACKOFF_SECONDS, BACKOFF_MULTIPLIER, MAX_RETRY_ATTEMPTS,
    UPSTOX_API_BASE_URL, UPSTOX_SANDBOX_MODE
)
from src.auth.session_manager import SessionManager


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"
    BRACKET = "BRACKET"


class ProductType(Enum):
    """Product types"""
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"


class OrderSide(Enum):
    """Order sides"""
    BUY = "BUY"
    SELL = "SELL"


class OrderManager:
    """
    Manages order placement, modification, and cancellation
    Implements TWAP/VWAP for large order slicing
    Supports both sandbox (paper trading) and production modes
    """
    
    BASE_URL = UPSTOX_API_BASE_URL
    SANDBOX_MODE = UPSTOX_SANDBOX_MODE
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize Order Manager
        
        Args:
            session_manager: Authenticated session manager
        """
        self.session_manager = session_manager
        self.orders: Dict[str, Dict] = {}  # Track orders by order_id
        self.twap_orders: Dict[str, Dict] = {}  # Track TWAP orders
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make authenticated API request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            API response
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self.session_manager.get_headers()
        
        backoff = INITIAL_BACKOFF_SECONDS
        
        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                if method == "GET":
                    response = self.session_manager.get_session().get(url, headers=headers)
                elif method == "POST":
                    response = self.session_manager.get_session().post(url, headers=headers, json=data)
                elif method == "PUT":
                    response = self.session_manager.get_session().put(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = self.session_manager.get_session().delete(url, headers=headers)
                
                # Handle 401 - Token expired
                if response.status_code == 401:
                    logger.warning("Token expired, refreshing...")
                    if self.session_manager.refresh_access_token():
                        headers = self.session_manager.get_headers()
                        continue
                    else:
                        raise Exception("Failed to refresh token")
                
                # Handle 429 - Rate limit
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', backoff))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json()
            
            except Exception as e:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    wait_time = min(backoff, MAX_BACKOFF_SECONDS)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    backoff *= BACKOFF_MULTIPLIER
                else:
                    logger.error(f"Request failed after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                    raise
        
        raise Exception("Max retry attempts reached")
    
    def place_market_order(self, symbol: str, quantity: int, side: OrderSide,
                          product: ProductType = ProductType.INTRADAY) -> Dict:
        """
        Place market order
        
        Args:
            symbol: Stock symbol (e.g., "NSE_EQ|INE467B01029")
            quantity: Order quantity
            side: BUY or SELL
            product: Product type
            
        Returns:
            Order response
        """
        if quantity > MAX_ORDER_SIZE:
            logger.info(f"Order size {quantity} exceeds max {MAX_ORDER_SIZE}, using TWAP")
            return self.place_twap_order(symbol, quantity, side, product)
        
        order_data = {
            "quantity": quantity,
            "product": product.value,
            "validity": "DAY",
            "price": 0,
            "tag": "Algorithmic Trading Bot",
            "instrument_token": symbol,
            "order_type": OrderType.MARKET.value,
            "transaction_type": side.value
        }
        
        try:
            response = self._make_request("POST", "order/place", order_data)
            order_id = response.get('data', {}).get('order_id')
            
            if order_id:
                mode_text = "SANDBOX" if self.SANDBOX_MODE else "PRODUCTION"
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'side': side.value,
                    'type': OrderType.MARKET.value,
                    'status': 'PENDING',
                    'timestamp': datetime.now(),
                    'mode': mode_text
                }
                logger.info(f"Market order placed ({mode_text}): {side.value} {quantity} {symbol}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise
    
    def place_limit_order(self, symbol: str, quantity: int, price: float, side: OrderSide,
                         product: ProductType = ProductType.INTRADAY) -> Dict:
        """
        Place limit order
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            price: Limit price
            side: BUY or SELL
            product: Product type
            
        Returns:
            Order response
        """
        if quantity > MAX_ORDER_SIZE:
            logger.info(f"Order size {quantity} exceeds max {MAX_ORDER_SIZE}, using TWAP")
            return self.place_twap_order(symbol, quantity, side, product, price)
        
        order_data = {
            "quantity": quantity,
            "product": product.value,
            "validity": "DAY",
            "price": price,
            "tag": "Algorithmic Trading Bot",
            "instrument_token": symbol,
            "order_type": OrderType.LIMIT.value,
            "transaction_type": side.value
        }
        
        try:
            response = self._make_request("POST", "order/place", order_data)
            order_id = response.get('data', {}).get('order_id')
            
            if order_id:
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'side': side.value,
                    'type': OrderType.LIMIT.value,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Limit order placed: {side.value} {quantity} {symbol} @ {price}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise
    
    def place_sl_order(self, symbol: str, quantity: int, trigger_price: float, side: OrderSide,
                      product: ProductType = ProductType.INTRADAY) -> Dict:
        """
        Place stop-loss order
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            trigger_price: Stop-loss trigger price
            side: BUY or SELL
            product: Product type
            
        Returns:
            Order response
        """
        order_data = {
            "quantity": quantity,
            "product": product.value,
            "validity": "DAY",
            "price": trigger_price,
            "trigger_price": trigger_price,
            "tag": "Algorithmic Trading Bot",
            "instrument_token": symbol,
            "order_type": OrderType.SL.value,
            "transaction_type": side.value
        }
        
        try:
            response = self._make_request("POST", "order/place", order_data)
            order_id = response.get('data', {}).get('order_id')
            
            if order_id:
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'trigger_price': trigger_price,
                    'side': side.value,
                    'type': OrderType.SL.value,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"SL order placed: {side.value} {quantity} {symbol} @ {trigger_price}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error placing SL order: {e}")
            raise
    
    def place_bracket_order(self, symbol: str, quantity: int, price: float, 
                           stop_loss: float, target: float, side: OrderSide,
                           product: ProductType = ProductType.INTRADAY) -> Dict:
        """
        Place bracket order (entry + SL + target)
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            price: Entry price
            stop_loss: Stop-loss price
            target: Target price
            side: BUY or SELL
            product: Product type
            
        Returns:
            Order response
        """
        order_data = {
            "quantity": quantity,
            "product": product.value,
            "validity": "DAY",
            "price": price,
            "tag": "Algorithmic Trading Bot",
            "instrument_token": symbol,
            "order_type": OrderType.BRACKET.value,
            "transaction_type": side.value,
            "stop_loss": stop_loss,
            "squareoff": target
        }
        
        try:
            response = self._make_request("POST", "order/place", order_data)
            order_id = response.get('data', {}).get('order_id')
            
            if order_id:
                self.orders[order_id] = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'side': side.value,
                    'type': OrderType.BRACKET.value,
                    'status': 'PENDING',
                    'timestamp': datetime.now()
                }
                logger.info(f"Bracket order placed: {side.value} {quantity} {symbol} @ {price}, SL: {stop_loss}, Target: {target}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error placing bracket order: {e}")
            raise
    
    def place_twap_order(self, symbol: str, total_quantity: int, side: OrderSide,
                        product: ProductType = ProductType.INTRADAY,
                        limit_price: Optional[float] = None) -> Dict:
        """
        Place TWAP (Time-Weighted Average Price) order
        Slices large order into smaller chunks over time
        
        Args:
            symbol: Stock symbol
            total_quantity: Total quantity to execute
            side: BUY or SELL
            product: Product type
            limit_price: Optional limit price
            
        Returns:
            TWAP order tracking dictionary
        """
        twap_id = f"TWAP_{symbol}_{int(time.time())}"
        num_slices = math.ceil(total_quantity / MAX_ORDER_SIZE)
        slice_quantity = total_quantity // num_slices
        remaining_quantity = total_quantity
        
        twap_order = {
            'twap_id': twap_id,
            'symbol': symbol,
            'total_quantity': total_quantity,
            'side': side.value,
            'num_slices': num_slices,
            'slice_quantity': slice_quantity,
            'remaining_quantity': remaining_quantity,
            'executed_quantity': 0,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(minutes=TWAP_DURATION_MINUTES),
            'orders': []
        }
        
        self.twap_orders[twap_id] = twap_order
        
        logger.info(f"TWAP order initiated: {twap_id}, {num_slices} slices over {TWAP_DURATION_MINUTES} minutes")
        
        # Execute first slice immediately
        self._execute_twap_slice(twap_id)
        
        return {'twap_id': twap_id, 'status': 'INITIATED'}
    
    def _execute_twap_slice(self, twap_id: str):
        """Execute next slice of TWAP order"""
        if twap_id not in self.twap_orders:
            return
        
        twap = self.twap_orders[twap_id]
        
        if twap['remaining_quantity'] <= 0:
            logger.info(f"TWAP order {twap_id} completed")
            return
        
        if datetime.now() >= twap['end_time']:
            logger.warning(f"TWAP order {twap_id} time expired, executing remaining quantity")
            slice_qty = twap['remaining_quantity']
        else:
            # Calculate time-based slice quantity
            elapsed_minutes = (datetime.now() - twap['start_time']).total_seconds() / 60
            target_elapsed = (twap['end_time'] - twap['start_time']).total_seconds() / 60
            
            if target_elapsed > 0:
                target_executed = (elapsed_minutes / target_elapsed) * twap['total_quantity']
                slice_qty = max(1, min(twap['slice_quantity'], 
                                     int(target_executed - twap['executed_quantity'])))
            else:
                slice_qty = twap['slice_quantity']
        
        slice_qty = min(slice_qty, twap['remaining_quantity'], MAX_ORDER_SIZE)
        
        if slice_qty <= 0:
            return
        
        try:
            side = OrderSide.BUY if twap['side'] == 'BUY' else OrderSide.SELL
            
            if twap.get('limit_price'):
                response = self.place_limit_order(
                    twap['symbol'], slice_qty, twap['limit_price'], side
                )
            else:
                response = self.place_market_order(
                    twap['symbol'], slice_qty, side
                )
            
            order_id = response.get('data', {}).get('order_id')
            if order_id:
                twap['orders'].append(order_id)
                twap['remaining_quantity'] -= slice_qty
                twap['executed_quantity'] += slice_qty
                logger.info(f"TWAP slice executed: {twap_id}, {slice_qty} shares")
        
        except Exception as e:
            logger.error(f"Error executing TWAP slice: {e}")
    
    def modify_order(self, order_id: str, quantity: Optional[int] = None,
                    price: Optional[float] = None) -> Dict:
        """
        Modify existing order
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            
        Returns:
            Modification response
        """
        order_data = {"order_id": order_id}
        if quantity:
            order_data["quantity"] = quantity
        if price:
            order_data["price"] = price
        
        try:
            response = self._make_request("PUT", "order/modify", order_data)
            logger.info(f"Order modified: {order_id}")
            return response
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        try:
            response = self._make_request("DELETE", f"order/cancel?order_id={order_id}")
            if order_id in self.orders:
                self.orders[order_id]['status'] = 'CANCELLED'
            logger.info(f"Order cancelled: {order_id}")
            return response
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise
    
    def get_order_status(self, order_id: str) -> Dict:
        """
        Get order status
        
        Args:
            order_id: Order ID
            
        Returns:
            Order status
        """
        try:
            response = self._make_request("GET", f"order/history?order_id={order_id}")
            return response
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise
    
    def get_all_orders(self) -> List[Dict]:
        """
        Get all orders
        
        Returns:
            List of all orders
        """
        try:
            response = self._make_request("GET", "order/retrieve-all")
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            raise
