"""
Web Interface State Management Models

This module provides comprehensive state management models for the Gradio web interface,
including session state, caching, user preferences, and real-time synchronization.
"""

import json
import pickle
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from abc import ABC, abstractmethod
import logging


class CacheStrategy(Enum):
    """Cache invalidation strategies."""
    TTL = "ttl"  # Time-to-live
    LRU = "lru"  # Least recently used
    MANUAL = "manual"  # Manual invalidation only
    DEPENDENCY = "dependency"  # Dependency-based invalidation


class SessionStatus(Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    TERMINATED = "terminated"


@dataclass
class CacheEntry:
    """Represents a cached data entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    dependencies: List[str] = field(default_factory=list)
    size_bytes: int = 0
    strategy: CacheStrategy = CacheStrategy.TTL
    
    def __post_init__(self):
        """Calculate size after initialization."""
        try:
            self.size_bytes = len(pickle.dumps(self.value))
        except Exception:
            self.size_bytes = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def touch(self) -> None:
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class UserPreferences:
    """User preferences for the web interface."""
    theme: str = "soft"
    default_chart_type: str = "radar"
    auto_refresh_interval: int = 30  # seconds
    max_results_per_page: int = 50
    preferred_date_range: int = 60  # days
    show_advanced_options: bool = False
    notification_settings: Dict[str, bool] = field(default_factory=lambda: {
        "extraction_complete": True,
        "analysis_ready": True,
        "errors": True,
        "warnings": False
    })
    dashboard_layout: Dict[str, Any] = field(default_factory=dict)
    saved_filters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    export_preferences: Dict[str, str] = field(default_factory=lambda: {
        "format": "pdf",
        "include_charts": "true",
        "include_raw_data": "false"
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary."""
        return cls(**data)


@dataclass
class OperationState:
    """State tracking for long-running operations."""
    operation_id: str
    operation_type: str
    status: str  # "pending", "running", "completed", "failed", "cancelled"
    progress_percentage: float = 0.0
    status_message: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    cancellable: bool = True
    result_data: Optional[Any] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_running(self) -> bool:
        """Check if operation is currently running."""
        return self.status in ["pending", "running"]
    
    @property
    def is_completed(self) -> bool:
        """Check if operation is completed (success or failure)."""
        return self.status in ["completed", "failed", "cancelled"]
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class WebInterfaceState:
    """Comprehensive state management for web interface sessions."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    current_tab: str = "player_management"
    selected_players: List[str] = field(default_factory=list)
    active_filters: Dict[str, Any] = field(default_factory=dict)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    operation_states: Dict[str, OperationState] = field(default_factory=dict)
    component_states: Dict[str, Any] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    event_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize session after creation."""
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
        if self.status == SessionStatus.IDLE:
            self.status = SessionStatus.ACTIVE
    
    def add_operation(self, operation: OperationState) -> None:
        """Add operation to session state."""
        self.operation_states[operation.operation_id] = operation
        self.update_activity()
    
    def get_active_operations(self) -> List[OperationState]:
        """Get all active operations."""
        return [op for op in self.operation_states.values() if op.is_running]
    
    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add event to history."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.event_history.append(event)
        
        # Keep only last 100 events
        if len(self.event_history) > 100:
            self.event_history = self.event_history[-100:]
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired (inactive for more than 24 hours)."""
        return datetime.now() > self.last_activity + timedelta(hours=24)
    
    @property
    def idle_time_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()


class PersistentStorage(ABC):
    """Abstract base class for persistent storage backends."""
    
    @abstractmethod
    def save(self, key: str, data: Any) -> bool:
        """Save data to persistent storage."""
        pass
    
    @abstractmethod
    def load(self, key: str) -> Optional[Any]:
        """Load data from persistent storage."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from persistent storage."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        pass
    
    @abstractmethod
    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys matching pattern."""
        pass


class SQLiteStorage(PersistentStorage):
    """SQLite-based persistent storage implementation."""
    
    def __init__(self, db_path: str = "web_interface_state.db"):
        """Initialize SQLite storage."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS storage (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_storage_key ON storage(key)
            """)
            conn.commit()
        finally:
            if conn:
                conn.close()
    
    def save(self, key: str, data: Any) -> bool:
        """Save data to SQLite storage."""
        conn = None
        try:
            with self._lock:
                serialized_data = pickle.dumps(data)
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO storage (key, data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, serialized_data))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to save data for key {key}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def load(self, key: str) -> Optional[Any]:
        """Load data from SQLite storage."""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("SELECT data FROM storage WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return pickle.loads(row[0])
                return None
        except Exception as e:
            logging.error(f"Failed to load data for key {key}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def delete(self, key: str) -> bool:
        """Delete data from SQLite storage."""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("DELETE FROM storage WHERE key = ?", (key,))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Failed to delete data for key {key}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in SQLite storage."""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("SELECT 1 FROM storage WHERE key = ? LIMIT 1", (key,))
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Failed to check existence for key {key}: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys matching pattern."""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path)
                if pattern:
                    cursor = conn.execute("SELECT key FROM storage WHERE key LIKE ?", (f"%{pattern}%",))
                else:
                    cursor = conn.execute("SELECT key FROM storage")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Failed to list keys with pattern {pattern}: {e}")
            return []
        finally:
            if conn:
                conn.close()


class FileStorage(PersistentStorage):
    """File-based persistent storage implementation."""
    
    def __init__(self, storage_dir: str = "web_interface_storage"):
        """Initialize file storage."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        # Replace invalid filename characters
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.storage_dir / f"{safe_key}.pkl"
    
    def save(self, key: str, data: Any) -> bool:
        """Save data to file storage."""
        try:
            with self._lock:
                file_path = self._get_file_path(key)
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f)
                return True
        except Exception as e:
            logging.error(f"Failed to save data for key {key}: {e}")
            return False
    
    def load(self, key: str) -> Optional[Any]:
        """Load data from file storage."""
        try:
            with self._lock:
                file_path = self._get_file_path(key)
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        return pickle.load(f)
                return None
        except Exception as e:
            logging.error(f"Failed to load data for key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete data from file storage."""
        try:
            with self._lock:
                file_path = self._get_file_path(key)
                if file_path.exists():
                    file_path.unlink()
                return True
        except Exception as e:
            logging.error(f"Failed to delete data for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in file storage."""
        try:
            file_path = self._get_file_path(key)
            return file_path.exists()
        except Exception as e:
            logging.error(f"Failed to check existence for key {key}: {e}")
            return False
    
    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """List all keys matching pattern."""
        try:
            keys = []
            for file_path in self.storage_dir.glob("*.pkl"):
                key = file_path.stem
                if pattern is None or pattern in key:
                    keys.append(key)
            return keys
        except Exception as e:
            logging.error(f"Failed to list keys with pattern {pattern}: {e}")
            return []


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    average_access_time_ms: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hit_count + self.miss_count
        return self.hit_count / max(total_requests, 1)
    
    @property
    def average_entry_size_bytes(self) -> float:
        """Calculate average entry size."""
        return self.total_size_bytes / max(self.total_entries, 1)


@dataclass
class ShareableResult:
    """Shareable analysis results with metadata."""
    result_id: str
    result_type: str
    title: str
    description: str
    data: Dict[str, Any]
    visualizations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    created_by_session: str = ""
    share_url: Optional[str] = None
    expiration_date: Optional[datetime] = None
    access_count: int = 0
    is_public: bool = False
    
    def __post_init__(self):
        """Initialize result after creation."""
        if not self.result_id:
            self.result_id = str(uuid.uuid4())
    
    @property
    def is_expired(self) -> bool:
        """Check if result is expired."""
        if self.expiration_date is None:
            return False
        return datetime.now() > self.expiration_date
    
    def generate_share_url(self, base_url: str) -> str:
        """Generate shareable URL."""
        self.share_url = f"{base_url}/shared/{self.result_id}"
        return self.share_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)