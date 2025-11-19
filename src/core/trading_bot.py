"""
Main Trading Bot
Orchestrates all components: data feed, strategies, risk management, order execution
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import (
    PRIMARY_TIMEFRAME, CONFIRMATION_TIMEFRAME, CONFIRMATION_EMA_PERIOD,
    MARKET_OPEN_TIME, MARKET_CLOSE_TIME, PRE_MARKET_START
)
from src.auth.session_manager import SessionManager
from src.market_data.data_feed import MarketDataFeed
from src.orders.order_manager import OrderManager, OrderSide, ProductType
from src.portfolio.portfolio_manager import PortfolioManager
from src.logging.trade_logger import TradeLogger
from src.strategies.regime_classifier import RegimeClassifier
from src.strategies.strategy_a_trending import StrategyA_Trending
from src.strategies.strategy_b_ranging import StrategyB_Ranging
from src.risk.risk_manager import RiskManager
from src.core.external_events import ExternalEventFilter


class TradingBot:
    """
    Main Trading Bot
    Integrates all components and executes trading logic
    """
    
    def __init__(self, session_manager: SessionManager, symbols: List[str]):
        """
        Initialize Trading Bot
        
        Args:
            session_manager: Authenticated session manager
            symbols: List of symbols to trade
        """
        self.session_manager = session_manager
        self.symbols = symbols
        
        # Initialize components
        self.order_manager = OrderManager(session_manager)
        self.portfolio_manager = PortfolioManager(session_manager)
        self.trade_logger = TradeLogger()
        self.regime_classifier = RegimeClassifier()
        self.strategy_a = StrategyA_Trending()
        self.strategy_b = StrategyB_Ranging()
        self.risk_manager = RiskManager()
        self.external_event_filter = ExternalEventFilter()
        
        # Data storage
        self.candle_data: Dict[str, pd.DataFrame] = {}
        self.confirmation_data: Dict[str, pd.DataFrame] = {}
        self.open_trades: Dict[str, Dict] = {}
        
        # Market data feed
        self.data_feed: Optional[MarketDataFeed] = None
        
        # Control flags
        self.is_running = False
        self._stop_event = threading.Event()
    
    def initialize_data_feed(self):
        """Initialize market data feed"""
        self.data_feed = MarketDataFeed(
            self.session_manager,
            self.symbols,
            candle_callback=self._on_candle_complete
        )
        logger.info("Market data feed initialized")
    
    def _on_candle_complete(self, candle: Dict):
        """Callback when a candle is completed"""
        symbol = candle['symbol']
        timestamp = pd.to_datetime(candle['timestamp'])
        
        # Update candle data
        if symbol not in self.candle_data:
            self.candle_data[symbol] = pd.DataFrame()
        
        candle_df = pd.DataFrame([{
            'timestamp': timestamp,
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'volume': candle['volume']
        }])
        
        self.candle_data[symbol] = pd.concat([self.candle_data[symbol], candle_df], ignore_index=True)
        self.candle_data[symbol].set_index('timestamp', inplace=True)
        
        # Process trading logic
        self._process_trading_logic(symbol)
    
    def _process_trading_logic(self, symbol: str):
        """Process trading logic for a symbol"""
        try:
            # Check circuit breaker
            if self.portfolio_manager.check_circuit_breaker():
                logger.critical("Circuit breaker triggered! Halting trading.")
                self._square_off_all_positions()
                self.stop()
                return
            
            # Check external events
            if self.external_event_filter.should_halt_trading():
                logger.warning("External event detected! Halting trading.")
                return
            
            # Get candle data
            if symbol not in self.candle_data or len(self.candle_data[symbol]) < 200:
                return  # Need sufficient data
            
            df = self.candle_data[symbol]
            
            # Classify market regime
            regime_result = self.regime_classifier.classify_regime(df)
            regime = regime_result['regime']
            
            if regime == 'UNKNOWN':
                return  # Cannot determine regime
            
            # Get confirmation timeframe data (simplified - in production, fetch separately)
            confirmation_df = df  # In production, fetch higher timeframe data
            
            # Generate signals based on regime
            if regime == 'TRENDING':
                signal = self.strategy_a.generate_signals(df)
            else:  # RANGING
                signal = self.strategy_b.generate_signals(df)
            
            if signal['signal'] == 'HOLD':
                return  # No signal
            
            # Multi-timeframe confirmation
            mtf_confirmed, mtf_reason = self.risk_manager.check_multi_timeframe_confirmation(
                df, confirmation_df, CONFIRMATION_EMA_PERIOD
            )
            
            if not mtf_confirmed:
                logger.debug(f"MTF confirmation failed for {symbol}: {mtf_reason}")
                return
            
            # Check if we already have a position
            if symbol in self.open_trades:
                self._manage_existing_position(symbol, df, signal)
            else:
                self._evaluate_new_entry(symbol, df, signal, regime)
        
        except Exception as e:
            logger.error(f"Error processing trading logic for {symbol}: {e}")
    
    def _evaluate_new_entry(self, symbol: str, df: pd.DataFrame, signal: Dict, regime: str):
        """Evaluate and execute new entry"""
        try:
            side = signal['side']
            entry_price = df['close'].iloc[-1]
            
            # Calculate stop-loss
            stop_loss = self.risk_manager.calculate_stop_loss(df, entry_price, side)
            
            # Calculate position size
            current_capital = self.portfolio_manager.initial_capital + self.portfolio_manager.calculate_daily_pnl()
            position_size, risk_amount = self.risk_manager.calculate_position_size(
                entry_price, stop_loss, current_capital
            )
            
            # Calculate target
            target = self.risk_manager.calculate_target(df, entry_price, stop_loss, side)
            
            # Place order
            order_side = OrderSide.BUY if side == 'BUY' else OrderSide.SELL
            
            # Use bracket order for automatic SL and target
            response = self.order_manager.place_bracket_order(
                symbol=symbol,
                quantity=position_size,
                price=entry_price,
                stop_loss=stop_loss,
                target=target,
                side=order_side
            )
            
            order_id = response.get('data', {}).get('order_id')
            
            if order_id:
                # Log trade entry
                trade_id = self.trade_logger.log_entry(
                    symbol=symbol,
                    side=side,
                    quantity=position_size,
                    price=entry_price,
                    order_type='BRACKET',
                    reason=signal.get('reason', ''),
                    stop_loss=stop_loss,
                    target=target,
                    strategy='Strategy A' if regime == 'TRENDING' else 'Strategy B',
                    regime=regime
                )
                
                # Track open trade
                self.open_trades[symbol] = {
                    'trade_id': trade_id,
                    'symbol': symbol,
                    'side': side,
                    'quantity': position_size,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target': target,
                    'highest_price': entry_price if side == 'BUY' else entry_price,
                    'lowest_price': entry_price if side == 'SELL' else entry_price,
                    'regime': regime,
                    'entry_time': datetime.now()
                }
                
                logger.info(
                    f"Entry executed: {symbol} | {side} {position_size} @ {entry_price:.2f} | "
                    f"SL: {stop_loss:.2f} | Target: {target:.2f} | Regime: {regime}"
                )
        
        except Exception as e:
            logger.error(f"Error evaluating new entry for {symbol}: {e}")
    
    def _manage_existing_position(self, symbol: str, df: pd.DataFrame, signal: Dict):
        """Manage existing position (trailing stop, exit conditions)"""
        try:
            trade = self.open_trades[symbol]
            current_price = df['close'].iloc[-1]
            side = trade['side']
            
            # Update highest/lowest price
            if side == 'BUY':
                trade['highest_price'] = max(trade['highest_price'], current_price)
            else:
                trade['lowest_price'] = min(trade['lowest_price'], current_price)
            
            # Calculate trailing stop
            highest_for_tsl = trade['highest_price'] if side == 'BUY' else trade['lowest_price']
            trailing_stop = self.risk_manager.calculate_trailing_stop(
                df, trade['entry_price'], highest_for_tsl, side
            )
            
            # Check exit conditions
            should_exit = False
            exit_reason = ""
            
            # Check stop-loss
            if side == 'BUY' and current_price <= trailing_stop:
                should_exit = True
                exit_reason = "Trailing stop-loss hit"
            elif side == 'SELL' and current_price >= trailing_stop:
                should_exit = True
                exit_reason = "Trailing stop-loss hit"
            
            # Check target
            if side == 'BUY' and current_price >= trade['target']:
                should_exit = True
                exit_reason = "Target reached"
            elif side == 'SELL' and current_price <= trade['target']:
                should_exit = True
                exit_reason = "Target reached"
            
            # Check opposite signal
            if signal['signal'] != 'HOLD' and signal['side'] != side:
                should_exit = True
                exit_reason = f"Opposite signal: {signal['side']}"
            
            if should_exit:
                self._exit_position(symbol, current_price, exit_reason)
        
        except Exception as e:
            logger.error(f"Error managing position for {symbol}: {e}")
    
    def _exit_position(self, symbol: str, exit_price: float, reason: str):
        """Exit a position"""
        try:
            trade = self.open_trades[symbol]
            trade_id = trade['trade_id']
            
            # Place market order to exit
            order_side = OrderSide.SELL if trade['side'] == 'BUY' else OrderSide.BUY
            
            response = self.order_manager.place_market_order(
                symbol=symbol,
                quantity=trade['quantity'],
                side=order_side
            )
            
            # Calculate P&L
            if trade['side'] == 'BUY':
                pnl = (exit_price - trade['entry_price']) * trade['quantity']
            else:
                pnl = (trade['entry_price'] - exit_price) * trade['quantity']
            
            # Log exit
            self.trade_logger.log_exit(trade_id, exit_price, reason, pnl)
            
            # Update portfolio
            self.portfolio_manager.update_position(
                symbol, trade['quantity'], exit_price, trade['side']
            )
            
            # Remove from open trades
            del self.open_trades[symbol]
            
            logger.info(
                f"Position exited: {symbol} | Exit @ {exit_price:.2f} | "
                f"P&L: ₹{pnl:.2f} | Reason: {reason}"
            )
        
        except Exception as e:
            logger.error(f"Error exiting position for {symbol}: {e}")
    
    def _square_off_all_positions(self):
        """Square off all open positions (circuit breaker)"""
        logger.critical("Squaring off all positions due to circuit breaker")
        
        for symbol in list(self.open_trades.keys()):
            try:
                trade = self.open_trades[symbol]
                # Get current price from data feed
                current_price = self.candle_data.get(symbol, pd.DataFrame()).iloc[-1]['close'] if symbol in self.candle_data else trade['entry_price']
                self._exit_position(symbol, current_price, "Circuit breaker - forced exit")
            except Exception as e:
                logger.error(f"Error squaring off position {symbol}: {e}")
    
    def start(self):
        """Start the trading bot"""
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        logger.info("Starting trading bot...")
        
        # Check if market is open
        if not self._is_market_open():
            logger.warning("Market is not open. Bot will start when market opens.")
        
        # Initialize data feed
        self.initialize_data_feed()
        
        # Connect to data feed
        self.data_feed.connect()
        
        # Reset daily stats
        self.portfolio_manager.reset_daily_stats()
        
        self.is_running = True
        self._stop_event.clear()
        
        # Start main loop
        self._main_loop()
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.is_running = False
        self._stop_event.set()
        
        if self.data_feed:
            self.data_feed.disconnect()
        
        logger.info("Trading bot stopped")
    
    def _main_loop(self):
        """Main trading loop"""
        while self.is_running and not self._stop_event.is_set():
            try:
                # Check market hours
                if not self._is_market_open():
                    time.sleep(60)  # Wait 1 minute
                    continue
                
                # Update positions
                self.portfolio_manager.fetch_positions()
                
                # Sleep for a short interval
                time.sleep(5)  # Check every 5 seconds
            
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(10)
    
    def _is_market_open(self) -> bool:
        """Check if market is open"""
        now = datetime.now()
        current_time = now.time()
        
        market_open = datetime.strptime(MARKET_OPEN_TIME, "%H:%M").time()
        market_close = datetime.strptime(MARKET_CLOSE_TIME, "%H:%M").time()
        
        return market_open <= current_time <= market_close
