"""
Data Ingestion for Backtesting
Downloads and cleans historical data using yfinance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
from loguru import logger
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import DATA_DIR, NIFTY_50_SYMBOLS, BACKTEST_START_DATE, BACKTEST_END_DATE


class DataIngestion:
    """
    Downloads and processes historical market data for backtesting
    """
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize Data Ingestion
        
        Args:
            data_dir: Directory to save data
        """
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
    
    def download_data(self, symbols: List[str], start_date: str, end_date: str,
                     interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Download historical data for symbols
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1h, 1m, etc.)
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        data = {}
        
        for symbol in symbols:
            try:
                logger.info(f"Downloading data for {symbol}...")
                
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval=interval)
                
                if df.empty:
                    logger.warning(f"No data downloaded for {symbol}")
                    continue
                
                # Clean and standardize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]
                
                # Ensure required columns exist
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_cols):
                    logger.warning(f"Missing required columns for {symbol}")
                    continue
                
                # Remove rows with missing data
                df = df.dropna(subset=required_cols)
                
                # Save to file
                file_path = self.data_dir / f"{symbol.replace('.NS', '')}_{interval}.csv"
                df.to_csv(file_path)
                
                data[symbol] = df
                logger.info(f"Downloaded {len(df)} rows for {symbol}")
            
            except Exception as e:
                logger.error(f"Error downloading data for {symbol}: {e}")
                continue
        
        return data
    
    def download_nifty50_data(self, start_date: str = None, end_date: str = None,
                              interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Download NIFTY 50 data
        
        Args:
            start_date: Start date (defaults to config)
            end_date: End date (defaults to config)
            interval: Data interval
            
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        start_date = start_date or BACKTEST_START_DATE
        end_date = end_date or BACKTEST_END_DATE
        
        logger.info(f"Downloading NIFTY 50 data from {start_date} to {end_date}")
        
        return self.download_data(NIFTY_50_SYMBOLS[:10], start_date, end_date, interval)
    
    def load_data(self, symbol: str, interval: str = "1d") -> pd.DataFrame:
        """
        Load data from file
        
        Args:
            symbol: Stock symbol
            interval: Data interval
            
        Returns:
            DataFrame with historical data
        """
        file_path = self.data_dir / f"{symbol.replace('.NS', '')}_{interval}.csv"
        
        if not file_path.exists():
            logger.warning(f"Data file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            return df
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            return pd.DataFrame()
    
    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resample data to different timeframe
        
        Args:
            df: Original DataFrame
            timeframe: Target timeframe (e.g., '1H', '5T', '1D')
            
        Returns:
            Resampled DataFrame
        """
        if df.empty:
            return df
        
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        resampled = df.resample(timeframe).agg(ohlc_dict).dropna()
        return resampled
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate data
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Remove rows with zero volume
        df = df[df['volume'] > 0]
        
        # Remove rows where high < low
        df = df[df['high'] >= df['low']]
        
        # Remove rows where close is outside high-low range
        df = df[(df['close'] >= df['low']) & (df['close'] <= df['high'])]
        
        # Forward fill missing values
        df = df.fillna(method='ffill')
        
        # Remove remaining NaN rows
        df = df.dropna()
        
        return df
