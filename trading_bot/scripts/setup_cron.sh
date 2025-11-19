#!/bin/bash
# Setup script for cron-based trading bot execution

# This script sets up a cron job to start the trading bot at market open
# and stop it at market close

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_DIR/venv/bin/python"
MAIN_SCRIPT="$PROJECT_DIR/main.py"
LOG_DIR="/var/log/trading-bot"

# Create log directory if it doesn't exist
sudo mkdir -p $LOG_DIR
sudo chown $USER:$USER $LOG_DIR

# Create a wrapper script that activates venv and runs main.py
WRAPPER_SCRIPT="$PROJECT_DIR/run_bot.sh"
cat > $WRAPPER_SCRIPT << EOF
#!/bin/bash
cd $PROJECT_DIR
source venv/bin/activate
python main.py >> $LOG_DIR/cron.log 2>&1
EOF

chmod +x $WRAPPER_SCRIPT

# Add cron jobs
(crontab -l 2>/dev/null; echo "# Trading Bot - Start at 9:14 AM IST (market opens at 9:15 AM)"; echo "14 9 * * 1-5 $WRAPPER_SCRIPT") | crontab -
(crontab -l 2>/dev/null; echo "# Trading Bot - Stop at 3:30 PM IST (market closes at 3:30 PM)"; echo "30 15 * * 1-5 pkill -f 'python main.py'") | crontab -

echo "Cron jobs installed successfully!"
echo "View cron jobs with: crontab -l"
echo "View logs at: $LOG_DIR/cron.log"
