# 🚀 Advanced Algorithmic Trading System for Indian Stock Markets (NSE)

A comprehensive, production-ready algorithmic trading bot designed for the Indian stock markets using the Upstox API. This system features multi-regime strategy switching, advanced risk management, comprehensive backtesting, and robust error handling.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Deployment](#deployment)
- [Backtesting](#backtesting)
- [Performance Metrics](#performance-metrics)
- [Risk Management](#risk-management)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Core System
- ✅ **Upstox API Integration** - Full integration with Upstox API for live trading
- ✅ **Modular Architecture** - Clean, commented, and modular codebase
- ✅ **Authentication & Session Management** - Automatic token refresh with exponential backoff
- ✅ **Live Market Data Feed** - WebSocket subscription with 1-minute candle construction
- ✅ **Order Management** - Market, Limit, SL, Bracket Orders, and TWAP/VWAP for large orders
- ✅ **Portfolio & Position Manager** - Real-time P&L tracking
- ✅ **Trade Logging** - Detailed entry/exit logging with P&L, reason, and timestamps

### Resilience & Reliability
- ✅ **Advanced Error Handling** - Comprehensive try/except blocks with specific error handling
- ✅ **Reconnection Logic** - Exponential backoff for WebSocket and REST API
- ✅ **Circuit Breakers** - Automatic square-off and halt if daily loss exceeds threshold (default 3%)

### Strategy & Risk Management
- ✅ **Multi-Regime Strategy** - Automatic detection and switching between Trending and Ranging markets
- ✅ **Regime Classifier** - Uses ADX (14) and Bollinger Band Width
- ✅ **Strategy A (Trending)** - RSI (14), MACD (12, 26, 9), and 200-Day EMA
- ✅ **Strategy B (Ranging)** - Mean-reversion using Bollinger Bands
- ✅ **Multi-Timeframe Confirmation** - Entry signals confirmed by higher timeframe trend
- ✅ **Dynamic Position Sizing** - ATR-based position sizing (1% risk per trade)
- ✅ **Volatility-Adjusted Stops** - Dynamic SL (3× ATR) and Trailing SL (2× ATR)
- ✅ **External Event Filter** - Halts trading during major events (RBI announcements, elections)

### Backtesting & Validation
- ✅ **Data Ingestion** - Downloads historical data using yfinance
- ✅ **Advanced Backtesting** - Custom engine with dynamic SL/TSL and position sizing
- ✅ **Walk-Forward Optimization** - Proves strategy robustness across market regimes
- ✅ **Performance Metrics** - CAGR, Max Drawdown, Sharpe Ratio, Win Rate, Profit Factor
- ✅ **Visualizations** - Equity curve and drawdown charts

## 🏗️ Architecture

```
trading-bot/
├── src/
│   ├── auth/              # Authentication & session management
│   ├── market_data/       # Live data feed (WebSocket)
│   ├── orders/            # Order management
│   ├── portfolio/         # Portfolio & position tracking
│   ├── logging/           # Trade logging
│   ├── strategies/         # Trading strategies
│   │   ├── regime_classifier.py
│   │   ├── strategy_a_trending.py
│   │   └── strategy_b_ranging.py
│   ├── risk/              # Risk management
│   ├── core/              # Main trading bot
│   └── backtesting/       # Backtesting engine
├── deployment/            # Deployment scripts
├── config.py             # Configuration
├── main.py               # Live trading entry point
├── backtest.py           # Backtesting entry point
└── walk_forward.py       # Walk-forward optimization
```

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Upstox API credentials (API Key, Secret, Access Token)
- **For Testing:** Upstox Sandbox credentials (recommended)
- **For Production:** Upstox Production credentials + Linux VPS or AWS EC2/Azure VM

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd trading-bot
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If TA-Lib installation fails, install system dependencies first:

```bash
# Ubuntu/Debian
sudo apt-get install build-essential
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib

# macOS
brew install ta-lib
pip install TA-Lib
```

### Step 4: Configure Environment

```bash
cp .env.example .env
# Edit .env with your Upstox API credentials
```

**⚠️ Important:** For testing, use **Sandbox mode** (default). See [SANDBOX_SETUP.md](SANDBOX_SETUP.md) for detailed instructions.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Upstox API Credentials
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:3000/callback
UPSTOX_ACCESS_TOKEN=your_access_token_here

# Trading Configuration
INITIAL_CAPITAL=100000          # ₹1,00,000
RISK_PER_TRADE=0.01            # 1% per trade
MAX_DAILY_LOSS_PERCENT=0.03    # 3% daily loss limit
CIRCUIT_BREAKER_ENABLED=true

# Strategy Parameters (can be adjusted in config.py)
RSI_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
EMA_PERIOD=200
ADX_PERIOD=14
ATR_PERIOD=14
```

### Obtaining Upstox API Credentials

#### For Sandbox Testing (Recommended First):

1. **Register Sandbox Application:**
   - Visit [Upstox Developer Portal](https://account.upstox.com/developer/apps)
   - Create a new application and select **"Sandbox"** environment
   - Note your Sandbox API Key and Secret

2. **Get Access Token:**
   ```bash
   python get_token.py
   # Follow instructions to get authorization code
   python get_token.py <authorization_code>
   ```

3. **Test Connection:**
   ```bash
   python test_sandbox.py
   ```

See [SANDBOX_SETUP.md](SANDBOX_SETUP.md) for detailed sandbox setup instructions.

#### For Production:

1. **Register Production Application:**
   - Create a separate application in Upstox Developer Portal
   - Select **"Production"** environment
   - Note your Production API Key and Secret

2. **Update `.env`:**
   ```bash
   UPSTOX_SANDBOX_MODE=false
   UPSTOX_API_KEY=your_production_api_key
   UPSTOX_API_SECRET=your_production_api_secret
   ```

3. **Get Production Access Token:**
   ```bash
   python get_token.py
   ```

## 🚀 Usage

### Testing in Sandbox (Recommended First)

```bash
# 1. Test connection
python test_sandbox.py

# 2. Run backtests
python backtest.py

# 3. Start bot in sandbox mode (default)
python main.py
```

The bot will:
1. Show "SANDBOX MODE" warning (no real money)
2. Authenticate with Upstox Sandbox API
3. Connect to market data feed
4. Execute simulated trades
5. Log all trades and P&L

### Live Trading (Production)

**⚠️ WARNING: Production mode uses REAL MONEY!**

```bash
# 1. Set sandbox mode to false in .env
UPSTOX_SANDBOX_MODE=false

# 2. Use production credentials
# 3. Start bot
python main.py
```

The bot will:
1. Show "PRODUCTION MODE" warning
2. Authenticate with Upstox Production API
3. Execute real trades with real money
4. Log all trades and P&L

### Backtesting

```bash
python backtest.py
```

This will:
1. Download historical data for NIFTY 50 stocks
2. Run backtests with the configured strategies
3. Generate performance reports and visualizations
4. Save results to `backtest_results/`

### Walk-Forward Optimization

```bash
python walk_forward.py
```

This validates strategy robustness by:
1. Splitting data into train/test periods
2. Running backtests on each period
3. Calculating consistency metrics

## 🐳 Deployment

### Option 1: Docker Deployment

```bash
# Build image
docker build -t trading-bot .

# Run container
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 2: Linux VPS Deployment

#### Step 1: Transfer Files

```bash
scp -r trading-bot/ user@your-vps:/opt/
```

#### Step 2: Setup on VPS

```bash
ssh user@your-vps
cd /opt/trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 3: Configure Systemd Service

```bash
sudo cp deployment/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

#### Step 4: Configure Cron (Alternative)

```bash
# Edit crontab
crontab -e

# Add entries (see deployment/crontab.example)
14 9 * * 1-5 /opt/trading-bot/deployment/trading-bot-cron.sh start
30 15 * * 1-5 /opt/trading-bot/deployment/trading-bot-cron.sh stop
```

### Option 3: AWS EC2 / Azure VM

1. **Launch Instance:**
   - Choose Ubuntu 22.04 LTS
   - Minimum: t2.micro (for testing)
   - Recommended: t3.small or larger (for production)

2. **Security Groups:**
   - Allow SSH (port 22)
   - No need to expose web ports

3. **Follow Linux VPS Deployment steps**

4. **Optional: Use AWS Systems Manager for automation**

## 📊 Backtesting

### Running Backtests

```bash
python backtest.py
```

### Backtest Results

Results are saved in `backtest_results/`:
- `results_<symbol>.json` - Performance metrics
- `equity_curve_<symbol>.png` - Equity curve chart
- `drawdown_<symbol>.png` - Drawdown chart

### Performance Metrics

The backtest calculates:
- **CAGR** - Compound Annual Growth Rate
- **Max Drawdown** - Maximum peak-to-trough decline
- **Sharpe Ratio** - Risk-adjusted return
- **Win Rate** - Percentage of profitable trades
- **Profit Factor** - Gross profit / Gross loss
- **Sortino Ratio** - Downside risk-adjusted return

## 🛡️ Risk Management

### Position Sizing

Position size is calculated using ATR:
```
Risk Amount = Capital × Risk Per Trade (1%)
Position Size = Risk Amount / (Entry Price - Stop Loss)
```

### Stop Loss

- **Initial SL:** 3× ATR from entry price
- **Trailing SL:** 2× ATR from highest/lowest price

### Circuit Breaker

Automatically squares off all positions if:
- Daily loss exceeds configured threshold (default 3%)
- Can be disabled via `CIRCUIT_BREAKER_ENABLED=false`

## 🔍 Troubleshooting

### Common Issues

1. **Token Expired:**
   ```
   Error: Invalid or expired access token
   ```
   **Solution:** Refresh token or re-authenticate

2. **WebSocket Connection Failed:**
   ```
   Error: WebSocket connection failed
   ```
   **Solution:** Check network connectivity, verify API credentials

3. **Insufficient Data:**
   ```
   Warning: Insufficient data for backtesting
   ```
   **Solution:** Ensure historical data is downloaded, check date range

4. **TA-Lib Import Error:**
   ```
   ImportError: libta_lib.so: cannot open shared object file
   ```
   **Solution:** Install TA-Lib system library (see Installation section)

### Logs

- Live trading logs: `logs/trading_bot.log`
- Trade logs: `logs/trades_YYYYMMDD.json` and `.csv`
- Backtest logs: Console output

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for detailed logging.

## 📝 External Events

The bot can halt trading during major events. Configure events in `external_events.json`:

```json
[
  {
    "name": "RBI Monetary Policy Meeting",
    "date": "2024-12-06",
    "start_time": "10:00",
    "end_time": "12:00",
    "type": "RBI_ANNOUNCEMENT",
    "halt_trading": true
  }
]
```

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use environment variables** - Don't hardcode credentials
3. **Restrict file permissions:**
   ```bash
   chmod 600 .env
   chmod 600 .upstox_token.json
   ```
4. **Run as non-root user** - Use dedicated user account
5. **Enable firewall** - Restrict unnecessary ports

## 📈 Performance Optimization

1. **Use vectorized operations** - Already implemented in backtesting
2. **Cache indicator calculations** - Reduces computation time
3. **Optimize database queries** - If using database for logging
4. **Monitor resource usage** - Use `htop` or `top`

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ⚠️ Disclaimer

**This software is for educational and research purposes only. Trading in financial markets involves substantial risk of loss. Past performance does not guarantee future results. Always test thoroughly in a paper trading environment before using real capital.**

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Upstox API for market data and trading
- yfinance for historical data
- vectorbt and backtrader communities
- TA-Lib for technical indicators

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review logs for error messages

---

**Built with ❤️ for the Indian Stock Market**
