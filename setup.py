#!/usr/bin/env python3
"""
Unified setup script for League of Legends Team Optimizer.

This script provides a simple way to set up the application in any environment.
It automatically detects the environment and configures everything appropriately.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main setup function with enhanced error handling and guidance."""
    print("=" * 70)
    print("League of Legends Team Optimizer - Unified Setup")
    print("=" * 70)
    
    try:
        from lol_team_optimizer.unified_setup import setup_application, diagnose_system
        
        # Run unified setup
        setup_result = setup_application()
        
        if setup_result.success:
            print("\n🎉 Setup completed successfully!")
            print(f"   Setup time: {setup_result.setup_time:.2f}s")
            print(f"   Environment: {setup_result.environment}")
            print(f"   API Status: {'Available' if setup_result.api_available else 'Offline Mode'}")
            
            print("\n🚀 Next steps:")
            if setup_result.environment in ['colab', 'jupyter']:
                print("   📓 Notebook Usage:")
                print("      • Use the notebook helper functions")
                print("      • Try: add_player('Name', 'gameName#tag')")
                print("      • Or: optimize_team()")
                print("      • See NOTEBOOK_USAGE.md for examples")
            else:
                print("   💻 Command Line Usage:")
                print("      • Run: python main.py")
                print("      • Or: python -m lol_team_optimizer.streamlined_cli")
                print("   📓 Programmatic Usage:")
                print("      • from lol_team_optimizer.streamlined_cli import StreamlinedCLI")
                print("      • from lol_team_optimizer.core_engine import CoreEngine")
            
            if not setup_result.api_available:
                print("\n💡 To enable full functionality:")
                print("   • Get API key: https://developer.riotgames.com/")
                print("   • Set RIOT_API_KEY environment variable")
                print("   • Or create .env file with your API key")
            
            return 0
        else:
            print("\n❌ Setup failed. Issues found:")
            for i, error in enumerate(setup_result.errors, 1):
                print(f"   {i}. {error}")
            
            print("\n🔧 Troubleshooting:")
            print("   • Run diagnostics: python -c \"from lol_team_optimizer.unified_setup import diagnose_system; diagnose_system()\"")
            print("   • Check dependencies: pip install -r requirements.txt")
            print("   • Verify Python 3.8+ is installed")
            print("   • Ensure you're in the project directory")
            
            return 1
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\n🔧 This usually means:")
        print("   • Missing dependencies - run: pip install -r requirements.txt")
        print("   • Wrong directory - ensure you're in the project root")
        print("   • Python path issues - try: python -m pip install -e .")
        return 1
        
    except Exception as e:
        print(f"\n❌ Setup error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   • Make sure you're in the project directory")
        print("   • Check that all dependencies are installed: pip install -r requirements.txt")
        print("   • Verify your Python version is 3.8+: python --version")
        print("   • Check file permissions for data directory")
        print("   • For detailed diagnostics, run the diagnose_system() function")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)