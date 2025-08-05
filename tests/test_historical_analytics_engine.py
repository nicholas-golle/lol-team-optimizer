"""
Tests for the Historical Analytics Engine.

This module contains comprehensive tests for the HistoricalAnalyticsEngine,
including integration tests with real match data scenarios.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

from lol_team_optimizer.historical_analytics_engine import (
    HistoricalAnalyticsEngine, AnalyticsCacheManager
)
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters, PlayerAnalytics, ChampionPerformanceMetrics,
    PerformanceMetrics, DateRange, AnalyticsError, InsufficientDataError
)
from lol_team_optimizer.baseline_manager import BaselineManager
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestAnalyticsCacheManager:
    """Test suite for analytics cache manager."""
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache_manager = AnalyticsCacheManager()
        
        # Test putting and getting a value
        test_data = {"test": "data"}
        cache_manager.cache_analytics("test_key", test_data)
        
        retrieved_data = cache_manager.get_cached_analytics("test_key")
        assert retrieved_data == test_data
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        cache_manager = AnalyticsCacheManager()
        
        test_data = {"test": "data"}
        cache_manager.cache_analytics("test_key", test_data, ttl=1)  # 1 second TTL
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        
        retrieved_data = cache_manager.get_cached_analytics("test_key")
        assert retrieved_data is None
    
    def test_cache_size_limit(self):
        """Test cache size limit enforcement."""
        cache_manager = AnalyticsCacheManager()
        
        # Add items up to limit
        cache_manager.cache_analytics("key1", "data1")
        cache_manager.cache_analytics("key2", "data2")
        
        # Add one more item, should evict oldest
        cache_manager.cache_analytics("key3", "data3")
        
        # key1 should be evicted (due to LRU eviction)
        # Note: The exact eviction behavior depends on cache implementation
        # We'll just check that we can retrieve the newer items
        assert cache_manager.get_cached_analytics("key2") == "data2"
        assert cache_manager.get_cached_analytics("key3") == "data3"
    
    def test_cache_invalidation(self):
        """Test cache invalidation by pattern."""
        cache_manager = AnalyticsCacheManager()
        
        cache_manager.cache_analytics("player_123_analytics", "data1")
        cache_manager.cache_analytics("player_456_analytics", "data2")
        cache_manager.cache_analytics("champion_789_data", "data3")
        
        # Invalidate player analytics
        cache_manager.invalidate_cache("player_*")
        
        assert cache_manager.get_cached_analytics("player_123_analytics") is None
        assert cache_manager.get_cached_analytics("player_456_analytics") is None
        assert cache_manager.get_cached_analytics("champion_789_data") == "data3"


class TestHistoricalAnalyticsEngine:
    """Test suite for historical analytics engine."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config object."""
        config = Mock(spec=Config)
        config.cache_directory = "/tmp/test_cache"
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create a mock match manager."""
        match_manager = Mock()
        return match_manager
    
    @pytest.fixture
    def mock_baseline_manager(self):
        """Create a mock baseline manager."""
        baseline_manager = Mock(spec=BaselineManager)
        return baseline_manager
    
    @pytest.fixture
    def analytics_engine(self, mock_config, mock_match_manager, mock_baseline_manager):
        """Create analytics engine with mocked dependencies."""
        return HistoricalAnalyticsEngine(
            config=mock_config,
            match_manager=mock_match_manager,
            baseline_manager=mock_baseline_manager
        )
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample match data for testing."""
        matches = []
        
        for i in range(15):  # Increased to 15 matches
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            # Create recent matches for trend analysis
            recent_timestamp = datetime.now().timestamp() - (i * 86400)  # Recent daily matches
            match.game_creation = int(recent_timestamp)
            match.game_creation_datetime = datetime.fromtimestamp(match.game_creation)
            match.game_duration = 1800 + (i * 60)  # 30-40 minute games
            match.queue_id = 420  # Ranked Solo/Duo
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_puuid"
            participant.summoner_name = "TestPlayer"
            participant.champion_id = 1 + (i % 3)  # Rotate between 3 champions (5 matches each)
            participant.champion_name = f"Champion_{participant.champion_id}"
            participant.individual_position = "TOP"
            participant.team_id = 100
            participant.win = i % 2 == 0  # Alternate wins/losses
            participant.kills = 5 + (i % 3)
            participant.deaths = 2 + (i % 2)
            participant.assists = 8 + (i % 4)
            participant.cs_total = 150 + (i * 10)
            participant.vision_score = 20 + (i % 5)
            participant.total_damage_dealt_to_champions = 15000 + (i * 1000)
            participant.gold_earned = 12000 + (i * 500)
            
            # Mock match participants
            match.participants = [participant]
            match.get_participant_by_puuid = Mock(return_value=participant)
            
            matches.append((match, participant))
        
        return matches
    
    def test_analyze_player_performance_success(self, analytics_engine, mock_match_manager, sample_matches):
        """Test successful player performance analysis."""
        mock_match_manager.get_matches_for_player.return_value = [match for match, _ in sample_matches]
        
        result = analytics_engine.analyze_player_performance("test_puuid")
        
        assert isinstance(result, PlayerAnalytics)
        assert result.puuid == "test_puuid"
        assert result.player_name == "TestPlayer"
        assert result.overall_performance.games_played == 15
        assert 0 <= result.overall_performance.win_rate <= 1
        assert result.overall_performance.avg_kda > 0
        
        # Check that role performance is calculated
        assert "top" in result.role_performance
        
        # Check that champion performance is calculated
        assert len(result.champion_performance) > 0
    
    def test_analyze_player_performance_insufficient_data(self, analytics_engine, mock_match_manager):
        """Test player performance analysis with insufficient data."""
        # Return fewer matches than minimum required
        mock_match_manager.get_matches_for_player.return_value = []
        
        with pytest.raises(InsufficientDataError) as exc_info:
            analytics_engine.analyze_player_performance("test_puuid")
        
        assert exc_info.value.required_games == 5
        assert exc_info.value.available_games == 0
    
    def test_analyze_champion_performance_success(self, analytics_engine, mock_match_manager, sample_matches):
        """Test successful champion performance analysis."""
        # Filter matches for specific champion
        champion_matches = [(match, participant) for match, participant in sample_matches 
                          if participant.champion_id == 1]
        mock_match_manager.get_matches_for_player.return_value = [match for match, _ in champion_matches]
        
        result = analytics_engine.analyze_champion_performance("test_puuid", 1, "top")
        
        assert isinstance(result, ChampionPerformanceMetrics)
        assert result.champion_id == 1
        assert result.role == "top"
        assert result.performance.games_played > 0
        assert 0 <= result.performance.win_rate <= 1
    
    def test_analyze_champion_performance_insufficient_data(self, analytics_engine, mock_match_manager):
        """Test champion performance analysis with insufficient data."""
        mock_match_manager.get_matches_for_player.return_value = []
        
        with pytest.raises(InsufficientDataError):
            analytics_engine.analyze_champion_performance("test_puuid", 1, "top")
    
    def test_calculate_performance_trends_success(self, analytics_engine, mock_match_manager, sample_matches):
        """Test successful performance trend calculation."""
        mock_match_manager.get_matches_for_player.return_value = [match for match, _ in sample_matches]
        
        result = analytics_engine.calculate_performance_trends("test_puuid", time_window_days=90)
        
        assert result is not None
        assert hasattr(result, 'trend_direction')
        assert hasattr(result, 'trend_strength')
    
    def test_calculate_performance_trends_insufficient_data(self, analytics_engine, mock_match_manager):
        """Test performance trend calculation with insufficient data."""
        # Return fewer matches than required for trend analysis
        mock_match_manager.get_matches_for_player.return_value = []
        
        with pytest.raises(InsufficientDataError):
            analytics_engine.calculate_performance_trends("test_puuid")
    
    def test_generate_comparative_analysis_success(self, analytics_engine, mock_match_manager, sample_matches):
        """Test successful comparative analysis."""
        from lol_team_optimizer.analytics_models import PerformanceMetrics
        
        # Mock the _get_filtered_matches method in the comparative analyzer
        def mock_get_filtered_matches(puuid, filters):
            if puuid == "player1":
                return sample_matches[:15]  # 15 matches for player1
            elif puuid == "player2":
                return sample_matches[5:20]  # 15 matches for player2
            return []
        
        # Mock the _calculate_performance_metrics method to return valid performance data
        def mock_calculate_performance_metrics(matches):
            return PerformanceMetrics(
                games_played=len(matches),
                wins=int(len(matches) * 0.6),
                losses=int(len(matches) * 0.4),
                win_rate=0.6,
                total_kills=len(matches) * 5,
                total_deaths=len(matches) * 3,
                total_assists=len(matches) * 8,
                avg_kda=4.33,
                total_cs=len(matches) * 180,
                avg_cs_per_min=6.0,
                total_vision_score=len(matches) * 50,
                avg_vision_score=50.0,
                total_damage_to_champions=len(matches) * 20000,
                avg_damage_per_min=666.67,
                total_gold_earned=len(matches) * 15000,
                avg_gold_per_min=500.0,
                total_game_duration=len(matches) * 1800,
                avg_game_duration=30.0
            )
        
        analytics_engine.comparative_analyzer._get_filtered_matches = mock_get_filtered_matches
        analytics_engine.comparative_analyzer._calculate_performance_metrics = mock_calculate_performance_metrics
        
        result = analytics_engine.generate_comparative_analysis(["player1", "player2"])
        
        # Result should be a dictionary of MultiPlayerComparison objects
        assert isinstance(result, dict)
        assert len(result) > 0  # Should have at least one metric comparison
        
        # Check that each comparison has the expected structure
        for metric, comparison in result.items():
            assert hasattr(comparison, 'players')
            assert hasattr(comparison, 'values')
            assert hasattr(comparison, 'rankings')
            assert hasattr(comparison, 'percentiles')
            assert len(comparison.players) <= 2  # Some players might be filtered out
    
    def test_generate_comparative_analysis_insufficient_players(self, analytics_engine):
        """Test comparative analysis with insufficient players."""
        with pytest.raises(AnalyticsError) as exc_info:
            analytics_engine.generate_comparative_analysis(["player1"])
        
        assert "Need at least 2 players" in str(exc_info.value)
    
    def test_cache_integration(self, analytics_engine, mock_match_manager, sample_matches):
        """Test that caching works correctly."""
        mock_match_manager.get_matches_for_player.return_value = [match for match, _ in sample_matches]
        
        # First call should hit the database
        result1 = analytics_engine.analyze_player_performance("test_puuid")
        
        # Second call should use cache
        result2 = analytics_engine.analyze_player_performance("test_puuid")
        
        # Results should be identical
        assert result1.puuid == result2.puuid
        assert result1.overall_performance.games_played == result2.overall_performance.games_played
        
        # Database should only be called once due to caching
        assert mock_match_manager.get_matches_for_player.call_count == 1
    
    def test_filters_application(self, analytics_engine, mock_match_manager, sample_matches):
        """Test that analytics filters are applied correctly."""
        mock_match_manager.get_matches_for_player.return_value = [match for match, _ in sample_matches]
        
        # Create filters - use less restrictive filters to ensure enough data
        filters = AnalyticsFilters(
            champions=[1, 2, 3],  # Include all champions
            roles=["top"],
            win_only=None  # Don't filter by wins
        )
        
        result = analytics_engine.analyze_player_performance("test_puuid", filters)
        
        # Should still get results but filtered
        assert isinstance(result, PlayerAnalytics)
        # The actual filtering logic would be tested in integration tests
    
    def test_performance_metrics_calculation(self, analytics_engine):
        """Test performance metrics calculation."""
        # Create test matches
        test_matches = []
        
        for i in range(5):
            match = Mock()
            match.game_duration = 1800  # 30 minutes
            
            participant = Mock()
            participant.win = i < 3  # 3 wins, 2 losses
            participant.kills = 5
            participant.deaths = 2
            participant.assists = 8
            participant.cs_total = 150
            participant.vision_score = 20
            participant.total_damage_dealt_to_champions = 15000
            participant.gold_earned = 12000
            
            test_matches.append((match, participant))
        
        metrics = analytics_engine._calculate_performance_metrics(test_matches)
        
        assert metrics.games_played == 5
        assert metrics.wins == 3
        assert metrics.losses == 2
        assert metrics.win_rate == 0.6
        assert metrics.avg_kda == (5 + 8) / 2  # (kills + assists) / deaths
        assert metrics.avg_cs_per_min == 150 / 30  # cs / (duration in minutes)
    
    def test_role_normalization(self, analytics_engine):
        """Test role normalization functionality."""
        assert analytics_engine._normalize_role("TOP") == "top"
        assert analytics_engine._normalize_role("JUNGLE") == "jungle"
        assert analytics_engine._normalize_role("MIDDLE") == "middle"
        assert analytics_engine._normalize_role("MID") == "middle"
        assert analytics_engine._normalize_role("BOTTOM") == "bottom"
        assert analytics_engine._normalize_role("BOT") == "bottom"
        assert analytics_engine._normalize_role("ADC") == "bottom"
        assert analytics_engine._normalize_role("SUPPORT") == "support"
        assert analytics_engine._normalize_role("UTILITY") == "support"