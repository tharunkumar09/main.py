# ✅ Quick Start Checklist

Use this checklist to ensure you've completed all setup steps correctly.

## Prerequisites

- [ ] Computer with internet connection
- [ ] Upstox account created (free at upstox.com)
- [ ] About 30-60 minutes available

## Step 1: Install Python

- [ ] Downloaded Python from python.org
- [ ] Installed Python (Windows: checked "Add to PATH")
- [ ] Verified installation: `python --version` works
- [ ] Can see Python version number

## Step 2: Get Bot Code

- [ ] Bot code files are in a folder (e.g., `C:\TradingBot`)
- [ ] Can see files like `main.py`, `config.py`, `requirements.txt`

## Step 3: Upstox Sandbox Setup

- [ ] Logged into Upstox account
- [ ] Visited https://account.upstox.com/developer/apps
- [ ] Created new Sandbox application
- [ ] Selected "Sandbox" environment (NOT Production)
- [ ] Set Redirect URI to: `http://localhost:3000/callback`
- [ ] Saved API Key (Client ID)
- [ ] Saved API Secret (Client Secret)
- [ ] Credentials are saved in a safe place

## Step 4: Install Bot Dependencies

- [ ] Opened Terminal/Command Prompt
- [ ] Navigated to bot folder (`cd` command worked)
- [ ] Created virtual environment: `python -m venv venv`
- [ ] Activated virtual environment (sees `(venv)` in prompt)
- [ ] Installed packages: `pip install -r requirements.txt`
- [ ] Installation completed without major errors

## Step 5: Configure Bot

- [ ] Created `.env` file (copied from `.env.example`)
- [ ] Set `UPSTOX_SANDBOX_MODE=true`
- [ ] Added API Key to `.env`
- [ ] Added API Secret to `.env`
- [ ] Set Redirect URI: `http://localhost:3000/callback`
- [ ] Saved `.env` file

## Step 6: Get Access Token

- [ ] Ran `python get_token.py`
- [ ] Copied the authorization URL
- [ ] Opened URL in browser
- [ ] Logged into Upstox
- [ ] Authorized the application
- [ ] Copied authorization code from redirect URL
- [ ] Ran `python get_token.py <code>`
- [ ] Received access token
- [ ] Added token to `.env` file
- [ ] Saved `.env` file

## Step 7: Test Connection

- [ ] Ran `python test_sandbox.py`
- [ ] All tests passed (✅ marks)
- [ ] No authentication errors
- [ ] Connection to Upstox successful

## Step 8: Ready to Run

- [ ] All above steps completed
- [ ] Understand this is SANDBOX mode (no real money)
- [ ] Ready to start bot: `python main.py`

## Troubleshooting Checklist

If something doesn't work:

- [ ] Checked Python is installed correctly
- [ ] Verified virtual environment is activated
- [ ] Confirmed `.env` file has correct values
- [ ] Checked API credentials are from Sandbox (not Production)
- [ ] Verified access token is not expired
- [ ] Checked `logs/trading_bot.log` for errors
- [ ] Ran `python test_sandbox.py` to diagnose

## Final Verification

Before running the bot:

- [ ] `python test_sandbox.py` shows all ✅
- [ ] `.env` file is properly configured
- [ ] Virtual environment is active (`(venv)` visible)
- [ ] You're in the correct folder
- [ ] Internet connection is working

---

**When all items are checked, you're ready to run: `python main.py`**

Good luck! 🚀
