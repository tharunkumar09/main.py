"""
Backtesting Script - Run comprehensive backtests
"""
import logging
import sys
from pathlib import Path
import pandas as pd
from trading_bot.backtesting.data_loader import DataLoader
from trading_bot.backtesting.backtest_engine import BacktestEngine
from trading_bot.backtesting.metrics import PerformanceMetrics
from trading_bot.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def run_backtest(symbol: str, years: int = 20):
    """Run backtest for a single symbol"""
    logger.info(f"Running backtest for {symbol} over {years} years")
    
    # Load data
    data_loader = DataLoader()
    
    # Try to load from file first
    df = data_loader.load_data(symbol, interval="1d")
    
    if df is None or df.empty:
        logger.info(f"Data not found locally. Downloading for {symbol}...")
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        data_dict = data_loader.download_data([symbol], start_date, end_date, interval="1d")
        if symbol not in data_dict:
            logger.error(f"Failed to download data for {symbol}")
            return None
        
        df = data_dict[symbol]
    
    # Clean data
    df = data_loader.clean_data(df)
    
    if df.empty:
        logger.error(f"No data available for {symbol}")
        return None
    
    logger.info(f"Loaded {len(df)} rows of data for {symbol}")
    
    # Run backtest
    engine = BacktestEngine(
        initial_capital=settings.INITIAL_CAPITAL,
        risk_per_trade_percent=settings.RISK_PER_TRADE_PERCENT
    )
    
    results = engine.run_backtest(df, symbol)
    
    return results


def run_walk_forward_optimization(symbol: str, train_years: int = 5, test_years: int = 1):
    """
    Walk-Forward Optimization (Conceptual Implementation)
    
    This is a simplified version. A full implementation would:
    1. Split data into training and testing periods
    2. Optimize parameters on training data
    3. Test on out-of-sample data
    4. Roll forward and repeat
    """
    logger.info(f"Running walk-forward optimization for {symbol}")
    logger.warning("Walk-forward optimization is a conceptual implementation")
    
    # Load data
    data_loader = DataLoader()
    df = data_loader.load_data(symbol, interval="1d")
    
    if df is None or df.empty:
        logger.error(f"No data available for {symbol}")
        return None
    
    df = data_loader.clean_data(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Split into periods (simplified)
    total_years = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).days / 365.25
    num_periods = int((total_years - train_years) / test_years)
    
    logger.info(f"Total data: {total_years:.1f} years, {num_periods} walk-forward periods")
    
    all_results = []
    
    for i in range(num_periods):
        # Calculate date ranges
        start_idx = int(i * test_years * 252)  # Approximate trading days
        train_end_idx = start_idx + int(train_years * 252)
        test_end_idx = train_end_idx + int(test_years * 252)
        
        if test_end_idx > len(df):
            break
        
        train_data = df.iloc[start_idx:train_end_idx]
        test_data = df.iloc[train_end_idx:test_end_idx]
        
        logger.info(
            f"Period {i+1}/{num_periods}: "
            f"Train: {train_data['timestamp'].iloc[0].date()} to {train_data['timestamp'].iloc[-1].date()}, "
            f"Test: {test_data['timestamp'].iloc[0].date()} to {test_data['timestamp'].iloc[-1].date()}"
        )
        
        # Run backtest on test period (in production, optimize on train first)
        engine = BacktestEngine(
            initial_capital=settings.INITIAL_CAPITAL,
            risk_per_trade_percent=settings.RISK_PER_TRADE_PERCENT
        )
        
        results = engine.run_backtest(test_data, symbol)
        
        if results:
            all_results.append({
                'period': i + 1,
                'start_date': test_data['timestamp'].iloc[0],
                'end_date': test_data['timestamp'].iloc[-1],
                'metrics': results['metrics']
            })
    
    # Aggregate results
    if all_results:
        logger.info("\n=== Walk-Forward Optimization Results ===")
        for result in all_results:
            metrics = result['metrics']
            logger.info(
                f"Period {result['period']} ({result['start_date'].date()} to {result['end_date'].date()}): "
                f"CAGR: {metrics.get('cagr', 0):.2f}%, "
                f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}, "
                f"Max DD: {metrics.get('max_drawdown', 0):.2f}%"
            )
    
    return all_results


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run backtests for trading strategies')
    parser.add_argument('--symbol', type=str, default='RELIANCE.NS', help='Stock symbol (yfinance format)')
    parser.add_argument('--years', type=int, default=20, help='Number of years of data')
    parser.add_argument('--walk-forward', action='store_true', help='Run walk-forward optimization')
    
    args = parser.parse_args()
    
    if args.walk_forward:
        results = run_walk_forward_optimization(args.symbol, train_years=5, test_years=1)
    else:
        results = run_backtest(args.symbol, years=args.years)
        
        if results:
            # Print results
            metrics = results['metrics']
            logger.info("\n=== Backtest Results ===")
            logger.info(f"Symbol: {results['symbol']}")
            logger.info(f"CAGR: {metrics.get('cagr', 0):.2f}%")
            logger.info(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
            logger.info(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
            logger.info(f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
            logger.info(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
            logger.info(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
            logger.info(f"Total Trades: {metrics.get('total_trades', 0)}")
            logger.info(f"Total P&L: {metrics.get('total_pnl', 0):.2f}")
            
            # Plot equity and drawdown curves
            equity_curve = results['equity_curve']
            metrics_calc = PerformanceMetrics(equity_curve, settings.INITIAL_CAPITAL)
            
            output_dir = Path("./output")
            output_dir.mkdir(exist_ok=True)
            
            equity_path = output_dir / f"{args.symbol.replace('.', '_')}_equity_curve.png"
            drawdown_path = output_dir / f"{args.symbol.replace('.', '_')}_drawdown_curve.png"
            
            metrics_calc.plot_equity_curve(str(equity_path))
            metrics_calc.plot_drawdown_curve(str(drawdown_path))
            
            logger.info(f"Equity curve saved to: {equity_path}")
            logger.info(f"Drawdown curve saved to: {drawdown_path}")


if __name__ == "__main__":
    main()
