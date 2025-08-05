#!/usr/bin/env python3
"""
Main entry point for the League of Legends Team Optimizer application.

Provides a streamlined entry point that uses the unified setup system
and launches the consolidated CLI interface.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lol_team_optimizer.unified_setup import setup_application
from lol_team_optimizer.streamlined_cli import StreamlinedCLI


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Run unified setup
        setup_result = setup_application()
        
        if not setup_result.success:
            print("\n❌ Setup failed. Please fix the errors above and try again.")
            return 1
        
        # Launch streamlined CLI
        print("\n🚀 Starting League of Legends Team Optimizer...")
        
        if not setup_result.api_available:
            print("   ⚠️ Running in offline mode (limited functionality)")
        
        cli = StreamlinedCLI()
        cli.main()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Application interrupted by user.")
        return 0
        
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("💡 Try: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        print("💡 For diagnostics, check your setup and dependencies")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)