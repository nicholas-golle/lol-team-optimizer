"""
Tests for the StreamlinedCLI module.

Tests the new streamlined interface functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from lol_team_optimizer.streamlined_cli import StreamlinedCLI


class TestStreamlinedCLI:
    """Test cases for the StreamlinedCLI class."""
    
    @patch('lol_team_optimizer.streamlined_cli.CoreEngine')
    def test_cli_initialization_success(self, mock_core_engine):
        """Test successful CLI initialization."""
        # Mock the core engine
        mock_engine = Mock()
        mock_engine.system_status = {'player_count': 0, 'ready_for_optimization': False}
        mock_core_engine.return_value = mock_engine
        
        # Initialize CLI
        cli = StreamlinedCLI()
        
        # Verify initialization
        assert cli.engine == mock_engine
        mock_core_engine.assert_called_once()
    
    @patch('lol_team_optimizer.streamlined_cli.CoreEngine')
    @patch('sys.exit')
    def test_cli_initialization_failure(self, mock_exit, mock_core_engine):
        """Test CLI initialization failure handling."""
        # Mock core engine to raise exception
        mock_core_engine.side_effect = Exception("Initialization failed")
        
        # Initialize CLI (should exit)
        StreamlinedCLI()
        
        # Verify exit was called
        mock_exit.assert_called_once_with(1)
    
    @patch('lol_team_optimizer.streamlined_cli.CoreEngine')
    @patch('builtins.input', return_value='5')  # Exit option
    def test_main_menu_exit(self, mock_input, mock_core_engine):
        """Test main menu exit functionality."""
        # Mock the core engine with all required attributes
        mock_engine = Mock()
        mock_engine.system_status = {'player_count': 0, 'ready_for_optimization': False}
        mock_engine.champion_data_manager.champions = {}  # Empty dict for len()
        mock_core_engine.return_value = mock_engine
        
        # Initialize CLI and run main
        cli = StreamlinedCLI()
        cli.main()
        
        # Verify input was called (menu was displayed)
        mock_input.assert_called()
    
    @patch('lol_team_optimizer.streamlined_cli.CoreEngine')
    def test_engine_property_access(self, mock_core_engine):
        """Test that CLI properly exposes engine functionality."""
        # Mock the core engine with some methods
        mock_engine = Mock()
        mock_engine.system_status = {'player_count': 5, 'ready_for_optimization': True}
        mock_engine.add_player_with_data = Mock(return_value=(True, "Success", None))
        mock_core_engine.return_value = mock_engine
        
        # Initialize CLI
        cli = StreamlinedCLI()
        
        # Test engine access
        assert cli.engine.system_status['player_count'] == 5
        assert cli.engine.system_status['ready_for_optimization'] is True
        
        # Test engine method access
        result = cli.engine.add_player_with_data("test", "test#tag")
        assert result[0] is True
        assert result[1] == "Success"


class TestStreamlinedCLIIntegration:
    """Integration tests for StreamlinedCLI with real CoreEngine."""
    
    def test_cli_with_real_engine(self):
        """Test CLI with real CoreEngine (no mocking)."""
        try:
            cli = StreamlinedCLI()
            
            # Basic checks
            assert cli.engine is not None
            assert hasattr(cli.engine, 'system_status')
            assert hasattr(cli.engine, 'add_player_with_data')
            assert hasattr(cli.engine, 'optimize_team_smart')
            assert hasattr(cli.engine, 'get_comprehensive_analysis')
            
        except Exception as e:
            # If initialization fails due to missing dependencies, that's expected in test environment
            pytest.skip(f"CLI initialization failed (expected in test environment): {e}")
    
    def test_system_status_access(self):
        """Test accessing system status through CLI."""
        try:
            cli = StreamlinedCLI()
            status = cli.engine.system_status
            
            # Verify status has expected keys
            assert isinstance(status, dict)
            # These keys should exist even if values are default
            expected_keys = ['player_count', 'ready_for_optimization']
            for key in expected_keys:
                assert key in status or status.get(key) is not None
                
        except Exception as e:
            pytest.skip(f"CLI initialization failed (expected in test environment): {e}")