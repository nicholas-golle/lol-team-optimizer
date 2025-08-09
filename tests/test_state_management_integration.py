"""
Integration Tests for State Management System

This module contains integration tests that verify the state management
system works correctly with the Gradio interface and core engine.
"""

import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from lol_team_optimizer.enhanced_state_manager import EnhancedStateManager
from lol_team_optimizer.gradio_interface_controller import GradioInterface
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.web_state_models import (
    UserPreferences, OperationState, ShareableResult, SQLiteStorage
)


class TestStateManagementIntegration:
    """Integration tests for state management system."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield SQLiteStorage(str(Path(temp_dir) / "integration_test.db"))
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create mock core engine for testing."""
        engine = Mock(spec=CoreEngine)
        engine.api_available = True
        engine.analytics_available = True
        engine.data_manager = Mock()
        engine.data_manager.load_player_data.return_value = []
        engine.get_migration_status.return_value = {"migration_needed": False}
        return engine
    
    @pytest.fixture
    def state_manager(self, temp_storage):
        """Create enhanced state manager for testing."""
        return EnhancedStateManager(
            cache_size_mb=10,
            max_sessions=50,
            persistent_storage=temp_storage
        )
    
    @pytest.fixture
    def gradio_interface(self, mock_core_engine, state_manager):
        """Create Gradio interface with enhanced state management."""
        interface = GradioInterface(mock_core_engine)
        interface.enhanced_state_manager = state_manager
        return interface
    
    def test_session_creation_and_management(self, state_manager):
        """Test session creation and management workflow."""
        # Create session with preferences
        preferences = UserPreferences(
            theme="dark",
            max_results_per_page=100,
            auto_refresh_interval=30
        )
        
        session_id = state_manager.create_session(preferences)
        assert session_id is not None
        
        # Verify session exists and has correct preferences
        session = state_manager.get_session(session_id)
        assert session is not None
        assert session.user_preferences.theme == "dark"
        assert session.user_preferences.max_results_per_page == 100
        
        # Update session state
        assert state_manager.update_session_state(session_id, "current_tab", "analytics")
        assert state_manager.update_session_state(session_id, "selected_players", ["player1", "player2"])
        
        # Verify updates
        updated_session = state_manager.get_session(session_id)
        assert updated_session.current_tab == "analytics"
        assert updated_session.selected_players == ["player1", "player2"]
    
    def test_cache_workflow_with_dependencies(self, state_manager):
        """Test caching workflow with dependency management."""
        # Cache base data
        player_data = {"player1": {"rank": "diamond", "role": "adc"}}
        assert state_manager.cache_result("player_data", player_data, ttl=3600)
        
        # Cache dependent analytics data
        analytics_data = {"win_rate": 0.65, "kda": 2.1}
        assert state_manager.cache_result(
            "analytics_player1", 
            analytics_data, 
            ttl=1800,
            dependencies=["player_data"]
        )
        
        # Verify both cached
        assert state_manager.get_cached_result("player_data") == player_data
        assert state_manager.get_cached_result("analytics_player1") == analytics_data
        
        # Invalidate base data - should invalidate dependent data too
        invalidated = state_manager.invalidate_cache("player_data")
        assert "player_data" in invalidated
        assert "analytics_player1" in invalidated
        
        # Verify both invalidated
        assert state_manager.get_cached_result("player_data") is None
        assert state_manager.get_cached_result("analytics_player1") is None
    
    def test_operation_state_tracking(self, state_manager):
        """Test operation state tracking workflow."""
        # Create session
        session_id = state_manager.create_session()
        
        # Create and add operation
        operation = OperationState(
            operation_id="match_extraction_001",
            operation_type="match_extraction",
            status="pending",
            progress_percentage=0.0,
            status_message="Initializing extraction..."
        )
        
        assert state_manager.add_operation(session_id, operation)
        
        # Simulate operation progress updates
        progress_updates = [
            {"status": "running", "progress_percentage": 25.0, "status_message": "Extracting matches..."},
            {"status": "running", "progress_percentage": 50.0, "status_message": "Processing data..."},
            {"status": "running", "progress_percentage": 75.0, "status_message": "Finalizing..."},
            {"status": "completed", "progress_percentage": 100.0, "status_message": "Extraction complete"}
        ]
        
        for update in progress_updates:
            assert state_manager.update_operation(session_id, "match_extraction_001", update)
            
            # Verify update applied
            session = state_manager.get_session(session_id)
            op = session.operation_states["match_extraction_001"]
            assert op.status == update["status"]
            assert op.progress_percentage == update["progress_percentage"]
            assert op.status_message == update["status_message"]
    
    def test_real_time_event_system(self, state_manager):
        """Test real-time event system."""
        received_events = []
        
        def event_handler(event):
            received_events.append(event)
        
        # Subscribe to state change events
        state_manager.subscribe_to_events("state_change", event_handler)
        
        # Create session and make state changes
        session_id = state_manager.create_session()
        
        # Update session state (should trigger events)
        state_manager.update_session_state(session_id, "current_tab", "player_management")
        state_manager.update_session_state(session_id, "selected_players", ["player1"])
        
        # Allow async event processing
        time.sleep(0.2)
        
        # Verify events received
        assert len(received_events) >= 2
        
        # Check event structure
        for event in received_events:
            assert "type" in event
            assert "data" in event
            assert "timestamp" in event
            assert event["type"] == "state_change"
            assert "session_id" in event["data"]
            assert event["data"]["session_id"] == session_id
    
    def test_shareable_results_workflow(self, state_manager):
        """Test shareable results creation and access."""
        # Create session
        session_id = state_manager.create_session()
        
        # Create shareable result
        analysis_data = {
            "player_performance": {"win_rate": 0.68, "avg_kda": 2.3},
            "champion_recommendations": ["Jinx", "Caitlyn", "Ezreal"],
            "team_synergy": {"score": 8.5, "strengths": ["early_game", "team_fights"]}
        }
        
        result = state_manager.create_shareable_result(
            result_type="player_analysis",
            title="Player Performance Analysis",
            description="Comprehensive analysis of player performance and recommendations",
            data=analysis_data,
            session_id=session_id,
            expiration_hours=48
        )
        
        assert result.result_id is not None
        assert result.title == "Player Performance Analysis"
        assert result.data == analysis_data
        assert result.created_by_session == session_id
        
        # Access shareable result
        retrieved_result = state_manager.get_shareable_result(result.result_id)
        assert retrieved_result is not None
        assert retrieved_result.data == analysis_data
        assert retrieved_result.access_count == 1
        
        # Access again - should increment count
        retrieved_again = state_manager.get_shareable_result(result.result_id)
        assert retrieved_again.access_count == 2
    
    def test_user_preferences_persistence(self, state_manager):
        """Test user preferences persistence across sessions."""
        # Create session with custom preferences
        custom_preferences = UserPreferences(
            theme="dark",
            default_chart_type="bar",
            max_results_per_page=200,
            auto_refresh_interval=45,
            show_advanced_options=True,
            notification_settings={
                "extraction_complete": True,
                "analysis_ready": False,
                "errors": True,
                "warnings": True
            }
        )
        
        session_id = state_manager.create_session(custom_preferences)
        
        # Verify preferences saved
        saved_preferences = state_manager.get_user_preferences(session_id)
        assert saved_preferences.theme == "dark"
        assert saved_preferences.default_chart_type == "bar"
        assert saved_preferences.max_results_per_page == 200
        assert saved_preferences.show_advanced_options is True
        assert saved_preferences.notification_settings["analysis_ready"] is False
        
        # Update preferences
        updated_preferences = UserPreferences(
            theme="light",
            default_chart_type="radar",
            max_results_per_page=150
        )
        
        assert state_manager.save_user_preferences(session_id, updated_preferences)
        
        # Verify updates
        final_preferences = state_manager.get_user_preferences(session_id)
        assert final_preferences.theme == "light"
        assert final_preferences.default_chart_type == "radar"
        assert final_preferences.max_results_per_page == 150
    
    def test_concurrent_session_management(self, state_manager):
        """Test concurrent session management."""
        import threading
        
        session_ids = []
        errors = []
        
        def create_session_worker(worker_id):
            try:
                # Create session with unique preferences
                preferences = UserPreferences(
                    theme=f"theme_{worker_id}",
                    max_results_per_page=50 + worker_id * 10
                )
                
                session_id = state_manager.create_session(preferences)
                session_ids.append(session_id)
                
                # Perform operations
                state_manager.update_session_state(session_id, "worker_id", worker_id)
                state_manager.cache_result(f"worker_{worker_id}_data", f"data_{worker_id}")
                
                # Create operation
                operation = OperationState(
                    operation_id=f"op_{worker_id}",
                    operation_type="test",
                    status="running"
                )
                state_manager.add_operation(session_id, operation)
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Run concurrent workers
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_session_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(session_ids) == 10
        
        # Verify each session is unique and has correct data
        for i, session_id in enumerate(session_ids):
            session = state_manager.get_session(session_id)
            assert session is not None
            assert session.component_states.get("worker_id") == i
            assert session.user_preferences.theme == f"theme_{i}"
            
            # Verify cached data
            cached_data = state_manager.get_cached_result(f"worker_{i}_data")
            assert cached_data == f"data_{i}"
            
            # Verify operation
            assert f"op_{i}" in session.operation_states
    
    def test_system_statistics_and_monitoring(self, state_manager):
        """Test system statistics and monitoring."""
        # Create some activity
        session_ids = []
        for i in range(5):
            session_id = state_manager.create_session()
            session_ids.append(session_id)
            
            # Cache some data
            state_manager.cache_result(f"test_data_{i}", f"value_{i}")
            
            # Create shareable result
            state_manager.create_shareable_result(
                result_type="test",
                title=f"Test Result {i}",
                description="Test description",
                data={"test": i},
                session_id=session_id
            )
        
        # Get system statistics
        stats = state_manager.get_system_statistics()
        
        # Verify statistics structure and values
        assert "cache" in stats
        assert "sessions" in stats
        assert "shared_results" in stats
        
        # Cache statistics
        cache_stats = stats["cache"]
        assert cache_stats["total_entries"] >= 5
        assert cache_stats["total_size_mb"] > 0
        
        # Session statistics
        session_stats = stats["sessions"]
        assert session_stats["total_sessions"] >= 5
        assert session_stats["active_sessions"] >= 5
        
        # Shared results statistics
        shared_stats = stats["shared_results"]
        assert shared_stats["total_results"] >= 5
        assert shared_stats["active_results"] >= 5
    
    def test_cache_expiration_and_cleanup(self, state_manager):
        """Test cache expiration and cleanup mechanisms."""
        # Cache data with short TTL
        state_manager.cache_result("short_ttl_data", "test_value", ttl=1)
        assert state_manager.get_cached_result("short_ttl_data") == "test_value"
        
        # Cache data with long TTL
        state_manager.cache_result("long_ttl_data", "persistent_value", ttl=3600)
        assert state_manager.get_cached_result("long_ttl_data") == "persistent_value"
        
        # Wait for short TTL to expire
        time.sleep(1.5)
        
        # Short TTL data should be expired
        assert state_manager.get_cached_result("short_ttl_data") is None
        
        # Long TTL data should still be available
        assert state_manager.get_cached_result("long_ttl_data") == "persistent_value"
        
        # Test manual cleanup
        cleanup_result = state_manager.cleanup_expired_data()
        assert isinstance(cleanup_result, dict)
        assert "expired_shared_results" in cleanup_result
    
    def test_persistence_across_manager_instances(self, temp_storage):
        """Test data persistence across state manager instances."""
        # Create first state manager instance
        state_manager1 = EnhancedStateManager(persistent_storage=temp_storage)
        
        # Create session and cache data
        session_id = state_manager1.create_session()
        state_manager1.update_session_state(session_id, "test_key", "test_value")
        state_manager1.cache_result("persistent_cache", "cached_value", ttl=3600)
        
        # Create second state manager instance with same storage
        state_manager2 = EnhancedStateManager(persistent_storage=temp_storage)
        
        # Session should be loaded from persistence
        loaded_session = state_manager2.get_session(session_id)
        assert loaded_session is not None
        assert loaded_session.component_states.get("test_key") == "test_value"
        
        # Cache should be loaded from persistence
        cached_value = state_manager2.get_cached_result("persistent_cache")
        assert cached_value == "cached_value"


class TestGradioInterfaceIntegration:
    """Test Gradio interface integration with enhanced state management."""
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create mock core engine for testing."""
        engine = Mock(spec=CoreEngine)
        engine.api_available = True
        engine.analytics_available = True
        engine.data_manager = Mock()
        engine.data_manager.load_player_data.return_value = []
        engine.get_migration_status.return_value = {"migration_needed": False}
        return engine
    
    def test_interface_initialization_with_enhanced_state(self, mock_core_engine):
        """Test Gradio interface initialization with enhanced state management."""
        interface = GradioInterface(mock_core_engine)
        
        # Verify enhanced state manager is initialized
        assert hasattr(interface, 'enhanced_state_manager')
        assert interface.enhanced_state_manager is not None
        
        # Verify session creation
        demo = interface.create_interface()
        assert demo is not None
        assert interface.current_session_id is not None
        
        # Verify session exists in enhanced state manager
        session = interface.enhanced_state_manager.get_session(interface.current_session_id)
        assert session is not None
    
    def test_interface_state_management_integration(self, mock_core_engine):
        """Test integration between interface and state management."""
        interface = GradioInterface(mock_core_engine)
        interface.create_interface()
        
        session_id = interface.current_session_id
        state_manager = interface.enhanced_state_manager
        
        # Test state updates through interface
        assert state_manager.update_session_state(session_id, "current_tab", "analytics")
        assert state_manager.update_session_state(session_id, "selected_players", ["test_player"])
        
        # Verify updates
        session = state_manager.get_session(session_id)
        assert session.current_tab == "analytics"
        assert session.selected_players == ["test_player"]
        
        # Test caching through interface
        test_data = {"analysis": "test_analysis"}
        assert state_manager.cache_result("interface_test", test_data)
        
        cached_data = state_manager.get_cached_result("interface_test")
        assert cached_data == test_data


if __name__ == "__main__":
    pytest.main([__file__])