#!/usr/bin/env python
import os
import sys
import subprocess
import argparse
import platform
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        print(f"Error: Python 3.10+ is required, but you're using {major}.{minor}")
        return False
    return True

def setup_virtual_env():
    """Create and activate a virtual environment"""
    print("Setting up virtual environment...")
    
    venv_dir = Path("venv")
    if venv_dir.exists():
        should_recreate = input("Virtual environment already exists. Recreate? (y/n): ")
        if should_recreate.lower() == 'y':
            shutil.rmtree(venv_dir)
        else:
            print("Using existing virtual environment.")
            return True
    
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("Virtual environment created successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False

def ensure_pip():
    """Ensure pip is installed in the virtual environment"""
    print("Checking pip installation...")
    
    # Determine the path to python executable based on the operating system
    if platform.system() == "Windows":
        python_path = os.path.join("venv", "Scripts", "python")
    else:
        python_path = os.path.join("venv", "bin", "python")
    
    # Try to run pip to check if it's installed
    result = subprocess.run([python_path, "-m", "pip", "--version"], capture_output=True)
    
    if result.returncode != 0:
        print("Pip not found in virtual environment. Installing pip...")
        try:
            # Use ensurepip to bootstrap pip into the virtual environment
            subprocess.run([python_path, "-m", "ensurepip", "--upgrade"], check=True)
            print("Pip installed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing pip: {e}")
            
            # Alternative method for Windows - download get-pip.py and run it
            if platform.system() == "Windows":
                try:
                    print("Trying alternative method to install pip...")
                    # Download get-pip.py
                    import urllib.request
                    urllib.request.urlretrieve(
                        "https://bootstrap.pypa.io/get-pip.py", "get-pip.py"
                    )
                    # Run get-pip.py
                    subprocess.run([python_path, "get-pip.py"], check=True)
                    print("Pip installed successfully using get-pip.py.")
                    # Clean up
                    os.remove("get-pip.py")
                    return True
                except Exception as e2:
                    print(f"Error installing pip with get-pip.py: {e2}")
                    return False
            return False
    else:
        print("Pip is already installed.")
        return True

def install_dependencies():
    """Install project dependencies"""
    print("Installing dependencies...")
    
    # Ensure pip is installed first
    if not ensure_pip():
        print("Cannot continue without pip. Please install pip manually.")
        return False
    
    # Determine the path to python executable based on the operating system
    if platform.system() == "Windows":
        python_path = os.path.join("venv", "Scripts", "python")
    else:
        python_path = os.path.join("venv", "bin", "python")
    
    try:
        # Use python -m pip instead of direct pip calls to avoid issues
        subprocess.run([python_path, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([python_path, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

def setup_env_file():
    """Set up the .env file"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print(".env file already exists.")
    else:
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print(".env file created from template. Please edit it with your credentials.")
        else:
            # Create a simple .env file with default values
            with open(env_file, "w") as f:
                f.write("""# Database configuration
DATABASE_URL=sqlite:///price_tracker.db

# Email configuration
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# API keys
SCRAPER_API_KEY=your_api_key

# Discord configuration (optional)
DISCORD_WEBHOOK_URL=your_discord_webhook_url

# Scraping configuration
SCRAPE_INTERVAL_HOURS=1
PRICE_DROP_THRESHOLD=5  # Percentage
""")
            print(".env file created with default values. Please edit it with your credentials.")
    
    return True

def show_next_steps():
    """Show next steps for the user"""
    print("\n=== Setup Complete! ===")
    print("\nNext steps:")
    
    if platform.system() == "Windows":
        activate_cmd = ".\\venv\\Scripts\\activate"
    else:
        activate_cmd = "source venv/bin/activate"
    
    print(f"1. Activate the virtual environment: {activate_cmd}")
    print("2. Edit the .env file with your Gmail credentials")
    print("3. Add a product to track: python add_product.py add \"https://example.com/product/123\"")
    print("4. Run a price check: python app/tasks/check_prices.py --check-all")
    print("5. Start the dashboard: streamlit run app/dashboard.py")
    print("\nFor more information, refer to the README.md file.")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Set up the Price Tracker project")
    parser.add_argument("--skip-venv", action="store_true", help="Skip virtual environment creation")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    args = parser.parse_args()
    
    print("=== Price Tracker Setup ===")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Set up virtual environment
    if not args.skip_venv and not setup_virtual_env():
        return False
    
    # Install dependencies
    if not args.skip_deps and not install_dependencies():
        return False
    
    # Set up .env file
    if not setup_env_file():
        return False
    
    # Show next steps
    show_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 