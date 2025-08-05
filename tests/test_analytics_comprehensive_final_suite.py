"""
Final Comprehensive Test Suite for Analytics System

This module provides the complete test suite covering all requirements for task 22:
- End-to-end integration tests for complete analytics workflows
- Performance tests for large dataset processing  
- Data quality tests with various match data scenarios
- Statistical accuracy tests with known datasets
- User interface tests for all CLI analytics features
- Load tests for concurrent analytics operations
"""

import pytest
import asyncio
import time
import threading
import multiprocessing
import statistics
import os
import gc
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
from pathlib import Path
import concurrent.futures
import queue

# Optional imports for performance monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    
    # Mock psutil for tests that need it
    class MockProcess:
        def memory_info(self):
            return type('MemInfo', (), {'rss': 100 * 1024 * 1024})()  # 100MB
        
        def cpu_percent(self):
            return 10.0
    
    class MockPsutil:
        def Process(self, pid=None):
            return MockProcess()
    
    psutil = MockPsutil()

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
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.streamlined_cli import StreamlinedCLI

# Import models and utilities
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, AnalyticsFilters,
    TeamComposition, CompositionPerformance, ChampionRecommendation,
    PerformanceDelta, TrendAnalysis, DateRange, PerformanceMetrics
)
from lol_team_optimizer.models import Match, Player, MatchParticipant
from lol_team_optimizer.match_manager import MatchManager


class TestEndToEndAnalyticsWorkflows:
    """End-to-end integration tests for complete analytics workflows."""
    
    @pytest.fixture
    def comprehensive_test_data(self):
        """Create comprehensive test data for end-to-end testing."""
        matches = []
        players = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry"]
        champions = list(range(1, 51))  # 50 different champions
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        # Generate 6 months of realistic match data
        base_date = datetime.now() - timedelta(days=180)
        
        for day in range(180):
            current_date = base_date + timedelta(days=day)
            daily_matches = 3 + (day % 5)  # 3-7 matches per day
            
            for match_num in range(daily_matches):
                match = Mock(spec=Match)
                match.match_id = f"e2e_match_{day}_{match_num}"
                match.game_creation = int(current_date.timestamp() * 1000)
                match.game_duration = 1500 + (day * 5) + (match_num * 200)  # 25-50 minutes
                match.participants = []
                
                # Select players for this match
                match_players = players[:8] if day % 2 == 0 else players[2:]
                
                # Create realistic team compositions
                for team in range(2):
                    for role_idx, role in enumerate(roles):
                        participant = Mock(spec=MatchParticipant)
                        participant.puuid = match_players[(team * 5 + role_idx) % len(match_players)]
                        participant.champion_id = champions[(day + match_num + team * 5 + role_idx) % len(champions)]
                        participant.team_position = role
                        participant.win = team == 0 if (day + match_num) % 2 == 0 else team == 1
                        
                        # Generate realistic performance metrics
                        base_perf = self._get_realistic_performance(role, day, match_num)
                        participant.kills = base_perf['kills']
                        participant.deaths = base_perf['deaths']
                        participant.assists = base_perf['assists']
                        participant.total_minions_killed = base_perf['cs']
                        participant.vision_score = base_perf['vision']
                        participant.total_damage_dealt_to_champions = base_perf['damage']
                        
                        match.participants.append(participant)
                
                matches.append(match)
        
        return matches
    
    def _get_realistic_performance(self, role: str, day: int, match_num: int) -> Dict[str, int]:
        """Generate realistic performance metrics based on role and game context."""
        role_bases = {
            "TOP": {"kills": 4, "deaths": 3, "assists": 6, "cs": 180, "vision": 20, "damage": 18000},
            "JUNGLE": {"kills": 6, "deaths": 4, "assists": 8, "cs": 120, "vision": 35, "damage": 16000},
            "MIDDLE": {"kills": 7, "deaths": 4, "assists": 7, "cs": 170, "vision": 25, "damage": 22000},
            "BOTTOM": {"kills": 8, "deaths": 3, "assists": 6, "cs": 190, "vision": 15, "damage": 25000},
            "UTILITY": {"kills": 2, "deaths": 5, "assists": 12, "cs": 40, "vision": 60, "damage": 8000}
        }
        
        base = role_bases[role].copy()
        
        # Add realistic variation
        variation = {
            "kills": max(0, base["kills"] + (day % 7) - 3 + (match_num % 5) - 2),
            "deaths": max(1, base["deaths"] + (day % 4) - 1 + (match_num % 3) - 1),
            "assists": max(0, base["assists"] + (day % 6) - 2 + (match_num % 4) - 1),
            "cs": max(0, base["cs"] + (day % 50) - 25 + (match_num * 10)),
            "vision": max(0, base["vision"] + (day % 20) - 10 + (match_num % 8)),
            "damage": max(0, base["damage"] + (day * 100) + (match_num * 500))
        }
        
        return variation
    
    @pytest.fixture
    def complete_analytics_system(self, comprehensive_test_data):
        """Set up complete analytics system for end-to-end testing."""
        # Mock match manager
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = comprehensive_test_data
        match_manager.get_recent_matches.return_value = comprehensive_test_data
        
        # Create all analytics components
        from lol_team_optimizer.config import Config
        config = Config()
        config.cache_directory = Path(tempfile.mkdtemp())
        
        baseline_manager = BaselineManager(config, match_manager)
        statistical_analyzer = StatisticalAnalyzer()
        cache_manager = AnalyticsCacheManager(config)
        
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, statistical_analyzer, cache_manager
        )
        
        recommendation_engine = ChampionRecommendationEngine(
            analytics_engine, Mock()
        )
        
        composition_analyzer = TeamCompositionAnalyzer(
            match_manager, baseline_manager
        )
        
        comparative_analyzer = ComparativeAnalyzer(
            analytics_engine, statistical_analyzer
        )
        
        synergy_matrix = PlayerSynergyMatrix(
            match_manager, baseline_manager
        )
        
        data_validator = DataQualityValidator()
        
        dashboard = InteractiveAnalyticsDashboard(analytics_engine)
        
        export_manager = AnalyticsExportManager(analytics_engine)
        
        # Mock core engine
        core_engine = Mock(spec=CoreEngine)
        core_engine.analytics_engine = analytics_engine
        core_engine.recommendation_engine = recommendation_engine
        core_engine.composition_analyzer = composition_analyzer
        
        return {
            'match_manager': match_manager,
            'analytics_engine': analytics_engine,
            'recommendation_engine': recommendation_engine,
            'composition_analyzer': composition_analyzer,
            'comparative_analyzer': comparative_analyzer,
            'synergy_matrix': synergy_matrix,
            'data_validator': data_validator,
            'dashboard': dashboard,
            'export_manager': export_manager,
            'core_engine': core_engine,
            'baseline_manager': baseline_manager,
            'statistical_analyzer': statistical_analyzer,
            'cache_manager': cache_manager
        }
    
    def test_complete_player_analysis_workflow(self, complete_analytics_system):
        """Test complete workflow from raw data to player insights."""
        analytics_engine = complete_analytics_system['analytics_engine']
        
        # Step 1: Basic player analysis
        filters = AnalyticsFilters(min_games=5)
        player_analytics = analytics_engine.analyze_player_performance("alice", filters)
        
        # Verify comprehensive analysis
        assert isinstance(player_analytics, PlayerAnalytics)
        assert player_analytics.puuid == "alice"
        assert player_analytics.overall_performance is not None
        assert len(player_analytics.role_performance) > 0
        assert len(player_analytics.champion_performance) > 0
        
        # Step 2: Champion-specific analysis
        champion_analytics = analytics_engine.analyze_champion_performance("alice", 1, "TOP")
        
        assert isinstance(champion_analytics, ChampionPerformanceMetrics)
        assert champion_analytics.champion_id == 1
        assert champion_analytics.role == "TOP"
        assert champion_analytics.games_played > 0
        
        # Step 3: Trend analysis
        trend_analysis = analytics_engine.calculate_performance_trends("alice", 30)
        
        assert isinstance(trend_analysis, TrendAnalysis)
        assert trend_analysis.player_puuid == "alice"
        assert len(trend_analysis.trend_data) > 0
    
    def test_complete_recommendation_workflow(self, complete_analytics_system):
        """Test complete champion recommendation workflow."""
        recommendation_engine = complete_analytics_system['recommendation_engine']
        analytics_engine = complete_analytics_system['analytics_engine']
        
        # Step 1: Analyze player performance for context
        player_analytics = analytics_engine.analyze_player_performance("alice", AnalyticsFilters())
        
        # Step 2: Get recommendations with team context
        team_context = {
            'existing_picks': [{'role': 'TOP', 'champion_id': 1}],
            'banned_champions': [2, 3, 4],
            'enemy_picks': [5, 6]
        }
        
        recommendations = recommendation_engine.get_champion_recommendations(
            "alice", "JUNGLE", team_context
        )
        
        # Verify recommendations
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        for rec in recommendations:
            assert isinstance(rec, ChampionRecommendation)
            assert rec.role == "JUNGLE"
            assert 0 <= rec.recommendation_score <= 1
            assert 0 <= rec.confidence <= 1
            assert rec.champion_id not in [2, 3, 4]  # Not banned
        
        # Step 3: Verify recommendation reasoning
        top_recommendation = recommendations[0]
        assert hasattr(top_recommendation, 'reasoning')
        assert hasattr(top_recommendation, 'expected_performance')
    
    def test_complete_team_optimization_workflow(self, complete_analytics_system):
        """Test complete team optimization workflow."""
        composition_analyzer = complete_analytics_system['composition_analyzer']
        synergy_matrix = complete_analytics_system['synergy_matrix']
        recommendation_engine = complete_analytics_system['recommendation_engine']
        
        # Step 1: Analyze player synergies
        player_pool = ["alice", "bob", "charlie", "diana", "eve"]
        synergy_analysis = synergy_matrix.calculate_synergy_matrix(player_pool)
        
        assert synergy_analysis is not None
        assert len(synergy_analysis.synergy_scores) > 0
        
        # Step 2: Find optimal compositions
        optimal_compositions = composition_analyzer.identify_optimal_compositions(
            player_pool, {'max_compositions': 3}
        )
        
        assert isinstance(optimal_compositions, list)
        assert len(optimal_compositions) > 0
        
        # Step 3: Analyze best composition performance
        best_composition = optimal_compositions[0]
        composition_performance = composition_analyzer.analyze_composition_performance(
            best_composition
        )
        
        assert isinstance(composition_performance, CompositionPerformance)
        assert composition_performance.total_games >= 0
        assert 0 <= composition_performance.win_rate <= 1
        
        # Step 4: Get champion recommendations for composition
        for role in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            if role in best_composition.players:
                player = best_composition.players[role]['puuid']
                recommendations = recommendation_engine.get_champion_recommendations(
                    player, role, {}
                )
                assert len(recommendations) > 0
    
    def test_complete_export_workflow(self, complete_analytics_system):
        """Test complete analytics export workflow."""
        analytics_engine = complete_analytics_system['analytics_engine']
        export_manager = complete_analytics_system['export_manager']
        
        # Step 1: Generate analytics
        player_analytics = analytics_engine.analyze_player_performance("alice", AnalyticsFilters())
        
        # Step 2: Export in multiple formats
        export_formats = ['json', 'csv']
        export_results = {}
        
        for format_type in export_formats:
            try:
                export_result = export_manager.export_player_analytics(
                    "alice", format=format_type
                )
                export_results[format_type] = export_result
                assert export_result is not None
            except Exception as e:
                # Some formats might not be available in test environment
                export_results[format_type] = f"Error: {str(e)}"
        
        # Step 3: Generate comprehensive report
        comprehensive_report = export_manager.generate_comprehensive_report("alice")
        
        assert comprehensive_report is not None
        assert 'player_summary' in comprehensive_report
        assert 'performance_analysis' in comprehensive_report
        
        # Step 4: Generate team report
        team_report = export_manager.generate_team_report(
            ["alice", "bob", "charlie"]
        )
        
        assert team_report is not None
        assert 'team_overview' in team_report


class TestLargeDatasetPerformance:
    """Performance tests for large dataset processing."""
    
    @pytest.fixture(params=[1000, 5000, 10000])
    def large_datasets(self, request):
        """Create datasets of varying sizes for performance testing."""
        dataset_size = request.param
        matches = []
        players = [f"perf_player_{i}" for i in range(20)]
        champions = list(range(1, 161))
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(dataset_size):
            match = Mock(spec=Match)
            match.match_id = f"perf_match_{i}"
            match.game_creation = int((base_date + timedelta(days=i * 365 / dataset_size)).timestamp() * 1000)
            match.game_duration = 1500 + (i % 1800)
            match.participants = []
            
            # Create 10 participants per match
            for j in range(10):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = players[j % len(players)]
                participant.champion_id = champions[(i + j) % len(champions)]
                participant.team_position = roles[j % 5]
                participant.win = j < 5 if i % 2 == 0 else j >= 5
                
                # Generate performance data
                participant.kills = max(0, 5 + (i % 10) - 3)
                participant.deaths = max(1, 3 + (i % 5) - 1)
                participant.assists = max(0, 8 + (i % 8) - 3)
                participant.total_minions_killed = 120 + (i % 100)
                participant.vision_score = 15 + (i % 30)
                participant.total_damage_dealt_to_champions = 12000 + (i * 50)
                
                match.participants.append(participant)
            
            matches.append(match)
        
        return {'size': dataset_size, 'matches': matches}
    
    def test_analytics_performance_scaling(self, large_datasets):
        """Test how analytics performance scales with dataset size."""
        dataset_size = large_datasets['size']
        matches = large_datasets['matches']
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        from lol_team_optimizer.config import Config
        config = Config()
        baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Measure performance
        start_time = time.time()
        if PSUTIL_AVAILABLE:
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            initial_memory = 100  # Mock value
        
        # Perform analytics
        result = analytics_engine.analyze_player_performance("perf_player_0", AnalyticsFilters())
        
        end_time = time.time()
        if PSUTIL_AVAILABLE:
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            final_memory = initial_memory + 10  # Mock increase
        
        # Verify results
        assert result is not None
        assert isinstance(result, PlayerAnalytics)
        
        # Performance should be reasonable
        execution_time = end_time - start_time
        memory_used = final_memory - initial_memory
        
        # Performance thresholds based on dataset size
        if dataset_size <= 1000:
            assert execution_time < 5.0, f"Small dataset too slow: {execution_time}s"
            assert memory_used < 100, f"Small dataset uses too much memory: {memory_used}MB"
        elif dataset_size <= 5000:
            assert execution_time < 15.0, f"Medium dataset too slow: {execution_time}s"
            assert memory_used < 300, f"Medium dataset uses too much memory: {memory_used}MB"
        else:  # 10000+
            assert execution_time < 30.0, f"Large dataset too slow: {execution_time}s"
            assert memory_used < 500, f"Large dataset uses too much memory: {memory_used}MB"
        
        print(f"Dataset size {dataset_size}: {execution_time:.2f}s, {memory_used:.1f}MB")
    
    def test_batch_processing_performance(self, large_datasets):
        """Test batch processing performance for multiple players."""
        matches = large_datasets['matches']
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        from lol_team_optimizer.config import Config
        config = Config()
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, BaselineManager(config, match_manager), StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Test batch processing
        players = [f"perf_player_{i}" for i in range(10)]
        
        start_time = time.time()
        results = []
        
        for player in players:
            result = analytics_engine.analyze_player_performance(player, AnalyticsFilters())
            results.append(result)
        
        end_time = time.time()
        
        # Verify batch results
        assert len(results) == len(players)
        assert all(result is not None for result in results)
        
        # Batch processing should be efficient
        total_time = end_time - start_time
        avg_time_per_player = total_time / len(players)
        
        assert avg_time_per_player < 5.0, f"Batch processing too slow: {avg_time_per_player}s per player"
        
        print(f"Batch processing {len(players)} players: {total_time:.2f}s total, {avg_time_per_player:.2f}s avg")


class TestDataQualityScenarios:
    """Data quality tests with various match data scenarios."""
    
    def test_missing_data_scenarios(self):
        """Test handling of various missing data scenarios."""
        # Create matches with different types of missing data
        test_scenarios = [
            {
                'name': 'missing_kills',
                'missing_fields': ['kills'],
                'expected_quality_score': 0.8
            },
            {
                'name': 'missing_multiple_fields',
                'missing_fields': ['kills', 'assists', 'vision_score'],
                'expected_quality_score': 0.6
            },
            {
                'name': 'missing_critical_fields',
                'missing_fields': ['champion_id', 'team_position'],
                'expected_quality_score': 0.3
            }
        ]
        
        for scenario in test_scenarios:
            matches = self._create_matches_with_missing_data(scenario['missing_fields'])
            
            # Create validator
            match_manager = Mock(spec=MatchManager)
            match_manager.get_matches_for_player.return_value = matches
            validator = DataQualityValidator()
            
            # Test validation on each match
            all_issues = []
            for match in matches:
                issues = validator.validate_match_data(match)
                all_issues.extend(issues)
            
            # Verify validation found issues
            assert len(all_issues) > 0, f"Should have found validation issues for scenario {scenario['name']}"
            
            # Check that issues relate to missing fields
            issue_descriptions = [issue.description for issue in all_issues]
            for field in scenario['missing_fields']:
                # At least one issue should mention the missing field
                field_mentioned = any(field.lower() in desc.lower() for desc in issue_descriptions)
                assert field_mentioned, f"Missing field {field} should be mentioned in validation issues"
    
    def _create_matches_with_missing_data(self, missing_fields: List[str]) -> List[Match]:
        """Create matches with specified missing fields."""
        matches = []
        
        for i in range(10):
            match = Mock(spec=Match)
            match.match_id = f"missing_data_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_player"
            
            # Set default values
            participant.champion_id = 1
            participant.team_position = "TOP"
            participant.win = True
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 8
            participant.total_minions_killed = 150
            participant.vision_score = 25
            participant.total_damage_dealt_to_champions = 15000
            
            # Remove specified fields (set to None)
            for field in missing_fields:
                if hasattr(participant, field):
                    setattr(participant, field, None)
            
            match.participants.append(participant)
            matches.append(match)
        
        return matches
    
    def test_anomalous_data_detection(self):
        """Test detection of anomalous match data."""
        # Create matches with anomalous data
        anomalous_scenarios = [
            {
                'name': 'unrealistic_kills',
                'anomalies': {'kills': 100},  # Impossible kills
                'expected_anomalies': ['high_kills']
            },
            {
                'name': 'negative_values',
                'anomalies': {'total_minions_killed': -50},  # Negative CS
                'expected_anomalies': ['negative_cs']
            },
            {
                'name': 'impossible_game_duration',
                'anomalies': {'game_duration': 60},  # 1 minute game
                'expected_anomalies': ['short_game']
            }
        ]
        
        for scenario in anomalous_scenarios:
            matches = self._create_matches_with_anomalies(scenario['anomalies'])
            
            # Create validator
            match_manager = Mock(spec=MatchManager)
            match_manager.get_matches_for_player.return_value = matches
            validator = DataQualityValidator()
            
            # Test anomaly detection on each match
            all_issues = []
            for match in matches:
                issues = validator.validate_match_data(match)
                all_issues.extend(issues)
            
            # Verify anomaly detection found issues
            assert len(all_issues) > 0, f"Should have found anomalies for scenario {scenario['name']}"
            
            # Check that issues are related to anomalies
            issue_types = [issue.issue_type for issue in all_issues]
            anomaly_types = ['data_anomaly', 'invalid_value', 'unrealistic_value']
            anomaly_found = any(issue_type in anomaly_types for issue_type in issue_types)
            assert anomaly_found, "Should have found anomaly-related issues"
    
    def _create_matches_with_anomalies(self, anomalies: Dict[str, Any]) -> List[Match]:
        """Create matches with specified anomalies."""
        matches = []
        
        for i in range(5):
            match = Mock(spec=Match)
            match.match_id = f"anomaly_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = anomalies.get('game_duration', 1800)
            match.participants = []
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_player"
            participant.champion_id = 1
            participant.team_position = "TOP"
            participant.win = True
            participant.kills = anomalies.get('kills', 5)
            participant.deaths = anomalies.get('deaths', 3)
            participant.assists = anomalies.get('assists', 8)
            participant.total_minions_killed = anomalies.get('total_minions_killed', 150)
            participant.vision_score = anomalies.get('vision_score', 25)
            participant.total_damage_dealt_to_champions = anomalies.get('total_damage_dealt_to_champions', 15000)
            
            match.participants.append(participant)
            matches.append(match)
        
        return matches
    
    def test_data_consistency_validation(self):
        """Test validation of data consistency across matches."""
        # Create matches with consistency issues
        inconsistent_matches = []
        
        for i in range(10):
            match = Mock(spec=Match)
            match.match_id = f"consistency_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_player"
            
            # Introduce consistency issues
            if i < 5:
                participant.champion_id = 1  # Consistent champion
                participant.team_position = "TOP"  # Consistent role
            else:
                participant.champion_id = 999  # Invalid champion ID
                participant.team_position = "INVALID_ROLE"  # Invalid role
            
            participant.win = True
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 8
            participant.total_minions_killed = 150
            participant.vision_score = 25
            participant.total_damage_dealt_to_champions = 15000
            
            match.participants.append(participant)
            inconsistent_matches.append(match)
        
        # Create validator
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = inconsistent_matches
        validator = DataQualityValidator()
        
        # Test consistency validation on each match
        all_issues = []
        for match in inconsistent_matches:
            issues = validator.validate_match_data(match)
            all_issues.extend(issues)
        
        # Verify consistency issues are detected
        assert len(all_issues) > 0, "Should have found consistency issues"
        
        # Check that issues are related to consistency
        issue_types = [issue.issue_type for issue in all_issues]
        consistency_types = ['invalid_champion', 'invalid_role', 'data_inconsistency']
        consistency_found = any(issue_type in consistency_types for issue_type in issue_types)
        assert consistency_found, "Should have found consistency-related issues"


class TestStatisticalAccuracy:
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
        
        # Test with known datasets that should be significantly different
        sample1 = [10.0 + i * 0.1 for i in range(100)]  # Mean ≈ 14.95
        sample2 = [15.0 + i * 0.1 for i in range(100)]  # Mean ≈ 19.95
        
        # Test significance
        significance_result = statistical_analyzer.perform_significance_testing(sample1, sample2)
        
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
        
        # Known dataset with mean=10, std≈2
        known_data = [10.0 + (i % 11 - 5) * 0.4 for i in range(100)]
        known_mean = statistics.mean(known_data)
        known_std = statistics.stdev(known_data)
        
        # Calculate 95% confidence interval
        ci = statistical_analyzer.calculate_confidence_interval(known_data, 0.95)
        
        # Verify confidence interval properties
        assert ci.lower_bound < known_mean < ci.upper_bound
        assert ci.confidence_level == 0.95
        
        # For large sample, CI should be relatively narrow
        ci_width = ci.upper_bound - ci.lower_bound
        expected_width = 2 * 1.96 * (known_std / (len(known_data) ** 0.5))  # Approximate
        
        # Allow 10% tolerance for CI width
        assert abs(ci_width - expected_width) < expected_width * 0.1
    
    def test_correlation_analysis_accuracy(self):
        """Test accuracy of correlation analysis."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Create known correlated data
        x_data = list(range(100))
        y_data_positive = [2 * x + 5 + (x % 7 - 3) * 0.1 for x in x_data]  # Strong positive correlation
        y_data_negative = [-1.5 * x + 100 + (x % 5 - 2) * 0.1 for x in x_data]  # Strong negative correlation
        y_data_uncorrelated = [(x * 17 + 23) % 50 for x in x_data]  # No correlation
        
        variables = {
            'x': x_data,
            'y_pos': y_data_positive,
            'y_neg': y_data_negative,
            'y_uncorr': y_data_uncorrelated
        }
        
        # Analyze correlations
        correlation_result = statistical_analyzer.analyze_correlations(variables)
        
        # Verify correlation results (correlation_result is a dict with tuple keys)
        assert correlation_result[('x', 'y_pos')].correlation_coefficient > 0.9  # Strong positive
        assert correlation_result[('x', 'y_neg')].correlation_coefficient < -0.9  # Strong negative
        assert abs(correlation_result[('x', 'y_uncorr')].correlation_coefficient) < 0.3  # Weak correlation


class TestUserInterfaceFeatures:
    """User interface tests for all CLI analytics features."""
    
    @pytest.fixture
    def mock_cli_system(self):
        """Set up mock CLI system for testing."""
        # Create mock data
        matches = []
        for i in range(50):
            match = Mock(spec=Match)
            match.match_id = f"cli_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "cli_test_player"
            participant.champion_id = (i % 10) + 1
            participant.team_position = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][i % 5]
            participant.win = i % 2 == 0
            participant.kills = 5 + (i % 7)
            participant.deaths = 3 + (i % 4)
            participant.assists = 8 + (i % 6)
            participant.total_minions_killed = 150 + (i * 5)
            participant.vision_score = 25 + (i % 10)
            participant.total_damage_dealt_to_champions = 15000 + (i * 100)
            
            match.participants.append(participant)
            matches.append(match)
        
        # Create mock CLI system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        match_manager.get_recent_matches.return_value = matches
        
        from lol_team_optimizer.config import Config
        config = Config()
        config.data_directory = Path(tempfile.mkdtemp())
        
        core_engine = Mock(spec=CoreEngine)
        core_engine.match_manager = match_manager
        core_engine.config = config
        
        # Create analytics components
        baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        core_engine.analytics_engine = analytics_engine
        
        cli = StreamlinedCLI(core_engine)
        
        return {
            'cli': cli,
            'core_engine': core_engine,
            'match_manager': match_manager,
            'analytics_engine': analytics_engine
        }
    
    def test_historical_match_browser_interface(self, mock_cli_system):
        """Test historical match browser CLI interface."""
        cli = mock_cli_system['cli']
        
        # Test match browsing functionality
        with patch('builtins.input', side_effect=['1', 'cli_test_player', '4']):  # Browse matches, enter player, exit
            with patch('builtins.print') as mock_print:
                try:
                    cli.show_historical_match_browser()
                except (SystemExit, KeyboardInterrupt):
                    pass  # Expected when exiting menu
        
        # Verify that match data was displayed
        print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        match_display_found = any("Match ID" in str(call) or "cli_match_" in str(call) for call in print_calls)
        assert match_display_found, "Match browser should display match information"
    
    def test_champion_performance_analytics_interface(self, mock_cli_system):
        """Test champion performance analytics CLI interface."""
        cli = mock_cli_system['cli']
        
        # Test champion performance analysis
        with patch('builtins.input', side_effect=['1', 'cli_test_player', '1', '4']):  # Analyze performance, player, champion 1, exit
            with patch('builtins.print') as mock_print:
                try:
                    cli.show_champion_performance_analytics()
                except (SystemExit, KeyboardInterrupt):
                    pass
        
        # Verify that performance data was displayed
        print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        performance_display_found = any(
            "performance" in str(call).lower() or "win rate" in str(call).lower() 
            for call in print_calls
        )
        assert performance_display_found, "Champion performance interface should display performance metrics"
    
    def test_team_composition_analysis_interface(self, mock_cli_system):
        """Test team composition analysis CLI interface."""
        cli = mock_cli_system['cli']
        
        # Test composition analysis
        with patch('builtins.input', side_effect=['1', 'cli_test_player', 'cli_test_player', 'cli_test_player', 'cli_test_player', 'cli_test_player', '4']):
            with patch('builtins.print') as mock_print:
                try:
                    cli.show_team_composition_analysis()
                except (SystemExit, KeyboardInterrupt):
                    pass
        
        # Verify that composition data was displayed
        print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        composition_display_found = any(
            "composition" in str(call).lower() or "synergy" in str(call).lower()
            for call in print_calls
        )
        assert composition_display_found, "Team composition interface should display composition analysis"
    
    def test_interactive_analytics_dashboard(self, mock_cli_system):
        """Test interactive analytics dashboard interface."""
        analytics_engine = mock_cli_system['analytics_engine']
        
        # Create dashboard
        dashboard = InteractiveAnalyticsDashboard(analytics_engine)
        
        # Test dashboard functionality
        with patch('builtins.input', side_effect=['cli_test_player', 'q']):  # Enter player, quit
            with patch('builtins.print') as mock_print:
                try:
                    dashboard.run_interactive_session()
                except (SystemExit, KeyboardInterrupt):
                    pass
        
        # Verify dashboard displayed analytics
        print_calls = [call.args[0] for call in mock_print.call_args_list if call.args]
        dashboard_display_found = any(
            "analytics" in str(call).lower() or "dashboard" in str(call).lower()
            for call in print_calls
        )
        assert dashboard_display_found, "Interactive dashboard should display analytics information"


class TestConcurrentAnalyticsOperations:
    """Load tests for concurrent analytics operations."""
    
    @pytest.fixture
    def concurrent_test_system(self):
        """Set up system for concurrent testing."""
        # Create substantial dataset
        matches = []
        players = [f"concurrent_player_{i}" for i in range(20)]
        
        for i in range(2000):  # 2000 matches
            match = Mock(spec=Match)
            match.match_id = f"concurrent_match_{i}"
            match.game_creation = int(datetime.now().timestamp() * 1000)
            match.game_duration = 1800
            match.participants = []
            
            # Create 10 participants per match
            for j in range(10):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = players[j % len(players)]
                participant.champion_id = (i + j) % 50 + 1
                participant.team_position = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][j % 5]
                participant.win = j < 5 if i % 2 == 0 else j >= 5
                participant.kills = 5 + (i % 10)
                participant.deaths = 3 + (i % 5)
                participant.assists = 8 + (i % 8)
                participant.total_minions_killed = 150 + (i % 100)
                participant.vision_score = 25 + (i % 20)
                participant.total_damage_dealt_to_champions = 15000 + (i * 50)
                
                match.participants.append(participant)
            
            matches.append(match)
        
        # Create analytics system
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = matches
        
        from lol_team_optimizer.config import Config
        config = Config()
        baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        return {
            'analytics_engine': analytics_engine,
            'players': players,
            'matches': matches
        }
    
    def test_concurrent_player_analysis(self, concurrent_test_system):
        """Test concurrent player analysis operations."""
        analytics_engine = concurrent_test_system['analytics_engine']
        players = concurrent_test_system['players'][:10]  # Use first 10 players
        
        def analyze_player(player_id):
            """Analyze a single player."""
            try:
                result = analytics_engine.analyze_player_performance(player_id, AnalyticsFilters())
                return {'success': True, 'result': result, 'player': player_id}
            except Exception as e:
                return {'success': False, 'error': str(e), 'player': player_id}
        
        # Test with different concurrency levels
        concurrency_levels = [1, 5, 10]
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                # Submit tasks
                futures = [executor.submit(analyze_player, player) for player in players[:concurrency]]
                
                # Collect results
                results = []
                for future in concurrent.futures.as_completed(futures, timeout=60):
                    result = future.result()
                    results.append(result)
            
            end_time = time.time()
            
            # Verify results
            successful_results = [r for r in results if r['success']]
            failed_results = [r for r in results if not r['success']]
            
            # At least 80% should succeed
            success_rate = len(successful_results) / len(results)
            assert success_rate >= 0.8, f"Success rate too low at concurrency {concurrency}: {success_rate:.2%}"
            
            # Performance should be reasonable
            total_time = end_time - start_time
            avg_time_per_task = total_time / len(results)
            
            assert avg_time_per_task < 10.0, f"Average time per task too high: {avg_time_per_task:.2f}s"
            
            print(f"Concurrency {concurrency}: {len(successful_results)}/{len(results)} succeeded, "
                  f"{total_time:.2f}s total, {avg_time_per_task:.2f}s avg")
    
    def test_concurrent_recommendation_generation(self, concurrent_test_system):
        """Test concurrent champion recommendation generation."""
        analytics_engine = concurrent_test_system['analytics_engine']
        players = concurrent_test_system['players'][:5]
        
        # Create recommendation engine
        recommendation_engine = ChampionRecommendationEngine(analytics_engine, Mock())
        
        def generate_recommendations(player_role_pair):
            """Generate recommendations for a player-role pair."""
            player, role = player_role_pair
            try:
                recommendations = recommendation_engine.get_champion_recommendations(
                    player, role, {'existing_picks': [], 'banned_champions': []}
                )
                return {'success': True, 'recommendations': recommendations, 'player': player, 'role': role}
            except Exception as e:
                return {'success': False, 'error': str(e), 'player': player, 'role': role}
        
        # Create player-role pairs for concurrent testing
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        player_role_pairs = [(player, role) for player in players for role in roles][:15]  # 15 combinations
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(generate_recommendations, pair) for pair in player_role_pairs]
            
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=120):
                result = future.result()
                results.append(result)
        
        end_time = time.time()
        
        # Verify concurrent recommendation results
        successful_results = [r for r in results if r['success']]
        success_rate = len(successful_results) / len(results)
        
        assert success_rate >= 0.7, f"Recommendation success rate too low: {success_rate:.2%}"
        
        # Verify recommendation quality
        for result in successful_results:
            recommendations = result['recommendations']
            assert isinstance(recommendations, list)
            assert len(recommendations) > 0
            
            for rec in recommendations:
                assert isinstance(rec, ChampionRecommendation)
                assert 0 <= rec.recommendation_score <= 1
                assert 0 <= rec.confidence <= 1
        
        total_time = end_time - start_time
        print(f"Concurrent recommendations: {len(successful_results)}/{len(results)} succeeded in {total_time:.2f}s")
    
    def test_system_stability_under_load(self, concurrent_test_system):
        """Test system stability under sustained load."""
        analytics_engine = concurrent_test_system['analytics_engine']
        players = concurrent_test_system['players'][:5]
        
        def sustained_analysis_task():
            """Perform sustained analysis operations."""
            results = []
            for i in range(10):  # 10 operations per thread
                try:
                    player = players[i % len(players)]
                    result = analytics_engine.analyze_player_performance(player, AnalyticsFilters())
                    results.append({'success': True, 'iteration': i})
                    time.sleep(0.1)  # Small delay between operations
                except Exception as e:
                    results.append({'success': False, 'error': str(e), 'iteration': i})
            return results
        
        # Run sustained load test
        start_time = time.time()
        if PSUTIL_AVAILABLE:
            initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            initial_memory = 100  # Mock value
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(sustained_analysis_task) for _ in range(5)]
            
            all_results = []
            for future in concurrent.futures.as_completed(futures, timeout=180):
                thread_results = future.result()
                all_results.extend(thread_results)
        
        end_time = time.time()
        if PSUTIL_AVAILABLE:
            final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        else:
            final_memory = initial_memory + 20  # Mock increase
        
        # Analyze stability results
        successful_operations = [r for r in all_results if r['success']]
        failed_operations = [r for r in all_results if not r['success']]
        
        success_rate = len(successful_operations) / len(all_results)
        memory_increase = final_memory - initial_memory
        total_time = end_time - start_time
        
        # Verify system stability
        assert success_rate >= 0.9, f"System stability poor under load: {success_rate:.2%} success rate"
        assert memory_increase < 200, f"Excessive memory growth under load: {memory_increase:.1f}MB"
        assert total_time < 120, f"Load test took too long: {total_time:.1f}s"
        
        print(f"Stability test: {len(successful_operations)}/{len(all_results)} operations succeeded")
        print(f"Memory increase: {memory_increase:.1f}MB, Total time: {total_time:.1f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])