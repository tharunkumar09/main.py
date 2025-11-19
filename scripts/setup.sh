#!/bin/bash

###############################################################################
# Algorithmic Trading Bot - Setup Script
# 
# This script sets up the trading bot on a fresh Ubuntu/Debian system
###############################################################################

set -e

echo "============================================"
echo "Algorithmic Trading Bot - Setup"
echo "============================================"
echo

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Please do not run as root. Run as a regular user with sudo privileges."
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.10+
echo "🐍 Installing Python 3.10..."
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install system dependencies
echo "📚 Installing system dependencies..."
sudo apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    wget \
    git \
    libta-lib-dev \
    libssl-dev \
    libffi-dev

# Install TA-Lib
echo "📊 Installing TA-Lib..."
if [ ! -f /usr/local/lib/libta_lib.so ]; then
    cd /tmp
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
    sudo ldconfig
fi

# Create virtual environment
echo "🔧 Creating Python virtual environment..."
cd /workspace
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p config
mkdir -p deployment

# Copy example config if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env file with your Upstox API credentials"
fi

# Set permissions
echo "🔒 Setting permissions..."
chmod +x scripts/*.sh
chmod 600 .env

echo
echo "============================================"
echo "✅ Setup Complete!"
echo "============================================"
echo
echo "Next Steps:"
echo "1. Edit .env file with your Upstox API credentials"
echo "2. Review and customize config/config.yaml"
echo "3. Run backtests: python3 backtesting/backtest_engine.py"
echo "4. Start bot: python3 src/bot.py"
echo
echo "For deployment:"
echo "- Systemd: sudo bash scripts/install_service.sh"
echo "- Cron: crontab deployment/cron/trading-bot.cron"
echo "- Docker: cd deployment/docker && docker-compose up -d"
echo
