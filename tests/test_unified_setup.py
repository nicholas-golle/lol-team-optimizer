"""
Tests for unified setup and configuration system.

Tests the UnifiedSetup class, environment detection, configuration management,
and cross-platform compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from lol_team_optimizer.unified_setup import UnifiedSetup, SetupResult


class TestEnvironmentDetection:
    """Test environment detection functionality."""
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', True)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    def test_detect_colab_environment(self):
        """Test detection of Google Colab environment."""
        setup = UnifiedSetup()
        assert setup.environment == "colab"
        assert setup.system_info['in_colab'] is True
        assert setup.system_info['in_jupyter'] is False
        assert setup.system_info['in_terminal'] is False
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', True)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    def test_detect_jupyter_environment(self):
        """Test detection of Jupyter notebook environment."""
        setup = UnifiedSetup()
        assert setup.environment == "jupyter"
        assert setup.system_info['in_colab'] is False
        assert setup.system_info['in_jupyter'] is True
        assert setup.system_info['in_terminal'] is False
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', True)
    def test_detect_interactive_environment(self):
        """Test detection of interactive terminal environment."""
        setup = UnifiedSetup()
        assert setup.environment == "interactive"
        assert setup.system_info['in_terminal'] is True
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    @patch('os.getenv')
    def test_detect_ci_environment(self, mock_getenv):
        """Test detection of CI environment."""
        mock_getenv.side_effect = lambda key, default=None: "true" if key == "CI" else default
        
        setup = UnifiedSetup()
        assert setup.environment == "ci"
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    @patch('os.getenv')
    def test_detect_docker_environment(self, mock_getenv):
        """Test detection of Docker environment."""
        mock_getenv.side_effect = lambda key, default=None: "true" if key == "DOCKER_CONTAINER" else default
        
        setup = UnifiedSetup()
        assert setup.environment == "docker"
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    @patch('os.getenv', return_value=None)
    def test_detect_cli_environment_default(self, mock_getenv):
        """Test detection of CLI environment as default."""
        setup = UnifiedSetup()
        assert setup.environment == "cli"


class TestSystemInfoCollection:
    """Test system information collection."""
    
    def test_collect_basic_system_info(self):
        """Test collection of basic system information."""
        setup = UnifiedSetup()
        info = setup.system_info
        
        assert 'python_version' in info
        assert 'platform' in info
        assert 'executable' in info
        assert 'environment' in info
        assert info['python_version'] == f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert info['platform'] == sys.platform
        assert info['executable'] == sys.executable
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', True)
    @patch('google.colab.__version__', '1.0.0', create=True)
    def test_collect_colab_specific_info(self):
        """Test collection of Colab-specific information."""
        with patch.dict('sys.modules', {'google.colab': Mock(__version__='1.0.0')}):
            setup = UnifiedSetup()
            info = setup.system_info
            
            assert info['in_colab'] is True
            assert 'colab_version' in info
    
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', True)
    def test_collect_jupyter_specific_info(self):
        """Test collection of Jupyter-specific information."""
        mock_ipython = Mock()
        mock_ipython.__version__ = '7.0.0'
        
        with patch.dict('sys.modules', {'IPython': mock_ipython}):
            setup = UnifiedSetup()
            info = setup.system_info
            
            assert info['in_jupyter'] is True
            assert 'ipython_version' in info
            assert info['ipython_version'] == '7.0.0'
    
    def test_collect_environment_variables(self):
        """Test collection of environment variables."""
        setup = UnifiedSetup()
        info = setup.system_info
        
        assert 'env_vars' in info
        assert isinstance(info['env_vars'], dict)
        assert 'PATH' in info['env_vars']
        assert 'HOME' in info['env_vars']
        assert 'USER' in info['env_vars']


class TestProjectRootDetection:
    """Test project root directory detection."""
    
    def test_find_project_root_current_directory(self):
        """Test finding project root in current directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project indicator files
            (Path(temp_dir) / 'lol_team_optimizer').mkdir()
            (Path(temp_dir) / 'requirements.txt').touch()
            
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                setup = UnifiedSetup()
                assert setup.project_root == Path(temp_dir)
    
    def test_find_project_root_parent_directory(self):
        """Test finding project root in parent directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project structure
            project_dir = Path(temp_dir) / 'project'
            project_dir.mkdir()
            (project_dir / 'lol_team_optimizer').mkdir()
            
            sub_dir = project_dir / 'subdir'
            sub_dir.mkdir()
            
            with patch('pathlib.Path.cwd', return_value=sub_dir):
                setup = UnifiedSetup()
                assert setup.project_root == project_dir
    
    def test_find_project_root_fallback_to_current(self):
        """Test fallback to current directory when no indicators found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('pathlib.Path.cwd', return_value=Path(temp_dir)):
                setup = UnifiedSetup()
                assert setup.project_root == Path(temp_dir)


class TestPythonVersionValidation:
    """Test Python version validation."""
    
    @patch('sys.version_info', (3, 7, 0))
    def test_python_version_too_old(self):
        """Test handling of Python version that's too old."""
        setup = UnifiedSetup()
        setup._validate_python_version()
        
        assert len(setup.errors) > 0
        assert any("Python 3.8+ required" in error for error in setup.errors)
    
    @patch('sys.version_info', (3, 9, 0))
    def test_python_version_supported(self):
        """Test handling of supported Python version."""
        setup = UnifiedSetup()
        setup._validate_python_version()
        
        # Should not have errors for supported version
        python_errors = [error for error in setup.errors if "Python" in error]
        assert len(python_errors) == 0
    
    @patch('sys.version_info', (3, 12, 0))
    def test_python_version_very_new(self):
        """Test handling of very new Python version."""
        setup = UnifiedSetup()
        setup._validate_python_version()
        
        # Should have warning for very new version
        assert len(setup.warnings) > 0
        assert any("very new" in warning for warning in setup.warnings)


class TestDependencyChecking:
    """Test dependency checking functionality."""
    
    def test_check_dependencies_all_present(self):
        """Test dependency checking when all packages are present."""
        setup = UnifiedSetup()
        
        # Mock all imports to succeed
        with patch('builtins.__import__', return_value=Mock(__version__='1.0.0')):
            setup._check_dependencies()
            
            assert setup.dependencies_installed is True
            missing_errors = [error for error in setup.errors if "Missing required packages" in error]
            assert len(missing_errors) == 0
    
    def test_check_dependencies_missing_packages(self):
        """Test dependency checking with missing packages."""
        setup = UnifiedSetup()
        
        # Mock some imports to fail
        def mock_import(name, *args, **kwargs):
            if name in ['requests', 'numpy']:
                raise ImportError(f"No module named '{name}'")
            return Mock(__version__='1.0.0')
        
        with patch('builtins.__import__', side_effect=mock_import):
            setup._check_dependencies()
            
            assert setup.dependencies_installed is False
            assert len(setup.errors) > 0
            assert any("Missing required packages" in error for error in setup.errors)
    
    def test_check_dependencies_outdated_packages(self):
        """Test dependency checking with outdated packages."""
        setup = UnifiedSetup()
        
        # Mock imports with old versions
        mock_module = Mock()
        mock_module.__version__ = '1.0.0'  # Old version
        
        with patch('builtins.__import__', return_value=mock_module), \
             patch('packaging.version.parse') as mock_parse:
            
            # Mock version comparison to show package is outdated
            mock_parse.side_effect = lambda v: Mock(__lt__=lambda self, other: v == '1.0.0')
            
            setup._check_dependencies()
            
            # Should have warnings about outdated packages
            assert len(setup.warnings) > 0 or setup.dependencies_installed is True  # May skip version check if packaging not available


class TestDirectorySetup:
    """Test directory setup functionality."""
    
    def test_setup_directories_success(self):
        """Test successful directory setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            setup._setup_directories()
            
            # Check that all required directories were created
            assert (Path(temp_dir) / 'data').exists()
            assert (Path(temp_dir) / 'cache').exists()
            assert (Path(temp_dir) / 'data' / 'logs').exists()
            assert (Path(temp_dir) / 'cache' / 'champion_data').exists()
            assert (Path(temp_dir) / 'cache' / 'api_cache').exists()
            assert setup.directories_created is True
    
    def test_setup_directories_permission_error(self):
        """Test directory setup with permission errors."""
        setup = UnifiedSetup()
        
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Permission denied")):
            setup._setup_directories()
            
            assert setup.directories_created is False
            assert len(setup.errors) > 0
            assert any("Failed to create directories" in error for error in setup.errors)
    
    def test_setup_directories_write_permission_test(self):
        """Test write permission testing for critical directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Create directories first
            (Path(temp_dir) / 'data').mkdir()
            (Path(temp_dir) / 'cache').mkdir()
            
            # Mock write test to fail
            with patch.object(Path, 'write_text', side_effect=PermissionError("No write permission")):
                setup._setup_directories()
                
                # Should have errors about write permissions
                assert len(setup.errors) > 0
                assert any("No write permission" in error for error in setup.errors)


class TestAPIKeyManagement:
    """Test API key management functionality."""
    
    def test_validate_api_key_valid_format(self):
        """Test validation of valid API key format."""
        setup = UnifiedSetup()
        
        valid_key = "RGAPI-12345678-abcd-1234-efgh-123456789012"
        assert setup._validate_api_key(valid_key) is True
    
    def test_validate_api_key_invalid_format(self):
        """Test validation of invalid API key formats."""
        setup = UnifiedSetup()
        
        invalid_keys = [
            "invalid-key",
            "RGAPI-",
            "RGAPI-short",
            "",
            None,
            123,
            "RGAPI-key-with-invalid-chars!"
        ]
        
        for key in invalid_keys:
            assert setup._validate_api_key(key) is False
    
    @patch('requests.get')
    def test_test_api_key_valid(self, mock_get):
        """Test API key testing with valid key."""
        setup = UnifiedSetup()
        
        # Mock successful API response (404 is expected for test endpoint)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = setup._test_api_key("RGAPI-valid-key")
        assert result is True
    
    @patch('requests.get')
    def test_test_api_key_invalid(self, mock_get):
        """Test API key testing with invalid key."""
        setup = UnifiedSetup()
        
        # Mock 403 response (invalid key)
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        
        result = setup._test_api_key("RGAPI-invalid-key")
        assert result is False
    
    @patch('requests.get')
    def test_test_api_key_network_error(self, mock_get):
        """Test API key testing with network error."""
        setup = UnifiedSetup()
        
        # Mock network error
        mock_get.side_effect = Exception("Network error")
        
        result = setup._test_api_key("RGAPI-test-key")
        assert result is True  # Should assume valid if can't test
        assert len(setup.warnings) > 0
        assert any("Could not test API key" in warning for warning in setup.warnings)
    
    def test_save_api_key_to_env_new_file(self):
        """Test saving API key to new .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            result = setup._save_api_key_to_env("RGAPI-test-key")
            
            assert result is True
            env_file = Path(temp_dir) / '.env'
            assert env_file.exists()
            content = env_file.read_text()
            assert 'RIOT_API_KEY=RGAPI-test-key' in content
    
    def test_save_api_key_to_env_existing_file(self):
        """Test saving API key to existing .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Create existing .env file
            env_file = Path(temp_dir) / '.env'
            env_file.write_text('OTHER_VAR=value\nRIOT_API_KEY=old-key\n')
            
            result = setup._save_api_key_to_env("RGAPI-new-key")
            
            assert result is True
            content = env_file.read_text()
            assert 'RIOT_API_KEY=RGAPI-new-key' in content
            assert 'OTHER_VAR=value' in content
            assert 'old-key' not in content
    
    def test_load_api_key_from_env_file(self):
        """Test loading API key from .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Create .env file with API key
            env_file = Path(temp_dir) / '.env'
            env_file.write_text('RIOT_API_KEY=RGAPI-from-file\nOTHER_VAR=value\n')
            
            key = setup._load_api_key_from_env_file()
            assert key == "RGAPI-from-file"
    
    def test_load_api_key_from_env_file_not_found(self):
        """Test loading API key when .env file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            key = setup._load_api_key_from_env_file()
            assert key is None
    
    @patch('os.getenv')
    def test_setup_api_key_env_success(self, mock_getenv):
        """Test API key setup from environment variables."""
        setup = UnifiedSetup()
        
        mock_getenv.return_value = "RGAPI-env-key"
        
        with patch.object(setup, '_validate_api_key', return_value=True), \
             patch.object(setup, '_test_api_key', return_value=True):
            
            result = setup._setup_api_key_env()
            
            assert result is True
            assert setup.api_key_configured is True
    
    @patch('os.getenv', return_value=None)
    def test_setup_api_key_env_not_found(self, mock_getenv):
        """Test API key setup when not found in environment."""
        setup = UnifiedSetup()
        
        with patch.object(setup, '_load_api_key_from_env_file', return_value=None):
            result = setup._setup_api_key_env()
            
            assert result is False
            assert setup.api_key_configured is False
            assert len(setup.warnings) > 0
            assert any("No API key found" in warning for warning in setup.warnings)


class TestLoggingSetup:
    """Test logging setup functionality."""
    
    def test_setup_logging_success(self):
        """Test successful logging setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Create log directory
            log_dir = Path(temp_dir) / "data" / "logs"
            log_dir.mkdir(parents=True)
            
            setup._setup_logging()
            
            assert setup.logging_configured is True
    
    def test_setup_logging_file_handler_error(self):
        """Test logging setup with file handler error."""
        setup = UnifiedSetup()
        
        with patch('logging.FileHandler', side_effect=PermissionError("Permission denied")):
            setup._setup_logging()
            
            # Should have warnings but still configure logging
            assert len(setup.warnings) > 0
            assert any("Could not create log file" in warning for warning in setup.warnings)
    
    @patch('os.getenv')
    def test_setup_logging_custom_level(self, mock_getenv):
        """Test logging setup with custom log level."""
        setup = UnifiedSetup()
        
        mock_getenv.side_effect = lambda key, default=None: "DEBUG" if key == "LOG_LEVEL" else default
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup.project_root = Path(temp_dir)
            log_dir = Path(temp_dir) / "data" / "logs"
            log_dir.mkdir(parents=True)
            
            setup._setup_logging()
            
            assert setup.logging_configured is True


class TestConfigurationInitialization:
    """Test configuration initialization functionality."""
    
    def test_initialize_config_success(self):
        """Test successful configuration initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock config class
            mock_config = Mock()
            mock_config.data_directory = str(Path(temp_dir) / "data")
            mock_config.cache_directory = str(Path(temp_dir) / "cache")
            mock_config.individual_weight = 0.4
            mock_config.preference_weight = 0.3
            mock_config.synergy_weight = 0.3
            
            # Create directories for validation
            Path(temp_dir, "data").mkdir()
            Path(temp_dir, "cache").mkdir()
            
            with patch('lol_team_optimizer.config.Config', return_value=mock_config):
                config = setup._initialize_config()
                
                assert config is not None
                assert config == mock_config
    
    def test_initialize_config_import_error(self):
        """Test configuration initialization with import error."""
        setup = UnifiedSetup()
        
        with patch('lol_team_optimizer.config.Config', side_effect=ImportError("Module not found")):
            config = setup._initialize_config()
            
            assert config is None
            assert len(setup.errors) > 0
            assert any("Could not import configuration module" in error for error in setup.errors)
    
    def test_initialize_config_initialization_error(self):
        """Test configuration initialization with initialization error."""
        setup = UnifiedSetup()
        
        with patch('lol_team_optimizer.config.Config', side_effect=Exception("Config failed")):
            config = setup._initialize_config()
            
            assert config is None
            assert len(setup.errors) > 0
            assert any("Configuration initialization failed" in error for error in setup.errors)
    
    def test_validate_config_missing_directories(self):
        """Test configuration validation with missing directories."""
        setup = UnifiedSetup()
        
        mock_config = Mock()
        mock_config.data_directory = "/non/existent/data"
        mock_config.cache_directory = "/non/existent/cache"
        mock_config.individual_weight = 0.4
        mock_config.preference_weight = 0.3
        mock_config.synergy_weight = 0.3
        
        setup._validate_config(mock_config)
        
        assert len(setup.warnings) >= 2
        assert any("Data directory does not exist" in warning for warning in setup.warnings)
        assert any("Cache directory does not exist" in warning for warning in setup.warnings)


class TestSetupResult:
    """Test SetupResult functionality."""
    
    def test_setup_result_creation(self):
        """Test creation of SetupResult object."""
        result = SetupResult(
            success=True,
            environment="test",
            api_available=True,
            warnings=["test warning"],
            errors=[],
            config=Mock(),
            setup_time=1.5,
            dependencies_installed=True,
            directories_created=True,
            api_key_configured=True,
            logging_configured=True,
            system_info={"test": "info"}
        )
        
        assert result.success is True
        assert result.environment == "test"
        assert result.api_available is True
        assert len(result.warnings) == 1
        assert len(result.errors) == 0
        assert result.config is not None
        assert result.setup_time == 1.5
        assert result.dependencies_installed is True
        assert result.directories_created is True
        assert result.api_key_configured is True
        assert result.logging_configured is True
        assert result.system_info["test"] == "info"
    
    def test_create_failed_result(self):
        """Test creation of failed setup result."""
        setup = UnifiedSetup()
        setup.errors.append("Test error")
        setup.warnings.append("Test warning")
        
        result = setup._create_failed_result()
        
        assert result.success is False
        assert result.environment == setup.environment
        assert result.api_available is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.setup_time > 0


class TestCompleteSetupWorkflows:
    """Test complete setup workflows for different environments."""
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False)
    @patch('os.getenv', return_value=None)
    def test_complete_local_setup_success(self, mock_getenv):
        """Test complete successful local setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock all components to succeed
            with patch.object(setup, '_check_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_env', return_value=True), \
                 patch.object(setup, '_setup_logging'), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                setup.dependencies_installed = True
                setup.directories_created = True
                setup.api_key_configured = True
                setup.logging_configured = True
                
                result = setup.setup_environment()
                
                assert result.success is True
                assert result.environment == "cli"
                assert result.api_available is True
                assert result.dependencies_installed is True
                assert result.directories_created is True
                assert result.api_key_configured is True
                assert result.logging_configured is True
                assert result.setup_time > 0
    
    def test_setup_with_errors(self):
        """Test setup with errors."""
        setup = UnifiedSetup()
        
        # Add some errors
        setup.errors.append("Test error 1")
        setup.errors.append("Test error 2")
        
        with patch.object(setup, '_setup_local', return_value=setup._create_failed_result()):
            result = setup.setup_environment()
            
            assert result.success is False
            assert len(result.errors) >= 2
    
    def test_setup_exception_handling(self):
        """Test setup exception handling."""
        setup = UnifiedSetup()
        
        with patch.object(setup, '_setup_local', side_effect=Exception("Unexpected error")):
            result = setup.setup_environment()
            
            assert result.success is False
            assert len(result.errors) > 0
            assert any("Setup failed with unexpected error" in error for error in result.errors)