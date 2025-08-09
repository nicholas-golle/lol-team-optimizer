"""
Tests for Enhanced State Manager

This module contains comprehensive tests for the enhanced state management
and caching system, including session management, cache strategies, and
real-time synchronization.
"""

import pytest
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from lol_team_optimizer.enhanced_state_manager import (
    EnhancedStateManager, AdvancedCacheManager, SessionManager,
    RealTimeSynchronizer, CacheInvalidationManager
)
from lol_team_optimizer.web_state_models import (
    WebInterfaceState, UserPreferences, OperationState, CacheEntry,
    CacheStrategy, SessionStatus, ShareableResult, SQLiteStorage, FileStorage
)


class TestCacheInvalidationManager:
    """Test cache invalidation manager."""
    
    def test_dependency_management(self):
        """Test dependency relationship management."""
        manager = CacheInvalidationManager()
        
        # Add dependencies
        manager.add_dependency("child1", "parent")
        manager.add_dependency("child2", "parent")
        manager.add_dependency("grandchild", "child1")
        
        # Test dependency retrieval
        dependents = manager.get_dependent_keys("parent")
        assert "child1" in dependents
        assert "child2" in dependents
        assert "grandchild" in dependents  # Transitive dependency
    
    def test_invalidation_callbacks(self):
        """Test invalidation callback system."""
        manager = CacheInvalidationManager()
        callback_called = []
        
        def test_callback(key):
            callback_called.append(key)
        
        manager.register_invalidation_callback("test_key", test_callback)
        invalidated = manager.invalidate_key("test_key")
        
        assert "test_key" in invalidated
        assert "test_key" in callback_called
    
    def test_remove_dependency(self):
        """Test dependency removal."""
        manager = CacheInvalidationManager()
        
        manager.add_dependency("child", "parent")
        assert "child" in manager.get_dependent_keys("parent")
        
        manager.remove_dependency("child", "parent")
        assert "child" not in manager.get_dependent_keys("parent")


class TestAdvancedCacheManager:
    """Test advanced cache manager."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield SQLiteStorage(str(Path(temp_dir) / "test.db"))
    
    @pytest.fixture
    def cache_manager(self, temp_storage):
        """Create cache manager for testing."""
        return AdvancedCacheManager(
            max_size_mb=1,  # Small size for testing eviction
            default_ttl_seconds=60,
            persistent_storage=temp_storage
        )
    
    def test_basic_cache_operations(self, cache_manager):
        """Test basic cache put/get operations."""
        # Test put and get
        assert cache_manager.put("test_key", "test_value")
        assert cache_manager.get("test_key") == "test_value"
        
        # Test miss
        assert cache_manager.get("nonexistent_key") is None
    
    def test_ttl_expiration(self, cache_manager):
        """Test TTL-based cache expiration."""
        # Put with short TTL
        cache_manager.put("short_ttl", "value", ttl_seconds=1)
        assert cache_manager.get("short_ttl") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache_manager.get("short_ttl") is None
    
    def test_lru_eviction(self, cache_manager):
        """Test LRU eviction when cache is full."""
        # Fill cache beyond capacity
        large_value = "x" * 100000  # 100KB
        
        for i in range(15):  # Should exceed 1MB limit
            cache_manager.put(f"key_{i}", large_value)
        
        # First keys should be evicted
        assert cache_manager.get("key_0") is None
        assert cache_manager.get("key_14") is not None
    
    def test_dependency_invalidation(self, cache_manager):
        """Test dependency-based cache invalidation."""
        # Put dependent entries
        cache_manager.put("parent", "parent_value")
        cache_manager.put("child", "child_value", dependencies=["parent"])
        
        # Verify both exist
        assert cache_manager.get("parent") == "parent_value"
        assert cache_manager.get("child") == "child_value"
        
        # Invalidate parent
        invalidated = cache_manager.invalidate("parent")
        
        # Both should be invalidated
        assert "parent" in invalidated
        assert "child" in invalidated
        assert cache_manager.get("parent") is None
        assert cache_manager.get("child") is None
    
    def test_pattern_invalidation(self, cache_manager):
        """Test pattern-based cache invalidation."""
        # Put entries with pattern
        cache_manager.put("user_123_profile", "profile_data")
        cache_manager.put("user_123_settings", "settings_data")
        cache_manager.put("user_456_profile", "other_profile")
        
        # Invalidate pattern
        invalidated = cache_manager.invalidate_pattern("user_123")
        
        # Only matching entries should be invalidated
        assert len(invalidated) == 2
        assert cache_manager.get("user_123_profile") is None
        assert cache_manager.get("user_123_settings") is None
        assert cache_manager.get("user_456_profile") == "other_profile"
    
    def test_cache_statistics(self, cache_manager):
        """Test cache statistics tracking."""
        # Generate some cache activity
        cache_manager.put("key1", "value1")
        cache_manager.put("key2", "value2")
        
        # Generate hits and misses
        cache_manager.get("key1")  # Hit
        cache_manager.get("key1")  # Hit
        cache_manager.get("nonexistent")  # Miss
        
        stats = cache_manager.get_statistics()
        assert stats.hit_count == 2
        assert stats.miss_count == 1
        assert stats.hit_rate == 2/3
    
    def test_persistent_storage_integration(self, cache_manager):
        """Test integration with persistent storage."""
        # Put value in cache
        cache_manager.put("persistent_key", "persistent_value")
        
        # Create new cache manager with same storage
        new_cache = AdvancedCacheManager(
            persistent_storage=cache_manager.persistent_storage
        )
        
        # Should load from persistent storage
        assert new_cache.get("persistent_key") == "persistent_value"


class TestSessionManager:
    """Test session manager."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield SQLiteStorage(str(Path(temp_dir) / "test.db"))
    
    @pytest.fixture
    def session_manager(self, temp_storage):
        """Create session manager for testing."""
        return SessionManager(
            max_sessions=5,  # Small limit for testing
            session_timeout_hours=1,  # Short timeout for testing
            persistent_storage=temp_storage
        )
    
    def test_session_creation(self, session_manager):
        """Test session creation."""
        session_id = session_manager.create_session()
        assert session_id is not None
        
        session = session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.status == SessionStatus.ACTIVE
    
    def test_session_with_preferences(self, session_manager):
        """Test session creation with initial preferences."""
        preferences = UserPreferences(theme="dark", max_results_per_page=100)
        session_id = session_manager.create_session(preferences)
        
        session = session_manager.get_session(session_id)
        assert session.user_preferences.theme == "dark"
        assert session.user_preferences.max_results_per_page == 100
    
    def test_session_updates(self, session_manager):
        """Test session state updates."""
        session_id = session_manager.create_session()
        
        # Update session
        updates = {
            "current_tab": "analytics",
            "selected_players": ["player1", "player2"]
        }
        assert session_manager.update_session(session_id, updates)
        
        # Verify updates
        session = session_manager.get_session(session_id)
        assert session.current_tab == "analytics"
        assert session.selected_players == ["player1", "player2"]
    
    def test_session_eviction(self, session_manager):
        """Test session eviction when limit is reached."""
        # Create sessions up to limit
        session_ids = []
        for i in range(5):
            session_id = session_manager.create_session()
            session_ids.append(session_id)
        
        # Create one more session (should evict oldest)
        new_session_id = session_manager.create_session()
        
        # First session should be evicted
        assert session_manager.get_session(session_ids[0]) is None
        assert session_manager.get_session(new_session_id) is not None
    
    def test_session_persistence(self, session_manager):
        """Test session persistence across manager instances."""
        # Create session
        session_id = session_manager.create_session()
        session_manager.update_session(session_id, {"current_tab": "test_tab"})
        
        # Create new session manager with same storage
        new_manager = SessionManager(
            persistent_storage=session_manager.persistent_storage
        )
        
        # Session should be loaded
        session = new_manager.get_session(session_id)
        assert session is not None
        assert session.current_tab == "test_tab"
    
    def test_session_statistics(self, session_manager):
        """Test session statistics."""
        # Create some sessions
        for i in range(3):
            session_manager.create_session()
        
        stats = session_manager.get_session_statistics()
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 3


class TestRealTimeSynchronizer:
    """Test real-time synchronizer."""
    
    @pytest.fixture
    def synchronizer(self):
        """Create synchronizer for testing."""
        return RealTimeSynchronizer()
    
    def test_event_subscription_and_emission(self, synchronizer):
        """Test event subscription and emission."""
        received_events = []
        
        def event_handler(event):
            received_events.append(event)
        
        # Subscribe to events
        subscription_id = synchronizer.subscribe("test_event", event_handler, weak=False)
        
        # Emit event
        test_data = {"message": "test"}
        synchronizer.emit("test_event", test_data, async_processing=False)
        
        # Verify event received
        assert len(received_events) == 1
        assert received_events[0]["type"] == "test_event"
        assert received_events[0]["data"] == test_data
    
    def test_multiple_subscribers(self, synchronizer):
        """Test multiple subscribers for same event."""
        received_counts = [0, 0]
        
        def handler1(event):
            received_counts[0] += 1
        
        def handler2(event):
            received_counts[1] += 1
        
        # Subscribe multiple handlers
        synchronizer.subscribe("multi_event", handler1, weak=False)
        synchronizer.subscribe("multi_event", handler2, weak=False)
        
        # Emit event
        synchronizer.emit("multi_event", {"data": "test"}, async_processing=False)
        
        # Both handlers should receive event
        assert received_counts[0] == 1
        assert received_counts[1] == 1
    
    def test_weak_reference_cleanup(self, synchronizer):
        """Test weak reference cleanup."""
        received_events = []
        
        class EventHandler:
            def __call__(self, event):
                received_events.append(event)
        
        # Create handler and subscribe with weak reference
        handler = EventHandler()
        synchronizer.subscribe("weak_event", handler, weak=True)
        
        # Emit event - should work
        synchronizer.emit("weak_event", {"data": "test1"}, async_processing=False)
        time.sleep(0.1)  # Allow async processing
        
        # Delete handler reference
        del handler
        
        # Emit another event - weak reference should be cleaned up
        synchronizer.emit("weak_event", {"data": "test2"}, async_processing=False)
        time.sleep(0.1)
        
        # Should only have received first event
        assert len(received_events) == 1
    
    def test_state_change_broadcast(self, synchronizer):
        """Test state change broadcasting."""
        received_changes = []
        
        def change_handler(event):
            received_changes.append(event)
        
        synchronizer.subscribe("state_change", change_handler, weak=False)
        
        # Broadcast state change
        synchronizer.broadcast_state_change("session1", "component1", "old", "new")
        time.sleep(0.1)  # Allow async processing
        
        # Verify broadcast
        assert len(received_changes) == 1
        change_data = received_changes[0]["data"]
        assert change_data["session_id"] == "session1"
        assert change_data["component_id"] == "component1"
        assert change_data["old_state"] == "old"
        assert change_data["new_state"] == "new"
    
    def test_operation_update_broadcast(self, synchronizer):
        """Test operation update broadcasting."""
        received_updates = []
        
        def update_handler(event):
            received_updates.append(event)
        
        synchronizer.subscribe("operation_update", update_handler, weak=False)
        
        # Create operation and broadcast update
        operation = OperationState(
            operation_id="op1",
            operation_type="test",
            status="running",
            progress_percentage=50.0
        )
        
        synchronizer.broadcast_operation_update("session1", operation)
        time.sleep(0.1)  # Allow async processing
        
        # Verify broadcast
        assert len(received_updates) == 1
        update_data = received_updates[0]["data"]
        assert update_data["session_id"] == "session1"
        assert update_data["operation"].operation_id == "op1"


class TestEnhancedStateManager:
    """Test enhanced state manager integration."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield SQLiteStorage(str(Path(temp_dir) / "test.db"))
    
    @pytest.fixture
    def state_manager(self, temp_storage):
        """Create enhanced state manager for testing."""
        return EnhancedStateManager(
            cache_size_mb=1,
            max_sessions=10,
            persistent_storage=temp_storage
        )
    
    def test_session_lifecycle(self, state_manager):
        """Test complete session lifecycle."""
        # Create session
        session_id = state_manager.create_session()
        assert session_id is not None
        
        # Get session
        session = state_manager.get_session(session_id)
        assert session is not None
        
        # Update session state
        assert state_manager.update_session_state(session_id, "current_tab", "analytics")
        
        # Verify update
        updated_session = state_manager.get_session(session_id)
        assert updated_session.current_tab == "analytics"
    
    def test_cache_integration(self, state_manager):
        """Test cache integration."""
        # Cache result
        test_data = {"key": "value", "number": 42}
        assert state_manager.cache_result("test_cache", test_data, ttl=60)
        
        # Retrieve cached result
        cached_data = state_manager.get_cached_result("test_cache")
        assert cached_data == test_data
        
        # Test cache invalidation
        invalidated = state_manager.invalidate_cache("test_")
        assert "test_cache" in invalidated
        assert state_manager.get_cached_result("test_cache") is None
    
    def test_user_preferences(self, state_manager):
        """Test user preferences management."""
        # Create session
        session_id = state_manager.create_session()
        
        # Save preferences
        preferences = UserPreferences(
            theme="dark",
            max_results_per_page=100,
            auto_refresh_interval=60
        )
        assert state_manager.save_user_preferences(session_id, preferences)
        
        # Retrieve preferences
        saved_preferences = state_manager.get_user_preferences(session_id)
        assert saved_preferences.theme == "dark"
        assert saved_preferences.max_results_per_page == 100
    
    def test_operation_management(self, state_manager):
        """Test operation state management."""
        # Create session
        session_id = state_manager.create_session()
        
        # Add operation
        operation = OperationState(
            operation_id="test_op",
            operation_type="extraction",
            status="running",
            progress_percentage=25.0
        )
        assert state_manager.add_operation(session_id, operation)
        
        # Update operation
        updates = {
            "progress_percentage": 75.0,
            "status_message": "Almost complete"
        }
        assert state_manager.update_operation(session_id, "test_op", updates)
        
        # Verify updates
        session = state_manager.get_session(session_id)
        updated_operation = session.operation_states["test_op"]
        assert updated_operation.progress_percentage == 75.0
        assert updated_operation.status_message == "Almost complete"
    
    def test_shareable_results(self, state_manager):
        """Test shareable results management."""
        # Create session
        session_id = state_manager.create_session()
        
        # Create shareable result
        result_data = {"analysis": "test_analysis", "charts": ["chart1", "chart2"]}
        result = state_manager.create_shareable_result(
            result_type="analytics",
            title="Test Analysis",
            description="Test analysis description",
            data=result_data,
            session_id=session_id,
            expiration_hours=24
        )
        
        assert result.result_id is not None
        assert result.title == "Test Analysis"
        
        # Retrieve shareable result
        retrieved_result = state_manager.get_shareable_result(result.result_id)
        assert retrieved_result is not None
        assert retrieved_result.data == result_data
        assert retrieved_result.access_count == 1  # Should increment on access
    
    def test_event_system(self, state_manager):
        """Test event subscription and emission."""
        received_events = []
        
        def event_handler(event):
            received_events.append(event)
        
        # Subscribe to events
        subscription_id = state_manager.subscribe_to_events("test_event", event_handler)
        
        # Emit event
        test_data = {"message": "integration_test"}
        state_manager.emit_event("test_event", test_data)
        
        # Allow async processing
        time.sleep(0.1)
        
        # Verify event received
        assert len(received_events) == 1
        assert received_events[0]["data"] == test_data
    
    def test_system_statistics(self, state_manager):
        """Test system statistics collection."""
        # Create some activity
        session_id = state_manager.create_session()
        state_manager.cache_result("stat_test", "test_data")
        
        # Get statistics
        stats = state_manager.get_system_statistics()
        
        # Verify statistics structure
        assert "cache" in stats
        assert "sessions" in stats
        assert "shared_results" in stats
        
        assert stats["sessions"]["total_sessions"] >= 1
        assert stats["cache"]["total_entries"] >= 1
    
    def test_concurrent_access(self, state_manager):
        """Test concurrent access to state manager."""
        results = []
        errors = []
        
        def worker_function(worker_id):
            try:
                # Create session
                session_id = state_manager.create_session()
                
                # Perform operations
                state_manager.update_session_state(session_id, "worker_id", worker_id)
                state_manager.cache_result(f"worker_{worker_id}", f"data_{worker_id}")
                
                # Verify operations
                session = state_manager.get_session(session_id)
                cached_data = state_manager.get_cached_result(f"worker_{worker_id}")
                
                results.append({
                    "worker_id": worker_id,
                    "session_id": session_id,
                    "session_worker_id": session.component_states.get("worker_id"),
                    "cached_data": cached_data
                })
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Run concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_function, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Verify each worker's data is correct
        for result in results:
            worker_id = result["worker_id"]
            assert result["session_worker_id"] == worker_id
            assert result["cached_data"] == f"data_{worker_id}"


class TestPersistentStorage:
    """Test persistent storage implementations."""
    
    def test_sqlite_storage(self):
        """Test SQLite storage implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = SQLiteStorage(str(Path(temp_dir) / "test.db"))
            
            # Test basic operations
            test_data = {"key": "value", "number": 42}
            assert storage.save("test_key", test_data)
            assert storage.exists("test_key")
            
            loaded_data = storage.load("test_key")
            assert loaded_data == test_data
            
            # Test key listing
            storage.save("another_key", "another_value")
            keys = storage.list_keys()
            assert "test_key" in keys
            assert "another_key" in keys
            
            # Test pattern matching
            pattern_keys = storage.list_keys("test")
            assert "test_key" in pattern_keys
            assert "another_key" not in pattern_keys
            
            # Test deletion
            assert storage.delete("test_key")
            assert not storage.exists("test_key")
    
    def test_file_storage(self):
        """Test file storage implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = FileStorage(temp_dir)
            
            # Test basic operations
            test_data = {"key": "value", "list": [1, 2, 3]}
            assert storage.save("test_key", test_data)
            assert storage.exists("test_key")
            
            loaded_data = storage.load("test_key")
            assert loaded_data == test_data
            
            # Test key listing
            storage.save("another_key", "another_value")
            keys = storage.list_keys()
            assert "test_key" in keys
            assert "another_key" in keys
            
            # Test deletion
            assert storage.delete("test_key")
            assert not storage.exists("test_key")


if __name__ == "__main__":
    pytest.main([__file__])