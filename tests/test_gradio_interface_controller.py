"""
Unit tests for Gradio Interface Controller and State Management

Tests the enhanced Gradio interface controller with modular architecture,
including state management, data flow, error handling, and component integration.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import pytest
from datetime import datetime, timedelta
import uuid
import sys
import os

# Add the parent directory to the path to import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lol_team_optimizer.gradio_interface_controller import (
    GradioInterface,
    StateManager,
    DataFlowManager,
    WebErrorHandler,
    SessionState,
    OperationResult
)
from lol_team_optimizer.models import Player


class TestSessionState(unittest.TestCase):
    """Test SessionState dataclass."""
    
    def test_session_state_creation(self):
        """Test creating a new session state."""
        session_id = "test-session-123"
        created_at = datetime.now()
        last_activity = datetime.now()
        
        session = SessionState(
            session_id=session_id,
            created_at=created_at,
            last_activity=last_activity
        )
        
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(session.created_at, created_at)
        self.assertEqual(session.last_activity, last_activity)
        self.assertEqual(session.current_tab, "player_management")
        self.assertEqual(session.selected_players, [])
        self.assertEqual(session.active_filters, {})
        self.assertEqual(session.cached_results, {})
        self.assertEqual(session.user_preferences, {})
        self.assertEqual(session.operation_states, {})


class TestOperationResult(unittest.TestCase):
    """Test OperationResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful operation result."""
        result = OperationResult(
            success=True,
            message="Operation completed successfully",
            data={"key": "value"}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Operation completed successfully")
        self.assertEqual(result.data, {"key": "value"})
        self.assertIsNone(result.error_details)
        self.assertIsNone(result.operation_id)
    
    def test_error_result(self):
        """Test creating an error operation result."""
        result = OperationResult(
            success=False,
            message="Operation failed",
            error_details="Detailed error information"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Operation failed")
        self.assertEqual(result.error_details, "Detailed error information")
        self.assertIsNone(result.data)


class TestStateManager(unittest.TestCase):
    """Test StateManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.state_manager = StateManager()
    
    def test_create_session(self):
        """Test creating a new session."""
        session_id = self.state_manager.create_session()
        
        self.assertIsInstance(session_id, str)
        self.assertTrue(len(session_id) > 0)
        
        # Verify session exists
        session = self.state_manager.get_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, session_id)
    
    def test_get_nonexistent_session(self):
        """Test getting a session that doesn't exist."""
        session = self.state_manager.get_session("nonexistent-session")
        self.assertIsNone(session)
    
    def test_update_session_state(self):
        """Test updating session state."""
        session_id = self.state_manager.create_session()
        
        # Test updating current tab
        success = self.state_manager.update_session_state(session_id, "current_tab", "analytics")
        self.assertTrue(success)
        
        session = self.state_manager.get_session(session_id)
        self.assertEqual(session.current_tab, "analytics")
        
        # Test updating selected players
        players = ["Player1", "Player2"]
        success = self.state_manager.update_session_state(session_id, "selected_players", players)
        self.assertTrue(success)
        
        session = self.state_manager.get_session(session_id)
        self.assertEqual(session.selected_players, players)
        
        # Test updating active filters
        filters = {"role": "middle", "days": 30}
        success = self.state_manager.update_session_state(session_id, "active_filters", filters)
        self.assertTrue(success)
        
        session = self.state_manager.get_session(session_id)
        self.assertEqual(session.active_filters, filters)
        
        # Test updating user preferences
        preferences = {"theme": "dark", "language": "en"}
        success = self.state_manager.update_session_state(session_id, "user_preferences", preferences)
        self.assertTrue(success)
        
        session = self.state_manager.get_session(session_id)
        self.assertEqual(session.user_preferences, preferences)
        
        # Test updating custom operation state
        operation_data = {"status": "running", "progress": 0.5}
        success = self.state_manager.update_session_state(session_id, "custom_operation", operation_data)
        self.assertTrue(success)
        
        session = self.state_manager.get_session(session_id)
        self.assertEqual(session.operation_states["custom_operation"], operation_data)
    
    def test_update_nonexistent_session(self):
        """Test updating a session that doesn't exist."""
        success = self.state_manager.update_session_state("nonexistent", "current_tab", "analytics")
        self.assertFalse(success)
    
    def test_cache_operations(self):
        """Test caching and retrieving results."""
        # Cache a result
        key = "test_key"
        value = {"data": "test_value"}
        self.state_manager.cache_result(key, value)
        
        # Retrieve cached result
        cached_value = self.state_manager.get_cached_result(key)
        self.assertEqual(cached_value, value)
        
        # Test cache miss
        missing_value = self.state_manager.get_cached_result("nonexistent_key")
        self.assertIsNone(missing_value)
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        key = "expiring_key"
        value = {"data": "expiring_value"}
        
        # Cache with very short TTL
        self.state_manager.cache_result(key, value, ttl=1)
        
        # Should be available immediately
        cached_value = self.state_manager.get_cached_result(key)
        self.assertEqual(cached_value, value)
        
        # Manually expire the cache
        self.state_manager.cache_ttl[key] = datetime.now() - timedelta(seconds=1)
        
        # Should be None after expiration
        expired_value = self.state_manager.get_cached_result(key)
        self.assertIsNone(expired_value)
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        # Cache multiple items
        self.state_manager.cache_result("key1", "value1")
        self.state_manager.cache_result("key2", "value2")
        self.state_manager.cache_result("analytics_key", "analytics_value")
        
        # Verify all cached
        self.assertIsNotNone(self.state_manager.get_cached_result("key1"))
        self.assertIsNotNone(self.state_manager.get_cached_result("key2"))
        self.assertIsNotNone(self.state_manager.get_cached_result("analytics_key"))
        
        # Invalidate by pattern
        self.state_manager.invalidate_cache("analytics")
        
        # Analytics key should be gone, others should remain
        self.assertIsNotNone(self.state_manager.get_cached_result("key1"))
        self.assertIsNotNone(self.state_manager.get_cached_result("key2"))
        self.assertIsNone(self.state_manager.get_cached_result("analytics_key"))
        
        # Clear all cache
        self.state_manager.invalidate_cache()
        
        # All should be gone
        self.assertIsNone(self.state_manager.get_cached_result("key1"))
        self.assertIsNone(self.state_manager.get_cached_result("key2"))
    
    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        # Create sessions
        session1_id = self.state_manager.create_session()
        session2_id = self.state_manager.create_session()
        
        # Manually set one session as old
        old_time = datetime.now() - timedelta(hours=25)
        self.state_manager.sessions[session1_id].last_activity = old_time
        
        # Cleanup with 24 hour threshold
        self.state_manager.cleanup_expired_sessions(max_age_hours=24)
        
        # Old session should be gone, new one should remain
        self.assertIsNone(self.state_manager.get_session(session1_id))
        self.assertIsNotNone(self.state_manager.get_session(session2_id))


class TestWebErrorHandler(unittest.TestCase):
    """Test WebErrorHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = WebErrorHandler()
    
    def test_handle_generic_error(self):
        """Test handling a generic error."""
        error = Exception("Test error message")
        result = self.error_handler.handle_error(error, "test_context")
        
        self.assertFalse(result.success)
        self.assertIn("server error", result.message.lower())
        self.assertIsNotNone(result.error_details)
        self.assertIn("Error ID:", result.error_details)
    
    def test_handle_api_error(self):
        """Test handling API-related errors."""
        error = ConnectionError("API connection failed")
        result = self.error_handler.handle_error(error, "api_call")
        
        self.assertFalse(result.success)
        self.assertIn("Riot API", result.message)
    
    def test_handle_validation_error(self):
        """Test handling validation errors."""
        error = ValueError("Invalid input value")
        result = self.error_handler.handle_error(error, "validation")
        
        self.assertFalse(result.success)
        self.assertIn("check your input", result.message.lower())
    
    def test_handle_timeout_error(self):
        """Test handling timeout errors."""
        error = TimeoutError("Operation timed out")
        result = self.error_handler.handle_error(error, "long_operation")
        
        self.assertFalse(result.success)
        self.assertIn("took too long", result.message.lower())
    
    def test_handle_not_found_error(self):
        """Test handling not found errors."""
        error = KeyError("Key not found")
        result = self.error_handler.handle_error(error, "data_lookup")
        
        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        error = Exception("Test error")
        
        # Clear error log
        self.error_handler.error_log.clear()
        
        result = self.error_handler.handle_error(error, "test_context")
        
        # Check that error was logged
        self.assertEqual(len(self.error_handler.error_log), 1)
        
        log_entry = self.error_handler.error_log[0]
        self.assertIn("error_id", log_entry)
        self.assertIn("timestamp", log_entry)
        self.assertIn("error_type", log_entry)
        self.assertIn("error_message", log_entry)
        self.assertIn("context", log_entry)
        self.assertIn("traceback", log_entry)
        
        self.assertEqual(log_entry["context"], "test_context")
        self.assertEqual(log_entry["error_message"], "Test error")
    
    def test_get_error_log(self):
        """Test retrieving error log."""
        # Generate multiple errors
        for i in range(10):
            error = Exception(f"Test error {i}")
            self.error_handler.handle_error(error, f"context_{i}")
        
        # Get limited log
        log_entries = self.error_handler.get_error_log(limit=5)
        self.assertEqual(len(log_entries), 5)
        
        # Should get the most recent entries
        self.assertIn("Test error 9", log_entries[-1]["error_message"])
        self.assertIn("Test error 5", log_entries[0]["error_message"])


class TestDataFlowManager(unittest.TestCase):
    """Test DataFlowManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_core_engine = Mock()
        self.mock_state_manager = Mock()
        self.data_flow_manager = DataFlowManager(self.mock_core_engine, self.mock_state_manager)
    
    def test_register_event_handler(self):
        """Test registering event handlers."""
        handler = Mock()
        self.data_flow_manager.register_event_handler("test_event", handler)
        
        self.assertIn("test_event", self.data_flow_manager.event_handlers)
        self.assertIn(handler, self.data_flow_manager.event_handlers["test_event"])
    
    def test_emit_event(self):
        """Test emitting events to handlers."""
        handler1 = Mock()
        handler2 = Mock()
        
        self.data_flow_manager.register_event_handler("test_event", handler1)
        self.data_flow_manager.register_event_handler("test_event", handler2)
        
        test_data = {"key": "value"}
        self.data_flow_manager.emit_event("test_event", test_data)
        
        handler1.assert_called_once_with(test_data)
        handler2.assert_called_once_with(test_data)
    
    def test_emit_event_with_handler_error(self):
        """Test emitting events when a handler raises an error."""
        good_handler = Mock()
        bad_handler = Mock(side_effect=Exception("Handler error"))
        
        self.data_flow_manager.register_event_handler("test_event", good_handler)
        self.data_flow_manager.register_event_handler("test_event", bad_handler)
        
        # Should not raise exception even if handler fails
        test_data = {"key": "value"}
        self.data_flow_manager.emit_event("test_event", test_data)
        
        # Good handler should still be called
        good_handler.assert_called_once_with(test_data)
    
    def test_handle_player_update_success(self):
        """Test successful player update handling."""
        session_id = "test-session"
        player_data = {
            "name": "Test Player",
            "summoner_name": "TestSummoner",
            "riot_id": "TestPlayer#NA1",
            "region": "na1"
        }
        
        # Mock successful player addition
        self.mock_core_engine.data_manager.add_player = Mock()
        
        result = self.data_flow_manager.handle_player_update(session_id, player_data)
        
        self.assertTrue(result.success)
        self.assertIn("Successfully added player", result.message)
        self.assertIsNotNone(result.data)
        
        # Verify player was added to core engine
        self.mock_core_engine.data_manager.add_player.assert_called_once()
        
        # Verify cache invalidation
        self.mock_state_manager.invalidate_cache.assert_called_with("player_")
    
    def test_handle_player_update_missing_fields(self):
        """Test player update with missing required fields."""
        session_id = "test-session"
        player_data = {
            "name": "Test Player",
            # Missing summoner_name, riot_id, region
        }
        
        result = self.data_flow_manager.handle_player_update(session_id, player_data)
        
        self.assertFalse(result.success)
        self.assertIn("Missing required player fields", result.message)
    
    def test_handle_player_update_exception(self):
        """Test player update when core engine raises exception."""
        session_id = "test-session"
        player_data = {
            "name": "Test Player",
            "summoner_name": "TestSummoner",
            "riot_id": "TestPlayer#NA1",
            "region": "na1"
        }
        
        # Mock exception in core engine
        self.mock_core_engine.data_manager.add_player.side_effect = Exception("Database error")
        
        result = self.data_flow_manager.handle_player_update(session_id, player_data)
        
        self.assertFalse(result.success)
        self.assertIn("Failed to add player", result.message)
        self.assertIsNotNone(result.error_details)
    
    def test_handle_match_extraction_success(self):
        """Test successful match extraction handling."""
        session_id = "test-session"
        extraction_params = {
            "player_selection": "Test Player (TestSummoner)",
            "days": 30
        }
        
        # Mock player data
        mock_player = Player(
            name="Test Player",
            summoner_name="TestSummoner",
            puuid="test-puuid",
            riot_id="TestPlayer#NA1",
            region="na1"
        )
        self.mock_core_engine.data_manager.load_player_data.return_value = [mock_player]
        
        # Mock successful extraction
        self.mock_core_engine.extract_player_matches.return_value = {
            "success": True,
            "matches_extracted": 25
        }
        
        result = self.data_flow_manager.handle_match_extraction(session_id, extraction_params)
        
        self.assertTrue(result.success)
        self.assertIn("Extracted 25 matches", result.message)
        self.assertIsNotNone(result.operation_id)
        
        # Verify extraction was called
        self.mock_core_engine.extract_player_matches.assert_called_once_with(
            "TestSummoner", "TestPlayer#NA1", days_back=30
        )
        
        # Verify cache invalidation
        self.mock_state_manager.invalidate_cache.assert_called_with("analytics_")
    
    def test_handle_match_extraction_no_player(self):
        """Test match extraction with no player selected."""
        session_id = "test-session"
        extraction_params = {}  # No player_selection
        
        result = self.data_flow_manager.handle_match_extraction(session_id, extraction_params)
        
        self.assertFalse(result.success)
        self.assertIn("No player selected", result.message)
    
    def test_handle_match_extraction_player_not_found(self):
        """Test match extraction with player not found."""
        session_id = "test-session"
        extraction_params = {
            "player_selection": "Nonexistent Player",
            "days": 30
        }
        
        # Mock empty player data
        self.mock_core_engine.data_manager.load_player_data.return_value = []
        
        result = self.data_flow_manager.handle_match_extraction(session_id, extraction_params)
        
        self.assertFalse(result.success)
        self.assertIn("Selected player not found", result.message)
    
    def test_handle_analytics_request_cached(self):
        """Test analytics request with cached result."""
        session_id = "test-session"
        analytics_params = {
            "player_selection": "Test Player (TestSummoner)",
            "days": 60
        }
        
        # Mock cached result
        cached_analytics = {"cached": True}
        self.mock_state_manager.get_cached_result.return_value = cached_analytics
        
        result = self.data_flow_manager.handle_analytics_request(session_id, analytics_params)
        
        self.assertTrue(result.success)
        self.assertIn("retrieved from cache", result.message)
        self.assertEqual(result.data, cached_analytics)
    
    def test_handle_analytics_request_no_cache(self):
        """Test analytics request without cached result."""
        session_id = "test-session"
        analytics_params = {
            "player_selection": "Test Player (TestSummoner)",
            "days": 60
        }
        
        # Mock no cached result
        self.mock_state_manager.get_cached_result.return_value = None
        
        # Mock analytics availability
        self.mock_core_engine.analytics_available = True
        
        # Mock player data
        mock_player = Player(
            name="Test Player",
            summoner_name="TestSummoner",
            puuid="test-puuid",
            riot_id="TestPlayer#NA1",
            region="na1"
        )
        self.mock_core_engine.data_manager.load_player_data.return_value = [mock_player]
        
        # Mock analytics result
        mock_analytics = {"analytics": "data"}
        self.mock_core_engine.historical_analytics_engine.analyze_player_performance.return_value = mock_analytics
        
        result = self.data_flow_manager.handle_analytics_request(session_id, analytics_params)
        
        self.assertTrue(result.success)
        self.assertIn("Analytics generated successfully", result.message)
        self.assertEqual(result.data, mock_analytics)
        
        # Verify caching was called
        self.mock_state_manager.cache_result.assert_called_once()
    
    def test_handle_analytics_request_not_available(self):
        """Test analytics request when analytics not available."""
        session_id = "test-session"
        analytics_params = {
            "player_selection": "Test Player (TestSummoner)",
            "days": 60
        }
        
        # Mock no cached result
        self.mock_state_manager.get_cached_result.return_value = None
        
        # Mock analytics not available
        self.mock_core_engine.analytics_available = False
        
        result = self.data_flow_manager.handle_analytics_request(session_id, analytics_params)
        
        self.assertFalse(result.success)
        self.assertIn("Analytics engine not available", result.message)


class TestGradioInterface(unittest.TestCase):
    """Test GradioInterface class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_core_engine = Mock()
        self.mock_core_engine.api_available = True
        self.mock_core_engine.analytics_available = True
        self.mock_core_engine.get_migration_status.return_value = None
        
    @patch('lol_team_optimizer.gradio_interface_controller.CoreEngine')
    def test_init_with_default_core_engine(self, mock_core_engine_class):
        """Test initialization with default core engine."""
        mock_core_engine_instance = Mock()
        mock_core_engine_class.return_value = mock_core_engine_instance
        
        interface = GradioInterface()
        
        self.assertEqual(interface.core_engine, mock_core_engine_instance)
        self.assertIsInstance(interface.state_manager, StateManager)
        self.assertIsInstance(interface.data_flow_manager, DataFlowManager)
        self.assertIsInstance(interface.error_handler, WebErrorHandler)
    
    def test_init_with_provided_core_engine(self):
        """Test initialization with provided core engine."""
        interface = GradioInterface(self.mock_core_engine)
        
        self.assertEqual(interface.core_engine, self.mock_core_engine)
        self.assertIsInstance(interface.state_manager, StateManager)
        self.assertIsInstance(interface.data_flow_manager, DataFlowManager)
        self.assertIsInstance(interface.error_handler, WebErrorHandler)
    
    @patch('lol_team_optimizer.gradio_interface_controller.CoreEngine')
    def test_init_core_engine_failure(self, mock_core_engine_class):
        """Test initialization when core engine fails."""
        mock_core_engine_class.side_effect = Exception("Core engine failed")
        
        with self.assertRaises(RuntimeError) as context:
            GradioInterface()
        
        self.assertIn("Core engine initialization failed", str(context.exception))
    
    @patch('lol_team_optimizer.gradio_interface_controller.gr.Blocks')
    def test_create_interface(self, mock_blocks):
        """Test creating the Gradio interface."""
        interface = GradioInterface(self.mock_core_engine)
        
        # Mock the Blocks context manager
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        
        result = interface.create_interface()
        
        self.assertIsNotNone(interface.current_session_id)
        self.assertEqual(interface.demo, mock_blocks_instance)
        self.assertEqual(result, mock_blocks_instance)
    
    def test_get_system_status_display(self):
        """Test system status display generation."""
        interface = GradioInterface(self.mock_core_engine)
        
        status_display = interface._get_system_status_display()
        
        self.assertIn("System Status:", status_display)
        self.assertIn("Core Engine: Ready", status_display)
        self.assertIn("Riot API: Connected", status_display)
        self.assertIn("Analytics: Available", status_display)
    
    def test_get_system_status_display_with_issues(self):
        """Test system status display with various issues."""
        self.mock_core_engine.api_available = False
        self.mock_core_engine.analytics_available = False
        self.mock_core_engine.get_migration_status.return_value = {"migration_needed": True}
        
        interface = GradioInterface(self.mock_core_engine)
        
        status_display = interface._get_system_status_display()
        
        self.assertIn("Riot API: Not Available", status_display)
        self.assertIn("Analytics: Limited", status_display)
        self.assertIn("Migration: Required", status_display)
    
    def test_get_session_info(self):
        """Test getting session information."""
        interface = GradioInterface(self.mock_core_engine)
        interface.current_session_id = interface.state_manager.create_session()
        
        session_info = interface.get_session_info()
        
        self.assertIn("session_id", session_info)
        self.assertIn("created_at", session_info)
        self.assertIn("last_activity", session_info)
        self.assertIn("current_tab", session_info)
        self.assertIn("cache_size", session_info)
    
    def test_get_session_info_no_session(self):
        """Test getting session info when no session exists."""
        interface = GradioInterface(self.mock_core_engine)
        
        session_info = interface.get_session_info()
        
        self.assertIn("error", session_info)
        self.assertEqual(session_info["error"], "No active session")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete interface system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.mock_core_engine = Mock()
        self.mock_core_engine.api_available = True
        self.mock_core_engine.analytics_available = True
        self.mock_core_engine.get_migration_status.return_value = None
        
        # Mock data manager
        self.mock_core_engine.data_manager.load_player_data.return_value = []
        self.mock_core_engine.data_manager.add_player = Mock()
    
    def test_complete_player_workflow(self):
        """Test complete player management workflow."""
        interface = GradioInterface(self.mock_core_engine)
        
        # Add a player
        player_data = {
            "name": "Integration Test Player",
            "summoner_name": "IntegrationTest",
            "riot_id": "IntegrationTest#NA1",
            "region": "na1"
        }
        
        result = interface.data_flow_manager.handle_player_update(
            interface.current_session_id, player_data
        )
        
        self.assertTrue(result.success)
        self.mock_core_engine.data_manager.add_player.assert_called_once()
    
    def test_state_persistence_across_operations(self):
        """Test that state persists across multiple operations."""
        interface = GradioInterface(self.mock_core_engine)
        session_id = interface.current_session_id
        
        # Update session state
        interface.state_manager.update_session_state(session_id, "current_tab", "analytics")
        interface.state_manager.update_session_state(session_id, "selected_players", ["Player1"])
        
        # Verify state persists
        session = interface.state_manager.get_session(session_id)
        self.assertEqual(session.current_tab, "analytics")
        self.assertEqual(session.selected_players, ["Player1"])
        
        # Perform another operation
        interface.state_manager.cache_result("test_key", "test_value")
        
        # Verify original state still exists
        session = interface.state_manager.get_session(session_id)
        self.assertEqual(session.current_tab, "analytics")
        self.assertEqual(session.selected_players, ["Player1"])
        
        # Verify cache works
        cached_value = interface.state_manager.get_cached_result("test_key")
        self.assertEqual(cached_value, "test_value")
    
    def test_error_handling_integration(self):
        """Test error handling across the system."""
        interface = GradioInterface(self.mock_core_engine)
        
        # Simulate error in core engine
        self.mock_core_engine.data_manager.add_player.side_effect = Exception("Database connection failed")
        
        # Attempt player addition
        player_data = {
            "name": "Error Test Player",
            "summoner_name": "ErrorTest",
            "riot_id": "ErrorTest#NA1",
            "region": "na1"
        }
        
        result = interface.data_flow_manager.handle_player_update(
            interface.current_session_id, player_data
        )
        
        # Should handle error gracefully
        self.assertFalse(result.success)
        self.assertIn("Failed to add player", result.message)
        self.assertIsNotNone(result.error_details)
        
        # Error should be logged
        error_log = interface.error_handler.get_error_log()
        self.assertGreater(len(error_log), 0)


if __name__ == '__main__':
    # Set up logging for tests
    logging.basicConfig(level=logging.DEBUG)
    
    # Run tests
    unittest.main(verbosity=2)