"""
Circuit Breaker (Kill Switch)
Automatic trading halt on excessive losses or anomalies
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from enum import Enum


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # Trading halted
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


class CircuitBreakerTrigger(Enum):
    """Triggers for circuit breaker"""
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    RAPID_DRAWDOWN = "RAPID_DRAWDOWN"
    API_ERRORS = "API_ERRORS"
    EXTERNAL_EVENT = "EXTERNAL_EVENT"
    MANUAL = "MANUAL"


class CircuitBreaker:
    """
    Circuit Breaker System
    
    Triggers:
    1. Daily loss exceeds threshold (e.g., 3%)
    2. Consecutive losing trades (e.g., 5 in a row)
    3. Rapid drawdown (e.g., 2% loss in 5 minutes)
    4. Excessive API errors
    5. External events (scheduled)
    6. Manual override
    
    Actions:
    - Square off all positions
    - Halt new trades
    - Send alerts
    - Log incident
    """
    
    def __init__(self, config: dict):
        """
        Initialize circuit breaker
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Thresholds
        self.max_daily_loss_percent = config.get('trading', {}).get('max_daily_loss_percent', 3.0)
        self.max_consecutive_losses = 5
        self.rapid_drawdown_percent = 2.0
        self.rapid_drawdown_period_minutes = 5
        self.max_api_errors = 10
        
        # State
        self.state = CircuitBreakerState.CLOSED
        self.triggered_at: Optional[datetime] = None
        self.trigger_reason: Optional[CircuitBreakerTrigger] = None
        self.reset_time: Optional[datetime] = None
        
        # Tracking
        self.consecutive_losses = 0
        self.recent_pnl_history: List[Dict] = []
        self.api_error_count = 0
        self.external_events: List[Dict] = []
        
        # Recovery settings
        self.cooldown_period_minutes = 30
        
        logger.info(f"CircuitBreaker initialized: max_daily_loss={self.max_daily_loss_percent}%, "
                   f"cooldown={self.cooldown_period_minutes}min")
    
    def check_daily_loss(self, daily_pnl_percent: float) -> bool:
        """
        Check if daily loss limit is breached
        
        Args:
            daily_pnl_percent: Daily P&L percentage
            
        Returns:
            True if circuit breaker should trip
        """
        if daily_pnl_percent < 0 and abs(daily_pnl_percent) >= self.max_daily_loss_percent:
            logger.critical(f"Daily loss limit breached: {daily_pnl_percent:.2f}% (limit: -{self.max_daily_loss_percent}%)")
            return True
        return False
    
    def check_consecutive_losses(self, trade_result: str):
        """
        Track consecutive losses
        
        Args:
            trade_result: 'WIN' or 'LOSS'
        """
        if trade_result == 'LOSS':
            self.consecutive_losses += 1
            if self.consecutive_losses >= self.max_consecutive_losses:
                logger.critical(f"Consecutive losses limit reached: {self.consecutive_losses}")
                return True
        else:
            self.consecutive_losses = 0
        
        return False
    
    def check_rapid_drawdown(self, current_pnl_percent: float) -> bool:
        """
        Check for rapid drawdown
        
        Args:
            current_pnl_percent: Current P&L percentage
            
        Returns:
            True if rapid drawdown detected
        """
        now = datetime.now()
        
        # Add current P&L to history
        self.recent_pnl_history.append({
            'timestamp': now,
            'pnl_percent': current_pnl_percent
        })
        
        # Keep only recent history
        cutoff_time = now - timedelta(minutes=self.rapid_drawdown_period_minutes)
        self.recent_pnl_history = [
            entry for entry in self.recent_pnl_history
            if entry['timestamp'] > cutoff_time
        ]
        
        # Check for rapid drawdown
        if len(self.recent_pnl_history) >= 2:
            first_pnl = self.recent_pnl_history[0]['pnl_percent']
            current_pnl = self.recent_pnl_history[-1]['pnl_percent']
            drawdown = first_pnl - current_pnl
            
            if drawdown >= self.rapid_drawdown_percent:
                logger.critical(f"Rapid drawdown detected: {drawdown:.2f}% in {self.rapid_drawdown_period_minutes} minutes")
                return True
        
        return False
    
    def check_api_errors(self) -> bool:
        """
        Check API error count
        
        Returns:
            True if too many API errors
        """
        if self.api_error_count >= self.max_api_errors:
            logger.critical(f"Too many API errors: {self.api_error_count}")
            return True
        return False
    
    def increment_api_error(self):
        """Increment API error counter"""
        self.api_error_count += 1
        logger.warning(f"API error count: {self.api_error_count}/{self.max_api_errors}")
    
    def reset_api_errors(self):
        """Reset API error counter"""
        self.api_error_count = 0
    
    def add_external_event(self, event_name: str, event_time: datetime):
        """
        Add scheduled external event (e.g., RBI announcement)
        
        Args:
            event_name: Name of event
            event_time: Time of event
        """
        self.external_events.append({
            'name': event_name,
            'time': event_time
        })
        logger.info(f"External event scheduled: {event_name} at {event_time}")
    
    def check_external_events(self) -> Tuple[bool, Optional[str]]:
        """
        Check for upcoming external events
        
        Returns:
            Tuple of (should_halt, event_name)
        """
        now = datetime.now()
        buffer_minutes = 30  # Halt trading 30 min before event
        
        for event in self.external_events:
            time_to_event = (event['time'] - now).total_seconds() / 60
            
            if 0 <= time_to_event <= buffer_minutes:
                logger.warning(f"External event approaching: {event['name']} in {time_to_event:.0f} minutes")
                return True, event['name']
        
        return False, None
    
    def trip(self, trigger: CircuitBreakerTrigger, reason: str = ""):
        """
        Trip the circuit breaker
        
        Args:
            trigger: Trigger type
            reason: Additional reason
        """
        if self.state == CircuitBreakerState.OPEN:
            logger.warning("Circuit breaker already OPEN")
            return
        
        self.state = CircuitBreakerState.OPEN
        self.triggered_at = datetime.now()
        self.trigger_reason = trigger
        self.reset_time = self.triggered_at + timedelta(minutes=self.cooldown_period_minutes)
        
        logger.critical(f"⚠️  CIRCUIT BREAKER TRIPPED ⚠️")
        logger.critical(f"Trigger: {trigger.value}")
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Time: {self.triggered_at}")
        logger.critical(f"Reset scheduled at: {self.reset_time}")
        logger.critical(f"ACTION REQUIRED: Square off all positions and halt trading")
    
    def reset(self):
        """Reset circuit breaker to normal operation"""
        if self.state == CircuitBreakerState.CLOSED:
            logger.warning("Circuit breaker already CLOSED")
            return
        
        self.state = CircuitBreakerState.CLOSED
        self.triggered_at = None
        self.trigger_reason = None
        self.reset_time = None
        self.consecutive_losses = 0
        self.api_error_count = 0
        
        logger.info("✅ Circuit breaker RESET - normal operation resumed")
    
    def can_trade(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed
        
        Returns:
            Tuple of (can_trade, reason)
        """
        if self.state == CircuitBreakerState.OPEN:
            time_remaining = None
            if self.reset_time:
                time_remaining = (self.reset_time - datetime.now()).total_seconds() / 60
            
            reason = f"Circuit breaker OPEN: {self.trigger_reason.value}"
            if time_remaining and time_remaining > 0:
                reason += f" (reset in {time_remaining:.0f} minutes)"
            
            return False, reason
        
        return True, "Trading allowed"
    
    def check_auto_reset(self):
        """Check if circuit breaker should auto-reset"""
        if self.state == CircuitBreakerState.OPEN and self.reset_time:
            if datetime.now() >= self.reset_time:
                logger.info("Circuit breaker cooldown period elapsed - auto-resetting")
                self.reset()
    
    def manual_trip(self, reason: str = "Manual override"):
        """Manually trip circuit breaker"""
        self.trip(CircuitBreakerTrigger.MANUAL, reason)
    
    def get_status(self) -> Dict:
        """
        Get circuit breaker status
        
        Returns:
            Status dictionary
        """
        return {
            'state': self.state.value,
            'can_trade': self.state == CircuitBreakerState.CLOSED,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'trigger_reason': self.trigger_reason.value if self.trigger_reason else None,
            'reset_time': self.reset_time.isoformat() if self.reset_time else None,
            'consecutive_losses': self.consecutive_losses,
            'api_error_count': self.api_error_count,
            'scheduled_events': len(self.external_events)
        }
    
    def __repr__(self) -> str:
        return f"CircuitBreaker(state={self.state.value}, consecutive_losses={self.consecutive_losses})"
