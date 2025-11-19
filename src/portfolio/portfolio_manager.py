"""
Portfolio and Position Manager
Real-time P&L tracking, fetching open/closed positions
"""

from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import INITIAL_CAPITAL, MAX_DAILY_LOSS_PERCENT, CIRCUIT_BREAKER_ENABLED
from src.auth.session_manager import SessionManager


class PortfolioManager:
    """
    Manages portfolio positions and P&L tracking
    Implements circuit breaker (kill switch) for daily loss limits
    """
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize Portfolio Manager
        
        Args:
            session_manager: Authenticated session manager
        """
        self.session_manager = session_manager
        self.initial_capital = INITIAL_CAPITAL
        self.positions: Dict[str, Dict] = {}
        self.closed_positions: List[Dict] = []
        self.daily_pnl = 0.0
        self.daily_start_capital = INITIAL_CAPITAL
        self.circuit_breaker_triggered = False
    
    def _make_request(self, endpoint: str) -> Dict:
        """
        Make authenticated API request
        
        Args:
            endpoint: API endpoint
            
        Returns:
            API response
        """
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self.session_manager.get_headers()
        
        try:
            response = self.session_manager.get_session().get(url, headers=headers)
            
            if response.status_code == 401:
                logger.warning("Token expired, refreshing...")
                if self.session_manager.refresh_access_token():
                    headers = self.session_manager.get_headers()
                    response = self.session_manager.get_session().get(url, headers=headers)
                else:
                    raise Exception("Failed to refresh token")
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"Error making portfolio request: {e}")
            raise
    
    def fetch_positions(self) -> List[Dict]:
        """
        Fetch all open positions
        
        Returns:
            List of open positions
        """
        try:
            response = self._make_request("portfolio/positions")
            positions_data = response.get('data', [])
            
            # Update positions dictionary
            for pos in positions_data:
                symbol = pos.get('symbol') or pos.get('instrument_token')
                if symbol:
                    self.positions[symbol] = {
                        'symbol': symbol,
                        'quantity': int(pos.get('quantity', 0)),
                        'average_price': float(pos.get('average_price', 0)),
                        'last_price': float(pos.get('last_price', 0)),
                        'pnl': float(pos.get('pnl', 0)),
                        'product': pos.get('product', 'INTRADAY'),
                        'timestamp': datetime.now()
                    }
            
            logger.info(f"Fetched {len(positions_data)} positions")
            return positions_data
        
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def fetch_holdings(self) -> List[Dict]:
        """
        Fetch all holdings (delivery positions)
        
        Returns:
            List of holdings
        """
        try:
            response = self._make_request("portfolio/holdings")
            holdings_data = response.get('data', [])
            logger.info(f"Fetched {len(holdings_data)} holdings")
            return holdings_data
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position dictionary or None
        """
        return self.positions.get(symbol)
    
    def calculate_total_pnl(self) -> float:
        """
        Calculate total unrealized P&L from all positions
        
        Returns:
            Total P&L
        """
        total_pnl = 0.0
        for pos in self.positions.values():
            total_pnl += pos.get('pnl', 0)
        return total_pnl
    
    def calculate_daily_pnl(self) -> float:
        """
        Calculate daily P&L (including closed positions)
        
        Returns:
            Daily P&L
        """
        # Calculate unrealized P&L from open positions
        unrealized_pnl = self.calculate_total_pnl()
        
        # Calculate realized P&L from closed positions today
        realized_pnl = sum(
            pos.get('realized_pnl', 0) 
            for pos in self.closed_positions 
            if pos.get('close_date', datetime.now()).date() == datetime.now().date()
        )
        
        self.daily_pnl = unrealized_pnl + realized_pnl
        return self.daily_pnl
    
    def update_position(self, symbol: str, quantity: int, price: float, side: str):
        """
        Update position after order execution
        
        Args:
            symbol: Stock symbol
            quantity: Order quantity
            price: Execution price
            side: BUY or SELL
        """
        if symbol not in self.positions:
            self.positions[symbol] = {
                'symbol': symbol,
                'quantity': 0,
                'average_price': 0.0,
                'last_price': price,
                'pnl': 0.0,
                'product': 'INTRADAY',
                'timestamp': datetime.now()
            }
        
        pos = self.positions[symbol]
        
        if side == 'BUY':
            # Add to position
            total_cost = (pos['quantity'] * pos['average_price']) + (quantity * price)
            pos['quantity'] += quantity
            if pos['quantity'] > 0:
                pos['average_price'] = total_cost / pos['quantity']
        elif side == 'SELL':
            # Reduce position
            pos['quantity'] -= quantity
            if pos['quantity'] <= 0:
                # Position closed
                realized_pnl = quantity * (price - pos['average_price'])
                closed_pos = {
                    'symbol': symbol,
                    'quantity': quantity,
                    'entry_price': pos['average_price'],
                    'exit_price': price,
                    'realized_pnl': realized_pnl,
                    'close_date': datetime.now()
                }
                self.closed_positions.append(closed_pos)
                
                if pos['quantity'] == 0:
                    del self.positions[symbol]
                else:
                    pos['average_price'] = price  # Update average for remaining quantity
        
        pos['last_price'] = price
        pos['pnl'] = pos['quantity'] * (pos['last_price'] - pos['average_price'])
    
    def check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker should be triggered
        
        Returns:
            True if circuit breaker triggered, False otherwise
        """
        if not CIRCUIT_BREAKER_ENABLED:
            return False
        
        if self.circuit_breaker_triggered:
            return True
        
        daily_pnl = self.calculate_daily_pnl()
        daily_loss_percent = abs(daily_pnl) / self.daily_start_capital if daily_pnl < 0 else 0
        
        if daily_loss_percent >= MAX_DAILY_LOSS_PERCENT:
            self.circuit_breaker_triggered = True
            logger.critical(
                f"CIRCUIT BREAKER TRIGGERED! Daily loss: ₹{daily_pnl:.2f} "
                f"({daily_loss_percent*100:.2f}%) exceeds limit of {MAX_DAILY_LOSS_PERCENT*100}%"
            )
            return True
        
        return False
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get portfolio summary
        
        Returns:
            Portfolio summary dictionary
        """
        total_pnl = self.calculate_total_pnl()
        daily_pnl = self.calculate_daily_pnl()
        current_capital = self.initial_capital + daily_pnl
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': current_capital,
            'total_pnl': total_pnl,
            'daily_pnl': daily_pnl,
            'daily_return_pct': (daily_pnl / self.daily_start_capital) * 100,
            'num_positions': len(self.positions),
            'num_closed_today': len([
                p for p in self.closed_positions 
                if p.get('close_date', datetime.now()).date() == datetime.now().date()
            ]),
            'circuit_breaker_triggered': self.circuit_breaker_triggered
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of trading day)"""
        self.daily_start_capital = self.initial_capital + self.daily_pnl
        self.daily_pnl = 0.0
        self.circuit_breaker_triggered = False
        logger.info("Daily stats reset")
