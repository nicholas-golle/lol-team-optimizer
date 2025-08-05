"""
Tests for the Analytics Cache Manager.

This module contains comprehensive tests for the multi-level caching system
used to optimize analytics operations performance.
"""

import pytest
import tempfile
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from lol_team_optimizer.analytics_cache_manager import (
    AnalyticsCacheManager,
    CacheEntry,
    CacheStatistics,
    LRUCache,
    PersistentCache,
    CacheError,
    CacheKeyError,
    CacheSerializationError
)
from lol_team_optimizer.config import Config
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics,
    PerformanceMetrics,
    DateRange,
    ChampionPerformanceMetrics
)


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and validation."""
        now = datetime.now()
        entry = CacheEntry(
            key="test_key",
            data={"test": "data"},
            created_at=now,
            last_accessed=now,
            ttl_seconds=3600
        )
        
        assert entry.key == "test_key"
        assert entry.data == {"test": "data"}
        assert entry.created_at == now
        assert entry.last_accessed == now
        assert entry.ttl_seconds == 3600
        assert entry.access_count == 0
        assert entry.size_bytes > 0
    
    def test_cache_entry_empty_key(self):
        """Test cache entry with empty key raises error."""
        with pytest.raises(CacheKeyError):
            CacheEntry(
                key="",
                data={"test": "data"},
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        now = datetime.now()
        
        # Non-expiring entry
        entry1 = CacheEntry(
            key="test1",
            data={"test": "data"},
            created_at=now,
            last_accessed=now,
            ttl_seconds=None
        )
        assert not entry1.is_expired
        
        # Expired entry
        entry2 = CacheEntry(
            key="test2",
            data={"test": "data"},
            created_at=now - timedelta(seconds=3600),
            last_accessed=now - timedelta(seconds=3600),
            ttl_seconds=1800  # 30 minutes
        )
        assert entry2.is_expired
        
        # Non-expired entry
        entry3 = CacheEntry(
            key="test3",
            data={"test": "data"},
            created_at=now,
            last_accessed=now,
            ttl_seconds=3600  # 1 hour
        )
        assert not entry3.is_expired
    
    def test_cache_entry_touch(self):
        """Test cache entry touch functionality."""
        now = datetime.now()
        entry = CacheEntry(
            key="test",
            data={"test": "data"},
            created_at=now,
            last_accessed=now
        )
        
        original_access_count = entry.access_count
        original_last_accessed = entry.last_accessed
        
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        assert entry.access_count == original_access_count + 1
        assert entry.last_accessed > original_last_accessed
    
    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        past_time = datetime.now() - timedelta(seconds=60)
        entry = CacheEntry(
            key="test",
            data={"test": "data"},
            created_at=past_time,
            last_accessed=past_time
        )
        
        assert entry.age_seconds >= 60


class TestLRUCache:
    """Test LRU Cache functionality."""
    
    def test_lru_cache_basic_operations(self):
        """Test basic LRU cache operations."""
        cache = LRUCache(max_size=3, max_size_bytes=1024)
        
        # Test put and get
        entry1 = CacheEntry("key1", "data1", datetime.now(), datetime.now())
        cache.put("key1", entry1)
        
        retrieved = cache.get("key1")
        assert retrieved is not None
        assert retrieved.data == "data1"
        
        # Test non-existent key
        assert cache.get("nonexistent") is None
        
        # Test size
        assert cache.size == 1
    
    def test_lru_cache_eviction_by_count(self):
        """Test LRU cache eviction by entry count."""
        cache = LRUCache(max_size=2, max_size_bytes=1024 * 1024)
        
        # Add entries up to limit
        entry1 = CacheEntry("key1", "data1", datetime.now(), datetime.now())
        entry2 = CacheEntry("key2", "data2", datetime.now(), datetime.now())
        entry3 = CacheEntry("key3", "data3", datetime.now(), datetime.now())
        
        cache.put("key1", entry1)
        cache.put("key2", entry2)
        assert cache.size == 2
        
        # Add third entry, should evict first
        cache.put("key3", entry3)
        assert cache.size == 2
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
    
    def test_lru_cache_eviction_by_size(self):
        """Test LRU cache eviction by total size."""
        cache = LRUCache(max_size=100, max_size_bytes=100)
        
        # Create large entries
        large_data = "x" * 60
        entry1 = CacheEntry("key1", large_data, datetime.now(), datetime.now())
        entry2 = CacheEntry("key2", large_data, datetime.now(), datetime.now())
        
        cache.put("key1", entry1)
        assert cache.size == 1
        
        # Adding second large entry should evict first
        cache.put("key2", entry2)
        assert cache.get("key1") is None  # Evicted due to size
        assert cache.get("key2") is not None
    
    def test_lru_cache_access_order(self):
        """Test LRU cache maintains access order."""
        cache = LRUCache(max_size=2, max_size_bytes=1024)
        
        entry1 = CacheEntry("key1", "data1", datetime.now(), datetime.now())
        entry2 = CacheEntry("key2", "data2", datetime.now(), datetime.now())
        entry3 = CacheEntry("key3", "data3", datetime.now(), datetime.now())
        
        cache.put("key1", entry1)
        cache.put("key2", entry2)
        
        # Access key1 to make it most recently used
        cache.get("key1")
        
        # Add key3, should evict key2 (least recently used)
        cache.put("key3", entry3)
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None
    
    def test_lru_cache_expired_entries(self):
        """Test LRU cache handles expired entries."""
        cache = LRUCache(max_size=10, max_size_bytes=1024)
        
        # Create expired entry
        past_time = datetime.now() - timedelta(seconds=3600)
        expired_entry = CacheEntry(
            "expired_key",
            "expired_data",
            past_time,
            past_time,
            ttl_seconds=1800  # 30 minutes
        )
        
        cache.put("expired_key", expired_entry)
        
        # Should return None for expired entry
        assert cache.get("expired_key") is None
        assert cache.size == 0  # Entry should be removed
    
    def test_lru_cache_remove(self):
        """Test LRU cache remove functionality."""
        cache = LRUCache(max_size=10, max_size_bytes=1024)
        
        entry = CacheEntry("key1", "data1", datetime.now(), datetime.now())
        cache.put("key1", entry)
        
        assert cache.get("key1") is not None
        assert cache.remove("key1") is True
        assert cache.get("key1") is None
        assert cache.remove("nonexistent") is False
    
    def test_lru_cache_clear(self):
        """Test LRU cache clear functionality."""
        cache = LRUCache(max_size=10, max_size_bytes=1024)
        
        entry1 = CacheEntry("key1", "data1", datetime.now(), datetime.now())
        entry2 = CacheEntry("key2", "data2", datetime.now(), datetime.now())
        
        cache.put("key1", entry1)
        cache.put("key2", entry2)
        
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_lru_cache_thread_safety(self):
        """Test LRU cache thread safety."""
        cache = LRUCache(max_size=100, max_size_bytes=1024 * 1024)
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                entry = CacheEntry(key, f"data_{i}", datetime.now(), datetime.now())
                cache.put(key, entry)
                
                retrieved = cache.get(key)
                results.append(retrieved is not None)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert all(results)


class TestPersistentCache:
    """Test Persistent Cache functionality."""
    
    def test_persistent_cache_basic_operations(self):
        """Test basic persistent cache operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            
            # Test put and get
            entry = CacheEntry("test_key", {"test": "data"}, datetime.now(), datetime.now())
            assert cache.put("test_key", entry) is True
            
            retrieved = cache.get("test_key")
            assert retrieved is not None
            assert retrieved.data == {"test": "data"}
            assert retrieved.key == "test_key"
            
            # Test non-existent key
            assert cache.get("nonexistent") is None
    
    def test_persistent_cache_persistence(self):
        """Test persistent cache data persistence."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            
            # Create cache and add entry
            cache1 = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            entry = CacheEntry("persistent_key", {"persistent": "data"}, datetime.now(), datetime.now())
            cache1.put("persistent_key", entry)
            
            # Create new cache instance with same directory
            cache2 = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            retrieved = cache2.get("persistent_key")
            
            assert retrieved is not None
            assert retrieved.data == {"persistent": "data"}
    
    def test_persistent_cache_expired_entries(self):
        """Test persistent cache handles expired entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            
            # Create expired entry
            past_time = datetime.now() - timedelta(seconds=3600)
            expired_entry = CacheEntry(
                "expired_key",
                {"expired": "data"},
                past_time,
                past_time,
                ttl_seconds=1800  # 30 minutes
            )
            
            cache.put("expired_key", expired_entry)
            
            # Should return None for expired entry and clean up files
            assert cache.get("expired_key") is None
    
    def test_persistent_cache_corrupted_files(self):
        """Test persistent cache handles corrupted files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            
            # Create corrupted cache file
            analytics_dir = cache_dir / "analytics"
            analytics_dir.mkdir(parents=True, exist_ok=True)
            
            corrupted_file = analytics_dir / "corrupted.cache"
            corrupted_file.write_text("corrupted data")
            
            meta_file = analytics_dir / "corrupted.meta"
            meta_file.write_text("corrupted metadata")
            
            # Should handle corrupted files gracefully
            assert cache.get("corrupted") is None
    
    def test_persistent_cache_remove(self):
        """Test persistent cache remove functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            
            entry = CacheEntry("remove_key", {"remove": "data"}, datetime.now(), datetime.now())
            cache.put("remove_key", entry)
            
            assert cache.get("remove_key") is not None
            assert cache.remove("remove_key") is True
            assert cache.get("remove_key") is None
            assert cache.remove("nonexistent") is False
    
    def test_persistent_cache_clear(self):
        """Test persistent cache clear functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1024 * 1024)
            
            entry1 = CacheEntry("key1", {"data": "1"}, datetime.now(), datetime.now())
            entry2 = CacheEntry("key2", {"data": "2"}, datetime.now(), datetime.now())
            
            cache.put("key1", entry1)
            cache.put("key2", entry2)
            
            assert cache.get("key1") is not None
            assert cache.get("key2") is not None
            
            cache.clear()
            
            assert cache.get("key1") is None
            assert cache.get("key2") is None
    
    def test_persistent_cache_size_cleanup(self):
        """Test persistent cache size-based cleanup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = PersistentCache(cache_dir, max_size_bytes=1000)  # Small limit
            
            # Add entries that exceed size limit
            large_data = "x" * 400  # Smaller data to account for metadata overhead
            for i in range(5):
                entry = CacheEntry(f"key_{i}", large_data, datetime.now(), datetime.now())
                cache.put(f"key_{i}", entry)
            
            # Cache should clean up old entries (allow some overhead for metadata)
            total_size = cache.size_bytes
            assert total_size <= 1200  # Allow some overhead for metadata and file system


class TestAnalyticsCacheManager:
    """Test Analytics Cache Manager functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            cache_directory=self.temp_dir,
            max_cache_size_mb=1
        )
        self.cache_manager = AnalyticsCacheManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        assert self.cache_manager.config == self.config
        assert self.cache_manager.memory_cache is not None
        assert self.cache_manager.persistent_cache is not None
        assert isinstance(self.cache_manager.stats, CacheStatistics)
    
    def test_cache_manager_basic_operations(self):
        """Test basic cache manager operations."""
        # Test caching and retrieval
        test_data = {"test": "analytics_data", "value": 42}
        self.cache_manager.cache_analytics("test_key", test_data)
        
        retrieved = self.cache_manager.get_cached_analytics("test_key")
        assert retrieved == test_data
        
        # Test cache miss
        assert self.cache_manager.get_cached_analytics("nonexistent") is None
    
    def test_cache_manager_memory_and_persistent(self):
        """Test memory and persistent cache interaction."""
        test_data = {"large": "analytics_data" * 100}
        
        # Cache with persistent=True
        self.cache_manager.cache_analytics("persistent_key", test_data, persistent=True)
        
        # Should be in both caches
        assert self.cache_manager.get_cached_analytics("persistent_key") == test_data
        
        # Clear memory cache
        self.cache_manager.memory_cache.clear()
        
        # Should still be available from persistent cache
        assert self.cache_manager.get_cached_analytics("persistent_key") == test_data
    
    def test_cache_manager_promotion(self):
        """Test cache promotion from persistent to memory."""
        test_data = {"promotion": "test_data"}
        
        # Add to persistent cache with high access count
        entry = CacheEntry(
            "promotion_key",
            test_data,
            datetime.now(),
            datetime.now(),
            access_count=5  # High access count
        )
        self.cache_manager.persistent_cache.put("promotion_key", entry)
        
        # Clear memory cache
        self.cache_manager.memory_cache.clear()
        
        # Access should promote to memory cache
        retrieved = self.cache_manager.get_cached_analytics("promotion_key")
        assert retrieved == test_data
        
        # Should now be in memory cache
        memory_entry = self.cache_manager.memory_cache.get("promotion_key")
        assert memory_entry is not None
    
    def test_cache_manager_key_generation(self):
        """Test cache key generation."""
        # Test basic key generation
        key1 = self.cache_manager.generate_cache_key("test_func", param1="value1", param2=42)
        key2 = self.cache_manager.generate_cache_key("test_func", param2=42, param1="value1")
        assert key1 == key2  # Order shouldn't matter
        
        # Test with different parameters
        key3 = self.cache_manager.generate_cache_key("test_func", param1="different")
        assert key1 != key3
        
        # Test with complex parameters
        key4 = self.cache_manager.generate_cache_key(
            "complex_func",
            list_param=[1, 2, 3],
            dict_param={"a": 1, "b": 2}
        )
        assert "complex_func" in key4
    
    def test_cache_manager_function_result_caching(self):
        """Test caching of function results."""
        test_result = {"function": "result", "data": [1, 2, 3]}
        
        # Cache function result
        cache_key = self.cache_manager.cache_analytics_result(
            "test_function",
            test_result,
            param1="value1",
            param2=42
        )
        
        # Retrieve cached result
        retrieved = self.cache_manager.get_cached_analytics_result(
            "test_function",
            param1="value1",
            param2=42
        )
        
        assert retrieved == test_result
        assert cache_key.startswith("test_function:")
    
    def test_cache_manager_invalidation(self):
        """Test cache invalidation."""
        # Add multiple entries
        self.cache_manager.cache_analytics("user:123:performance", {"data": "1"})
        self.cache_manager.cache_analytics("user:456:performance", {"data": "2"})
        self.cache_manager.cache_analytics("champion:789:stats", {"data": "3"})
        
        # Invalidate user performance entries
        invalidated = self.cache_manager.invalidate_cache("user:*:performance")
        assert invalidated >= 2
        
        # Check that user entries are gone but champion entry remains
        assert self.cache_manager.get_cached_analytics("user:123:performance") is None
        assert self.cache_manager.get_cached_analytics("user:456:performance") is None
        assert self.cache_manager.get_cached_analytics("champion:789:stats") is not None
    
    def test_cache_manager_statistics(self):
        """Test cache statistics tracking."""
        initial_stats = self.cache_manager.get_cache_statistics()
        assert initial_stats.total_requests == 0
        assert initial_stats.cache_hits == 0
        assert initial_stats.cache_misses == 0
        
        # Generate cache activity
        self.cache_manager.cache_analytics("stats_test", {"data": "test"})
        
        # Cache hit
        self.cache_manager.get_cached_analytics("stats_test")
        
        # Cache miss
        self.cache_manager.get_cached_analytics("nonexistent")
        
        stats = self.cache_manager.get_cache_statistics()
        assert stats.total_requests == 2
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.hit_rate == 0.5
    
    def test_cache_manager_ttl(self):
        """Test cache TTL functionality."""
        # Cache with short TTL
        self.cache_manager.cache_analytics("ttl_test", {"data": "test"}, ttl=1)
        
        # Should be available immediately
        assert self.cache_manager.get_cached_analytics("ttl_test") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert self.cache_manager.get_cached_analytics("ttl_test") is None
    
    def test_cache_manager_clear(self):
        """Test cache clearing."""
        # Add entries to both caches
        self.cache_manager.cache_analytics("clear_test1", {"data": "1"}, persistent=True)
        self.cache_manager.cache_analytics("clear_test2", {"data": "2"}, persistent=False)
        
        # Clear memory only
        self.cache_manager.clear_cache(memory_only=True)
        
        # Memory cache should be empty, persistent should remain
        self.cache_manager.memory_cache.clear()  # Ensure memory is clear
        assert self.cache_manager.get_cached_analytics("clear_test1") is not None  # From persistent
        
        # Clear all
        self.cache_manager.clear_cache(memory_only=False)
        assert self.cache_manager.get_cached_analytics("clear_test1") is None
    
    def test_cache_manager_persistent_determination(self):
        """Test determination of persistent caching."""
        # Test with function that should be cached persistently
        assert self.cache_manager._should_cache_persistently("analyze_player_performance", {}) is True
        
        # Test with function that shouldn't be cached persistently
        assert self.cache_manager._should_cache_persistently("simple_function", {}) is False
        
        # Test with large result
        large_result = {"data": "x" * 20000}  # > 10KB
        assert self.cache_manager._should_cache_persistently("any_function", large_result) is True
    
    def test_cache_manager_thread_safety(self):
        """Test cache manager thread safety."""
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"thread_{thread_id}_item_{i}"
                data = {"thread": thread_id, "item": i}
                
                # Cache data
                self.cache_manager.cache_analytics(key, data)
                
                # Retrieve data
                retrieved = self.cache_manager.get_cached_analytics(key)
                results.append(retrieved == data)
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert all(results)
    
    def test_cache_manager_with_analytics_models(self):
        """Test cache manager with actual analytics models."""
        # Create sample analytics data
        date_range = DateRange(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        performance = PerformanceMetrics(
            games_played=10,
            wins=7,
            losses=3,
            total_kills=50,
            total_deaths=25,
            total_assists=75
        )
        
        player_analytics = PlayerAnalytics(
            puuid="test_puuid",
            player_name="Test Player",
            analysis_period=date_range,
            overall_performance=performance
        )
        
        # Cache the analytics data
        self.cache_manager.cache_analytics("player_analytics_test", player_analytics)
        
        # Retrieve and verify
        retrieved = self.cache_manager.get_cached_analytics("player_analytics_test")
        assert retrieved is not None
        assert retrieved.puuid == "test_puuid"
        assert retrieved.player_name == "Test Player"
        assert retrieved.overall_performance.games_played == 10
    
    def test_cache_manager_error_handling(self):
        """Test cache manager error handling."""
        # Test with empty cache key
        with pytest.raises(CacheKeyError):
            self.cache_manager.cache_analytics("", {"data": "test"})
        
        # Test with None data (should work)
        self.cache_manager.cache_analytics("none_test", None)
        assert self.cache_manager.get_cached_analytics("none_test") is None
    
    def test_cache_manager_cleanup(self):
        """Test cache cleanup functionality."""
        # Add some entries
        for i in range(5):
            self.cache_manager.cache_analytics(f"cleanup_test_{i}", {"data": i})
        
        # Cleanup should not raise errors
        cleaned = self.cache_manager.cleanup_expired_entries()
        assert cleaned >= 0


class TestCacheStatistics:
    """Test Cache Statistics functionality."""
    
    def test_cache_statistics_creation(self):
        """Test cache statistics creation and properties."""
        stats = CacheStatistics(
            total_requests=100,
            cache_hits=75,
            cache_misses=25,
            total_entries=50,
            total_size_bytes=1024000
        )
        
        assert stats.hit_rate == 0.75
        assert stats.miss_rate == 0.25
        assert stats.average_entry_size == 20480.0
    
    def test_cache_statistics_edge_cases(self):
        """Test cache statistics edge cases."""
        # Zero requests
        stats = CacheStatistics()
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 1.0
        assert stats.average_entry_size == 0.0
        
        # Zero entries
        stats = CacheStatistics(total_requests=10, cache_hits=5, cache_misses=5)
        assert stats.average_entry_size == 0.0


if __name__ == "__main__":
    pytest.main([__file__])