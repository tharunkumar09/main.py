#!/bin/bash
# Setup script for Algorithmic Trading Bot

set -e

echo "=========================================="
echo "Algorithmic Trading Bot Setup"
echo "=========================================="

# Check Python version
echo "Checking Python version..."
python3 --version | grep -q "Python 3.1[0-9]" || {
    echo "Error: Python 3.10+ required"
    exit 1
}

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create directories
echo "Creating necessary directories..."
mkdir -p logs data backtest_results

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your Upstox API credentials"
else
    echo ".env file already exists"
fi

# Create external events file if it doesn't exist
if [ ! -f "external_events.json" ]; then
    echo "External events file will be created on first run"
fi

echo ""
echo "=========================================="
echo "Setup completed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Upstox API credentials"
echo "2. Run: source venv/bin/activate"
echo "3. For backtesting: python backtest.py"
echo "4. For live trading: python main.py"
echo ""
