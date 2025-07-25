#!/usr/bin/env python3
"""
Main entry point for the League of Legends Team Optimizer application.

This module provides the main application flow with comprehensive error handling,
graceful degradation, and proper component integration.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lol_team_optimizer.cli import CLI
from lol_team_optimizer.config import Config


def setup_logging(config: Config) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        config: Application configuration
    """
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(config.data_directory) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout) if config.debug else logging.NullHandler()
        ]
    )


def check_environment() -> tuple[bool, list[str]]:
    """
    Check if the environment is properly set up for the application.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    warnings = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check for required environment variables
    riot_api_key = os.getenv('RIOT_API_KEY')
    if not riot_api_key:
        warnings.append("RIOT_API_KEY environment variable not set - running in offline mode")
    elif len(riot_api_key) < 10:  # Basic validation
        warnings.append("RIOT_API_KEY appears to be invalid - API features may not work")
    
    # Check for required packages
    required_packages = {
        'requests': 'HTTP client for API calls',
        'numpy': 'Numerical computations',
        'scipy': 'Optimization algorithms'
    }
    
    for package, description in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            errors.append(f"Missing required package '{package}' ({description})")
    
    # Check write permissions for data directory
    try:
        from pathlib import Path
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except (OSError, PermissionError):
        errors.append("Cannot write to data directory - check permissions")
    
    # Print warnings if any
    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    return len(errors) == 0, errors


def handle_startup_errors(errors: list[str]) -> None:
    """
    Handle startup errors with helpful messages.
    
    Args:
        errors: List of error messages
    """
    print("=" * 60)
    print("    League of Legends Team Optimizer - Startup Error")
    print("=" * 60)
    print("\nThe application cannot start due to the following issues:\n")
    
    for i, error in enumerate(errors, 1):
        print(f"{i}. {error}")
    
    print("\nPlease fix these issues and try again.")
    print("\nFor help with setup, please refer to the README.md file.")
    print("=" * 60)


def main() -> int:
    """
    Main application entry point with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Check environment before starting
        env_valid, env_errors = check_environment()
        if not env_valid:
            handle_startup_errors(env_errors)
            return 1
        
        # Initialize configuration
        try:
            config = Config()
        except Exception as e:
            print(f"Configuration error: {e}")
            print("Please check your configuration settings.")
            return 1
        
        # Set up logging
        try:
            setup_logging(config)
            logger = logging.getLogger(__name__)
            logger.info("Application starting up")
        except Exception as e:
            print(f"Warning: Could not set up logging: {e}")
            logger = None
        
        # Initialize and run CLI
        try:
            cli = CLI()
            cli.main()
            
            if logger:
                logger.info("Application shutdown normally")
            
            return 0
            
        except KeyboardInterrupt:
            print("\n\nApplication interrupted by user.")
            if logger:
                logger.info("Application interrupted by user")
            return 0
            
        except Exception as e:
            print(f"\nFatal application error: {e}")
            if logger:
                logger.error(f"Fatal application error: {e}", exc_info=True)
            
            if config and config.debug:
                import traceback
                traceback.print_exc()
            
            return 1
    
    except Exception as e:
        # Last resort error handling
        print(f"Critical startup error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)