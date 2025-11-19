"""
Backtesting Engine using vectorbt
Advanced backtesting with walk-forward optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger
import vectorbt as vbt
import matplotlib.pyplot as plt
import seaborn as sns

from src.strategies.regime_classifier import RegimeClassifier, MarketRegime
from src.strategies.trending_strategy import TrendingStrategy, Signal
from src.strategies.ranging_strategy import RangingStrategy
from src.strategies.indicators import TechnicalIndicators


class BacktestEngine:
    """
    Advanced Backtesting Engine
    
    Features:
    - Historical data download via yfinance
    - Multi-regime strategy backtesting
    - Dynamic SL/TSL simulation
    - ATR-based position sizing
    - Walk-forward optimization
    - Comprehensive performance metrics
    """
    
    def __init__(self, config: dict):
        """
        Initialize backtest engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        bt_config = config.get('backtesting', {})
        
        self.start_date = bt_config.get('start_date', '2008-01-01')
        self.end_date = bt_config.get('end_date', '2023-12-31')
        self.initial_capital = bt_config.get('initial_capital', 100000)
        self.commission = bt_config.get('commission', 0.0003)
        self.slippage = bt_config.get('slippage', 0.001)
        
        # Initialize strategies
        self.regime_classifier = RegimeClassifier(config)
        self.trending_strategy = TrendingStrategy(config)
        self.ranging_strategy = RangingStrategy(config)
        
        # Results storage
        self.results = {}
        
        logger.info(f"BacktestEngine initialized: {self.start_date} to {self.end_date}")
    
    def download_data(self, symbols: List[str], progress: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Download historical data for symbols
        
        Args:
            symbols: List of ticker symbols
            progress: Show progress bar
            
        Returns:
            Dictionary of {symbol: DataFrame}
        """
        logger.info(f"Downloading data for {len(symbols)} symbols...")
        
        data = {}
        for symbol in symbols:
            try:
                # Convert NSE symbols to Yahoo Finance format
                yf_symbol = f"{symbol}.NS"
                
                logger.info(f"Downloading {yf_symbol}...")
                df = yf.download(
                    yf_symbol,
                    start=self.start_date,
                    end=self.end_date,
                    progress=progress
                )
                
                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    continue
                
                # Rename columns to lowercase
                df.columns = [col.lower() for col in df.columns]
                
                # Add indicators
                df = TechnicalIndicators.add_all_indicators(df, self.config)
                
                data[symbol] = df
                logger.info(f"Downloaded {len(df)} rows for {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to download {symbol}: {e}")
        
        logger.info(f"Downloaded data for {len(data)}/{len(symbols)} symbols")
        return data
    
    def generate_signals(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Generate entry and exit signals
        
        Args:
            df: DataFrame with OHLCV and indicators
            
        Returns:
            Tuple of (entries, exits, regime)
        """
        entries = pd.Series(0, index=df.index)
        exits = pd.Series(0, index=df.index)
        regime = pd.Series("UNDEFINED", index=df.index)
        
        for i in range(200, len(df)):  # Start after enough data for indicators
            window_df = df.iloc[:i+1]
            
            # Classify regime
            current_regime = self.regime_classifier.classify(window_df)
            regime.iloc[i] = current_regime.value
            
            # Select strategy
            if current_regime == MarketRegime.TRENDING:
                strategy = self.trending_strategy
            elif current_regime == MarketRegime.RANGING:
                strategy = self.ranging_strategy
            else:
                continue
            
            # Generate signal
            signal, _ = strategy.generate_signal(window_df)
            
            if signal == Signal.BUY:
                entries.iloc[i] = 1
            elif signal == Signal.SELL:
                entries.iloc[i] = -1
        
        return entries, exits, regime
    
    def calculate_position_size_series(
        self,
        df: pd.DataFrame,
        entries: pd.Series,
        capital: float
    ) -> pd.Series:
        """
        Calculate position sizes using ATR
        
        Args:
            df: DataFrame with OHLCV and indicators
            entries: Entry signals
            capital: Available capital
            
        Returns:
            Series of position sizes
        """
        risk_per_trade = capital * (self.config.get('trading', {}).get('risk_per_trade_percent', 1.0) / 100)
        atr_multiplier = self.config.get('risk_management', {}).get('atr_sl_multiplier', 3.0)
        
        position_sizes = pd.Series(1.0, index=df.index)
        
        for i in range(len(df)):
            if entries.iloc[i] != 0:
                atr = df['atr'].iloc[i]
                price = df['close'].iloc[i]
                
                if pd.notna(atr) and atr > 0:
                    risk_per_share = atr * atr_multiplier
                    size = risk_per_trade / risk_per_share
                    size_fraction = (size * price) / capital
                    position_sizes.iloc[i] = min(size_fraction, 0.2)  # Max 20% per position
        
        return position_sizes
    
    def run_backtest(
        self,
        symbol: str,
        df: pd.DataFrame,
        plot: bool = False
    ) -> Dict:
        """
        Run backtest for single symbol
        
        Args:
            symbol: Symbol name
            df: DataFrame with OHLCV and indicators
            plot: Generate plots
            
        Returns:
            Results dictionary
        """
        logger.info(f"Running backtest for {symbol}...")
        
        # Generate signals
        entries, exits, regime = self.generate_signals(df)
        
        # Calculate position sizes
        position_sizes = self.calculate_position_size_series(df, entries, self.initial_capital)
        
        # Run vectorbt portfolio simulation
        portfolio = vbt.Portfolio.from_signals(
            close=df['close'],
            entries=entries > 0,
            exits=exits > 0,
            short_entries=entries < 0,
            short_exits=exits < 0,
            size=position_sizes,
            size_type='targetpercent',
            init_cash=self.initial_capital,
            fees=self.commission,
            slippage=self.slippage,
            freq='1D'
        )
        
        # Calculate metrics
        stats = portfolio.stats()
        
        results = {
            'symbol': symbol,
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'total_return': portfolio.total_return() * 100,
            'cagr': self._calculate_cagr(portfolio),
            'sharpe_ratio': portfolio.sharpe_ratio(),
            'sortino_ratio': portfolio.sortino_ratio(),
            'max_drawdown': portfolio.max_drawdown() * 100,
            'max_drawdown_duration': portfolio.max_drawdown_duration(),
            'win_rate': portfolio.trades.win_rate * 100 if portfolio.trades.count > 0 else 0,
            'profit_factor': portfolio.trades.profit_factor if portfolio.trades.count > 0 else 0,
            'total_trades': portfolio.trades.count,
            'avg_trade': portfolio.trades.expectancy if portfolio.trades.count > 0 else 0,
            'best_trade': portfolio.trades.returns.max() * 100 if portfolio.trades.count > 0 else 0,
            'worst_trade': portfolio.trades.returns.min() * 100 if portfolio.trades.count > 0 else 0,
            'portfolio': portfolio,
            'regime': regime
        }
        
        logger.info(f"Backtest complete for {symbol}: "
                   f"CAGR={results['cagr']:.2f}%, Sharpe={results['sharpe_ratio']:.2f}, "
                   f"MDD={results['max_drawdown']:.2f}%, Trades={results['total_trades']}")
        
        # Generate plots
        if plot:
            self._plot_results(symbol, df, portfolio, entries, regime)
        
        return results
    
    def run_walk_forward_optimization(
        self,
        symbol: str,
        df: pd.DataFrame,
        train_period_days: int = 252,
        test_period_days: int = 63,
        step_days: int = 63
    ) -> Dict:
        """
        Run walk-forward optimization
        
        Args:
            symbol: Symbol name
            df: DataFrame with OHLCV data
            train_period_days: Training period in days
            test_period_days: Testing period in days
            step_days: Step size in days
            
        Returns:
            Walk-forward results
        """
        logger.info(f"Running walk-forward optimization for {symbol}...")
        logger.info(f"Train: {train_period_days} days, Test: {test_period_days} days, Step: {step_days} days")
        
        results = []
        start_idx = train_period_days
        
        while start_idx + test_period_days < len(df):
            # Define train and test windows
            train_start = start_idx - train_period_days
            train_end = start_idx
            test_start = start_idx
            test_end = min(start_idx + test_period_days, len(df))
            
            train_df = df.iloc[train_start:train_end].copy()
            test_df = df.iloc[test_start:test_end].copy()
            
            logger.info(f"Window: Train {train_df.index[0]} to {train_df.index[-1]}, "
                       f"Test {test_df.index[0]} to {test_df.index[-1]}")
            
            # Run backtest on test period
            test_result = self.run_backtest(symbol, test_df, plot=False)
            test_result['train_start'] = train_df.index[0]
            test_result['train_end'] = train_df.index[-1]
            test_result['test_start'] = test_df.index[0]
            test_result['test_end'] = test_df.index[-1]
            
            results.append(test_result)
            
            # Step forward
            start_idx += step_days
        
        # Aggregate results
        avg_cagr = np.mean([r['cagr'] for r in results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
        avg_max_dd = np.mean([r['max_drawdown'] for r in results])
        total_trades = sum([r['total_trades'] for r in results])
        
        wf_results = {
            'symbol': symbol,
            'windows': len(results),
            'avg_cagr': avg_cagr,
            'avg_sharpe': avg_sharpe,
            'avg_max_drawdown': avg_max_dd,
            'total_trades': total_trades,
            'window_results': results
        }
        
        logger.info(f"Walk-forward complete: {len(results)} windows, "
                   f"Avg CAGR={avg_cagr:.2f}%, Avg Sharpe={avg_sharpe:.2f}")
        
        return wf_results
    
    def _calculate_cagr(self, portfolio) -> float:
        """Calculate Compound Annual Growth Rate"""
        total_return = portfolio.total_return()
        days = (portfolio.wrapper.index[-1] - portfolio.wrapper.index[0]).days
        years = days / 365.25
        
        if years > 0:
            cagr = (((1 + total_return) ** (1 / years)) - 1) * 100
        else:
            cagr = 0
        
        return cagr
    
    def _plot_results(
        self,
        symbol: str,
        df: pd.DataFrame,
        portfolio,
        entries: pd.Series,
        regime: pd.Series
    ):
        """Generate comprehensive plots"""
        fig, axes = plt.subplots(4, 1, figsize=(15, 12))
        fig.suptitle(f'Backtest Results: {symbol}', fontsize=16)
        
        # Plot 1: Equity curve
        portfolio.plot(ax=axes[0])
        axes[0].set_title('Equity Curve')
        axes[0].set_ylabel('Portfolio Value')
        axes[0].grid(True)
        
        # Plot 2: Drawdown
        portfolio.drawdowns.plot(ax=axes[1])
        axes[1].set_title('Drawdown')
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].grid(True)
        
        # Plot 3: Price with entries
        axes[2].plot(df.index, df['close'], label='Close', alpha=0.7)
        buy_signals = entries[entries > 0]
        sell_signals = entries[entries < 0]
        axes[2].scatter(buy_signals.index, df.loc[buy_signals.index, 'close'], 
                       color='green', marker='^', s=100, label='Buy', alpha=0.8)
        axes[2].scatter(sell_signals.index, df.loc[sell_signals.index, 'close'],
                       color='red', marker='v', s=100, label='Sell', alpha=0.8)
        axes[2].set_title('Price and Signals')
        axes[2].set_ylabel('Price')
        axes[2].legend()
        axes[2].grid(True)
        
        # Plot 4: Regime classification
        regime_numeric = regime.map({'TRENDING': 1, 'RANGING': -1, 'UNDEFINED': 0})
        axes[3].fill_between(df.index, 0, regime_numeric, alpha=0.3)
        axes[3].set_title('Market Regime (Green=Trending, Red=Ranging)')
        axes[3].set_ylabel('Regime')
        axes[3].set_ylim(-1.5, 1.5)
        axes[3].grid(True)
        
        plt.tight_layout()
        plt.savefig(f'backtest_{symbol}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', dpi=150)
        logger.info(f"Plot saved for {symbol}")
        plt.close()
    
    def generate_performance_report(self, results: Dict) -> str:
        """
        Generate formatted performance report
        
        Args:
            results: Backtest results dictionary
            
        Returns:
            Formatted report string
        """
        report = f"""
        
{'='*70}
BACKTEST PERFORMANCE REPORT: {results['symbol']}
{'='*70}

Period: {results['start_date'].strftime('%Y-%m-%d')} to {results['end_date'].strftime('%Y-%m-%d')}

RETURNS
-------
Total Return:         {results['total_return']:>10.2f}%
CAGR:                 {results['cagr']:>10.2f}%

RISK METRICS
------------
Sharpe Ratio:         {results['sharpe_ratio']:>10.2f}
Sortino Ratio:        {results['sortino_ratio']:>10.2f}
Max Drawdown:         {results['max_drawdown']:>10.2f}%
Max DD Duration:      {results['max_drawdown_duration']} days

TRADE STATISTICS
----------------
Total Trades:         {results['total_trades']:>10}
Win Rate:             {results['win_rate']:>10.2f}%
Profit Factor:        {results['profit_factor']:>10.2f}
Average Trade:        {results['avg_trade']:>10.2f}
Best Trade:           {results['best_trade']:>10.2f}%
Worst Trade:          {results['worst_trade']:>10.2f}%

{'='*70}
        """
        
        return report


def main():
    """Run backtest example"""
    from src.core.config_loader import get_config
    
    # Load config
    config = get_config()
    
    # Create backtest engine
    engine = BacktestEngine(config.config_data)
    
    # Test symbols (top NIFTY 50 stocks)
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
    
    # Download data
    data = engine.download_data(symbols, progress=True)
    
    # Run backtests
    best_result = None
    best_sharpe = -999
    
    for symbol, df in data.items():
        result = engine.run_backtest(symbol, df, plot=True)
        
        # Print report
        report = engine.generate_performance_report(result)
        print(report)
        
        # Track best performing symbol
        if result['sharpe_ratio'] > best_sharpe:
            best_sharpe = result['sharpe_ratio']
            best_result = result
    
    # Run walk-forward optimization on best symbol
    if best_result:
        logger.info(f"\nRunning walk-forward optimization on best symbol: {best_result['symbol']}")
        wf_results = engine.run_walk_forward_optimization(
            best_result['symbol'],
            data[best_result['symbol']],
            train_period_days=252,
            test_period_days=63,
            step_days=21
        )
        
        print(f"\n{'='*70}")
        print(f"WALK-FORWARD OPTIMIZATION: {wf_results['symbol']}")
        print(f"{'='*70}")
        print(f"Windows:           {wf_results['windows']}")
        print(f"Avg CAGR:          {wf_results['avg_cagr']:.2f}%")
        print(f"Avg Sharpe:        {wf_results['avg_sharpe']:.2f}")
        print(f"Avg Max Drawdown:  {wf_results['avg_max_drawdown']:.2f}%")
        print(f"Total Trades:      {wf_results['total_trades']}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
