# Quick Start Guide

## 1. Installation

```bash
# Clone or download the project
cd trading_bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

Create a `.env` file in the project root:

```env
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_REDIRECT_URI=http://localhost:3000/callback
UPSTOX_ACCESS_TOKEN=your_access_token

MAX_DAILY_LOSS_PERCENT=3.0
RISK_PER_TRADE_PERCENT=1.0
INITIAL_CAPITAL=100000
```

**Getting Upstox API Credentials:**

1. Register at https://upstox.com/
2. Go to Developer Dashboard
3. Create a new app
4. Get API Key and Secret
5. Set redirect URI
6. Complete OAuth flow to get access token

## 3. Run Backtest

Test the strategy with historical data:

```bash
# Backtest a single stock
python backtest.py --symbol RELIANCE.NS --years 5

# Run walk-forward optimization
python backtest.py --symbol RELIANCE.NS --years 10 --walk-forward
```

This will:
- Download historical data (if not available)
- Run backtest with the strategy
- Calculate performance metrics
- Generate equity and drawdown curves

## 4. Run Live Trading (Paper Trading First!)

**⚠️ IMPORTANT: Start with paper trading or small amounts!**

```bash
# Update symbols in main.py (use actual Upstox instrument keys)
# Then run:
python main.py
```

The bot will:
- Connect to Upstox API
- Subscribe to market data
- Monitor for trading signals
- Execute trades based on strategy
- Manage risk with stop losses
- Log all trades

## 5. Monitor Trading

```bash
# View application logs
tail -f trading_bot.log

# View trade logs
ls -lh logs/trades/
cat logs/trades/trades_YYYYMMDD.csv
```

## 6. Key Features

### Multi-Regime Strategy
- Automatically detects trending vs ranging markets
- Switches strategies accordingly

### Risk Management
- ATR-based position sizing
- Dynamic stop losses
- Trailing stop losses
- Circuit breaker (kill switch)

### Backtesting
- Historical data from yfinance
- Performance metrics (CAGR, Sharpe, Max DD, etc.)
- Equity and drawdown curves

## 7. Next Steps

1. **Test thoroughly** with backtests before live trading
2. **Start small** with minimal capital
3. **Monitor closely** during initial runs
4. **Review logs** regularly
5. **Adjust parameters** based on performance

## 8. Troubleshooting

### Authentication Issues
- Verify `.env` file has correct credentials
- Check if access token has expired
- Re-authenticate if needed

### No Market Data
- Check WebSocket connection
- Verify instrument keys are correct
- Ensure market is open

### Import Errors
- Activate virtual environment
- Reinstall dependencies: `pip install -r requirements.txt`

## 9. Production Deployment

See `DEPLOYMENT.md` for detailed deployment instructions on:
- Linux VPS
- AWS EC2
- Azure VM
- Docker

## 10. Support

- Review logs in `logs/` directory
- Check Upstox API documentation
- Review code comments for implementation details
