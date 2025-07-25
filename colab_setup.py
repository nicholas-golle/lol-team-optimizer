"""
Google Colab setup script for League of Legends Team Optimizer.

This script handles the setup and configuration needed to run the optimizer in Google Colab.
"""

import os
import sys
from pathlib import Path

def setup_colab_environment():
    """Set up the environment for Google Colab."""
    print("🚀 Setting up League of Legends Team Optimizer for Google Colab...")
    
    # Install dependencies
    print("📦 Installing dependencies...")
    os.system("pip install requests python-dotenv numpy scipy")
    
    # Set up API key
    print("\n🔑 API Key Setup:")
    print("You'll need a Riot Games API key to use this application.")
    print("Get one from: https://developer.riotgames.com/")
    
    api_key = input("\nEnter your Riot API key (starts with RGAPI-): ").strip()
    
    if api_key and api_key.startswith('RGAPI-'):
        # Set environment variable for this session
        os.environ['RIOT_API_KEY'] = api_key
        
        # Create .env file
        with open('.env', 'w') as f:
            f.write(f'RIOT_API_KEY={api_key}\n')
        
        print("✅ API key configured successfully!")
    else:
        print("⚠️ Invalid API key format. You can set it later.")
        print("Expected format: RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    
    # Create necessary directories
    print("\n📁 Creating directories...")
    Path("data").mkdir(exist_ok=True)
    Path("cache").mkdir(exist_ok=True)
    Path("data/logs").mkdir(exist_ok=True)
    
    print("✅ Setup complete!")
    print("\n🎮 You can now use the League of Legends Team Optimizer!")
    print("\nTo start the application, run:")
    print("from lol_team_optimizer.cli import CLI")
    print("cli = CLI()")
    print("cli.main()")

def quick_demo():
    """Run a quick demo of the optimizer."""
    print("\n🎯 Running Quick Demo...")
    
    try:
        from lol_team_optimizer.cli import CLI
        
        # Test API connectivity
        cli = CLI()
        if cli.api_available:
            print("✅ API connection successful!")
            print(f"✅ Champion data loaded: {len(cli.champion_data_manager.champions)} champions")
        else:
            print("⚠️ API not available - running in offline mode")
        
        print("\n📊 System Status:")
        print(f"  • Data directory: {cli.config.data_directory}")
        print(f"  • Cache directory: {cli.config.cache_directory}")
        print(f"  • API available: {cli.api_available}")
        
        return cli
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        return None

if __name__ == "__main__":
    setup_colab_environment()