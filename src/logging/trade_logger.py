"""
Trade Logging System
Detailed entry/exit, P&L, reason, and timestamp logging
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import LOGS_DIR


class TradeLogger:
    """
    Comprehensive trade logging system
    Logs all trades with detailed information
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize Trade Logger
        
        Args:
            log_file: Path to log file (optional)
        """
        self.log_file = log_file or (LOGS_DIR / f"trades_{datetime.now().strftime('%Y%m%d')}.json")
        self.csv_file = self.log_file.with_suffix('.csv')
        self.trades: List[Dict] = []
        
        # Initialize CSV file with headers
        self._init_csv()
    
    def _init_csv(self):
        """Initialize CSV file with headers"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'side', 'quantity', 'price', 'order_type',
                    'entry_time', 'exit_time', 'entry_price', 'exit_price',
                    'pnl', 'pnl_percent', 'reason', 'stop_loss', 'target',
                    'holding_duration_minutes', 'strategy', 'regime'
                ])
    
    def log_entry(self, symbol: str, side: str, quantity: int, price: float,
                  order_type: str, reason: str, stop_loss: Optional[float] = None,
                  target: Optional[float] = None, strategy: str = None,
                  regime: str = None) -> str:
        """
        Log trade entry
        
        Args:
            symbol: Stock symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Entry price
            order_type: Order type (MARKET, LIMIT, etc.)
            reason: Reason for entry
            stop_loss: Stop-loss price
            target: Target price
            strategy: Strategy name
            regime: Market regime (TRENDING, RANGING)
            
        Returns:
            Trade ID
        """
        trade_id = f"{symbol}_{int(datetime.now().timestamp())}"
        
        trade = {
            'trade_id': trade_id,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'entry_time': datetime.now().isoformat(),
            'order_type': order_type,
            'reason': reason,
            'stop_loss': stop_loss,
            'target': target,
            'strategy': strategy,
            'regime': regime,
            'status': 'OPEN'
        }
        
        self.trades.append(trade)
        self._save_trade(trade)
        
        logger.info(
            f"Trade Entry Logged: {trade_id} | {side} {quantity} {symbol} @ {price} | "
            f"Reason: {reason} | Strategy: {strategy} | Regime: {regime}"
        )
        
        return trade_id
    
    def log_exit(self, trade_id: str, exit_price: float, exit_reason: str,
                 pnl: Optional[float] = None):
        """
        Log trade exit
        
        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_reason: Reason for exit
            pnl: Realized P&L (optional, will be calculated if not provided)
        """
        trade = self._find_trade(trade_id)
        if not trade:
            logger.warning(f"Trade {trade_id} not found for exit logging")
            return
        
        entry_price = trade['entry_price']
        quantity = trade['quantity']
        side = trade['side']
        
        # Calculate P&L if not provided
        if pnl is None:
            if side == 'BUY':
                pnl = (exit_price - entry_price) * quantity
            else:  # SELL
                pnl = (entry_price - exit_price) * quantity
        
        pnl_percent = (pnl / (entry_price * quantity)) * 100
        
        # Calculate holding duration
        entry_time = datetime.fromisoformat(trade['entry_time'])
        exit_time = datetime.now()
        holding_duration = (exit_time - entry_time).total_seconds() / 60
        
        trade.update({
            'exit_price': exit_price,
            'exit_time': exit_time.isoformat(),
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'holding_duration_minutes': holding_duration,
            'status': 'CLOSED'
        })
        
        self._save_trade(trade, update=True)
        
        logger.info(
            f"Trade Exit Logged: {trade_id} | Exit @ {exit_price} | "
            f"P&L: ₹{pnl:.2f} ({pnl_percent:.2f}%) | Reason: {exit_reason} | "
            f"Duration: {holding_duration:.1f} min"
        )
    
    def _find_trade(self, trade_id: str) -> Optional[Dict]:
        """Find trade by ID"""
        for trade in self.trades:
            if trade.get('trade_id') == trade_id:
                return trade
        return None
    
    def _save_trade(self, trade: Dict, update: bool = False):
        """
        Save trade to JSON and CSV files
        
        Args:
            trade: Trade dictionary
            update: Whether this is an update to existing trade
        """
        # Save to JSON
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    trades = json.load(f)
            else:
                trades = []
            
            if update:
                # Update existing trade
                for i, t in enumerate(trades):
                    if t.get('trade_id') == trade.get('trade_id'):
                        trades[i] = trade
                        break
            else:
                # Add new trade
                trades.append(trade)
            
            with open(self.log_file, 'w') as f:
                json.dump(trades, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving trade to JSON: {e}")
        
        # Append to CSV
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                
                entry_time = trade.get('entry_time', '')
                exit_time = trade.get('exit_time', '')
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                pnl = trade.get('pnl', 0)
                pnl_percent = trade.get('pnl_percent', 0)
                holding_duration = trade.get('holding_duration_minutes', 0)
                
                writer.writerow([
                    trade.get('entry_time', datetime.now().isoformat()),
                    trade.get('symbol', ''),
                    trade.get('side', ''),
                    trade.get('quantity', 0),
                    entry_price,
                    trade.get('order_type', ''),
                    entry_time,
                    exit_time,
                    entry_price,
                    exit_price,
                    pnl,
                    pnl_percent,
                    trade.get('reason', ''),
                    trade.get('stop_loss', ''),
                    trade.get('target', ''),
                    holding_duration,
                    trade.get('strategy', ''),
                    trade.get('regime', '')
                ])
        
        except Exception as e:
            logger.error(f"Error saving trade to CSV: {e}")
    
    def get_trades(self, symbol: Optional[str] = None, 
                   status: Optional[str] = None) -> List[Dict]:
        """
        Get trades with optional filters
        
        Args:
            symbol: Filter by symbol
            status: Filter by status (OPEN, CLOSED)
            
        Returns:
            List of trades
        """
        trades = self.trades
        
        if symbol:
            trades = [t for t in trades if t.get('symbol') == symbol]
        
        if status:
            trades = [t for t in trades if t.get('status') == status]
        
        return trades
    
    def get_performance_summary(self) -> Dict:
        """
        Get performance summary from logged trades
        
        Returns:
            Performance summary dictionary
        """
        closed_trades = [t for t in self.trades if t.get('status') == 'CLOSED']
        
        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'profit_factor': 0
            }
        
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100
        total_profit = sum(t.get('pnl', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(closed_trades),
            'total_profit': total_profit,
            'total_loss': total_loss,
            'profit_factor': profit_factor,
            'avg_win': total_profit / len(winning_trades) if winning_trades else 0,
            'avg_loss': total_loss / len(losing_trades) if losing_trades else 0
        }
