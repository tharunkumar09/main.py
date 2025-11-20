#!/bin/bash
# Trading Bot Cron Script
# Starts bot at market open and stops at market close

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="/opt/trading-bot"
VENV_DIR="$BOT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
MAIN_SCRIPT="$BOT_DIR/main.py"

# Log file
LOG_FILE="$BOT_DIR/logs/cron.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to start bot
start_bot() {
    log "Starting trading bot..."
    cd "$BOT_DIR"
    nohup "$PYTHON" "$MAIN_SCRIPT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$BOT_DIR/trading_bot.pid"
    log "Trading bot started with PID $(cat $BOT_DIR/trading_bot.pid)"
}

# Function to stop bot
stop_bot() {
    if [ -f "$BOT_DIR/trading_bot.pid" ]; then
        PID=$(cat "$BOT_DIR/trading_bot.pid")
        if ps -p "$PID" > /dev/null 2>&1; then
            log "Stopping trading bot (PID: $PID)..."
            kill "$PID"
            rm "$BOT_DIR/trading_bot.pid"
            log "Trading bot stopped"
        else
            log "Trading bot process not found"
            rm "$BOT_DIR/trading_bot.pid"
        fi
    else
        log "No PID file found, bot may not be running"
    fi
}

# Check command line argument
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0
