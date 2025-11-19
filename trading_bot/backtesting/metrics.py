"""
Performance Metrics Calculation
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("darkgrid")


class PerformanceMetrics:
    """Calculate comprehensive performance metrics"""
    
    def __init__(self, equity_curve: pd.Series, initial_capital: float):
        """
        Args:
            equity_curve: Series of portfolio values over time
            initial_capital: Initial capital
        """
        self.equity_curve = equity_curve
        self.initial_capital = initial_capital
        self.returns = equity_curve.pct_change().dropna()
    
    def calculate_cagr(self) -> float:
        """Calculate Compound Annual Growth Rate"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        final_value = self.equity_curve.iloc[-1]
        initial_value = self.equity_curve.iloc[0]
        
        if initial_value <= 0:
            return 0.0
        
        # Calculate number of years
        days = (self.equity_curve.index[-1] - self.equity_curve.index[0]).days
        years = days / 365.25
        
        if years <= 0:
            return 0.0
        
        cagr = ((final_value / initial_value) ** (1 / years) - 1) * 100
        return cagr
    
    def calculate_max_drawdown(self) -> tuple[float, pd.Timestamp, pd.Timestamp]:
        """
        Calculate Maximum Drawdown and duration
        
        Returns:
            tuple: (max_drawdown_percent, start_date, end_date)
        """
        if self.equity_curve.empty:
            return 0.0, None, None
        
        # Calculate running maximum
        running_max = self.equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = (self.equity_curve - running_max) / running_max * 100
        
        # Find maximum drawdown
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        
        # Find start of drawdown (peak before max drawdown)
        peak_idx = running_max[:max_dd_idx].idxmax()
        
        return abs(max_dd_value), peak_idx, max_dd_idx
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe Ratio"""
        if len(self.returns) == 0:
            return 0.0
        
        excess_returns = self.returns - (risk_free_rate / 252)  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0.0
        
        sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return sharpe
    
    def calculate_sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino Ratio (only considers downside deviation)"""
        if len(self.returns) == 0:
            return 0.0
        
        excess_returns = self.returns - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        sortino = np.sqrt(252) * excess_returns.mean() / downside_returns.std()
        return sortino
    
    def calculate_win_rate(self, trades: pd.DataFrame) -> float:
        """Calculate win rate from trades"""
        if trades.empty or 'pnl' not in trades.columns:
            return 0.0
        
        winning_trades = trades[trades['pnl'] > 0]
        total_trades = len(trades[trades['pnl'].notna()])
        
        if total_trades == 0:
            return 0.0
        
        return (len(winning_trades) / total_trades) * 100
    
    def calculate_profit_factor(self, trades: pd.DataFrame) -> float:
        """Calculate Profit Factor"""
        if trades.empty or 'pnl' not in trades.columns:
            return 0.0
        
        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def get_all_metrics(self, trades: Optional[pd.DataFrame] = None) -> Dict:
        """Calculate all performance metrics"""
        metrics = {
            'cagr': self.calculate_cagr(),
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'sortino_ratio': self.calculate_sortino_ratio(),
        }
        
        max_dd, dd_start, dd_end = self.calculate_max_drawdown()
        metrics['max_drawdown'] = max_dd
        metrics['drawdown_start'] = dd_start
        metrics['drawdown_end'] = dd_end
        
        if trades is not None:
            metrics['win_rate'] = self.calculate_win_rate(trades)
            metrics['profit_factor'] = self.calculate_profit_factor(trades)
            metrics['total_trades'] = len(trades[trades['pnl'].notna()])
            metrics['winning_trades'] = len(trades[trades['pnl'] > 0])
            metrics['losing_trades'] = len(trades[trades['pnl'] < 0])
            metrics['total_pnl'] = trades['pnl'].sum()
        
        return metrics
    
    def plot_equity_curve(self, save_path: Optional[str] = None):
        """Plot equity curve"""
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve.index, self.equity_curve.values, linewidth=2)
        plt.title('Equity Curve', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Portfolio Value', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
    
    def plot_drawdown_curve(self, save_path: Optional[str] = None):
        """Plot drawdown curve"""
        running_max = self.equity_curve.expanding().max()
        drawdown = (self.equity_curve - running_max) / running_max * 100
        
        plt.figure(figsize=(12, 6))
        plt.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red')
        plt.plot(drawdown.index, drawdown.values, linewidth=2, color='red')
        plt.title('Drawdown Curve', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Drawdown (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        else:
            plt.show()
        
        plt.close()
