"""
Tests for Advanced Extraction Monitoring and Error Handling

This module contains comprehensive tests for the advanced extraction monitoring
system, including rate limit monitoring, retry logic, data quality validation,
performance metrics collection, and error handling scenarios.
"""

import pytest
import time
import threading
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import requests

from lol_team_optimizer.advanced_extraction_monitor import (
    AdvancedExtractionMonitor,
    APIRateLimitMonitor,
    ExtractionRetryManager,
    DataQualityValidator,
    PerformanceMetricsCollector,
    ExtractionStatus,
    ErrorSeverity,
    ExtractionError,
    PlayerProgress,
    DataQualityCheck,
    ExtractionMetrics
)
from lol_team_optimizer.config import Config
from lol_team_optimizer.riot_client import RiotAPIClient
from lol_team_optimizer.models import Player


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.riot_api_rate_limit = 120
    config.max_retries = 3
    config.retry_backoff_factor = 2.0
    config.request_timeout_seconds = 30
    config.cache_duration_hours = 24
    config.data_directory = tempfile.mkdtemp()
    config.cache_directory = tempfile.mkdtemp()
    config.riot_api_base_url = "https://na1.api.riotgames.com"
    config.riot_api_key = "test_api_key"
    return config


@pytest.fixture
def mock_riot_client(mock_config):
    """Create a mock Riot API client for testing."""
    return Mock(spec=RiotAPIClient)


@pytest.fixture
def sample_players():
    """Create sample players for testing."""
    return [
        Player(name="TestPlayer1", summoner_name="TestSummoner1"),
        Player(name="TestPlayer2", summoner_name="TestSummoner2"),
        Player(name="TestPlayer3", summoner_name="TestSummoner3")
    ]


class TestAPIRateLimitMonitor:
    """Test cases for API rate limit monitoring."""
    
    def test_initialization(self, mock_config):
        """Test rate limit monitor initialization."""
        monitor = APIRateLimitMonitor(mock_config)
        
        assert monitor.config == mock_config
        assert monitor.rate_limits == {}
        assert monitor.global_throttle is False
        assert monitor.global_throttle_until is None
        assert len(monitor.request_history) == 0
    
    def test_can_make_request_new_endpoint(self, mock_config):
        """Test request permission for new endpoint."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Should allow request for new endpoint
        assert monitor.can_make_request("test_endpoint") is True
        
        # Should create rate limit tracker
        assert "test_endpoint" in monitor.rate_limits
        assert monitor.rate_limits["test_endpoint"].requests_made == 0
    
    def test_record_request(self, mock_config):
        """Test recording API requests."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Record successful request
        monitor.record_request("test_endpoint", success=True)
        
        assert monitor.rate_limits["test_endpoint"].requests_made == 1
        assert len(monitor.request_history) == 1
        assert monitor.request_history[0]["success"] is True
    
    def test_rate_limit_enforcement(self, mock_config):
        """Test rate limit enforcement."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Make requests up to limit
        for i in range(120):
            monitor.record_request("test_endpoint")
        
        # Should not allow more requests
        assert monitor.can_make_request("test_endpoint") is False
        
        # Should calculate wait time
        wait_time = monitor.get_wait_time("test_endpoint")
        assert wait_time > 0
    
    def test_rate_limit_window_reset(self, mock_config):
        """Test rate limit window reset."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Fill up rate limit
        for i in range(120):
            monitor.record_request("test_endpoint")
        
        # Manually reset window start time to simulate time passage
        monitor.rate_limits["test_endpoint"].window_start = datetime.now() - timedelta(seconds=130)
        
        # Should allow requests again
        assert monitor.can_make_request("test_endpoint") is True
    
    def test_handle_rate_limit_response(self, mock_config):
        """Test handling rate limit response from API."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Create mock response with rate limit
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        
        monitor.handle_rate_limit_response("test_endpoint", mock_response)
        
        # Should throttle endpoint
        assert monitor.rate_limits["test_endpoint"].throttled is True
        assert monitor.rate_limits["test_endpoint"].throttle_until is not None
        assert not monitor.can_make_request("test_endpoint")
    
    def test_get_current_metrics(self, mock_config):
        """Test getting current rate limit metrics."""
        monitor = APIRateLimitMonitor(mock_config)
        
        # Make some requests
        for i in range(10):
            monitor.record_request("test_endpoint")
        
        metrics = monitor.get_current_metrics()
        
        assert "global_throttled" in metrics
        assert "endpoints" in metrics
        assert "recent_requests" in metrics
        assert "test_endpoint" in metrics["endpoints"]
        assert metrics["endpoints"]["test_endpoint"]["requests_made"] == 10


class TestExtractionRetryManager:
    """Test cases for extraction retry management."""
    
    def test_initialization(self, mock_config):
        """Test retry manager initialization."""
        manager = ExtractionRetryManager(mock_config)
        
        assert manager.config == mock_config
        assert manager.retry_attempts == {}
        assert manager.backoff_delays == {}
        assert manager.max_retries == mock_config.max_retries
    
    def test_should_retry_normal_error(self, mock_config):
        """Test retry decision for normal errors."""
        manager = ExtractionRetryManager(mock_config)
        
        error = ExtractionError(
            error_id="test_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="network_error",
            error_message="Connection timeout",
            severity=ErrorSeverity.MEDIUM,
            retry_count=1,
            max_retries=3
        )
        
        assert manager.should_retry(error) is True
    
    def test_should_not_retry_critical_error(self, mock_config):
        """Test retry decision for critical errors."""
        manager = ExtractionRetryManager(mock_config)
        
        error = ExtractionError(
            error_id="test_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="critical_error",
            error_message="Critical system failure",
            severity=ErrorSeverity.CRITICAL,
            retry_count=1,
            max_retries=3
        )
        
        assert manager.should_retry(error) is False
    
    def test_should_not_retry_max_attempts(self, mock_config):
        """Test retry decision when max attempts reached."""
        manager = ExtractionRetryManager(mock_config)
        
        error = ExtractionError(
            error_id="test_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="network_error",
            error_message="Connection timeout",
            severity=ErrorSeverity.MEDIUM,
            retry_count=3,
            max_retries=3
        )
        
        assert manager.should_retry(error) is False
    
    def test_should_not_retry_non_retryable_error(self, mock_config):
        """Test retry decision for non-retryable errors."""
        manager = ExtractionRetryManager(mock_config)
        
        error = ExtractionError(
            error_id="test_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="invalid_api_key",
            error_message="Invalid API key",
            severity=ErrorSeverity.HIGH,
            retry_count=1,
            max_retries=3
        )
        
        assert manager.should_retry(error) is False
    
    def test_get_retry_delay_exponential_backoff(self, mock_config):
        """Test exponential backoff delay calculation."""
        manager = ExtractionRetryManager(mock_config)
        
        # First attempt
        delay1 = manager.get_retry_delay("test_error", 0)
        assert delay1 >= 0.8  # With jitter, should be around base_delay
        assert delay1 <= 1.2
        
        # Second attempt
        delay2 = manager.get_retry_delay("test_error", 1)
        assert delay2 > delay1  # Should be larger
        
        # Third attempt
        delay3 = manager.get_retry_delay("test_error", 2)
        assert delay3 > delay2  # Should be even larger
    
    def test_record_retry_attempt(self, mock_config):
        """Test recording retry attempts."""
        manager = ExtractionRetryManager(mock_config)
        
        manager.record_retry_attempt("test_error")
        assert manager.retry_attempts["test_error"] == 1
        
        manager.record_retry_attempt("test_error")
        assert manager.retry_attempts["test_error"] == 2
    
    def test_reset_retry_state(self, mock_config):
        """Test resetting retry state."""
        manager = ExtractionRetryManager(mock_config)
        
        # Set up retry state
        manager.record_retry_attempt("test_error")
        manager.get_retry_delay("test_error", 1)
        
        assert "test_error" in manager.retry_attempts
        assert "test_error" in manager.backoff_delays
        
        # Reset state
        manager.reset_retry_state("test_error")
        
        assert "test_error" not in manager.retry_attempts
        assert "test_error" not in manager.backoff_delays


class TestDataQualityValidator:
    """Test cases for data quality validation."""
    
    def test_initialization(self, mock_config):
        """Test data quality validator initialization."""
        validator = DataQualityValidator(mock_config)
        
        assert validator.config == mock_config
        assert "match_data" in validator.validation_rules
        assert "participant_data" in validator.validation_rules
    
    def test_validate_match_data_valid(self, mock_config):
        """Test validation of valid match data."""
        validator = DataQualityValidator(mock_config)
        
        valid_match_data = {
            'gameId': 12345,
            'gameCreation': 1234567890,
            'gameDuration': 1800,  # 30 minutes
            'queueId': 420,
            'participants': [{'participantId': i} for i in range(10)],
            'teams': [{'teamId': 100}, {'teamId': 200}]
        }
        
        checks = validator.validate_match_data(valid_match_data)
        
        # Should have checks for required fields, duration, and participant count
        assert len(checks) >= 3
        
        # All checks should pass
        passed_checks = [check for check in checks if check.passed]
        assert len(passed_checks) == len(checks)
    
    def test_validate_match_data_missing_fields(self, mock_config):
        """Test validation of match data with missing fields."""
        validator = DataQualityValidator(mock_config)
        
        invalid_match_data = {
            'gameId': 12345,
            # Missing required fields
        }
        
        checks = validator.validate_match_data(invalid_match_data)
        
        # Should have failed check for missing fields
        failed_checks = [check for check in checks if not check.passed]
        assert len(failed_checks) > 0
        
        # Should identify missing fields
        missing_field_check = next((check for check in checks if check.check_name == "required_fields"), None)
        assert missing_field_check is not None
        assert not missing_field_check.passed
        assert missing_field_check.severity == ErrorSeverity.HIGH
    
    def test_validate_match_data_invalid_duration(self, mock_config):
        """Test validation of match data with invalid duration."""
        validator = DataQualityValidator(mock_config)
        
        invalid_match_data = {
            'gameId': 12345,
            'gameCreation': 1234567890,
            'gameDuration': 60,  # Too short
            'queueId': 420,
            'participants': [{'participantId': i} for i in range(10)],
            'teams': [{'teamId': 100}, {'teamId': 200}]
        }
        
        checks = validator.validate_match_data(invalid_match_data)
        
        # Should have failed check for game duration
        duration_check = next((check for check in checks if check.check_name == "game_duration"), None)
        assert duration_check is not None
        assert not duration_check.passed
        assert duration_check.severity == ErrorSeverity.MEDIUM
    
    def test_validate_participant_data_valid(self, mock_config):
        """Test validation of valid participant data."""
        validator = DataQualityValidator(mock_config)
        
        valid_participant_data = {
            'championId': 1,
            'spell1Id': 4,
            'spell2Id': 7,
            'teamId': 100,
            'stats': {'kills': 5, 'deaths': 2, 'assists': 8}
        }
        
        checks = validator.validate_participant_data(valid_participant_data)
        
        # All checks should pass
        passed_checks = [check for check in checks if check.passed]
        assert len(passed_checks) == len(checks)
    
    def test_validate_participant_data_invalid_team_id(self, mock_config):
        """Test validation of participant data with invalid team ID."""
        validator = DataQualityValidator(mock_config)
        
        invalid_participant_data = {
            'championId': 1,
            'spell1Id': 4,
            'spell2Id': 7,
            'teamId': 300,  # Invalid team ID
            'stats': {'kills': 5, 'deaths': 2, 'assists': 8}
        }
        
        checks = validator.validate_participant_data(invalid_participant_data)
        
        # Should have failed check for team ID
        team_id_check = next((check for check in checks if check.check_name == "team_id"), None)
        assert team_id_check is not None
        assert not team_id_check.passed
        assert team_id_check.severity == ErrorSeverity.MEDIUM
    
    def test_calculate_quality_score(self, mock_config):
        """Test quality score calculation."""
        validator = DataQualityValidator(mock_config)
        
        # All checks pass
        all_pass_checks = [
            DataQualityCheck("test1", True, "Pass", ErrorSeverity.LOW),
            DataQualityCheck("test2", True, "Pass", ErrorSeverity.MEDIUM),
            DataQualityCheck("test3", True, "Pass", ErrorSeverity.HIGH)
        ]
        
        score = validator.calculate_quality_score(all_pass_checks)
        assert score == 100.0
        
        # Some checks fail
        mixed_checks = [
            DataQualityCheck("test1", True, "Pass", ErrorSeverity.LOW),
            DataQualityCheck("test2", False, "Fail", ErrorSeverity.MEDIUM),
            DataQualityCheck("test3", True, "Pass", ErrorSeverity.HIGH)
        ]
        
        score = validator.calculate_quality_score(mixed_checks)
        assert 0 < score < 100
        
        # No checks
        score = validator.calculate_quality_score([])
        assert score == 0.0


class TestPerformanceMetricsCollector:
    """Test cases for performance metrics collection."""
    
    def test_initialization(self, mock_config):
        """Test performance metrics collector initialization."""
        collector = PerformanceMetricsCollector(mock_config)
        
        assert collector.config == mock_config
        assert collector.metrics_history == []
        assert collector.real_time_metrics == {}
    
    def test_start_operation_tracking(self, mock_config):
        """Test starting operation tracking."""
        collector = PerformanceMetricsCollector(mock_config)
        
        collector.start_operation_tracking("test_op", 5)
        
        assert "test_op" in collector.real_time_metrics
        metrics = collector.real_time_metrics["test_op"]
        assert metrics["total_players"] == 5
        assert metrics["completed_players"] == 0
        assert "start_time" in metrics
    
    def test_update_player_metrics(self, mock_config):
        """Test updating player metrics."""
        collector = PerformanceMetricsCollector(mock_config)
        collector.start_operation_tracking("test_op", 1)
        
        progress = PlayerProgress(
            player_name="test_player",
            status=ExtractionStatus.COMPLETED,
            matches_extracted=50,
            api_calls_made=25,
            error_count=2,
            extraction_rate=10.0
        )
        
        collector.update_player_metrics("test_op", progress)
        
        metrics = collector.real_time_metrics["test_op"]
        assert metrics["completed_players"] == 1
        assert metrics["total_matches_extracted"] == 50
        assert metrics["total_api_calls"] == 25
        assert metrics["total_errors"] == 2
        assert len(metrics["extraction_rates"]) == 1
    
    def test_calculate_efficiency_score(self, mock_config):
        """Test efficiency score calculation."""
        collector = PerformanceMetricsCollector(mock_config)
        collector.start_operation_tracking("test_op", 10)
        
        # Simulate good performance
        metrics = collector.real_time_metrics["test_op"]
        metrics["completed_players"] = 9  # 90% success rate
        metrics["total_api_calls"] = 100
        metrics["total_errors"] = 5  # 5% error rate
        metrics["extraction_rates"].extend([8.0, 9.0, 10.0])  # Good rates
        
        efficiency = collector.calculate_efficiency_score("test_op")
        assert 70 <= efficiency <= 100  # Should be high efficiency
    
    def test_finalize_operation_metrics(self, mock_config):
        """Test finalizing operation metrics."""
        collector = PerformanceMetricsCollector(mock_config)
        collector.start_operation_tracking("test_op", 2)
        
        # Add some data
        metrics = collector.real_time_metrics["test_op"]
        metrics["completed_players"] = 2
        metrics["total_matches_extracted"] = 100
        metrics["extraction_rates"].extend([5.0, 8.0, 10.0])
        
        # Wait a bit to have some duration
        time.sleep(0.1)
        
        final_metrics = collector.finalize_operation_metrics("test_op")
        
        assert isinstance(final_metrics, ExtractionMetrics)
        assert final_metrics.operation_id == "test_op"
        assert final_metrics.total_players == 2
        assert final_metrics.completed_players == 2
        assert final_metrics.total_matches_extracted == 100
        assert final_metrics.total_duration > 0
        assert final_metrics.average_extraction_rate > 0
        assert final_metrics.peak_extraction_rate == 10.0
        
        # Should be removed from real-time tracking
        assert "test_op" not in collector.real_time_metrics
        
        # Should be in history
        assert len(collector.metrics_history) == 1
        assert collector.metrics_history[0] == final_metrics
    
    def test_get_optimization_suggestions(self, mock_config):
        """Test optimization suggestions generation."""
        collector = PerformanceMetricsCollector(mock_config)
        
        # Create metrics with various issues
        poor_metrics = ExtractionMetrics(
            operation_id="test_op",
            total_players=10,
            completed_players=5,
            failed_players=3,
            total_matches_extracted=100,
            total_api_calls=200,
            total_errors=30,  # High error rate
            average_extraction_rate=2.0,  # Low rate
            peak_extraction_rate=5.0,
            efficiency_score=50.0,  # Low efficiency
            data_quality_score=60.0  # Low quality
        )
        
        suggestions = collector.get_optimization_suggestions(poor_metrics)
        
        assert len(suggestions) > 0
        assert any("error rate" in suggestion.lower() for suggestion in suggestions)
        assert any("extraction rate" in suggestion.lower() for suggestion in suggestions)
        assert any("quality" in suggestion.lower() for suggestion in suggestions)


class TestAdvancedExtractionMonitor:
    """Test cases for the main advanced extraction monitor."""
    
    def test_initialization(self, mock_config, mock_riot_client):
        """Test advanced extraction monitor initialization."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        assert monitor.config == mock_config
        assert monitor.riot_client == mock_riot_client
        assert isinstance(monitor.rate_monitor, APIRateLimitMonitor)
        assert isinstance(monitor.retry_manager, ExtractionRetryManager)
        assert isinstance(monitor.quality_validator, DataQualityValidator)
        assert isinstance(monitor.metrics_collector, PerformanceMetricsCollector)
        assert monitor.active_operations == {}
        assert monitor.operation_errors == {}
        assert monitor.monitoring_active is False
    
    def test_create_extraction_operation(self, mock_config, mock_riot_client, sample_players):
        """Test creating extraction operation."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        assert operation_id in monitor.active_operations
        assert operation_id in monitor.operation_errors
        assert operation_id in monitor.cancellation_events
        
        # Should have progress for each player
        assert len(monitor.active_operations[operation_id]) == len(sample_players)
        for player in sample_players:
            assert player.name in monitor.active_operations[operation_id]
            progress = monitor.active_operations[operation_id][player.name]
            assert progress.status == ExtractionStatus.NOT_STARTED
    
    def test_update_player_progress(self, mock_config, mock_riot_client, sample_players):
        """Test updating player progress."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        player_name = sample_players[0].name
        progress_update = {
            'status': ExtractionStatus.RUNNING,
            'matches_extracted': 25,
            'current_step': 'Extracting matches'
        }
        
        monitor.update_player_progress(operation_id, player_name, progress_update)
        
        progress = monitor.active_operations[operation_id][player_name]
        assert progress.status == ExtractionStatus.RUNNING
        assert progress.matches_extracted == 25
        assert progress.current_step == 'Extracting matches'
    
    def test_record_extraction_error(self, mock_config, mock_riot_client, sample_players):
        """Test recording extraction errors."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        player_name = sample_players[0].name
        error_id = monitor.record_extraction_error(
            operation_id, player_name, "network_error", 
            "Connection timeout", ErrorSeverity.MEDIUM
        )
        
        assert error_id is not None
        assert len(monitor.operation_errors[operation_id]) == 1
        
        error = monitor.operation_errors[operation_id][0]
        assert error.error_id == error_id
        assert error.player_name == player_name
        assert error.error_type == "network_error"
        assert error.severity == ErrorSeverity.MEDIUM
        
        # Should update player progress
        progress = monitor.active_operations[operation_id][player_name]
        assert progress.error_count == 1
        assert progress.last_error == error
    
    def test_cancel_operation(self, mock_config, mock_riot_client, sample_players):
        """Test cancelling extraction operation."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        # Set some players to running status
        for player in sample_players[:2]:
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.RUNNING
            })
        
        # Cancel operation
        result = monitor.cancel_operation(operation_id)
        assert result is True
        
        # Should set cancellation event
        assert monitor.cancellation_events[operation_id].is_set()
        
        # Should update player statuses
        for player in sample_players[:2]:
            progress = monitor.active_operations[operation_id][player.name]
            assert progress.status == ExtractionStatus.CANCELLED
            assert progress.end_time is not None
    
    def test_should_cancel_operation(self, mock_config, mock_riot_client, sample_players):
        """Test checking if operation should be cancelled."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        # Initially should not be cancelled
        assert monitor.should_cancel_operation(operation_id) is False
        
        # After cancellation, should be cancelled
        monitor.cancel_operation(operation_id)
        assert monitor.should_cancel_operation(operation_id) is True
    
    def test_get_operation_status(self, mock_config, mock_riot_client, sample_players):
        """Test getting operation status."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        # Update some progress
        monitor.update_player_progress(operation_id, sample_players[0].name, {
            'status': ExtractionStatus.COMPLETED,
            'matches_extracted': 50
        })
        monitor.update_player_progress(operation_id, sample_players[1].name, {
            'status': ExtractionStatus.RUNNING,
            'matches_extracted': 25
        })
        
        # Add an error
        monitor.record_extraction_error(
            operation_id, sample_players[2].name, "test_error", "Test error message"
        )
        
        status = monitor.get_operation_status(operation_id)
        
        assert status['operation_id'] == operation_id
        assert status['total_players'] == len(sample_players)
        assert status['completed_players'] == 1
        assert status['running_players'] == 1
        assert status['total_matches_extracted'] == 75
        assert status['total_errors'] == 1
        assert len(status['players']) == len(sample_players)
        assert len(status['recent_errors']) == 1
        assert 'rate_limit_status' in status
        assert status['can_cancel'] is True
    
    def test_get_operation_status_not_found(self, mock_config, mock_riot_client):
        """Test getting status for non-existent operation."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        status = monitor.get_operation_status("non_existent")
        assert 'error' in status
        assert status['error'] == 'Operation not found'
    
    def test_start_stop_monitoring(self, mock_config, mock_riot_client):
        """Test starting and stopping monitoring thread."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring_active is True
        assert monitor.monitoring_thread is not None
        assert monitor.monitoring_thread.is_alive()
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.monitoring_active is False
        
        # Give thread time to stop
        time.sleep(0.1)
        if monitor.monitoring_thread:
            assert not monitor.monitoring_thread.is_alive()
    
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_monitoring_loop_cleanup(self, mock_sleep, mock_config, mock_riot_client, sample_players):
        """Test monitoring loop cleanup of completed operations."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        # Mark all players as completed
        for player in sample_players:
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.COMPLETED
            })
        
        # Start monitoring briefly
        monitor.start_monitoring()
        time.sleep(0.1)  # Let monitoring loop run once
        monitor.stop_monitoring()
        
        # Operation should be cleaned up
        assert operation_id not in monitor.active_operations
        assert operation_id not in monitor.cancellation_events


class TestErrorScenarios:
    """Test cases for various error scenarios and recovery mechanisms."""
    
    def test_network_timeout_retry(self, mock_config, mock_riot_client):
        """Test retry logic for network timeout errors."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        error = ExtractionError(
            error_id="timeout_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="network_timeout",
            error_message="Request timed out",
            severity=ErrorSeverity.MEDIUM,
            retry_count=0,
            max_retries=3
        )
        
        # Should be retryable
        assert monitor.retry_manager.should_retry(error) is True
        
        # Should have reasonable delay
        delay = monitor.retry_manager.get_retry_delay(error.error_id, error.retry_count)
        assert 0.5 <= delay <= 2.0
    
    def test_api_key_error_no_retry(self, mock_config, mock_riot_client):
        """Test that API key errors are not retried."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        error = ExtractionError(
            error_id="api_key_error",
            timestamp=datetime.now(),
            operation_id="test_op",
            player_name="test_player",
            error_type="invalid_api_key",
            error_message="Invalid API key",
            severity=ErrorSeverity.HIGH,
            retry_count=0,
            max_retries=3
        )
        
        # Should not be retryable
        assert monitor.retry_manager.should_retry(error) is False
    
    def test_rate_limit_handling(self, mock_config, mock_riot_client):
        """Test rate limit handling and throttling."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        # Simulate rate limit hit
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '30'}
        
        monitor.rate_monitor.handle_rate_limit_response("test_endpoint", mock_response)
        
        # Should be throttled
        assert not monitor.rate_monitor.can_make_request("test_endpoint")
        
        # Should have wait time
        wait_time = monitor.rate_monitor.get_wait_time("test_endpoint")
        assert wait_time > 0
    
    def test_data_corruption_detection(self, mock_config, mock_riot_client):
        """Test detection of corrupted match data."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        # Corrupted match data
        corrupted_data = {
            'gameId': 12345,
            # Missing required fields
            'participants': [{'id': i} for i in range(5)]  # Wrong participant count
        }
        
        checks = monitor.quality_validator.validate_match_data(corrupted_data)
        
        # Should detect multiple issues
        failed_checks = [check for check in checks if not check.passed]
        assert len(failed_checks) > 0
        
        # Quality score should be low
        quality_score = monitor.quality_validator.calculate_quality_score(checks)
        assert quality_score < 50
    
    def test_stalled_operation_detection(self, mock_config, mock_riot_client, sample_players):
        """Test detection of stalled operations."""
        monitor = AdvancedExtractionMonitor(mock_config, mock_riot_client)
        
        operation_id = "test_operation"
        monitor.create_extraction_operation(operation_id, sample_players)
        
        # Set player to running with old start time
        old_time = datetime.now() - timedelta(minutes=15)
        progress = monitor.active_operations[operation_id][sample_players[0].name]
        progress.status = ExtractionStatus.RUNNING
        progress.start_time = old_time
        progress.matches_extracted = 0  # No progress
        
        # Check for stalled operations
        monitor._check_stalled_operations()
        
        # Should have recorded stall error
        errors = monitor.operation_errors[operation_id]
        stall_errors = [e for e in errors if e.error_type == "stalled_operation"]
        assert len(stall_errors) > 0
        assert stall_errors[0].severity == ErrorSeverity.HIGH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])