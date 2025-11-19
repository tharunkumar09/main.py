"""
Main Trading Bot
Orchestrates all components for automated trading
"""

import time
import schedule
from typing import Dict, Optional
from datetime import datetime, time as dt_time
from loguru import logger
import pytz

from src.core.config_loader import get_config
from src.core.upstox_client import UpstoxClient
from src.core.market_data_feed import MarketDataFeed
from src.core.order_manager import OrderManager, TransactionType
from src.core.portfolio_manager import PortfolioManager
from src.strategies.regime_classifier import RegimeClassifier, MarketRegime
from src.strategies.trending_strategy import TrendingStrategy, Signal
from src.strategies.ranging_strategy import RangingStrategy
from src.strategies.multi_timeframe import MultiTimeframeAnalyzer
from src.strategies.indicators import TechnicalIndicators
from src.risk.risk_manager import RiskManager
from src.risk.circuit_breaker import CircuitBreaker, CircuitBreakerTrigger


class AlgoTradingBot:
    """
    Advanced Algorithmic Trading Bot
    
    Features:
    - Multi-regime strategy switching
    - Multi-timeframe confirmation
    - ATR-based risk management
    - Circuit breaker protection
    - Real-time position tracking
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize trading bot
        
        Args:
            config_path: Path to configuration file
        """
        logger.info("="*60)
        logger.info("Initializing Algorithmic Trading Bot")
        logger.info("="*60)
        
        # Load configuration
        self.config = get_config(config_path)
        self.config.validate()
        
        # Initialize API client
        self.api_client = UpstoxClient(
            api_key=self.config.upstox.UPSTOX_API_KEY,
            api_secret=self.config.upstox.UPSTOX_API_SECRET,
            redirect_uri=self.config.upstox.UPSTOX_REDIRECT_URI,
            access_token=self.config.upstox.UPSTOX_ACCESS_TOKEN
        )
        
        # Initialize components
        capital = self.config.trading.capital
        self.portfolio_manager = PortfolioManager(self.api_client, self.config, capital)
        self.order_manager = OrderManager(self.api_client, self.config)
        self.risk_manager = RiskManager(self.config, capital)
        self.circuit_breaker = CircuitBreaker(self.config)
        
        # Initialize strategies
        self.regime_classifier = RegimeClassifier(self.config)
        self.trending_strategy = TrendingStrategy(self.config)
        self.ranging_strategy = RangingStrategy(self.config)
        self.mtf_analyzer = MultiTimeframeAnalyzer(self.config)
        
        # Market data feed
        self.market_feed: Optional[MarketDataFeed] = None
        self.watchlist = self.config.watchlist
        
        # State
        self.is_running = False
        self.is_trading_hours = False
        self.timezone = pytz.timezone(self.config.market['timezone'])
        
        # Symbol data cache
        self.symbol_data: Dict[str, Dict] = {
            symbol: {'candles': [], 'last_signal': None}
            for symbol in self.watchlist
        }
        
        logger.info(f"Bot initialized: mode={self.config.trading.trading_mode}, "
                   f"capital={capital}, watchlist={len(self.watchlist)} symbols")
    
    def start(self):
        """Start the trading bot"""
        logger.info("🚀 Starting Trading Bot")
        
        # Health check
        if not self.api_client.health_check():
            logger.error("API health check failed - cannot start")
            return
        
        # Start market data feed
        self._start_market_feed()
        
        # Schedule tasks
        self._schedule_tasks()
        
        self.is_running = True
        logger.info("✅ Trading Bot started successfully")
        
        # Main loop
        self._run()
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("🛑 Stopping Trading Bot")
        
        self.is_running = False
        
        # Stop market feed
        if self.market_feed:
            self.market_feed.stop()
        
        # Square off positions if configured
        if self.config.trading.trading_mode == "live":
            logger.warning("Squaring off all positions before shutdown")
            self.portfolio_manager.square_off_all_positions(reason="Bot shutdown")
        
        logger.info("✅ Trading Bot stopped")
    
    def _start_market_feed(self):
        """Start market data feed"""
        logger.info("Starting market data feed...")
        
        # Convert watchlist symbols to Upstox format (NSE_EQ|...)
        # Note: In production, you'd need proper instrument token mapping
        symbols = [f"NSE_EQ|INE{i:06d}" for i in range(len(self.watchlist))]
        
        self.market_feed = MarketDataFeed(
            access_token=self.config.upstox.UPSTOX_ACCESS_TOKEN,
            symbols=symbols,
            on_tick_callback=self._on_tick,
            on_candle_callback=self._on_candle_complete,
            reconnect_delay=self.config.websocket['reconnect_delay'],
            max_reconnect_attempts=self.config.websocket['max_reconnect_attempts']
        )
        
        self.market_feed.start()
        logger.info("Market data feed started")
    
    def _schedule_tasks(self):
        """Schedule periodic tasks"""
        # Market open/close times
        market_open = self.config.market['open_time']
        market_close = self.config.market['close_time']
        
        # Schedule market hours
        schedule.every().day.at(market_open).do(self._on_market_open)
        schedule.every().day.at(market_close).do(self._on_market_close)
        
        # Periodic tasks during trading hours
        schedule.every(1).minutes.do(self._periodic_check)
        schedule.every(5).minutes.do(self._sync_portfolio)
        
        logger.info(f"Tasks scheduled: market hours {market_open} - {market_close}")
    
    def _run(self):
        """Main event loop"""
        logger.info("Entering main event loop")
        
        while self.is_running:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Process TWAP executions
                self.order_manager.process_twap_executions()
                
                # Check circuit breaker auto-reset
                self.circuit_breaker.check_auto_reset()
                
                # Sleep
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                self.circuit_breaker.increment_api_error()
                time.sleep(5)
    
    def _on_market_open(self):
        """Market open handler"""
        logger.info("📈 Market OPEN")
        self.is_trading_hours = True
        self.portfolio_manager.reset_daily_tracking()
        self.circuit_breaker.reset()
    
    def _on_market_close(self):
        """Market close handler"""
        logger.info("📉 Market CLOSE")
        self.is_trading_hours = False
        
        # Square off all positions (if configured for intraday)
        if self.config.trading.trading_mode == "live":
            self.portfolio_manager.square_off_all_positions(reason="Market close")
        
        # Log daily summary
        summary = self.portfolio_manager.get_portfolio_summary()
        logger.info(f"📊 Daily Summary: P&L={summary['daily_pnl']:.2f} ({summary['daily_pnl_percent']:.2f}%), "
                   f"Trades={summary['total_trades']}, Win Rate={summary['win_rate']:.1f}%")
    
    def _periodic_check(self):
        """Periodic health and risk checks"""
        if not self.is_trading_hours:
            return
        
        # Check circuit breaker conditions
        daily_pnl_percent = self.portfolio_manager.get_daily_pnl_percent()
        
        if self.circuit_breaker.check_daily_loss(daily_pnl_percent):
            self._trigger_circuit_breaker(CircuitBreakerTrigger.DAILY_LOSS_LIMIT, 
                                         f"Daily loss: {daily_pnl_percent:.2f}%")
        
        if self.circuit_breaker.check_rapid_drawdown(daily_pnl_percent):
            self._trigger_circuit_breaker(CircuitBreakerTrigger.RAPID_DRAWDOWN, 
                                         "Rapid drawdown detected")
        
        # Check external events
        should_halt, event_name = self.circuit_breaker.check_external_events()
        if should_halt:
            self._trigger_circuit_breaker(CircuitBreakerTrigger.EXTERNAL_EVENT, 
                                         f"Event: {event_name}")
        
        # Check stops and targets
        symbols_to_close = self.portfolio_manager.check_stops_and_targets()
        for symbol, reason in symbols_to_close:
            self._close_position(symbol, reason)
    
    def _sync_portfolio(self):
        """Sync portfolio with broker"""
        try:
            self.portfolio_manager.sync_with_broker()
        except Exception as e:
            logger.error(f"Failed to sync portfolio: {e}")
    
    def _on_tick(self, symbol: str, price: float, volume: int, timestamp):
        """Handle tick data"""
        # Update position prices for trailing stop
        if self.portfolio_manager.has_position(symbol):
            self.portfolio_manager.update_position_price(symbol, price)
            
            # Update trailing stop
            position = self.portfolio_manager.get_position(symbol)
            if position:
                candles_df = self.market_feed.get_candles(symbol, 100)
                if not candles_df.empty:
                    position_type = 'LONG' if position.is_long else 'SHORT'
                    new_tsl = self.risk_manager.calculate_trailing_stop(
                        symbol, candles_df, price, position_type
                    )
                    if new_tsl:
                        self.portfolio_manager.update_position_trailing_stop(symbol, new_tsl)
    
    def _on_candle_complete(self, symbol: str, candle: Dict):
        """Handle completed candle"""
        if not self.is_trading_hours:
            return
        
        # Check circuit breaker
        can_trade, reason = self.circuit_breaker.can_trade()
        if not can_trade:
            return
        
        # Get candles for analysis
        candles_df = self.market_feed.get_candles(symbol, 250)
        if candles_df.empty or len(candles_df) < 200:
            return
        
        # Add indicators
        candles_df = TechnicalIndicators.add_all_indicators(candles_df, self.config)
        
        # Check if already have position
        if self.portfolio_manager.has_position(symbol):
            self._manage_existing_position(symbol, candles_df)
        else:
            self._check_entry_signal(symbol, candles_df)
    
    def _check_entry_signal(self, symbol: str, df):
        """Check for entry signal"""
        # Check if can open new position
        if not self.portfolio_manager.can_open_new_position():
            return
        
        # Classify market regime
        regime = self.regime_classifier.classify(df)
        
        if regime == MarketRegime.UNDEFINED:
            logger.debug(f"{symbol}: Market regime undefined - skipping")
            return
        
        # Select strategy based on regime
        if regime == MarketRegime.TRENDING:
            strategy = self.trending_strategy
        else:
            strategy = self.ranging_strategy
        
        # Generate signal
        signal, signal_info = strategy.generate_signal(df)
        
        if signal == Signal.NO_SIGNAL:
            return
        
        # Multi-timeframe confirmation (if enabled)
        if self.mtf_analyzer.enabled:
            # For simplicity, using same df resampled to higher TF
            higher_tf_df = self.mtf_analyzer.resample_to_higher_timeframe(
                df, self.mtf_analyzer.secondary_tf
            )
            confirmed, mtf_reason = self.mtf_analyzer.confirm_signal(
                signal.value, df, higher_tf_df
            )
            
            if not confirmed:
                logger.info(f"{symbol}: Signal not confirmed by higher TF: {mtf_reason}")
                return
        
        # Calculate position parameters
        entry_price = df['close'].iloc[-1]
        position_type = 'LONG' if signal == Signal.BUY else 'SHORT'
        
        params = self.risk_manager.calculate_full_position_params(
            symbol, df, entry_price, position_type
        )
        
        if not params['rr_valid']:
            logger.warning(f"{symbol}: Risk-reward ratio not valid")
            return
        
        # Execute trade
        self._execute_entry(symbol, signal, params, strategy.name)
    
    def _execute_entry(self, symbol: str, signal: Signal, params: Dict, strategy_name: str):
        """Execute entry trade"""
        logger.info(f"🎯 Executing {signal.value} for {symbol}")
        
        transaction_type = TransactionType.BUY if signal == Signal.BUY else TransactionType.SELL
        
        # Place bracket order
        orders = self.order_manager.place_bracket_order(
            symbol=symbol,
            quantity=params['position_size'],
            entry_price=params['entry_price'],
            stop_loss=params['stop_loss'],
            target=params['target'],
            transaction_type=transaction_type,
            product="I",  # Intraday
            strategy_name=strategy_name
        )
        
        if orders:
            entry_order, sl_order, target_order = orders
            
            # Add to portfolio
            quantity = params['position_size'] if signal == Signal.BUY else -params['position_size']
            self.portfolio_manager.open_position(
                symbol=symbol,
                quantity=quantity,
                entry_price=params['entry_price'],
                stop_loss=params['stop_loss'],
                target=params['target'],
                strategy_name=strategy_name
            )
            
            logger.info(f"✅ Position opened for {symbol}")
    
    def _manage_existing_position(self, symbol: str, df):
        """Manage existing position"""
        position = self.portfolio_manager.get_position(symbol)
        if not position:
            return
        
        # Determine which strategy to use based on original strategy
        if "Trending" in position.strategy_name:
            strategy = self.trending_strategy
        else:
            strategy = self.ranging_strategy
        
        # Check for exit signal from strategy
        position_type = 'LONG' if position.is_long else 'SHORT'
        should_exit, reason = strategy.get_exit_signal(df, position_type)
        
        if should_exit:
            self._close_position(symbol, reason)
    
    def _close_position(self, symbol: str, reason: str):
        """Close position"""
        logger.info(f"Closing position for {symbol}: {reason}")
        
        position = self.portfolio_manager.get_position(symbol)
        if not position:
            return
        
        # Place market order to close
        transaction_type = TransactionType.SELL if position.is_long else TransactionType.BUY
        
        order = self.order_manager.place_market_order(
            symbol=symbol,
            quantity=position.abs_quantity,
            transaction_type=transaction_type,
            product="I",
            strategy_name=f"{position.strategy_name}_EXIT"
        )
        
        if order:
            # Close in portfolio
            trade = self.portfolio_manager.close_position(symbol, exit_reason=reason)
            
            if trade:
                # Track for circuit breaker
                result = 'WIN' if trade.pnl > 0 else 'LOSS'
                if self.circuit_breaker.check_consecutive_losses(result):
                    self._trigger_circuit_breaker(CircuitBreakerTrigger.CONSECUTIVE_LOSSES, 
                                                 f"{self.circuit_breaker.consecutive_losses} consecutive losses")
                
                # Reset risk manager tracking
                self.risk_manager.reset_position_tracking(symbol)
    
    def _trigger_circuit_breaker(self, trigger, reason: str):
        """Trigger circuit breaker"""
        self.circuit_breaker.trip(trigger, reason)
        
        # Square off all positions
        self.portfolio_manager.square_off_all_positions(reason=f"Circuit Breaker: {trigger.value}")
        
        logger.critical("🚨 ALL POSITIONS SQUARED OFF 🚨")
    
    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            'is_running': self.is_running,
            'is_trading_hours': self.is_trading_hours,
            'circuit_breaker': self.circuit_breaker.get_status(),
            'portfolio': self.portfolio_manager.get_portfolio_summary(),
            'active_orders': len(self.order_manager.get_active_orders())
        }


def main():
    """Main entry point"""
    # Setup logging
    logger.add(
        "logs/trading_{time}.log",
        rotation="100 MB",
        retention="30 days",
        level="INFO"
    )
    
    # Create and start bot
    bot = AlgoTradingBot()
    
    try:
        bot.start()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    finally:
        bot.stop()


if __name__ == "__main__":
    main()
