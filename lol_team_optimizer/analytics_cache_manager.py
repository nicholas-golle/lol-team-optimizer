"""
Analytics Cache Manager for the League of Legends Team Optimizer.

This module provides multi-level caching for analytics operations to optimize
performance and reduce computation time for frequently accessed analytics.
"""

import json
import pickle
import hashlib
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import OrderedDict
import logging

from .config import Config
from .analytics_models import AnalyticsError


logger = logging.getLogger(__name__)


class CacheError(AnalyticsError):
    """Base exception for cache operations."""
    pass


class CacheKeyError(CacheError):
    """Raised when cache key is invalid."""
    pass


class CacheSerializationError(CacheError):
    """Raised when cache serialization/deserialization fails."""
    pass


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    
    def __post_init__(self):
        """Initialize cache entry."""
        if not self.key:
            raise CacheKeyError("Cache key cannot be empty")
        
        # Calculate approximate size
        try:
            if isinstance(self.data, (str, bytes)):
                self.size_bytes = len(self.data)
            else:
                # Rough estimate using pickle
                self.size_bytes = len(pickle.dumps(self.data))
        except Exception:
            self.size_bytes = 1024  # Default estimate
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    @property
    def age_seconds(self) -> int:
        """Get age of cache entry in seconds."""
        return int((datetime.now() - self.created_at).total_seconds())
    
    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStatistics:
    """Cache performance statistics."""
    
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0
    memory_cache_entries: int = 0
    memory_cache_size_bytes: int = 0
    persistent_cache_entries: int = 0
    persistent_cache_size_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate
    
    @property
    def average_entry_size(self) -> float:
        """Calculate average entry size in bytes."""
        if self.total_entries == 0:
            return 0.0
        return self.total_size_bytes / self.total_entries


class LRUCache:
    """Least Recently Used cache implementation."""
    
    def __init__(self, max_size: int = 1000, max_size_bytes: int = 50 * 1024 * 1024):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries
            max_size_bytes: Maximum total size in bytes
        """
        self.max_size = max_size
        self.max_size_bytes = max_size_bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._total_size_bytes = 0
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired:
                del self._cache[key]
                self._total_size_bytes -= entry.size_bytes
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            return entry
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put cache entry."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._total_size_bytes -= old_entry.size_bytes
                del self._cache[key]
            
            # Check if entry would exceed size limits
            if (entry.size_bytes > self.max_size_bytes or 
                len(self._cache) >= self.max_size):
                self._evict_entries()
            
            # Add new entry
            self._cache[key] = entry
            self._total_size_bytes += entry.size_bytes
            
            # Evict if necessary
            self._evict_entries()
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove cache entry by key."""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            self._total_size_bytes -= entry.size_bytes
            del self._cache[key]
            return True
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._total_size_bytes = 0
    
    def _evict_entries(self) -> int:
        """Evict entries to maintain size limits."""
        evicted_count = 0
        
        # Evict by count
        while len(self._cache) > self.max_size:
            key, entry = self._cache.popitem(last=False)  # Remove least recently used
            self._total_size_bytes -= entry.size_bytes
            evicted_count += 1
        
        # Evict by size
        while self._total_size_bytes > self.max_size_bytes and self._cache:
            key, entry = self._cache.popitem(last=False)
            self._total_size_bytes -= entry.size_bytes
            evicted_count += 1
        
        return evicted_count
    
    @property
    def size(self) -> int:
        """Get number of entries."""
        return len(self._cache)
    
    @property
    def size_bytes(self) -> int:
        """Get total size in bytes."""
        return self._total_size_bytes
    
    def get_keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())


class PersistentCache:
    """Persistent cache using file system."""
    
    def __init__(self, cache_directory: Path, max_size_bytes: int = 100 * 1024 * 1024):
        """Initialize persistent cache.
        
        Args:
            cache_directory: Directory for cache files
            max_size_bytes: Maximum total size in bytes
        """
        self.cache_directory = cache_directory
        self.max_size_bytes = max_size_bytes
        self._lock = threading.RLock()
        
        # Create cache directory
        self.cache_directory.mkdir(parents=True, exist_ok=True)
        
        # Create analytics subdirectory
        self.analytics_cache_dir = self.cache_directory / "analytics"
        self.analytics_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_file_path(self, key: str) -> Path:
        """Get cache file path for key."""
        # Create safe filename from key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.analytics_cache_dir / f"{safe_key}.cache"
    
    def _get_metadata_file_path(self, key: str) -> Path:
        """Get metadata file path for key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.analytics_cache_dir / f"{safe_key}.meta"
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            cache_file = self._get_cache_file_path(key)
            meta_file = self._get_metadata_file_path(key)
            
            if not cache_file.exists() or not meta_file.exists():
                return None
            
            try:
                # Load metadata
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check if expired
                created_at = datetime.fromisoformat(metadata['created_at'])
                ttl_seconds = metadata.get('ttl_seconds')
                
                if ttl_seconds is not None:
                    expiry_time = created_at + timedelta(seconds=ttl_seconds)
                    if datetime.now() > expiry_time:
                        # Remove expired files
                        cache_file.unlink(missing_ok=True)
                        meta_file.unlink(missing_ok=True)
                        return None
                
                # Load data
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                # Create cache entry
                entry = CacheEntry(
                    key=key,
                    data=data,
                    created_at=created_at,
                    last_accessed=datetime.fromisoformat(metadata['last_accessed']),
                    access_count=metadata['access_count'],
                    ttl_seconds=ttl_seconds,
                    size_bytes=metadata['size_bytes']
                )
                
                # Update access info
                entry.touch()
                self._update_metadata(key, entry)
                
                return entry
                
            except Exception as e:
                logger.warning(f"Failed to load cache entry {key}: {e}")
                # Clean up corrupted files
                cache_file.unlink(missing_ok=True)
                meta_file.unlink(missing_ok=True)
                return None
    
    def put(self, key: str, entry: CacheEntry) -> bool:
        """Put cache entry."""
        with self._lock:
            try:
                cache_file = self._get_cache_file_path(key)
                meta_file = self._get_metadata_file_path(key)
                
                # Remove existing entry if present to avoid double counting
                if cache_file.exists():
                    cache_file.unlink(missing_ok=True)
                if meta_file.exists():
                    meta_file.unlink(missing_ok=True)
                
                # Save data
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry.data, f)
                
                # Save metadata
                self._update_metadata(key, entry)
                
                # Clean up if necessary (do this after adding the new entry)
                self._cleanup_cache()
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to save cache entry {key}: {e}")
                return False
    
    def remove(self, key: str) -> bool:
        """Remove cache entry by key."""
        with self._lock:
            cache_file = self._get_cache_file_path(key)
            meta_file = self._get_metadata_file_path(key)
            
            removed = False
            if cache_file.exists():
                cache_file.unlink()
                removed = True
            
            if meta_file.exists():
                meta_file.unlink()
                removed = True
            
            return removed
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            for file_path in self.analytics_cache_dir.glob("*.cache"):
                file_path.unlink(missing_ok=True)
            
            for file_path in self.analytics_cache_dir.glob("*.meta"):
                file_path.unlink(missing_ok=True)
    
    def _update_metadata(self, key: str, entry: CacheEntry):
        """Update metadata file for cache entry."""
        meta_file = self._get_metadata_file_path(key)
        
        metadata = {
            'key': key,
            'created_at': entry.created_at.isoformat(),
            'last_accessed': entry.last_accessed.isoformat(),
            'access_count': entry.access_count,
            'ttl_seconds': entry.ttl_seconds,
            'size_bytes': entry.size_bytes
        }
        
        with open(meta_file, 'w') as f:
            json.dump(metadata, f)
    
    def _cleanup_cache(self):
        """Clean up cache to maintain size limits."""
        try:
            # Get all cache files with their sizes and access times
            cache_files = []
            total_size = 0
            
            for cache_file in self.analytics_cache_dir.glob("*.cache"):
                meta_file = cache_file.with_suffix(".meta")
                
                if meta_file.exists():
                    try:
                        with open(meta_file, 'r') as f:
                            metadata = json.load(f)
                        
                        size = metadata.get('size_bytes', cache_file.stat().st_size)
                        last_accessed = datetime.fromisoformat(metadata['last_accessed'])
                        
                        cache_files.append((cache_file, meta_file, size, last_accessed))
                        total_size += size
                        
                    except Exception:
                        # Remove corrupted files
                        cache_file.unlink(missing_ok=True)
                        meta_file.unlink(missing_ok=True)
                else:
                    # Remove orphaned cache files without metadata
                    cache_file.unlink(missing_ok=True)
            
            # Remove oldest files if over size limit
            if total_size > self.max_size_bytes:
                # Sort by last accessed time (oldest first)
                cache_files.sort(key=lambda x: x[3])
                
                for cache_file, meta_file, size, _ in cache_files:
                    if total_size <= self.max_size_bytes:
                        break
                    
                    try:
                        cache_file.unlink(missing_ok=True)
                        meta_file.unlink(missing_ok=True)
                        total_size -= size
                    except Exception:
                        # Continue cleanup even if individual file removal fails
                        pass
                    
        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")
    
    @property
    def size_bytes(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        
        for cache_file in self.analytics_cache_dir.glob("*.cache"):
            try:
                total_size += cache_file.stat().st_size
            except Exception:
                pass
        
        return total_size
    
    def get_keys(self) -> List[str]:
        """Get all cache keys."""
        keys = []
        
        for meta_file in self.analytics_cache_dir.glob("*.meta"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                keys.append(metadata['key'])
            except Exception:
                pass
        
        return keys


class AnalyticsCacheManager:
    """Multi-level cache manager for analytics operations."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize analytics cache manager.
        
        Args:
            config: Application configuration
        """
        if config is None:
            from .config import get_config
            config = get_config()
        
        self.config = config
        
        # Initialize caches
        cache_dir = Path(config.cache_directory)
        
        # Memory cache for frequently accessed data
        self.memory_cache = LRUCache(
            max_size=1000,
            max_size_bytes=config.max_cache_size_mb * 1024 * 1024 // 2  # Half for memory
        )
        
        # Persistent cache for expensive calculations
        self.persistent_cache = PersistentCache(
            cache_directory=cache_dir,
            max_size_bytes=config.max_cache_size_mb * 1024 * 1024  # Full size for persistent
        )
        
        # Cache statistics
        self.stats = CacheStatistics()
        self._lock = threading.RLock()
        
        # Default TTL values (in seconds)
        self.default_memory_ttl = 3600  # 1 hour
        self.default_persistent_ttl = 86400  # 24 hours
        
        logger.info(f"Analytics cache manager initialized with cache directory: {cache_dir}")
    
    def get_cached_analytics(self, cache_key: str) -> Optional[Any]:
        """Get cached analytics data.
        
        Args:
            cache_key: Unique cache key
            
        Returns:
            Cached data if found, None otherwise
        """
        with self._lock:
            self.stats.total_requests += 1
            
            # Try memory cache first
            entry = self.memory_cache.get(cache_key)
            if entry is not None:
                self.stats.cache_hits += 1
                logger.debug(f"Memory cache hit for key: {cache_key}")
                return entry.data
            
            # Try persistent cache
            entry = self.persistent_cache.get(cache_key)
            if entry is not None:
                self.stats.cache_hits += 1
                logger.debug(f"Persistent cache hit for key: {cache_key}")
                
                # Promote to memory cache if frequently accessed
                if entry.access_count >= 3:
                    memory_entry = CacheEntry(
                        key=cache_key,
                        data=entry.data,
                        created_at=entry.created_at,
                        last_accessed=entry.last_accessed,
                        access_count=entry.access_count,
                        ttl_seconds=self.default_memory_ttl,
                        size_bytes=entry.size_bytes
                    )
                    self.memory_cache.put(cache_key, memory_entry)
                
                return entry.data
            
            # Cache miss
            self.stats.cache_misses += 1
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
    
    def cache_analytics(self, cache_key: str, data: Any, ttl: Optional[int] = None, 
                       persistent: bool = True) -> None:
        """Cache analytics data.
        
        Args:
            cache_key: Unique cache key
            data: Data to cache
            ttl: Time to live in seconds (None for default)
            persistent: Whether to store in persistent cache
        """
        if not cache_key:
            raise CacheKeyError("Cache key cannot be empty")
        
        with self._lock:
            now = datetime.now()
            
            # Determine TTL
            if ttl is None:
                ttl = self.default_persistent_ttl if persistent else self.default_memory_ttl
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                data=data,
                created_at=now,
                last_accessed=now,
                access_count=1,
                ttl_seconds=ttl
            )
            
            # Store in memory cache
            self.memory_cache.put(cache_key, entry)
            
            # Store in persistent cache if requested
            if persistent:
                persistent_entry = CacheEntry(
                    key=cache_key,
                    data=data,
                    created_at=now,
                    last_accessed=now,
                    access_count=1,
                    ttl_seconds=ttl
                )
                self.persistent_cache.put(cache_key, persistent_entry)
            
            logger.debug(f"Cached data for key: {cache_key} (persistent: {persistent})")
    
    def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern.
        
        Args:
            pattern: Pattern to match cache keys (supports wildcards)
            
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            invalidated_count = 0
            
            # Get all keys from both caches
            memory_keys = self.memory_cache.get_keys()
            persistent_keys = self.persistent_cache.get_keys()
            all_keys = set(memory_keys + persistent_keys)
            
            # Simple pattern matching (supports * wildcard)
            import fnmatch
            
            for key in all_keys:
                if fnmatch.fnmatch(key, pattern):
                    # Remove from memory cache
                    if self.memory_cache.remove(key):
                        invalidated_count += 1
                    
                    # Remove from persistent cache
                    if self.persistent_cache.remove(key):
                        invalidated_count += 1
            
            logger.info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
            return invalidated_count
    
    def clear_cache(self, memory_only: bool = False) -> None:
        """Clear all cache entries.
        
        Args:
            memory_only: If True, only clear memory cache
        """
        with self._lock:
            self.memory_cache.clear()
            
            if not memory_only:
                self.persistent_cache.clear()
            
            logger.info(f"Cache cleared (memory_only: {memory_only})")
    
    def get_cache_statistics(self) -> CacheStatistics:
        """Get cache performance statistics.
        
        Returns:
            Cache statistics
        """
        with self._lock:
            # Update current statistics
            self.stats.total_entries = self.memory_cache.size + len(self.persistent_cache.get_keys())
            self.stats.total_size_bytes = self.memory_cache.size_bytes + self.persistent_cache.size_bytes
            self.stats.memory_cache_entries = self.memory_cache.size
            self.stats.memory_cache_size_bytes = self.memory_cache.size_bytes
            self.stats.persistent_cache_entries = len(self.persistent_cache.get_keys())
            self.stats.persistent_cache_size_bytes = self.persistent_cache.size_bytes
            
            return self.stats
    
    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters.
        
        Args:
            prefix: Key prefix
            **kwargs: Parameters to include in key
            
        Returns:
            Generated cache key
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        
        # Create parameter string
        param_parts = []
        for key, value in sorted_params:
            if value is not None:
                if isinstance(value, (list, tuple)):
                    value_str = ",".join(str(v) for v in sorted(value))
                elif isinstance(value, dict):
                    value_str = ",".join(f"{k}:{v}" for k, v in sorted(value.items()))
                else:
                    value_str = str(value)
                param_parts.append(f"{key}={value_str}")
        
        param_string = "|".join(param_parts)
        
        # Generate hash for long parameter strings
        if len(param_string) > 200:
            param_hash = hashlib.md5(param_string.encode()).hexdigest()
            return f"{prefix}:{param_hash}"
        else:
            return f"{prefix}:{param_string}"
    
    def cache_analytics_result(self, func_name: str, result: Any, **params) -> str:
        """Cache analytics function result.
        
        Args:
            func_name: Name of the analytics function
            result: Function result to cache
            **params: Function parameters
            
        Returns:
            Cache key used
        """
        cache_key = self.generate_cache_key(func_name, **params)
        
        # Determine if result should be cached persistently
        # Large or expensive calculations should be persistent
        persistent = self._should_cache_persistently(func_name, result)
        
        self.cache_analytics(cache_key, result, persistent=persistent)
        return cache_key
    
    def get_cached_analytics_result(self, func_name: str, **params) -> Optional[Any]:
        """Get cached analytics function result.
        
        Args:
            func_name: Name of the analytics function
            **params: Function parameters
            
        Returns:
            Cached result if found, None otherwise
        """
        cache_key = self.generate_cache_key(func_name, **params)
        return self.get_cached_analytics(cache_key)
    
    def _should_cache_persistently(self, func_name: str, result: Any) -> bool:
        """Determine if result should be cached persistently.
        
        Args:
            func_name: Name of the analytics function
            result: Function result
            
        Returns:
            True if should be cached persistently
        """
        # Functions that should always be cached persistently
        persistent_functions = {
            'analyze_player_performance',
            'analyze_champion_performance',
            'analyze_team_composition',
            'calculate_performance_trends',
            'generate_comparative_analysis',
            'calculate_player_baseline',
            'get_champion_recommendations',
            'analyze_composition_performance'
        }
        
        if func_name in persistent_functions:
            return True
        
        # Large results should be cached persistently
        try:
            result_size = len(pickle.dumps(result))
            if result_size > 10 * 1024:  # 10KB threshold
                return True
        except Exception:
            pass
        
        return False
    
    def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        with self._lock:
            cleaned_count = 0
            
            # Memory cache cleanup is handled automatically by LRU eviction
            # Just trigger a cleanup for persistent cache
            try:
                self.persistent_cache._cleanup_cache()
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to cleanup persistent cache: {e}")
            
            return cleaned_count