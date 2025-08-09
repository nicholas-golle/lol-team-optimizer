"""
Tests for Match Extraction Interface

This module contains comprehensive tests for the interactive match extraction
interface, including progress tracking, configuration validation, and
extraction workflows.
"""

import pytest
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from lol_team_optimizer.match_extraction_interface import (
    MatchExtractionInterface,
    ExtractionConfig,
    ExtractionProgress,
    ExtractionHistory,
    ExtractionScheduler
)
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player
from lol_team_optimizer.config import Config


class TestExtractionConfig:
    """Test extraction configuration functionality."""
    
    def test_extraction_config_creation(self):
        """Test creating extraction configuration."""
        config = ExtractionConfig(
            player_selection="TestPlayer (test#NA1)",
            queue_types=["420", "440"],
            max_matches_per_player=500,
            date_range_days=180
        )
        
        assert config.player_selection == "TestPlayer (test#NA1)"
        assert config.queue_types == ["420", "440"]
        assert config.max_matches_per_player == 500
        assert config.date_range_days == 180
        assert config.batch_size == 20  # default
        assert config.rate_limit_delay == 1.0  # default
        assert config.enable_validation is True  # default
    
    def test_extraction_config_defaults(self):
        """Test extraction configuration with defaults."""
        config = ExtractionConfig(player_selection="TestPlayer")
        
        assert config.player_selection == "TestPlayer"
        assert config.queue_types == ["420", "440"]  # default
        assert config.max_matches_per_player == 300  # default
        assert config.date_range_days == 365  # default
        assert config.batch_size == 20  # default
        assert config.rate_limit_delay == 1.0  # default
        assert config.enable_validation is True  # default
        assert config.auto_retry is True  # default
        assert config.max_retries == 3  # default


class TestExtractionProgress:
    """Test extraction progress tracking functionality."""
    
    def test_extraction_progress_creation(self):
        """Test creating extraction progress tracker."""
        progress = ExtractionProgress(
            operation_id="test-op-123",
            player_name="TestPlayer"
        )
        
        assert progress.operation_id == "test-op-123"
        assert progress.player_name == "TestPlayer"
        assert progress.status == "not_started"
        assert progress.progress_percentage == 0.0
        assert progress.current_step == ""
        assert progress.matches_extracted == 0
        assert progress.total_matches_available is None
        assert progress.start_time is None
        assert progress.end_time is None
        assert progress.error_message is None
        assert progress.detailed_log == []
        assert progress.can_pause is True
        assert progress.can_resume is False
        assert progress.can_cancel is True
    
    def test_extraction_progress_updates(self):
        """Test updating extraction progress."""
        progress = ExtractionProgress(
            operation_id="test-op-123",
            player_name="TestPlayer"
        )
        
        # Update progress
        progress.status = "running"
        progress.progress_percentage = 25.0
        progress.current_step = "Fetching match IDs"
        progress.matches_extracted = 50
        progress.total_matches_available = 200
        progress.start_time = datetime.now()
        
        assert progress.status == "running"
        assert progress.progress_percentage == 25.0
        assert progress.current_step == "Fetching match IDs"
        assert progress.matches_extracted == 50
        assert progress.total_matches_available == 200
        assert progress.start_time is not None
    
    def test_extraction_progress_logging(self):
        """Test extraction progress logging."""
        progress = ExtractionProgress(
            operation_id="test-op-123",
            player_name="TestPlayer"
        )
        
        # Add log entries
        progress.detailed_log.append("Starting extraction")
        progress.detailed_log.append("Fetching player data")
        progress.detailed_log.append("Processing matches")
        
        assert len(progress.detailed_log) == 3
        assert "Starting extraction" in progress.detailed_log
        assert "Fetching player data" in progress.detailed_log
        assert "Processing matches" in progress.detailed_log


class TestExtractionScheduler:
    """Test extraction scheduling functionality."""
    
    def test_scheduler_creation(self):
        """Test creating extraction scheduler."""
        scheduler = ExtractionScheduler()
        
        assert scheduler.scheduled_operations == {}
        assert scheduler.recurring_schedules == {}
    
    def test_schedule_extraction(self):
        """Test scheduling a one-time extraction."""
        scheduler = ExtractionScheduler()
        config = ExtractionConfig(player_selection="TestPlayer")
        schedule_time = datetime.now() + timedelta(hours=1)
        
        schedule_id = scheduler.schedule_extraction(config, schedule_time)
        
        assert schedule_id in scheduler.scheduled_operations
        operation = scheduler.scheduled_operations[schedule_id]
        assert operation['config'] == config
        assert operation['schedule_time'] == schedule_time
        assert operation['status'] == 'scheduled'
        assert operation['created_at'] is not None
    
    def test_create_recurring_schedule(self):
        """Test creating a recurring extraction schedule."""
        scheduler = ExtractionScheduler()
        config = ExtractionConfig(player_selection="TestPlayer")
        interval_hours = 24
        
        schedule_id = scheduler.create_recurring_schedule(config, interval_hours)
        
        assert schedule_id in scheduler.recurring_schedules
        schedule = scheduler.recurring_schedules[schedule_id]
        assert schedule['config'] == config
        assert schedule['interval_hours'] == interval_hours
        assert schedule['last_run'] is None
        assert schedule['next_run'] is not None
        assert schedule['status'] == 'active'
        assert schedule['created_at'] is not None
    
    def test_get_pending_operations(self):
        """Test getting pending operations."""
        scheduler = ExtractionScheduler()
        config = ExtractionConfig(player_selection="TestPlayer")
        
        # Schedule operation in the past (should be pending)
        past_time = datetime.now() - timedelta(minutes=1)
        schedule_id = scheduler.schedule_extraction(config, past_time)
        
        pending = scheduler.get_pending_operations()
        
        assert len(pending) == 1
        assert pending[0]['type'] == 'scheduled'
        assert pending[0]['id'] == schedule_id
        assert pending[0]['config'] == config
    
    def test_get_pending_recurring_operations(self):
        """Test getting pending recurring operations."""
        scheduler = ExtractionScheduler()
        config = ExtractionConfig(player_selection="TestPlayer")
        
        # Create recurring schedule with next run in the past
        schedule_id = scheduler.create_recurring_schedule(config, 24)
        scheduler.recurring_schedules[schedule_id]['next_run'] = datetime.now() - timedelta(minutes=1)
        
        pending = scheduler.get_pending_operations()
        
        assert len(pending) == 1
        assert pending[0]['type'] == 'recurring'
        assert pending[0]['id'] == schedule_id
        assert pending[0]['config'] == config


class TestMatchExtractionInterface:
    """Test match extraction interface functionality."""
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create a mock core engine for testing."""
        mock_engine = Mock(spec=CoreEngine)
        mock_engine.config = Mock()
        mock_engine.config.data_directory = tempfile.mkdtemp()
        
        # Mock data manager
        mock_engine.data_manager = Mock()
        mock_engine.data_manager.load_player_data.return_value = [
            Player(name="TestPlayer1", summoner_name="test1#NA1", puuid="test-puuid-1"),
            Player(name="TestPlayer2", summoner_name="test2#NA1", puuid="test-puuid-2")
        ]
        
        # Mock historical match scraping
        mock_engine.historical_match_scraping.return_value = {
            'players_processed': 1,
            'total_new_matches': 50,
            'player_results': {
                'TestPlayer1': {
                    'status': 'completed',
                    'new_matches_stored': 50,
                    'total_matches_extracted': 150
                }
            }
        }
        
        return mock_engine
    
    @pytest.fixture
    def extraction_interface(self, mock_core_engine):
        """Create extraction interface for testing."""
        return MatchExtractionInterface(mock_core_engine)
    
    def test_interface_creation(self, extraction_interface):
        """Test creating match extraction interface."""
        assert extraction_interface.core_engine is not None
        assert extraction_interface.active_operations == {}
        assert extraction_interface.extraction_history == []
        assert extraction_interface.scheduler is not None
        assert extraction_interface.operation_threads == {}
        assert extraction_interface.stop_events == {}
        assert extraction_interface.pause_events == {}
    
    def test_create_extraction_interface_components(self, extraction_interface):
        """Test creating extraction interface components."""
        import gradio as gr
        
        # Create components within a Gradio context
        with gr.Blocks() as demo:
            components = extraction_interface.create_extraction_interface()
            
            # Check that all required components are created
            required_components = [
                'player_selection', 'queue_types', 'max_matches', 'date_range_days',
                'batch_size', 'rate_limit_delay', 'enable_validation', 'auto_retry',
                'max_retries', 'config_validation', 'progress_bar', 'progress_percentage',
                'current_status', 'matches_extracted', 'total_available', 'extraction_rate',
                'estimated_completion', 'progress_timeline', 'start_extraction',
                'pause_extraction', 'resume_extraction', 'cancel_extraction',
                'validate_config', 'save_config', 'load_config', 'history_table',
                'refresh_history', 'clear_history', 'export_history', 'log_display',
                'auto_scroll_logs', 'clear_logs', 'export_logs'
            ]
            
            for component_name in required_components:
                assert component_name in components, f"Missing component: {component_name}"
    
    def test_config_validation_valid(self, extraction_interface):
        """Test configuration validation with valid config."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=["420", "440"],
            max_matches_per_player=300,
            date_range_days=365,
            batch_size=20,
            rate_limit_delay=1.0
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is True
        assert result['message'] == 'Configuration is valid'
    
    def test_config_validation_invalid_player(self, extraction_interface):
        """Test configuration validation with invalid player."""
        config = ExtractionConfig(
            player_selection="",  # Empty player selection
            queue_types=["420", "440"],
            max_matches_per_player=300
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'Player selection is required' in result['message']
    
    def test_config_validation_invalid_queue_types(self, extraction_interface):
        """Test configuration validation with invalid queue types."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=[],  # Empty queue types
            max_matches_per_player=300
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'At least one queue type must be selected' in result['message']
    
    def test_config_validation_invalid_max_matches(self, extraction_interface):
        """Test configuration validation with invalid max matches."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=["420"],
            max_matches_per_player=0  # Invalid max matches
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'Max matches must be at least 1' in result['message']
    
    def test_config_validation_invalid_batch_size(self, extraction_interface):
        """Test configuration validation with invalid batch size."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=["420"],
            max_matches_per_player=300,
            batch_size=150  # Too large batch size
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'Batch size must be between 1 and 100' in result['message']
    
    def test_config_validation_invalid_rate_limit(self, extraction_interface):
        """Test configuration validation with invalid rate limit."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=["420"],
            max_matches_per_player=300,
            rate_limit_delay=0.05  # Too small rate limit delay
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'Rate limit delay must be at least 0.1 seconds' in result['message']
    
    def test_config_validation_nonexistent_player(self, extraction_interface):
        """Test configuration validation with nonexistent player."""
        config = ExtractionConfig(
            player_selection="NonexistentPlayer (nonexistent#NA1)",
            queue_types=["420"],
            max_matches_per_player=300
        )
        
        result = extraction_interface._validate_extraction_config(config)
        
        assert result['valid'] is False
        assert 'Selected player not found' in result['message']
    
    def test_get_config_from_inputs(self, extraction_interface):
        """Test extracting configuration from input components."""
        inputs = [
            "TestPlayer1 (test1#NA1)",  # player_selection
            ["420", "440"],             # queue_types
            500,                        # max_matches_per_player
            180,                        # date_range_days
            25,                         # batch_size
            1.5,                        # rate_limit_delay
            True,                       # enable_validation
            False,                      # auto_retry
            5                           # max_retries
        ]
        
        config = extraction_interface._get_config_from_inputs(*inputs)
        
        assert config.player_selection == "TestPlayer1 (test1#NA1)"
        assert config.queue_types == ["420", "440"]
        assert config.max_matches_per_player == 500
        assert config.date_range_days == 180
        assert config.batch_size == 25
        assert config.rate_limit_delay == 1.5
        assert config.enable_validation is True
        assert config.auto_retry is False
        assert config.max_retries == 5
    
    def test_get_config_from_inputs_with_defaults(self, extraction_interface):
        """Test extracting configuration with default values."""
        inputs = [
            "",      # empty player_selection
            None,    # None queue_types
            None,    # None max_matches_per_player
            None,    # None date_range_days
            None,    # None batch_size
            None,    # None rate_limit_delay
            None,    # None enable_validation
            None,    # None auto_retry
            None     # None max_retries
        ]
        
        config = extraction_interface._get_config_from_inputs(*inputs)
        
        assert config.player_selection == ""
        assert config.queue_types == ["420", "440"]  # default
        assert config.max_matches_per_player == 300  # default
        assert config.date_range_days == 365  # default
        assert config.batch_size == 20  # default
        assert config.rate_limit_delay == 1.0  # default
        assert config.enable_validation is True  # default
        assert config.auto_retry is True  # default
        assert config.max_retries == 3  # default
    
    def test_start_extraction_operation(self, extraction_interface):
        """Test starting an extraction operation."""
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            queue_types=["420"],
            max_matches_per_player=100
        )
        
        operation_id = extraction_interface._start_extraction_operation(config)
        
        assert operation_id in extraction_interface.active_operations
        assert operation_id in extraction_interface.stop_events
        assert operation_id in extraction_interface.pause_events
        assert operation_id in extraction_interface.operation_threads
        
        progress = extraction_interface.active_operations[operation_id]
        assert progress.operation_id == operation_id
        assert progress.player_name == "TestPlayer1"
        # Status might be "running" or "completed" depending on timing
        assert progress.status in ["running", "completed"]
        assert progress.start_time is not None
    
    def test_get_active_operations(self, extraction_interface):
        """Test getting active operations."""
        # Initially no active operations
        active_ops = extraction_interface.get_active_operations()
        assert len(active_ops) == 0
        
        # Add a mock operation
        progress = ExtractionProgress(
            operation_id="test-op-123",
            player_name="TestPlayer1",
            status="running"
        )
        extraction_interface.active_operations["test-op-123"] = progress
        
        active_ops = extraction_interface.get_active_operations()
        assert len(active_ops) == 1
        assert active_ops[0].operation_id == "test-op-123"
        assert active_ops[0].player_name == "TestPlayer1"
        assert active_ops[0].status == "running"
    
    def test_get_extraction_history(self, extraction_interface):
        """Test getting extraction history."""
        # Initially no history
        history = extraction_interface.get_extraction_history()
        assert len(history) == 0
        
        # Add a mock history entry
        config = ExtractionConfig(player_selection="TestPlayer1")
        progress = ExtractionProgress(operation_id="test-op-123", player_name="TestPlayer1")
        history_entry = ExtractionHistory(
            operation_id="test-op-123",
            player_name="TestPlayer1",
            config=config,
            progress=progress,
            timestamp=datetime.now(),
            success=True
        )
        extraction_interface.extraction_history.append(history_entry)
        
        history = extraction_interface.get_extraction_history()
        assert len(history) == 1
        assert history[0].operation_id == "test-op-123"
        assert history[0].player_name == "TestPlayer1"
        assert history[0].success is True
    
    def test_cleanup_completed_operations(self, extraction_interface):
        """Test cleaning up completed operations."""
        # Add mock operations with different statuses
        operations = {
            "running-op": ExtractionProgress(operation_id="running-op", player_name="Player1", status="running"),
            "completed-op": ExtractionProgress(operation_id="completed-op", player_name="Player2", status="completed"),
            "failed-op": ExtractionProgress(operation_id="failed-op", player_name="Player3", status="failed"),
            "cancelled-op": ExtractionProgress(operation_id="cancelled-op", player_name="Player4", status="cancelled")
        }
        
        extraction_interface.active_operations.update(operations)
        
        # Cleanup completed operations
        extraction_interface.cleanup_completed_operations()
        
        # Only running operation should remain
        assert len(extraction_interface.active_operations) == 1
        assert "running-op" in extraction_interface.active_operations
        assert "completed-op" not in extraction_interface.active_operations
        assert "failed-op" not in extraction_interface.active_operations
        assert "cancelled-op" not in extraction_interface.active_operations
    
    def test_save_and_load_extraction_history(self, extraction_interface):
        """Test saving and loading extraction history."""
        # Create test history entry
        config = ExtractionConfig(player_selection="TestPlayer1")
        progress = ExtractionProgress(operation_id="test-op-123", player_name="TestPlayer1")
        history_entry = ExtractionHistory(
            operation_id="test-op-123",
            player_name="TestPlayer1",
            config=config,
            progress=progress,
            timestamp=datetime.now(),
            duration_seconds=120.5,
            success=True
        )
        
        extraction_interface.extraction_history.append(history_entry)
        
        # Save history
        extraction_interface._save_extraction_history()
        
        # Create new interface and load history
        new_interface = MatchExtractionInterface(extraction_interface.core_engine)
        
        # Check that history was loaded
        assert len(new_interface.extraction_history) == 1
        loaded_entry = new_interface.extraction_history[0]
        assert loaded_entry.operation_id == "test-op-123"
        assert loaded_entry.player_name == "TestPlayer1"
        assert loaded_entry.duration_seconds == 120.5
        assert loaded_entry.success is True


class TestExtractionWorkflows:
    """Test complete extraction workflows."""
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create a mock core engine for workflow testing."""
        mock_engine = Mock(spec=CoreEngine)
        mock_engine.config = Mock()
        mock_engine.config.data_directory = tempfile.mkdtemp()
        
        # Mock data manager
        mock_engine.data_manager = Mock()
        mock_engine.data_manager.load_player_data.return_value = [
            Player(name="TestPlayer1", summoner_name="test1#NA1", puuid="test-puuid-1")
        ]
        
        return mock_engine
    
    def test_successful_extraction_workflow(self, mock_core_engine):
        """Test a successful extraction workflow."""
        # Mock successful extraction result
        mock_core_engine.historical_match_scraping.return_value = {
            'players_processed': 1,
            'total_new_matches': 75,
            'player_results': {
                'TestPlayer1': {
                    'status': 'completed',
                    'new_matches_stored': 75,
                    'total_matches_extracted': 200
                }
            },
            'start_time': datetime.now().isoformat(),
            'end_time': datetime.now().isoformat()
        }
        
        interface = MatchExtractionInterface(mock_core_engine)
        
        # Start extraction
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            max_matches_per_player=100
        )
        
        operation_id = interface._start_extraction_operation(config)
        
        # Wait for operation to complete
        thread = interface.operation_threads[operation_id]
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        # Check results
        progress = interface.active_operations[operation_id]
        assert progress.status == "completed"
        assert progress.matches_extracted == 75
        assert progress.end_time is not None
        
        # Check history
        assert len(interface.extraction_history) == 1
        history_entry = interface.extraction_history[0]
        assert history_entry.success is True
        assert history_entry.operation_id == operation_id
    
    def test_failed_extraction_workflow(self, mock_core_engine):
        """Test a failed extraction workflow."""
        # Mock failed extraction result
        mock_core_engine.historical_match_scraping.return_value = {
            'error': 'API rate limit exceeded'
        }
        
        interface = MatchExtractionInterface(mock_core_engine)
        
        # Start extraction
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            max_matches_per_player=100
        )
        
        operation_id = interface._start_extraction_operation(config)
        
        # Wait for operation to complete
        thread = interface.operation_threads[operation_id]
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        # Check results
        progress = interface.active_operations[operation_id]
        assert progress.status == "failed"
        assert progress.error_message == 'API rate limit exceeded'
        assert progress.end_time is not None
        
        # Check history
        assert len(interface.extraction_history) == 1
        history_entry = interface.extraction_history[0]
        assert history_entry.success is False
        assert history_entry.operation_id == operation_id
    
    def test_extraction_with_exception(self, mock_core_engine):
        """Test extraction workflow with exception."""
        # Mock exception during extraction
        mock_core_engine.historical_match_scraping.side_effect = Exception("Network error")
        
        interface = MatchExtractionInterface(mock_core_engine)
        
        # Start extraction
        config = ExtractionConfig(
            player_selection="TestPlayer1 (test1#NA1)",
            max_matches_per_player=100
        )
        
        operation_id = interface._start_extraction_operation(config)
        
        # Wait for operation to complete
        if operation_id in interface.operation_threads:
            thread = interface.operation_threads[operation_id]
            thread.join(timeout=5)  # Wait up to 5 seconds
        
        # Check results
        progress = interface.active_operations[operation_id]
        assert progress.status == "failed"
        assert "Network error" in progress.error_message
        assert progress.end_time is not None
        
        # Check that operation was cleaned up (threads are cleaned up after completion)
        assert operation_id not in interface.stop_events
        assert operation_id not in interface.pause_events
        assert operation_id not in interface.operation_threads


if __name__ == "__main__":
    pytest.main([__file__])