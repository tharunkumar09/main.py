# Deployment Guide

This guide provides step-by-step instructions for deploying the trading bot on various platforms.

## Prerequisites

- Python 3.10 or higher
- Upstox API credentials
- Linux-based system (for production deployment)

## 1. Local Setup

### Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create a `.env` file in the project root:

```env
UPSTOX_API_KEY=your_api_key_here
UPSTOX_API_SECRET=your_api_secret_here
UPSTOX_REDIRECT_URI=http://localhost:3000/callback
UPSTOX_ACCESS_TOKEN=your_access_token_here

MAX_DAILY_LOSS_PERCENT=3.0
RISK_PER_TRADE_PERCENT=1.0
INITIAL_CAPITAL=100000

MARKET_OPEN_HOUR=9
MARKET_OPEN_MINUTE=15
MARKET_CLOSE_HOUR=15
MARKET_CLOSE_MINUTE=30

LOG_LEVEL=INFO
LOG_FILE=trading_bot.log
```

### Step 3: Test Backtest

```bash
python backtest.py --symbol RELIANCE.NS --years 5
```

## 2. Linux VPS Deployment

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Create project directory
mkdir -p ~/trading_bot
cd ~/trading_bot
```

### Step 2: Deploy Code

```bash
# Clone or copy your code
# git clone <your-repo> .
# OR copy files manually

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Environment

Create `.env` file with your credentials (see Local Setup).

### Step 4: Set Up Systemd Service

Create `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=Trading Bot Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/trading_bot
Environment="PATH=/home/your_username/trading_bot/venv/bin"
ExecStart=/home/your_username/trading_bot/venv/bin/python /home/your_username/trading_bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-bot/output.log
StandardError=append:/var/log/trading-bot/error.log

[Install]
WantedBy=multi-user.target
```

Create log directory:

```bash
sudo mkdir -p /var/log/trading-bot
sudo chown your_username:your_username /var/log/trading-bot
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service
sudo systemctl start trading-bot.service
sudo systemctl status trading-bot.service
```

### Step 5: Set Up Cron Job (Alternative to Systemd)

If you prefer cron over systemd, create a cron job:

```bash
crontab -e
```

Add the following lines:

```cron
# Start trading bot at 9:14 AM IST (market opens at 9:15 AM)
14 9 * * 1-5 cd /home/your_username/trading_bot && source venv/bin/activate && python main.py >> /var/log/trading-bot/cron.log 2>&1 &

# Stop trading bot at 3:30 PM IST (market closes at 3:30 PM)
30 15 * * 1-5 pkill -f "python main.py"
```

Note: The cron approach requires a more sophisticated script to handle the bot lifecycle. Consider using systemd for better process management.

## 3. AWS EC2 Deployment

### Step 1: Launch EC2 Instance

1. Launch an EC2 instance (Ubuntu 22.04 LTS recommended)
2. Configure security group to allow SSH (port 22)
3. Allocate Elastic IP (optional but recommended)

### Step 2: Connect and Setup

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Follow Linux VPS setup steps (Step 1-3)
```

### Step 3: Configure Security Group

Ensure your EC2 security group allows:
- Outbound HTTPS (443) for API calls
- Outbound WebSocket (443) for market data

### Step 4: Set Up Systemd Service

Follow the same systemd setup as Linux VPS (Step 4).

### Step 5: Monitor and Logs

```bash
# View logs
sudo journalctl -u trading-bot.service -f

# Or view log files
tail -f /var/log/trading-bot/output.log
tail -f /var/log/trading-bot/error.log
```

## 4. Azure VM Deployment

### Step 1: Create VM

1. Create a Linux VM (Ubuntu Server 22.04 LTS)
2. Configure Network Security Group (NSG) to allow SSH
3. Allocate static public IP

### Step 2: Connect and Setup

```bash
# SSH into VM
ssh azureuser@your-vm-ip

# Follow Linux VPS setup steps
```

### Step 3: Configure NSG Rules

Allow outbound HTTPS (443) and WebSocket (443) traffic.

### Step 4: Set Up Systemd Service

Follow the same systemd setup as Linux VPS.

## 5. Docker Deployment (Optional)

### Step 1: Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run application
CMD ["python", "main.py"]
```

### Step 2: Create docker-compose.yml

```yaml
version: '3.8'

services:
  trading-bot:
    build: .
    container_name: trading-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - trading-network

networks:
  trading-network:
    driver: bridge
```

### Step 3: Build and Run

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

## 6. Monitoring and Maintenance

### View Logs

```bash
# Systemd service logs
sudo journalctl -u trading-bot.service -f

# Application logs
tail -f trading_bot.log

# Trade logs
ls -lh logs/trades/
```

### Check Status

```bash
# Systemd service status
sudo systemctl status trading-bot.service

# Check if process is running
ps aux | grep "python main.py"
```

### Restart Service

```bash
sudo systemctl restart trading-bot.service
```

### Stop Service

```bash
sudo systemctl stop trading-bot.service
```

## 7. Security Best Practices

1. **Environment Variables**: Never commit `.env` file to version control
2. **File Permissions**: Restrict access to sensitive files
   ```bash
   chmod 600 .env
   ```
3. **Firewall**: Configure firewall to allow only necessary ports
4. **SSH Keys**: Use SSH keys instead of passwords
5. **Regular Updates**: Keep system and dependencies updated
6. **Backup**: Regularly backup trade logs and configuration

## 8. Troubleshooting

### Issue: Service fails to start

```bash
# Check service status
sudo systemctl status trading-bot.service

# Check logs
sudo journalctl -u trading-bot.service -n 50
```

### Issue: Authentication errors

- Verify `.env` file has correct credentials
- Check if access token has expired
- Re-authenticate and update token

### Issue: Market data not received

- Check WebSocket connection
- Verify instrument keys are correct
- Check network connectivity

### Issue: Orders not executing

- Verify account has sufficient margin
- Check order limits and restrictions
- Review order manager logs

## 9. Performance Optimization

1. **Resource Monitoring**: Monitor CPU and memory usage
2. **Database**: Consider using a database for trade logs (PostgreSQL/MySQL)
3. **Caching**: Cache frequently accessed data
4. **Connection Pooling**: Optimize API connection handling

## 10. Backup and Recovery

### Backup Strategy

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/trading_bot"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR/$DATE
cp -r logs/ $BACKUP_DIR/$DATE/
cp -r data/ $BACKUP_DIR/$DATE/
cp .env $BACKUP_DIR/$DATE/
```

Schedule daily backups using cron:

```cron
0 2 * * * /path/to/backup-script.sh
```

## Support

For issues and questions, refer to:
- Upstox API Documentation: https://upstox.com/developer/api-documentation
- Project README.md
- Log files in `logs/` directory
