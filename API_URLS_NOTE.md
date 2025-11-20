# 📝 Note About Upstox API URLs

## Current Implementation

The code now supports **both** approaches:

1. **Same URLs for Sandbox and Production** (Default - Most Common)
   - Upstox typically uses the same API endpoints
   - Environment is determined by app credentials (sandbox app vs production app)
   - This is the default behavior

2. **Separate Sandbox URLs** (If Needed)
   - If Upstox provides separate sandbox endpoints, you can override them
   - Set environment variables or modify `config.py`

## How It Works

The code automatically selects URLs based on `UPSTOX_SANDBOX_MODE`:

- **Sandbox Mode (`true`):** Uses `UPSTOX_API_BASE_URL_SANDBOX` (defaults to production URLs)
- **Production Mode (`false`):** Uses `UPSTOX_API_BASE_URL_PRODUCTION` (defaults to production URLs)

## Verifying Correct URLs

### Option 1: Check Upstox Documentation
Visit: https://upstox.com/developer/api-documentation
- Look for "Sandbox" or "Testing" section
- Check if separate URLs are mentioned

### Option 2: Test with Current Setup
1. Use sandbox credentials
2. Run: `python test_sandbox.py`
3. If it works → URLs are correct
4. If you get connection errors → May need separate sandbox URLs

### Option 3: Check Upstox Developer Portal
When you create a sandbox app, check if:
- API documentation shows different URLs
- There's a "Sandbox Base URL" field
- Support mentions separate endpoints

## If You Need Separate Sandbox URLs

### Method 1: Environment Variables (Recommended)

Add to your `.env` file:
```bash
UPSTOX_API_BASE_URL_SANDBOX=https://api-sandbox.upstox.com/v2
UPSTOX_WS_BASE_URL_SANDBOX=wss://api-sandbox.upstox.com/v2/feed/market-data-feed
UPSTOX_AUTH_BASE_URL_SANDBOX=https://account-sandbox.upstox.com
```

### Method 2: Modify config.py

Edit `config.py` and change:
```python
UPSTOX_API_BASE_URL_SANDBOX = "https://api-sandbox.upstox.com/v2"
UPSTOX_WS_BASE_URL_SANDBOX = "wss://api-sandbox.upstox.com/v2/feed/market-data-feed"
UPSTOX_AUTH_BASE_URL_SANDBOX = "https://account-sandbox.upstox.com"
```

## Default Behavior (Recommended)

**By default, the code uses the same URLs for both environments.**

This is correct for Upstox because:
- ✅ Same API endpoints
- ✅ Environment determined by app credentials
- ✅ Simpler configuration
- ✅ Works out of the box

## Testing

After making changes, test:
```bash
python test_sandbox.py
```

If you see:
- ✅ All tests pass → URLs are correct
- ❌ Connection errors → Check URLs or contact Upstox support

## Common URLs (Reference)

### Production (Default)
- API: `https://api.upstox.com/v2`
- WebSocket: `wss://api.upstox.com/v2/feed/market-data-feed`
- Auth: `https://account.upstox.com`

### Sandbox (If Separate - Verify with Upstox)
- API: `https://api-sandbox.upstox.com/v2` (example - verify!)
- WebSocket: `wss://api-sandbox.upstox.com/v2/feed/market-data-feed` (example - verify!)
- Auth: `https://account-sandbox.upstox.com` (example - verify!)

**⚠️ Important:** Always verify sandbox URLs with Upstox documentation or support before using separate URLs.

---

**Bottom Line:** Start with the default (same URLs). Only change if Upstox documentation specifically mentions separate sandbox endpoints.
