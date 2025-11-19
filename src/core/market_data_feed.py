"""
Market Data Feed Module
WebSocket-based live market data with 1-minute candle construction
"""

import json
import time
import threading
from typing import Dict, List, Callable, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import websocket
import pandas as pd
from loguru import logger
import upstox_client


class CandleBuilder:
    """Build OHLCV candles from tick data"""
    
    def __init__(self, symbol: str, timeframe: str = "1min"):
        """
        Initialize candle builder
        
        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (e.g., '1min', '5min', '15min')
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_seconds = self._parse_timeframe(timeframe)
        
        # Current candle data
        self.current_candle = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0,
            'timestamp': None
        }
        
        # Completed candles buffer
        self.candles = deque(maxlen=1000)
        self.candle_start_time = None
        
    def _parse_timeframe(self, timeframe: str) -> int:
        """Parse timeframe string to seconds"""
        unit = timeframe[-3:]
        value = int(timeframe[:-3])
        
        if unit == 'min':
            return value * 60
        elif unit == 'hour':
            return value * 3600
        else:
            return 60  # default 1 minute
    
    def add_tick(self, price: float, volume: int, timestamp: datetime):
        """
        Add tick data to build candle
        
        Args:
            price: Tick price
            volume: Tick volume
            timestamp: Tick timestamp
        """
        # Initialize candle if first tick or new candle period
        if self.candle_start_time is None:
            self.candle_start_time = self._get_candle_start_time(timestamp)
            self.current_candle['open'] = price
            self.current_candle['high'] = price
            self.current_candle['low'] = price
            self.current_candle['close'] = price
            self.current_candle['volume'] = volume
            self.current_candle['timestamp'] = self.candle_start_time
            return
        
        # Check if we need to close current candle and start new one
        if timestamp >= self.candle_start_time + timedelta(seconds=self.timeframe_seconds):
            self._close_candle()
            self.candle_start_time = self._get_candle_start_time(timestamp)
            self.current_candle = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'timestamp': self.candle_start_time
            }
            return
        
        # Update current candle
        self.current_candle['high'] = max(self.current_candle['high'], price)
        self.current_candle['low'] = min(self.current_candle['low'], price)
        self.current_candle['close'] = price
        self.current_candle['volume'] += volume
    
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """Get candle start time aligned to timeframe"""
        total_seconds = int(timestamp.timestamp())
        aligned_seconds = (total_seconds // self.timeframe_seconds) * self.timeframe_seconds
        return datetime.fromtimestamp(aligned_seconds)
    
    def _close_candle(self):
        """Close current candle and add to buffer"""
        if self.current_candle['open'] is not None:
            self.candles.append(self.current_candle.copy())
            logger.debug(f"Candle closed for {self.symbol}: {self.current_candle}")
    
    def get_candles_df(self, n: int = 100) -> pd.DataFrame:
        """
        Get last n candles as DataFrame
        
        Args:
            n: Number of candles to return
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.candles:
            return pd.DataFrame()
        
        candles_list = list(self.candles)[-n:]
        df = pd.DataFrame(candles_list)
        df.set_index('timestamp', inplace=True)
        return df


class MarketDataFeed:
    """
    WebSocket-based market data feed with:
    - Automatic reconnection with exponential backoff
    - Multi-symbol subscription
    - Real-time candle construction
    - Callback-based data delivery
    """
    
    def __init__(
        self,
        access_token: str,
        symbols: List[str],
        on_tick_callback: Optional[Callable] = None,
        on_candle_callback: Optional[Callable] = None,
        reconnect_delay: int = 5,
        max_reconnect_attempts: int = 10
    ):
        """
        Initialize market data feed
        
        Args:
            access_token: Upstox access token
            symbols: List of symbols to subscribe
            on_tick_callback: Callback for tick data
            on_candle_callback: Callback for completed candles
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_attempts: Maximum reconnection attempts
        """
        self.access_token = access_token
        self.symbols = symbols
        self.on_tick_callback = on_tick_callback
        self.on_candle_callback = on_candle_callback
        
        # Reconnection settings
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_count = 0
        
        # WebSocket
        self.ws = None
        self.ws_thread = None
        self.is_connected = False
        self.should_run = True
        
        # Candle builders for each symbol
        self.candle_builders: Dict[str, CandleBuilder] = {
            symbol: CandleBuilder(symbol) for symbol in symbols
        }
        
        # Market data buffer
        self.tick_buffer: Dict[str, List] = defaultdict(list)
        
        # Heartbeat
        self.last_heartbeat = datetime.now()
        self.heartbeat_timeout = 60  # seconds
    
    def start(self):
        """Start market data feed"""
        logger.info("Starting market data feed...")
        self.should_run = True
        self.ws_thread = threading.Thread(target=self._connect_and_run, daemon=True)
        self.ws_thread.start()
        logger.info("Market data feed started")
    
    def stop(self):
        """Stop market data feed"""
        logger.info("Stopping market data feed...")
        self.should_run = False
        if self.ws:
            self.ws.close()
        if self.ws_thread:
            self.ws_thread.join(timeout=5)
        logger.info("Market data feed stopped")
    
    def _connect_and_run(self):
        """Connect to WebSocket with retry logic"""
        while self.should_run and self.reconnect_count < self.max_reconnect_attempts:
            try:
                self._connect()
                self.reconnect_count = 0  # Reset on successful connection
            except Exception as e:
                self.reconnect_count += 1
                logger.error(f"WebSocket error (attempt {self.reconnect_count}): {e}")
                
                if self.reconnect_count < self.max_reconnect_attempts:
                    # Exponential backoff
                    delay = self.reconnect_delay * (2 ** (self.reconnect_count - 1))
                    delay = min(delay, 300)  # Max 5 minutes
                    logger.info(f"Reconnecting in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error("Max reconnection attempts reached")
                    break
    
    def _connect(self):
        """Establish WebSocket connection"""
        # Get WebSocket URL from Upstox API
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_client = upstox_client.ApiClient(configuration)
        api_instance = upstox_client.WebSocketApi(api_client)
        
        try:
            # Get authorized WebSocket URL
            api_response = api_instance.get_market_data_feed_authorize(api_version='2.0')
            ws_url = api_response.data.authorized_redirect_uri
            
            logger.info(f"Connecting to WebSocket: {ws_url}")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run WebSocket
            self.ws.run_forever(ping_interval=30, ping_timeout=10)
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            raise
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.last_heartbeat = datetime.now()
        
        # Subscribe to symbols
        self._subscribe_symbols()
    
    def _subscribe_symbols(self):
        """Subscribe to market data for symbols"""
        try:
            # Upstox subscription message format
            subscription_message = {
                "guid": "someguid",
                "method": "sub",
                "data": {
                    "mode": "full",
                    "instrumentKeys": self.symbols
                }
            }
            
            self.ws.send(json.dumps(subscription_message))
            logger.info(f"Subscribed to {len(self.symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to symbols: {e}")
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            self.last_heartbeat = datetime.now()
            
            # Parse message
            data = json.loads(message) if isinstance(message, str) else message
            
            # Handle different message types
            if 'type' in data:
                if data['type'] == 'ping':
                    # Respond to ping
                    pong_message = {"type": "pong"}
                    ws.send(json.dumps(pong_message))
                    return
                elif data['type'] == 'error':
                    logger.error(f"WebSocket error: {data}")
                    return
            
            # Process market data
            if 'feeds' in data:
                for symbol, tick_data in data['feeds'].items():
                    self._process_tick(symbol, tick_data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _process_tick(self, symbol: str, tick_data: Dict):
        """
        Process tick data and build candles
        
        Args:
            symbol: Trading symbol
            tick_data: Tick data dictionary
        """
        try:
            # Extract tick information
            ltp = tick_data.get('ltpc', {}).get('ltp', 0)
            volume = tick_data.get('ltpc', {}).get('volume', 0)
            timestamp = datetime.now()
            
            # Call tick callback
            if self.on_tick_callback:
                self.on_tick_callback(symbol, ltp, volume, timestamp)
            
            # Add to candle builder
            if symbol in self.candle_builders:
                old_candle_count = len(self.candle_builders[symbol].candles)
                self.candle_builders[symbol].add_tick(ltp, volume, timestamp)
                new_candle_count = len(self.candle_builders[symbol].candles)
                
                # Check if new candle was completed
                if new_candle_count > old_candle_count and self.on_candle_callback:
                    candle = self.candle_builders[symbol].candles[-1]
                    self.on_candle_callback(symbol, candle)
            
        except Exception as e:
            logger.error(f"Error processing tick for {symbol}: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False
    
    def get_candles(self, symbol: str, n: int = 100) -> pd.DataFrame:
        """
        Get candles for symbol
        
        Args:
            symbol: Trading symbol
            n: Number of candles
            
        Returns:
            DataFrame with candles
        """
        if symbol in self.candle_builders:
            return self.candle_builders[symbol].get_candles_df(n)
        return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price or None
        """
        if symbol in self.candle_builders:
            candle = self.candle_builders[symbol].current_candle
            return candle.get('close')
        return None
    
    def health_check(self) -> bool:
        """Check if feed is healthy"""
        if not self.is_connected:
            return False
        
        # Check heartbeat
        if datetime.now() - self.last_heartbeat > timedelta(seconds=self.heartbeat_timeout):
            logger.warning("Heartbeat timeout")
            return False
        
        return True
    
    def __repr__(self) -> str:
        return f"MarketDataFeed(symbols={len(self.symbols)}, connected={self.is_connected})"
