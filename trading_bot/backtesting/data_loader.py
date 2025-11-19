"""
Data Ingestion for Backtesting using yfinance
"""
import logging
from typing import List, Optional
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class DataLoader:
    """Load historical data for backtesting"""
    
    # NIFTY 50 stocks mapping (symbol -> yfinance ticker)
    NIFTY_50_STOCKS = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
        "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS", "SUNPHARMA.NS",
        "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "M&M.NS", "BAJFINANCE.NS",
        "TECHM.NS", "JSWSTEEL.NS", "TATAMOTORS.NS", "HDFC.NS", "ADANIENT.NS",
        "TATASTEEL.NS", "DIVISLAB.NS", "BAJAJFINSV.NS", "CIPLA.NS", "GRASIM.NS",
        "HINDALCO.NS", "INDUSINDBK.NS", "EICHERMOT.NS", "DRREDDY.NS", "BPCL.NS",
        "HEROMOTOCO.NS", "COALINDIA.NS", "SBILIFE.NS", "HDFCLIFE.NS", "APOLLOHOSP.NS",
        "BRITANNIA.NS", "NYKAA.NS", "ADANIPORTS.NS", "PIDILITIND.NS", "GODREJCP.NS"
    ]
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def download_data(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """
        Download historical data for multiple symbols
        
        Args:
            symbols: List of stock symbols (yfinance format, e.g., "RELIANCE.NS")
            start_date: Start date
            end_date: End date
            interval: Data interval ('1d', '1h', '1m', etc.)
        
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        
        for symbol in symbols:
            try:
                logger.info(f"Downloading data for {symbol} from {start_date.date()} to {end_date.date()}")
                
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval=interval)
                
                if df.empty:
                    logger.warning(f"No data downloaded for {symbol}")
                    continue
                
                # Standardize column names
                df.columns = [col.lower().replace(' ', '_') for col in df.columns]
                df = df.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'})
                
                # Ensure we have required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_cols):
                    logger.warning(f"Missing required columns for {symbol}")
                    continue
                
                # Reset index to make date a column
                df.reset_index(inplace=True)
                if 'date' in df.columns:
                    df.rename(columns={'date': 'timestamp'}, inplace=True)
                elif 'datetime' in df.columns:
                    df.rename(columns={'datetime': 'timestamp'}, inplace=True)
                
                # Ensure timestamp is datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Save to file
                file_path = self.data_dir / f"{symbol.replace('.', '_')}_{interval}.csv"
                df.to_csv(file_path, index=False)
                logger.info(f"Saved {len(df)} rows to {file_path}")
                
                data[symbol] = df
                
            except Exception as e:
                logger.error(f"Error downloading data for {symbol}: {e}")
                continue
        
        return data
    
    def download_nifty50_data(
        self,
        years: int = 20,
        interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        """
        Download data for NIFTY 50 stocks
        
        Args:
            years: Number of years of historical data
            interval: Data interval
        
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        return self.download_data(self.NIFTY_50_STOCKS, start_date, end_date, interval)
    
    def load_data(
        self,
        symbol: str,
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Load data from local file
        
        Args:
            symbol: Stock symbol
            interval: Data interval
        
        Returns:
            DataFrame or None if file doesn't exist
        """
        file_path = self.data_dir / f"{symbol.replace('.', '_')}_{interval}.csv"
        
        if not file_path.exists():
            logger.warning(f"Data file not found: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            return None
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare data for backtesting
        
        Args:
            df: Raw DataFrame
        
        Returns:
            Cleaned DataFrame
        """
        # Remove rows with missing values
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
        
        # Remove rows with zero volume
        df = df[df['volume'] > 0]
        
        # Ensure high >= low
        df = df[df['high'] >= df['low']]
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df
