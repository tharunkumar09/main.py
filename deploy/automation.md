## Automation Playbook

This document captures two complementary approaches to run the live trading bot strictly during NSE market hours (09:14–15:30 IST) with automatic recovery and graceful shutdown.

---

### 1. Cron-Based Scheduling

1. **Wrapper script**

   Create `scripts/cron_wrapper.sh` (already included) or similar to activate the virtual environment and start the bot:

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   cd /opt/upstox-bot
   source .venv/bin/activate
   ./scripts/run_live.py >> logs/cron.log 2>&1
   ```

2. **Crontab entries (IST)**

   ```
   # Start at 09:14 IST every trading day
   14 9 * * 1-5 TZ=Asia/Kolkata /opt/upstox-bot/scripts/cron_wrapper.sh

   # Force-stop at 15:30 IST (SIGTERM -> graceful shutdown)
   30 15 * * 1-5 TZ=Asia/Kolkata pkill -f scripts/run_live.py || true
   ```

3. **Pros / Cons**

| Pros | Cons |
| --- | --- |
| Simple, no root privileges needed | No automatic restart on crash mid-session |
| Easy to stagger multiple strategies | Harder to monitor lifecycle |

Add health checks (e.g., `pgrep -f algobot.main` with alerts) to mitigate the lack of a supervisor.

---

### 2. systemd Service (Recommended)

1. **Environment file `/etc/upstox-bot.env`**

   ```
   UPSTOX_API_KEY=...
   UPSTOX_API_SECRET=...
   UPSTOX_REDIRECT_URI=...
   CAPITAL_BASE=1000000
   MAX_DAILY_LOSS_PCT=0.03
   # ... other overrides
   ```

2. **Unit file `/etc/systemd/system/upstox-bot.service`**

   ```
   [Unit]
   Description=Upstox Regime-Aware Trading Bot
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=trader
   WorkingDirectory=/opt/upstox-bot
   EnvironmentFile=/etc/upstox-bot.env
   ExecStart=/opt/upstox-bot/.venv/bin/python -m algobot.main
   Restart=on-failure
   RestartSec=10
   KillSignal=SIGINT
   TimeoutStopSec=60
   StandardOutput=append:/opt/upstox-bot/logs/systemd.log
   StandardError=append:/opt/upstox-bot/logs/systemd.log

   [Install]
   WantedBy=multi-user.target
   ```

3. **Timer for market hours** (`/etc/systemd/system/upstox-bot.timer`)

   ```
   [Unit]
   Description=Start bot during NSE market hours (IST)

   [Timer]
   OnCalendar=Mon..Fri 09:14:00 Asia/Kolkata
   Persistent=true

   [Install]
   WantedBy=timers.target
   ```

   Add a complementary stop timer:

   ```
   [Timer]
   OnCalendar=Mon..Fri 15:30:00 Asia/Kolkata
   Unit=upstox-bot-stop.service
   ```

   Where `upstox-bot-stop.service` simply runs `ExecStart=/usr/bin/systemctl stop upstox-bot.service`.

4. **Lifecycle commands**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now upstox-bot.timer
   sudo systemctl enable upstox-bot-stop.timer
   sudo systemctl status upstox-bot.service
   ```

5. **Log management**

   - Use `logrotate` for `/opt/upstox-bot/logs/*.log`.
   - Ship logs to ELK/CloudWatch/Log Analytics for retention and alerting (critical for kill-switch triggers).

---

### Monitoring Hooks

- Export Prometheus metrics (latency, order rejects, kill switch state) via a lightweight FastAPI sidecar.
- Configure alerts for:
  - **Kill switch activation** (daily loss > limit).
  - **Websocket reconnects > N/min**.
  - **Cron/systemd failures** (non-zero exit codes).
  - **No trade events** during regime triggers (detect stuck logic).

These automation patterns ensure deterministic market-hour execution while still allowing manual intervention when macro event filters (RBI announcements, election results, etc.) demand a trading halt.
