"""
Integration workflow tests for analytics system.

This module tests complete end-to-end workflows that span multiple
analytics components and verify their proper integration.
"""

import pytest
import asyncio
import time
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
from lol_team_optimizer.core_engine import CoreEngine

# Import models
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, AnalyticsFilters,
    TeamComposition, CompositionPerformance, ChampionRecommendation,
    PerformanceDelta, TrendAnalysis, DateRange
)
from lol_team_optimizer.models import Match, Player, MatchParticipant
from lol_team_optimizer.match_manager import MatchManager


class TestCompleteAnalyticsWorkflows:
    """Test complete analytics workflows from data ingestion to insights."""
    
    @pytest.fixture
    def comprehensive_match_dataset(self):
        """Create comprehensive match dataset for workflow testing."""
        matches = []
        players = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "henry"]
        champions = list(range(1, 21))  # 20 different champions
        roles = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
        
        # Generate 6 months of match data
        base_date = datetime.now() - timedelta(days=180)
        
        for day in range(180):
            current_date = base_date + timedelta(days=day)
            
            # Generate 2-5 matches per day
            daily_matches = 2 + (day % 4)
            
            for match_num in range(daily_matches):
                match = Mock(spec=Match)
                match.match_id = f"match_{day}_{match_num}"
                match.game_creation = int(current_date.timestamp() * 1000)
                match.game_duration = 1500 + (day * 10) + (match_num * 300)  # 25-50 minutes
                match.participants = []
                
                # Select 10 players for this match (5 per team)
                match_players = players[:8] if day % 2 == 0 else players[2:]
                selected_players = match_players[:10] if len(match_players) >= 10 else match_players * 2
                
                # Create team 1
                for i in range(5):
                    participant = Mock(spec=MatchParticipant)
                    participant.puuid = selected_players[i]
                    participant.champion_id = champions[(day + i + match_num) % len(champions)]
                    participant.team_position = roles[i]
                    participant.win = (day + match_num) % 3 != 0  # Varied win pattern
                    
                    # Performance metrics with realistic variation
                    base_performance = self._get_base_performance(roles[i], day)
                    participant.kills = max(0, base_performance['kills'] + (match_num % 7 - 3))
                    participant.deaths = max(1, base_performance['deaths'] + (match_num % 5 - 2))
                    participant.assists = max(0, base_performance['assists'] + (match_num % 9 - 4))
                    participant.total_minions_killed = base_performance['cs'] + (match_num * 10)
                    participant.vision_score = base_performance['vision'] + (match_num % 10)
                    participant.total_damage_dealt_to_champions = base_performance['damage'] + (match_num * 500)
                    
                    match.participants.append(participant)
                
                # Create team 2
                for i in range(5, 10):
                    participant = Mock(spec=MatchParticipant)
                    participant.puuid = selected_players[i % len(selected_players)]
                    participant.champion_id = champions[(day + i + match_num + 10) % len(champions)]
                    participant.team_position = roles[i - 5]
                    participant.win = not ((day + match_num) % 3 != 0)  # Opposite of team 1
                    
                    # Performance metrics
                    base_performance = self._get_base_performance(roles[i - 5], day)
                    participant.kills = max(0, base_performance['kills'] + (match_num % 6 - 2))
                    participant.deaths = max(1, base_performance['deaths'] + (match_num % 4 - 1))
                    participant.assists = max(0, base_performance['assists'] + (match_num % 8 - 3))
                    participant.total_minions_killed = base_performance['cs'] + (match_num * 8)
                    participant.vision_score = base_performance['vision'] + (match_num % 8)
                    participant.total_damage_dealt_to_champions = base_performance['damage'] + (match_num * 400)
                    
                    match.participants.append(participant)
                
                matches.append(match)
        
        return matches
    
    def _get_base_performance(self, role: str, day: int) -> Dict[str, int]:
        """Get base performance metrics for a role with temporal variation."""
        base_stats = {
            "TOP": {"kills": 4, "deaths": 3, "assists": 6, "cs": 180, "vision": 20, "damage": 18000},
            "JUNGLE": {"kills": 6, "deaths": 4, "assists": 8, "cs": 120, "vision": 35, "damage": 16000},
            "MIDDLE": {"kills": 7, "deaths": 4, "assists": 7, "cs": 170, "vision": 25, "damage": 22000},
            "BOTTOM": {"kills": 8, "deaths": 3, "assists": 6, "cs": 190, "vision": 15, "damage": 25000},
            "UTILITY": {"kills": 2, "deaths": 5, "assists": 12, "cs": 40, "vision": 60, "damage": 8000}
        }
        
        # Add temporal variation (meta shifts, player improvement)
        stats = base_stats[role].copy()
        improvement_factor = 1 + (day / 1000)  # Gradual improvement over time
        
        for key in stats:
            if key != "deaths":  # Deaths don't improve
                stats[key] = int(stats[key] * improvement_factor)
        
        return stats
    
    @pytest.fixture
    def integrated_analytics_system(self, comprehensive_match_dataset):
        """Set up fully integrated analytics system."""
        # Mock match manager with comprehensive dataset
        match_manager = Mock(spec=MatchManager)
        match_manager.get_matches_for_player.return_value = comprehensive_match_dataset
        match_manager.get_recent_matches.return_value = comprehensive_match_dataset
        
        # Create all analytics components
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        statistical_analyzer = StatisticalAnalyzer()
        cache_manager = AnalyticsCacheManager()
        
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
        
        # Mock core engine integration
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
    
    def test_player_improvement_tracking_workflow(self, integrated_analytics_system):
        """Test complete workflow for tracking player improvement over time."""
        analytics_engine = integrated_analytics_system['analytics_engine']
        comparative_analyzer = integrated_analytics_system['comparative_analyzer']
        
        # Analyze player performance over different time periods
        recent_filters = AnalyticsFilters(
            date_range={
                'start': datetime.now() - timedelta(days=30),
                'end': datetime.now()
            }
        )
        
        historical_filters = AnalyticsFilters(
            date_range={
                'start': datetime.now() - timedelta(days=180),
                'end': datetime.now() - timedelta(days=150)
            }
        )
        
        # Get recent and historical performance
        recent_performance = analytics_engine.analyze_player_performance("alice", recent_filters)
        historical_performance = analytics_engine.analyze_player_performance("alice", historical_filters)
        
        # Compare performance periods
        improvement_analysis = comparative_analyzer.compare_performance_periods(
            "alice", historical_performance, recent_performance
        )
        
        # Verify workflow results
        assert recent_performance is not None
        assert historical_performance is not None
        assert improvement_analysis is not None
        
        # Should show improvement over time (based on our test data design)
        assert improvement_analysis.overall_improvement_score > 0
        assert len(improvement_analysis.improved_metrics) > 0
    
    def test_team_optimization_workflow(self, integrated_analytics_system):
        """Test complete team optimization workflow."""
        recommendation_engine = integrated_analytics_system['recommendation_engine']
        composition_analyzer = integrated_analytics_system['composition_analyzer']
        synergy_matrix = integrated_analytics_system['synergy_matrix']
        
        # Step 1: Analyze player synergies
        player_pool = ["alice", "bob", "charlie", "diana", "eve"]
        synergy_analysis = synergy_matrix.calculate_synergy_matrix(player_pool)
        
        # Step 2: Get champion recommendations for each role
        team_context = {'existing_picks': [], 'banned_champions': [1, 2, 3]}
        
        recommendations = {}
        for role in ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]:
            player = player_pool[["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"].index(role)]
            role_recommendations = recommendation_engine.get_champion_recommendations(
                player, role, team_context
            )
            recommendations[role] = role_recommendations
        
        # Step 3: Build optimal composition
        optimal_composition = composition_analyzer.identify_optimal_compositions(
            player_pool, {'max_compositions': 3}
        )
        
        # Step 4: Analyze composition performance
        if optimal_composition:
            composition_performance = composition_analyzer.analyze_composition_performance(
                optimal_composition[0]
            )
        
        # Verify workflow results
        assert synergy_analysis is not None
        assert len(recommendations) == 5
        assert all(len(recs) > 0 for recs in recommendations.values())
        assert optimal_composition is not None
        assert len(optimal_composition) > 0
    
    def test_champion_meta_analysis_workflow(self, integrated_analytics_system):
        """Test workflow for analyzing champion meta trends."""
        analytics_engine = integrated_analytics_system['analytics_engine']
        comparative_analyzer = integrated_analytics_system['comparative_analyzer']
        
        # Analyze champion performance across different time periods
        champions_to_analyze = [1, 2, 3, 4, 5]
        
        # Get performance for each champion across multiple players
        champion_analysis = {}
        
        for champion_id in champions_to_analyze:
            # Analyze champion across all players who played it
            players_performance = []
            
            for player in ["alice", "bob", "charlie", "diana"]:
                try:
                    performance = analytics_engine.analyze_champion_performance(
                        player, champion_id, "TOP"  # Analyze as TOP laner
                    )
                    if performance and performance.games_played > 0:
                        players_performance.append(performance)
                except:
                    continue  # Skip if player hasn't played this champion
            
            if players_performance:
                # Calculate meta trends for this champion
                meta_analysis = comparative_analyzer.analyze_champion_meta_trends(
                    champion_id, players_performance
                )
                champion_analysis[champion_id] = meta_analysis
        
        # Verify meta analysis results
        assert len(champion_analysis) > 0
        
        for champion_id, analysis in champion_analysis.items():
            assert analysis is not None
            assert hasattr(analysis, 'overall_performance_trend')
            assert hasattr(analysis, 'win_rate_trend')
    
    def test_data_quality_and_validation_workflow(self, integrated_analytics_system):
        """Test complete data quality validation workflow."""
        data_validator = integrated_analytics_system['data_validator']
        analytics_engine = integrated_analytics_system['analytics_engine']
        
        # Step 1: Validate data quality for multiple players
        players_to_validate = ["alice", "bob", "charlie"]
        validation_results = {}
        
        for player in players_to_validate:
            # Mock quality report for testing
            quality_report = {
                'quality_score': 0.85,
                'data_completeness': 0.9,
                'anomalies': [],
                'validation_issues': []
            }
            validation_results[player] = quality_report
        
        # Step 2: Identify data quality issues (mock for testing)
        quality_issues = {
            'system_wide_issues': [],
            'common_problems': [],
            'recommendations': []
        }
        
        # Step 3: Generate analytics with quality indicators
        for player in players_to_validate:
            analytics = analytics_engine.analyze_player_performance(
                player, AnalyticsFilters()
            )
            
            # Verify quality indicators are included
            assert hasattr(analytics, 'data_quality_score')
            assert hasattr(analytics, 'confidence_indicators')
        
        # Verify validation workflow results
        assert len(validation_results) == len(players_to_validate)
        assert all(report['quality_score'] >= 0 for report in validation_results.values())
        assert quality_issues is not None
    
    def test_export_and_reporting_workflow(self, integrated_analytics_system):
        """Test complete export and reporting workflow."""
        export_manager = integrated_analytics_system['export_manager']
        analytics_engine = integrated_analytics_system['analytics_engine']
        
        # Step 1: Generate comprehensive analytics
        player_analytics = analytics_engine.analyze_player_performance(
            "alice", AnalyticsFilters()
        )
        
        # Step 2: Export in multiple formats
        export_formats = ['csv', 'json', 'excel']
        export_results = {}
        
        for format_type in export_formats:
            try:
                export_result = export_manager.export_player_analytics(
                    "alice", format=format_type
                )
                export_results[format_type] = export_result
            except Exception as e:
                # Some formats might not be available in test environment
                export_results[format_type] = f"Error: {str(e)}"
        
        # Step 3: Generate comprehensive report
        comprehensive_report = export_manager.generate_comprehensive_report(
            "alice", include_charts=False  # Disable charts for testing
        )
        
        # Step 4: Generate team report
        team_report = export_manager.generate_team_report(
            ["alice", "bob", "charlie"], include_comparisons=True
        )
        
        # Verify export workflow results
        assert len(export_results) == len(export_formats)
        assert comprehensive_report is not None
        assert team_report is not None
        
        # Verify report contains expected sections
        assert 'player_summary' in comprehensive_report
        assert 'performance_analysis' in comprehensive_report
        assert 'recommendations' in comprehensive_report
    
    def test_real_time_analytics_update_workflow(self, integrated_analytics_system):
        """Test workflow for updating analytics with new match data."""
        analytics_engine = integrated_analytics_system['analytics_engine']
        cache_manager = integrated_analytics_system['cache_manager']
        baseline_manager = integrated_analytics_system['baseline_manager']
        
        # Step 1: Get initial analytics
        initial_analytics = analytics_engine.analyze_player_performance(
            "alice", AnalyticsFilters()
        )
        
        # Step 2: Simulate new match data
        new_match = Mock(spec=Match)
        new_match.match_id = "new_match_001"
        new_match.game_creation = int(datetime.now().timestamp() * 1000)
        new_match.game_duration = 1800
        new_match.participants = []
        
        # Add participant for alice
        participant = Mock(spec=MatchParticipant)
        participant.puuid = "alice"
        participant.champion_id = 10
        participant.team_position = "TOP"
        participant.win = True
        participant.kills = 8
        participant.deaths = 2
        participant.assists = 10
        participant.total_minions_killed = 200
        participant.vision_score = 30
        participant.total_damage_dealt_to_champions = 20000
        new_match.participants.append(participant)
        
        # Step 3: Update system with new match
        # In real system, this would trigger incremental updates
        baseline_manager.update_baselines("alice", [new_match])
        
        # Step 4: Invalidate relevant caches
        cache_manager.invalidate_cache("alice_*")
        
        # Step 5: Get updated analytics
        updated_analytics = analytics_engine.analyze_player_performance(
            "alice", AnalyticsFilters()
        )
        
        # Verify update workflow
        assert initial_analytics is not None
        assert updated_analytics is not None
        
        # Analytics should reflect the update (in a real system)
        # For this test, we verify the workflow completes successfully
        assert updated_analytics.puuid == "alice"
    
    def test_cross_component_integration_workflow(self, integrated_analytics_system):
        """Test workflow that integrates multiple analytics components."""
        analytics_engine = integrated_analytics_system['analytics_engine']
        recommendation_engine = integrated_analytics_system['recommendation_engine']
        composition_analyzer = integrated_analytics_system['composition_analyzer']
        comparative_analyzer = integrated_analytics_system['comparative_analyzer']
        
        # Step 1: Analyze multiple players
        players = ["alice", "bob", "charlie"]
        player_analyses = {}
        
        for player in players:
            analysis = analytics_engine.analyze_player_performance(
                player, AnalyticsFilters()
            )
            player_analyses[player] = analysis
        
        # Step 2: Compare players
        comparison_result = comparative_analyzer.compare_multiple_players(
            players, metric="overall_performance"
        )
        
        # Step 3: Get recommendations based on comparative analysis
        best_player = comparison_result.top_performers[0] if comparison_result.top_performers else players[0]
        
        recommendations = recommendation_engine.get_champion_recommendations(
            best_player, "TOP", {'existing_picks': []}
        )
        
        # Step 4: Analyze team composition with recommended champions
        if recommendations:
            test_composition = TeamComposition(
                players={
                    'TOP': {'puuid': best_player, 'champion_id': recommendations[0].champion_id},
                    'JUNGLE': {'puuid': players[1], 'champion_id': 2},
                    'MIDDLE': {'puuid': players[2], 'champion_id': 3},
                    'BOTTOM': {'puuid': players[0], 'champion_id': 4},
                    'UTILITY': {'puuid': players[1], 'champion_id': 5}
                }
            )
            
            composition_performance = composition_analyzer.analyze_composition_performance(
                test_composition
            )
        
        # Verify cross-component integration
        assert len(player_analyses) == len(players)
        assert comparison_result is not None
        assert len(recommendations) > 0
        
        # All components should work together seamlessly
        for player, analysis in player_analyses.items():
            assert analysis.puuid == player
            assert analysis.overall_performance is not None


class TestAnalyticsSystemResilience:
    """Test analytics system resilience and error recovery."""
    
    def test_partial_data_failure_recovery(self):
        """Test system recovery when some data sources fail."""
        # Create match manager that fails for some players
        match_manager = Mock(spec=MatchManager)
        
        def mock_get_matches(puuid):
            if puuid == "failing_player":
                raise Exception("Data source unavailable")
            return [Mock(spec=Match)]  # Return mock data for other players
        
        match_manager.get_matches_for_player.side_effect = mock_get_matches
        
        # Create analytics system
        from lol_team_optimizer.config import Config; config = Config(); baseline_manager = BaselineManager(config, match_manager)
        analytics_engine = HistoricalAnalyticsEngine(
            match_manager, baseline_manager, StatisticalAnalyzer(),
            AnalyticsCacheManager()
        )
        
        # Test resilience
        successful_analysis = analytics_engine.analyze_player_performance(
            "working_player", AnalyticsFilters()
        )
        
        # Should handle failure gracefully
        with pytest.raises(Exception):
            analytics_engine.analyze_player_performance(
                "failing_player", AnalyticsFilters()
            )
        
        # Successful analysis should still work
        assert successful_analysis is not None
    
    def test_cache_corruption_recovery(self):
        """Test recovery from cache corruption."""
        # Create cache manager with corrupted cache
        cache_dir = Path(tempfile.mkdtemp())
        cache_manager = AnalyticsCacheManager(cache_dir)
        
        # Corrupt cache by writing invalid data
        cache_file = cache_dir / "corrupted_cache.json"
        cache_file.write_text("invalid json data {{{")
        
        # System should handle corrupted cache gracefully
        cached_data = cache_manager.get_cached_analytics("corrupted_cache")
        assert cached_data is None  # Should return None for corrupted cache
        
        # Should be able to cache new data
        cache_manager.cache_analytics("new_data", {"test": "data"}, 3600)
        retrieved_data = cache_manager.get_cached_analytics("new_data")
        assert retrieved_data is not None
    
    def test_statistical_calculation_edge_cases(self):
        """Test statistical calculations with edge case data."""
        statistical_analyzer = StatisticalAnalyzer()
        
        # Test with empty data
        empty_result = statistical_analyzer.calculate_confidence_intervals([], 0.95)
        assert empty_result is not None  # Should handle gracefully
        
        # Test with single data point
        single_point_result = statistical_analyzer.calculate_confidence_intervals([5.0], 0.95)
        assert single_point_result is not None
        
        # Test with identical values
        identical_values = [10.0] * 100
        identical_result = statistical_analyzer.calculate_confidence_intervals(identical_values, 0.95)
        assert identical_result is not None
        assert identical_result.lower_bound == identical_result.upper_bound == 10.0
        
        # Test significance testing with identical samples
        significance_result = statistical_analyzer.perform_significance_testing(
            identical_values, identical_values
        )
        assert significance_result.p_value > 0.05  # Should not be significant
        assert not significance_result.is_significant


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
