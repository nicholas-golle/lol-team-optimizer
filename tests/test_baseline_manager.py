"""
Tests for the BaselineManager module.

This module tests baseline calculation algorithms, caching mechanisms,
and edge cases for performance baseline management.
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from lol_team_optimizer.baseline_manager import (
    BaselineManager, BaselineContext, PlayerBaseline, ContextualBaseline,
    BaselineCache
)
from lol_team_optimizer.analytics_models import (
    PerformanceMetrics, ConfidenceInterval, InsufficientDataError,
    BaselineCalculationError
)
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestBaselineContext:
    """Test BaselineContext data class."""
    
    def test_valid_context_creation(self):
        """Test creating a valid baseline context."""
        context = BaselineContext(
            puuid="test_puuid",
            champion_id=1,
            role="middle",
            time_window_days=30
        )
        
        assert context.puuid == "test_puuid"
        assert context.champion_id == 1
        assert context.role == "middle"
        assert context.time_window_days == 30
    
    def test_invalid_puuid(self):
        """Test validation of empty PUUID."""
        with pytest.raises(ValueError, match="PUUID cannot be empty"):
            BaselineContext(puuid="")
    
    def test_invalid_role(self):
        """Test validation of invalid role."""
        with pytest.raises(ValueError, match="Invalid role"):
            BaselineContext(puuid="test_puuid", role="invalid_role")
    
    def test_invalid_time_window(self):
        """Test validation of invalid time window."""
        with pytest.raises(ValueError, match="Time window must be positive"):
            BaselineContext(puuid="test_puuid", time_window_days=0)
    
    def test_invalid_champion_id(self):
        """Test validation of invalid champion ID."""
        with pytest.raises(ValueError, match="Champion ID must be positive"):
            BaselineContext(puuid="test_puuid", champion_id=0)
    
    def test_cache_key_generation(self):
        """Test cache key generation for different contexts."""
        # Basic context
        context1 = BaselineContext(puuid="test_puuid")
        assert context1.cache_key == "test_puuid"
        
        # With champion and role
        context2 = BaselineContext(
            puuid="test_puuid",
            champion_id=1,
            role="middle"
        )
        assert "champ_1" in context2.cache_key
        assert "role_middle" in context2.cache_key
        
        # With time window
        context3 = BaselineContext(
            puuid="test_puuid",
            time_window_days=30
        )
        assert "time_30" in context3.cache_key
        
        # With team context
        context4 = BaselineContext(
            puuid="test_puuid",
            team_composition_context=["teammate1", "teammate2"]
        )
        assert "team_" in context4.cache_key


class TestPlayerBaseline:
    """Test PlayerBaseline data class."""
    
    def create_sample_baseline(self):
        """Create a sample baseline for testing."""
        context = BaselineContext(puuid="test_puuid")
        metrics = PerformanceMetrics(
            games_played=10,
            wins=6,
            losses=4,
            win_rate=0.6,
            avg_kda=2.5
        )
        confidence_interval = ConfidenceInterval(
            lower_bound=0.4,
            upper_bound=0.8,
            confidence_level=0.95,
            sample_size=10
        )
        
        return PlayerBaseline(
            puuid="test_puuid",
            context=context,
            baseline_metrics=metrics,
            sample_size=10,
            confidence_interval=confidence_interval,
            calculation_date=datetime.now()
        )
    
    def test_valid_baseline_creation(self):
        """Test creating a valid player baseline."""
        baseline = self.create_sample_baseline()
        
        assert baseline.puuid == "test_puuid"
        assert baseline.sample_size == 10
        assert baseline.baseline_metrics.win_rate == 0.6
    
    def test_invalid_puuid(self):
        """Test validation of empty PUUID."""
        context = BaselineContext(puuid="test_puuid")
        metrics = PerformanceMetrics()
        confidence_interval = ConfidenceInterval(
            lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
        )
        
        with pytest.raises(ValueError, match="PUUID cannot be empty"):
            PlayerBaseline(
                puuid="",
                context=context,
                baseline_metrics=metrics,
                sample_size=10,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now()
            )
    
    def test_invalid_sample_size(self):
        """Test validation of invalid sample size."""
        context = BaselineContext(puuid="test_puuid")
        metrics = PerformanceMetrics()
        confidence_interval = ConfidenceInterval(
            lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
        )
        
        with pytest.raises(ValueError, match="Sample size must be positive"):
            PlayerBaseline(
                puuid="test_puuid",
                context=context,
                baseline_metrics=metrics,
                sample_size=0,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now()
            )
    
    def test_context_puuid_mismatch(self):
        """Test validation of context PUUID mismatch."""
        context = BaselineContext(puuid="different_puuid")
        metrics = PerformanceMetrics()
        confidence_interval = ConfidenceInterval(
            lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
        )
        
        with pytest.raises(ValueError, match="Context PUUID must match baseline PUUID"):
            PlayerBaseline(
                puuid="test_puuid",
                context=context,
                baseline_metrics=metrics,
                sample_size=10,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now()
            )
    
    def test_is_stale(self):
        """Test staleness detection."""
        baseline = self.create_sample_baseline()
        
        # Fresh baseline should not be stale
        assert not baseline.is_stale(max_age_days=7)
        
        # Old baseline should be stale
        old_baseline = self.create_sample_baseline()
        old_baseline.calculation_date = datetime.now() - timedelta(days=10)
        assert old_baseline.is_stale(max_age_days=7)
    
    def test_reliability_score(self):
        """Test reliability score calculation."""
        baseline = self.create_sample_baseline()
        
        # Fresh baseline with decent sample size should have good reliability
        reliability = baseline.reliability_score
        assert 0 < reliability <= 1
        
        # Old baseline should have lower reliability
        old_baseline = self.create_sample_baseline()
        old_baseline.calculation_date = datetime.now() - timedelta(days=20)
        old_reliability = old_baseline.reliability_score
        assert old_reliability < reliability


class TestBaselineCache:
    """Test BaselineCache functionality."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = BaselineCache(cache_dir)
            
            # Create sample baseline
            context = BaselineContext(puuid="test_puuid")
            metrics = PerformanceMetrics(games_played=10, win_rate=0.6)
            confidence_interval = ConfidenceInterval(
                lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
            )
            baseline = PlayerBaseline(
                puuid="test_puuid",
                context=context,
                baseline_metrics=metrics,
                sample_size=10,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now()
            )
            
            # Test put and get
            cache_key = "test_key"
            cache.put(cache_key, baseline)
            retrieved = cache.get(cache_key)
            
            assert retrieved is not None
            assert retrieved.puuid == baseline.puuid
            assert retrieved.baseline_metrics.win_rate == baseline.baseline_metrics.win_rate
    
    def test_cache_persistence(self):
        """Test cache persistence across instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            
            # Create and populate first cache instance
            cache1 = BaselineCache(cache_dir)
            context = BaselineContext(puuid="test_puuid")
            metrics = PerformanceMetrics(games_played=10, win_rate=0.6)
            confidence_interval = ConfidenceInterval(
                lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
            )
            baseline = PlayerBaseline(
                puuid="test_puuid",
                context=context,
                baseline_metrics=metrics,
                sample_size=10,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now()
            )
            
            cache_key = "test_key"
            cache1.put(cache_key, baseline)
            
            # Create second cache instance and verify data persisted
            cache2 = BaselineCache(cache_dir)
            retrieved = cache2.get(cache_key)
            
            assert retrieved is not None
            assert retrieved.puuid == baseline.puuid
    
    def test_stale_baseline_removal(self):
        """Test automatic removal of stale baselines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = BaselineCache(cache_dir)
            
            # Create stale baseline
            context = BaselineContext(puuid="test_puuid")
            metrics = PerformanceMetrics(games_played=10, win_rate=0.6)
            confidence_interval = ConfidenceInterval(
                lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
            )
            stale_baseline = PlayerBaseline(
                puuid="test_puuid",
                context=context,
                baseline_metrics=metrics,
                sample_size=10,
                confidence_interval=confidence_interval,
                calculation_date=datetime.now() - timedelta(days=10)
            )
            
            cache_key = "stale_key"
            cache.memory_cache[cache_key] = stale_baseline
            
            # Get should return None for stale baseline
            retrieved = cache.get(cache_key)
            assert retrieved is None
            assert cache_key not in cache.memory_cache
    
    def test_invalidate_player_baselines(self):
        """Test invalidating all baselines for a player."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)
            cache = BaselineCache(cache_dir)
            
            # Add multiple baselines for the same player
            puuid = "test_puuid"
            for i in range(3):
                context = BaselineContext(puuid=puuid, champion_id=i+1)
                metrics = PerformanceMetrics(games_played=10, win_rate=0.6)
                confidence_interval = ConfidenceInterval(
                    lower_bound=0.4, upper_bound=0.8, confidence_level=0.95, sample_size=10
                )
                baseline = PlayerBaseline(
                    puuid=puuid,
                    context=context,
                    baseline_metrics=metrics,
                    sample_size=10,
                    confidence_interval=confidence_interval,
                    calculation_date=datetime.now()
                )
                cache.put(f"{puuid}_champ_{i+1}", baseline)
            
            # Verify baselines exist
            assert len(cache.memory_cache) == 3
            
            # Invalidate player baselines
            cache.invalidate(puuid)
            
            # Verify all baselines for player are removed
            assert len(cache.memory_cache) == 0


class TestBaselineManager:
    """Test BaselineManager functionality."""
    
    def create_mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "/tmp/test_cache"
        config.data_directory = "/tmp/test_data"
        return config
    
    def create_mock_match_manager(self):
        """Create a mock match manager."""
        match_manager = Mock()
        return match_manager
    
    def create_sample_matches(self, puuid: str, count: int = 10) -> list:
        """Create sample matches for testing."""
        matches = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(count):
            # Create match
            match = Match(
                match_id=f"match_{i}",
                game_creation=int((base_time + timedelta(days=i)).timestamp() * 1000),
                game_duration=1800,  # 30 minutes
                game_end_timestamp=int((base_time + timedelta(days=i) + timedelta(minutes=30)).timestamp() * 1000),
                queue_id=420  # Ranked Solo
            )
            
            # Create participant
            participant = MatchParticipant(
                puuid=puuid,
                summoner_name="TestPlayer",
                champion_id=1,
                champion_name="TestChampion",
                team_id=100,
                individual_position="MIDDLE",
                kills=5 + i % 3,
                deaths=3 + i % 2,
                assists=8 + i % 4,
                total_damage_dealt_to_champions=20000 + i * 1000,
                total_minions_killed=150 + i * 5,
                neutral_minions_killed=20 + i,
                vision_score=25 + i,
                gold_earned=12000 + i * 500,
                win=i % 2 == 0  # Alternate wins/losses
            )
            
            match.participants = [participant]
            matches.append(match)
        
        return matches
    
    @patch('lol_team_optimizer.baseline_manager.BaselineCache')
    def test_baseline_manager_initialization(self, mock_cache_class):
        """Test BaselineManager initialization."""
        config = self.create_mock_config()
        match_manager = self.create_mock_match_manager()
        
        manager = BaselineManager(config, match_manager)
        
        assert manager.config == config
        assert manager.match_manager == match_manager
        assert manager.min_games_for_baseline == 5
        mock_cache_class.assert_called_once()
    
    def test_insufficient_data_error(self):
        """Test handling of insufficient data for baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            # Return insufficient matches
            match_manager.get_matches_for_player.return_value = self.create_sample_matches("test_puuid", 2)
            
            manager = BaselineManager(config, match_manager)
            context = BaselineContext(puuid="test_puuid")
            
            with pytest.raises(InsufficientDataError):
                manager.calculate_player_baseline(context)
    
    def test_successful_baseline_calculation(self):
        """Test successful baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            context = BaselineContext(puuid="test_puuid")
            
            baseline = manager.calculate_player_baseline(context)
            
            assert baseline.puuid == "test_puuid"
            assert baseline.sample_size == 10
            assert 0 <= baseline.baseline_metrics.win_rate <= 1
            assert baseline.baseline_metrics.avg_kda > 0
    
    def test_overall_baseline(self):
        """Test overall baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            baseline = manager.get_overall_baseline("test_puuid")
            
            assert baseline.puuid == "test_puuid"
            assert baseline.context.champion_id is None
            assert baseline.context.role is None
    
    def test_role_specific_baseline(self):
        """Test role-specific baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            baseline = manager.get_role_specific_baseline("test_puuid", "middle")
            
            assert baseline.puuid == "test_puuid"
            assert baseline.context.role == "middle"
    
    def test_champion_specific_baseline(self):
        """Test champion-specific baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            baseline = manager.get_champion_specific_baseline("test_puuid", 1, "middle")
            
            assert baseline.puuid == "test_puuid"
            assert baseline.context.champion_id == 1
            assert baseline.context.role == "middle"
    
    def test_contextual_baseline(self):
        """Test contextual baseline calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            contextual_baseline = manager.get_contextual_baseline(
                "test_puuid", 1, "middle", ["teammate1", "teammate2"]
            )
            
            assert contextual_baseline.puuid == "test_puuid"
            assert contextual_baseline.champion_id == 1
            assert contextual_baseline.role == "middle"
            assert isinstance(contextual_baseline.synergy_adjustments, dict)
    
    def test_performance_delta_calculation(self):
        """Test performance delta calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            # Get baseline
            baseline = manager.get_overall_baseline("test_puuid")
            
            # Create performance metrics
            performance = PerformanceMetrics(
                games_played=5,
                wins=4,
                losses=1,
                win_rate=0.8,
                avg_kda=3.0
            )
            
            # Calculate deltas
            deltas = manager.calculate_performance_delta(performance, baseline)
            
            assert "win_rate" in deltas
            assert "avg_kda" in deltas
            
            win_rate_delta = deltas["win_rate"]
            assert win_rate_delta.metric_name == "win_rate"
            assert win_rate_delta.actual_value == 0.8
            assert win_rate_delta.baseline_value == baseline.baseline_metrics.win_rate
    
    def test_temporal_weighting(self):
        """Test temporal weighting application."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            # Test with temporal weighting
            baseline_with_weighting = manager.get_overall_baseline("test_puuid", time_window_days=30)
            baseline_without_weighting = manager.get_overall_baseline("test_puuid")
            
            assert baseline_with_weighting.temporal_weight_applied
            assert not baseline_without_weighting.temporal_weight_applied
    
    def test_baseline_caching(self):
        """Test baseline caching functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            # First call should calculate baseline
            baseline1 = manager.get_overall_baseline("test_puuid")
            
            # Second call should use cache (match_manager should only be called once)
            baseline2 = manager.get_overall_baseline("test_puuid")
            
            assert baseline1.puuid == baseline2.puuid
            assert baseline1.baseline_metrics.win_rate == baseline2.baseline_metrics.win_rate
            
            # Verify match manager was only called once
            assert match_manager.get_matches_for_player.call_count == 1
    
    def test_baseline_update_invalidation(self):
        """Test baseline cache invalidation on updates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            # Calculate initial baseline
            baseline1 = manager.get_overall_baseline("test_puuid")
            
            # Update with new matches
            new_matches = self.create_sample_matches("test_puuid", 2)
            manager.update_baselines("test_puuid", new_matches)
            
            # Next call should recalculate (cache invalidated)
            baseline2 = manager.get_overall_baseline("test_puuid")
            
            # Verify match manager was called twice (once for each baseline calculation)
            assert match_manager.get_matches_for_player.call_count == 2
    
    def test_baseline_statistics(self):
        """Test baseline statistics reporting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            matches = self.create_sample_matches("test_puuid", 10)
            match_manager.get_matches_for_player.return_value = matches
            
            manager = BaselineManager(config, match_manager)
            
            # Calculate some baselines
            manager.get_overall_baseline("test_puuid")
            manager.get_role_specific_baseline("test_puuid", "middle")
            manager.get_champion_specific_baseline("test_puuid", 1, "middle")
            
            # Get statistics
            stats = manager.get_baseline_statistics()
            
            assert stats["total_baselines"] == 3
            assert stats["overall_baselines"] >= 1
            assert stats["role_specific_baselines"] >= 1
            assert stats["champion_specific_baselines"] >= 1
            assert stats["average_sample_size"] > 0
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self.create_mock_config()
            config.cache_directory = temp_dir
            
            match_manager = self.create_mock_match_manager()
            
            manager = BaselineManager(config, match_manager)
            
            # Test with no matches
            match_manager.get_matches_for_player.return_value = []
            context = BaselineContext(puuid="test_puuid")
            
            with pytest.raises(InsufficientDataError):
                manager.calculate_player_baseline(context)
            
            # Test with matches but no participant data
            empty_match = Match(match_id="empty", game_creation=0, game_duration=0, game_end_timestamp=0)
            empty_match.participants = []
            match_manager.get_matches_for_player.return_value = [empty_match]
            
            with pytest.raises(InsufficientDataError):
                manager.calculate_player_baseline(context)


if __name__ == "__main__":
    pytest.main([__file__])