#!/bin/bash

###############################################################################
# Install Trading Bot as Systemd Service
###############################################################################

set -e

echo "Installing Trading Bot as systemd service..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Copy service file
echo "Copying service file..."
cp deployment/systemd/trading-bot.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable trading-bot.service

echo "✅ Service installed successfully!"
echo
echo "Commands:"
echo "  Start:   sudo systemctl start trading-bot"
echo "  Stop:    sudo systemctl stop trading-bot"
echo "  Status:  sudo systemctl status trading-bot"
echo "  Logs:    sudo journalctl -u trading-bot -f"
echo
