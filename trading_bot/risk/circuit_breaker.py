"""
Circuit Breaker (Kill Switch) - Square off all positions if daily loss exceeds threshold
"""
import logging
from datetime import datetime
from trading_bot.core.logger import TradeLogger
from trading_bot.core.portfolio import PortfolioManager
from trading_bot.core.order_manager import OrderManager
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to halt trading if daily loss exceeds threshold"""
    
    def __init__(
        self,
        portfolio_manager: PortfolioManager,
        order_manager: OrderManager,
        trade_logger: TradeLogger,
        max_daily_loss_percent: Optional[float] = None,
        initial_capital: Optional[float] = None
    ):
        self.portfolio_manager = portfolio_manager
        self.order_manager = order_manager
        self.trade_logger = trade_logger
        self.max_daily_loss_percent = max_daily_loss_percent or settings.MAX_DAILY_LOSS_PERCENT
        self.initial_capital = initial_capital or settings.INITIAL_CAPITAL
        self.is_triggered = False
        self.trigger_time: Optional[datetime] = None
    
    def check_daily_loss(self) -> tuple[bool, float]:
        """
        Check if daily loss exceeds threshold
        
        Returns:
            tuple: (should_halt, daily_loss_percent)
        """
        if self.is_triggered:
            return True, 0.0
        
        # Get daily P&L from trade logger
        daily_pnl = self.trade_logger.get_daily_pnl()
        
        # Also check current positions P&L
        positions_pnl = self.portfolio_manager.get_total_pnl()
        total_daily_pnl = daily_pnl + positions_pnl
        
        # Calculate loss percentage
        daily_loss_percent = abs(total_daily_pnl / self.initial_capital) * 100 if total_daily_pnl < 0 else 0.0
        
        should_halt = daily_loss_percent >= self.max_daily_loss_percent
        
        if should_halt and not self.is_triggered:
            logger.critical(
                f"Circuit breaker triggered! Daily loss: {daily_loss_percent:.2f}% "
                f"(Threshold: {self.max_daily_loss_percent}%)"
            )
            self.is_triggered = True
            self.trigger_time = datetime.now()
            self._execute_kill_switch()
        
        return should_halt, daily_loss_percent
    
    def _execute_kill_switch(self):
        """Execute kill switch: square off all positions and halt trading"""
        logger.critical("Executing kill switch - squaring off all positions")
        
        try:
            # Square off all positions
            order_ids = self.portfolio_manager.square_off_all_positions(self.order_manager)
            
            logger.critical(
                f"Kill switch executed. Squared off {len(order_ids)} positions. "
                f"Trading halted at {self.trigger_time}"
            )
            
            # Log the event
            self.trade_logger.log_entry(
                symbol="SYSTEM",
                action="KILL_SWITCH",
                order_type="MARKET",
                quantity=0,
                entry_price=0,
                stop_loss=0,
                strategy="CIRCUIT_BREAKER",
                regime="N/A",
                timeframe="N/A",
                position_size=0,
                risk_amount=0,
                atr_value=0,
                reason=f"Daily loss exceeded {self.max_daily_loss_percent}% threshold"
            )
            
        except Exception as e:
            logger.error(f"Error executing kill switch: {e}")
    
    def reset(self):
        """Reset circuit breaker (for new trading day)"""
        self.is_triggered = False
        self.trigger_time = None
        logger.info("Circuit breaker reset")
    
    def is_halted(self) -> bool:
        """Check if trading is currently halted"""
        return self.is_triggered
