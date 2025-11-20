"""
Walk-Forward Optimization Entry Point
"""

import sys
from pathlib import Path
from loguru import logger

sys.path.append(str(Path(__file__).parent))

from config import BACKTEST_START_DATE, BACKTEST_END_DATE, INITIAL_CAPITAL
from src.backtesting.data_ingestion import DataIngestion
from src.backtesting.walk_forward import WalkForwardOptimizer


def main():
    """Main walk-forward optimization function"""
    logger.info("="*80)
    logger.info("Walk-Forward Optimization Starting")
    logger.info("="*80)
    
    try:
        # Initialize components
        data_ingestion = DataIngestion()
        optimizer = WalkForwardOptimizer(initial_capital=INITIAL_CAPITAL)
        
        # Download data for a single stock (best performer from backtest)
        # In production, you'd select the best performer
        symbol = "RELIANCE.NS"  # Example
        
        logger.info(f"Downloading data for {symbol}...")
        data = data_ingestion.download_data(
            [symbol],
            start_date=BACKTEST_START_DATE,
            end_date=BACKTEST_END_DATE
        )
        
        if symbol not in data:
            logger.error(f"No data for {symbol}")
            return
        
        df = data[symbol]
        df = data_ingestion.clean_data(df)
        
        # Run walk-forward optimization
        results = optimizer.run_walk_forward(
            df,
            train_period_months=12,
            test_period_months=3,
            step_months=3
        )
        
        if results:
            logger.info("\nWalk-forward optimization completed successfully!")
        else:
            logger.warning("Walk-forward optimization produced no results")
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
