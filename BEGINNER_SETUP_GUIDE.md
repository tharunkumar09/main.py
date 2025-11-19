# 🚀 Complete Beginner's Guide: Setting Up Trading Bot with Upstox Sandbox

This guide is designed for **complete beginners** with zero coding experience. Follow each step carefully.

---

## 📋 What You'll Need

1. **Computer** (Windows, Mac, or Linux)
2. **Internet connection**
3. **Upstox account** (free to create)
4. **About 30-60 minutes** of your time

---

## Part 1: Installing Python (The Programming Language)

### For Windows Users:

1. **Download Python:**
   - Go to: https://www.python.org/downloads/
   - Click the big yellow "Download Python 3.12.x" button
   - Save the file (it will be something like `python-3.12.0.exe`)

2. **Install Python:**
   - Double-click the downloaded file
   - **IMPORTANT:** Check the box "Add Python to PATH" at the bottom
   - Click "Install Now"
   - Wait for installation to complete
   - Click "Close"

3. **Verify Installation:**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter
   - In the black window, type: `python --version`
   - You should see something like: `Python 3.12.0`
   - If you see an error, Python is not installed correctly

### For Mac Users:

1. **Check if Python is installed:**
   - Open Terminal (Press `Cmd + Space`, type "Terminal", press Enter)
   - Type: `python3 --version`
   - If you see a version number (like 3.10 or higher), skip to Part 2
   - If you see "command not found", continue below

2. **Install Python:**
   - Go to: https://www.python.org/downloads/
   - Click "Download Python 3.12.x"
   - Open the downloaded `.pkg` file
   - Follow the installation wizard
   - Click "Install"

3. **Verify Installation:**
   - Open Terminal
   - Type: `python3 --version`
   - You should see: `Python 3.12.x`

### For Linux Users:

1. **Open Terminal** (Press `Ctrl + Alt + T`)

2. **Install Python:**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv -y
   ```

3. **Verify Installation:**
   ```bash
   python3 --version
   ```

---

## Part 2: Getting the Trading Bot Code

### Option A: If You Have the Code Files

1. **Create a folder** on your computer (e.g., `C:\TradingBot` on Windows or `~/TradingBot` on Mac/Linux)

2. **Copy all the code files** into this folder

### Option B: If You Need to Download

1. **Download the code** (if it's in a ZIP file)
2. **Extract the ZIP file** to a folder (e.g., `C:\TradingBot`)

---

## Part 3: Setting Up Upstox Sandbox Account

### Step 1: Create Upstox Account (If You Don't Have One)

1. **Go to:** https://upstox.com
2. **Click "Sign Up"** or "Open Account"
3. **Fill in your details:**
   - Name
   - Email
   - Phone number
   - Create a password
4. **Complete the registration** (you may need to verify email/phone)
5. **Login** to your Upstox account

### Step 2: Register Sandbox Application

1. **Go to Upstox Developer Portal:**
   - Visit: https://account.upstox.com/developer/apps
   - **Login** with your Upstox account credentials

2. **Create New Application:**
   - Click the **"Create New App"** button (usually at the top right)
   - You'll see a form to fill

3. **Fill the Application Form:**
   
   **App Name:** 
   - Enter: `Trading Bot Sandbox` (or any name you like)
   
   **Environment:**
   - **IMPORTANT:** Select **"Sandbox"** (NOT Production)
   - This ensures you're testing with fake money
   
   **Redirect URI:**
   - Enter exactly: `http://localhost:3000/callback`
   - Copy this exactly as shown (don't change anything)
   
   **Description (Optional):**
   - Enter: `Algorithmic Trading Bot for Testing`
   
   **Click "Create" or "Submit"**

4. **Save Your Credentials:**
   After creating the app, you'll see:
   - **API Key** (also called Client ID) - looks like: `abc123xyz456`
   - **API Secret** (also called Client Secret) - looks like: `secret789xyz`
   
   **⚠️ IMPORTANT:** Copy these and save them in a text file. You'll need them later!
   
   - Click "Copy" next to each credential
   - Paste them into a Notepad/TextEdit file
   - Save the file as `credentials.txt` (keep it safe!)

---

## Part 4: Installing the Trading Bot

### Step 1: Open Command Prompt / Terminal

**Windows:**
- Press `Windows Key + R`
- Type `cmd` and press Enter
- A black window will open

**Mac/Linux:**
- Press `Cmd + Space` (Mac) or `Ctrl + Alt + T` (Linux)
- Type "Terminal" and press Enter

### Step 2: Navigate to the Bot Folder

**Windows:**
```cmd
cd C:\TradingBot
```
(Replace `C:\TradingBot` with your actual folder path)

**Mac/Linux:**
```bash
cd ~/TradingBot
```
(Replace `~/TradingBot` with your actual folder path)

**Tip:** If you're not sure of the path:
- **Windows:** Right-click the folder → Properties → Copy the "Location" path
- **Mac/Linux:** Drag the folder into Terminal to see the path

### Step 3: Create Virtual Environment

**Windows:**
```cmd
python -m venv venv
```

**Mac/Linux:**
```bash
python3 -m venv venv
```

Wait for it to complete (may take 1-2 minutes)

### Step 4: Activate Virtual Environment

**Windows:**
```cmd
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

**Success indicator:** You should see `(venv)` at the beginning of your command line, like:
```
(venv) C:\TradingBot>
```

### Step 5: Install Required Packages

**Windows/Mac/Linux (all same):**
```bash
pip install -r requirements.txt
```

**This will take 5-10 minutes.** You'll see lots of text scrolling. Wait until you see:
```
Successfully installed ...
```

**If you get errors:**
- Make sure you're in the `(venv)` environment
- Make sure you're in the correct folder
- Try: `pip install --upgrade pip` first, then try again

---

## Part 5: Configuring the Bot

### Step 1: Create Configuration File

1. **Find the file named:** `.env.example`
   - It should be in your TradingBot folder

2. **Copy it:**
   - **Windows:** Right-click → Copy → Right-click in folder → Paste → Rename to `.env`
   - **Mac/Linux:** In Terminal: `cp .env.example .env`

3. **Open `.env` file** with Notepad (Windows) or TextEdit (Mac)

### Step 2: Edit the Configuration

Find these lines in the `.env` file and replace with YOUR values:

```bash
# Set to true for sandbox (paper trading)
UPSTOX_SANDBOX_MODE=true

# Your Upstox Sandbox Credentials (from Part 3, Step 2)
UPSTOX_API_KEY=paste_your_api_key_here
UPSTOX_API_SECRET=paste_your_api_secret_here

# Redirect URI (keep this as is)
UPSTOX_REDIRECT_URI=http://localhost:3000/callback

# Access Token (leave empty for now - we'll get it next)
UPSTOX_ACCESS_TOKEN=
```

**Example:**
```bash
UPSTOX_SANDBOX_MODE=true
UPSTOX_API_KEY=abc123xyz456
UPSTOX_API_SECRET=secret789xyz
UPSTOX_REDIRECT_URI=http://localhost:3000/callback
UPSTOX_ACCESS_TOKEN=
```

**Save the file** (Ctrl+S or Cmd+S)

---

## Part 6: Getting Access Token

### Step 1: Run the Token Helper Script

In your Terminal/Command Prompt (make sure you're in the bot folder and `(venv)` is active):

```bash
python get_token.py
```

**Windows users:** If `python` doesn't work, try `python get_token.py` or `py get_token.py`

**Mac/Linux users:** Use `python3 get_token.py`

### Step 2: Get Authorization Code

1. **You'll see a URL** that looks like:
   ```
   https://account.upstox.com/oauth/authorize?response_type=code&client_id=...
   ```

2. **Copy the entire URL**

3. **Open your web browser** (Chrome, Firefox, etc.)

4. **Paste the URL** in the address bar and press Enter

5. **Login** to your Upstox account (if not already logged in)

6. **Authorize the application:**
   - You'll see a page asking to authorize
   - Click "Authorize" or "Allow"

7. **After authorization, you'll be redirected** to a page that says something like:
   ```
   http://localhost:3000/callback?code=ABC123XYZ456...
   ```
   - The page might show "This site can't be reached" - **THIS IS NORMAL!**
   - **Don't close the page!**

8. **Copy the code:**
   - Look at the URL in your browser's address bar
   - Find the part after `code=`
   - Copy everything after `code=` until the end (or until you see `&` if there is one)
   - Example: If URL is `...code=ABC123XYZ456&state=...`, copy `ABC123XYZ456`

### Step 3: Exchange Code for Token

1. **Go back to your Terminal/Command Prompt**

2. **Run:**
   ```bash
   python get_token.py YOUR_AUTHORIZATION_CODE
   ```
   
   Replace `YOUR_AUTHORIZATION_CODE` with the code you copied
   
   Example:
   ```bash
   python get_token.py ABC123XYZ456
   ```

3. **You'll see:**
   ```
   ✅ SUCCESS! Access token obtained
   Access Token: xyz789abc123...
   ```

4. **Copy the Access Token**

5. **Update your `.env` file:**
   - Open `.env` file again
   - Find the line: `UPSTOX_ACCESS_TOKEN=`
   - Paste your token after the `=`
   - Save the file

---

## Part 7: Testing the Setup

### Step 1: Test Connection

In Terminal/Command Prompt:

```bash
python test_sandbox.py
```

**You should see:**
```
================================================================================
Upstox Sandbox Connection Test
================================================================================

TEST 1: Authentication
✅ Authentication successful (SANDBOX mode)

TEST 2: Portfolio API
✅ Portfolio API working

TEST SUMMARY
✅ PASS: Configuration
✅ PASS: Authentication
✅ PASS: Portfolio API

✅ All tests passed! Sandbox is ready to use.
```

**If you see errors:**
- Check that your `.env` file has correct credentials
- Make sure you saved the `.env` file
- Verify your API Key and Secret are correct
- Try getting a new access token

---

## Part 8: Running the Trading Bot

### Step 1: Start the Bot

In Terminal/Command Prompt (make sure `(venv)` is active):

```bash
python main.py
```

### Step 2: What You'll See

You should see output like:
```
================================================================================
Algorithmic Trading Bot Starting
Mode: SANDBOX (Paper Trading)
Time: 2024-12-06 10:00:00
================================================================================
⚠️  SANDBOX MODE: All trades are simulated - No real money at risk

Starting trading bot in SANDBOX (Paper Trading) mode...
SANDBOX MODE ENABLED - No real money will be used
All trades are simulated for testing purposes
```

### Step 3: The Bot is Running!

- The bot will connect to Upstox sandbox
- It will start monitoring the market
- It will execute trades based on the strategy (simulated, no real money)
- All activity is logged to files in the `logs/` folder

### Step 4: Stop the Bot

Press `Ctrl + C` (Windows/Linux) or `Cmd + C` (Mac) to stop the bot

---

## Part 9: Understanding What's Happening

### Logs

The bot creates log files:
- **Location:** `logs/` folder in your bot directory
- **Files:**
  - `trading_bot.log` - General bot activity
  - `trades_YYYYMMDD.json` - Trade details (JSON format)
  - `trades_YYYYMMDD.csv` - Trade details (Excel-readable format)

### Viewing Logs

**Windows:**
- Navigate to `logs` folder
- Open files with Notepad or Excel

**Mac/Linux:**
- Open Terminal in logs folder
- Type: `cat trading_bot.log` to view

### Checking Trades

Open `logs/trades_YYYYMMDD.csv` in Excel or Google Sheets to see:
- Entry time
- Exit time
- Profit/Loss
- Entry/Exit prices

---

## 🐛 Troubleshooting Common Issues

### Issue 1: "Python is not recognized"

**Solution:**
- Reinstall Python and make sure "Add Python to PATH" is checked
- Or use `python3` instead of `python`

### Issue 2: "No module named 'xxx'"

**Solution:**
- Make sure `(venv)` is active
- Run: `pip install -r requirements.txt` again

### Issue 3: "Invalid API credentials"

**Solution:**
- Check `.env` file has correct API Key and Secret
- Make sure there are no extra spaces
- Verify you're using Sandbox credentials (not Production)

### Issue 4: "Token expired"

**Solution:**
- Run `python get_token.py` again to get a new token
- Update `.env` file with new token

### Issue 5: "Market is not open"

**Solution:**
- Indian stock market is open: 9:15 AM - 3:30 PM IST (Monday-Friday)
- Bot will wait until market opens
- This is normal behavior

### Issue 6: Bot not placing trades

**Solution:**
- Check logs for errors
- Verify market is open
- Check that symbols are configured correctly
- In sandbox, trades are simulated - check order status in Upstox dashboard

---

## 📞 Getting Help

### If You're Stuck:

1. **Check the logs:**
   - Look in `logs/trading_bot.log` for error messages

2. **Verify your setup:**
   - Run `python test_sandbox.py` to check connection

3. **Common mistakes:**
   - Forgot to activate `(venv)`
   - Wrong credentials in `.env`
   - Using Production credentials instead of Sandbox
   - Not saving `.env` file after editing

---

## ✅ Checklist

Before running the bot, make sure:

- [ ] Python is installed and working
- [ ] Bot code is in a folder
- [ ] Virtual environment is created and activated
- [ ] All packages are installed (`pip install -r requirements.txt`)
- [ ] Upstox sandbox app is created
- [ ] API Key and Secret are saved
- [ ] `.env` file is configured with correct credentials
- [ ] Access token is obtained and added to `.env`
- [ ] `test_sandbox.py` passes all tests
- [ ] You understand this is SANDBOX mode (no real money)

---

## 🎉 Congratulations!

You've successfully set up the trading bot! 

**Remember:**
- You're in **SANDBOX mode** - no real money is at risk
- All trades are **simulated** for testing
- You can experiment safely
- When ready for real trading, you'll need Production credentials

**Next Steps:**
1. Let the bot run and observe its behavior
2. Check the logs to see what it's doing
3. Review trades in the CSV files
4. Adjust strategy parameters in `config.py` if needed
5. Run backtests: `python backtest.py`

---

## 📚 Additional Resources

- **Upstox API Docs:** https://upstox.com/developer/api-documentation
- **Upstox Developer Portal:** https://account.upstox.com/developer
- **Python Tutorial:** https://www.python.org/about/gettingstarted/

---

**Good luck with your trading bot! 🚀**

If you encounter any issues not covered here, check the `logs/trading_bot.log` file for detailed error messages.
