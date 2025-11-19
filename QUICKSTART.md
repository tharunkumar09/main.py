# 🚀 Quick Start Guide

This guide will get you trading in 15 minutes!

## 📋 Prerequisites Checklist

- [ ] Python 3.10+ installed
- [ ] Upstox account with API access
- [ ] API key and secret from Upstox Developer Portal
- [ ] Linux/Mac system (Ubuntu 20.04+ recommended)

---

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip build-essential libta-lib-dev

# Install Python packages
pip install -r requirements.txt
```

### Step 2: Configure Credentials

```bash
# Copy environment template
cp .env.example .env

# Edit with your Upstox credentials
nano .env
```

Add your credentials:
```bash
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_ACCESS_TOKEN=your_access_token_here
CAPITAL=100000
```

### Step 3: Configure Strategy (Optional)

The default configuration in `config/config.yaml` is production-ready, but you can customize:

```yaml
trading:
  capital: 100000
  max_daily_loss_percent: 3.0
  risk_per_trade_percent: 1.0
  max_positions: 5
  trading_mode: "paper"  # Change to "live" when ready
```

---

## 🧪 Test the System

### 1. Run Backtest First

**Always backtest before going live!**

```bash
python3 backtesting/backtest_engine.py
```

This will:
- Download historical data for top NIFTY 50 stocks
- Run backtests for 15-20 years
- Show performance metrics
- Generate equity curves
- Run walk-forward optimization

**Look for:**
- ✅ CAGR > 10%
- ✅ Sharpe Ratio > 1.5
- ✅ Max Drawdown < 25%
- ✅ Win Rate > 55%

### 2. Paper Trading Test

```bash
# Set trading_mode to "paper" in config/config.yaml
python3 src/bot.py
```

Monitor for:
- ✅ WebSocket connection successful
- ✅ Candles building correctly
- ✅ Signals generating
- ✅ No errors in logs

---

## 🔴 Go Live (When Ready)

### Option 1: Manual Start

```bash
# Change trading_mode to "live" in config/config.yaml
python3 src/bot.py
```

### Option 2: Systemd Service (Recommended)

```bash
# Install as system service
sudo bash scripts/install_service.sh

# Start service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View live logs
sudo journalctl -u trading-bot -f
```

### Option 3: Docker

```bash
cd deployment/docker
docker-compose up -d

# View logs
docker-compose logs -f trading-bot
```

---

## 📊 Monitor Performance

### Check Portfolio Status

```bash
# View logs
tail -f logs/trading_*.log

# Check positions via Upstox dashboard
# https://upstox.com/
```

### Key Metrics to Watch

1. **Daily P&L**: Should stay within ±3%
2. **Open Positions**: Max 5 positions
3. **Win Rate**: Target 55-65%
4. **Circuit Breaker**: Should remain CLOSED

---

## 🚨 Emergency Stop

If you need to stop trading immediately:

```bash
# Kill the bot
pkill -f "python3.*bot.py"

# Or stop service
sudo systemctl stop trading-bot

# Or manually trigger circuit breaker
# (Implement manual override in bot interface)
```

All positions will be automatically squared off when the bot stops.

---

## ⚙️ Configuration Checklist

Before going live, verify:

- [ ] Correct Upstox credentials in `.env`
- [ ] `trading_mode: "live"` in `config.yaml`
- [ ] Capital amount is correct
- [ ] Max daily loss set appropriately (default 3%)
- [ ] Risk per trade set (default 1%)
- [ ] Watchlist contains desired symbols
- [ ] Market hours configured for IST
- [ ] Logs directory exists and is writable
- [ ] Sufficient disk space for logs and data

---

## 🎯 First Trade Checklist

When you see your first trade:

1. **Verify Entry**:
   - [ ] Signal was valid (check logs)
   - [ ] Entry price is reasonable
   - [ ] Stop loss is set correctly
   - [ ] Position size matches risk calculation

2. **Monitor Position**:
   - [ ] Trailing stop is updating
   - [ ] Position appears in Upstox dashboard
   - [ ] P&L is tracking correctly

3. **Exit**:
   - [ ] Exit reason is logged
   - [ ] P&L is calculated correctly
   - [ ] Trade appears in history

---

## 🔧 Troubleshooting

### Bot Won't Start

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check dependencies
pip install -r requirements.txt

# Check logs
cat logs/trading_*.log
```

### Authentication Errors

```bash
# Verify credentials
cat .env | grep UPSTOX

# Get new access token from Upstox
# (Tokens expire after 24 hours)
```

### No Signals Generated

```bash
# Check if market is open
date  # Should be weekday, 9:15-15:30 IST

# Check data feed
tail -f logs/trading_*.log | grep "WebSocket"

# Check regime classification
# Market might be in UNDEFINED regime (skip trading)
```

### Circuit Breaker Triggered

```bash
# Check reason
cat logs/trading_*.log | grep "CIRCUIT BREAKER"

# Common causes:
# - Daily loss limit hit (3%)
# - Too many API errors
# - Rapid drawdown detected

# Reset after cooldown period (30 minutes)
```

---

## 📞 Getting Help

1. **Check logs**: `logs/trading_*.log`
2. **Review configuration**: `config/config.yaml`
3. **Consult documentation**: `README.md`
4. **Upstox API docs**: https://upstox.com/developer/

---

## ⚠️ Safety Reminders

- **Start small**: Begin with minimum capital to test
- **Monitor daily**: Check bot status daily for first week
- **Paper trade first**: Run in paper mode for at least 1 week
- **Set limits**: Never exceed 3% daily loss limit
- **Stay informed**: Be aware of major market events
- **Regular reviews**: Review performance weekly
- **Emergency plan**: Know how to stop the bot immediately

---

## 🎓 Learning Path

1. **Week 1**: Paper trading, monitor signals
2. **Week 2**: Go live with small capital
3. **Week 3**: Gradually increase capital
4. **Week 4**: Optimize based on results
5. **Month 2+**: Fine-tune strategies

---

## 📈 Success Metrics

After 1 month of live trading, you should see:

- ✅ Positive total P&L
- ✅ Win rate around 55-60%
- ✅ Max drawdown < 10%
- ✅ Circuit breaker never triggered
- ✅ Consistent daily performance

If not meeting these metrics:
1. Review backtest results
2. Check signal quality in logs
3. Verify risk management is working
4. Consider adjusting strategy parameters

---

**You're ready! Good luck trading! 🚀**

*Remember: Start small, monitor closely, and scale gradually.*
