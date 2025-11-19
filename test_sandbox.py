#!/usr/bin/env python3
"""
Test script to verify Upstox Sandbox connection
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from loguru import logger
from config import UPSTOX_SANDBOX_MODE, UPSTOX_API_KEY, UPSTOX_ACCESS_TOKEN
from src.auth.session_manager import SessionManager
from src.portfolio.portfolio_manager import PortfolioManager


def test_authentication():
    """Test authentication"""
    print("\n" + "="*80)
    print("TEST 1: Authentication")
    print("="*80)
    
    try:
        session_manager = SessionManager()
        
        if not UPSTOX_API_KEY:
            print("❌ UPSTOX_API_KEY not set in .env")
            return False
        
        if not UPSTOX_ACCESS_TOKEN:
            print("❌ UPSTOX_ACCESS_TOKEN not set in .env")
            print("   Run: python get_token.py")
            return False
        
        if session_manager.is_token_valid():
            mode_text = "SANDBOX" if UPSTOX_SANDBOX_MODE else "PRODUCTION"
            print(f"✅ Authentication successful ({mode_text} mode)")
            return True
        else:
            print("❌ Token validation failed")
            print("   Try refreshing token or getting a new one")
            return False
    
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False


def test_portfolio():
    """Test portfolio API"""
    print("\n" + "="*80)
    print("TEST 2: Portfolio API")
    print("="*80)
    
    try:
        session_manager = SessionManager()
        portfolio_manager = PortfolioManager(session_manager)
        
        # Fetch positions
        positions = portfolio_manager.fetch_positions()
        print(f"✅ Portfolio API working")
        print(f"   Open positions: {len(positions)}")
        
        # Get summary
        summary = portfolio_manager.get_portfolio_summary()
        print(f"\nPortfolio Summary:")
        print(f"   Initial Capital: ₹{summary['initial_capital']:,.2f}")
        print(f"   Current Capital: ₹{summary['current_capital']:,.2f}")
        print(f"   Daily P&L: ₹{summary['daily_pnl']:,.2f}")
        print(f"   Daily Return: {summary['daily_return_pct']:.2f}%")
        
        return True
    
    except Exception as e:
        print(f"❌ Portfolio API error: {e}")
        return False


def test_configuration():
    """Test configuration"""
    print("\n" + "="*80)
    print("TEST 3: Configuration")
    print("="*80)
    
    mode_text = "SANDBOX (Paper Trading)" if UPSTOX_SANDBOX_MODE else "PRODUCTION (Live Trading)"
    print(f"✅ Mode: {mode_text}")
    print(f"✅ API Key: {'Set' if UPSTOX_API_KEY else 'Not set'}")
    print(f"✅ Access Token: {'Set' if UPSTOX_ACCESS_TOKEN else 'Not set'}")
    
    if UPSTOX_SANDBOX_MODE:
        print("\n⚠️  SANDBOX MODE: All trades will be simulated")
        print("   No real money will be used")
    else:
        print("\n⚠️  PRODUCTION MODE: Real money trading")
        print("   Use with caution!")
    
    return True


def main():
    """Main test function"""
    print("\n" + "="*80)
    print("Upstox Sandbox Connection Test")
    print("="*80)
    
    results = []
    
    # Test configuration
    results.append(("Configuration", test_configuration()))
    
    # Test authentication
    results.append(("Authentication", test_authentication()))
    
    # Test portfolio (only if auth works)
    if results[-1][1]:
        results.append(("Portfolio API", test_portfolio()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ All tests passed! Sandbox is ready to use.")
        print("\nNext steps:")
        print("1. Review configuration in .env")
        print("2. Run backtest: python backtest.py")
        print("3. Start bot: python main.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("1. Set UPSTOX_API_KEY and UPSTOX_API_SECRET in .env")
        print("2. Get access token: python get_token.py")
        print("3. Verify sandbox credentials are correct")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
