"""
Main Trading Bot - Live Trading Execution
"""
import logging
import time
import sys
from datetime import datetime
import pandas as pd
from trading_bot.core.auth import UpstoxAuth
from trading_bot.core.market_data import MarketDataFeed
from trading_bot.core.order_manager import OrderManager
from trading_bot.core.portfolio import PortfolioManager
from trading_bot.core.logger import TradeLogger
from trading_bot.strategies.regime_classifier import RegimeClassifier
from trading_bot.strategies.trending_strategy import TrendingStrategy
from trading_bot.strategies.ranging_strategy import RangingStrategy
from trading_bot.risk.position_sizing import PositionSizer
from trading_bot.risk.stop_loss import StopLossManager
from trading_bot.risk.circuit_breaker import CircuitBreaker
from trading_bot.utils.indicators import calculate_all_indicators
from trading_bot.utils.helpers import is_market_open, get_ist_time
from trading_bot.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot class"""
    
    def __init__(self):
        # Initialize authentication
        self.auth = UpstoxAuth()
        
        if not self.auth.is_authenticated():
            logger.error("Authentication failed. Please check your credentials.")
            sys.exit(1)
        
        # Initialize core components
        self.market_data = MarketDataFeed(self.auth)
        self.order_manager = OrderManager(self.auth)
        self.portfolio_manager = PortfolioManager(self.auth)
        self.trade_logger = TradeLogger()
        
        # Initialize strategies
        self.regime_classifier = RegimeClassifier()
        self.trending_strategy = TrendingStrategy()
        self.ranging_strategy = RangingStrategy()
        
        # Initialize risk management
        self.position_sizer = PositionSizer(settings.INITIAL_CAPITAL, settings.RISK_PER_TRADE_PERCENT)
        self.stop_loss_manager = StopLossManager()
        self.circuit_breaker = CircuitBreaker(
            self.portfolio_manager,
            self.order_manager,
            self.trade_logger
        )
        
        # Track positions
        self.active_positions: dict[str, dict] = {}
        
        # External event filter (conceptual)
        self.external_events_blocked = False
        self._load_external_events()
    
    def _load_external_events(self):
        """
        Load external events that should halt trading
        This is a conceptual implementation - in production, you would:
        1. Connect to a calendar API (e.g., RBI announcements, election results)
        2. Check scheduled events before trading
        3. Set self.external_events_blocked = True if event is scheduled
        
        Example events:
        - RBI Monetary Policy Committee (MPC) meetings
        - General Election results
        - Budget announcements
        - Major economic data releases
        """
        # Placeholder: In production, implement actual event checking
        # For now, this is a template showing awareness of macro shocks
        
        today = get_ist_time().date()
        
        # Example: Check for known event dates (this would come from an API in production)
        # blocked_dates = [
        #     datetime(2024, 3, 15).date(),  # Example: RBI MPC meeting
        #     datetime(2024, 4, 19).date(),  # Example: Election results
        # ]
        #
        # if today in blocked_dates:
        #     self.external_events_blocked = True
        #     logger.warning(f"Trading blocked due to external event on {today}")
        
        logger.info("External event filter initialized (conceptual)")
    
    def _on_candle_update(self, symbol: str, candle: dict):
        """Callback when new candle is formed"""
        try:
            # Get historical candles
            candles_df = self.market_data.get_candles(symbol, count=300)
            
            if candles_df.empty or len(candles_df) < 200:
                return
            
            # Prepare data
            candles_df = calculate_all_indicators(candles_df)
            current_price = candle['close']
            
            # Check circuit breaker
            should_halt, daily_loss = self.circuit_breaker.check_daily_loss()
            if should_halt:
                logger.critical("Trading halted by circuit breaker")
                return
            
            # Check external events
            if self.external_events_blocked:
                logger.warning("Trading blocked due to external event")
                return
            
            # Classify regime
            regime = self.regime_classifier.classify_regime(candles_df)
            
            # Generate signal
            if regime == "TRENDING":
                signal, signal_data = self.trending_strategy.generate_signal(candles_df, current_price)
            elif regime == "RANGING":
                signal, signal_data = self.ranging_strategy.generate_signal(candles_df, current_price)
            else:
                signal = "HOLD"
                signal_data = {}
            
            # Multi-timeframe confirmation (would need higher timeframe data)
            # For now, we'll proceed with the signal
            
            # Execute trading logic
            self._execute_trading_logic(symbol, signal, signal_data, candles_df, current_price, regime)
            
        except Exception as e:
            logger.error(f"Error in candle update handler: {e}")
    
    def _execute_trading_logic(
        self,
        symbol: str,
        signal: str,
        signal_data: dict,
        candles_df: pd.DataFrame,
        current_price: float,
        regime: str
    ):
        """Execute trading logic based on signal"""
        try:
            # Check if we already have a position
            existing_position = self.active_positions.get(symbol)
            current_bar = candles_df.iloc[-1]
            atr = current_bar.get('atr', 0)
            
            if signal == "BUY" and existing_position is None:
                # Enter new position
                if pd.notna(atr) and atr > 0:
                    # Calculate position size and stop loss
                    quantity, risk_amount, stop_loss = self.position_sizer.calculate_position_size_from_atr(
                        current_price, atr
                    )
                    
                    # Place order
                    order_id = self.order_manager.place_market_order(
                        symbol=symbol,
                        quantity=quantity,
                        transaction_type="BUY",
                        product="I"  # Intraday
                    )
                    
                    if order_id:
                        # Track position
                        self.active_positions[symbol] = {
                            'symbol': symbol,
                            'entry_price': current_price,
                            'quantity': quantity,
                            'stop_loss': stop_loss,
                            'trailing_stop': stop_loss,
                            'highest_price': current_price,
                            'lowest_price': current_price,
                            'entry_time': get_ist_time(),
                            'regime': regime,
                            'strategy': signal_data.get('strategy', regime),
                            'order_id': order_id
                        }
                        
                        # Log entry
                        self.trade_logger.log_entry(
                            symbol=symbol,
                            action="BUY",
                            order_type="MARKET",
                            quantity=quantity,
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            strategy=regime,
                            regime=regime,
                            timeframe=settings.ENTRY_TIMEFRAME,
                            position_size=quantity * current_price,
                            risk_amount=risk_amount,
                            atr_value=atr,
                            reason=signal_data.get('reason', '')
                        )
                        
                        logger.info(f"Entered BUY position: {symbol} @ {current_price}")
            
            elif signal == "SELL" and existing_position:
                # Exit position
                exit_price = current_price
                order_id = self.order_manager.place_market_order(
                    symbol=symbol,
                    quantity=existing_position['quantity'],
                    transaction_type="SELL",
                    product="I"
                )
                
                if order_id:
                    # Log exit
                    self.trade_logger.log_exit(
                        symbol=symbol,
                        exit_price=exit_price,
                        trailing_stop=existing_position.get('trailing_stop'),
                        reason=signal_data.get('reason', 'Signal Exit')
                    )
                    
                    # Remove position
                    del self.active_positions[symbol]
                    logger.info(f"Exited position: {symbol} @ {exit_price}")
            
            # Update trailing stop for existing positions
            if existing_position:
                updated_tsl = self.stop_loss_manager.update_trailing_stop(
                    symbol,
                    existing_position['entry_price'],
                    current_price,
                    atr,
                    existing_position,
                    is_long=True
                )
                
                if updated_tsl:
                    existing_position['trailing_stop'] = updated_tsl
                    self.trade_logger.log_update(symbol, updated_tsl, current_price)
                
                # Check if stop loss hit
                stop_loss = existing_position.get('trailing_stop') or existing_position.get('stop_loss')
                if stop_loss and self.stop_loss_manager.should_exit_on_stop_loss(
                    current_price, stop_loss, is_long=True
                ):
                    # Exit on stop loss
                    exit_order_id = self.order_manager.place_market_order(
                        symbol=symbol,
                        quantity=existing_position['quantity'],
                        transaction_type="SELL",
                        product="I"
                    )
                    
                    if exit_order_id:
                        self.trade_logger.log_exit(
                            symbol=symbol,
                            exit_price=stop_loss,
                            trailing_stop=stop_loss,
                            reason="Stop Loss"
                        )
                        
                        del self.active_positions[symbol]
                        logger.warning(f"Stop loss triggered: {symbol} @ {stop_loss}")
        
        except Exception as e:
            logger.error(f"Error executing trading logic: {e}")
    
    def start(self, symbols: list[str]):
        """Start the trading bot"""
        logger.info("Starting trading bot...")
        
        # Check if market is open
        if not is_market_open():
            logger.warning("Market is not open. Waiting...")
            # Wait until market opens
            while not is_market_open():
                time.sleep(60)
        
        # Set up market data callbacks
        self.market_data.on_candle_update = self._on_candle_update
        
        # Start market data feed
        self.market_data.start()
        
        # Subscribe to symbols
        time.sleep(2)  # Wait for connection
        self.market_data.subscribe(symbols)
        
        logger.info(f"Trading bot started. Monitoring {len(symbols)} symbols")
        
        # Main loop
        try:
            while is_market_open():
                # Check circuit breaker
                should_halt, daily_loss = self.circuit_breaker.check_daily_loss()
                if should_halt:
                    logger.critical("Circuit breaker triggered. Stopping bot.")
                    break
                
                # Update positions from portfolio
                self.portfolio_manager.fetch_positions()
                
                # Sleep for a minute
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Trading bot stopped by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("Stopping trading bot...")
        self.market_data.stop()
        logger.info("Trading bot stopped")


def main():
    """Main entry point"""
    # Symbols to trade (should be in Upstox instrument key format)
    # Example: ["NSE_EQ|INE467B01029"] for RELIANCE
    symbols = [
        "NSE_EQ|INE467B01029",  # RELIANCE (example - replace with actual instrument keys)
    ]
    
    bot = TradingBot()
    bot.start(symbols)


if __name__ == "__main__":
    main()
