# Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Setup Environment

```bash
# Run setup script
./setup.sh

# Activate virtual environment
source venv/bin/activate
```

### Step 2: Configure API Credentials

Edit `.env` file:

```bash
UPSTOX_API_KEY=your_api_key
UPSTOX_API_SECRET=your_api_secret
UPSTOX_ACCESS_TOKEN=your_access_token
```

### Step 3: Run Backtest (Recommended First)

```bash
python backtest.py
```

This will:
- Download historical data
- Run backtests on NIFTY 50 stocks
- Generate performance reports
- Create equity curve and drawdown charts

### Step 4: Run Live Trading (After Testing)

```bash
python main.py
```

## 📊 Understanding the Output

### Backtest Results

After running `backtest.py`, check:
- `backtest_results/results_*.json` - Performance metrics
- `backtest_results/equity_curve_*.png` - Equity curve visualization
- `backtest_results/drawdown_*.png` - Drawdown visualization

### Live Trading Logs

- `logs/trading_bot.log` - System logs
- `logs/trades_YYYYMMDD.json` - Trade entries/exits
- `logs/trades_YYYYMMDD.csv` - Trade data (for analysis)

## ⚙️ Key Configuration Options

### Risk Management

```python
# In config.py or .env
RISK_PER_TRADE = 0.01  # 1% risk per trade
MAX_DAILY_LOSS_PERCENT = 0.03  # 3% daily loss limit
CIRCUIT_BREAKER_ENABLED = True  # Auto square-off on loss limit
```

### Strategy Parameters

```python
# Trending Strategy
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
EMA_PERIOD = 200

# Regime Detection
ADX_TRENDING_THRESHOLD = 25
ADX_RANGING_THRESHOLD = 20

# Risk Management
ATR_MULTIPLIER_SL = 3.0  # Stop-loss distance
ATR_MULTIPLIER_TSL = 2.0  # Trailing stop distance
```

## 🔧 Common Tasks

### Change Symbols to Trade

Edit `main.py`:

```python
symbols = [
    "NSE_EQ|INE467B01029",  # RELIANCE
    # Add more instrument tokens
]
```

### Adjust Market Hours

Edit `config.py`:

```python
MARKET_OPEN_TIME = "09:15"
MARKET_CLOSE_TIME = "15:30"
```

### Add External Events

Edit `external_events.json`:

```json
[
  {
    "name": "RBI Policy Meeting",
    "date": "2024-12-06",
    "start_time": "10:00",
    "end_time": "12:00",
    "type": "RBI_ANNOUNCEMENT",
    "halt_trading": true
  }
]
```

## 🐳 Docker Quick Start

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📈 Performance Monitoring

### Check Portfolio Status

The bot logs portfolio summary every 5 seconds:
- Current capital
- Daily P&L
- Open positions
- Circuit breaker status

### Review Trade Performance

```bash
# View trade log
cat logs/trades_$(date +%Y%m%d).csv

# Or use pandas in Python
import pandas as pd
df = pd.read_csv('logs/trades_20241206.csv')
print(df.describe())
```

## ⚠️ Important Notes

1. **Always test in paper trading first** - Use Upstox paper trading API
2. **Start with small capital** - Test with minimum amounts initially
3. **Monitor closely** - Check logs regularly, especially during first week
4. **Understand the strategies** - Read the code to understand entry/exit logic
5. **Backtest thoroughly** - Run backtests on multiple stocks and time periods

## 🆘 Troubleshooting

### Bot Not Starting

```bash
# Check logs
tail -f logs/trading_bot.log

# Verify API credentials
python -c "from config import UPSTOX_ACCESS_TOKEN; print('Token set:', bool(UPSTOX_ACCESS_TOKEN))"
```

### No Trades Executed

- Check if market is open
- Verify symbols are correct
- Check regime classification (may be UNKNOWN)
- Review strategy signals in logs

### Connection Issues

- Verify internet connectivity
- Check Upstox API status
- Review WebSocket reconnection logs

## 📚 Next Steps

1. **Read Full Documentation** - See `README.md`
2. **Customize Strategies** - Modify strategy files in `src/strategies/`
3. **Add More Indicators** - Extend strategy logic
4. **Optimize Parameters** - Use walk-forward optimization
5. **Deploy to Production** - Follow deployment guide in README

## 💡 Tips

- Start with backtesting to understand strategy behavior
- Use walk-forward optimization to validate robustness
- Monitor drawdowns closely - they're key to risk management
- Adjust position sizing based on your risk tolerance
- Keep logs for analysis and improvement

---

**Happy Trading! 📈**
