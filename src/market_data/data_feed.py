"""
Live Market Data Feed with WebSocket subscription and 1-minute candle construction
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import defaultdict
import websocket
from loguru import logger
import pandas as pd
import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import WS_RECONNECT_DELAY, WS_HEARTBEAT_INTERVAL, INITIAL_BACKOFF_SECONDS, MAX_BACKOFF_SECONDS, BACKOFF_MULTIPLIER, MAX_RETRY_ATTEMPTS
from src.auth.session_manager import SessionManager


class CandleBuilder:
    """
    Builds OHLCV candles from tick data
    """
    
    def __init__(self, timeframe_minutes: int = 1):
        """
        Initialize Candle Builder
        
        Args:
            timeframe_minutes: Candle timeframe in minutes
        """
        self.timeframe_minutes = timeframe_minutes
        self.candles: Dict[str, List[Dict]] = defaultdict(list)
        self.current_candles: Dict[str, Dict] = {}
    
    def process_tick(self, symbol: str, price: float, volume: int, timestamp: datetime) -> Optional[Dict]:
        """
        Process a tick and update current candle
        
        Args:
            symbol: Stock symbol
            price: Last traded price
            volume: Volume traded
            timestamp: Tick timestamp
            
        Returns:
            Completed candle if timeframe elapsed, None otherwise
        """
        # Round timestamp to timeframe boundary
        candle_time = self._round_to_timeframe(timestamp)
        
        candle_key = f"{symbol}_{candle_time.isoformat()}"
        
        if candle_key not in self.current_candles:
            # Start new candle
            self.current_candles[candle_key] = {
                'symbol': symbol,
                'timestamp': candle_time,
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume
            }
        else:
            # Update existing candle
            candle = self.current_candles[candle_key]
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price
            candle['volume'] += volume
        
        # Check if candle is complete
        next_candle_time = candle_time + timedelta(minutes=self.timeframe_minutes)
        if timestamp >= next_candle_time:
            completed_candle = self.current_candles.pop(candle_key)
            self.candles[symbol].append(completed_candle)
            return completed_candle
        
        return None
    
    def _round_to_timeframe(self, timestamp: datetime) -> datetime:
        """Round timestamp to timeframe boundary"""
        minutes = timestamp.minute
        rounded_minutes = (minutes // self.timeframe_minutes) * self.timeframe_minutes
        return timestamp.replace(minute=rounded_minutes, second=0, microsecond=0)
    
    def get_latest_candle(self, symbol: str) -> Optional[Dict]:
        """Get the latest completed candle for a symbol"""
        if symbol in self.candles and len(self.candles[symbol]) > 0:
            return self.candles[symbol][-1]
        return None
    
    def get_candles_df(self, symbol: str, limit: int = None) -> pd.DataFrame:
        """
        Get candles as DataFrame
        
        Args:
            symbol: Stock symbol
            limit: Maximum number of candles to return
            
        Returns:
            DataFrame with OHLCV data
        """
        if symbol not in self.candles:
            return pd.DataFrame()
        
        candles = self.candles[symbol]
        if limit:
            candles = candles[-limit:]
        
        df = pd.DataFrame(candles)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        return df


class MarketDataFeed:
    """
    Live market data feed using Upstox WebSocket API
    Implements reconnection logic with exponential backoff
    """
    
    WS_BASE_URL = "wss://api.upstox.com/v2/feed/market-data-feed"
    
    def __init__(self, session_manager: SessionManager, symbols: List[str], 
                 candle_callback: Optional[Callable] = None):
        """
        Initialize Market Data Feed
        
        Args:
            session_manager: Authenticated session manager
            symbols: List of symbols to subscribe to
            candle_callback: Callback function for completed candles
        """
        self.session_manager = session_manager
        self.symbols = symbols
        self.candle_callback = candle_callback
        
        self.ws: Optional[websocket.WebSocketApp] = None
        self.candle_builder = CandleBuilder(timeframe_minutes=1)
        self.is_connected = False
        self.reconnect_attempts = 0
        self.backoff_seconds = INITIAL_BACKOFF_SECONDS
        
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
    
    def _get_ws_url(self) -> str:
        """Get WebSocket URL with access token"""
        access_token = self.session_manager.access_token
        return f"{self.WS_BASE_URL}?authorization={access_token}"
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if 'type' in data:
                if data['type'] == 'error':
                    logger.error(f"WebSocket error: {data}")
                elif data['type'] == 'success':
                    logger.info(f"WebSocket success: {data}")
                elif data['type'] == 'message':
                    self._process_market_data(data['data'])
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    def _process_market_data(self, data: Dict):
        """Process market data tick"""
        try:
            symbol = data.get('symbol')
            ltp = data.get('ltp')  # Last traded price
            volume = data.get('volume', 0)
            timestamp = datetime.now()  # Use current time as tick timestamp
            
            if symbol and ltp:
                # Process tick through candle builder
                completed_candle = self.candle_builder.process_tick(
                    symbol, float(ltp), int(volume), timestamp
                )
                
                # Call callback if candle completed
                if completed_candle and self.candle_callback:
                    self.candle_callback(completed_candle)
        
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        
        # Attempt reconnection if not stopped
        if not self._stop_event.is_set():
            self._reconnect()
    
    def _on_open(self, ws):
        """Handle WebSocket open"""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.reconnect_attempts = 0
        self.backoff_seconds = INITIAL_BACKOFF_SECONDS
        
        # Subscribe to symbols
        self._subscribe_symbols()
    
    def _subscribe_symbols(self):
        """Subscribe to market data for symbols"""
        try:
            # Upstox WebSocket subscription format
            subscription_message = {
                "action": "subscribe",
                "symbols": self.symbols
            }
            
            if self.ws:
                self.ws.send(json.dumps(subscription_message))
                logger.info(f"Subscribed to symbols: {self.symbols}")
        
        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
    
    def _reconnect(self):
        """Reconnect with exponential backoff"""
        if self._stop_event.is_set():
            return
        
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > MAX_RETRY_ATTEMPTS:
            logger.error("Max reconnection attempts reached")
            return
        
        wait_time = min(self.backoff_seconds, MAX_BACKOFF_SECONDS)
        logger.info(f"Reconnecting in {wait_time} seconds (attempt {self.reconnect_attempts})")
        
        time.sleep(wait_time)
        self.backoff_seconds *= BACKOFF_MULTIPLIER
        
        # Refresh token if needed
        if not self.session_manager.is_token_valid():
            self.session_manager.refresh_access_token()
        
        self.connect()
    
    def connect(self):
        """Connect to WebSocket"""
        try:
            ws_url = self._get_ws_url()
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # Run in separate thread
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            self._reconnect()
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        self.is_connected = False
        logger.info("WebSocket disconnected")
    
    def get_latest_candle(self, symbol: str) -> Optional[Dict]:
        """Get latest completed candle for symbol"""
        return self.candle_builder.get_latest_candle(symbol)
    
    def get_candles_df(self, symbol: str, limit: int = None) -> pd.DataFrame:
        """Get candles DataFrame for symbol"""
        return self.candle_builder.get_candles_df(symbol, limit)
