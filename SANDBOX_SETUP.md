# Upstox Sandbox Setup Guide

This guide will help you set up and test the trading bot using Upstox Sandbox (Paper Trading) environment.

## 🎯 What is Upstox Sandbox?

Upstox Sandbox is a **paper trading environment** that allows you to:
- Test trading strategies without risking real money
- Practice with live market data
- Validate your bot's logic before going live
- Learn the Upstox API without financial risk

## 📋 Prerequisites

1. **Upstox Account** - Sign up at [upstox.com](https://upstox.com)
2. **Sandbox API Credentials** - Register a sandbox application

## 🔧 Step-by-Step Setup

### Step 1: Register Sandbox Application

1. **Login to Upstox Developer Portal:**
   - Visit: https://account.upstox.com/developer/apps
   - Login with your Upstox credentials

2. **Create Sandbox Application:**
   - Click "Create New App"
   - Select **"Sandbox"** environment (not Production)
   - Fill in application details:
     - **App Name:** Trading Bot Sandbox
     - **Redirect URI:** `http://localhost:3000/callback`
     - **Description:** Algorithmic Trading Bot Testing
   - Click "Create"

3. **Get Your Credentials:**
   - After creation, you'll see:
     - **API Key** (Client ID)
     - **API Secret** (Client Secret)
   - **Save these credentials securely**

### Step 2: Configure Environment

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   # Set sandbox mode (default is true)
   UPSTOX_SANDBOX_MODE=true

   # Add your sandbox credentials
   UPSTOX_API_KEY=your_sandbox_api_key_here
   UPSTOX_API_SECRET=your_sandbox_api_secret_here
   UPSTOX_REDIRECT_URI=http://localhost:3000/callback

   # Leave access token empty initially - will be generated
   UPSTOX_ACCESS_TOKEN=
   ```

### Step 3: Get Access Token

#### Option A: Using Python Script (Recommended)

Create a file `get_token.py`:

```python
from src.auth.session_manager import SessionManager
from config import UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_REDIRECT_URI

# Initialize session manager
session_manager = SessionManager()

# Get authorization URL
auth_url = session_manager.get_authorization_url()
print("\n" + "="*80)
print("SANDBOX MODE - Get Access Token")
print("="*80)
print(f"\n1. Visit this URL in your browser:")
print(f"\n{auth_url}\n")
print("2. Authorize the application")
print("3. After authorization, you'll be redirected to:")
print(f"   {UPSTOX_REDIRECT_URI}?code=AUTHORIZATION_CODE")
print("\n4. Copy the 'code' parameter from the URL")
print("5. Run: python get_token.py <authorization_code>")
print("="*80)

# If authorization code provided as argument
import sys
if len(sys.argv) > 1:
    auth_code = sys.argv[1]
    try:
        token_data = session_manager.get_access_token_from_code(auth_code)
        print("\n✅ Access token obtained successfully!")
        print(f"Access Token: {token_data.get('access_token')[:20]}...")
        print("\nAdd this to your .env file:")
        print(f"UPSTOX_ACCESS_TOKEN={token_data.get('access_token')}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
```

Run it:
```bash
python get_token.py
# Follow the instructions, then:
python get_token.py <authorization_code>
```

#### Option B: Manual Process

1. **Get Authorization URL:**
   ```python
   from src.auth.session_manager import SessionManager
   sm = SessionManager()
   print(sm.get_authorization_url())
   ```

2. **Visit the URL** in your browser and authorize

3. **Copy the authorization code** from the redirect URL

4. **Exchange code for token:**
   ```python
   from src.auth.session_manager import SessionManager
   sm = SessionManager()
   token_data = sm.get_access_token_from_code("YOUR_AUTH_CODE")
   print(token_data['access_token'])
   ```

5. **Add token to `.env`:**
   ```
   UPSTOX_ACCESS_TOKEN=your_access_token_here
   ```

### Step 4: Verify Sandbox Mode

Check that sandbox mode is enabled:

```python
from config import UPSTOX_SANDBOX_MODE
print(f"Sandbox Mode: {UPSTOX_SANDBOX_MODE}")  # Should be True
```

### Step 5: Test Connection

Run a simple test:

```python
from src.auth.session_manager import SessionManager

sm = SessionManager()
if sm.is_token_valid():
    print("✅ Connected to Upstox Sandbox successfully!")
    print(f"Mode: {'SANDBOX' if sm.SANDBOX_MODE else 'PRODUCTION'}")
else:
    print("❌ Connection failed. Check your credentials.")
```

## 🧪 Testing the Bot

### 1. Test Authentication

```bash
python -c "from src.auth.session_manager import SessionManager; sm = SessionManager(); print('✅ Valid' if sm.is_token_valid() else '❌ Invalid')"
```

### 2. Test Market Data (WebSocket)

The bot will automatically connect to sandbox WebSocket feed when started.

### 3. Test Order Placement

**Important:** In sandbox mode, orders are simulated. They won't execute with real money.

```python
from src.orders.order_manager import OrderManager, OrderSide, ProductType
from src.auth.session_manager import SessionManager

sm = SessionManager()
om = OrderManager(sm)

# Test market order (will be simulated in sandbox)
# Note: Use valid instrument token from Upstox
# response = om.place_market_order(
#     symbol="NSE_EQ|INE467B01029",  # Example: RELIANCE
#     quantity=1,
#     side=OrderSide.BUY
# )
```

### 4. Run Full Bot Test

```bash
# Start the bot (will use sandbox)
python main.py
```

You should see:
```
================================================================================
Algorithmic Trading Bot Starting
Mode: SANDBOX (Paper Trading)
Time: 2024-12-06 10:00:00
================================================================================
⚠️  SANDBOX MODE: All trades are simulated - No real money at risk
```

## 🔍 Sandbox vs Production Differences

| Feature | Sandbox | Production |
|---------|---------|------------|
| **Money** | Virtual/Paper | Real |
| **Orders** | Simulated | Executed |
| **API Credentials** | Separate sandbox app | Production app |
| **Risk** | None | Real financial risk |
| **Data** | Live market data | Live market data |
| **Testing** | Unlimited | Limited by capital |

## 📝 Important Notes

1. **Separate Credentials:**
   - Sandbox and Production use **different API credentials**
   - You need to register separate applications for each

2. **Same API Endpoints:**
   - Sandbox uses the same API URLs as production
   - The difference is in the credentials and environment

3. **Paper Trading:**
   - Orders in sandbox are **simulated**
   - You can test strategies without risk
   - Portfolio values are virtual

4. **Market Data:**
   - Sandbox provides **real-time market data**
   - Same data feed as production
   - Perfect for strategy testing

5. **Token Expiry:**
   - Sandbox tokens expire like production tokens
   - The bot automatically refreshes tokens

## 🚨 Switching to Production

**⚠️ WARNING: Production mode uses REAL MONEY!**

To switch to production:

1. **Register Production App:**
   - Create a new application in Upstox Developer Portal
   - Select **"Production"** environment

2. **Update `.env`:**
   ```bash
   UPSTOX_SANDBOX_MODE=false
   UPSTOX_API_KEY=your_production_api_key
   UPSTOX_API_SECRET=your_production_api_secret
   UPSTOX_ACCESS_TOKEN=your_production_access_token
   ```

3. **Test Thoroughly:**
   - Run extensive backtests
   - Test in sandbox first
   - Start with small capital
   - Monitor closely

## 🐛 Troubleshooting

### Issue: "Invalid API credentials"

**Solution:**
- Verify you're using **sandbox credentials** (not production)
- Check that `UPSTOX_SANDBOX_MODE=true` in `.env`
- Ensure credentials are correctly set

### Issue: "Token expired"

**Solution:**
- The bot auto-refreshes tokens
- If manual refresh needed:
  ```python
  from src.auth.session_manager import SessionManager
  sm = SessionManager()
  sm.refresh_access_token()
  ```

### Issue: "WebSocket connection failed"

**Solution:**
- Check internet connectivity
- Verify access token is valid
- Check Upstox API status

### Issue: "Orders not executing"

**Solution:**
- In sandbox, orders are **simulated** - this is normal
- Check order status via API
- Verify instrument tokens are correct

## 📚 Additional Resources

- [Upstox API Documentation](https://upstox.com/developer/api-documentation)
- [Upstox Developer Portal](https://account.upstox.com/developer)
- [Sandbox Testing Guide](https://upstox.com/developer/docs/sandbox)

## ✅ Checklist

Before going live, ensure:

- [ ] Successfully tested in sandbox mode
- [ ] All strategies backtested
- [ ] Risk management verified
- [ ] Circuit breaker tested
- [ ] Error handling validated
- [ ] Logging working correctly
- [ ] Production credentials secured
- [ ] Small capital allocation for initial testing

---

**Happy Testing! 🚀**

Remember: Always test thoroughly in sandbox before using real money.
