# 🚀 Advanced Algorithmic Trading System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Production-ready algorithmic trading bot for Indian stock markets (NSE) using Upstox API**

A sophisticated, multi-strategy algorithmic trading system featuring regime detection, multi-timeframe analysis, ATR-based risk management, and comprehensive backtesting with walk-forward optimization.

---

## 📋 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)  
- [Core Components](#-core-components)
- [Strategies](#-strategies)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Backtesting](#-backtesting)
- [Deployment](#-deployment)
- [Risk Management](#-risk-management)
- [Disclaimer](#️-disclaimer)

---

## ✨ Features

### 🎯 Core Trading System

- **Multi-Regime Strategy Switching**: Automatically detects trending vs. ranging markets using ADX and Bollinger Band Width
- **Dual Strategy Approach**:
  - **Strategy A (Trending)**: RSI, MACD, and 200-EMA based trend-following
  - **Strategy B (Ranging)**: Bollinger Bands mean-reversion
- **Multi-Timeframe Confirmation**: Validates signals across multiple timeframes (e.g., 1-min entry with 60-min trend confirmation)

### 🛡️ Advanced Risk Management

- **ATR-Based Position Sizing**: Risk exactly 1% of capital per trade
- **Dynamic Stop Loss**: 3× ATR initial stop loss
- **Trailing Stop Loss**: 2.5× ATR trailing stop from peak price
- **Risk-Reward Validation**: Minimum 2:1 risk-reward ratio enforced
- **Circuit Breaker (Kill Switch)**:
  - Automatic halt on 3% daily loss
  - Detection of rapid drawdowns
  - API error monitoring
  - External event awareness

### 🔌 Robust API Integration

- **Upstox API Client** with:
  - Automatic token refresh logic
  - Exponential backoff retry mechanism
  - Circuit breaker pattern
  - Comprehensive error handling (401, 429, 500+ errors)

### 📊 Order Execution

- **Order Types**: Market, Limit, Stop Loss, Bracket Orders
- **Smart Execution**:
  - TWAP (Time-Weighted Average Price) for large orders
  - VWAP (Volume-Weighted Average Price) execution
  - Order slicing to minimize market impact

### 📈 Market Data

- **WebSocket-based live feed** with:
  - Real-time tick data
  - 1-minute candle construction
  - Automatic reconnection with exponential backoff
  - Multi-symbol subscription

### 🧪 Backtesting & Optimization

- **Vectorbt-powered backtesting** with:
  - Historical data from yfinance (15-20 years)
  - Dynamic SL/TSL simulation
  - ATR-based position sizing
- **Walk-Forward Optimization**: Validates strategy robustness across market regimes
- **Comprehensive Metrics**: CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate, Profit Factor

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING BOT ORCHESTRATOR                  │
│                        (src/bot.py)                          │
└────────────┬────────────────────────────────────┬───────────┘
             │                                    │
    ┌────────▼────────┐                  ┌────────▼────────┐
    │  MARKET DATA    │                  │  STRATEGY       │
    │  FEED           │                  │  ENGINE         │
    │  (WebSocket)    │                  │                 │
    │  • Live Ticks   │                  │ • Regime        │
    │  • Candles      │                  │   Classifier    │
    └────────┬────────┘                  │ • Trending      │
             │                           │   Strategy      │
    ┌────────▼────────┐                  │ • Ranging       │
    │  INDICATORS     │◄─────────────────┤   Strategy      │
    │  • RSI, MACD    │                  │ • MTF Analyzer  │
    │  • ADX, BB      │                  └────────┬────────┘
    │  • ATR, EMA     │                           │
    └─────────────────┘                  ┌────────▼────────┐
                                         │  RISK           │
                                         │  MANAGER        │
             ┌───────────────────────────┤  • Position     │
             │                           │    Sizing       │
    ┌────────▼────────┐                  │  • SL/TSL       │
    │  ORDER          │                  │  • RR Ratio     │
    │  MANAGER        │                  └────────┬────────┘
    │  • Market       │                           │
    │  • Limit        │                  ┌────────▼────────┐
    │  • Bracket      │                  │  CIRCUIT        │
    │  • TWAP/VWAP    │                  │  BREAKER        │
    └────────┬────────┘                  │  • Daily Loss   │
             │                           │  • Drawdown     │
    ┌────────▼────────┐                  │  • API Errors   │
    │  PORTFOLIO      │◄─────────────────┴─────────────────┘
    │  MANAGER        │
    │  • Positions    │
    │  • P&L          │
    │  • Trades       │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  UPSTOX API     │
    │  CLIENT         │
    │  • Auth         │
    │  • Orders       │
    │  • Positions    │
    └─────────────────┘
```

---

## 🔧 Core Components

### 1. **Configuration Loader** (`src/core/config_loader.py`)
- YAML and .env configuration management
- Pydantic-based validation
- Centralized settings access

### 2. **Upstox API Client** (`src/core/upstox_client.py`)
- OAuth authentication
- Exponential backoff retry
- Circuit breaker protection
- Rate limit handling

### 3. **Market Data Feed** (`src/core/market_data_feed.py`)
- WebSocket connection management
- Real-time candle construction
- Automatic reconnection

### 4. **Order Manager** (`src/core/order_manager.py`)
- Multi-order-type support
- TWAP/VWAP execution
- Order tracking and history

### 5. **Portfolio Manager** (`src/core/portfolio_manager.py`)
- Real-time position tracking
- P&L calculation
- Trade logging

### 6. **Risk Manager** (`src/risk/risk_manager.py`)
- ATR-based position sizing
- Dynamic SL/TSL calculation
- Risk-reward validation

### 7. **Circuit Breaker** (`src/risk/circuit_breaker.py`)
- Multiple trigger conditions
- Automatic position square-off
- Cooldown period management

---

## 📊 Strategies

### Strategy A: Trending Markets (RSI + MACD + EMA)

**Entry Conditions (BUY)**:
- Price > 200 EMA (long-term uptrend)
- 30 < RSI < 70 (not overbought/oversold)
- MACD line crosses above signal line
- MACD histogram > 0

**Entry Conditions (SELL)**:
- Price < 200 EMA (long-term downtrend)
- 30 < RSI < 70
- MACD line crosses below signal line
- MACD histogram < 0

### Strategy B: Ranging Markets (Bollinger Bands Mean-Reversion)

**Entry Conditions (BUY)**:
- Price touches lower Bollinger Band
- RSI < 30 (oversold)
- Price < BB Middle

**Entry Conditions (SELL)**:
- Price touches upper Bollinger Band
- RSI > 70 (overbought)
- Price > BB Middle

### Regime Classification

Uses **ADX (14)** and **Bollinger Band Width**:
- **Trending**: ADX > 25
- **Ranging**: ADX < 20
- **Undefined**: 20 ≤ ADX ≤ 25 (skip trading)

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Ubuntu 20.04+ (recommended) or macOS/Windows
- Upstox account with API access

### Quick Setup

```bash
# Clone repository
git clone https://github.com/yourusername/algo-trading-bot.git
cd algo-trading-bot

# Run setup script (Linux/Mac)
bash scripts/setup.sh

# Or manually:
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and configure environment
cp .env.example .env
nano .env  # Edit with your Upstox credentials

# 3. Configure trading parameters
nano config/config.yaml
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# Upstox API Credentials
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:8080/callback
UPSTOX_ACCESS_TOKEN=your_access_token_here

# Trading Configuration
CAPITAL=100000
MAX_DAILY_LOSS_PERCENT=3.0
RISK_PER_TRADE_PERCENT=1.0
MAX_POSITIONS=5
```

---

## 🎮 Usage

### Running the Bot

**Development/Testing:**
```bash
python3 src/bot.py
```

**Production (Systemd):**
```bash
# Install as service
sudo bash scripts/install_service.sh

# Start service
sudo systemctl start trading-bot

# Check status
sudo systemctl status trading-bot

# View logs
sudo journalctl -u trading-bot -f
```

**Docker:**
```bash
cd deployment/docker
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## 🧪 Backtesting

### Run Backtest

```bash
python3 backtesting/backtest_engine.py
```

### Example Output

```
======================================================================
BACKTEST PERFORMANCE REPORT: RELIANCE
======================================================================

Period: 2008-01-01 to 2023-12-31

RETURNS
-------
Total Return:         324.56%
CAGR:                  12.45%

RISK METRICS
------------
Sharpe Ratio:           1.89
Sortino Ratio:          2.34
Max Drawdown:          18.32%
Max DD Duration:       127 days

TRADE STATISTICS
----------------
Total Trades:           342
Win Rate:              58.77%
Profit Factor:          2.14
======================================================================
```

---

## 🚢 Deployment

### Option 1: Linux VPS

```bash
bash scripts/setup.sh
sudo bash scripts/install_service.sh
sudo systemctl start trading-bot
```

### Option 2: AWS EC2

```bash
bash scripts/deploy_aws.sh <EC2_PUBLIC_IP> ~/.ssh/your-key.pem
```

### Option 3: Docker

```bash
cd deployment/docker
docker-compose up -d
```

---

## 🛡️ Risk Management

### Position Sizing Formula

**Position Size** = (Capital × Risk%) / (Entry Price - Stop Loss)

### Stop Loss Calculation

- **Initial SL**: Entry Price ± (3 × ATR)
- **Trailing SL**: Peak Price ∓ (2.5 × ATR)

### Circuit Breaker Triggers

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Daily Loss | 3% of capital | Square off all + halt |
| Consecutive Losses | 5 in a row | Square off all + halt |
| Rapid Drawdown | 2% in 5 min | Square off all + halt |
| API Errors | 10 errors | Halt trading |

---

## ⚠️ Disclaimer

**IMPORTANT: This software is for educational purposes only.**

- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- The authors are not responsible for any financial losses
- Test thoroughly in paper trading mode before going live
- Consult with a financial advisor before trading
- Ensure compliance with local regulations

---

## 📂 Project Structure

```
algo-trading-bot/
├── src/
│   ├── core/          # Core trading system components
│   ├── strategies/    # Trading strategies
│   ├── risk/          # Risk management
│   └── bot.py         # Main bot orchestrator
├── backtesting/       # Backtesting engine
├── deployment/        # Deployment configs
│   ├── systemd/
│   ├── cron/
│   └── docker/
├── scripts/           # Setup and deployment scripts
├── config/            # Configuration files
├── requirements.txt
└── README.md
```

---

## 🙏 Acknowledgments

- [Upstox](https://upstox.com/) for API access
- [vectorbt](https://vectorbt.dev/) for backtesting framework
- [TA-Lib](https://ta-lib.org/) for technical indicators
- The open-source trading community

---

**Built with ❤️ for algorithmic traders**

*Remember: The best strategy is the one you understand and can stick to consistently.*
