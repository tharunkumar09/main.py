"""
Live Market Data Feed with WebSocket subscription and 1-minute candle construction
"""
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pandas as pd
import websocket
from threading import Thread, Lock
import requests
from trading_bot.core.auth import UpstoxAuth
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class MarketDataFeed:
    """Live market data feed with WebSocket and candle construction"""
    
    def __init__(self, auth: UpstoxAuth):
        self.auth = auth
        self.ws_url = settings.WS_BASE_URL
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[Thread] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Candle storage
        self.candles: Dict[str, pd.DataFrame] = {}  # symbol -> DataFrame
        self.ticks: Dict[str, List[Dict]] = {}  # symbol -> list of ticks
        self.candle_lock = Lock()
        
        # Subscribed instruments
        self.subscribed_instruments: List[str] = []
        
        # Callbacks
        self.on_candle_update: Optional[Callable] = None
        self.on_tick_update: Optional[Callable] = None
    
    def _get_exponential_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = min(
            settings.RETRY_DELAY * (2 ** attempt),
            settings.MAX_RETRY_DELAY
        )
        return delay
    
    def _connect_websocket(self):
        """Connect to Upstox WebSocket feed"""
        try:
            token = self.auth.get_valid_token()
            if not token:
                raise ValueError("No valid access token")
            
            ws_url = f"{self.ws_url}?token={token}"
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            self.ws_thread = Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            self._schedule_reconnect()
    
    def _on_open(self, ws):
        """WebSocket connection opened"""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        self.reconnect_attempts = 0
        
        # Subscribe to instruments
        if self.subscribed_instruments:
            self.subscribe(self.subscribed_instruments)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            if 'action' in data:
                if data['action'] == 'subscribed':
                    logger.info(f"Subscribed to: {data.get('symbols', [])}")
                elif data['action'] == 'error':
                    logger.error(f"WebSocket error: {data.get('message', 'Unknown error')}")
            
            # Handle tick data
            elif 'data' in data:
                self._process_tick_data(data['data'])
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket error handler"""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        logger.warning("WebSocket connection closed")
        self.is_connected = False
        self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        delay = self._get_exponential_backoff_delay(self.reconnect_attempts)
        self.reconnect_attempts += 1
        
        logger.info(f"Scheduling reconnection in {delay:.2f} seconds (attempt {self.reconnect_attempts})")
        time.sleep(delay)
        self._connect_websocket()
    
    def _process_tick_data(self, tick_data: Dict):
        """Process incoming tick data and construct candles"""
        try:
            symbol = tick_data.get('symbol')
            if not symbol:
                return
            
            # Extract tick information
            tick = {
                'timestamp': datetime.now(),
                'ltp': tick_data.get('ltp', 0),
                'volume': tick_data.get('volume', 0),
                'bid': tick_data.get('bid', 0),
                'ask': tick_data.get('ask', 0)
            }
            
            # Store tick
            if symbol not in self.ticks:
                self.ticks[symbol] = []
            self.ticks[symbol].append(tick)
            
            # Call tick callback
            if self.on_tick_update:
                self.on_tick_update(symbol, tick)
            
            # Construct 1-minute candles
            self._update_candles(symbol, tick)
            
        except Exception as e:
            logger.error(f"Error processing tick data: {e}")
    
    def _update_candles(self, symbol: str, tick: Dict):
        """Update 1-minute candles from tick data"""
        with self.candle_lock:
            current_time = tick['timestamp']
            minute_start = current_time.replace(second=0, microsecond=0)
            
            if symbol not in self.candles:
                self.candles[symbol] = pd.DataFrame(columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume'
                ])
            
            df = self.candles[symbol]
            
            # Check if we need a new candle
            if df.empty or df.iloc[-1]['timestamp'] < minute_start:
                # Create new candle
                new_candle = {
                    'timestamp': minute_start,
                    'open': tick['ltp'],
                    'high': tick['ltp'],
                    'low': tick['ltp'],
                    'close': tick['ltp'],
                    'volume': tick['volume']
                }
                df = pd.concat([df, pd.DataFrame([new_candle])], ignore_index=True)
            else:
                # Update current candle
                idx = len(df) - 1
                df.at[idx, 'high'] = max(df.at[idx, 'high'], tick['ltp'])
                df.at[idx, 'low'] = min(df.at[idx, 'low'], tick['ltp'])
                df.at[idx, 'close'] = tick['ltp']
                df.at[idx, 'volume'] += tick['volume']
            
            self.candles[symbol] = df
            
            # Call candle update callback
            if self.on_candle_update:
                latest_candle = df.iloc[-1].to_dict()
                self.on_candle_update(symbol, latest_candle)
    
    def subscribe(self, instruments: List[str]):
        """Subscribe to market data for given instruments"""
        self.subscribed_instruments = instruments
        
        if not self.is_connected:
            logger.warning("WebSocket not connected, will subscribe after connection")
            return
        
        try:
            subscribe_msg = {
                "action": "subscribe",
                "symbols": instruments
            }
            self.ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to instruments: {instruments}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
    
    def unsubscribe(self, instruments: List[str]):
        """Unsubscribe from market data"""
        if not self.is_connected:
            return
        
        try:
            unsubscribe_msg = {
                "action": "unsubscribe",
                "symbols": instruments
            }
            self.ws.send(json.dumps(unsubscribe_msg))
            logger.info(f"Unsubscribed from instruments: {instruments}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
    
    def get_latest_candle(self, symbol: str) -> Optional[pd.Series]:
        """Get the latest 1-minute candle for a symbol"""
        with self.candle_lock:
            if symbol in self.candles and not self.candles[symbol].empty:
                return self.candles[symbol].iloc[-1]
        return None
    
    def get_candles(self, symbol: str, count: int = 100) -> pd.DataFrame:
        """Get last N candles for a symbol"""
        with self.candle_lock:
            if symbol in self.candles:
                df = self.candles[symbol]
                return df.tail(count).copy()
        return pd.DataFrame()
    
    def get_historical_data(
        self,
        symbol: str,
        interval: str = "1minute",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fetch historical data from Upstox API"""
        try:
            headers = self.auth.get_headers()
            
            # Convert symbol to instrument key format (NSE_EQ:INE467B01029)
            # This is a simplified version - actual implementation needs instrument key mapping
            instrument_key = symbol  # Should be mapped to actual instrument key
            
            url = f"{settings.API_BASE_URL}/market-quote/historical-candle/{instrument_key}/{interval}"
            
            params = {}
            if from_date:
                params['from'] = from_date.strftime('%Y-%m-%d')
            if to_date:
                params['to'] = to_date.strftime('%Y-%m-%d')
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            candles = data.get('data', {}).get('candles', [])
            
            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return pd.DataFrame()
    
    def start(self):
        """Start the market data feed"""
        self._connect_websocket()
    
    def stop(self):
        """Stop the market data feed"""
        if self.ws:
            self.ws.close()
        self.is_connected = False
