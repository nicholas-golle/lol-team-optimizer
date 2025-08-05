"""
Performance tests for the Analytics Cache Manager.

This module contains performance tests to demonstrate the effectiveness
of the caching system in improving analytics operations speed.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock

from lol_team_optimizer.analytics_cache_manager import AnalyticsCacheManager
from lol_team_optimizer.config import Config
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics,
    PerformanceMetrics,
    DateRange,
    ChampionPerformanceMetrics
)


class TestAnalyticsCachePerformance:
    """Performance tests for analytics cache manager."""
    
    def setup_method(self):
        """Set up test environment."""
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            cache_directory=self.temp_dir,
            max_cache_size_mb=10  # Larger cache for performance tests
        )
        self.cache_manager = AnalyticsCacheManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_sample_analytics_data(self, player_id: str) -> PlayerAnalytics:
        """Create sample analytics data for testing."""
        date_range = DateRange(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        performance = PerformanceMetrics(
            games_played=50,
            wins=32,
            losses=18,
            total_kills=250,
            total_deaths=125,
            total_assists=375,
            total_cs=12500,
            total_vision_score=1500,
            total_damage_to_champions=500000,
            total_gold_earned=750000,
            total_game_duration=90000  # 25 hours in seconds
        )
        
        return PlayerAnalytics(
            puuid=player_id,
            player_name=f"Player {player_id}",
            analysis_period=date_range,
            overall_performance=performance
        )
    
    def _expensive_analytics_calculation(self, player_id: str) -> PlayerAnalytics:
        """Simulate an expensive analytics calculation."""
        # Simulate computation time
        time.sleep(0.01)  # 10ms delay
        return self._create_sample_analytics_data(player_id)
    
    def test_cache_hit_performance(self):
        """Test performance improvement from cache hits."""
        player_id = "performance_test_player"
        
        # First call - cache miss (expensive)
        start_time = time.time()
        result1 = self._expensive_analytics_calculation(player_id)
        self.cache_manager.cache_analytics(f"player_analytics:{player_id}", result1)
        first_call_time = time.time() - start_time
        
        # Second call - cache hit (fast)
        start_time = time.time()
        cached_result = self.cache_manager.get_cached_analytics(f"player_analytics:{player_id}")
        second_call_time = time.time() - start_time
        
        # Cache hit should be significantly faster
        assert cached_result is not None
        assert cached_result.puuid == player_id
        assert second_call_time < first_call_time * 0.1  # At least 10x faster
    
    def test_memory_cache_performance(self):
        """Test memory cache performance with frequent access."""
        num_players = 100
        access_count = 5
        
        # Populate cache with player data
        for i in range(num_players):
            player_id = f"memory_test_player_{i}"
            data = self._create_sample_analytics_data(player_id)
            self.cache_manager.cache_analytics(f"player:{player_id}", data, persistent=False)
        
        # Measure access time for frequent lookups
        start_time = time.time()
        for _ in range(access_count):
            for i in range(num_players):
                player_id = f"memory_test_player_{i}"
                result = self.cache_manager.get_cached_analytics(f"player:{player_id}")
                assert result is not None
        
        total_time = time.time() - start_time
        avg_access_time = total_time / (num_players * access_count)
        
        # Memory cache access should be very fast
        assert avg_access_time < 0.001  # Less than 1ms per access
    
    def test_persistent_cache_performance(self):
        """Test persistent cache performance."""
        num_entries = 50
        
        # Populate persistent cache
        populate_start = time.time()
        for i in range(num_entries):
            key = f"persistent_test_{i}"
            data = self._create_sample_analytics_data(f"player_{i}")
            self.cache_manager.cache_analytics(key, data, persistent=True)
        populate_time = time.time() - populate_start
        
        # Clear memory cache to force persistent cache access
        self.cache_manager.memory_cache.clear()
        
        # Measure persistent cache access time
        access_start = time.time()
        for i in range(num_entries):
            key = f"persistent_test_{i}"
            result = self.cache_manager.get_cached_analytics(key)
            assert result is not None
        access_time = time.time() - access_start
        
        avg_populate_time = populate_time / num_entries
        avg_access_time = access_time / num_entries
        
        # Persistent cache should still be reasonably fast
        assert avg_populate_time < 0.1  # Less than 100ms per entry
        assert avg_access_time < 0.05   # Less than 50ms per access
    
    def test_cache_promotion_performance(self):
        """Test performance of cache promotion from persistent to memory."""
        player_id = "promotion_test_player"
        data = self._create_sample_analytics_data(player_id)
        
        # Add to persistent cache only
        from lol_team_optimizer.analytics_cache_manager import CacheEntry
        entry = CacheEntry(
            key=f"player:{player_id}",
            data=data,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1
        )
        self.cache_manager.persistent_cache.put(f"player:{player_id}", entry)
        
        # Clear memory cache
        self.cache_manager.memory_cache.clear()
        
        # First access - from persistent cache
        start_time = time.time()
        result1 = self.cache_manager.get_cached_analytics(f"player:{player_id}")
        first_access_time = time.time() - start_time
        
        # Simulate multiple accesses to trigger promotion
        for _ in range(3):
            self.cache_manager.get_cached_analytics(f"player:{player_id}")
        
        # Access after promotion - should be from memory cache
        start_time = time.time()
        result2 = self.cache_manager.get_cached_analytics(f"player:{player_id}")
        promoted_access_time = time.time() - start_time
        
        assert result1 is not None
        assert result2 is not None
        # Promoted access should be faster
        assert promoted_access_time < first_access_time * 0.5
    
    def test_concurrent_cache_performance(self):
        """Test cache performance under concurrent access."""
        num_threads = 10
        operations_per_thread = 20
        results = []
        
        def worker(thread_id):
            thread_results = []
            for i in range(operations_per_thread):
                key = f"concurrent_test_{thread_id}_{i}"
                data = self._create_sample_analytics_data(f"player_{thread_id}_{i}")
                
                # Cache data
                start_time = time.time()
                self.cache_manager.cache_analytics(key, data)
                cache_time = time.time() - start_time
                
                # Retrieve data
                start_time = time.time()
                retrieved = self.cache_manager.get_cached_analytics(key)
                retrieve_time = time.time() - start_time
                
                thread_results.append({
                    'cache_time': cache_time,
                    'retrieve_time': retrieve_time,
                    'success': retrieved is not None
                })
            
            results.extend(thread_results)
        
        # Run concurrent operations
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_operations = sum(1 for r in results if r['success'])
        avg_cache_time = sum(r['cache_time'] for r in results) / len(results)
        avg_retrieve_time = sum(r['retrieve_time'] for r in results) / len(results)
        
        # All operations should succeed
        assert successful_operations == num_threads * operations_per_thread
        
        # Operations should complete in reasonable time
        assert avg_cache_time < 0.5   # Less than 500ms per cache operation
        assert avg_retrieve_time < 0.1  # Less than 100ms per retrieve operation
        assert total_time < 30.0  # Total test should complete in under 30 seconds
    
    def test_cache_statistics_performance_impact(self):
        """Test that statistics tracking doesn't significantly impact performance."""
        num_operations = 1000
        
        # Test with statistics enabled (default)
        start_time = time.time()
        for i in range(num_operations):
            key = f"stats_test_{i}"
            data = {"test": f"data_{i}"}
            self.cache_manager.cache_analytics(key, data)
            self.cache_manager.get_cached_analytics(key)
        
        with_stats_time = time.time() - start_time
        
        # Get statistics
        stats = self.cache_manager.get_cache_statistics()
        
        # Verify statistics are being tracked
        assert stats.total_requests >= num_operations
        assert stats.cache_hits > 0
        
        # Statistics overhead should be minimal
        avg_operation_time = with_stats_time / (num_operations * 2)  # 2 operations per iteration
        assert avg_operation_time < 0.1  # Less than 100ms per operation
    
    def test_large_data_caching_performance(self):
        """Test performance with large data objects."""
        # Create large analytics data
        large_data = {
            'player_analytics': self._create_sample_analytics_data("large_data_player"),
            'match_history': [{'match_id': f'match_{i}', 'data': 'x' * 1000} for i in range(100)],
            'performance_trends': [{'timestamp': datetime.now(), 'value': i} for i in range(500)]
        }
        
        # Test caching large data
        start_time = time.time()
        self.cache_manager.cache_analytics("large_data_test", large_data, persistent=True)
        cache_time = time.time() - start_time
        
        # Test retrieving large data
        start_time = time.time()
        retrieved = self.cache_manager.get_cached_analytics("large_data_test")
        retrieve_time = time.time() - start_time
        
        assert retrieved is not None
        assert len(retrieved['match_history']) == 100
        assert len(retrieved['performance_trends']) == 500
        
        # Large data operations should still be reasonably fast
        assert cache_time < 0.1    # Less than 100ms to cache
        assert retrieve_time < 0.05  # Less than 50ms to retrieve
    
    def test_cache_invalidation_performance(self):
        """Test performance of cache invalidation operations."""
        num_entries = 200
        
        # Populate cache with entries
        for i in range(num_entries):
            key = f"invalidation_test_{i % 10}_{i}"  # Create pattern for invalidation
            data = self._create_sample_analytics_data(f"player_{i}")
            self.cache_manager.cache_analytics(key, data)
        
        # Test pattern-based invalidation performance
        start_time = time.time()
        invalidated = self.cache_manager.invalidate_cache("invalidation_test_5_*")
        invalidation_time = time.time() - start_time
        
        assert invalidated > 0
        # Invalidation should be fast even with many entries
        assert invalidation_time < 0.1  # Less than 100ms
        
        # Test full cache clear performance
        start_time = time.time()
        self.cache_manager.clear_cache()
        clear_time = time.time() - start_time
        
        # Cache clear should be reasonably fast
        assert clear_time < 1.0  # Less than 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])