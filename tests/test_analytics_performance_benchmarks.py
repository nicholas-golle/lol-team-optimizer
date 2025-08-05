"""
Performance benchmark tests for analytics system.

This module provides comprehensive performance testing for analytics operations
under various load conditions and dataset sizes.
"""

import pytest
import time
import threading
import multiprocessing
import psutil
import os
import gc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock, MagicMock
import tempfile
from pathlib import Path
import statistics
import json

# Import analytics components
from lol_team_optimizer.historical_analytics_engine import HistoricalAnalyticsEngine
from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
from lol_team_optimizer.team_composition_analyzer import TeamCompositionAnalyzer
from lol_team_optimizer.baseline_manager import BaselineManager
from lol_team_optimizer.statistical_analyzer import StatisticalAnalyzer
from lol_team_optimizer.analytics_cache_manager import AnalyticsCacheManager
from lol_team_optimizer.comparative_analyzer import ComparativeAnalyzer

# Import models
from lol_team_optimizer.analytics_models import AnalyticsFilters, TeamComposition
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.match_manager import MatchManager


class PerformanceBenchmark:
    """Utility class for performance benchmarking."""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process(os.getpid())
    
    def benchmark_function(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Benchmark a function and return performance metrics."""
        # Record initial state
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu_percent = self.process.cpu_percent()
        
        # Run garbage collection before benchmark
        gc.collect()
        
        # Execute function with timing
        start_time = time.time()
        start_cpu_time = time.process_time()
        
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_cpu_time = time.process_time()
        
        # Record final state
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        final_cpu_percent = self.process.cpu_percent()
        
        return {
            'result': result,
            'success': success,
            'error': error,
            'wall_time': end_time - start_time,
            'cpu_time': end_cpu_time - start_cpu_time,
            'memory_used': final_memory - initial_memory,
            'peak_memory': final_memory,
            'cpu_percent': final_cpu_percent
        }
    
    def benchmark_concurrent(self, func, args_list: List[Tuple], max_workers: int = 10) -> Dict[str, Any]:
        """Benchmark concurrent execution of a function."""
        import concurrent.futures
        
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        start_time = time.time()
        
        results = []
        errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(func, *args) for args in args_list]
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
        
        end_time = time.time()
        final_memory = self.process.memory_info().rss / 1024 / 1024
        
        return {
            'total_tasks': len(args_list),
            'successful_tasks': len(results),
            'failed_tasks': len(errors),
            'total_time': end_time - start_time,
            'average_time_per_task': (end_time - start_time) / len(args_list),
            'memory_used': final_memory - initial_memory,
            'errors': errors[:5]  # First 5 errors for debugging
        }


class TestAnalyticsPerformanceBenchmarks:
    """Comprehensive performance benchmarks for analytics system."""
    
    @pytest.fixture(scope="class")
    def performance_datasets(self):
        """Create datasets of various sizes for performance testing."""
        datasets = {}
        
        # Small dataset: 100 matches
        datasets['small'] = self._create_dataset(100, 5, 30)
        
        # Medium dataset: 1000 matches
        datasets['medium'] = self._create_dataset(1000, 10, 90)
        
        # Large dataset: 5000 matches
        datasets['large'] = self._create_dataset(5000, 20, 180)
        
        # Extra large dataset: 10000 matches
        datasets['xlarge'] = self._create_dataset(10000, 50, 365)
        
        return datasets
    
    def _create_dataset(self, num_matches: int, num_players: int, days_span: int) -> List[Match]:
        """Create a dataset with specified parameters."""
        matches = []
        players = [f"player_{i}" for i in range(num_players)]
        champions = list(range(1, 161))  # All champions
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        base_date = datetime.now() - timedelta(days=days_span)
        
        for i in range(num_matches):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_creation = int((base_date + timedelta(days=i * days_span / num_matches)).timestamp() * 1000)
            match.game_duration = 1500 + (i % 1800)  # 25-55 minutes
            match.participants = []
            
            # Create 10 participants per match
            for j in range(10):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = players[j % num_players]
                participant.champion_id = champions[(i + j) % len(champions)]
                participant.team_position = roles[j % 5]
                participant.win = j < 5 if i % 2 == 0 else j >= 5
                
                # Generate realistic performance data
                participant.kills = max(0, 5 + (i % 10) - 3 + (j % 7) - 3)
                participant.deaths = max(1, 3 + (i % 5) - 1 + (j % 4) - 1)
                participant.assists = max(0, 8 + (i % 8) - 3 + (j % 6) - 2)
                participant.total_minions_killed = 120 + (i % 100) + (j * 10)
                participant.vision_score = 15 + (i % 25) + (j % 10)
                participant.total_damage_dealt_to_champions = 12000 + (i * 50) + (j * 500)
                
                match.participants.append(participant)
            
            matches.append(match)
        
        return matches
    
    @pytest.fixture
    def benchmark_tool(self):
        """Create performance benchmark tool."""
        return PerformanceBenchmark()
    
    def test_player_analysis_performance_scaling(self, performance_datasets, benchmark_tool):
        """Test how player analysis performance scales with dataset size."""
        results = {}
        
        for dataset_name, dataset in performance_datasets.items():
            # Create analytics system with this dataset
            match_manager = Mock(spec=MatchManager)
            match_manager.get_matches_for_player.return_value = dataset
            
            from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
            analytics_engine = HistoricalAnalyticsEngine(
                match_manager, baseline_manager, StatisticalAnalyzer(),
                AnalyticsCacheManager()
            )
            
            # Benchmark player analysis
            benchmark_result = benchmark_tool.benchmark_function(
                analytics_engine.analyze_player_performance,
                "player_0", AnalyticsFilters()
            )
            
            results[dataset_name] = {
                'dataset_size': len(dataset),
                'wall_time': benchmark_result['wall_time'],
                'cpu_time': benchmark_result['cpu_time'],
                'memory_used': benchmark_result['memory_used'],
                'success': benchmark_result['success']
            }
        
        # Verify performance scaling
        assert all(result['success'] for result in results.values())
        
        # Performance should scale reasonably (not exponentially)
        small_time = results['small']['wall_time']
        large_time = results['large']['wall_time']
        
        # Large dataset (50x size) should not take more than 100x time
        scaling_factor = large_time / small_time if small_time > 0 else 0
        assert scaling_factor < 100, f"Performance scaling too poor: {scaling_factor}x"
        
        # Log performance results
        print("\nPlayer Analysis Performance Scaling:")
        for dataset_name, result in results.items():
            print(f"{dataset_name}: {result['dataset_size']} matches, "
                  f"{result['wall_time']:.3f}s, {result['memory_used']:.1f}MB")
    
    def test_champion_recommendation_performance(self, performance_datasets, benchmark_tool):
        """Test champion recommendation performance across dataset sizes."""
        results = {}
        
        for dataset_name, dataset in performance_datasets.items():
            if dataset_name == 'xlarge':  # Skip extra large for recommendation tests
                continue
                
            # Create analytics system
            match_manager = Mock(spec=MatchManager)
            match_manager.get_matches_for_player.return_value = dataset
            
            from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
            analytics_engine = HistoricalAnalyticsEngine(
                match_manager, baseline_manager, StatisticalAnalyzer(),
                AnalyticsCacheManager()
            )
            
            recommendation_engine = ChampionRecommendationEngine(
                analytics_engine, Mock()
            )
            
            # Benchmark recommendation generation
            team_context = {'existing_picks': [], 'banned_champions': [1, 2, 3]}
            
            benchmark_result = benchmark_tool.benchmark_function(
                recommendation_engine.get_champion_recommendations,
                "player_0", "TOP", team_context
            )
            
            results[dataset_name] = {
                'dataset_size': len(dataset),
                'wall_time': benchmark_result['wall_time'],
                'memory_used': benchmark_result['memory_used'],
                'success': benchmark_result['success']
            }
        
        # Verify recommendation performance
        assert all(result['success'] for result in results.values())
        
        # Recommendations should complete within reasonable time
        for dataset_name, result in results.items():
            assert result['wall_time'] < 10.0, f"Recommendation too slow for {dataset_name}: {result['wall_time']}s"
        
        print("\nChampion Recommendation Performance:")
        for dataset_name, result in results.items():
            print(f"{dataset_name}: {result['wall_time']:.3f}s, {result['memory_used']:.1f}MB")
    
    def test_concurrent_analytics_performance(self, performance_datasets, benchmark_tool):
        """Test performance under concurrent analytics requests."""
        dataset = performance_datasets['medium']  # Use medium dataset
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = dataset
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            # Prepare arguments for concurrent execution
            args_list = [
                ("player_0", AnalyticsFilters()),
                ("player_1", AnalyticsFilters()),
                ("player_2", AnalyticsFilters()),
                ("player_3", AnalyticsFilters()),
                ("player_4", AnalyticsFilters())
            ] * (concurrency // 5 + 1)  # Repeat to reach desired concurrency
            
            args_list = args_list[:concurrency]  # Trim to exact concurrency level
            
            # Benchmark concurrent execution
            concurrent_result = benchmark_tool.benchmark_concurrent(
                analytics_engine.analyze_player_performance,
                args_list,
                max_workers=concurrency
            )
            
            results[concurrency] = concurrent_result
        
        # Verify concurrent performance
        for concurrency, result in results.items():
            assert result['successful_tasks'] == result['total_tasks'], \
                f"Some tasks failed at concurrency {concurrency}"
            
            # Higher concurrency should not be dramatically slower per task
            if concurrency > 1:
                single_thread_time = results[1]['average_time_per_task']
                concurrent_time = result['average_time_per_task']
                
                # Allow up to 3x slowdown for high concurrency
                slowdown_factor = concurrent_time / single_thread_time if single_thread_time > 0 else 1
                assert slowdown_factor < 3.0, \
                    f"Concurrency {concurrency} too slow: {slowdown_factor}x slowdown"
        
        print("\nConcurrent Analytics Performance:")
        for concurrency, result in results.items():
            print(f"{concurrency} threads: {result['total_time']:.3f}s total, "
                  f"{result['average_time_per_task']:.3f}s per task")
    
    def test_cache_performance_impact(self, performance_datasets, benchmark_tool):
        """Test performance impact of caching system."""
        dataset = performance_datasets['medium']
        
        # Test without caching
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = dataset
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        
        # Analytics engine without cache
        analytics_engine_no_cache = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(), None
        )
        
        # Analytics engine with cache
        analytics_engine_with_cache = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Benchmark without cache (first run)
        no_cache_result = benchmark_tool.benchmark_function(
            analytics_engine_no_cache.analyze_player_performance,
            "player_0", AnalyticsFilters()
        )
        
        # Benchmark with cache (first run - should populate cache)
        with_cache_first = benchmark_tool.benchmark_function(
            analytics_engine_with_cache.analyze_player_performance,
            "player_0", AnalyticsFilters()
        )
        
        # Benchmark with cache (second run - should use cache)
        with_cache_second = benchmark_tool.benchmark_function(
            analytics_engine_with_cache.analyze_player_performance,
            "player_0", AnalyticsFilters()
        )
        
        # Verify cache effectiveness
        assert no_cache_result['success']
        assert with_cache_first['success']
        assert with_cache_second['success']
        
        # Second cached run should be significantly faster
        cache_speedup = with_cache_first['wall_time'] / with_cache_second['wall_time'] \
            if with_cache_second['wall_time'] > 0 else 1
        
        # Cache should provide at least 2x speedup
        assert cache_speedup >= 2.0, f"Cache not effective: only {cache_speedup}x speedup"
        
        print(f"\nCache Performance Impact:")
        print(f"No cache: {no_cache_result['wall_time']:.3f}s")
        print(f"With cache (first): {with_cache_first['wall_time']:.3f}s")
        print(f"With cache (second): {with_cache_second['wall_time']:.3f}s")
        print(f"Cache speedup: {cache_speedup:.1f}x")
    
    def test_memory_usage_patterns(self, performance_datasets, benchmark_tool):
        """Test memory usage patterns during analytics operations."""
        dataset = performance_datasets['large']
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = dataset
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Monitor memory usage during multiple operations
        initial_memory = benchmark_tool.process.memory_info().rss / 1024 / 1024
        memory_samples = [initial_memory]
        
        # Perform multiple analytics operations
        for i in range(10):
            analytics_engine.analyze_player_performance(f"player_{i % 5}", AnalyticsFilters())
            
            current_memory = benchmark_tool.process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
            # Force garbage collection periodically
            if i % 3 == 0:
                gc.collect()
        
        # Analyze memory usage patterns
        max_memory = max(memory_samples)
        final_memory = memory_samples[-1]
        memory_growth = final_memory - initial_memory
        peak_memory_growth = max_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 500, f"Excessive memory growth: {memory_growth}MB"
        assert peak_memory_growth < 1000, f"Excessive peak memory: {peak_memory_growth}MB"
        
        print(f"\nMemory Usage Patterns:")
        print(f"Initial: {initial_memory:.1f}MB")
        print(f"Final: {final_memory:.1f}MB")
        print(f"Growth: {memory_growth:.1f}MB")
        print(f"Peak growth: {peak_memory_growth:.1f}MB")
    
    def test_statistical_computation_performance(self, benchmark_tool):
        """Test performance of statistical computations."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Test with different data sizes
        data_sizes = [100, 1000, 10000, 50000]
        results = {}
        
        for size in data_sizes:
            # Generate test data
            test_data = [i + (i % 17) * 0.1 for i in range(size)]
            
            # Benchmark confidence interval calculation
            ci_result = benchmark_tool.benchmark_function(
                statistical_analyzer.calculate_confidence_intervals,
                test_data, 0.95
            )
            
            # Benchmark correlation analysis
            variables = {
                'x': test_data,
                'y': [val * 2 + 1 for val in test_data],
                'z': [val * -0.5 + 10 for val in test_data]
            }
            
            corr_result = benchmark_tool.benchmark_function(
                statistical_analyzer.analyze_correlations,
                variables
            )
            
            results[size] = {
                'confidence_interval_time': ci_result['wall_time'],
                'correlation_time': corr_result['wall_time'],
                'ci_success': ci_result['success'],
                'corr_success': corr_result['success']
            }
        
        # Verify statistical computation performance
        for size, result in results.items():
            assert result['ci_success'], f"CI calculation failed for size {size}"
            assert result['corr_success'], f"Correlation calculation failed for size {size}"
            
            # Performance should be reasonable even for large datasets
            assert result['confidence_interval_time'] < 5.0, \
                f"CI calculation too slow for size {size}: {result['confidence_interval_time']}s"
            assert result['correlation_time'] < 10.0, \
                f"Correlation calculation too slow for size {size}: {result['correlation_time']}s"
        
        print("\nStatistical Computation Performance:")
        for size, result in results.items():
            print(f"Size {size}: CI {result['confidence_interval_time']:.3f}s, "
                  f"Corr {result['correlation_time']:.3f}s")
    
    def test_team_composition_analysis_performance(self, performance_datasets, benchmark_tool):
        """Test performance of team composition analysis."""
        dataset = performance_datasets['medium']
        
        # Create composition analyzer
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = dataset
        match_manager.get_recent_matches.return_value = dataset
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        composition_analyzer = TeamCompositionAnalyzer(match_manager, baseline_manager)
        
        # Test composition analysis performance
        test_composition = TeamComposition(
            players={
                'TOP': {'puuid': 'player_0', 'champion_id': 1},
                'JUNGLE': {'puuid': 'player_1', 'champion_id': 2},
                'MIDDLE': {'puuid': 'player_2', 'champion_id': 3},
                'BOTTOM': {'puuid': 'player_3', 'champion_id': 4},
                'UTILITY': {'puuid': 'player_4', 'champion_id': 5}
            }
        )
        
        # Benchmark composition analysis
        analysis_result = benchmark_tool.benchmark_function(
            composition_analyzer.analyze_composition_performance,
            test_composition
        )
        
        # Benchmark optimal composition identification
        player_pool = ['player_0', 'player_1', 'player_2', 'player_3', 'player_4']
        optimal_result = benchmark_tool.benchmark_function(
            composition_analyzer.identify_optimal_compositions,
            player_pool, {'max_compositions': 5}
        )
        
        # Verify composition analysis performance
        assert analysis_result['success'], f"Composition analysis failed: {analysis_result['error']}"
        assert optimal_result['success'], f"Optimal composition failed: {optimal_result['error']}"
        
        # Performance should be reasonable
        assert analysis_result['wall_time'] < 5.0, \
            f"Composition analysis too slow: {analysis_result['wall_time']}s"
        assert optimal_result['wall_time'] < 15.0, \
            f"Optimal composition too slow: {optimal_result['wall_time']}s"
        
        print(f"\nTeam Composition Analysis Performance:")
        print(f"Analysis: {analysis_result['wall_time']:.3f}s")
        print(f"Optimization: {optimal_result['wall_time']:.3f}s")


class TestAnalyticsStressTests:
    """Stress tests for analytics system under extreme conditions."""
    
    def test_extreme_dataset_size_handling(self):
        """Test handling of extremely large datasets."""
        # Create very large dataset
        num_matches = 50000
        matches = []
        
        for i in range(num_matches):
            match = Mock(spec=Match)
            match.match_id = f"stress_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = [Mock(spec=MatchParticipant) for _ in range(10)]
            matches.append(match)
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Test system under stress
        start_time = time.time()
        
        try:
            result = analytics_engine.analyze_player_performance("stress_player", AnalyticsFilters())
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            result = None
        
        end_time = time.time()
        
        # System should either succeed or fail gracefully
        if success:
            assert result is not None
            # If successful, should complete within reasonable time
            assert end_time - start_time < 60, "Stress test took too long"
        else:
            # If failed, should be a graceful failure with meaningful error
            assert error is not None
            assert "memory" in error.lower() or "timeout" in error.lower() or "size" in error.lower()
    
    def test_rapid_concurrent_requests(self):
        """Test system under rapid concurrent request load."""
        # Create moderate dataset
        dataset = []
        for i in range(1000):
            match = Mock(spec=Match)
            match.match_id = f"concurrent_match_{i}"
            match.participants = [Mock(spec=MatchParticipant) for _ in range(10)]
            dataset.append(match)
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = dataset
        
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, BaselineManager(match_manager), StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Launch many concurrent requests
        import concurrent.futures
        
        def make_request(player_id):
            return analytics_engine.analyze_player_performance(f"player_{player_id}", AnalyticsFilters())
        
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request, i) for i in range(100)]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    if result is not None:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                except Exception:
                    failed_requests += 1
        
        end_time = time.time()
        
        # Verify stress test results
        total_requests = successful_requests + failed_requests
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        # At least 70% of requests should succeed under stress
        assert success_rate >= 0.7, f"Success rate too low under stress: {success_rate:.2%}"
        
        # Should complete within reasonable time
        assert end_time - start_time < 120, f"Stress test took too long: {end_time - start_time}s"
        
        print(f"\nRapid Concurrent Requests Stress Test:")
        print(f"Total requests: {total_requests}")
        print(f"Successful: {successful_requests}")
        print(f"Failed: {failed_requests}")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Total time: {end_time - start_time:.1f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
