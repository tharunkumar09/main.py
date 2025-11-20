"""
Walk-Forward Optimization
Proves strategy robustness across different market regimes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger
from datetime import datetime, timedelta

from src.backtesting.backtest_engine import BacktestEngine


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization
    Splits data into in-sample and out-of-sample periods
    """
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize Walk-Forward Optimizer
        
        Args:
            initial_capital: Initial capital for each optimization run
        """
        self.initial_capital = initial_capital
    
    def run_walk_forward(self, df: pd.DataFrame, train_period_months: int = 12,
                        test_period_months: int = 3, step_months: int = 3) -> Dict:
        """
        Run walk-forward optimization
        
        Args:
            df: Historical data DataFrame
            train_period_months: Training period in months
            test_period_months: Testing period in months
            step_months: Step size in months
            
        Returns:
            Dictionary with walk-forward results
        """
        if len(df) < 365:  # Need at least 1 year of data
            logger.warning("Insufficient data for walk-forward optimization")
            return {}
        
        # Sort by date
        df = df.sort_index()
        
        start_date = df.index[0]
        end_date = df.index[-1]
        
        results = []
        current_date = start_date
        
        logger.info(f"Starting walk-forward optimization")
        logger.info(f"Data period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Train period: {train_period_months} months")
        logger.info(f"Test period: {test_period_months} months")
        logger.info(f"Step size: {step_months} months")
        
        iteration = 0
        
        while current_date < end_date:
            iteration += 1
            
            # Calculate train and test periods
            train_start = current_date
            train_end = train_start + pd.DateOffset(months=train_period_months)
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=test_period_months)
            
            # Check if we have enough data
            if test_end > end_date:
                break
            
            # Extract train and test data
            train_data = df[(df.index >= train_start) & (df.index < train_end)]
            test_data = df[(df.index >= test_start) & (df.index < test_end)]
            
            if len(train_data) < 200 or len(test_data) < 50:
                logger.warning(f"Iteration {iteration}: Insufficient data, skipping...")
                current_date += pd.DateOffset(months=step_months)
                continue
            
            logger.info(f"\nIteration {iteration}:")
            logger.info(f"  Train: {train_start.date()} to {train_end.date()} ({len(train_data)} bars)")
            logger.info(f"  Test: {test_start.date()} to {test_end.date()} ({len(test_data)} bars)")
            
            # Run backtest on training data (for parameter optimization - simplified here)
            train_engine = BacktestEngine(initial_capital=self.initial_capital)
            train_results = train_engine.run_backtest(train_data)
            
            # Run backtest on test data
            test_engine = BacktestEngine(initial_capital=self.initial_capital)
            test_results = test_engine.run_backtest(test_data)
            
            # Store results
            iteration_result = {
                'iteration': iteration,
                'train_start': train_start.date(),
                'train_end': train_end.date(),
                'test_start': test_start.date(),
                'test_end': test_end.date(),
                'train_cagr': train_results.get('cagr', 0),
                'train_sharpe': train_results.get('sharpe_ratio', 0),
                'train_win_rate': train_results.get('win_rate', 0),
                'test_cagr': test_results.get('cagr', 0),
                'test_sharpe': test_results.get('sharpe_ratio', 0),
                'test_win_rate': test_results.get('win_rate', 0),
                'test_total_return': test_results.get('total_return', 0),
                'test_max_drawdown': test_results.get('max_drawdown', 0)
            }
            
            results.append(iteration_result)
            
            logger.info(
                f"  Train: CAGR={train_results.get('cagr', 0):.2f}%, "
                f"Sharpe={train_results.get('sharpe_ratio', 0):.2f}, "
                f"Win Rate={train_results.get('win_rate', 0):.2f}%"
            )
            logger.info(
                f"  Test: CAGR={test_results.get('cagr', 0):.2f}%, "
                f"Sharpe={test_results.get('sharpe_ratio', 0):.2f}, "
                f"Win Rate={test_results.get('win_rate', 0):.2f}%, "
                f"Return={test_results.get('total_return', 0):.2f}%, "
                f"MDD={test_results.get('max_drawdown', 0):.2f}%"
            )
            
            # Move to next period
            current_date += pd.DateOffset(months=step_months)
        
        # Calculate summary statistics
        if results:
            summary = self._calculate_summary(results)
            logger.info("\n" + "="*80)
            logger.info("WALK-FORWARD OPTIMIZATION SUMMARY")
            logger.info("="*80)
            logger.info(summary)
            
            return {
                'iterations': results,
                'summary': summary
            }
        
        return {}
    
    def _calculate_summary(self, results: List[Dict]) -> str:
        """Calculate summary statistics"""
        test_cagrs = [r['test_cagr'] for r in results]
        test_sharpes = [r['test_sharpe'] for r in results]
        test_win_rates = [r['test_win_rate'] for r in results]
        test_returns = [r['test_total_return'] for r in results]
        test_mdds = [r['test_max_drawdown'] for r in results]
        
        summary = f"""
Total Iterations: {len(results)}

TEST PERIOD STATISTICS:
  Average CAGR: {np.mean(test_cagrs):.2f}%
  Average Sharpe Ratio: {np.mean(test_sharpes):.2f}
  Average Win Rate: {np.mean(test_win_rates):.2f}%
  Average Return: {np.mean(test_returns):.2f}%
  Average Max Drawdown: {np.mean(test_mdds):.2f}%

  Best CAGR: {max(test_cagrs):.2f}%
  Worst CAGR: {min(test_cagrs):.2f}%
  Best Sharpe: {max(test_sharpes):.2f}
  Worst Sharpe: {min(test_sharpes):.2f}

CONSISTENCY:
  Positive Return Periods: {sum(1 for r in test_returns if r > 0)} / {len(results)}
  Positive CAGR Periods: {sum(1 for c in test_cagrs if c > 0)} / {len(results)}
  Win Rate > 50%: {sum(1 for w in test_win_rates if w > 50)} / {len(results)}
"""
        
        return summary
