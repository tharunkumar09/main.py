"""
Portfolio & Position Manager with Real-time P&L tracking
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import requests
import pandas as pd
from trading_bot.core.auth import UpstoxAuth
from trading_bot.config.settings import settings

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Real-time portfolio and position management"""
    
    def __init__(self, auth: UpstoxAuth):
        self.auth = auth
        self.base_url = settings.API_BASE_URL
        self.positions: Dict[str, Dict] = {}  # symbol -> position_data
        self.holdings: Dict[str, Dict] = {}  # symbol -> holding_data
        self.margin: Optional[Dict] = None
    
    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make API request"""
        try:
            headers = self.auth.get_headers()
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def fetch_positions(self) -> Dict[str, Dict]:
        """Fetch all open positions"""
        try:
            response = self._make_request("portfolio/short-term-positions")
            if response and 'data' in response:
                positions_data = response['data']
                
                # Update positions dictionary
                for pos in positions_data:
                    symbol = pos.get('symbol') or pos.get('instrument_token')
                    if symbol:
                        self.positions[symbol] = {
                            'symbol': symbol,
                            'quantity': pos.get('quantity', 0),
                            'average_price': pos.get('average_price', 0),
                            'last_price': pos.get('last_price', 0),
                            'pnl': pos.get('pnl', 0),
                            'pnl_percent': pos.get('pnl_percent', 0),
                            'product': pos.get('product', 'D'),
                            'transaction_type': pos.get('transaction_type', 'BUY'),
                            'timestamp': datetime.now()
                        }
                
                logger.info(f"Fetched {len(self.positions)} positions")
                return self.positions
            
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
        
        return {}
    
    def fetch_holdings(self) -> Dict[str, Dict]:
        """Fetch all holdings (delivery positions)"""
        try:
            response = self._make_request("portfolio/long-term-holdings")
            if response and 'data' in response:
                holdings_data = response['data']
                
                for holding in holdings_data:
                    symbol = holding.get('symbol') or holding.get('instrument_token')
                    if symbol:
                        self.holdings[symbol] = {
                            'symbol': symbol,
                            'quantity': holding.get('quantity', 0),
                            'average_price': holding.get('average_price', 0),
                            'last_price': holding.get('last_price', 0),
                            'pnl': holding.get('pnl', 0),
                            'pnl_percent': holding.get('pnl_percent', 0),
                            'timestamp': datetime.now()
                        }
                
                logger.info(f"Fetched {len(self.holdings)} holdings")
                return self.holdings
            
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {e}")
        
        return {}
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position for a specific symbol"""
        self.fetch_positions()  # Refresh positions
        return self.positions.get(symbol)
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L from all positions"""
        self.fetch_positions()
        total_pnl = sum(pos.get('pnl', 0) for pos in self.positions.values())
        return total_pnl
    
    def get_total_pnl_percent(self) -> float:
        """Calculate total P&L percentage"""
        self.fetch_positions()
        total_invested = sum(
            pos.get('average_price', 0) * pos.get('quantity', 0)
            for pos in self.positions.values()
        )
        
        if total_invested == 0:
            return 0.0
        
        total_pnl = self.get_total_pnl()
        return (total_pnl / total_invested) * 100
    
    def get_margin(self) -> Optional[Dict]:
        """Fetch available margin"""
        try:
            response = self._make_request("user/get-margins")
            if response and 'data' in response:
                self.margin = response['data']
                return self.margin
            
        except Exception as e:
            logger.error(f"Failed to fetch margin: {e}")
        
        return None
    
    def get_available_margin(self) -> float:
        """Get available margin for trading"""
        margin = self.get_margin()
        if margin:
            # Adjust based on actual API response structure
            return margin.get('available', 0) or margin.get('equity', {}).get('available', 0)
        return 0.0
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        positions = self.fetch_positions()
        holdings = self.fetch_holdings()
        margin = self.get_margin()
        
        total_positions_pnl = sum(pos.get('pnl', 0) for pos in positions.values())
        total_holdings_pnl = sum(hold.get('pnl', 0) for hold in holdings.values())
        
        return {
            'positions_count': len(positions),
            'holdings_count': len(holdings),
            'total_positions_pnl': total_positions_pnl,
            'total_holdings_pnl': total_holdings_pnl,
            'total_pnl': total_positions_pnl + total_holdings_pnl,
            'available_margin': self.get_available_margin(),
            'positions': positions,
            'holdings': holdings,
            'margin': margin,
            'timestamp': datetime.now().isoformat()
        }
    
    def square_off_all_positions(self, order_manager) -> List[str]:
        """Square off all open positions (used by circuit breaker)"""
        positions = self.fetch_positions()
        order_ids = []
        
        for symbol, position in positions.items():
            quantity = abs(position.get('quantity', 0))
            if quantity == 0:
                continue
            
            # Determine opposite transaction type
            current_type = position.get('transaction_type', 'BUY')
            opposite_type = 'SELL' if current_type == 'BUY' else 'BUY'
            
            # Place market order to square off
            order_id = order_manager.place_market_order(
                symbol=symbol,
                quantity=quantity,
                transaction_type=opposite_type,
                product=position.get('product', 'I')  # Intraday for quick square off
            )
            
            if order_id:
                order_ids.append(order_id)
                logger.warning(f"Squaring off position: {symbol} - Order ID: {order_id}")
        
        return order_ids
