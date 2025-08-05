"""
Performance tests and benchmarks for analytics optimization.

This module provides comprehensive performance testing for the analytics
optimization features including batch processing, incremental updates,
and query optimization.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock, patch
import statistics

from lol_team_optimizer.analytics_batch_processor import (
    BatchProcessor, AnalyticsBatchProcessor, BatchTask, BatchProgress
)
from lol_team_optimizer.incremental_analytics_updater import (
    IncrementalAnalyticsUpdater, CheckpointManager, UpdateCheckpoint
)
from lol_team_optimizer.query_optimizer import QueryOptimizer, MatchIndex
from lol_team_optimizer.analytics_models import AnalyticsFilters, DateRange
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestBatchProcessorPerformance:
    """Performance tests for batch processing."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "test_cache"
        config.max_cache_size_mb = 100
        return config
    
    @pytest.fixture
    def batch_processor(self, config):
        """Create batch processor for testing."""
        return BatchProcessor(config, max_workers=4)
    
    def test_batch_processing_throughput(self, batch_processor):
        """Test batch processing throughput with various task counts."""
        def dummy_task(task_id: str, delay: float = 0.01):
            """Dummy task that simulates work."""
            time.sleep(delay)
            return f"result_{task_id}"
        
        # Test different batch sizes
        batch_sizes = [10, 50, 100, 500]
        results = {}
        
        for batch_size in batch_sizes:
            # Create tasks
            tasks = []
            for i in range(batch_size):
                task = BatchTask(
                    task_id=f"task_{i}",
                    function=dummy_task,
                    args=(f"task_{i}",),
                    kwargs={"delay": 0.01}
                )
                tasks.append(task)
            
            # Measure execution time
            start_time = time.time()
            batch_result = batch_processor.process_batch_threaded(
                f"perf_test_{batch_size}", tasks
            )
            execution_time = time.time() - start_time
            
            # Calculate throughput
            throughput = batch_size / execution_time
            results[batch_size] = {
                'execution_time': execution_time,
                'throughput': throughput,
                'success_rate': batch_result.progress.success_rate
            }
            
            # Verify all tasks completed successfully
            assert batch_result.progress.completed_tasks == batch_size
            assert len(batch_result.successful_results) == batch_size
        
        # Verify throughput scales reasonably
        assert results[100]['throughput'] > results[10]['throughput']
        
        # Log performance results
        for batch_size, metrics in results.items():
            print(f"Batch size {batch_size}: {metrics['throughput']:.1f} tasks/sec, "
                  f"{metrics['execution_time']:.2f}s total")
    
    def test_parallel_vs_sequential_performance(self, batch_processor):
        """Compare parallel vs sequential execution performance."""
        def cpu_intensive_task(task_id: str, iterations: int = 10000):
            """CPU-intensive task for testing."""
            result = 0
            for i in range(iterations):
                result += i * i
            return result
        
        task_count = 20
        tasks = []
        for i in range(task_count):
            task = BatchTask(
                task_id=f"cpu_task_{i}",
                function=cpu_intensive_task,
                args=(f"cpu_task_{i}",),
                kwargs={"iterations": 50000}
            )
            tasks.append(task)
        
        # Test parallel execution
        start_time = time.time()
        parallel_result = batch_processor.process_batch_threaded(
            "parallel_test", tasks
        )
        parallel_time = time.time() - start_time
        
        # Test sequential execution (single worker)
        sequential_processor = BatchProcessor(batch_processor.config, max_workers=1)
        start_time = time.time()
        sequential_result = sequential_processor.process_batch_threaded(
            "sequential_test", tasks
        )
        sequential_time = time.time() - start_time
        
        # Verify both completed successfully
        assert parallel_result.progress.completed_tasks == task_count
        assert sequential_result.progress.completed_tasks == task_count
        
        # Parallel should be faster (with some tolerance for overhead)
        speedup = sequential_time / parallel_time
        assert speedup > 1.5, f"Expected speedup > 1.5, got {speedup:.2f}"
        
        print(f"Parallel: {parallel_time:.2f}s, Sequential: {sequential_time:.2f}s, "
              f"Speedup: {speedup:.2f}x")
    
    def test_memory_usage_under_load(self, batch_processor):
        """Test memory usage during large batch processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def memory_intensive_task(task_id: str, data_size: int = 1000):
            """Task that uses memory."""
            # Create some data
            data = list(range(data_size))
            return sum(data)
        
        # Process large batch
        task_count = 1000
        tasks = []
        for i in range(task_count):
            task = BatchTask(
                task_id=f"memory_task_{i}",
                function=memory_intensive_task,
                args=(f"memory_task_{i}",),
                kwargs={"data_size": 10000}
            )
            tasks.append(task)
        
        batch_result = batch_processor.process_batch_threaded(
            "memory_test", tasks
        )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify completion
        assert batch_result.progress.completed_tasks == task_count
        
        # Memory increase should be reasonable (less than 500MB for this test)
        assert memory_increase < 500, f"Memory increase too high: {memory_increase:.1f}MB"
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB "
              f"(+{memory_increase:.1f}MB)")
    
    def test_cancellation_performance(self, batch_processor):
        """Test performance of batch cancellation."""
        def long_running_task(task_id: str, duration: float = 1.0):
            """Long-running task for cancellation testing."""
            time.sleep(duration)
            return f"completed_{task_id}"
        
        # Create many long-running tasks
        task_count = 100
        tasks = []
        for i in range(task_count):
            task = BatchTask(
                task_id=f"long_task_{i}",
                function=long_running_task,
                args=(f"long_task_{i}",),
                kwargs={"duration": 0.5}
            )
            tasks.append(task)
        
        # Start batch processing in background
        batch_id = "cancellation_test"
        
        def run_batch():
            return batch_processor.process_batch_threaded(batch_id, tasks)
        
        batch_thread = threading.Thread(target=run_batch)
        batch_thread.start()
        
        # Wait a bit then cancel
        time.sleep(0.2)
        cancel_start = time.time()
        cancelled = batch_processor.cancel_batch(batch_id, "Performance test cancellation")
        cancel_time = time.time() - cancel_start
        
        # Wait for thread to complete
        batch_thread.join(timeout=5.0)
        
        # Verify cancellation was fast
        assert cancelled, "Batch should have been cancelled"
        assert cancel_time < 0.1, f"Cancellation took too long: {cancel_time:.3f}s"
        
        print(f"Cancellation time: {cancel_time:.3f}s")


class TestIncrementalUpdatePerformance:
    """Performance tests for incremental analytics updates."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Mock(spec=Config)
        config.data_directory = "test_data"
        config.cache_directory = "test_cache"
        config.max_cache_size_mb = 100
        return config
    
    @pytest.fixture
    def mock_analytics_engine(self):
        """Create mock analytics engine."""
        engine = Mock()
        engine.baseline_manager = Mock()
        engine.analyze_champion_performance = Mock(return_value=Mock())
        engine.calculate_performance_trends = Mock(return_value=Mock())
        return engine
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        manager = Mock()
        return manager
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create mock cache manager."""
        manager = Mock()
        manager.invalidate_cache = Mock(return_value=5)
        return manager
    
    @pytest.fixture
    def incremental_updater(self, config, mock_analytics_engine, 
                          mock_match_manager, mock_cache_manager):
        """Create incremental updater for testing."""
        return IncrementalAnalyticsUpdater(
            config, mock_analytics_engine, mock_match_manager, mock_cache_manager
        )
    
    def create_mock_matches(self, count: int, player_puuid: str) -> List[Match]:
        """Create mock matches for testing."""
        matches = []
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(count):
            participant = MatchParticipant(
                puuid=player_puuid,
                summoner_name=f"Player_{i}",
                champion_id=1 + (i % 10),
                champion_name=f"Champion_{1 + (i % 10)}",
                team_id=100,
                role="MIDDLE",
                lane="MIDDLE",
                individual_position="MIDDLE",
                kills=5,
                deaths=2,
                assists=8,
                total_damage_dealt_to_champions=15000,
                total_minions_killed=150,
                neutral_minions_killed=20,
                vision_score=25,
                gold_earned=12000,
                win=i % 2 == 0
            )
            
            match = Match(
                match_id=f"match_{i}",
                game_creation=base_time - (i * 3600000),  # 1 hour apart
                game_duration=1800,
                game_end_timestamp=base_time - (i * 3600000) + 1800000,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                map_id=11,
                queue_id=420,
                game_version="12.1.1",
                participants=[participant],
                winning_team=100 if i % 2 == 0 else 200
            )
            matches.append(match)
        
        return matches
    
    def test_incremental_update_performance(self, incremental_updater, mock_match_manager):
        """Test performance of incremental updates with various data sizes."""
        player_puuid = "test_player_123"
        
        # Test different numbers of new matches
        match_counts = [10, 50, 100, 500]
        results = {}
        
        for match_count in match_counts:
            # Create mock matches
            new_matches = self.create_mock_matches(match_count, player_puuid)
            mock_match_manager.get_matches_for_player.return_value = new_matches
            
            # Measure update time
            start_time = time.time()
            result = incremental_updater.update_player_analytics(player_puuid)
            update_time = time.time() - start_time
            
            results[match_count] = {
                'update_time': update_time,
                'matches_processed': result.new_matches_processed,
                'success': result.success
            }
            
            # Verify update succeeded
            assert result.success, f"Update failed for {match_count} matches"
            assert result.new_matches_processed == match_count
        
        # Verify performance scales reasonably (should be roughly linear)
        for count, metrics in results.items():
            throughput = metrics['matches_processed'] / metrics['update_time']
            print(f"Matches: {count}, Time: {metrics['update_time']:.3f}s, "
                  f"Throughput: {throughput:.1f} matches/sec")
        
        # Performance should not degrade significantly with more matches
        small_throughput = results[10]['matches_processed'] / results[10]['update_time']
        large_throughput = results[500]['matches_processed'] / results[500]['update_time']
        
        # Allow some degradation but not too much
        assert large_throughput > small_throughput * 0.5, \
            "Performance degraded too much with larger datasets"
    
    def test_checkpoint_manager_performance(self, config):
        """Test checkpoint manager performance with many checkpoints."""
        checkpoint_manager = CheckpointManager(config)
        
        # Create many checkpoints
        checkpoint_count = 1000
        player_puuids = [f"player_{i}" for i in range(checkpoint_count)]
        
        # Measure checkpoint creation time
        start_time = time.time()
        for puuid in player_puuids:
            checkpoint_manager.create_or_update_checkpoint(
                puuid, f"match_{puuid}", datetime.now()
            )
        creation_time = time.time() - start_time
        
        # Measure checkpoint retrieval time
        start_time = time.time()
        for puuid in player_puuids:
            checkpoint = checkpoint_manager.get_checkpoint(puuid)
            assert checkpoint is not None
        retrieval_time = time.time() - start_time
        
        # Performance should be reasonable
        creation_throughput = checkpoint_count / creation_time
        retrieval_throughput = checkpoint_count / retrieval_time
        
        assert creation_throughput > 100, f"Checkpoint creation too slow: {creation_throughput:.1f}/sec"
        assert retrieval_throughput > 1000, f"Checkpoint retrieval too slow: {retrieval_throughput:.1f}/sec"
        
        print(f"Checkpoint creation: {creation_throughput:.1f}/sec")
        print(f"Checkpoint retrieval: {retrieval_throughput:.1f}/sec")
    
    def test_concurrent_updates(self, incremental_updater, mock_match_manager):
        """Test performance of concurrent incremental updates."""
        player_count = 10
        matches_per_player = 50
        
        # Create mock data for each player
        for i in range(player_count):
            player_puuid = f"concurrent_player_{i}"
            matches = self.create_mock_matches(matches_per_player, player_puuid)
            mock_match_manager.get_matches_for_player.return_value = matches
        
        # Function to update a single player
        def update_player(player_id: int):
            player_puuid = f"concurrent_player_{player_id}"
            return incremental_updater.update_player_analytics(player_puuid)
        
        # Test concurrent updates
        start_time = time.time()
        
        threads = []
        results = {}
        
        for i in range(player_count):
            def worker(player_id=i):
                results[player_id] = update_player(player_id)
            
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        concurrent_time = time.time() - start_time
        
        # Verify all updates succeeded
        for i in range(player_count):
            assert results[i].success, f"Concurrent update failed for player {i}"
            assert results[i].new_matches_processed == matches_per_player
        
        # Calculate throughput
        total_matches = player_count * matches_per_player
        throughput = total_matches / concurrent_time
        
        print(f"Concurrent updates: {player_count} players, {total_matches} total matches, "
              f"{concurrent_time:.2f}s, {throughput:.1f} matches/sec")
        
        # Should be faster than sequential processing
        assert throughput > 50, f"Concurrent throughput too low: {throughput:.1f} matches/sec"


class TestQueryOptimizerPerformance:
    """Performance tests for query optimization."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "test_cache"
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        manager = Mock()
        manager.get_match_statistics.return_value = {'total_matches': 1000}
        manager.get_recent_matches.return_value = []
        return manager
    
    @pytest.fixture
    def query_optimizer(self, config, mock_match_manager):
        """Create query optimizer for testing."""
        return QueryOptimizer(config, mock_match_manager)
    
    def create_test_matches(self, count: int) -> List[Match]:
        """Create test matches for indexing."""
        matches = []
        base_time = int(datetime.now().timestamp() * 1000)
        
        for i in range(count):
            participants = []
            for j in range(10):  # 10 participants per match
                participant = MatchParticipant(
                    puuid=f"player_{j % 100}",  # 100 unique players
                    summoner_name=f"Player_{j}",
                    champion_id=1 + (i + j) % 50,  # 50 unique champions
                    champion_name=f"Champion_{1 + (i + j) % 50}",
                    team_id=100 if j < 5 else 200,
                    role=["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][j % 5],
                    lane=["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "BOTTOM"][j % 5],
                    individual_position=["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][j % 5],
                    kills=5,
                    deaths=2,
                    assists=8,
                    total_damage_dealt_to_champions=15000,
                    total_minions_killed=150,
                    neutral_minions_killed=20,
                    vision_score=25,
                    gold_earned=12000,
                    win=j < 5  # First team wins
                )
                participants.append(participant)
            
            match = Match(
                match_id=f"perf_match_{i}",
                game_creation=base_time - (i * 3600000),
                game_duration=1800,
                game_end_timestamp=base_time - (i * 3600000) + 1800000,
                game_mode="CLASSIC",
                game_type="MATCHED_GAME",
                map_id=11,
                queue_id=420,
                game_version="12.1.1",
                participants=participants,
                winning_team=100
            )
            matches.append(match)
        
        return matches
    
    def test_index_building_performance(self, query_optimizer):
        """Test performance of building match index."""
        match_counts = [100, 500, 1000, 5000]
        results = {}
        
        for match_count in match_counts:
            # Create test matches
            matches = self.create_test_matches(match_count)
            
            # Measure index building time
            start_time = time.time()
            for match in matches:
                query_optimizer.add_match_to_index(match)
            index_time = time.time() - start_time
            
            results[match_count] = {
                'index_time': index_time,
                'throughput': match_count / index_time
            }
            
            # Verify index was built correctly
            stats = query_optimizer.index.get_statistics()
            assert stats['total_matches_indexed'] >= match_count
        
        # Performance should scale reasonably
        for count, metrics in results.items():
            print(f"Matches: {count}, Index time: {metrics['index_time']:.3f}s, "
                  f"Throughput: {metrics['throughput']:.1f} matches/sec")
        
        # Should be able to index at least 1000 matches per second
        assert results[1000]['throughput'] > 1000, \
            f"Index building too slow: {results[1000]['throughput']:.1f} matches/sec"
    
    def test_query_execution_performance(self, query_optimizer, mock_match_manager):
        """Test query execution performance with various filter combinations."""
        # Build index with test data
        matches = self.create_test_matches(1000)
        for match in matches:
            query_optimizer.add_match_to_index(match)
        
        # Mock match manager to return matches
        match_lookup = {match.match_id: match for match in matches}
        mock_match_manager.get_match.side_effect = lambda match_id: match_lookup.get(match_id)
        
        # Test different query types
        query_tests = [
            {
                'name': 'player_filter',
                'filters': AnalyticsFilters(player_puuids=['player_1', 'player_2'])
            },
            {
                'name': 'champion_filter',
                'filters': AnalyticsFilters(champions=[1, 2, 3])
            },
            {
                'name': 'role_filter',
                'filters': AnalyticsFilters(roles=['MIDDLE', 'BOTTOM'])
            },
            {
                'name': 'date_filter',
                'filters': AnalyticsFilters(
                    date_range=DateRange(
                        start_date=datetime.now() - timedelta(days=30),
                        end_date=datetime.now()
                    )
                )
            },
            {
                'name': 'complex_filter',
                'filters': AnalyticsFilters(
                    player_puuids=['player_1'],
                    champions=[1, 2],
                    roles=['MIDDLE'],
                    queue_types=[420]
                )
            }
        ]
        
        results = {}
        
        for test in query_tests:
            # Measure query execution time
            start_time = time.time()
            query_results = query_optimizer.execute_optimized_query(
                test['filters'], test['name']
            )
            query_time = time.time() - start_time
            
            results[test['name']] = {
                'query_time': query_time,
                'result_count': len(query_results)
            }
            
            # Verify query returned results
            assert isinstance(query_results, list)
        
        # All queries should be fast (< 100ms for 1000 matches)
        for query_name, metrics in results.items():
            assert metrics['query_time'] < 0.1, \
                f"Query {query_name} too slow: {metrics['query_time']:.3f}s"
            
            print(f"Query {query_name}: {metrics['query_time']:.3f}s, "
                  f"{metrics['result_count']} results")
    
    def test_cache_performance(self, query_optimizer, mock_match_manager):
        """Test query cache performance."""
        # Build index
        matches = self.create_test_matches(500)
        for match in matches:
            query_optimizer.add_match_to_index(match)
        
        match_lookup = {match.match_id: match for match in matches}
        mock_match_manager.get_match.side_effect = lambda match_id: match_lookup.get(match_id)
        
        filters = AnalyticsFilters(player_puuids=['player_1'])
        
        # First query (cache miss)
        start_time = time.time()
        results1 = query_optimizer.execute_optimized_query(filters, "cache_test")
        first_query_time = time.time() - start_time
        
        # Second query (cache hit)
        start_time = time.time()
        results2 = query_optimizer.execute_optimized_query(filters, "cache_test")
        second_query_time = time.time() - start_time
        
        # Verify results are the same
        assert len(results1) == len(results2)
        
        # Cache hit should be much faster
        speedup = first_query_time / second_query_time
        assert speedup > 5, f"Cache speedup too low: {speedup:.1f}x"
        
        print(f"First query: {first_query_time:.3f}s, Second query: {second_query_time:.3f}s, "
              f"Speedup: {speedup:.1f}x")
    
    def test_concurrent_query_performance(self, query_optimizer, mock_match_manager):
        """Test concurrent query performance."""
        # Build index
        matches = self.create_test_matches(1000)
        for match in matches:
            query_optimizer.add_match_to_index(match)
        
        match_lookup = {match.match_id: match for match in matches}
        mock_match_manager.get_match.side_effect = lambda match_id: match_lookup.get(match_id)
        
        # Function to execute a query
        def execute_query(query_id: int):
            filters = AnalyticsFilters(player_puuids=[f'player_{query_id % 10}'])
            return query_optimizer.execute_optimized_query(filters, f"concurrent_{query_id}")
        
        # Test concurrent queries
        query_count = 20
        start_time = time.time()
        
        threads = []
        results = {}
        
        for i in range(query_count):
            def worker(query_id=i):
                results[query_id] = execute_query(query_id)
            
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        concurrent_time = time.time() - start_time
        
        # Verify all queries completed
        assert len(results) == query_count
        for i in range(query_count):
            assert isinstance(results[i], list)
        
        # Calculate throughput
        throughput = query_count / concurrent_time
        
        print(f"Concurrent queries: {query_count} queries in {concurrent_time:.2f}s, "
              f"{throughput:.1f} queries/sec")
        
        # Should handle at least 50 queries per second
        assert throughput > 50, f"Concurrent query throughput too low: {throughput:.1f} queries/sec"


class TestIntegratedPerformance:
    """Integrated performance tests combining all optimization features."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Mock(spec=Config)
        config.data_directory = "test_data"
        config.cache_directory = "test_cache"
        config.max_cache_size_mb = 100
        return config
    
    def test_end_to_end_performance(self, config):
        """Test end-to-end performance of the complete analytics system."""
        # This would be a comprehensive test that exercises all components
        # together in a realistic scenario
        
        # Mock components
        mock_match_manager = Mock()
        mock_analytics_engine = Mock()
        mock_cache_manager = Mock()
        
        # Create test data
        player_count = 50
        matches_per_player = 100
        
        # Simulate realistic workload
        start_time = time.time()
        
        # 1. Batch process player analytics
        batch_processor = AnalyticsBatchProcessor(
            config, mock_analytics_engine, mock_match_manager
        )
        
        player_puuids = [f"player_{i}" for i in range(player_count)]
        
        # Mock analytics engine responses
        mock_analytics_engine.analyze_player_performance.return_value = Mock()
        
        batch_result = batch_processor.batch_analyze_players(player_puuids)
        
        # 2. Incremental updates
        incremental_updater = IncrementalAnalyticsUpdater(
            config, mock_analytics_engine, mock_match_manager, mock_cache_manager
        )
        
        # Mock new matches for incremental updates
        mock_match_manager.get_matches_for_player.return_value = []
        
        update_results = incremental_updater.update_multiple_players(
            player_puuids[:10], force_full_update=False
        )
        
        # 3. Query optimization
        query_optimizer = QueryOptimizer(config, mock_match_manager)
        
        # Execute various queries
        filters = AnalyticsFilters(player_puuids=player_puuids[:5])
        query_results = query_optimizer.execute_optimized_query(filters, "integrated_test")
        
        total_time = time.time() - start_time
        
        # Verify all operations completed successfully
        assert batch_result.progress.success_rate > 95
        assert all(result.success for result in update_results.values())
        assert isinstance(query_results, list)
        
        # Performance should be reasonable for this workload
        assert total_time < 10.0, f"End-to-end test took too long: {total_time:.2f}s"
        
        print(f"End-to-end performance test completed in {total_time:.2f}s")
        print(f"Batch processing: {batch_result.progress.completed_tasks} players")
        print(f"Incremental updates: {len(update_results)} players")
        print(f"Query results: {len(query_results)} matches")
    
    def test_memory_efficiency(self, config):
        """Test memory efficiency of the complete system."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create components
        mock_match_manager = Mock()
        mock_analytics_engine = Mock()
        mock_cache_manager = Mock()
        
        batch_processor = AnalyticsBatchProcessor(
            config, mock_analytics_engine, mock_match_manager
        )
        
        incremental_updater = IncrementalAnalyticsUpdater(
            config, mock_analytics_engine, mock_match_manager, mock_cache_manager
        )
        
        query_optimizer = QueryOptimizer(config, mock_match_manager)
        
        # Simulate workload
        player_puuids = [f"player_{i}" for i in range(100)]
        
        # Mock responses
        mock_analytics_engine.analyze_player_performance.return_value = Mock()
        mock_match_manager.get_matches_for_player.return_value = []
        
        # Execute operations
        batch_processor.batch_analyze_players(player_puuids[:20])
        incremental_updater.update_multiple_players(player_puuids[:10])
        
        filters = AnalyticsFilters(player_puuids=player_puuids[:5])
        query_optimizer.execute_optimized_query(filters, "memory_test")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 200MB)
        assert memory_increase < 200, f"Memory usage too high: {memory_increase:.1f}MB"
        
        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB "
              f"(+{memory_increase:.1f}MB)")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])