"""
Performance Analyzer
Calculates metrics and generates visualizations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import BACKTEST_RESULTS_DIR


class PerformanceAnalyzer:
    """
    Analyzes backtest performance and generates visualizations
    """
    
    def __init__(self, results_dir: Path = None):
        """
        Initialize Performance Analyzer
        
        Args:
            results_dir: Directory to save results
        """
        self.results_dir = results_dir or BACKTEST_RESULTS_DIR
        self.results_dir.mkdir(exist_ok=True)
        
        # Set style
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
    
    def generate_report(self, results: Dict, symbol: str = None) -> str:
        """
        Generate performance report
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            
        Returns:
            Report string
        """
        symbol = symbol or results.get('symbol', 'UNKNOWN')
        
        report = f"""
{'='*80}
BACKTEST PERFORMANCE REPORT
{'='*80}
Symbol: {symbol}
Period: {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')}

CAPITAL METRICS:
  Initial Capital: ₹{results['initial_capital']:,.2f}
  Final Capital: ₹{results['final_capital']:,.2f}
  Total Return: {results['total_return']:.2f}%
  CAGR: {results['cagr']:.2f}%

TRADE STATISTICS:
  Total Trades: {results['total_trades']}
  Winning Trades: {results['winning_trades']}
  Losing Trades: {results['losing_trades']}
  Win Rate: {results['win_rate']:.2f}%

PROFITABILITY:
  Total P&L: ₹{results['total_pnl']:,.2f}
  Total Profit: ₹{results['total_profit']:,.2f}
  Total Loss: ₹{results['total_loss']:,.2f}
  Profit Factor: {results['profit_factor']:.2f}
  Average Win: ₹{results['avg_win']:,.2f}
  Average Loss: ₹{results['avg_loss']:,.2f}

RISK METRICS:
  Maximum Drawdown: {results['max_drawdown']:.2f}%
  Max DD Duration: {results['max_dd_duration']} periods
  Sharpe Ratio: {results['sharpe_ratio']:.2f}

{'='*80}
"""
        
        return report
    
    def plot_equity_curve(self, results: Dict, symbol: str = None, save: bool = True):
        """
        Plot equity curve
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            save: Whether to save the plot
        """
        if results.get('equity_curve') is None:
            logger.warning("No equity curve data available")
            return
        
        equity_curve = results['equity_curve']
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(equity_curve.index, equity_curve.values, linewidth=2, label='Equity Curve')
        ax.axhline(y=results['initial_capital'], color='r', linestyle='--', label='Initial Capital')
        ax.set_xlabel('Date')
        ax.set_ylabel('Capital (₹)')
        ax.set_title(f'Equity Curve - {symbol or results.get("symbol", "BACKTEST")}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filename = self.results_dir / f"equity_curve_{symbol or 'backtest'}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Equity curve saved to {filename}")
        
        plt.close()
    
    def plot_drawdown(self, results: Dict, symbol: str = None, save: bool = True):
        """
        Plot drawdown curve
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            save: Whether to save the plot
        """
        if results.get('equity_curve') is None:
            logger.warning("No equity curve data available")
            return
        
        equity_curve = results['equity_curve']
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak * 100
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, color='red', label='Drawdown')
        ax.plot(drawdown.index, drawdown.values, linewidth=1, color='darkred')
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown (%)')
        ax.set_title(f'Drawdown Curve - {symbol or results.get("symbol", "BACKTEST")}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            filename = self.results_dir / f"drawdown_{symbol or 'backtest'}.png"
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            logger.info(f"Drawdown curve saved to {filename}")
        
        plt.close()
    
    def plot_trade_distribution(self, results: Dict, symbol: str = None, save: bool = True):
        """
        Plot trade P&L distribution
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
            save: Whether to save the plot
        """
        # This would require access to individual trade P&L
        # For now, create a placeholder
        logger.info("Trade distribution plot not yet implemented")
    
    def generate_all_plots(self, results: Dict, symbol: str = None):
        """
        Generate all performance plots
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
        """
        self.plot_equity_curve(results, symbol)
        self.plot_drawdown(results, symbol)
    
    def save_results(self, results: Dict, symbol: str = None):
        """
        Save results to file
        
        Args:
            results: Backtest results dictionary
            symbol: Stock symbol
        """
        symbol = symbol or results.get('symbol', 'backtest')
        filename = self.results_dir / f"results_{symbol}.json"
        
        # Convert numpy types to Python types for JSON serialization
        results_copy = {}
        for k, v in results.items():
            if isinstance(v, (np.integer, np.floating)):
                results_copy[k] = float(v)
            elif isinstance(v, pd.Series):
                # Don't save Series in JSON, save separately
                continue
            else:
                results_copy[k] = v
        
        import json
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")
