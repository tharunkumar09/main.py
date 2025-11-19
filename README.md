## Upstox Algorithmic Trading System

A production-grade, regime-aware trading bot for NSE equities built on the Upstox API. The system covers live trading, advanced risk controls, historical validation, and deployment automation.

### Key Capabilities

- Modular Python 3.10+ codebase with dedicated components for authentication, data streaming, execution, portfolio/risk tracking, and trade logging.
- Multi-regime strategy layer combining RSI, MACD, EMA, Bollinger Band Width, ADX, ATR-based stops, and multi-timeframe confirmation (1/5/60-minutes).
- Automated kill switch when daily loss exceeds the configured capital percentage, plus ATR-driven initial and trailing stops per trade.
- Walk-forward ready backtesting toolkit using `yfinance` for 15–20 years of daily data and `vectorbt` for simulation, complete with equity/drawdown plots and robust metrics (CAGR, MDD, Sharpe, Sortino, win rate, profit factor).
- Deployment guidance for Linux VPS and AWS EC2/Azure VM plus automation via systemd or cron aligned to NSE trading hours (09:14–15:30 IST).

### Project Structure

```
.
├── algobot/                # Live trading modules
│   ├── auth.py             # Upstox OAuth/session lifecycle with refresh logic
│   ├── data.py             # Websocket feed handling, 1-min candles, resampling
│   ├── event_filter.py     # External macro-event kill switch
│   ├── indicators.py       # ADX, RSI, MACD, Bollinger, ATR helpers
│   ├── logging_utils.py
│   ├── main.py             # Entrypoint / dependency wiring
│   ├── models.py           # Trade dataclasses
│   ├── orders.py           # Market/limit/bracket + TWAP slicing
│   ├── portfolio.py        # Live positions & P&L snapshot
│   ├── position_sizing.py  # ATR & 1% risk sizing
│   ├── risk.py             # Circuit breaker/kill switch
│   ├── strategy.py         # Regime-switching strategy logic
│   └── trade_logger.py
├── backtesting/
│   ├── data_ingestion.py   # yfinance downloader (10 NIFTY50 names, 20y)
│   ├── backtest_engine.py  # vectorbt simulation with SL/TSL + metrics
│   └── walk_forward.py     # Walk-forward optimization scaffolding
├── config/settings.py      # Pydantic-based settings loader
├── deploy/
│   ├── automation.md       # Cron + systemd templates
│   └── deployment_guide.md # VPS / AWS / Azure instructions (Docker & bare metal)
├── scripts/run_live.py     # Convenience launcher
├── requirements.txt
└── logs/ & data/           # Runtime artifacts
```

### Quick Start

1. **Python & system packages**
   ```bash
   sudo apt update && sudo apt install -y python3.10-venv build-essential
   python3 -m venv .venv && source .venv/bin/activate
   pip install --upgrade pip && pip install -r requirements.txt
   ```

2. **Environment variables** (`.env`)
   ```
   UPSTOX_API_KEY=your_key
   UPSTOX_API_SECRET=your_secret
   UPSTOX_REDIRECT_URI=https://yourapp.com/callback
   CAPITAL_BASE=1000000
   MAX_DAILY_LOSS_PCT=0.03
   RISK_PER_TRADE_PCT=0.01
   INSTRUMENTS=RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK
   ```

3. **First-time auth**
   - Generate an authorization code through Upstox OAuth (manual step).
   - Exchange it and persist the refresh/access tokens automatically:
     ```bash
     python -m algobot.main --auth-code "<AUTHORIZATION_CODE>"
     ```

4. **Run the live bot**
   ```bash
   ./scripts/run_live.py
   ```
   Logs stream to `logs/bot.log`, trades to `logs/trades.csv`.

5. **Macro event filter (optional)**
   - Copy `data/macro_events.example.json` to `data/macro_events.json` and edit ISO timestamps to block trading windows such as RBI policy announcements or election results.

### Backtesting Workflow

```python
from backtesting.data_ingestion import download_history
from backtesting.backtest_engine import BacktestEngine

symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "ITC", "KOTAKBANK", "LT", "SBIN", "HINDUNILVR"]
history = download_history(symbols, start="2005-01-01")
engine = BacktestEngine(history)
results = engine.run()

for symbol, result in results.items():
    print(symbol, {k: round(v, 4) for k, v in result.metrics.items()})
    print("Equity:", result.equity_curve_path, "| Drawdown:", result.drawdown_curve_path)
```

- `walk_forward.py` shows how to orchestrate rolling out-of-sample windows (train 5y, validate 1y) to stress-test stability across market regimes.
- All ATR-based SL/TSL and 1% risk sizing rules used in production are replicated in the vectorbt engine for parity.

### Automation & Deployment

- **Automation**: See `deploy/automation.md` for production-ready cron (09:14–15:30 IST) and systemd units with graceful shutdown hooks and logrotate notes.
- **Deployment**: `deploy/deployment_guide.md` explains hardening on bare-metal Linux VPS, plus containerized rollouts to AWS EC2 / Azure VM (including Dockerfile guidance, secrets management, and observability tips).

### Next Steps

- Integrate a persistent instrument master (lot sizes, tick sizes) from Upstox contracts.
- Enrich the event filter with RBI calendars/News API and automatically pause trading around high-impact events.
- Extend telemetry via Prometheus/Grafana or AWS CloudWatch for latency, order rejection, and P&L drifts.
