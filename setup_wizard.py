#!/usr/bin/env python3
"""
Interactive Setup Wizard for Complete Beginners
Guides you through the entire setup process step by step
"""

import os
import sys
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def print_step(number, text):
    """Print a step"""
    print(f"\n{'='*80}")
    print(f"STEP {number}: {text}")
    print('='*80 + "\n")

def wait_for_user():
    """Wait for user to press Enter"""
    input("Press ENTER to continue...")

def check_python():
    """Check if Python is installed"""
    print_step(1, "Checking Python Installation")
    
    try:
        import sys
        version = sys.version_info
        print(f"✅ Python is installed!")
        print(f"   Version: {version.major}.{version.minor}.{version.micro}")
        
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            print("⚠️  WARNING: Python 3.10+ recommended")
            print("   Current version may work but 3.10+ is better")
        else:
            print("✅ Python version is good!")
        
        return True
    except:
        print("❌ Python is not installed or not in PATH")
        print("\nPlease install Python first:")
        print("1. Go to: https://www.python.org/downloads/")
        print("2. Download Python 3.10 or higher")
        print("3. Install it (Windows: Check 'Add to PATH')")
        print("4. Restart this script")
        return False

def check_files():
    """Check if required files exist"""
    print_step(2, "Checking Bot Files")
    
    required_files = [
        "main.py",
        "config.py",
        "requirements.txt",
        ".env.example"
    ]
    
    missing = []
    for file in required_files:
        if Path(file).exists():
            print(f"✅ Found: {file}")
        else:
            print(f"❌ Missing: {file}")
            missing.append(file)
    
    if missing:
        print(f"\n❌ Missing files: {', '.join(missing)}")
        print("Please make sure you're in the correct folder")
        return False
    
    print("\n✅ All required files are present!")
    return True

def setup_venv():
    """Guide user to set up virtual environment"""
    print_step(3, "Setting Up Virtual Environment")
    
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        print("   Skipping creation...")
    else:
        print("Creating virtual environment...")
        print("This may take 1-2 minutes...")
        
        import subprocess
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ Virtual environment created!")
        except Exception as e:
            print(f"❌ Error creating virtual environment: {e}")
            print("\nPlease run manually:")
            print(f"  {sys.executable} -m venv venv")
            return False
    
    # Check activation
    if os.name == 'nt':  # Windows
        activate_script = venv_path / "Scripts" / "activate.bat"
        print("\n📋 To activate virtual environment, run:")
        print("   venv\\Scripts\\activate")
    else:  # Mac/Linux
        activate_script = venv_path / "bin" / "activate"
        print("\n📋 To activate virtual environment, run:")
        print("   source venv/bin/activate")
    
    print("\n⚠️  IMPORTANT: Make sure (venv) appears in your terminal prompt")
    print("   before running the next steps!")
    
    return True

def install_packages():
    """Guide user to install packages"""
    print_step(4, "Installing Required Packages")
    
    print("You need to install packages manually:")
    print("\n1. Make sure virtual environment is activated (you see (venv))")
    print("2. Run this command:")
    print("   pip install -r requirements.txt")
    print("\nThis will take 5-10 minutes...")
    print("Wait until you see 'Successfully installed'")
    
    wait_for_user()
    
    # Try to check if packages are installed
    try:
        import requests
        print("✅ Some packages are installed (requests found)")
    except:
        print("⚠️  Packages may not be installed yet")
        print("   Please run: pip install -r requirements.txt")
    
    return True

def setup_env_file():
    """Guide user to set up .env file"""
    print_step(5, "Setting Up Configuration File")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        response = input("Do you want to recreate it? (y/n): ").lower()
        if response != 'y':
            print("Keeping existing .env file")
            return True
    
    if not env_example.exists():
        print("❌ .env.example file not found!")
        return False
    
    print("Creating .env file from template...")
    
    # Read example
    with open(env_example, 'r') as f:
        content = f.read()
    
    # Write .env
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ .env file created!")
    print("\n📋 Next steps:")
    print("1. Open .env file in Notepad (Windows) or TextEdit (Mac)")
    print("2. You'll need to add your Upstox credentials")
    print("3. We'll help you get those in the next step")
    
    return True

def get_upstox_credentials():
    """Guide user to get Upstox credentials"""
    print_step(6, "Getting Upstox Sandbox Credentials")
    
    print("You need to:")
    print("1. Go to: https://account.upstox.com/developer/apps")
    print("2. Login with your Upstox account")
    print("3. Click 'Create New App'")
    print("4. Fill in:")
    print("   - App Name: Trading Bot Sandbox")
    print("   - Environment: Select 'Sandbox' (IMPORTANT!)")
    print("   - Redirect URI: http://localhost:3000/callback")
    print("5. Click 'Create'")
    print("6. Copy your API Key and API Secret")
    
    wait_for_user()
    
    api_key = input("\nEnter your API Key (or press Enter to skip): ").strip()
    api_secret = input("Enter your API Secret (or press Enter to skip): ").strip()
    
    if api_key and api_secret:
        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Replace placeholders
            content = content.replace("your_api_key_here", api_key)
            content = content.replace("your_api_secret_here", api_secret)
            
            with open(env_file, 'w') as f:
                f.write(content)
            
            print("✅ Credentials saved to .env file!")
        else:
            print("⚠️  .env file not found. Please add credentials manually.")
    else:
        print("⚠️  Credentials not entered. Please add them manually to .env file")
    
    return True

def get_access_token():
    """Guide user to get access token"""
    print_step(7, "Getting Access Token")
    
    print("Now you need to get an access token:")
    print("\n1. Run this command:")
    print("   python get_token.py")
    print("\n2. Copy the URL that appears")
    print("3. Open it in your browser")
    print("4. Login and authorize")
    print("5. Copy the 'code' from the redirect URL")
    print("6. Run: python get_token.py <your_code>")
    print("7. Copy the access token to .env file")
    
    wait_for_user()
    
    response = input("\nHave you completed getting the access token? (y/n): ").lower()
    if response == 'y':
        print("✅ Great! Moving to next step...")
    else:
        print("⚠️  Please complete getting the access token before continuing")
    
    return True

def test_connection():
    """Guide user to test connection"""
    print_step(8, "Testing Connection")
    
    print("Let's test if everything is working:")
    print("\nRun this command:")
    print("   python test_sandbox.py")
    print("\nYou should see all ✅ marks if everything is correct")
    
    wait_for_user()
    
    return True

def final_instructions():
    """Show final instructions"""
    print_step(9, "You're Ready!")
    
    print("🎉 Congratulations! Setup is complete!")
    print("\nTo start the trading bot, run:")
    print("   python main.py")
    print("\nRemember:")
    print("✅ You're in SANDBOX mode - no real money")
    print("✅ All trades are simulated")
    print("✅ Safe to experiment")
    print("\nLogs are saved in the 'logs' folder")
    print("Check 'logs/trading_bot.log' to see what's happening")
    
    print("\n" + "="*80)
    print("Setup Complete!")
    print("="*80 + "\n")

def main():
    """Main setup wizard"""
    print_header("Trading Bot Setup Wizard")
    print("Welcome! This wizard will guide you through the setup process.")
    print("Follow each step carefully.")
    
    wait_for_user()
    
    # Step 1: Check Python
    if not check_python():
        print("\n❌ Setup cannot continue without Python")
        sys.exit(1)
    wait_for_user()
    
    # Step 2: Check files
    if not check_files():
        print("\n❌ Setup cannot continue - missing files")
        sys.exit(1)
    wait_for_user()
    
    # Step 3: Setup venv
    if not setup_venv():
        print("\n❌ Virtual environment setup failed")
        sys.exit(1)
    wait_for_user()
    
    # Step 4: Install packages
    install_packages()
    
    # Step 5: Setup .env
    if not setup_env_file():
        print("\n❌ Configuration file setup failed")
        sys.exit(1)
    wait_for_user()
    
    # Step 6: Get credentials
    get_upstox_credentials()
    wait_for_user()
    
    # Step 7: Get token
    get_access_token()
    wait_for_user()
    
    # Step 8: Test
    test_connection()
    wait_for_user()
    
    # Step 9: Final instructions
    final_instructions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("Please check the error and try again")
        sys.exit(1)
