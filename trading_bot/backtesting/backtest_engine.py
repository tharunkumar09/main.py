"""
Advanced Backtesting Engine with vectorbt
"""
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import vectorbt as vbt
from trading_bot.strategies.regime_classifier import RegimeClassifier
from trading_bot.strategies.trending_strategy import TrendingStrategy
from trading_bot.strategies.ranging_strategy import RangingStrategy
from trading_bot.risk.position_sizing import PositionSizer
from trading_bot.risk.stop_loss import StopLossManager
from trading_bot.utils.indicators import calculate_all_indicators
from trading_bot.backtesting.metrics import PerformanceMetrics

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Comprehensive backtesting engine"""
    
    def __init__(
        self,
        initial_capital: float = 100000,
        risk_per_trade_percent: float = 1.0
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade_percent = risk_per_trade_percent
        
        # Initialize components
        self.regime_classifier = RegimeClassifier()
        self.trending_strategy = TrendingStrategy()
        self.ranging_strategy = RangingStrategy()
        self.position_sizer = PositionSizer(initial_capital, risk_per_trade_percent)
        self.stop_loss_manager = StopLossManager()
        
        # Track trades
        self.trades: List[Dict] = []
        self.equity_curve: List[float] = []
        self.dates: List[datetime] = []
    
    def run_backtest(
        self,
        df: pd.DataFrame,
        symbol: str,
        use_multi_timeframe: bool = True
    ) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol
            use_multi_timeframe: Whether to use multi-timeframe confirmation
        
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest for {symbol}")
        
        # Prepare data
        df = calculate_all_indicators(df.copy())
        df = df.dropna().reset_index(drop=True)
        
        if df.empty:
            logger.error("No data available for backtest")
            return {}
        
        # Initialize tracking
        capital = self.initial_capital
        position = None  # {symbol, entry_price, quantity, stop_loss, trailing_stop, highest_price, lowest_price}
        self.trades = []
        self.equity_curve = [capital]
        self.dates = [df['timestamp'].iloc[0]]
        
        # Process each bar
        for i in range(len(df)):
            current_bar = df.iloc[i]
            current_price = current_bar['close']
            current_date = current_bar['timestamp']
            
            # Get data up to current bar
            historical_data = df.iloc[:i+1]
            
            # Update equity curve
            if position:
                # Calculate current portfolio value
                position_value = position['quantity'] * current_price
                cash = capital - (position['entry_price'] * position['quantity'])
                portfolio_value = cash + position_value
                self.equity_curve.append(portfolio_value)
            else:
                self.equity_curve.append(capital)
            
            self.dates.append(current_date)
            
            # Check stop loss if in position
            if position:
                # Update trailing stop
                atr = current_bar.get('atr', 0)
                if pd.notna(atr) and atr > 0:
                    updated_tsl = self.stop_loss_manager.update_trailing_stop(
                        symbol,
                        position['entry_price'],
                        current_price,
                        atr,
                        position,
                        is_long=True
                    )
                    
                    if updated_tsl:
                        position['trailing_stop'] = updated_tsl
                
                # Check if stop loss hit
                stop_loss = position.get('trailing_stop') or position.get('stop_loss')
                if stop_loss and self.stop_loss_manager.should_exit_on_stop_loss(
                    current_price, stop_loss, is_long=True
                ):
                    # Exit position
                    exit_price = stop_loss
                    pnl = (exit_price - position['entry_price']) * position['quantity']
                    capital += position['quantity'] * exit_price
                    
                    self.trades.append({
                        'symbol': symbol,
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'quantity': position['quantity'],
                        'pnl': pnl,
                        'pnl_percent': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                        'reason': 'Stop Loss'
                    })
                    
                    position = None
                    continue
            
            # Classify regime
            regime = self.regime_classifier.classify_regime(historical_data)
            
            # Generate signal based on regime
            if regime == "TRENDING":
                signal, signal_data = self.trending_strategy.generate_signal(
                    historical_data, current_price
                )
            elif regime == "RANGING":
                signal, signal_data = self.ranging_strategy.generate_signal(
                    historical_data, current_price
                )
            else:
                signal = "HOLD"
                signal_data = {}
            
            # Multi-timeframe confirmation (simplified - would need higher timeframe data)
            if use_multi_timeframe and signal != "HOLD":
                # In a real implementation, you would fetch higher timeframe data here
                # For now, we'll skip this check
                pass
            
            # Execute signal if not in position
            if signal == "BUY" and position is None:
                # Calculate position size
                atr = current_bar.get('atr', 0)
                if pd.notna(atr) and atr > 0:
                    stop_loss = self.stop_loss_manager.calculate_initial_stop_loss(
                        current_price, atr, is_long=True
                    )
                    
                    quantity, risk_amount, _ = self.position_sizer.calculate_position_size_from_atr(
                        current_price, atr
                    )
                    
                    # Check if we have enough capital
                    required_capital = quantity * current_price
                    if required_capital <= capital:
                        # Enter position
                        position = {
                            'symbol': symbol,
                            'entry_price': current_price,
                            'quantity': quantity,
                            'stop_loss': stop_loss,
                            'trailing_stop': stop_loss,
                            'highest_price': current_price,
                            'lowest_price': current_price,
                            'entry_date': current_date,
                            'regime': regime,
                            'strategy': signal_data.get('strategy', regime)
                        }
                        
                        capital -= required_capital
                        logger.debug(f"Entered position: {quantity} shares at {current_price}")
            
            elif signal == "SELL" and position:
                # Exit position
                exit_price = current_price
                pnl = (exit_price - position['entry_price']) * position['quantity']
                capital += position['quantity'] * exit_price
                
                self.trades.append({
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': current_date,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'quantity': position['quantity'],
                    'pnl': pnl,
                    'pnl_percent': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                    'reason': 'Signal Exit'
                })
                
                position = None
        
        # Close any remaining position at end
        if position:
            final_price = df['close'].iloc[-1]
            pnl = (final_price - position['entry_price']) * position['quantity']
            capital += position['quantity'] * final_price
            
            self.trades.append({
                'symbol': symbol,
                'entry_date': position['entry_date'],
                'exit_date': df['timestamp'].iloc[-1],
                'entry_price': position['entry_price'],
                'exit_price': final_price,
                'quantity': position['quantity'],
                'pnl': pnl,
                'pnl_percent': (pnl / (position['entry_price'] * position['quantity'])) * 100,
                'reason': 'End of Data'
            })
        
        # Calculate final metrics
        equity_series = pd.Series(self.equity_curve, index=self.dates[:len(self.equity_curve)])
        trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        
        metrics_calculator = PerformanceMetrics(equity_series, self.initial_capital)
        metrics = metrics_calculator.get_all_metrics(trades_df)
        
        return {
            'symbol': symbol,
            'metrics': metrics,
            'trades': trades_df,
            'equity_curve': equity_series,
            'final_capital': capital
        }
