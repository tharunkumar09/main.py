#!/bin/bash

###############################################################################
# Deploy Trading Bot to AWS EC2
#
# Prerequisites:
# - AWS CLI configured
# - EC2 instance running Ubuntu 20.04+
# - Security group allowing SSH (port 22)
###############################################################################

set -e

# Configuration
EC2_HOST="${1:-}"
KEY_FILE="${2:-~/.ssh/aws-trading-bot.pem}"
REMOTE_USER="ubuntu"
REMOTE_DIR="/home/ubuntu/trading-bot"

if [ -z "$EC2_HOST" ]; then
    echo "Usage: $0 <EC2_PUBLIC_IP> [SSH_KEY_FILE]"
    echo "Example: $0 54.123.45.67 ~/.ssh/my-key.pem"
    exit 1
fi

echo "============================================"
echo "Deploying to AWS EC2: $EC2_HOST"
echo "============================================"
echo

# Test SSH connection
echo "Testing SSH connection..."
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$EC2_HOST" "echo 'Connection successful'"

# Create remote directory
echo "Creating remote directory..."
ssh -i "$KEY_FILE" "$REMOTE_USER@$EC2_HOST" "mkdir -p $REMOTE_DIR"

# Copy files
echo "Copying files to EC2..."
rsync -avz -e "ssh -i $KEY_FILE" \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'logs/*' \
    --exclude 'data/*' \
    . "$REMOTE_USER@$EC2_HOST:$REMOTE_DIR/"

# Run setup script
echo "Running setup on EC2..."
ssh -i "$KEY_FILE" "$REMOTE_USER@$EC2_HOST" << 'ENDSSH'
cd /home/ubuntu/trading-bot
bash scripts/setup.sh
ENDSSH

echo
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo
echo "Connect to your instance:"
echo "  ssh -i $KEY_FILE $REMOTE_USER@$EC2_HOST"
echo
echo "Configure the bot:"
echo "  1. Edit .env with API credentials"
echo "  2. Review config/config.yaml"
echo "  3. Install as service: sudo bash scripts/install_service.sh"
echo "  4. Start service: sudo systemctl start trading-bot"
echo
