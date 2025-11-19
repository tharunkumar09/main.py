# System Architecture

## Overview

This is a production-ready algorithmic trading system for the Indian stock markets (NSE) using the Upstox API. The system implements a multi-regime strategy that automatically adapts to market conditions.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Trading Bot Main                        │
│                         (main.py)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│ Market Data  │ │   Order     │ │ Portfolio  │
│    Feed      │ │  Manager    │ │  Manager   │
└───────┬──────┘ └──────┬───────┘ └─────┬──────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
│  Strategies  │ │    Risk     │ │ Backtest  │
│              │ │ Management  │ │  Engine   │
└──────────────┘ └─────────────┘ └───────────┘
```

## Core Components

### 1. Authentication (`core/auth.py`)
- OAuth 2.0 flow with Upstox
- Automatic token refresh
- Session management

### 2. Market Data Feed (`core/market_data.py`)
- WebSocket connection for live data
- 1-minute candle construction
- Historical data fetching
- Exponential backoff reconnection

### 3. Order Management (`core/order_manager.py`)
- Market orders
- Limit orders
- Stop loss orders
- Bracket orders
- TWAP/VWAP order slicing
- Order modification and cancellation

### 4. Portfolio Manager (`core/portfolio.py`)
- Real-time position tracking
- P&L calculation
- Margin management
- Position squaring (for circuit breaker)

### 5. Trade Logger (`core/logger.py`)
- Detailed trade logging
- Entry/exit tracking
- P&L calculation
- CSV-based storage

## Strategy Components

### 1. Regime Classifier (`strategies/regime_classifier.py`)
- ADX-based trend detection
- Bollinger Band Width analysis
- Classifies: TRENDING, RANGING, UNCERTAIN

### 2. Trending Strategy (`strategies/trending_strategy.py`)
- RSI (14) for overbought/oversold
- MACD (12, 26, 9) for momentum
- 200-Day EMA for trend filter
- Entry: RSI < 30, MACD bullish cross, Price > 200-EMA

### 3. Ranging Strategy (`strategies/ranging_strategy.py`)
- Mean-reversion approach
- Bollinger Bands for support/resistance
- RSI confirmation
- Entry: Price near lower BB + RSI < 30

## Risk Management

### 1. Position Sizing (`risk/position_sizing.py`)
- ATR-based position sizing
- Risk percentage per trade (default: 1%)
- Dynamic quantity calculation

### 2. Stop Loss Manager (`risk/stop_loss.py`)
- ATR-based initial stop loss (3x ATR)
- Trailing stop loss
- Volatility-adjusted stops

### 3. Circuit Breaker (`risk/circuit_breaker.py`)
- Daily loss monitoring
- Automatic position squaring
- Kill switch functionality
- Threshold: 3% of capital (configurable)

## Backtesting

### 1. Data Loader (`backtesting/data_loader.py`)
- yfinance integration
- NIFTY 50 stock data
- Data cleaning and preparation

### 2. Backtest Engine (`backtesting/backtest_engine.py`)
- Historical simulation
- Position sizing simulation
- Stop loss simulation
- Trade tracking

### 3. Performance Metrics (`backtesting/metrics.py`)
- CAGR calculation
- Sharpe and Sortino ratios
- Maximum drawdown
- Win rate and profit factor
- Equity and drawdown curve plotting

## Utilities

### 1. Indicators (`utils/indicators.py`)
- RSI, MACD, EMA, SMA
- ATR, ADX
- Bollinger Bands
- All indicators calculated from scratch

### 2. Helpers (`utils/helpers.py`)
- Market hours checking
- IST timezone handling
- Symbol formatting
- Lot size rounding

## Data Flow

### Live Trading Flow

1. **Market Data Feed** receives ticks via WebSocket
2. **Candle Construction** builds 1-minute candles
3. **Regime Classifier** analyzes market condition
4. **Strategy Selection** chooses trending or ranging strategy
5. **Signal Generation** produces BUY/SELL/HOLD
6. **Multi-Timeframe Check** confirms higher timeframe trend
7. **Position Sizing** calculates quantity based on ATR
8. **Order Execution** places order via Order Manager
9. **Position Tracking** monitors via Portfolio Manager
10. **Stop Loss Management** updates trailing stops
11. **Trade Logging** records all actions
12. **Circuit Breaker** monitors daily loss

### Backtesting Flow

1. **Data Loader** fetches historical data
2. **Data Cleaning** prepares OHLCV data
3. **Indicator Calculation** computes all technical indicators
4. **Regime Classification** for each period
5. **Strategy Execution** generates signals
6. **Position Simulation** tracks virtual positions
7. **Stop Loss Simulation** applies ATR-based stops
8. **Metrics Calculation** computes performance
9. **Visualization** generates equity and drawdown curves

## Key Features

### Resilience
- Exponential backoff for API retries
- WebSocket reconnection logic
- Comprehensive error handling
- Circuit breaker for risk control

### Risk Management
- Dynamic position sizing
- Volatility-adjusted stops
- Multi-timeframe confirmation
- Daily loss limits

### Strategy Adaptability
- Automatic regime detection
- Strategy switching
- Confidence scoring
- Signal filtering

### Production Ready
- Systemd service support
- Cron job automation
- Comprehensive logging
- Deployment documentation

## Configuration

All configuration is managed through:
- `.env` file for secrets and parameters
- `config/settings.py` for application settings
- Environment variables override defaults

## External Dependencies

- **Upstox API**: Live trading and market data
- **yfinance**: Historical data for backtesting
- **pandas/numpy**: Data processing
- **vectorbt/backtrader**: Backtesting engines (optional)
- **matplotlib/seaborn**: Visualization

## Security Considerations

1. **Credentials**: Stored in `.env` (never committed)
2. **Token Management**: Automatic refresh
3. **Error Handling**: Prevents credential exposure
4. **Circuit Breaker**: Prevents catastrophic losses

## Scalability

The system is designed to:
- Handle multiple symbols simultaneously
- Process high-frequency tick data
- Manage multiple positions
- Scale to cloud infrastructure

## Monitoring

- Application logs: `trading_bot.log`
- Trade logs: `logs/trades/trades_YYYYMMDD.csv`
- System logs: `/var/log/trading-bot/` (production)

## Future Enhancements

1. Database integration for trade logs
2. Real-time dashboard
3. Machine learning for regime classification
4. Advanced order types (Iceberg, etc.)
5. Multi-asset support (Futures, Options)
6. Portfolio optimization
7. Real-time performance monitoring
