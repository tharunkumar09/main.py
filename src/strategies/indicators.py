"""
Technical Indicators Module
Common technical indicators for trading strategies
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import pandas_ta as ta


class TechnicalIndicators:
    """Technical indicators calculator"""
    
    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Simple Moving Average
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for SMA
            column: Column to calculate SMA on
            
        Returns:
            SMA series
        """
        return df[column].rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for EMA
            column: Column to calculate EMA on
            
        Returns:
            EMA series
        """
        return df[column].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """
        Calculate Relative Strength Index
        
        Args:
            df: DataFrame with OHLCV data
            period: RSI period
            column: Column to calculate RSI on
            
        Returns:
            RSI series
        """
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = 'close'
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            df: DataFrame with OHLCV data
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line period
            column: Column to calculate MACD on
            
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = 'close'
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for moving average
            std_dev: Number of standard deviations
            column: Column to calculate bands on
            
        Returns:
            Tuple of (Upper band, Middle band, Lower band)
        """
        middle_band = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR period
            
        Returns:
            ATR series
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Average Directional Index (ADX)
        
        Args:
            df: DataFrame with OHLCV data
            period: ADX period
            
        Returns:
            Tuple of (ADX, +DI, -DI)
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed TR and DM
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def calculate_bb_width(df: pd.DataFrame, period: int = 20, column: str = 'close') -> pd.Series:
        """
        Calculate Bollinger Band Width
        
        Args:
            df: DataFrame with OHLCV data
            period: Period for Bollinger Bands
            column: Column to calculate on
            
        Returns:
            Bollinger Band Width series
        """
        upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(df, period, column=column)
        bb_width = (upper - lower) / middle
        return bb_width
    
    @staticmethod
    def calculate_stochastic(
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator
        
        Args:
            df: DataFrame with OHLCV data
            k_period: %K period
            d_period: %D period
            
        Returns:
            Tuple of (%K, %D)
        """
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        k = 100 * ((df['close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def calculate_supertrend(
        df: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Supertrend indicator
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR period
            multiplier: ATR multiplier
            
        Returns:
            Tuple of (Supertrend, Direction)
        """
        atr = TechnicalIndicators.calculate_atr(df, period)
        hl_avg = (df['high'] + df['low']) / 2
        
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)
        
        for i in range(1, len(df)):
            if pd.isna(supertrend.iloc[i-1]):
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                if df['close'].iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
        
        return supertrend, direction
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
        """
        Add all common indicators to DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            config: Configuration dictionary
            
        Returns:
            DataFrame with indicators added
        """
        df = df.copy()
        
        # Moving averages
        df['ema_20'] = TechnicalIndicators.calculate_ema(df, 20)
        df['ema_50'] = TechnicalIndicators.calculate_ema(df, 50)
        df['ema_200'] = TechnicalIndicators.calculate_ema(df, 200)
        
        # RSI
        rsi_period = config.get('strategy', {}).get('trending_strategy', {}).get('rsi_period', 14)
        df['rsi'] = TechnicalIndicators.calculate_rsi(df, rsi_period)
        
        # MACD
        macd_config = config.get('strategy', {}).get('trending_strategy', {})
        macd_fast = macd_config.get('macd_fast', 12)
        macd_slow = macd_config.get('macd_slow', 26)
        macd_signal = macd_config.get('macd_signal', 9)
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.calculate_macd(
            df, macd_fast, macd_slow, macd_signal
        )
        
        # Bollinger Bands
        bb_config = config.get('strategy', {}).get('ranging_strategy', {})
        bb_period = bb_config.get('bb_period', 20)
        bb_std = bb_config.get('bb_std', 2)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = TechnicalIndicators.calculate_bollinger_bands(
            df, bb_period, bb_std
        )
        df['bb_width'] = TechnicalIndicators.calculate_bb_width(df, bb_period)
        
        # ATR
        atr_period = config.get('risk_management', {}).get('atr_period', 14)
        df['atr'] = TechnicalIndicators.calculate_atr(df, atr_period)
        
        # ADX
        adx_period = config.get('strategy', {}).get('regime_detection', {}).get('adx_period', 14)
        df['adx'], df['plus_di'], df['minus_di'] = TechnicalIndicators.calculate_adx(df, adx_period)
        
        return df
