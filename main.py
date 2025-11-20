"""
Main Entry Point for Live Trading Bot
"""

import sys
from pathlib import Path
from loguru import logger
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent))

from config import LOG_LEVEL, LOG_FILE, UPSTOX_ACCESS_TOKEN, UPSTOX_SANDBOX_MODE
from src.auth.session_manager import SessionManager
from src.core.trading_bot import TradingBot

# Configure logging
logger.add(
    LOG_FILE,
    rotation="1 day",
    retention="30 days",
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


def main():
    """Main function"""
    mode_text = "SANDBOX (Paper Trading)" if UPSTOX_SANDBOX_MODE else "PRODUCTION (Live Trading)"
    logger.info("="*80)
    logger.info("Algorithmic Trading Bot Starting")
    logger.info(f"Mode: {mode_text}")
    logger.info(f"Time: {datetime.now()}")
    logger.info("="*80)
    
    if UPSTOX_SANDBOX_MODE:
        logger.warning("⚠️  SANDBOX MODE: All trades are simulated - No real money at risk")
    else:
        logger.warning("⚠️  PRODUCTION MODE: Real money trading - Use with caution!")
    
    try:
        # Initialize session manager
        session_manager = SessionManager()
        
        # Check if we have a valid token
        if not session_manager.is_token_valid():
            logger.error("No valid access token found!")
            logger.info("Please obtain an access token using the OAuth flow:")
            logger.info(f"1. Visit: {session_manager.get_authorization_url()}")
            logger.info("2. Authorize and copy the authorization code")
            logger.info("3. Use the authorization code to get access token")
            logger.info("4. Set UPSTOX_ACCESS_TOKEN environment variable or update config")
            return
        
        # Define symbols to trade (example: NIFTY 50 stocks)
        # In production, load from config or database
        symbols = [
            "NSE_EQ|INE467B01029",  # RELIANCE
            "NSE_EQ|INE467B01029",  # TCS (replace with actual instrument tokens)
            # Add more symbols as needed
        ]
        
        # Initialize trading bot
        bot = TradingBot(session_manager, symbols)
        
        # Start bot
        bot.start()
        
        # Keep running until interrupted
        try:
            import time
            while bot.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            bot.stop()
        
        logger.info("Trading bot stopped")
    
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
