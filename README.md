# 🚀 Advanced Algorithmic Trading System for NSE

A production-ready, high-performance algorithmic trading bot for the Indian stock markets (NSE) using the Upstox API.

## Features

- **Multi-Regime Strategy**: Automatically switches between trending and ranging strategies
- **Advanced Risk Management**: ATR-based position sizing, dynamic stop losses, and trailing stops
- **Multi-Timeframe Confirmation**: Ensures alignment across timeframes before entry
- **Resilient Architecture**: Exponential backoff, circuit breakers, and comprehensive error handling
- **Comprehensive Backtesting**: Walk-forward optimization and detailed performance metrics
- **Production Ready**: Automated deployment with systemd/cron support

## Project Structure

```
trading_bot/
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── __init__.py
│   ├── auth.py
│   ├── market_data.py
│   ├── order_manager.py
│   ├── portfolio.py
│   └── logger.py
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── regime_classifier.py
│   ├── trending_strategy.py
│   └── ranging_strategy.py
├── risk/
│   ├── __init__.py
│   ├── position_sizing.py
│   ├── stop_loss.py
│   └── circuit_breaker.py
├── backtesting/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── backtest_engine.py
│   └── metrics.py
├── utils/
│   ├── __init__.py
│   ├── indicators.py
│   └── helpers.py
├── main.py
├── backtest.py
├── requirements.txt
└── README.md
```

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   Create a `.env` file in the project root:
   ```env
   UPSTOX_API_KEY=your_api_key
   UPSTOX_API_SECRET=your_api_secret
   UPSTOX_REDIRECT_URI=your_redirect_uri
   UPSTOX_ACCESS_TOKEN=your_access_token
   
   # Risk Parameters
   MAX_DAILY_LOSS_PERCENT=3.0
   RISK_PER_TRADE_PERCENT=1.0
   INITIAL_CAPITAL=100000
   
   # Trading Hours (IST)
   MARKET_OPEN_HOUR=9
   MARKET_OPEN_MINUTE=15
   MARKET_CLOSE_HOUR=15
   MARKET_CLOSE_MINUTE=30
   ```

3. **Run Backtest:**
   ```bash
   python backtest.py
   ```

4. **Run Live Trading:**
   ```bash
   python main.py
   ```

## Deployment

See `DEPLOYMENT.md` for detailed deployment instructions on Linux VPS, AWS EC2, or Azure VM.

## License

MIT License
