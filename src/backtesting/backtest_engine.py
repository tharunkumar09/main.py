"""
Backtesting Engine
Uses vectorbt for efficient vectorized backtesting
Includes dynamic SL/TSL and position sizing
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from datetime import datetime

try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    logger.warning("vectorbt not available, using simplified backtesting")

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.strategies.regime_classifier import RegimeClassifier
from src.strategies.strategy_a_trending import StrategyA_Trending
from src.strategies.strategy_b_ranging import StrategyB_Ranging
from src.risk.risk_manager import RiskManager


class BacktestEngine:
    """
    Backtesting engine with support for dynamic SL/TSL and position sizing
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize Backtest Engine
        
        Args:
            initial_capital: Initial capital for backtesting
        """
        self.initial_capital = initial_capital
        self.regime_classifier = RegimeClassifier()
        self.strategy_a = StrategyA_Trending()
        self.strategy_b = StrategyB_Ranging()
        self.risk_manager = RiskManager(initial_capital=initial_capital)
        
        self.trades: List[Dict] = []
        self.equity_curve: pd.Series = None
    
    def run_backtest(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol (optional)
            
        Returns:
            Dictionary with backtest results
        """
        if df.empty or len(df) < 200:
            logger.warning("Insufficient data for backtesting")
            return self._empty_results()
        
        logger.info(f"Running backtest on {len(df)} rows")
        
        # Reset state
        self.trades = []
        capital = self.initial_capital
        position = None
        equity_curve = [capital]
        
        # Process each bar
        for i in range(200, len(df)):  # Start after enough data for indicators
            current_df = df.iloc[:i+1]
            current_bar = df.iloc[i]
            current_price = current_bar['close']
            
            # Classify regime
            regime_result = self.regime_classifier.classify_regime(current_df)
            regime = regime_result['regime']
            
            if regime == 'UNKNOWN':
                equity_curve.append(capital)
                continue
            
            # Generate signals
            if regime == 'TRENDING':
                signal = self.strategy_a.generate_signals(current_df)
            else:
                signal = self.strategy_b.generate_signals(current_df)
            
            # Manage existing position
            if position:
                position = self._update_position(
                    position, current_bar, current_df, signal, regime
                )
                
                # Check exit conditions
                if position['status'] == 'CLOSED':
                    capital = self._close_position(position, capital, current_price)
                    self.trades.append(position.copy())
                    position = None
            
            # Evaluate new entry
            if not position and signal['signal'] != 'HOLD':
                position = self._open_position(
                    current_df, current_bar, signal, regime, capital
                )
            
            # Update equity curve
            if position:
                unrealized_pnl = self._calculate_unrealized_pnl(position, current_price)
                equity_curve.append(capital + unrealized_pnl)
            else:
                equity_curve.append(capital)
        
        # Close any remaining position
        if position and position['status'] == 'OPEN':
            capital = self._close_position(position, capital, df.iloc[-1]['close'])
            self.trades.append(position)
        
        self.equity_curve = pd.Series(equity_curve, index=df.index[:len(equity_curve)])
        
        # Calculate performance metrics
        results = self._calculate_metrics(capital, symbol)
        
        return results
    
    def _open_position(self, df: pd.DataFrame, bar: pd.Series, signal: Dict,
                      regime: str, capital: float) -> Dict:
        """Open a new position"""
        side = signal['side']
        entry_price = bar['close']
        
        # Calculate stop-loss
        stop_loss = self.risk_manager.calculate_stop_loss(df, entry_price, side)
        
        # Calculate position size
        position_size, risk_amount = self.risk_manager.calculate_position_size(
            entry_price, stop_loss, capital
        )
        
        # Calculate target
        target = self.risk_manager.calculate_target(df, entry_price, stop_loss, side)
        
        position = {
            'symbol': 'BACKTEST',
            'side': side,
            'quantity': position_size,
            'entry_price': entry_price,
            'entry_time': bar.name if hasattr(bar, 'name') else len(df) - 1,
            'stop_loss': stop_loss,
            'target': target,
            'highest_price': entry_price if side == 'BUY' else entry_price,
            'lowest_price': entry_price if side == 'SELL' else entry_price,
            'regime': regime,
            'status': 'OPEN'
        }
        
        return position
    
    def _update_position(self, position: Dict, bar: pd.Series, df: pd.DataFrame,
                        signal: Dict, regime: str) -> Dict:
        """Update position (trailing stop, exit conditions)"""
        current_price = bar['close']
        side = position['side']
        
        # Update highest/lowest price
        if side == 'BUY':
            position['highest_price'] = max(position['highest_price'], current_price)
        else:
            position['lowest_price'] = min(position['lowest_price'], current_price)
        
        # Calculate trailing stop
        highest_for_tsl = position['highest_price'] if side == 'BUY' else position['lowest_price']
        trailing_stop = self.risk_manager.calculate_trailing_stop(
            df, position['entry_price'], highest_for_tsl, side
        )
        
        # Check exit conditions
        if side == 'BUY':
            if current_price <= trailing_stop:
                position['status'] = 'CLOSED'
                position['exit_reason'] = 'Trailing stop-loss'
            elif current_price >= position['target']:
                position['status'] = 'CLOSED'
                position['exit_reason'] = 'Target reached'
        else:  # SELL
            if current_price >= trailing_stop:
                position['status'] = 'CLOSED'
                position['exit_reason'] = 'Trailing stop-loss'
            elif current_price <= position['target']:
                position['status'] = 'CLOSED'
                position['exit_reason'] = 'Target reached'
        
        # Check opposite signal
        if signal['signal'] != 'HOLD' and signal['side'] != side:
            position['status'] = 'CLOSED'
            position['exit_reason'] = f"Opposite signal: {signal['side']}"
        
        return position
    
    def _close_position(self, position: Dict, capital: float, exit_price: float) -> float:
        """Close position and update capital"""
        if position['side'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['quantity']
        else:
            pnl = (position['entry_price'] - exit_price) * position['quantity']
        
        position['exit_price'] = exit_price
        position['pnl'] = pnl
        position['pnl_percent'] = (pnl / (position['entry_price'] * position['quantity'])) * 100
        
        capital += pnl
        
        return capital
    
    def _calculate_unrealized_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if position['side'] == 'BUY':
            return (current_price - position['entry_price']) * position['quantity']
        else:
            return (position['entry_price'] - current_price) * position['quantity']
    
    def _calculate_metrics(self, final_capital: float, symbol: str = None) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return self._empty_results()
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl', 0) < 0]
        
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        total_profit = sum(t.get('pnl', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Returns
        total_return = (final_capital - self.initial_capital) / self.initial_capital
        
        # Calculate CAGR
        if self.equity_curve is not None and len(self.equity_curve) > 1:
            days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
            years = days / 365.25
            if years > 0:
                cagr = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100
            else:
                cagr = 0
        else:
            cagr = 0
        
        # Calculate drawdown
        if self.equity_curve is not None:
            peak = self.equity_curve.expanding().max()
            drawdown = (self.equity_curve - peak) / peak * 100
            max_drawdown = drawdown.min()
            
            # Drawdown duration
            in_drawdown = drawdown < 0
            drawdown_periods = []
            start = None
            for i, is_dd in enumerate(in_drawdown):
                if is_dd and start is None:
                    start = i
                elif not is_dd and start is not None:
                    drawdown_periods.append(i - start)
                    start = None
            if start is not None:
                drawdown_periods.append(len(in_drawdown) - start)
            max_dd_duration = max(drawdown_periods) if drawdown_periods else 0
        else:
            max_drawdown = 0
            max_dd_duration = 0
        
        # Sharpe Ratio (simplified)
        if self.equity_curve is not None and len(self.equity_curve) > 1:
            returns = self.equity_curve.pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'symbol': symbol or 'BACKTEST',
            'initial_capital': self.initial_capital,
            'final_capital': final_capital,
            'total_return': total_return * 100,
            'cagr': cagr,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'profit_factor': profit_factor,
            'avg_win': total_profit / len(winning_trades) if winning_trades else 0,
            'avg_loss': total_loss / len(losing_trades) if losing_trades else 0,
            'max_drawdown': max_drawdown,
            'max_dd_duration': max_dd_duration,
            'sharpe_ratio': sharpe_ratio,
            'equity_curve': self.equity_curve
        }
    
    def _empty_results(self) -> Dict:
        """Return empty results dictionary"""
        return {
            'symbol': 'BACKTEST',
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital,
            'total_return': 0,
            'cagr': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'total_profit': 0,
            'total_loss': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'max_drawdown': 0,
            'max_dd_duration': 0,
            'sharpe_ratio': 0,
            'equity_curve': None
        }
