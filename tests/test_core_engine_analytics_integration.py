"""
Tests for Core Engine Analytics Integration.

This module tests the integration of the analytics system with the core engine,
including analytics methods, health monitoring, and data migration procedures.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player, Match, MatchParticipant
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, PerformanceMetrics, ChampionPerformanceMetrics,
    AnalyticsFilters, DateRange, ChampionRecommendation
)


class TestCoreEngineAnalyticsIntegration:
    """Test suite for core engine analytics integration."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create mock configuration."""
        config = Mock()
        config.data_directory = temp_dir / "data"
        config.cache_directory = temp_dir / "cache"
        config.data_directory.mkdir(exist_ok=True)
        config.cache_directory.mkdir(exist_ok=True)
        return config
    
    @pytest.fixture
    def sample_player(self):
        """Create sample player for testing."""
        return Player(
            name="TestPlayer",
            summoner_name="TestPlayer#NA1",
            puuid="test-puuid-123",
            role_preferences={"top": 5, "jungle": 3, "middle": 2, "support": 1, "bottom": 4},
            performance_cache={"top": {"win_rate": 0.65, "matches_played": 20}},
            champion_masteries={},
            last_updated=datetime.now()
        )
    
    @pytest.fixture
    def sample_match(self):
        """Create sample match for testing."""
        participant = MatchParticipant(
            puuid="test-puuid-123",
            summoner_name="TestPlayer",
            champion_id=1,
            champion_name="Annie",
            individual_position="TOP",
            lane="TOP",
            role="SOLO",
            kills=5,
            deaths=2,
            assists=8,
            win=True,
            total_minions_killed=120,
            neutral_minions_killed=30,
            vision_score=25,
            total_damage_dealt_to_champions=15000
        )
        
        return Match(
            match_id="TEST_MATCH_1",
            game_creation=int(datetime.now().timestamp() * 1000),
            game_duration=1800,  # 30 minutes
            queue_id=420,  # Ranked Solo/Duo
            participants=[participant],
            winning_team=1
        )
    
    @pytest.fixture
    def core_engine_with_analytics(self, mock_config, temp_dir):
        """Create core engine with mocked analytics components."""
        with patch('lol_team_optimizer.core_engine.Config', return_value=mock_config), \
             patch('lol_team_optimizer.core_engine.DataManager'), \
             patch('lol_team_optimizer.core_engine.MatchManager'), \
             patch('lol_team_optimizer.core_engine.RiotAPIClient'), \
             patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager'), \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'), \
             patch('lol_team_optimizer.core_engine.DataMigrator'):
            
            engine = CoreEngine()
            
            # Mock analytics components
            engine.analytics_cache_manager = Mock()
            engine.baseline_manager = Mock()
            engine.statistical_analyzer = Mock()
            engine.champion_synergy_analyzer = Mock()
            engine.historical_analytics_engine = Mock()
            engine.champion_recommendation_engine = Mock()
            engine.analytics_available = True
            
            return engine
    
    def test_analytics_initialization_success(self, mock_config, temp_dir):
        """Test successful analytics initialization."""
        with patch('lol_team_optimizer.core_engine.Config', return_value=mock_config), \
             patch('lol_team_optimizer.core_engine.DataManager'), \
             patch('lol_team_optimizer.core_engine.MatchManager'), \
             patch('lol_team_optimizer.core_engine.RiotAPIClient'), \
             patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager'), \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'), \
             patch('lol_team_optimizer.core_engine.DataMigrator'), \
             patch('lol_team_optimizer.core_engine.AnalyticsCacheManager'), \
             patch('lol_team_optimizer.core_engine.BaselineManager'), \
             patch('lol_team_optimizer.core_engine.StatisticalAnalyzer'), \
             patch('lol_team_optimizer.core_engine.ChampionSynergyAnalyzer'), \
             patch('lol_team_optimizer.core_engine.HistoricalAnalyticsEngine'), \
             patch('lol_team_optimizer.core_engine.ChampionRecommendationEngine'):
            
            engine = CoreEngine()
            
            assert engine.analytics_available is True
            assert engine.analytics_cache_manager is not None
            assert engine.baseline_manager is not None
            assert engine.historical_analytics_engine is not None
            assert engine.champion_recommendation_engine is not None
    
    def test_analytics_initialization_failure(self, mock_config, temp_dir):
        """Test graceful handling of analytics initialization failure."""
        with patch('lol_team_optimizer.core_engine.Config', return_value=mock_config), \
             patch('lol_team_optimizer.core_engine.DataManager'), \
             patch('lol_team_optimizer.core_engine.MatchManager'), \
             patch('lol_team_optimizer.core_engine.RiotAPIClient'), \
             patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager'), \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'), \
             patch('lol_team_optimizer.core_engine.DataMigrator'), \
             patch('lol_team_optimizer.core_engine.AnalyticsCacheManager', side_effect=Exception("Analytics init failed")):
            
            engine = CoreEngine()
            
            assert engine.analytics_available is False
            assert engine.analytics_cache_manager is None
            assert engine.baseline_manager is None
            assert engine.historical_analytics_engine is None
            assert engine.champion_recommendation_engine is None
    
    def test_analyze_player_performance_success(self, core_engine_with_analytics):
        """Test successful player performance analysis."""
        # Mock the analytics engine response
        mock_analytics = PlayerAnalytics(
            puuid="test-puuid-123",
            player_name="TestPlayer",
            analysis_period=DateRange(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now()
            ),
            overall_performance=PerformanceMetrics(
                games_played=20,
                wins=13,
                losses=7,
                win_rate=0.65,
                avg_kda=2.5,
                avg_cs_per_min=6.8,
                avg_vision_score=25.0,
                avg_damage_per_min=500.0
            )
        )
        
        core_engine_with_analytics.historical_analytics_engine.analyze_player_performance.return_value = mock_analytics
        
        result = core_engine_with_analytics.analyze_player_performance("test-puuid-123")
        
        assert "error" not in result
        assert result["puuid"] == "test-puuid-123"
        assert result["overall_performance"]["win_rate"] == 0.65
        assert result["overall_performance"]["games_played"] == 20
    
    def test_analyze_player_performance_analytics_unavailable(self, core_engine_with_analytics):
        """Test player performance analysis when analytics unavailable."""
        core_engine_with_analytics.analytics_available = False
        
        result = core_engine_with_analytics.analyze_player_performance("test-puuid-123")
        
        assert "error" in result
        assert result["error"] == "Analytics system unavailable"
    
    def test_get_champion_recommendations_success(self, core_engine_with_analytics):
        """Test successful champion recommendations."""
        mock_recommendation = ChampionRecommendation(
            champion_id=1,
            champion_name="Annie",
            role="middle",
            recommendation_score=0.85,
            confidence=0.9,
            historical_performance=None,
            expected_performance=None,
            synergy_analysis=None,
            reasoning=None
        )
        
        core_engine_with_analytics.champion_recommendation_engine.get_champion_recommendations.return_value = [mock_recommendation]
        
        result = core_engine_with_analytics.get_champion_recommendations("test-puuid-123", "middle")
        
        assert "error" not in result
        assert result["puuid"] == "test-puuid-123"
        assert result["role"] == "middle"
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["champion_name"] == "Annie"
        assert result["recommendations"][0]["recommendation_score"] == 0.85
    
    def test_calculate_performance_trends_success(self, core_engine_with_analytics):
        """Test successful performance trends calculation."""
        from lol_team_optimizer.analytics_models import TrendAnalysis, TimeSeriesPoint, ConfidenceInterval
        
        mock_trend = TrendAnalysis(
            puuid="test-puuid-123",
            time_window_days=30,
            trend_data=[
                TimeSeriesPoint(
                    timestamp=datetime.now() - timedelta(days=i),
                    value=0.6 + (i * 0.01),
                    metadata={}
                ) for i in range(10)
            ],
            trend_direction="increasing",
            trend_strength=0.7,
            statistical_significance=0.05,
            confidence_interval=ConfidenceInterval(
                lower_bound=0.55, 
                upper_bound=0.75, 
                confidence_level=0.95,
                sample_size=30
            )
        )
        
        core_engine_with_analytics.historical_analytics_engine.calculate_performance_trends.return_value = mock_trend
        
        result = core_engine_with_analytics.calculate_performance_trends("test-puuid-123", 30)
        
        assert "error" not in result
        assert result["puuid"] == "test-puuid-123"
        assert result["time_window_days"] == 30
        assert result["trend_direction"] == "increasing"
        assert result["trend_strength"] == 0.7
        assert len(result["trend_data"]) == 10
    
    def test_generate_comparative_analysis_success(self, core_engine_with_analytics):
        """Test successful comparative analysis."""
        from lol_team_optimizer.historical_analytics_engine import ComparativeAnalytics
        
        mock_comparison = ComparativeAnalytics(
            players=["puuid1", "puuid2"],
            comparison_metric="win_rate",
            player_values={"puuid1": 0.65, "puuid2": 0.58},
            rankings={"puuid1": 1, "puuid2": 2},
            percentiles={"puuid1": 0.75, "puuid2": 0.60},
            statistical_significance={("puuid1", "puuid2"): 0.03},
            analysis_period=None,
            sample_sizes={"puuid1": 20, "puuid2": 18}
        )
        
        core_engine_with_analytics.historical_analytics_engine.generate_comparative_analysis.return_value = mock_comparison
        
        result = core_engine_with_analytics.generate_comparative_analysis(["puuid1", "puuid2"], "win_rate")
        
        assert "error" not in result
        assert result["comparison_metric"] == "win_rate"
        assert result["player_values"]["puuid1"] == 0.65
        assert result["rankings"]["puuid1"] == 1
        assert result["percentiles"]["puuid1"] == 0.75
    
    def test_get_analytics_cache_statistics(self, core_engine_with_analytics):
        """Test getting analytics cache statistics."""
        from lol_team_optimizer.analytics_cache_manager import CacheStatistics
        
        mock_stats = CacheStatistics(
            total_requests=1000,
            cache_hits=850,
            cache_misses=150,
            cache_evictions=10,
            total_entries=100,
            total_size_bytes=1024000,
            memory_cache_entries=50,
            memory_cache_size_bytes=512000,
            persistent_cache_entries=50,
            persistent_cache_size_bytes=512000
        )
        
        core_engine_with_analytics.analytics_cache_manager.get_cache_statistics.return_value = mock_stats
        
        result = core_engine_with_analytics.get_analytics_cache_statistics()
        
        assert "error" not in result
        assert result.hit_rate == 0.85
        assert result.total_entries == 100
    
    def test_invalidate_analytics_cache(self, core_engine_with_analytics):
        """Test analytics cache invalidation."""
        result = core_engine_with_analytics.invalidate_analytics_cache("player_*")
        
        assert result["success"] is True
        assert "player_*" in result["message"]
        core_engine_with_analytics.analytics_cache_manager.invalidate_cache.assert_called_once_with("player_*")
    
    def test_update_player_baselines(self, core_engine_with_analytics, sample_match):
        """Test updating player baselines."""
        from lol_team_optimizer.analytics_models import PlayerBaseline
        
        # Mock match manager to return matches
        core_engine_with_analytics.match_manager.get_matches_for_player.return_value = [sample_match]
        
        # Mock baseline calculation
        mock_baseline = Mock()
        mock_baseline.__dict__ = {
            "puuid": "test-puuid-123",
            "overall_metrics": {
                "games_played": 20,
                "win_rate": 0.65,
                "avg_kda": 2.5,
                "avg_cs_per_min": 6.8,
                "avg_vision_score": 25.0,
                "avg_damage_per_min": 500.0
            },
            "role_baselines": {},
            "champion_baselines": {},
            "last_updated": datetime.now().isoformat(),
            "confidence_score": 0.8
        }
        
        core_engine_with_analytics.baseline_manager.calculate_player_baseline.return_value = mock_baseline
        
        result = core_engine_with_analytics.update_player_baselines("test-puuid-123")
        
        assert result["success"] is True
        assert result["puuid"] == "test-puuid-123"
        assert result["matches_analyzed"] == 1
        assert result["baseline_updated"] is True
    
    def test_migrate_analytics_data_full(self, core_engine_with_analytics, sample_player):
        """Test full analytics data migration."""
        # Mock data manager to return players
        core_engine_with_analytics.data_manager.load_player_data.return_value = [sample_player]
        
        result = core_engine_with_analytics.migrate_analytics_data("full")
        
        assert result["success"] is True
        assert result["migration_type"] == "full"
        assert "Analytics cache cleared" in result["operations_performed"]
        assert "Baselines rebuilt for 1 players" in result["operations_performed"]
        assert len(result["errors"]) == 0
    
    def test_migrate_analytics_data_cache_only(self, core_engine_with_analytics):
        """Test cache-only analytics data migration."""
        result = core_engine_with_analytics.migrate_analytics_data("cache_only")
        
        assert result["success"] is True
        assert result["migration_type"] == "cache_only"
        assert "Analytics cache cleared" in result["operations_performed"]
        assert len(result["errors"]) == 0
    
    def test_analytics_health_status_all_online(self, core_engine_with_analytics):
        """Test analytics health status when all components are online."""
        health_status = core_engine_with_analytics._get_analytics_health_status()
        
        assert health_status["overall_status"] == "OK"
        assert all(status == "OK" for status in health_status["components"].values())
    
    def test_analytics_health_status_degraded(self, core_engine_with_analytics):
        """Test analytics health status when some components are offline."""
        # Set one component to None to simulate degraded state
        core_engine_with_analytics.baseline_manager = None
        
        health_status = core_engine_with_analytics._get_analytics_health_status()
        
        assert health_status["overall_status"] == "DEGRADED"
        assert health_status["components"]["baseline_manager"] == "OFFLINE"
        assert "Some analytics components are offline" in health_status["recommendations"]
    
    def test_analytics_health_status_offline(self, core_engine_with_analytics):
        """Test analytics health status when system is offline."""
        core_engine_with_analytics.analytics_available = False
        
        health_status = core_engine_with_analytics._get_analytics_health_status()
        
        assert health_status["overall_status"] == "OFFLINE"
        assert "Analytics system not initialized" in health_status["error"]
    
    def test_system_status_includes_analytics(self, core_engine_with_analytics):
        """Test that system status includes analytics information."""
        # Mock data manager and match manager
        core_engine_with_analytics.data_manager.load_player_data.return_value = []
        core_engine_with_analytics.match_manager.get_match_statistics.return_value = {
            'total_matches': 100,
            'total_players_indexed': 5,
            'oldest_match': '2024-01-01',
            'newest_match': '2024-01-31',
            'storage_file_size_mb': 10.5
        }
        core_engine_with_analytics.champion_data_manager.champions = {"1": "Annie"}
        
        status = core_engine_with_analytics._get_system_status()
        
        assert "analytics_available" in status
        assert "analytics_status" in status
        assert status["analytics_available"] is True
        assert status["analytics_status"]["available"] is True
        assert status["analytics_status"]["components_online"] == 6
        assert status["analytics_status"]["total_components"] == 6
    
    def test_system_diagnostics_includes_analytics(self, core_engine_with_analytics):
        """Test that system diagnostics includes analytics information."""
        # Mock required components
        core_engine_with_analytics.data_manager.load_player_data.return_value = []
        core_engine_with_analytics.champion_data_manager.champions = {"1": "Annie"}
        
        diagnostics = core_engine_with_analytics.get_system_diagnostics()
        
        assert "analytics_status" in diagnostics
        assert diagnostics["component_status"]["analytics"] == "OK"
        assert "analytics" in diagnostics["component_status"]
    
    def test_error_handling_in_analytics_methods(self, core_engine_with_analytics):
        """Test error handling in analytics methods."""
        # Make analytics engine raise an exception
        core_engine_with_analytics.historical_analytics_engine.analyze_player_performance.side_effect = Exception("Test error")
        
        result = core_engine_with_analytics.analyze_player_performance("test-puuid-123")
        
        assert "error" in result
        assert "Failed to analyze player performance" in result["error"]
    
    def test_analytics_methods_with_unavailable_system(self, core_engine_with_analytics):
        """Test all analytics methods when system is unavailable."""
        core_engine_with_analytics.analytics_available = False
        
        # Test all analytics methods
        methods_to_test = [
            ("analyze_player_performance", ("test-puuid",)),
            ("get_champion_recommendations", ("test-puuid", "middle")),
            ("calculate_performance_trends", ("test-puuid",)),
            ("generate_comparative_analysis", (["puuid1", "puuid2"], "win_rate")),
            ("get_analytics_cache_statistics", ()),
            ("invalidate_analytics_cache", ()),
            ("update_player_baselines", ("test-puuid",)),
            ("migrate_analytics_data", ())
        ]
        
        for method_name, args in methods_to_test:
            method = getattr(core_engine_with_analytics, method_name)
            result = method(*args)
            assert "error" in result
            assert "unavailable" in result["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__])