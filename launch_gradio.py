#!/usr/bin/env python3
"""
Standalone launcher for LoL Team Optimizer Gradio UI

This script provides an easy way to launch the Gradio interface locally
with proper environment setup and error handling.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'gradio',
        'plotly',
        'pandas',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages


def install_dependencies(missing_packages):
    """Install missing dependencies."""
    if not missing_packages:
        return True
    
    print(f"📦 Installing missing packages: {', '.join(missing_packages)}")
    
    try:
        # Try to install from requirements file first
        if Path('requirements_gradio.txt').exists():
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                '-r', 'requirements_gradio.txt'
            ])
        else:
            # Install individual packages
            for package in missing_packages:
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package
                ])
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def setup_environment():
    """Set up the environment for the Gradio UI."""
    # Add current directory to Python path
    current_dir = Path(__file__).parent.absolute()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Add lol_team_optimizer to path if it exists
    lol_dir = current_dir / 'lol_team_optimizer'
    if lol_dir.exists() and str(lol_dir) not in sys.path:
        sys.path.insert(0, str(lol_dir))
    
    # Set up environment variables
    if not os.getenv('RIOT_API_KEY'):
        print("⚠️ RIOT_API_KEY not found in environment variables")
        print("Some features may not work without a valid API key")
        print("Get your API key from: https://developer.riotgames.com/")


def main():
    """Main launcher function."""
    parser = argparse.ArgumentParser(
        description="Launch LoL Team Optimizer Gradio UI"
    )
    parser.add_argument(
        '--share', 
        action='store_true',
        help='Enable public sharing (creates a public URL)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=7860,
        help='Port to run the server on (default: 7860)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--no-install',
        action='store_true',
        help='Skip dependency installation check'
    )
    
    args = parser.parse_args()
    
    print("🎮 LoL Team Optimizer - Gradio UI Launcher")
    print("=" * 50)
    
    # Check and install dependencies
    if not args.no_install:
        print("🔍 Checking dependencies...")
        missing = check_dependencies()
        
        if missing:
            print(f"📦 Missing packages: {', '.join(missing)}")
            if not install_dependencies(missing):
                print("❌ Failed to install dependencies. Exiting.")
                return 1
        else:
            print("✅ All dependencies are installed")
    
    # Set up environment
    print("🔧 Setting up environment...")
    setup_environment()
    
    # Import and launch the UI
    try:
        print("🚀 Launching Gradio interface...")
        
        # Import after environment setup
        from gradio_ui import launch_ui
        
        # Launch with specified parameters
        launch_ui(
            share=args.share,
            server_port=args.port
        )
        
    except ImportError as e:
        print(f"❌ Failed to import Gradio UI: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you're in the correct directory")
        print("2. Verify that gradio_ui.py exists")
        print("3. Check that lol_team_optimizer module is available")
        print("4. Try running with --no-install to skip dependency checks")
        return 1
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        return 0
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)