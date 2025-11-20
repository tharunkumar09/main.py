#!/usr/bin/env python3
"""
Helper script to get Upstox access token for sandbox/production
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.auth.session_manager import SessionManager
from config import UPSTOX_SANDBOX_MODE, UPSTOX_REDIRECT_URI


def main():
    """Main function to get access token"""
    mode_text = "SANDBOX" if UPSTOX_SANDBOX_MODE else "PRODUCTION"
    
    print("\n" + "="*80)
    print(f"Upstox Access Token Generator - {mode_text} Mode")
    print("="*80)
    
    # Initialize session manager
    session_manager = SessionManager()
    
    # Check if authorization code provided
    if len(sys.argv) > 1:
        auth_code = sys.argv[1]
        print(f"\nExchanging authorization code for access token...")
        
        try:
            token_data = session_manager.get_access_token_from_code(auth_code)
            
            print("\n" + "="*80)
            print("✅ SUCCESS! Access token obtained")
            print("="*80)
            print(f"\nAccess Token: {token_data.get('access_token')}")
            print(f"Token Type: {token_data.get('token_type', 'Bearer')}")
            print(f"Expires In: {token_data.get('expires_in', 'N/A')} seconds")
            
            print("\n" + "-"*80)
            print("Add this to your .env file:")
            print("-"*80)
            print(f"UPSTOX_ACCESS_TOKEN={token_data.get('access_token')}")
            print("-"*80)
            
            print("\n✅ Token has been saved to .upstox_token.json")
            print("✅ You can now run the trading bot!")
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to get access token")
            print(f"Error: {e}")
            print("\nPlease check:")
            print("1. Authorization code is correct")
            print("2. Code hasn't expired (use within 5 minutes)")
            print("3. API credentials are correct in .env")
            sys.exit(1)
    
    else:
        # Show authorization URL
        auth_url = session_manager.get_authorization_url()
        
        print(f"\n📋 Step-by-Step Instructions:")
        print("-"*80)
        print(f"\n1. Visit this URL in your browser:")
        print(f"\n   {auth_url}\n")
        print("2. Login to your Upstox account")
        print("3. Authorize the application")
        print(f"4. You'll be redirected to: {UPSTOX_REDIRECT_URI}?code=AUTHORIZATION_CODE")
        print("5. Copy the 'code' parameter from the URL")
        print("\n6. Run this script again with the authorization code:")
        print(f"\n   python get_token.py <authorization_code>\n")
        print("-"*80)
        
        print(f"\n⚠️  Mode: {mode_text}")
        if UPSTOX_SANDBOX_MODE:
            print("   This is SANDBOX mode - safe for testing!")
        else:
            print("   ⚠️  WARNING: This is PRODUCTION mode - real money!")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    main()
