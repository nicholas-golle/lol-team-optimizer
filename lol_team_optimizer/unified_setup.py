"""
Unified setup and configuration system for League of Legends Team Optimizer.

This module consolidates setup functionality across all environments (local, Colab, etc.)
and provides a single configuration system that works everywhere. It provides comprehensive 
error handling and unified API key management across all interfaces.
"""

import os
import sys
import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, field
from getpass import getpass
import warnings

# Environment detection
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

try:
    import IPython
    IN_JUPYTER = True
except ImportError:
    IN_JUPYTER = False

# Check if running in a terminal
IN_TERMINAL = hasattr(sys, 'ps1') or (hasattr(sys.stdin, 'isatty') and sys.stdin.isatty())


@dataclass
class SetupResult:
    """Result of setup process with comprehensive status information."""
    success: bool
    environment: str
    api_available: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    config: Optional[Any] = None
    setup_time: float = 0.0
    dependencies_installed: bool = False
    directories_created: bool = False
    api_key_configured: bool = False
    logging_configured: bool = False
    system_info: Dict[str, Any] = field(default_factory=dict)


class UnifiedSetup:
    """
    Unified setup system that works across all environments.
    
    Provides:
    - Automatic environment detection
    - Comprehensive error handling and user guidance
    - Unified API key management across all interfaces
    - Single configuration system for all environments
    """
    
    def __init__(self):
        import time
        self.start_time = time.time()
        self.environment = self._detect_environment()
        self.project_root = self._find_project_root()
        self.warnings = []
        self.errors = []
        self.system_info = self._collect_system_info()
        
        # Setup state tracking
        self.dependencies_installed = False
        self.directories_created = False
        self.api_key_configured = False
        self.logging_configured = False
    
    def _detect_environment(self) -> str:
        """Detect the current environment with enhanced detection."""
        if IN_COLAB:
            return "colab"
        elif IN_JUPYTER:
            return "jupyter"
        elif IN_TERMINAL:
            return "interactive"
        elif os.getenv('CI'):
            return "ci"
        elif os.getenv('DOCKER_CONTAINER'):
            return "docker"
        else:
            return "cli"
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect comprehensive system information for diagnostics."""
        info = {
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'platform': sys.platform,
            'executable': sys.executable,
            'environment': self.environment,
            'in_colab': IN_COLAB,
            'in_jupyter': IN_JUPYTER,
            'in_terminal': IN_TERMINAL,
        }
        
        # Add environment-specific info
        if IN_COLAB:
            info['colab_version'] = getattr(google.colab, '__version__', 'unknown')
        
        if IN_JUPYTER:
            try:
                import IPython
                info['ipython_version'] = IPython.__version__
            except:
                pass
        
        # Add environment variables (non-sensitive)
        env_vars = ['PATH', 'PYTHONPATH', 'HOME', 'USER', 'CI', 'DOCKER_CONTAINER']
        info['env_vars'] = {var: os.getenv(var, 'not_set') for var in env_vars}
        
        return info
    
    def _find_project_root(self) -> Path:
        """Find the project root directory."""
        current = Path.cwd()
        
        # Look for project indicators
        indicators = ['lol_team_optimizer', 'requirements.txt', 'main.py']
        
        # Check current directory first
        if any((current / indicator).exists() for indicator in indicators):
            return current
        
        # Check parent directories
        for parent in current.parents:
            if any((parent / indicator).exists() for indicator in indicators):
                return parent
        
        # Default to current directory
        return current
    
    def setup_environment(self) -> SetupResult:
        """Set up the environment with automatic detection and configuration."""
        print(f"🚀 Setting up League of Legends Team Optimizer...")
        print(f"   Environment: {self.environment.title()}")
        print(f"   Project root: {self.project_root}")
        print(f"   Python: {self.system_info['python_version']} ({self.system_info['platform']})")
        
        # Pre-setup validation
        self._validate_python_version()
        
        # Environment-specific setup
        try:
            if self.environment == "colab":
                result = self._setup_colab()
            elif self.environment == "jupyter":
                result = self._setup_jupyter()
            elif self.environment == "ci":
                result = self._setup_ci()
            elif self.environment == "docker":
                result = self._setup_docker()
            else:
                result = self._setup_local()
            
            # Add timing and system info to result
            import time
            result.setup_time = time.time() - self.start_time
            result.system_info = self.system_info
            result.dependencies_installed = self.dependencies_installed
            result.directories_created = self.directories_created
            result.api_key_configured = self.api_key_configured
            result.logging_configured = self.logging_configured
            
            return result
            
        except Exception as e:
            self.errors.append(f"Setup failed with unexpected error: {e}")
            return self._create_failed_result()
    
    def _validate_python_version(self) -> None:
        """Validate Python version requirements."""
        if sys.version_info < (3, 8):
            self.errors.append(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        elif sys.version_info >= (3, 12):
            self.warnings.append(f"Python {sys.version_info.major}.{sys.version_info.minor} is very new - some dependencies may not be fully compatible")
    
    def _create_failed_result(self) -> SetupResult:
        """Create a failed setup result with current state."""
        import time
        return SetupResult(
            success=False,
            environment=self.environment,
            api_available=False,
            warnings=self.warnings,
            errors=self.errors,
            setup_time=time.time() - self.start_time,
            system_info=self.system_info,
            dependencies_installed=self.dependencies_installed,
            directories_created=self.directories_created,
            api_key_configured=self.api_key_configured,
            logging_configured=self.logging_configured
        )
    
    def _setup_colab(self) -> SetupResult:
        """Set up Google Colab environment with comprehensive error handling."""
        print("\n📦 Colab Environment Setup:")
        
        # Clone repository if needed
        if not (self.project_root / "lol_team_optimizer").exists():
            try:
                print("   Cloning repository...")
                result = subprocess.run(
                    ["git", "clone", "https://github.com/nicholas-golle/lol-team-optimizer.git"],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    os.chdir("lol-team-optimizer")
                    self.project_root = Path.cwd()
                    print("   ✅ Repository cloned")
                else:
                    self.errors.append(f"Git clone failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                self.errors.append("Repository clone timed out")
            except Exception as e:
                self.errors.append(f"Failed to clone repository: {e}")
        
        # Install dependencies with better error handling
        self._install_colab_dependencies()
        
        # Set up directories and API
        self._setup_directories()
        api_available = self._setup_api_key_interactive()
        
        # Initialize configuration
        config = self._initialize_config()
        
        return SetupResult(
            success=len(self.errors) == 0,
            environment=self.environment,
            api_available=api_available,
            warnings=self.warnings,
            errors=self.errors,
            config=config
        )
    
    def _install_colab_dependencies(self) -> None:
        """Install dependencies for Colab with comprehensive error handling."""
        required_packages = [
            "requests>=2.25.0",
            "python-dotenv>=0.19.0", 
            "numpy>=1.21.0",
            "scipy>=1.7.0"
        ]
        
        try:
            print("   Installing dependencies...")
            for package in required_packages:
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-q", package],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.returncode != 0:
                        self.warnings.append(f"Failed to install {package}: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self.warnings.append(f"Installation of {package} timed out")
            
            self.dependencies_installed = True
            print("   ✅ Dependencies installed")
            
        except Exception as e:
            self.warnings.append(f"Dependency installation error: {e}")
            self.dependencies_installed = False
    
    def _setup_jupyter(self) -> SetupResult:
        """Set up Jupyter notebook environment."""
        print("\n📓 Jupyter Environment Setup:")
        
        # Check if we're in the right directory
        if not (self.project_root / "lol_team_optimizer").exists():
            self.warnings.append("Project files not found in current directory")
            print("   ⚠️ Project files not found - you may need to clone the repository")
            print("   💡 Try: git clone https://github.com/nicholas-golle/lol-team-optimizer.git")
        
        # Check dependencies
        self._check_dependencies()
        
        # Set up directories and API
        self._setup_directories()
        api_available = self._setup_api_key_interactive()
        
        # Initialize configuration
        config = self._initialize_config()
        
        return SetupResult(
            success=len(self.errors) == 0,
            environment=self.environment,
            api_available=api_available,
            warnings=self.warnings,
            errors=self.errors,
            config=config
        )
    
    def _setup_ci(self) -> SetupResult:
        """Set up CI/CD environment."""
        print("\n🔧 CI Environment Setup:")
        
        # Check dependencies
        self._check_dependencies()
        
        # Set up directories
        self._setup_directories()
        
        # API key from environment only (no interactive prompts)
        api_available = self._setup_api_key_env()
        
        # Set up logging for CI
        self._setup_logging()
        
        # Initialize configuration
        config = self._initialize_config()
        
        return SetupResult(
            success=len(self.errors) == 0,
            environment=self.environment,
            api_available=api_available,
            warnings=self.warnings,
            errors=self.errors,
            config=config
        )
    
    def _setup_docker(self) -> SetupResult:
        """Set up Docker container environment."""
        print("\n🐳 Docker Environment Setup:")
        
        # Check dependencies (should be pre-installed in container)
        self._check_dependencies()
        
        # Set up directories
        self._setup_directories()
        
        # API key from environment only
        api_available = self._setup_api_key_env()
        
        # Set up logging
        self._setup_logging()
        
        # Initialize configuration
        config = self._initialize_config()
        
        return SetupResult(
            success=len(self.errors) == 0,
            environment=self.environment,
            api_available=api_available,
            warnings=self.warnings,
            errors=self.errors,
            config=config
        )
    
    def _setup_local(self) -> SetupResult:
        """Set up local CLI environment with enhanced error handling."""
        print("\n💻 Local Environment Setup:")
        
        # Check required packages
        self._check_dependencies()
        
        # Set up directories
        self._setup_directories()
        
        # Set up API key (try interactive if in terminal, otherwise env only)
        if IN_TERMINAL and not os.getenv('RIOT_API_KEY'):
            print("\n🔑 API Key Setup:")
            print("   No API key found in environment variables.")
            try:
                response = input("   Would you like to set up your API key now? (y/n): ").lower().strip()
                if response in ['y', 'yes']:
                    api_available = self._setup_api_key_interactive()
                else:
                    print("   ⚠️ Continuing without API key - limited functionality available")
                    api_available = False
            except (EOFError, KeyboardInterrupt):
                print("   ⚠️ Skipping API key setup - limited functionality available")
                api_available = False
        else:
            api_available = self._setup_api_key_env()
        
        # Set up logging
        self._setup_logging()
        
        # Initialize configuration
        config = self._initialize_config()
        
        return SetupResult(
            success=len(self.errors) == 0,
            environment=self.environment,
            api_available=api_available,
            warnings=self.warnings,
            errors=self.errors,
            config=config
        )
    
    def _check_dependencies(self) -> None:
        """Check for required dependencies with version validation."""
        required_packages = {
            'requests': {'description': 'HTTP client for API calls', 'min_version': '2.25.0'},
            'numpy': {'description': 'Numerical computations', 'min_version': '1.21.0'},
            'scipy': {'description': 'Optimization algorithms', 'min_version': '1.7.0'},
            'dotenv': {'description': 'Environment variable management', 'min_version': '0.19.0', 'import_name': 'dotenv'}
        }
        
        missing_packages = []
        outdated_packages = []
        
        for package, info in required_packages.items():
            import_name = info.get('import_name', package)
            try:
                module = __import__(import_name)
                
                # Check version if available
                if hasattr(module, '__version__'):
                    try:
                        from packaging import version
                        if version.parse(module.__version__) < version.parse(info['min_version']):
                            outdated_packages.append(f"{package} {module.__version__} (need {info['min_version']}+)")
                    except ImportError:
                        # packaging not available, skip version check
                        pass
                    except Exception:
                        # Version parsing failed, continue
                        pass
                        
            except ImportError:
                missing_packages.append(f"{package} ({info['description']})")
        
        if missing_packages:
            self.errors.append(f"Missing required packages: {', '.join(missing_packages)}")
            print("   💡 Install with: pip install " + " ".join(pkg.split(' ')[0] for pkg in missing_packages))
        
        if outdated_packages:
            self.warnings.append(f"Outdated packages: {', '.join(outdated_packages)}")
            print("   💡 Update with: pip install --upgrade " + " ".join(pkg.split(' ')[0] for pkg in outdated_packages))
        
        if not missing_packages:
            self.dependencies_installed = True
            print("   ✅ All dependencies available")
    
    def _setup_directories(self) -> None:
        """Set up required directories with comprehensive error handling."""
        required_directories = {
            'data': 'Main data storage',
            'cache': 'API response cache',
            'data/logs': 'Application logs',
            'cache/champion_data': 'Champion information cache',
            'cache/api_cache': 'API response cache'
        }
        
        created_dirs = []
        failed_dirs = []
        
        try:
            for dir_name, description in required_directories.items():
                dir_path = self.project_root / dir_name
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_name)
                except (OSError, PermissionError) as e:
                    failed_dirs.append(f"{dir_name} ({e})")
            
            # Test write permissions for critical directories
            critical_dirs = ['data', 'cache']
            for dir_name in critical_dirs:
                try:
                    test_file = self.project_root / dir_name / ".write_test"
                    test_file.write_text("test")
                    test_file.unlink()
                except (OSError, PermissionError) as e:
                    self.errors.append(f"No write permission for {dir_name} directory: {e}")
            
            if failed_dirs:
                self.errors.append(f"Failed to create directories: {', '.join(failed_dirs)}")
            else:
                self.directories_created = True
                print(f"   ✅ Directories created ({len(created_dirs)} total)")
            
        except Exception as e:
            self.errors.append(f"Directory setup failed: {e}")
    
    def _setup_api_key_interactive(self) -> bool:
        """Set up API key interactively with comprehensive validation and guidance."""
        print("\n🔑 API Key Setup:")
        print("   Get your free API key from: https://developer.riotgames.com/")
        
        # Check if API key already exists
        existing_key = os.getenv('RIOT_API_KEY')
        if existing_key and self._validate_api_key(existing_key):
            print("   ✅ API key already configured!")
            self.api_key_configured = True
            return True
        elif existing_key:
            print("   ⚠️ Found API key but it appears invalid")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    print(f"   Attempt {attempt + 1}/{max_attempts}")
                
                api_key = getpass("   Enter your Riot API key (input hidden): ").strip()
                
                if not api_key:
                    print("   ⚠️ No API key entered")
                    continue
                
                if self._validate_api_key(api_key):
                    # Test the API key
                    if self._test_api_key(api_key):
                        os.environ['RIOT_API_KEY'] = api_key
                        
                        # Save to .env file with proper format
                        if self._save_api_key_to_env(api_key):
                            print("   ✅ API key configured and saved!")
                        else:
                            print("   ✅ API key configured for this session!")
                        
                        self.api_key_configured = True
                        return True
                    else:
                        print("   ❌ API key validation failed - key may be expired or invalid")
                        if attempt < max_attempts - 1:
                            print("   💡 Please check your key at https://developer.riotgames.com/")
                else:
                    print("   ❌ Invalid API key format (should start with RGAPI-)")
                    if attempt < max_attempts - 1:
                        print("   💡 API keys start with 'RGAPI-' followed by your unique key")
                        
            except (EOFError, KeyboardInterrupt):
                print("   ⚠️ API key setup cancelled")
                break
            except Exception as e:
                self.warnings.append(f"API key setup error: {e}")
                print(f"   ❌ Error during setup: {e}")
        
        print("   ⚠️ Continuing without API key - limited functionality available")
        print("   💡 You can set RIOT_API_KEY environment variable later")
        return False
    
    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key format."""
        return (
            isinstance(api_key, str) and 
            api_key.startswith('RGAPI-') and 
            len(api_key) > 10 and
            all(c.isalnum() or c in '-_' for c in api_key)
        )
    
    def _test_api_key(self, api_key: str) -> bool:
        """Test API key by making a simple API call."""
        try:
            import requests
            
            # Test with a simple endpoint
            headers = {'X-Riot-Token': api_key}
            response = requests.get(
                'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/test/test',
                headers=headers,
                timeout=10
            )
            
            # 404 is expected for non-existent user, but means API key works
            # 403 means API key is invalid
            return response.status_code != 403
            
        except Exception as e:
            self.warnings.append(f"Could not test API key: {e}")
            return True  # Assume valid if we can't test
    
    def _save_api_key_to_env(self, api_key: str) -> bool:
        """Save API key to .env file with proper format."""
        try:
            env_file = self.project_root / '.env'
            
            # Read existing .env content
            existing_content = ""
            if env_file.exists():
                existing_content = env_file.read_text()
            
            # Update or add API key
            lines = existing_content.split('\n')
            api_key_line = f'RIOT_API_KEY={api_key}'
            
            # Replace existing API key line or add new one
            found = False
            for i, line in enumerate(lines):
                if line.startswith('RIOT_API_KEY='):
                    lines[i] = api_key_line
                    found = True
                    break
            
            if not found:
                lines.append(api_key_line)
            
            # Write back to file
            env_file.write_text('\n'.join(lines))
            return True
            
        except Exception as e:
            self.warnings.append(f"Could not save API key to .env file: {e}")
            return False
    
    def _setup_api_key_env(self) -> bool:
        """Set up API key from environment variables with comprehensive validation."""
        # Try multiple sources for API key
        api_key = (
            os.getenv('RIOT_API_KEY') or
            os.getenv('RIOT_TOKEN') or  # Alternative name
            self._load_api_key_from_env_file()
        )
        
        if not api_key:
            self.warnings.append("No API key found in environment variables or .env file")
            print("   ⚠️ No API key found - running in offline mode")
            print("   💡 Set RIOT_API_KEY environment variable or create .env file")
            return False
        
        if not self._validate_api_key(api_key):
            self.warnings.append("API key format appears invalid - should start with RGAPI-")
            print("   ⚠️ API key format appears invalid")
            return False
        
        # Test the API key if possible
        if self._test_api_key(api_key):
            print("   ✅ API key found and validated")
            self.api_key_configured = True
            return True
        else:
            self.warnings.append("API key validation failed - key may be expired")
            print("   ⚠️ API key found but validation failed")
            return False
    
    def _load_api_key_from_env_file(self) -> Optional[str]:
        """Load API key from .env file."""
        try:
            env_file = self.project_root / '.env'
            if env_file.exists():
                content = env_file.read_text()
                for line in content.split('\n'):
                    if line.startswith('RIOT_API_KEY='):
                        return line.split('=', 1)[1].strip()
        except Exception:
            pass
        return None
    
    def _setup_logging(self) -> None:
        """Set up logging with environment-appropriate configuration."""
        try:
            log_dir = self.project_root / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine log level from environment
            log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
            log_level = getattr(logging, log_level_str, logging.INFO)
            
            # Configure logging format
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            # Set up handlers based on environment
            handlers = []
            
            # File handler (always)
            try:
                file_handler = logging.FileHandler(log_dir / "app.log")
                file_handler.setFormatter(formatter)
                handlers.append(file_handler)
            except (OSError, PermissionError) as e:
                self.warnings.append(f"Could not create log file: {e}")
            
            # Console handler (environment dependent)
            if self.environment in ['cli', 'interactive'] or os.getenv('DEBUG', '').lower() == 'true':
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                handlers.append(console_handler)
            
            # Configure root logger
            logging.basicConfig(
                level=log_level,
                handlers=handlers,
                force=True  # Override any existing configuration
            )
            
            # Log setup information
            logger = logging.getLogger(__name__)
            logger.info(f"Logging configured for {self.environment} environment")
            logger.info(f"Log level: {log_level_str}")
            
            self.logging_configured = True
            print(f"   ✅ Logging configured (level: {log_level_str})")
            
        except Exception as e:
            self.warnings.append(f"Could not set up logging: {e}")
            self.logging_configured = False
    
    def _initialize_config(self) -> Optional[Any]:
        """Initialize the application configuration with validation."""
        try:
            # Add project root to Python path if not already there
            project_root_str = str(self.project_root)
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
            
            # Import and initialize configuration
            from lol_team_optimizer.config import Config
            config = Config()
            
            # Validate configuration
            self._validate_config(config)
            
            print("   ✅ Configuration initialized")
            return config
            
        except ImportError as e:
            self.errors.append(f"Could not import configuration module: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Configuration initialization failed: {e}")
            return None
    
    def _validate_config(self, config: Any) -> None:
        """Validate configuration settings."""
        try:
            # Check critical paths exist
            data_path = Path(config.data_directory)
            cache_path = Path(config.cache_directory)
            
            if not data_path.exists():
                self.warnings.append(f"Data directory does not exist: {data_path}")
            
            if not cache_path.exists():
                self.warnings.append(f"Cache directory does not exist: {cache_path}")
            
            # Validate weights
            total_weight = config.individual_weight + config.preference_weight + config.synergy_weight
            if abs(total_weight - 1.0) > 0.001:
                self.warnings.append(f"Performance weights sum to {total_weight:.3f}, should be 1.0")
            
            # Check API configuration
            if config.riot_api_key and not self._validate_api_key(config.riot_api_key):
                self.warnings.append("API key in configuration appears invalid")
            
        except Exception as e:
            self.warnings.append(f"Configuration validation failed: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for diagnostics."""
        status = {
            'environment': self.environment,
            'project_root': str(self.project_root),
            'system_info': self.system_info,
            'setup_state': {
                'dependencies_installed': self.dependencies_installed,
                'directories_created': self.directories_created,
                'api_key_configured': self.api_key_configured,
                'logging_configured': self.logging_configured
            },
            'warnings': self.warnings,
            'errors': self.errors
        }
        
        # Try to get engine status if available
        try:
            from lol_team_optimizer.core_engine import CoreEngine
            engine = CoreEngine()
            
            status.update({
                'api_available': engine.api_available,
                'player_count': engine.system_status.get('player_count', 0),
                'champions_loaded': len(engine.champion_data_manager.champions) if hasattr(engine, 'champion_data_manager') else 0,
                'ready_for_optimization': engine.system_status.get('ready_for_optimization', False),
                'cache_status': self._get_cache_status()
            })
        except Exception as e:
            status['engine_error'] = str(e)
        
        return status
    
    def _get_cache_status(self) -> Dict[str, Any]:
        """Get cache directory status."""
        try:
            cache_dir = self.project_root / 'cache'
            if not cache_dir.exists():
                return {'status': 'not_found'}
            
            # Count cache files
            cache_files = list(cache_dir.rglob('*.json'))
            total_size = sum(f.stat().st_size for f in cache_files if f.exists())
            
            return {
                'status': 'available',
                'file_count': len(cache_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'last_modified': max((f.stat().st_mtime for f in cache_files), default=0)
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def print_setup_summary(self, result: SetupResult) -> None:
        """Print a comprehensive setup summary with detailed status."""
        print("\n" + "=" * 70)
        print("🎉 LEAGUE OF LEGENDS TEAM OPTIMIZER - SETUP COMPLETE")
        print("=" * 70)
        
        # Basic status
        print(f"Environment: {result.environment.title()}")
        print(f"Setup Time: {result.setup_time:.2f}s")
        print(f"Python: {result.system_info.get('python_version', 'unknown')} ({result.system_info.get('platform', 'unknown')})")
        print(f"Project Root: {self.project_root}")
        
        # Component status
        print(f"\n📦 Component Status:")
        print(f"   Dependencies: {'✅' if result.dependencies_installed else '❌'}")
        print(f"   Directories: {'✅' if result.directories_created else '❌'}")
        print(f"   API Key: {'✅' if result.api_key_configured else '⚠️ Offline Mode'}")
        print(f"   Logging: {'✅' if result.logging_configured else '❌'}")
        print(f"   Configuration: {'✅' if result.config else '❌'}")
        
        # Overall status
        print(f"\n🚀 Overall Status: {'✅ Ready' if result.success else '❌ Issues Found'}")
        print(f"   API Access: {'🟢 Available' if result.api_available else '🔴 Offline Mode'}")
        
        # Warnings and errors
        if result.warnings:
            print(f"\n⚠️ Warnings ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"   {i}. {warning}")
        
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"   {i}. {error}")
        
        # Usage instructions
        if result.success:
            print(f"\n🎮 Ready to use! Available interfaces:")
            if result.environment in ['colab', 'jupyter']:
                print("   📓 Notebook Interface:")
                print("      • Use the notebook helper functions")
                print("      • Try: optimize_team(), add_player(), analyze_players()")
                print("      • Or: from lol_team_optimizer.streamlined_cli import StreamlinedCLI")
            else:
                print("   💻 Command Line Interface:")
                print("      • Run: python main.py")
                print("      • Or: python -m lol_team_optimizer.streamlined_cli")
                print("   📓 Programmatic Interface:")
                print("      • from lol_team_optimizer.core_engine import CoreEngine")
                print("      • from lol_team_optimizer.streamlined_cli import StreamlinedCLI")
        else:
            print(f"\n🔧 Setup Issues Found:")
            print("   Please fix the errors above before continuing.")
            print("   For help, visit: https://github.com/nicholas-golle/lol-team-optimizer")
        
        # Additional info
        if not result.api_available:
            print(f"\n💡 API Key Setup:")
            print("   • Get your free API key: https://developer.riotgames.com/")
            print("   • Set RIOT_API_KEY environment variable")
            print("   • Or create .env file with: RIOT_API_KEY=your-key-here")
        
        print("=" * 70)


# Main setup functions
def setup_application(silent: bool = False) -> SetupResult:
    """
    Main setup function - automatically detects environment and sets up accordingly.
    
    Args:
        silent: If True, suppress setup summary output
        
    Returns:
        SetupResult with comprehensive setup information
    """
    setup = UnifiedSetup()
    result = setup.setup_environment()
    
    if not silent:
        setup.print_setup_summary(result)
    
    return result


def quick_status() -> Dict[str, Any]:
    """Get quick system status without full setup."""
    setup = UnifiedSetup()
    return setup.get_system_status()


def diagnose_system() -> None:
    """Run comprehensive system diagnostics and print detailed report."""
    print("🔍 Running System Diagnostics...")
    print("=" * 50)
    
    setup = UnifiedSetup()
    status = setup.get_system_status()
    
    # System information
    print("📊 System Information:")
    for key, value in status['system_info'].items():
        print(f"   {key}: {value}")
    
    # Setup state
    print(f"\n🔧 Setup State:")
    for key, value in status['setup_state'].items():
        icon = "✅" if value else "❌"
        print(f"   {icon} {key.replace('_', ' ').title()}")
    
    # Cache status
    if 'cache_status' in status:
        cache = status['cache_status']
        print(f"\n💾 Cache Status:")
        print(f"   Status: {cache.get('status', 'unknown')}")
        if cache.get('file_count'):
            print(f"   Files: {cache['file_count']}")
            print(f"   Size: {cache['total_size_mb']} MB")
    
    # Issues
    if status['warnings']:
        print(f"\n⚠️ Warnings:")
        for warning in status['warnings']:
            print(f"   • {warning}")
    
    if status['errors']:
        print(f"\n❌ Errors:")
        for error in status['errors']:
            print(f"   • {error}")
    
    print("=" * 50)


def reset_configuration() -> bool:
    """Reset configuration to defaults and clear cache."""
    try:
        setup = UnifiedSetup()
        
        # Clear cache
        cache_dir = setup.project_root / 'cache'
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            print("✅ Cache cleared")
        
        # Remove .env file
        env_file = setup.project_root / '.env'
        if env_file.exists():
            env_file.unlink()
            print("✅ .env file removed")
        
        # Recreate directories
        setup._setup_directories()
        
        print("✅ Configuration reset complete")
        print("💡 Run setup again to reconfigure")
        return True
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False


# Convenience functions for different environments
def setup_for_colab(silent: bool = False):
    """Convenience function for Colab setup with environment validation."""
    if not IN_COLAB:
        print("⚠️ This function is designed for Google Colab")
        print("💡 Use setup_application() for automatic environment detection")
    return setup_application(silent=silent)


def setup_for_jupyter(silent: bool = False):
    """Convenience function for Jupyter setup with environment validation."""
    if not IN_JUPYTER:
        print("⚠️ This function is designed for Jupyter notebooks")
        print("💡 Use setup_application() for automatic environment detection")
    return setup_application(silent=silent)


def setup_for_cli(silent: bool = False):
    """Convenience function for CLI setup."""
    return setup_application(silent=silent)


# End of unified setup module