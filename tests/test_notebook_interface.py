"""
Tests for the simplified notebook interface.

Tests the notebook-specific functionality, Colab integration, and
interactive features of the streamlined system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path
from datetime import datetime

# Mock notebook environment detection
@pytest.fixture
def mock_colab_environment():
    """Mock Google Colab environment."""
    with patch('lol_team_optimizer.unified_setup.IN_COLAB', True), \
         patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False), \
         patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False):
        yield

@pytest.fixture
def mock_jupyter_environment():
    """Mock Jupyter notebook environment."""
    with patch('lol_team_optimizer.unified_setup.IN_COLAB', False), \
         patch('lol_team_optimizer.unified_setup.IN_JUPYTER', True), \
         patch('lol_team_optimizer.unified_setup.IN_TERMINAL', False):
        yield


class TestNotebookEnvironmentDetection:
    """Test notebook environment detection and setup."""
    
    def test_colab_environment_detection(self, mock_colab_environment):
        """Test detection of Google Colab environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        assert setup.environment == "colab"
        assert setup.system_info['in_colab'] is True
        assert setup.system_info['in_jupyter'] is False
    
    def test_jupyter_environment_detection(self, mock_jupyter_environment):
        """Test detection of Jupyter notebook environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        assert setup.environment == "jupyter"
        assert setup.system_info['in_colab'] is False
        assert setup.system_info['in_jupyter'] is True
    
    @patch('lol_team_optimizer.unified_setup.IN_COLAB', False)
    @patch('lol_team_optimizer.unified_setup.IN_JUPYTER', False)
    @patch('lol_team_optimizer.unified_setup.IN_TERMINAL', True)
    def test_interactive_environment_detection(self):
        """Test detection of interactive terminal environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        assert setup.environment == "interactive"
        assert setup.system_info['in_terminal'] is True


class TestColabSetup:
    """Test Google Colab specific setup functionality."""
    
    @patch('subprocess.run')
    @patch('os.chdir')
    def test_colab_repository_cloning(self, mock_chdir, mock_subprocess, mock_colab_environment):
        """Test repository cloning in Colab environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock successful git clone
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Mock project root detection
        with patch.object(Path, 'exists', return_value=False):  # No existing project
            setup = UnifiedSetup()
            
            with patch.object(setup, '_install_colab_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                result = setup._setup_colab()
                
                # Verify git clone was called
                mock_subprocess.assert_called_with(
                    ["git", "clone", "https://github.com/nicholas-golle/lol-team-optimizer.git"],
                    capture_output=True, text=True, timeout=60
                )
                mock_chdir.assert_called_with("lol-team-optimizer")
    
    @patch('subprocess.run')
    def test_colab_dependency_installation(self, mock_subprocess, mock_colab_environment):
        """Test dependency installation in Colab."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock successful pip install
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        setup = UnifiedSetup()
        setup._install_colab_dependencies()
        
        # Verify pip install was called for required packages
        assert mock_subprocess.call_count >= 4  # At least 4 packages
        
        # Check that pip install was called
        calls = mock_subprocess.call_args_list
        pip_calls = [call for call in calls if 'pip' in str(call)]
        assert len(pip_calls) >= 4
    
    @patch('subprocess.run')
    def test_colab_dependency_installation_failure(self, mock_subprocess, mock_colab_environment):
        """Test handling of dependency installation failure in Colab."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock failed pip install
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Package not found"
        mock_subprocess.return_value = mock_result
        
        setup = UnifiedSetup()
        setup._install_colab_dependencies()
        
        # Should have warnings about failed installations
        assert len(setup.warnings) > 0
        assert any("Failed to install" in warning for warning in setup.warnings)
    
    def test_colab_setup_integration(self, mock_colab_environment):
        """Test complete Colab setup integration."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with patch.object(Path, 'exists', return_value=True):  # Project exists
            setup = UnifiedSetup()
            
            with patch.object(setup, '_install_colab_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                result = setup._setup_colab()
                
                assert isinstance(result, type(setup)._create_failed_result().__class__)
                assert result.environment == "colab"


class TestJupyterSetup:
    """Test Jupyter notebook specific setup functionality."""
    
    def test_jupyter_project_detection(self, mock_jupyter_environment):
        """Test project file detection in Jupyter environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with patch.object(Path, 'exists', return_value=False):  # No project files
            setup = UnifiedSetup()
            
            with patch.object(setup, '_check_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                result = setup._setup_jupyter()
                
                # Should have warning about missing project files
                assert any("Project files not found" in warning for warning in setup.warnings)
    
    def test_jupyter_dependency_check(self, mock_jupyter_environment):
        """Test dependency checking in Jupyter environment."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        # Mock missing dependencies
        with patch('builtins.__import__', side_effect=ImportError("Module not found")):
            setup._check_dependencies()
            
            # Should have errors about missing packages
            assert len(setup.errors) > 0
            assert any("Missing required packages" in error for error in setup.errors)
    
    def test_jupyter_setup_integration(self, mock_jupyter_environment):
        """Test complete Jupyter setup integration."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with patch.object(Path, 'exists', return_value=True):  # Project exists
            setup = UnifiedSetup()
            
            with patch.object(setup, '_check_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                result = setup._setup_jupyter()
                
                assert isinstance(result, type(setup)._create_failed_result().__class__)
                assert result.environment == "jupyter"


class TestNotebookAPIKeySetup:
    """Test API key setup in notebook environments."""
    
    @patch('getpass.getpass')
    @patch('builtins.input')
    def test_interactive_api_key_setup_success(self, mock_input, mock_getpass, mock_jupyter_environment):
        """Test successful interactive API key setup."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock user input
        mock_getpass.return_value = "RGAPI-test-key-12345"
        
        setup = UnifiedSetup()
        
        with patch.object(setup, '_validate_api_key', return_value=True), \
             patch.object(setup, '_test_api_key', return_value=True), \
             patch.object(setup, '_save_api_key_to_env', return_value=True):
            
            result = setup._setup_api_key_interactive()
            
            assert result is True
            assert setup.api_key_configured is True
            mock_getpass.assert_called_once()
    
    @patch('getpass.getpass')
    def test_interactive_api_key_setup_invalid_format(self, mock_getpass, mock_jupyter_environment):
        """Test interactive API key setup with invalid format."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock invalid API key
        mock_getpass.return_value = "invalid-key-format"
        
        setup = UnifiedSetup()
        
        with patch.object(setup, '_validate_api_key', return_value=False):
            result = setup._setup_api_key_interactive()
            
            assert result is False
            assert setup.api_key_configured is False
    
    @patch('getpass.getpass')
    def test_interactive_api_key_setup_keyboard_interrupt(self, mock_getpass, mock_jupyter_environment):
        """Test interactive API key setup with keyboard interrupt."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Mock keyboard interrupt
        mock_getpass.side_effect = KeyboardInterrupt()
        
        setup = UnifiedSetup()
        result = setup._setup_api_key_interactive()
        
        assert result is False
        assert setup.api_key_configured is False
    
    def test_env_api_key_setup(self, mock_jupyter_environment):
        """Test API key setup from environment variables."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with patch('os.getenv', return_value="RGAPI-test-key-12345"):
            setup = UnifiedSetup()
            
            with patch.object(setup, '_validate_api_key', return_value=True), \
                 patch.object(setup, '_test_api_key', return_value=True):
                
                result = setup._setup_api_key_env()
                
                assert result is True
                assert setup.api_key_configured is True


class TestNotebookDirectorySetup:
    """Test directory setup in notebook environments."""
    
    def test_directory_creation_success(self, mock_jupyter_environment):
        """Test successful directory creation."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            setup._setup_directories()
            
            # Check that directories were created
            assert (Path(temp_dir) / 'data').exists()
            assert (Path(temp_dir) / 'cache').exists()
            assert (Path(temp_dir) / 'data' / 'logs').exists()
            assert setup.directories_created is True
    
    def test_directory_creation_permission_error(self, mock_jupyter_environment):
        """Test directory creation with permission errors."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Permission denied")):
            setup._setup_directories()
            
            # Should have errors about failed directory creation
            assert len(setup.errors) > 0
            assert any("Failed to create directories" in error for error in setup.errors)
            assert setup.directories_created is False


class TestNotebookLogging:
    """Test logging setup in notebook environments."""
    
    def test_logging_setup_success(self, mock_jupyter_environment):
        """Test successful logging setup."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Create log directory
            log_dir = Path(temp_dir) / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            setup._setup_logging()
            
            assert setup.logging_configured is True
    
    def test_logging_setup_permission_error(self, mock_jupyter_environment):
        """Test logging setup with permission errors."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        with patch('logging.FileHandler', side_effect=PermissionError("Permission denied")):
            setup._setup_logging()
            
            # Should have warnings about logging setup
            assert len(setup.warnings) > 0
            assert any("Could not create log file" in warning for warning in setup.warnings)


class TestNotebookConfigValidation:
    """Test configuration validation in notebook environments."""
    
    def test_config_initialization_success(self, mock_jupyter_environment):
        """Test successful configuration initialization."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
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
            
            # Create directories
            Path(temp_dir, "data").mkdir()
            Path(temp_dir, "cache").mkdir()
            
            with patch('lol_team_optimizer.config.Config', return_value=mock_config):
                config = setup._initialize_config()
                
                assert config is not None
                assert config == mock_config
    
    def test_config_initialization_import_error(self, mock_jupyter_environment):
        """Test configuration initialization with import error."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        with patch('lol_team_optimizer.config.Config', side_effect=ImportError("Module not found")):
            config = setup._initialize_config()
            
            assert config is None
            assert len(setup.errors) > 0
            assert any("Could not import configuration module" in error for error in setup.errors)
    
    def test_config_validation_missing_directories(self, mock_jupyter_environment):
        """Test configuration validation with missing directories."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        # Mock config with non-existent directories
        mock_config = Mock()
        mock_config.data_directory = "/non/existent/data"
        mock_config.cache_directory = "/non/existent/cache"
        mock_config.individual_weight = 0.4
        mock_config.preference_weight = 0.3
        mock_config.synergy_weight = 0.3
        
        setup._validate_config(mock_config)
        
        # Should have warnings about missing directories
        assert len(setup.warnings) >= 2
        assert any("Data directory does not exist" in warning for warning in setup.warnings)
        assert any("Cache directory does not exist" in warning for warning in setup.warnings)


class TestNotebookIntegration:
    """Test complete notebook integration scenarios."""
    
    def test_complete_colab_setup_success(self, mock_colab_environment):
        """Test complete successful Colab setup."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock all setup steps to succeed
            with patch.object(setup, '_install_colab_dependencies'), \
                 patch.object(setup, '_setup_directories') as mock_dirs, \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True) as mock_api, \
                 patch.object(setup, '_initialize_config', return_value=Mock()) as mock_config:
                
                mock_dirs.return_value = None
                setup.directories_created = True
                
                result = setup.setup_environment()
                
                assert result.success is True
                assert result.environment == "colab"
                assert result.api_available is True
                assert result.dependencies_installed is True
                assert result.directories_created is True
                assert result.api_key_configured is True
    
    def test_complete_jupyter_setup_with_warnings(self, mock_jupyter_environment):
        """Test complete Jupyter setup with warnings."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock setup steps with some warnings
            with patch.object(setup, '_check_dependencies') as mock_deps, \
                 patch.object(setup, '_setup_directories') as mock_dirs, \
                 patch.object(setup, '_setup_api_key_interactive', return_value=False) as mock_api, \
                 patch.object(setup, '_initialize_config', return_value=Mock()) as mock_config:
                
                # Add some warnings
                setup.warnings.append("Some packages are outdated")
                mock_dirs.return_value = None
                setup.directories_created = True
                
                result = setup.setup_environment()
                
                assert result.success is True  # Should still succeed with warnings
                assert result.environment == "jupyter"
                assert result.api_available is False
                assert len(result.warnings) > 0
    
    def test_setup_failure_handling(self, mock_jupyter_environment):
        """Test setup failure handling."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        setup = UnifiedSetup()
        
        # Mock setup to fail
        with patch.object(setup, '_setup_jupyter', side_effect=Exception("Setup failed")):
            result = setup.setup_environment()
            
            assert result.success is False
            assert len(result.errors) > 0
            assert any("Setup failed with unexpected error" in error for error in result.errors)


class TestNotebookUsagePatterns:
    """Test common notebook usage patterns."""
    
    def test_notebook_quick_start_pattern(self, mock_jupyter_environment):
        """Test the typical notebook quick start pattern."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        # Simulate typical notebook usage
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock successful setup
            with patch.object(setup, '_check_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=True), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                setup.directories_created = True
                setup.api_key_configured = True
                setup.logging_configured = True
                
                result = setup.setup_environment()
                
                # Verify setup result is suitable for notebook usage
                assert result.success is True
                assert result.api_available is True
                assert result.config is not None
                assert result.setup_time > 0
    
    def test_notebook_offline_mode_pattern(self, mock_jupyter_environment):
        """Test notebook usage in offline mode."""
        from lol_team_optimizer.unified_setup import UnifiedSetup
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup = UnifiedSetup()
            setup.project_root = Path(temp_dir)
            
            # Mock setup without API key
            with patch.object(setup, '_check_dependencies'), \
                 patch.object(setup, '_setup_directories'), \
                 patch.object(setup, '_setup_api_key_interactive', return_value=False), \
                 patch.object(setup, '_initialize_config', return_value=Mock()):
                
                setup.directories_created = True
                setup.logging_configured = True
                
                result = setup.setup_environment()
                
                # Should still work in offline mode
                assert result.success is True
                assert result.api_available is False
                assert result.config is not None
                assert len(result.warnings) == 0 or any("offline" in warning.lower() for warning in result.warnings)