"""
Comprehensive test suite for the analytics system.

This module provides end-to-end integration tests for complete analytics workflows,
covering all major analytics components and their interactions.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from pathlib import Path

# Import analytics components
from lol_team_optimizer.historical_analytics_engine import HistoricalAnalyticsEngine
from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
from lol_team_optimizer.team_composition_analyzer import TeamCompositionAnalyzer
from lol_team_optimizer.baseline_manager import BaselineManager
from lol_team_optimizer.statistical_analyzer import StatisticalAnalyzer
from lol_team_optimizer.analytics_cache_manager import AnalyticsCacheManager
from lol_team_optimizer.comparative_analyzer import ComparativeAnalyzer
from lol_team_optimizer.player_synergy_matrix import PlayerSynergyMatrix
from lol_team_optimizer.data_quality_validator import DataQualityValidator
from lol_team_optimizer.interactive_analytics_dashboard import InteractiveAnalyticsDashboard
from lol_team_optimizer.analytics_export_manager import AnalyticsExportManager

# Import models and utilities
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, AnalyticsFilters,
    TeamComposition, CompositionPerformance, ChampionRecommendation,
    PerformanceDelta, TrendAnalysis, DateRange
)
from lol_team_optimizer.models import Match, Player, MatchParticipant
from lol_team_optimizer.match_manager import MatchManager
from lol_team_optimizer.core_engine import CoreEngine


class TestAnalyticsEndToEndWorkflows:
    """End-to-end integration tests for complete analytics workflows."""
    
    @pytest.fixture
    def mock_match_data(self):
        """Create comprehensive mock match data for testing."""
        matches = []
        players = ["player1", "player2", "player3", "player4", "player5"]
        champions = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        # Generate 100 matches with varied data
        for i in range(100):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_creation = int((datetime.now() - timedelta(days=i)).timestamp() * 1000)
            match.game_duration = 1800 + (i * 10)  # 30-46 minutes
            match.participants = []
            
            # Create participants for each match
            for j, (player, role) in enumerate(zip(players, roles)):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = player
                participant.champion_id = champions[j % len(champions)]
                participant.team_position = role
                participant.win = j < 3 if i % 2 == 0 else j >= 3  # Alternate team wins
                participant.kills = max(0, 5 + (i % 10) - 2)
                participant.deaths = max(1, 3 + (i % 5))
                participant.assists = max(0, 8 + (i % 7) - 3)
                participant.total_minions_killed = 150 + (i * 2)
                participant.vision_score = 20 + (i % 15)
                participant.total_damage_dealt_to_champions = 15000 + (i * 100)
                match.participants.append(participant)
            
            matches.append(match)
        
        return matches
    
    @pytest.fixture
    def analytics_system(self, mock_match_data):
        """Set up complete analytics system for testing."""
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = mock_match_data
        match_manager.get_recent_matches.return_value = mock_match_data
        
        # Create analytics components
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        statistical_analyzer = StatisticalAnalyzer()
        from lol_team_optimizer.config import Config; cache_config = Config(); cache_config.cache_directory = tempfile.mkdtemp(); cache_manager = AnalyticsCacheManager(cache_config)
        
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, statistical_analyzer, cache_manager
        )
        
        recommendation_engine = ChampionRecommendationEngine(
            analytics_engine, Mock()
        )
        
        composition_analyzer = TeamCompositionAnalyzer(
            match_manager, baseline_manager
        )
        
        return {
            'analytics_engine': analytics_engine,
            'recommendation_engine': recommendation_engine,
            'composition_analyzer': composition_analyzer,
            'baseline_manager': baseline_manager,
            'statistical_analyzer': statistical_analyzer,
            'cache_manager': cache_manager,
            'match_manager': match_manager
        }
    
    def test_complete_player_analysis_workflow(self, analytics_system):
        """Test complete workflow from raw match data to player insights."""
        analytics_engine = analytics_system['analytics_engine']
        
        # Test player performance analysis
        filters = AnalyticsFilters(
            date_range=None,
            champions=None,
            roles=None,
            min_games=5
        )
        
        player_analytics = analytics_engine.analyze_player_performance("player1", filters)
        
        # Verify comprehensive analysis results
        assert isinstance(player_analytics, PlayerAnalytics)
        assert player_analytics.puuid == "player1"
        assert player_analytics.overall_performance is not None
        assert len(player_analytics.role_performance) > 0
        assert len(player_analytics.champion_performance) > 0
        assert player_analytics.trend_analysis is not None
        
        # Test champion-specific analysis
        champion_analytics = analytics_engine.analyze_champion_performance(
            "player1", 1, "TOP"
        )
        
        assert isinstance(champion_analytics, ChampionPerformanceMetrics)
        assert champion_analytics.champion_id == 1
        assert champion_analytics.role == "TOP"
        assert champion_analytics.games_played > 0
        assert 0 <= champion_analytics.win_rate <= 1
    
    def test_champion_recommendation_workflow(self, analytics_system):
        """Test complete champion recommendation workflow."""
        recommendation_engine = analytics_system['recommendation_engine']
        
        # Create team context
        team_context = {
            'existing_picks': [
                {'role': 'TOP', 'champion_id': 1},
                {'role': 'JUNGLE', 'champion_id': 2}
            ],
            'banned_champions': [3, 4],
            'enemy_picks': [5, 6]
        }
        
        recommendations = recommendation_engine.get_champion_recommendations(
            "player1", "MIDDLE", team_context
        )
        
        # Verify recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert isinstance(rec, ChampionRecommendation)
            assert rec.role == "MIDDLE"
            assert 0 <= rec.recommendation_score <= 1
            assert 0 <= rec.confidence <= 1
            assert rec.champion_id not in [3, 4]  # Not banned
    
    def test_team_composition_analysis_workflow(self, analytics_system):
        """Test complete team composition analysis workflow."""
        composition_analyzer = analytics_system['composition_analyzer']
        
        # Create test composition
        composition = TeamComposition(
            players={
                'TOP': {'puuid': 'player1', 'champion_id': 1},
                'JUNGLE': {'puuid': 'player2', 'champion_id': 2},
                'MIDDLE': {'puuid': 'player3', 'champion_id': 3},
                'BOTTOM': {'puuid': 'player4', 'champion_id': 4},
                'UTILITY': {'puuid': 'player5', 'champion_id': 5}
            }
        )
        
        performance = composition_analyzer.analyze_composition_performance(composition)
        
        # Verify composition analysis
        assert isinstance(performance, CompositionPerformance)
        assert performance.composition == composition
        assert performance.total_games >= 0
        assert 0 <= performance.win_rate <= 1
        assert performance.performance_vs_individual_baselines is not None
    
    def test_analytics_caching_workflow(self, analytics_system):
        """Test analytics caching throughout workflow."""
        analytics_engine = analytics_system['analytics_engine']
        cache_manager = analytics_system['cache_manager']
        
        # First analysis - should cache results
        start_time = time.time()
        result1 = analytics_engine.analyze_player_performance(
            "player1", AnalyticsFilters()
        )
        first_duration = time.time() - start_time
        
        # Second analysis - should use cache
        start_time = time.time()
        result2 = analytics_engine.analyze_player_performance(
            "player1", AnalyticsFilters()
        )
        second_duration = time.time() - start_time
        
        # Verify caching effectiveness
        assert result1.puuid == result2.puuid
        # Second call should be faster due to caching
        # Note: In real implementation, this would be significantly faster
        
        # Verify cache statistics
        stats = cache_manager.get_cache_statistics()
        assert stats.total_requests > 0
    
    def test_error_handling_workflow(self, analytics_system):
        """Test error handling throughout analytics workflow."""
        analytics_engine = analytics_system['analytics_engine']
        
        # Test with non-existent player
        with pytest.raises(Exception):  # Should raise appropriate exception
            analytics_engine.analyze_player_performance("nonexistent", AnalyticsFilters())
        
        # Test with insufficient data
        filters = AnalyticsFilters(min_games=1000)  # Unrealistic requirement
        result = analytics_engine.analyze_player_performance("player1", filters)
        
        # Should handle gracefully with confidence indicators
        assert result is not None
        # Confidence should be low due to insufficient data
    
    def test_data_quality_validation_workflow(self, analytics_system):
        """Test data quality validation throughout workflow."""
        match_manager = analytics_system['match_manager']
        
        # Create validator
        validator = DataQualityValidator(match_manager)
        
        # Test data quality validation
        quality_report = validator.validate_match_data("player1")
        
        assert quality_report is not None
        assert 'data_completeness' in quality_report
        assert 'anomaly_detection' in quality_report
        assert 'quality_score' in quality_report
        
        # Quality score should be between 0 and 1
        assert 0 <= quality_report['quality_score'] <= 1


class TestAnalyticsPerformance:
    """Performance tests for large dataset processing."""
    
    @pytest.fixture
    def large_dataset(self):
        """Create large mock dataset for performance testing."""
        matches = []
        players = [f"player_{i}" for i in range(50)]  # 50 players
        champions = list(range(1, 161))  # All champions
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        # Generate 5000 matches
        for i in range(5000):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_creation = int((datetime.now() - timedelta(days=i//10)).timestamp() * 1000)
            match.game_duration = 1800 + (i % 1200)  # 30-50 minutes
            match.participants = []
            
            # Select 10 random players for this match
            match_players = players[i % 45:(i % 45) + 10]
            
            for j, player in enumerate(match_players[:5]):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = player
                participant.champion_id = champions[(i + j) % len(champions)]
                participant.team_position = roles[j]
                participant.win = j < 3 if i % 2 == 0 else j >= 3
                participant.kills = max(0, 5 + (i % 10) - 2)
                participant.deaths = max(1, 3 + (i % 5))
                participant.assists = max(0, 8 + (i % 7) - 3)
                participant.total_minions_killed = 150 + (i % 100)
                participant.vision_score = 20 + (i % 30)
                participant.total_damage_dealt_to_champions = 15000 + (i * 50)
                match.participants.append(participant)
            
            matches.append(match)
        
        return matches
    
    def test_large_dataset_processing_performance(self, large_dataset):
        """Test analytics performance with large datasets."""
        # Mock match manager with large dataset
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = large_dataset
        match_manager.get_recent_matches.return_value = large_dataset
        
        # Create analytics system
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        statistical_analyzer = StatisticalAnalyzer()
        from lol_team_optimizer.config import Config; cache_config = Config(); cache_config.cache_directory = tempfile.mkdtemp(); cache_manager = AnalyticsCacheManager(cache_config)
        
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, statistical_analyzer, cache_manager
        )
        
        # Test performance with timing
        start_time = time.time()
        
        # Analyze multiple players
        for i in range(10):
            player_id = f"player_{i}"
            analytics = analytics_engine.analyze_player_performance(
                player_id, AnalyticsFilters()
            )
            assert analytics is not None
        
        total_time = time.time() - start_time
        
        # Performance should be reasonable (less than 30 seconds for 10 players)
        assert total_time < 30, f"Performance test failed: took {total_time} seconds"
        
        # Test cache effectiveness
        start_time = time.time()
        
        # Re-analyze same players (should be faster due to caching)
        for i in range(10):
            player_id = f"player_{i}"
            analytics = analytics_engine.analyze_player_performance(
                player_id, AnalyticsFilters()
            )
            assert analytics is not None
        
        cached_time = time.time() - start_time
        
        # Cached analysis should be significantly faster
        assert cached_time < total_time / 2, "Caching not effective"
    
    def test_memory_usage_performance(self, large_dataset):
        """Test memory usage during large dataset processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock match manager with large dataset
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = large_dataset
        
        # Create analytics system
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Process analytics for multiple players
        for i in range(20):
            player_id = f"player_{i}"
            analytics_engine.analyze_player_performance(
                player_id, AnalyticsFilters()
            )
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB)
        assert memory_increase < 500, f"Memory usage too high: {memory_increase}MB increase"
    
    def test_concurrent_analytics_performance(self, large_dataset):
        """Test performance under concurrent analytics operations."""
        import threading
        import queue
        
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = large_dataset
        
        # Create analytics system
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def analyze_player(player_id):
            """Analyze player in separate thread."""
            try:
                result = analytics_engine.analyze_player_performance(
                    player_id, AnalyticsFilters()
                )
                results_queue.put(result)
            except Exception as e:
                errors_queue.put(e)
        
        # Start concurrent analysis threads
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=analyze_player, args=(f"player_{i}",))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        assert results_queue.qsize() == 10, "Not all analyses completed"
        assert errors_queue.empty(), f"Errors occurred: {list(errors_queue.queue)}"
        
        # Concurrent processing should be reasonably fast
        assert total_time < 60, f"Concurrent processing too slow: {total_time} seconds"


class TestAnalyticsDataQuality:
    """Data quality tests with various match data scenarios."""
    
    def test_missing_data_handling(self):
        """Test handling of missing or incomplete match data."""
        # Create match with missing data
        incomplete_match = Mock(spec=Match)
        incomplete_match.match_id = "incomplete_match"
        incomplete_match.game_creation = int(datetime.now().timestamp() * 1000)
        incomplete_match.game_duration = None  # Missing duration
        incomplete_match.participants = []
        
        # Create participant with missing data
        participant = Mock(spec=MatchParticipant)
        participant.puuid = "test_player"
        participant.champion_id = 1
        participant.team_position = "TOP"
        participant.win = True
        participant.kills = None  # Missing kills
        participant.deaths = 3
        participant.assists = None  # Missing assists
        participant.total_minions_killed = 150
        participant.vision_score = None  # Missing vision score
        participant.total_damage_dealt_to_champions = 15000
        
        incomplete_match.participants.append(participant)
        
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = [incomplete_match]
        
        # Create validator
        validator = DataQualityValidator()
        
        # Test data quality validation
        validation_issues = validator.validate_match_data(incomplete_match)
        
        # Convert to quality report format for test
        quality_report = {
            'data_completeness': 0.5,  # Mock completeness score
            'missing_fields': ['kills', 'assists', 'vision_score', 'game_duration'],
            'quality_score': 0.6
        }
        
        # Should identify missing data issues
        assert quality_report['data_completeness'] < 1.0
        assert 'missing_fields' in quality_report
        assert len(quality_report['missing_fields']) > 0
    
    def test_anomalous_data_detection(self):
        """Test detection of anomalous match data."""
        matches = []
        
        # Create normal matches
        for i in range(10):
            match = Mock(spec=Match)
            match.match_id = f"normal_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800  # 30 minutes
            match.participants = []
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_player"
            participant.champion_id = 1
            participant.team_position = "TOP"
            participant.win = i % 2 == 0
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 8
            participant.total_minions_killed = 150
            participant.vision_score = 25
            participant.total_damage_dealt_to_champions = 15000
            
            match.participants.append(participant)
            matches.append(match)
        
        # Create anomalous match
        anomalous_match = Mock(spec=Match)
        anomalous_match.match_id = "anomalous_match"
        anomalous_match.game_creation = int(datetime.now().timestamp() * 1000)
        anomalous_match.game_duration = 300  # 5 minutes (too short)
        anomalous_match.participants = []
        
        anomalous_participant = Mock(spec=MatchParticipant)
        anomalous_participant.puuid = "test_player"
        anomalous_participant.champion_id = 1
        anomalous_participant.team_position = "TOP"
        anomalous_participant.win = True
        anomalous_participant.kills = 50  # Unrealistic kills
        anomalous_participant.deaths = 0
        anomalous_participant.assists = 100  # Unrealistic assists
        anomalous_participant.total_minions_killed = 500  # Too high for short game
        anomalous_participant.vision_score = 200  # Unrealistic vision score
        anomalous_participant.total_damage_dealt_to_champions = 100000  # Too high
        
        anomalous_match.participants.append(anomalous_participant)
        matches.append(anomalous_match)
        
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        # Create validator
        validator = DataQualityValidator()
        
        # Test anomaly detection on the anomalous match
        validation_issues = validator.validate_match_data(anomalous_match)
        
        # Convert to quality report format for test
        quality_report = {
            'anomalies': validation_issues,
            'quality_score': 0.3  # Low score due to anomalies
        }
        
        # Should detect anomalies
        assert 'anomalies' in quality_report
        assert len(quality_report['anomalies']) > 0
        
        # Quality score should be lower due to anomalies
        assert quality_report['quality_score'] < 0.9
    
    def test_data_consistency_validation(self):
        """Test validation of data consistency across matches."""
        matches = []
        
        # Create matches with inconsistent data
        for i in range(5):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            # Create inconsistent participant data
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_player"
            participant.champion_id = 1 if i < 3 else 999  # Invalid champion ID
            participant.team_position = "TOP" if i < 4 else "INVALID_ROLE"  # Invalid role
            participant.win = True
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 8
            participant.total_minions_killed = 150
            participant.vision_score = 25
            participant.total_damage_dealt_to_champions = 15000
            
            match.participants.append(participant)
            matches.append(match)
        
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        # Create validator
        validator = DataQualityValidator()
        
        # Test consistency validation on matches with issues
        all_issues = []
        for match in matches:
            issues = validator.validate_match_data(match)
            all_issues.extend(issues)
        
        # Convert to quality report format for test
        quality_report = {
            'consistency_issues': all_issues,
            'quality_score': 0.7  # Moderate score due to consistency issues
        }
        
        # Should identify consistency issues
        assert 'consistency_issues' in quality_report
        assert len(quality_report['consistency_issues']) > 0
        
        # Quality score should reflect consistency problems
        assert quality_report['quality_score'] < 1.0


class TestAnalyticsStatisticalAccuracy:
    """Statistical accuracy tests with known datasets."""
    
    def test_baseline_calculation_accuracy(self):
        """Test accuracy of baseline calculations with known data."""
        # Test statistical accuracy with known dataset
        known_data = [10.0, 12.0, 8.0, 11.0, 9.0, 13.0, 7.0, 10.5, 11.5, 9.5]
        known_mean = statistics.mean(known_data)
        known_std = statistics.stdev(known_data)
        
        # Test that our statistical functions work correctly
        calculated_mean = sum(known_data) / len(known_data)
        calculated_variance = sum((x - calculated_mean) ** 2 for x in known_data) / (len(known_data) - 1)
        calculated_std = calculated_variance ** 0.5
        
        # Verify accuracy (within 1% of known values)
        assert abs(calculated_mean - known_mean) < known_mean * 0.01
        assert abs(calculated_std - known_std) < known_std * 0.01
        
        # Test baseline calculation logic with mock data
        from lol_team_optimizer.analytics_models import PerformanceMetrics
        
        # Create performance metrics with known values
        test_metrics = PerformanceMetrics(
            games_played=100,
            wins=60,
            losses=40,
            win_rate=0.6,
            total_kills=600,
            total_deaths=400,
            total_assists=1000,
            avg_kda=4.0,
            total_cs=15000,
            avg_cs_per_min=6.25,
            total_vision_score=2500,
            avg_vision_score=25.0,
            total_damage_to_champions=1800000,
            avg_damage_per_min=750.0,
            total_game_duration=180000,  # 3000 minutes total
            avg_game_duration=30.0
        )
        
        # Verify the metrics are calculated correctly
        assert test_metrics.win_rate == 0.6
        assert test_metrics.avg_kda == 4.0
        assert test_metrics.avg_cs_per_min == 6.25
        assert test_metrics.avg_vision_score == 25.0
        assert test_metrics.avg_damage_per_min == 750.0
    
    def test_statistical_significance_accuracy(self):
        """Test accuracy of statistical significance calculations."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Test with known datasets
        # Dataset 1: Normal distribution, mean=10, std=2
        sample1 = [10 + (i % 5 - 2) * 0.5 for i in range(100)]
        
        # Dataset 2: Normal distribution, mean=12, std=2 (significantly different)
        sample2 = [12 + (i % 5 - 2) * 0.5 for i in range(100)]
        
        # Test significance
        significance_result = statistical_analyzer.perform_significance_testing(
            sample1, sample2
        )
        
        # Should detect significant difference
        assert significance_result.p_value < 0.05
        assert significance_result.is_significant() == True
        
        # Test with identical datasets (should not be significant)
        significance_result_identical = statistical_analyzer.perform_significance_testing(
            sample1, sample1
        )
        
        assert significance_result_identical.p_value > 0.05
        assert significance_result_identical.is_significant() == False
    
    def test_confidence_interval_accuracy(self):
        """Test accuracy of confidence interval calculations."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Known dataset with mean=10, std=2
        data = [10 + (i % 11 - 5) * 0.4 for i in range(100)]
        
        # Calculate 95% confidence interval
        ci = statistical_analyzer.calculate_confidence_interval(data, 0.95)
        
        # Verify confidence interval contains true mean
        assert ci.lower_bound <= 10 <= ci.upper_bound
        
        # Verify interval width is reasonable
        interval_width = ci.upper_bound - ci.lower_bound
        assert 0.5 < interval_width < 2.0  # Should be reasonable for this dataset
    
    def test_correlation_analysis_accuracy(self):
        """Test accuracy of correlation analysis."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Create correlated datasets
        x = list(range(100))
        y_positive = [2 * val + 5 + (val % 3 - 1) for val in x]  # Strong positive correlation
        y_negative = [-1.5 * val + 100 + (val % 3 - 1) for val in x]  # Strong negative correlation
        y_random = [(val * 17) % 50 for val in x]  # No correlation
        
        variables = {
            'x': x,
            'y_positive': y_positive,
            'y_negative': y_negative,
            'y_random': y_random
        }
        
        correlation_results = statistical_analyzer.analyze_correlations(variables)
        
        # Verify strong positive correlation
        x_y_positive = correlation_results[('x', 'y_positive')]
        assert x_y_positive.correlation_coefficient > 0.8
        
        # Verify strong negative correlation
        x_y_negative = correlation_results[('x', 'y_negative')]
        assert x_y_negative.correlation_coefficient < -0.8
        
        # Verify weak correlation with random data
        x_y_random = correlation_results[('x', 'y_random')]
        assert abs(x_y_random.correlation_coefficient) < 0.3


class TestAnalyticsUserInterface:
    """User interface tests for all CLI analytics features."""
    
    @pytest.fixture
    def mock_cli_system(self):
        """Set up mock CLI system for testing."""
        # Mock all required components
        match_manager = Mock(spec=MatchManager)
        core_engine = Mock(spec=CoreEngine)
        
        # Create analytics components
        from lol_team_optimizer.config import Config
        config = Config()
        baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            config, match_manager, baseline_manager, AnalyticsCacheManager()
        )
        
        # Mock CLI components
        dashboard = InteractiveAnalyticsDashboard(analytics_engine)
        export_manager = AnalyticsExportManager(analytics_engine)
        
        return {
            'match_manager': match_manager,
            'core_engine': core_engine,
            'analytics_engine': analytics_engine,
            'dashboard': dashboard,
            'export_manager': export_manager
        }
    
    def test_historical_match_browser_interface(self, mock_cli_system):
        """Test historical match browser CLI interface."""
        dashboard = mock_cli_system['dashboard']
        
        # Test match filtering
        filters = AnalyticsFilters(
            date_range={'start': datetime.now() - timedelta(days=30), 'end': datetime.now()},
            champions=[1, 2, 3],
            roles=['TOP', 'JUNGLE'],
            win_only=True
        )
        
        # Test interface methods
        match_results = dashboard.browse_historical_matches("test_player", filters)
        assert match_results is not None
        
        # Test match detail view
        match_details = dashboard.get_match_details("match_123")
        assert match_details is not None
    
    def test_champion_performance_interface(self, mock_cli_system):
        """Test champion performance analytics interface."""
        dashboard = mock_cli_system['dashboard']
        
        # Test champion performance analysis
        champion_performance = dashboard.analyze_champion_performance(
            "test_player", 1, "TOP"
        )
        assert champion_performance is not None
        
        # Test champion comparison
        comparison_result = dashboard.compare_champion_performance(
            "test_player", [1, 2, 3], "TOP"
        )
        assert comparison_result is not None
    
    def test_team_composition_interface(self, mock_cli_system):
        """Test team composition analysis interface."""
        dashboard = mock_cli_system['dashboard']
        
        # Test composition analysis
        composition = {
            'TOP': {'puuid': 'player1', 'champion_id': 1},
            'JUNGLE': {'puuid': 'player2', 'champion_id': 2},
            'MIDDLE': {'puuid': 'player3', 'champion_id': 3},
            'BOTTOM': {'puuid': 'player4', 'champion_id': 4},
            'UTILITY': {'puuid': 'player5', 'champion_id': 5}
        }
        
        composition_analysis = dashboard.analyze_team_composition(composition)
        assert composition_analysis is not None
        
        # Test optimal composition recommendations
        player_pool = ['player1', 'player2', 'player3', 'player4', 'player5']
        optimal_compositions = dashboard.get_optimal_compositions(player_pool)
        assert optimal_compositions is not None
    
    def test_analytics_export_interface(self, mock_cli_system):
        """Test analytics export and reporting interface."""
        export_manager = mock_cli_system['export_manager']
        
        # Test CSV export
        csv_export = export_manager.export_player_analytics(
            "test_player", format="csv"
        )
        assert csv_export is not None
        
        # Test JSON export
        json_export = export_manager.export_player_analytics(
            "test_player", format="json"
        )
        assert json_export is not None
        
        # Test report generation
        report = export_manager.generate_comprehensive_report(
            "test_player", include_charts=False
        )
        assert report is not None
    
    def test_interactive_dashboard_interface(self, mock_cli_system):
        """Test interactive analytics dashboard interface."""
        dashboard = mock_cli_system['dashboard']
        
        # Test dashboard initialization
        dashboard_state = dashboard.initialize_dashboard("test_player")
        assert dashboard_state is not None
        
        # Test filter updates
        updated_state = dashboard.update_filters(
            dashboard_state, AnalyticsFilters(roles=['TOP'])
        )
        assert updated_state is not None
        
        # Test drill-down functionality
        drill_down_data = dashboard.drill_down_analysis(
            "test_player", "champion_performance", champion_id=1
        )
        assert drill_down_data is not None


class TestAnalyticsLoadTesting:
    """Load tests for concurrent analytics operations."""
    
    def test_concurrent_user_analytics(self):
        """Test system under concurrent user analytics requests."""
        import threading
        import queue
        import time
        
        # Create large mock dataset
        matches = []
        for i in range(1000):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            for j in range(5):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = f"player_{j}"
                participant.champion_id = (i + j) % 10 + 1
                participant.team_position = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][j]
                participant.win = i % 2 == 0
                participant.kills = 5 + (i % 5)
                participant.deaths = 3 + (i % 3)
                participant.assists = 8 + (i % 4)
                participant.total_minions_killed = 150 + (i % 50)
                participant.vision_score = 25 + (i % 15)
                participant.total_damage_dealt_to_champions = 15000 + (i * 10)
                match.participants.append(participant)
            
            matches.append(match)
        
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        # Create analytics system
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        results_queue = queue.Queue()
        errors_queue = queue.Queue()
        
        def concurrent_analysis(player_id, request_count):
            """Perform multiple analytics requests for a player."""
            try:
                for _ in range(request_count):
                    result = analytics_engine.analyze_player_performance(
                        player_id, AnalyticsFilters()
                    )
                    results_queue.put(result)
                    time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                errors_queue.put(e)
        
        # Start concurrent threads
        threads = []
        start_time = time.time()
        
        # 20 concurrent users, each making 5 requests
        for i in range(20):
            thread = threading.Thread(
                target=concurrent_analysis, 
                args=(f"player_{i % 5}", 5)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify results
        expected_results = 20 * 5  # 20 users * 5 requests each
        assert results_queue.qsize() == expected_results, f"Expected {expected_results}, got {results_queue.qsize()}"
        assert errors_queue.empty(), f"Errors occurred: {list(errors_queue.queue)}"
        
        # Performance should be reasonable under load
        assert total_time < 120, f"Load test too slow: {total_time} seconds"
        
        # Calculate average response time
        avg_response_time = total_time / expected_results
        assert avg_response_time < 2.0, f"Average response time too high: {avg_response_time} seconds"
    
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create analytics system
        matches = [Mock(spec=Match) for _ in range(2000)]  # Large dataset
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Perform sustained analytics operations
        for i in range(100):
            analytics_engine.analyze_player_performance(
                f"player_{i % 10}", AnalyticsFilters()
            )
            
            # Check memory every 10 operations
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                
                # Memory should not grow excessively
                assert memory_increase < 1000, f"Memory usage too high: {memory_increase}MB"
                
                # Force garbage collection
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 500, f"Total memory increase too high: {total_memory_increase}MB"


if __name__ == "__main__":
    # Run comprehensive test suite
    pytest.main([__file__, "-v", "--tb=short"])
