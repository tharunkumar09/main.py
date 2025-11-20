"""
Backtesting Entry Point
Runs backtests on historical data
"""

import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

from config import BACKTEST_START_DATE, BACKTEST_END_DATE, INITIAL_CAPITAL
from src.backtesting.data_ingestion import DataIngestion
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.performance_analyzer import PerformanceAnalyzer


def main():
    """Main backtesting function"""
    logger.info("="*80)
    logger.info("Backtesting Engine Starting")
    logger.info(f"Period: {BACKTEST_START_DATE} to {BACKTEST_END_DATE}")
    logger.info("="*80)
    
    try:
        # Initialize components
        data_ingestion = DataIngestion()
        backtest_engine = BacktestEngine(initial_capital=INITIAL_CAPITAL)
        performance_analyzer = PerformanceAnalyzer()
        
        # Download data for top 10 NIFTY 50 stocks
        logger.info("Downloading historical data...")
        data = data_ingestion.download_nifty50_data(
            start_date=BACKTEST_START_DATE,
            end_date=BACKTEST_END_DATE
        )
        
        if not data:
            logger.error("No data downloaded!")
            return
        
        # Run backtests
        all_results = []
        
        for symbol, df in data.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"Running backtest for {symbol}")
            logger.info(f"{'='*80}")
            
            # Clean data
            df = data_ingestion.clean_data(df)
            
            if len(df) < 200:
                logger.warning(f"Insufficient data for {symbol}, skipping...")
                continue
            
            # Run backtest
            results = backtest_engine.run_backtest(df, symbol)
            
            # Add date range
            results['start_date'] = BACKTEST_START_DATE
            results['end_date'] = BACKTEST_END_DATE
            
            # Generate report
            report = performance_analyzer.generate_report(results, symbol)
            logger.info(report)
            
            # Generate plots
            performance_analyzer.generate_all_plots(results, symbol)
            
            # Save results
            performance_analyzer.save_results(results, symbol)
            
            all_results.append(results)
        
        # Find best performing stock
        if all_results:
            best_result = max(all_results, key=lambda x: x.get('cagr', 0))
            
            logger.info("\n" + "="*80)
            logger.info("BEST PERFORMING STOCK")
            logger.info("="*80)
            best_report = performance_analyzer.generate_report(best_result)
            logger.info(best_report)
            
            # Generate plots for best performer
            performance_analyzer.generate_all_plots(best_result, best_result['symbol'])
        
        logger.info("\nBacktesting completed!")
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
