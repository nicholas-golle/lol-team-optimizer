"""
Enhanced State Manager for Gradio Web Interface

This module provides comprehensive state management including session handling,
advanced caching with multiple strategies, user preferences, and real-time
synchronization between components.
"""

import asyncio
import hashlib
import logging
import threading
import time
import weakref
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union, Set
from concurrent.futures import ThreadPoolExecutor
import uuid

from .web_state_models import (
    WebInterfaceState, UserPreferences, OperationState, CacheEntry,
    CacheStrategy, SessionStatus, CacheStatistics, ShareableResult,
    PersistentStorage, SQLiteStorage, FileStorage
)


class CacheInvalidationManager:
    """Manages cache invalidation strategies and dependencies."""
    
    def __init__(self):
        """Initialize cache invalidation manager."""
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.invalidation_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    def add_dependency(self, dependent_key: str, dependency_key: str) -> None:
        """Add dependency relationship between cache keys."""
        self.dependency_graph[dependent_key].add(dependency_key)
        self.reverse_dependencies[dependency_key].add(dependent_key)
    
    def remove_dependency(self, dependent_key: str, dependency_key: str) -> None:
        """Remove dependency relationship."""
        self.dependency_graph[dependent_key].discard(dependency_key)
        self.reverse_dependencies[dependency_key].discard(dependent_key)
    
    def get_dependent_keys(self, key: str) -> Set[str]:
        """Get all keys that depend on the given key."""
        dependents = set()
        to_process = [key]
        processed = set()
        
        while to_process:
            current_key = to_process.pop()
            if current_key in processed:
                continue
            processed.add(current_key)
            
            direct_dependents = self.reverse_dependencies.get(current_key, set())
            dependents.update(direct_dependents)
            to_process.extend(direct_dependents)
        
        return dependents
    
    def register_invalidation_callback(self,
 key: str, callback: Callable[[str], None]) -> None:
        """Register callback for cache invalidation events."""
        self.invalidation_callbacks[key].append(callback)
    
    def invalidate_key(self, key: str) -> Set[str]:
        """Invalidate key and all dependent keys."""
        all_invalidated = {key}
        dependent_keys = self.get_dependent_keys(key)
        all_invalidated.update(dependent_keys)
        
        # Call invalidation callbacks
        for invalidated_key in all_invalidated:
            callbacks = self.invalidation_callbacks.get(invalidated_key, [])
            for callback in callbacks:
                try:
                    callback(invalidated_key)
                except Exception as e:
                    self.logger.error(f"Error in invalidation callback for {invalidated_key}: {e}")
        
        return all_invalidated


class AdvancedCacheManager:
    """Advanced caching system with multiple strategies and persistence."""
    
    def __init__(self, 
                 max_size_mb: int = 100,
                 default_ttl_seconds: int = 3600,
                 persistent_storage: Optional[PersistentStorage] = None):
        """Initialize advanced cache manager."""
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order = OrderedDict()  # For LRU tracking
        self.persistent_storage = persistent_storage or SQLiteStorage()
        self.invalidation_manager = CacheInvalidationManager()
        self.statistics = CacheStatistics()
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired entries."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                self._cleanup_expired_entries()
            except Exception as e:
                self.logger.error(f"Error in cache cleanup loop: {e}")
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired cache entries."""
        with self._lock:
            expired_keys = []
            for key, entry in self.cache.items():
                if entry.is_expired:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key)
                self.statistics.eviction_count += 1
    
    def _remove_entry(self, key: str) -> None:
        """Remove cache entry and update statistics."""
        if key in self.cache:
            entry = self.cache[key]
            del self.cache[key]
            self.access_order.pop(key, None)
            self.statistics.total_entries -= 1
            self.statistics.total_size_bytes -= entry.size_bytes
    
    def _evict_lru_entries(self, required_space: int) -> None:
        """Evict least recently used entries to free space."""
        freed_space = 0
        while freed_space < required_space and self.access_order:
            lru_key = next(iter(self.access_order))
            entry = self.cache.get(lru_key)
            if entry:
                freed_space += entry.size_bytes
                self._remove_entry(lru_key)
                self.statistics.eviction_count += 1
    
    def _ensure_space(self, required_space: int) -> None:
        """Ensure sufficient cache space is available."""
        current_size = self.statistics.total_size_bytes
        if current_size + required_space > self.max_size_bytes:
            space_to_free = (current_size + required_space) - self.max_size_bytes
            self._evict_lru_entries(space_to_free)
    
    def put(self, 
            key: str, 
            value: Any, 
            ttl_seconds: Optional[int] = None,
            strategy: CacheStrategy = CacheStrategy.TTL,
            dependencies: Optional[List[str]] = None) -> bool:
        """Store value in cache with specified strategy."""
        start_time = time.time()
        
        try:
            with self._lock:
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                    dependencies=dependencies or [],
                    strategy=strategy
                )
                
                # Ensure sufficient space
                self._ensure_space(entry.size_bytes)
                
                # Store entry
                self.cache[key] = entry
                self.access_order[key] = True
                
                # Update statistics
                self.statistics.total_entries += 1
                self.statistics.total_size_bytes += entry.size_bytes
                
                # Set up dependencies
                if dependencies:
                    for dep_key in dependencies:
                        self.invalidation_manager.add_dependency(key, dep_key)
                
                # Persist if storage available
                if self.persistent_storage and strategy != CacheStrategy.MANUAL:
                    self.persistent_storage.save(f"cache_{key}", entry)
                
                access_time = (time.time() - start_time) * 1000
                self.statistics.average_access_time_ms = (
                    (self.statistics.average_access_time_ms + access_time) / 2
                )
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to cache value for key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        start_time = time.time()
        
        try:
            with self._lock:
                entry = self.cache.get(key)
                
                if entry is None:
                    # Try loading from persistent storage
                    if self.persistent_storage:
                        stored_entry = self.persistent_storage.load(f"cache_{key}")
                        if stored_entry and not stored_entry.is_expired:
                            self.cache[key] = stored_entry
                            entry = stored_entry
                
                if entry is None or entry.is_expired:
                    self.statistics.miss_count += 1
                    return None
                
                # Update access information
                entry.touch()
                self.access_order.move_to_end(key)
                
                self.statistics.hit_count += 1
                
                access_time = (time.time() - start_time) * 1000
                self.statistics.average_access_time_ms = (
                    (self.statistics.average_access_time_ms + access_time) / 2
                )
                
                return entry.value
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve cached value for key {key}: {e}")
            self.statistics.miss_count += 1
            return None
    
    def invalidate(self, key: str) -> Set[str]:
        """Invalidate cache entry and all dependents."""
        with self._lock:
            invalidated_keys = self.invalidation_manager.invalidate_key(key)
            
            for inv_key in invalidated_keys:
                self._remove_entry(inv_key)
                if self.persistent_storage:
                    self.persistent_storage.delete(f"cache_{inv_key}")
            
            return invalidated_keys
    
    def invalidate_pattern(self, pattern: str) -> Set[str]:
        """Invalidate all keys matching pattern."""
        with self._lock:
            matching_keys = [key for key in self.cache.keys() if pattern in key]
            invalidated_keys = set()
            
            for key in matching_keys:
                invalidated_keys.update(self.invalidate(key))
            
            return invalidated_keys
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.statistics = CacheStatistics()
            
            if self.persistent_storage:
                cache_keys = self.persistent_storage.list_keys("cache_")
                for key in cache_keys:
                    self.persistent_storage.delete(key)
    
    def get_statistics(self) -> CacheStatistics:
        """Get cache performance statistics."""
        return self.statistics
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._lock:
            return {
                "total_entries": len(self.cache),
                "total_size_mb": self.statistics.total_size_bytes / (1024 * 1024),
                "hit_rate": self.statistics.hit_rate,
                "average_access_time_ms": self.statistics.average_access_time_ms,
                "entries_by_strategy": {
                    strategy.value: sum(1 for entry in self.cache.values() 
                                      if entry.strategy == strategy)
                    for strategy in CacheStrategy
                }
            }


class SessionManager:
    """Manages user sessions with automatic cleanup and persistence."""
    
    def __init__(self, 
                 max_sessions: int = 1000,
                 session_timeout_hours: int = 24,
                 persistent_storage: Optional[PersistentStorage] = None):
        """Initialize session manager."""
        self.max_sessions = max_sessions
        self.session_timeout_hours = session_timeout_hours
        self.sessions: Dict[str, WebInterfaceState] = {}
        self.session_access_order = OrderedDict()
        self.persistent_storage = persistent_storage or SQLiteStorage()
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Event handlers
        self.session_created_handlers: List[Callable[[str], None]] = []
        self.session_expired_handlers: List[Callable[[str], None]] = []
        
        # Background cleanup
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # Load existing sessions
        self._load_sessions()
    
    def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired sessions."""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                self._cleanup_expired_sessions()
            except Exception as e:
                self.logger.error(f"Error in session cleanup loop: {e}")
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        with self._lock:
            expired_sessions = []
            cutoff_time = datetime.now() - timedelta(hours=self.session_timeout_hours)
            
            for session_id, session in self.sessions.items():
                if session.last_activity < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self._remove_session(session_id)
    
    def _remove_session(self, session_id: str) -> None:
        """Remove session and notify handlers."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.status = SessionStatus.EXPIRED
            
            # Persist final state
            if self.persistent_storage:
                self.persistent_storage.save(f"session_{session_id}", session)
            
            del self.sessions[session_id]
            self.session_access_order.pop(session_id, None)
            
            # Notify handlers
            for handler in self.session_expired_handlers:
                try:
                    handler(session_id)
                except Exception as e:
                    self.logger.error(f"Error in session expired handler: {e}")
            
            self.logger.info(f"Removed expired session: {session_id}")
    
    def _evict_oldest_sessions(self, count: int) -> None:
        """Evict oldest sessions to make room."""
        for _ in range(count):
            if self.session_access_order:
                oldest_session_id = next(iter(self.session_access_order))
                self._remove_session(oldest_session_id)
    
    def _load_sessions(self) -> None:
        """Load existing sessions from persistent storage."""
        if not self.persistent_storage:
            return
        
        try:
            session_keys = self.persistent_storage.list_keys("session_")
            for key in session_keys:
                session = self.persistent_storage.load(key)
                if session and not session.is_expired:
                    self.sessions[session.session_id] = session
                    self.session_access_order[session.session_id] = True
                    self.logger.info(f"Loaded session: {session.session_id}")
        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}")
    
    def create_session(self, initial_preferences: Optional[UserPreferences] = None) -> str:
        """Create new session."""
        with self._lock:
            # Ensure space for new session
            if len(self.sessions) >= self.max_sessions:
                self._evict_oldest_sessions(1)
            
            # Create session
            session_id = str(uuid.uuid4())
            now = datetime.now()
            
            session = WebInterfaceState(
                session_id=session_id,
                created_at=now,
                last_activity=now,
                user_preferences=initial_preferences or UserPreferences()
            )
            
            self.sessions[session_id] = session
            self.session_access_order[session_id] = True
            
            # Persist session
            if self.persistent_storage:
                self.persistent_storage.save(f"session_{session_id}", session)
            
            # Notify handlers
            for handler in self.session_created_handlers:
                try:
                    handler(session_id)
                except Exception as e:
                    self.logger.error(f"Error in session created handler: {e}")
            
            self.logger.info(f"Created new session: {session_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[WebInterfaceState]:
        """Get session by ID."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.update_activity()
                self.session_access_order.move_to_end(session_id)
                
                # Persist updated session
                if self.persistent_storage:
                    self.persistent_storage.save(f"session_{session_id}", session)
            
            return session
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session with new data."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
                else:
                    session.component_states[key] = value
            
            session.update_activity()
            
            # Persist updated session
            if self.persistent_storage:
                self.persistent_storage.save(f"session_{session_id}", session)
            
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.status = SessionStatus.TERMINATED
                
                del self.sessions[session_id]
                self.session_access_order.pop(session_id, None)
                
                # Remove from persistent storage
                if self.persistent_storage:
                    self.persistent_storage.delete(f"session_{session_id}")
                
                self.logger.info(f"Deleted session: {session_id}")
                return True
            
            return False
    
    def get_active_sessions(self) -> List[WebInterfaceState]:
        """Get all active sessions."""
        with self._lock:
            return [session for session in self.sessions.values() 
                   if session.status == SessionStatus.ACTIVE]
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            active_count = len([s for s in self.sessions.values() 
                              if s.status == SessionStatus.ACTIVE])
            idle_count = len([s for s in self.sessions.values() 
                            if s.status == SessionStatus.IDLE])
            
            return {
                "total_sessions": len(self.sessions),
                "active_sessions": active_count,
                "idle_sessions": idle_count,
                "average_idle_time_minutes": sum(
                    s.idle_time_seconds for s in self.sessions.values()
                ) / max(len(self.sessions), 1) / 60
            }


class RealTimeSynchronizer:
    """Manages real-time synchronization between components."""
    
    def __init__(self):
        """Initialize real-time synchronizer."""
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.event_queue: List[Dict[str, Any]] = []
        self.weak_refs: Dict[str, List[weakref.ref]] = defaultdict(list)
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Background event processing
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sync")
    
    def subscribe(self, event_type: str, callback: Callable, weak: bool = True) -> str:
        """Subscribe to events with optional weak reference."""
        subscription_id = str(uuid.uuid4())
        
        with self._lock:
            if weak:
                weak_callback = weakref.ref(callback)
                self.weak_refs[event_type].append(weak_callback)
            else:
                self.subscribers[event_type].append(callback)
        
        return subscription_id
    
    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """Unsubscribe from events."""
        with self._lock:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                return True
            return False
    
    def emit(self, event_type: str, data: Any, async_processing: bool = True) -> None:
        """Emit event to all subscribers."""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "id": str(uuid.uuid4())
        }
        
        if async_processing:
            self.executor.submit(self._process_event, event)
        else:
            self._process_event(event)
    
    def _process_event(self, event: Dict[str, Any]) -> None:
        """Process event and notify subscribers."""
        event_type = event["type"]
        
        with self._lock:
            # Process strong references
            callbacks = self.subscribers[event_type].copy()
            
            # Process weak references
            weak_callbacks = []
            for weak_ref in self.weak_refs[event_type]:
                callback = weak_ref()
                if callback is not None:
                    weak_callbacks.append(callback)
                else:
                    # Remove dead weak reference
                    self.weak_refs[event_type].remove(weak_ref)
        
        # Execute callbacks outside of lock
        all_callbacks = callbacks + weak_callbacks
        for callback in all_callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in event callback for {event_type}: {e}")
    
    def broadcast_state_change(self, session_id: str, component_id: str, 
                             old_state: Any, new_state: Any) -> None:
        """Broadcast state change event."""
        self.emit("state_change", {
            "session_id": session_id,
            "component_id": component_id,
            "old_state": old_state,
            "new_state": new_state
        })
    
    def broadcast_operation_update(self, session_id: str, operation: OperationState) -> None:
        """Broadcast operation status update."""
        self.emit("operation_update", {
            "session_id": session_id,
            "operation": operation
        })


class EnhancedStateManager:
    """Enhanced state manager with comprehensive features."""
    
    def __init__(self,
                 cache_size_mb: int = 100,
                 max_sessions: int = 1000,
                 persistent_storage: Optional[PersistentStorage] = None):
        """Initialize enhanced state manager."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        storage = persistent_storage or SQLiteStorage()
        self.cache_manager = AdvancedCacheManager(
            max_size_mb=cache_size_mb,
            persistent_storage=storage
        )
        self.session_manager = SessionManager(
            max_sessions=max_sessions,
            persistent_storage=storage
        )
        self.synchronizer = RealTimeSynchronizer()
        
        # Shared results storage
        self.shared_results: Dict[str, ShareableResult] = {}
        self._shared_results_lock = threading.Lock()
        
        self.logger.info("Enhanced state manager initialized")
    
    # Session Management Methods
    def create_session(self, preferences: Optional[UserPreferences] = None) -> str:
        """Create new session."""
        return self.session_manager.create_session(preferences)
    
    def get_session(self, session_id: str) -> Optional[WebInterfaceState]:
        """Get session state."""
        return self.session_manager.get_session(session_id)
    
    def update_session_state(self, session_id: str, key: str, value: Any) -> bool:
        """Update session state and broadcast changes."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return False
        
        old_value = getattr(session, key, None) if hasattr(session, key) else session.component_states.get(key)
        
        success = self.session_manager.update_session(session_id, {key: value})
        if success:
            self.synchronizer.broadcast_state_change(session_id, key, old_value, value)
        
        return success
    
    # Cache Management Methods
    def cache_result(self, key: str, result: Any, ttl: Optional[int] = None,
                    dependencies: Optional[List[str]] = None) -> bool:
        """Cache computation result."""
        return self.cache_manager.put(key, result, ttl, dependencies=dependencies)
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result."""
        return self.cache_manager.get(key)
    
    def invalidate_cache(self, pattern: Optional[str] = None) -> Set[str]:
        """Invalidate cache entries."""
        if pattern:
            return self.cache_manager.invalidate_pattern(pattern)
        else:
            self.cache_manager.clear()
            return set()
    
    # User Preferences Management
    def save_user_preferences(self, session_id: str, preferences: UserPreferences) -> bool:
        """Save user preferences."""
        session = self.session_manager.get_session(session_id)
        if session:
            session.user_preferences = preferences
            return self.session_manager.update_session(session_id, {"user_preferences": preferences})
        return False
    
    def get_user_preferences(self, session_id: str) -> Optional[UserPreferences]:
        """Get user preferences."""
        session = self.session_manager.get_session(session_id)
        return session.user_preferences if session else None
    
    # Operation State Management
    def add_operation(self, session_id: str, operation: OperationState) -> bool:
        """Add operation to session."""
        session = self.session_manager.get_session(session_id)
        if session:
            session.add_operation(operation)
            self.synchronizer.broadcast_operation_update(session_id, operation)
            return True
        return False
    
    def update_operation(self, session_id: str, operation_id: str, updates: Dict[str, Any]) -> bool:
        """Update operation state."""
        session = self.session_manager.get_session(session_id)
        if session and operation_id in session.operation_states:
            operation = session.operation_states[operation_id]
            for key, value in updates.items():
                if hasattr(operation, key):
                    setattr(operation, key, value)
            
            self.synchronizer.broadcast_operation_update(session_id, operation)
            return True
        return False
    
    # Shared Results Management
    def create_shareable_result(self, result_type: str, title: str, description: str,
                              data: Dict[str, Any], session_id: str,
                              expiration_hours: Optional[int] = None) -> ShareableResult:
        """Create shareable result."""
        result = ShareableResult(
            result_id=str(uuid.uuid4()),
            result_type=result_type,
            title=title,
            description=description,
            data=data,
            created_by_session=session_id
        )
        
        if expiration_hours:
            result.expiration_date = datetime.now() + timedelta(hours=expiration_hours)
        
        with self._shared_results_lock:
            self.shared_results[result.result_id] = result
        
        return result
    
    def get_shareable_result(self, result_id: str) -> Optional[ShareableResult]:
        """Get shareable result by ID."""
        with self._shared_results_lock:
            result = self.shared_results.get(result_id)
            if result and not result.is_expired:
                result.access_count += 1
                return result
            elif result and result.is_expired:
                del self.shared_results[result_id]
        return None
    
    # Event Subscription
    def subscribe_to_events(self, event_type: str, callback: Callable) -> str:
        """Subscribe to real-time events."""
        return self.synchronizer.subscribe(event_type, callback)
    
    def emit_event(self, event_type: str, data: Any) -> None:
        """Emit event to subscribers."""
        self.synchronizer.emit(event_type, data)
    
    # Statistics and Monitoring
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "cache": self.cache_manager.get_cache_info(),
            "sessions": self.session_manager.get_session_statistics(),
            "shared_results": {
                "total_results": len(self.shared_results),
                "active_results": len([r for r in self.shared_results.values() if not r.is_expired])
            }
        }
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """Manually trigger cleanup of expired data."""
        # Cleanup is handled by background threads, but this provides manual trigger
        with self._shared_results_lock:
            expired_results = [rid for rid, result in self.shared_results.items() if result.is_expired]
            for rid in expired_results:
                del self.shared_results[rid]
        
        return {
            "expired_shared_results": len(expired_results)
        }