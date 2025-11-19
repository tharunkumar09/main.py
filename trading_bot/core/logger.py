"""
Trade logging system with detailed entry/exit, P&L, reason, and timestamp
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
import pandas as pd
from trading_bot.config.settings import settings


class TradeLogger:
    """Comprehensive trade logging system"""
    
    def __init__(self, log_dir: Optional[str] = None):
        self.log_dir = Path(log_dir or settings.TRADES_LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
        self._initialize_log_file()
    
    def _initialize_log_file(self):
        """Initialize the CSV log file with headers if it doesn't exist"""
        if not self.trades_file.exists():
            columns = [
                'timestamp', 'symbol', 'action', 'order_type', 'quantity',
                'entry_price', 'exit_price', 'stop_loss', 'trailing_stop',
                'pnl', 'pnl_percent', 'reason', 'strategy', 'regime',
                'timeframe', 'position_size', 'risk_amount', 'atr_value'
            ]
            pd.DataFrame(columns=columns).to_csv(self.trades_file, index=False)
    
    def log_entry(
        self,
        symbol: str,
        action: str,  # 'BUY' or 'SELL'
        order_type: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        strategy: str,
        regime: str,
        timeframe: str,
        position_size: float,
        risk_amount: float,
        atr_value: float,
        reason: str = ""
    ):
        """Log a trade entry"""
        trade_data = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'order_type': order_type,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': None,
            'stop_loss': stop_loss,
            'trailing_stop': None,
            'pnl': None,
            'pnl_percent': None,
            'reason': reason,
            'strategy': strategy,
            'regime': regime,
            'timeframe': timeframe,
            'position_size': position_size,
            'risk_amount': risk_amount,
            'atr_value': atr_value
        }
        self._append_to_log(trade_data)
        return trade_data
    
    def log_exit(
        self,
        symbol: str,
        exit_price: float,
        trailing_stop: Optional[float] = None,
        reason: str = ""
    ):
        """Log a trade exit and calculate P&L"""
        # Read existing trades
        df = pd.read_csv(self.trades_file)
        
        # Find the most recent open trade for this symbol
        open_trades = df[(df['symbol'] == symbol) & (df['exit_price'].isna())]
        
        if open_trades.empty:
            raise ValueError(f"No open trade found for symbol: {symbol}")
        
        # Get the most recent entry
        latest_entry = open_trades.iloc[-1]
        entry_price = latest_entry['entry_price']
        quantity = latest_entry['quantity']
        action = latest_entry['action']
        
        # Calculate P&L
        if action == 'BUY':
            pnl = (exit_price - entry_price) * quantity
        else:  # SELL
            pnl = (entry_price - exit_price) * quantity
        
        pnl_percent = (pnl / (entry_price * quantity)) * 100
        
        # Update the trade record
        idx = latest_entry.name
        df.at[idx, 'exit_price'] = exit_price
        df.at[idx, 'trailing_stop'] = trailing_stop
        df.at[idx, 'pnl'] = pnl
        df.at[idx, 'pnl_percent'] = pnl_percent
        df.at[idx, 'reason'] = reason
        
        # Save updated dataframe
        df.to_csv(self.trades_file, index=False)
        
        return {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'reason': reason
        }
    
    def log_update(
        self,
        symbol: str,
        trailing_stop: float,
        current_price: float
    ):
        """Log an update to trailing stop"""
        df = pd.read_csv(self.trades_file)
        open_trades = df[(df['symbol'] == symbol) & (df['exit_price'].isna())]
        
        if not open_trades.empty:
            idx = open_trades.iloc[-1].name
            df.at[idx, 'trailing_stop'] = trailing_stop
            df.to_csv(self.trades_file, index=False)
    
    def _append_to_log(self, trade_data: Dict[str, Any]):
        """Append trade data to CSV log file"""
        df = pd.DataFrame([trade_data])
        df.to_csv(self.trades_file, mode='a', header=False, index=False)
    
    def get_daily_pnl(self, date: Optional[str] = None) -> float:
        """Get total P&L for a specific date (default: today)"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        trades_file = self.log_dir / f"trades_{date}.csv"
        if not trades_file.exists():
            return 0.0
        
        df = pd.read_csv(trades_file)
        closed_trades = df[df['pnl'].notna()]
        return closed_trades['pnl'].sum()
    
    def get_all_trades(self) -> pd.DataFrame:
        """Get all trades from log files"""
        all_trades = []
        for log_file in self.log_dir.glob("trades_*.csv"):
            df = pd.read_csv(log_file)
            all_trades.append(df)
        
        if all_trades:
            return pd.concat(all_trades, ignore_index=True)
        return pd.DataFrame()
