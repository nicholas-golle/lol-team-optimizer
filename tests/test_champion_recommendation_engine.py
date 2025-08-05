"""
Unit tests for the Champion Recommendation Engine.

Tests the champion recommendation scoring algorithm, team synergy analysis,
and various edge cases for the recommendation system.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, List

from lol_team_optimizer.champion_recommendation_engine import (
    ChampionRecommendationEngine, RecommendationScore, TeamSynergyContext
)
from lol_team_optimizer.analytics_models import (
    ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
    PerformanceMetrics, PerformanceDelta, RecentFormMetrics,
    PlayerRoleAssignment, AnalyticsFilters, DateRange,
    AnalyticsError, InsufficientDataError, ConfidenceInterval,
    SynergyAnalysis
)
from lol_team_optimizer.config import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)
    config.cache_directory = "/tmp/test_cache"
    return config


@pytest.fixture
def mock_analytics_engine():
    """Create mock analytics engine."""
    return Mock()


@pytest.fixture
def mock_champion_data_manager():
    """Create mock champion data manager."""
    manager = Mock()
    manager.get_champions_by_role.return_value = [1, 2, 3, 4, 5]
    manager.get_champion_name.side_effect = lambda x: f"Champion_{x}"
    return manager


@pytest.fixture
def mock_baseline_manager():
    """Create mock baseline manager."""
    return Mock()


@pytest.fixture
def recommendation_engine(mock_config, mock_analytics_engine, 
                        mock_champion_data_manager, mock_baseline_manager):
    """Create recommendation engine instance."""
    return ChampionRecommendationEngine(
        config=mock_config,
        analytics_engine=mock_analytics_engine,
        champion_data_manager=mock_champion_data_manager,
        baseline_manager=mock_baseline_manager
    )


@pytest.fixture
def sample_champion_performance():
    """Create sample champion performance metrics."""
    performance = PerformanceMetrics(
        games_played=20,
        wins=12,
        losses=8,
        win_rate=0.6,
        total_kills=120,
        total_deaths=80,
        total_assists=200,
        avg_kda=2.5,
        total_cs=3000,
        avg_cs_per_min=6.5,
        total_vision_score=400,
        avg_vision_score=20.0,
        total_damage_to_champions=200000,
        avg_damage_per_min=1500,
        total_gold_earned=240000,
        avg_gold_per_min=400,
        total_game_duration=7200,
        avg_game_duration=30.0
    )
    
    recent_form = RecentFormMetrics(
        recent_games=10,
        recent_win_rate=0.7,
        recent_avg_kda=2.8,
        trend_direction="improving",
        trend_strength=0.6,
        form_score=0.3
    )
    
    return ChampionPerformanceMetrics(
        champion_id=1,
        champion_name="TestChampion",
        role="middle",
        performance=performance,
        recent_form=recent_form,
        confidence_scores={"overall": 0.8}
    )


@pytest.fixture
def sample_team_context():
    """Create sample team context."""
    existing_picks = {
        "top": PlayerRoleAssignment(
            puuid="player1",
            player_name="Player1",
            role="top",
            champion_id=10,
            champion_name="TopChampion"
        ),
        "jungle": PlayerRoleAssignment(
            puuid="player2",
            player_name="Player2",
            role="jungle",
            champion_id=20,
            champion_name="JungleChampion"
        )
    }
    
    return TeamContext(
        existing_picks=existing_picks,
        target_role="middle",
        target_player_puuid="target_player",
        available_champions=[1, 2, 3],
        banned_champions=[99, 100]
    )


class TestChampionRecommendationEngine:
    """Test suite for ChampionRecommendationEngine."""


class TestRecommendationScoring:
    """Test recommendation scoring algorithms."""
    
    def test_calculate_recommendation_score_success(self, recommendation_engine, 
                                                  sample_champion_performance):
        """Test successful recommendation score calculation."""
        # Setup mocks
        recommendation_engine.analytics_engine.analyze_champion_performance.return_value = sample_champion_performance
        
        # Calculate score
        score = recommendation_engine.calculate_recommendation_score(
            puuid="test_player",
            champion_id=1,
            role="middle"
        )
        
        # Verify score structure
        assert isinstance(score, RecommendationScore)
        assert score.champion_id == 1
        assert 0.0 <= score.total_score <= 1.0
        assert 0.0 <= score.individual_performance_score <= 1.0
        assert 0.0 <= score.team_synergy_score <= 1.0
        assert 0.0 <= score.recent_form_score <= 1.0
        assert 0.0 <= score.meta_relevance_score <= 1.0
        assert 0.0 <= score.confidence_score <= 1.0
        assert score.games_played == 20
    
    def test_calculate_recommendation_score_insufficient_data(self, recommendation_engine):
        """Test recommendation score calculation with insufficient data."""
        # Setup mock to raise InsufficientDataError
        recommendation_engine.analytics_engine.analyze_champion_performance.side_effect = InsufficientDataError(
            required_games=5, available_games=2
        )
        
        # Should raise InsufficientDataError
        with pytest.raises(InsufficientDataError):
            recommendation_engine.calculate_recommendation_score(
                puuid="test_player",
                champion_id=1,
                role="middle"
            )
    
    def test_individual_performance_score_calculation(self, recommendation_engine, 
                                                    sample_champion_performance):
        """Test individual performance score calculation."""
        score = recommendation_engine._calculate_individual_performance_score(
            sample_champion_performance, "test_player", 1, "middle"
        )
        
        assert 0.0 <= score <= 1.0
        # With 60% win rate and 2.5 KDA, should be above average
        assert score > 0.5
    
    def test_individual_performance_score_with_baseline(self, recommendation_engine):
        """Test individual performance score with baseline comparison."""
        # Create performance with baseline deltas
        performance = PerformanceMetrics(
            games_played=15,
            wins=10,
            losses=5,
            win_rate=0.67
        )
        
        performance_vs_baseline = {
            'win_rate': PerformanceDelta(
                metric_name='win_rate',
                baseline_value=0.5,
                actual_value=0.67,
                delta_percentage=34.0
            ),
            'avg_kda': PerformanceDelta(
                metric_name='avg_kda',
                baseline_value=1.5,
                actual_value=2.0,
                delta_percentage=33.3
            )
        }
        
        champion_performance = ChampionPerformanceMetrics(
            champion_id=1,
            champion_name="TestChampion",
            role="middle",
            performance=performance,
            performance_vs_baseline=performance_vs_baseline
        )
        
        score = recommendation_engine._calculate_individual_performance_score(
            champion_performance, "test_player", 1, "middle"
        )
        
        assert 0.0 <= score <= 1.0
        # Should be above average due to positive baseline deltas
        assert score > 0.5
    
    def test_team_synergy_score_no_context(self, recommendation_engine):
        """Test team synergy score with no team context."""
        score = recommendation_engine._calculate_team_synergy_score(
            champion_id=1,
            role="middle",
            team_context=None,
            puuid="test_player"
        )
        
        assert score == 0.5  # Should return neutral score
    
    def test_team_synergy_score_with_context(self, recommendation_engine, sample_team_context):
        """Test team synergy score with team context."""
        # Mock champion pair synergy calculation
        recommendation_engine._calculate_champion_pair_synergy = Mock(return_value=0.3)
        
        score = recommendation_engine._calculate_team_synergy_score(
            champion_id=1,
            role="middle",
            team_context=sample_team_context,
            puuid="test_player"
        )
        
        assert 0.0 <= score <= 1.0
        # Should call synergy calculation for each existing pick
        assert recommendation_engine._calculate_champion_pair_synergy.call_count == 2
    
    def test_recent_form_score_calculation(self, recommendation_engine):
        """Test recent form score calculation."""
        # Test improving form
        improving_form = RecentFormMetrics(
            recent_games=10,
            recent_win_rate=0.7,
            recent_avg_kda=2.5,
            trend_direction="improving",
            trend_strength=0.8,
            form_score=0.4
        )
        
        score = recommendation_engine._calculate_recent_form_score(improving_form)
        assert 0.0 <= score <= 1.0
        assert score > 0.7  # Should be high for improving form
        
        # Test declining form
        declining_form = RecentFormMetrics(
            recent_games=10,
            recent_win_rate=0.3,
            recent_avg_kda=1.2,
            trend_direction="declining",
            trend_strength=0.6,
            form_score=-0.3
        )
        
        score = recommendation_engine._calculate_recent_form_score(declining_form)
        assert 0.0 <= score <= 1.0
        assert score < 0.4  # Should be low for declining form
    
    def test_recent_form_score_no_data(self, recommendation_engine):
        """Test recent form score with no data."""
        score = recommendation_engine._calculate_recent_form_score(None)
        assert score == 0.5  # Should return neutral score
    
    def test_confidence_score_calculation(self, recommendation_engine, sample_champion_performance):
        """Test confidence score calculation."""
        confidence, quality, penalty = recommendation_engine._calculate_confidence_score(
            sample_champion_performance
        )
        
        assert 0.0 <= confidence <= 1.0
        assert 0.0 <= quality <= 1.0
        assert 0.0 <= penalty <= 1.0
        
        # With 20 games, should have high confidence
        assert confidence > 0.6
    
    def test_confidence_score_low_games(self, recommendation_engine):
        """Test confidence score with low game count."""
        performance = PerformanceMetrics(games_played=3)
        champion_performance = ChampionPerformanceMetrics(
            champion_id=1,
            champion_name="TestChampion",
            role="middle",
            performance=performance
        )
        
        confidence, quality, penalty = recommendation_engine._calculate_confidence_score(
            champion_performance
        )
        
        # Should have low confidence and high penalty
        assert confidence < 0.5
        assert penalty > 0.1


class TestChampionRecommendations:
    """Test champion recommendation generation."""
    
    def test_get_champion_recommendations_success(self, recommendation_engine, 
                                                sample_champion_performance):
        """Test successful champion recommendations generation."""
        # Setup mocks
        recommendation_engine.analytics_engine.analyze_champion_performance.return_value = sample_champion_performance
        recommendation_engine._generate_single_recommendation = Mock(
            return_value=ChampionRecommendation(
                champion_id=1,
                champion_name="TestChampion",
                role="middle",
                recommendation_score=0.8,
                confidence=0.7
            )
        )
        
        recommendations = recommendation_engine.get_champion_recommendations(
            puuid="test_player",
            role="middle",
            max_recommendations=3
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        assert all(isinstance(rec, ChampionRecommendation) for rec in recommendations)
        
        # Should be sorted by score (descending)
        if len(recommendations) > 1:
            for i in range(len(recommendations) - 1):
                assert recommendations[i].recommendation_score >= recommendations[i + 1].recommendation_score
    
    def test_get_champion_recommendations_no_available_champions(self, recommendation_engine):
        """Test recommendations with no available champions."""
        recommendation_engine.champion_data_manager.get_champions_by_role.return_value = []
        
        with pytest.raises(AnalyticsError, match="No available champions found"):
            recommendation_engine.get_champion_recommendations(
                puuid="test_player",
                role="middle"
            )
    
    def test_get_champion_recommendations_insufficient_data(self, recommendation_engine):
        """Test recommendations with insufficient data for all champions."""
        recommendation_engine._generate_single_recommendation = Mock(return_value=None)
        
        with pytest.raises(InsufficientDataError):
            recommendation_engine.get_champion_recommendations(
                puuid="test_player",
                role="middle"
            )
    
    def test_get_champion_recommendations_with_team_context(self, recommendation_engine, 
                                                          sample_team_context,
                                                          sample_champion_performance):
        """Test recommendations with team context filtering."""
        # Setup mocks
        recommendation_engine.analytics_engine.analyze_champion_performance.return_value = sample_champion_performance
        recommendation_engine._generate_single_recommendation = Mock(
            return_value=ChampionRecommendation(
                champion_id=1,
                champion_name="TestChampion",
                role="middle",
                recommendation_score=0.8,
                confidence=0.7
            )
        )
        
        recommendations = recommendation_engine.get_champion_recommendations(
            puuid="test_player",
            role="middle",
            team_context=sample_team_context
        )
        
        assert isinstance(recommendations, list)
        # Should only consider available champions (1, 2, 3) and exclude banned (99, 100)
        recommendation_engine._generate_single_recommendation.assert_called()
    
    def test_get_champion_recommendations_custom_weights(self, recommendation_engine,
                                                       sample_champion_performance):
        """Test recommendations with custom scoring weights."""
        custom_weights = {
            'individual_performance': 0.5,
            'team_synergy': 0.2,
            'recent_form': 0.1,
            'meta_relevance': 0.1,
            'confidence': 0.1
        }
        
        recommendation_engine.analytics_engine.analyze_champion_performance.return_value = sample_champion_performance
        recommendation_engine._generate_single_recommendation = Mock(
            return_value=ChampionRecommendation(
                champion_id=1,
                champion_name="TestChampion",
                role="middle",
                recommendation_score=0.8,
                confidence=0.7
            )
        )
        
        recommendations = recommendation_engine.get_champion_recommendations(
            puuid="test_player",
            role="middle",
            custom_weights=custom_weights
        )
        
        assert isinstance(recommendations, list)
        # Verify custom weights were passed to single recommendation generation
        recommendation_engine._generate_single_recommendation.assert_called()


class TestSynergyAnalysis:
    """Test champion synergy analysis."""
    
    def test_analyze_champion_synergies(self, recommendation_engine):
        """Test champion synergy analysis."""
        champion_combinations = [(1, 2), (1, 3), (2, 3)]
        
        # Mock synergy calculation
        recommendation_engine._calculate_champion_pair_synergy = Mock(return_value=0.3)
        
        synergies = recommendation_engine.analyze_champion_synergies(champion_combinations)
        
        assert isinstance(synergies, dict)
        assert len(synergies) == 3
        assert all(isinstance(key, tuple) for key in synergies.keys())
        assert all(-1.0 <= value <= 1.0 for value in synergies.values())
        
        # Should call synergy calculation for each pair
        assert recommendation_engine._calculate_champion_pair_synergy.call_count == 3
    
    def test_analyze_champion_synergies_with_errors(self, recommendation_engine):
        """Test synergy analysis with calculation errors."""
        champion_combinations = [(1, 2), (1, 3)]
        
        # Mock synergy calculation to raise error for first pair
        def side_effect(champ1, champ2, context=None):
            if champ1 == 1 and champ2 == 2:
                raise Exception("Calculation error")
            return 0.5
        
        recommendation_engine._calculate_champion_pair_synergy = Mock(side_effect=side_effect)
        
        synergies = recommendation_engine.analyze_champion_synergies(champion_combinations)
        
        assert len(synergies) == 2
        assert synergies[(1, 2)] == 0.0  # Should default to 0.0 on error
        assert synergies[(1, 3)] == 0.5  # Should work normally
    
    def test_champion_pair_synergy_calculation(self, recommendation_engine):
        """Test champion pair synergy calculation."""
        # Mock the analytics engine match manager
        recommendation_engine.analytics_engine.match_manager.get_matches_with_champions = Mock(return_value=[])
        
        synergy = recommendation_engine._calculate_champion_pair_synergy(1, 2)
        
        assert -1.0 <= synergy <= 1.0
    
    def test_historical_champion_synergy_analysis(self, recommendation_engine):
        """Test historical champion synergy analysis."""
        # Mock match data with both champions winning together
        mock_matches = [
            {'win': True}, {'win': True}, {'win': False}, 
            {'win': True}, {'win': True}  # 4/5 wins = 80% win rate
        ]
        
        # Mock individual champion performance (50% win rate each)
        individual_matches = [
            {'win': True}, {'win': False}, {'win': True}, {'win': False}  # 50% win rate
        ]
        
        recommendation_engine.analytics_engine.match_manager.get_matches_with_champions = Mock(
            side_effect=lambda champs, same_team=False: mock_matches if len(champs) == 2 else individual_matches
        )
        
        synergy = recommendation_engine._analyze_historical_champion_synergy(1, 2)
        
        # 80% together vs 50% individual = +30% synergy = +0.6 synergy score
        assert synergy > 0.0
        assert synergy <= 1.0
    
    def test_role_synergy_adjustment(self, recommendation_engine):
        """Test role-specific synergy adjustments."""
        # Test high synergy roles
        role_context = {1: 'support', 2: 'bottom'}
        synergy = recommendation_engine._calculate_role_synergy_adjustment(1, 2, role_context)
        assert synergy > 0.0  # Support-ADC should have positive synergy
        
        # Test neutral roles
        role_context = {1: 'top', 2: 'middle'}
        synergy = recommendation_engine._calculate_role_synergy_adjustment(1, 2, role_context)
        assert synergy == 0.0  # Top-mid should be neutral
        
        # Test missing role context
        synergy = recommendation_engine._calculate_role_synergy_adjustment(1, 2, {})
        assert synergy == 0.0


class TestMetaAdjustments:
    """Test meta-based recommendation adjustments."""
    
    def test_get_meta_adjusted_recommendations(self, recommendation_engine):
        """Test meta adjustment of recommendations."""
        base_recommendations = [
            ChampionRecommendation(
                champion_id=1,
                champion_name="Champion1",
                role="middle",
                recommendation_score=0.8,
                confidence=0.7
            ),
            ChampionRecommendation(
                champion_id=2,
                champion_name="Champion2",
                role="middle",
                recommendation_score=0.6,
                confidence=0.8
            )
        ]
        
        # Mock meta adjustment
        recommendation_engine._calculate_meta_adjustment = Mock(return_value=1.2)
        
        adjusted = recommendation_engine.get_meta_adjusted_recommendations(
            base_recommendations, meta_emphasis=1.5
        )
        
        assert len(adjusted) == 2
        assert all(isinstance(rec, ChampionRecommendation) for rec in adjusted)
        
        # Scores should be adjusted
        assert adjusted[0].recommendation_score == 0.8 * 1.2
        assert adjusted[1].recommendation_score == 0.6 * 1.2
        
        # Should still be sorted by score
        assert adjusted[0].recommendation_score >= adjusted[1].recommendation_score
    
    def test_meta_adjustment_calculation(self, recommendation_engine):
        """Test meta adjustment calculation."""
        adjustment = recommendation_engine._calculate_meta_adjustment(1, 1.0)
        
        assert 0.5 <= adjustment <= 1.5
        # Current implementation returns 1.0 (neutral)
        assert adjustment == 1.0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_champion_list(self, recommendation_engine):
        """Test handling of empty champion list."""
        recommendation_engine.champion_data_manager.get_champions_by_role.return_value = []
        
        with pytest.raises(AnalyticsError):
            recommendation_engine.get_champion_recommendations("test_player", "middle")
    
    def test_invalid_role(self, recommendation_engine):
        """Test handling of invalid role."""
        # Invalid role should result in no available champions
        recommendation_engine.champion_data_manager.get_champions_by_role.return_value = []
        
        with pytest.raises(AnalyticsError, match="No available champions found"):
            recommendation_engine.get_champion_recommendations("test_player", "invalid_role")
    
    def test_analytics_engine_failure(self, recommendation_engine):
        """Test handling of analytics engine failures."""
        recommendation_engine.analytics_engine.analyze_champion_performance.side_effect = Exception("Engine failure")
        
        # Should handle gracefully and raise InsufficientDataError when all champions fail
        with pytest.raises(InsufficientDataError):
            recommendation_engine.get_champion_recommendations("test_player", "middle")
    
    def test_missing_champion_name(self, recommendation_engine, sample_champion_performance):
        """Test handling of missing champion name."""
        recommendation_engine.champion_data_manager.get_champion_name.return_value = None
        recommendation_engine.analytics_engine.analyze_champion_performance.return_value = sample_champion_performance
        
        # Should use fallback name
        score = recommendation_engine.calculate_recommendation_score("test_player", 999, "middle")
        assert isinstance(score, RecommendationScore)


class TestPerformanceProjection:
    """Test performance projection generation."""
    
    def test_generate_performance_projection(self, recommendation_engine, sample_champion_performance):
        """Test performance projection generation."""
        score_breakdown = RecommendationScore(
            champion_id=1,
            total_score=0.8,
            individual_performance_score=0.7,
            team_synergy_score=0.6,
            recent_form_score=0.8,
            meta_relevance_score=0.5,
            confidence_score=0.7,
            performance_weight=0.35,
            synergy_weight=0.25,
            form_weight=0.20,
            meta_weight=0.10,
            confidence_weight=0.10,
            games_played=20,
            data_quality_score=0.8,
            sample_size_penalty=0.1
        )
        
        projection = recommendation_engine._generate_performance_projection(
            sample_champion_performance, score_breakdown
        )
        
        assert 0.0 <= projection.expected_win_rate <= 1.0
        assert projection.expected_kda >= 0.0
        assert projection.expected_cs_per_min >= 0.0
        assert projection.expected_vision_score >= 0.0
        assert isinstance(projection.confidence_interval, ConfidenceInterval)
        assert projection.projection_basis in ["historical", "similar_champions", "baseline_adjusted"]


class TestTeamContextIntegration:
    """Test team context integration for recommendations."""
    
    def test_ally_synergy_score_calculation(self, recommendation_engine, sample_team_context):
        """Test ally synergy score calculation."""
        # Mock champion pair synergy
        recommendation_engine._calculate_champion_pair_synergy = Mock(return_value=0.4)
        
        synergy_score = recommendation_engine._calculate_ally_synergy_score(
            champion_id=1,
            role="middle",
            team_context=sample_team_context
        )
        
        assert 0.0 <= synergy_score <= 1.0
        # Should call synergy calculation for each existing pick
        assert recommendation_engine._calculate_champion_pair_synergy.call_count == 2
        
        # With 0.4 synergy, normalized score should be (0.4 + 1.0) / 2.0 = 0.7
        assert abs(synergy_score - 0.7) < 0.01
    
    def test_ally_synergy_score_no_existing_picks(self, recommendation_engine):
        """Test ally synergy score with no existing picks."""
        team_context = TeamContext(
            existing_picks={},
            target_role="middle",
            target_player_puuid="test_player"
        )
        
        synergy_score = recommendation_engine._calculate_ally_synergy_score(
            champion_id=1,
            role="middle",
            team_context=team_context
        )
        
        assert synergy_score == 0.5  # Should return neutral score
    
    def test_counter_pick_score_calculation(self, recommendation_engine):
        """Test counter-pick score calculation."""
        team_context = TeamContext(
            existing_picks={},
            target_role="middle",
            target_player_puuid="test_player",
            enemy_composition={"middle": 50, "top": 51}
        )
        
        # Mock counter advantage calculation
        recommendation_engine._calculate_champion_counter_advantage = Mock(return_value=0.3)
        
        counter_score = recommendation_engine._calculate_counter_pick_score(
            champion_id=1,
            role="middle",
            team_context=team_context
        )
        
        assert 0.0 <= counter_score <= 1.0
        # Should call counter advantage calculation for each enemy
        assert recommendation_engine._calculate_champion_counter_advantage.call_count == 2
    
    def test_counter_pick_score_no_enemy_info(self, recommendation_engine, sample_team_context):
        """Test counter-pick score with no enemy information."""
        counter_score = recommendation_engine._calculate_counter_pick_score(
            champion_id=1,
            role="middle",
            team_context=sample_team_context
        )
        
        assert counter_score == 0.5  # Should return neutral score
    
    def test_champion_counter_advantage(self, recommendation_engine):
        """Test champion counter advantage calculation."""
        # Mock matchup data with favorable win rate
        mock_matchup_data = {
            'games': 10,
            'win_rate': 0.7,  # 70% win rate vs this enemy
            'sample_size': 'medium'
        }
        
        recommendation_engine._get_champion_matchup_data = Mock(return_value=mock_matchup_data)
        
        advantage = recommendation_engine._calculate_champion_counter_advantage(
            champion_id=1,
            enemy_champion_id=50,
            role="middle",
            enemy_role="middle"
        )
        
        # 70% vs 50% expected = +20% = +0.4 advantage
        assert advantage > 0.0
        assert advantage <= 1.0
    
    def test_champion_counter_advantage_insufficient_data(self, recommendation_engine):
        """Test counter advantage with insufficient data."""
        # Mock insufficient matchup data
        mock_matchup_data = {
            'games': 2,  # Too few games
            'win_rate': 0.8,
            'sample_size': 'low'
        }
        
        recommendation_engine._get_champion_matchup_data = Mock(return_value=mock_matchup_data)
        
        advantage = recommendation_engine._calculate_champion_counter_advantage(
            champion_id=1,
            enemy_champion_id=50,
            role="middle",
            enemy_role="middle"
        )
        
        assert advantage == 0.0  # Should return neutral for insufficient data
    
    def test_get_champion_matchup_data(self, recommendation_engine):
        """Test champion matchup data retrieval."""
        # Mock match manager response
        mock_matchups = [
            {'win': True}, {'win': False}, {'win': True}, {'win': True}  # 3/4 = 75%
        ]
        
        recommendation_engine.analytics_engine.match_manager.get_champion_matchups = Mock(
            return_value=mock_matchups
        )
        
        matchup_data = recommendation_engine._get_champion_matchup_data(
            champion_id=1,
            enemy_champion_id=50,
            role="middle",
            enemy_role="middle"
        )
        
        assert matchup_data is not None
        assert matchup_data['games'] == 4
        assert matchup_data['wins'] == 3
        assert matchup_data['win_rate'] == 0.75
        assert matchup_data['sample_size'] == 'low'  # < 10 games
    
    def test_team_synergy_score_integration(self, recommendation_engine, sample_team_context):
        """Test integrated team synergy score calculation."""
        # Mock ally and counter-pick scores
        recommendation_engine._calculate_ally_synergy_score = Mock(return_value=0.8)
        recommendation_engine._calculate_counter_pick_score = Mock(return_value=0.6)
        
        total_synergy = recommendation_engine._calculate_team_synergy_score(
            champion_id=1,
            role="middle",
            team_context=sample_team_context,
            puuid="test_player"
        )
        
        # Should combine: 0.8 * 0.7 + 0.6 * 0.3 = 0.56 + 0.18 = 0.74
        expected_score = 0.8 * 0.7 + 0.6 * 0.3
        assert abs(total_synergy - expected_score) < 0.01


class TestRoleSpecificAdjustments:
    """Test role-specific recommendation adjustments."""
    
    def test_role_specific_weight_adjustments(self, recommendation_engine):
        """Test role-specific weight adjustments."""
        base_weights = {
            'individual_performance': 0.35,
            'team_synergy': 0.25,
            'recent_form': 0.20,
            'meta_relevance': 0.10,
            'confidence': 0.10
        }
        
        # Test jungle role (should emphasize synergy more)
        jungle_weights = recommendation_engine._apply_role_specific_weight_adjustments(
            base_weights, "jungle", None
        )
        
        assert jungle_weights['team_synergy'] > base_weights['team_synergy']
        assert jungle_weights['individual_performance'] < base_weights['individual_performance']
        
        # Test support role (should emphasize synergy most)
        support_weights = recommendation_engine._apply_role_specific_weight_adjustments(
            base_weights, "support", None
        )
        
        assert support_weights['team_synergy'] > jungle_weights['team_synergy']
        assert support_weights['individual_performance'] < jungle_weights['individual_performance']
        
        # Test middle role (should emphasize meta more)
        middle_weights = recommendation_engine._apply_role_specific_weight_adjustments(
            base_weights, "middle", None
        )
        
        assert middle_weights['meta_relevance'] > base_weights['meta_relevance']
    
    def test_team_context_weight_adjustments(self, recommendation_engine):
        """Test team context-specific weight adjustments."""
        base_weights = {
            'individual_performance': 0.35,
            'team_synergy': 0.25,
            'recent_form': 0.20,
            'meta_relevance': 0.10,
            'confidence': 0.10
        }
        
        # Test with enemy composition known
        team_context_with_enemies = TeamContext(
            existing_picks={},
            target_role="middle",
            target_player_puuid="test_player",
            enemy_composition={"middle": 50, "top": 51}
        )
        
        adjusted_weights = recommendation_engine._apply_team_context_weight_adjustments(
            base_weights, team_context_with_enemies
        )
        
        assert adjusted_weights['team_synergy'] > base_weights['team_synergy']
        
        # Test with many bans
        team_context_many_bans = TeamContext(
            existing_picks={},
            target_role="middle",
            target_player_puuid="test_player",
            banned_champions=[1, 2, 3, 4, 5, 6, 7, 8]  # Many bans
        )
        
        adjusted_weights = recommendation_engine._apply_team_context_weight_adjustments(
            base_weights, team_context_many_bans
        )
        
        assert adjusted_weights['meta_relevance'] > base_weights['meta_relevance']
        
        # Test with limited champion pool
        team_context_limited_pool = TeamContext(
            existing_picks={},
            target_role="middle",
            target_player_puuid="test_player",
            available_champions=[1, 2, 3, 4, 5]  # Limited pool
        )
        
        adjusted_weights = recommendation_engine._apply_team_context_weight_adjustments(
            base_weights, team_context_limited_pool
        )
        
        assert adjusted_weights['individual_performance'] > base_weights['individual_performance']
    
    def test_weight_normalization(self, recommendation_engine):
        """Test that weights are properly normalized to sum to 1.0."""
        base_weights = {
            'individual_performance': 0.35,
            'team_synergy': 0.25,
            'recent_form': 0.20,
            'meta_relevance': 0.10,
            'confidence': 0.10
        }
        
        adjusted_weights = recommendation_engine._apply_role_specific_weight_adjustments(
            base_weights, "jungle", None
        )
        
        # Weights should sum to 1.0 (within floating point precision)
        total_weight = sum(adjusted_weights.values())
        assert abs(total_weight - 1.0) < 0.001


class TestRecommendationReasoning:
    """Test recommendation reasoning generation."""
    
    def test_identify_primary_factors(self, recommendation_engine):
        """Test identification of primary recommendation factors."""
        score_breakdown = RecommendationScore(
            champion_id=1,
            total_score=0.8,
            individual_performance_score=0.9,  # High performance
            team_synergy_score=0.2,           # Poor synergy
            recent_form_score=0.6,
            meta_relevance_score=0.5,
            confidence_score=0.8,
            performance_weight=0.35,
            synergy_weight=0.25,
            form_weight=0.20,
            meta_weight=0.10,
            confidence_weight=0.10,
            games_played=25,
            data_quality_score=0.8,
            sample_size_penalty=0.0
        )
        
        factors = recommendation_engine._identify_primary_factors(score_breakdown)
        
        assert "Strong historical performance" in factors
        assert "Poor team synergy" in factors
        assert len(factors) >= 2
    
    def test_generate_performance_summary(self, recommendation_engine, sample_champion_performance):
        """Test performance summary generation."""
        score_breakdown = RecommendationScore(
            champion_id=1,
            total_score=0.8,
            individual_performance_score=0.7,
            team_synergy_score=0.6,
            recent_form_score=0.8,
            meta_relevance_score=0.5,
            confidence_score=0.8,
            performance_weight=0.35,
            synergy_weight=0.25,
            form_weight=0.20,
            meta_weight=0.10,
            confidence_weight=0.10,
            games_played=20,
            data_quality_score=0.8,
            sample_size_penalty=0.0
        )
        
        summary = recommendation_engine._generate_performance_summary(
            sample_champion_performance, score_breakdown
        )
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "60.0%" in summary  # Win rate should be mentioned
        assert "2.5" in summary    # KDA should be mentioned
        assert "20 games" in summary  # Games played should be mentioned
    
    def test_generate_synergy_summary(self, recommendation_engine):
        """Test synergy summary generation."""
        synergy_analysis = SynergyAnalysis(
            team_synergy_score=0.4,
            individual_synergies={10: 0.5, 20: 0.3},
            synergy_explanation="Good synergy with team composition",
            historical_data_points=15
        )
        
        summary = recommendation_engine._generate_synergy_summary(synergy_analysis)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Strong positive synergy" in summary or "Good synergy" in summary
        assert "high confidence" in summary  # 15 data points should be high confidence
    
    def test_generate_confidence_explanation(self, recommendation_engine, sample_champion_performance):
        """Test confidence explanation generation."""
        score_breakdown = RecommendationScore(
            champion_id=1,
            total_score=0.8,
            individual_performance_score=0.7,
            team_synergy_score=0.6,
            recent_form_score=0.8,
            meta_relevance_score=0.5,
            confidence_score=0.8,
            performance_weight=0.35,
            synergy_weight=0.25,
            form_weight=0.20,
            meta_weight=0.10,
            confidence_weight=0.10,
            games_played=20,
            data_quality_score=0.8,
            sample_size_penalty=0.0
        )
        
        explanation = recommendation_engine._generate_confidence_explanation(
            score_breakdown, sample_champion_performance
        )
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "confidence" in explanation.lower()  # Accept "High" or "Very high" confidence
        assert "20 game" in explanation
    
    def test_identify_recommendation_warnings(self, recommendation_engine, sample_champion_performance):
        """Test identification of recommendation warnings."""
        # Create score breakdown with potential issues
        score_breakdown = RecommendationScore(
            champion_id=1,
            total_score=0.4,
            individual_performance_score=0.2,  # Poor performance
            team_synergy_score=0.2,           # Poor synergy
            recent_form_score=0.2,            # Poor recent form
            meta_relevance_score=0.2,         # Poor meta relevance
            confidence_score=0.3,             # Low confidence
            performance_weight=0.35,
            synergy_weight=0.25,
            form_weight=0.20,
            meta_weight=0.10,
            confidence_weight=0.10,
            games_played=5,  # Low sample size
            data_quality_score=0.5,
            sample_size_penalty=0.3
        )
        
        warnings = recommendation_engine._identify_recommendation_warnings(
            sample_champion_performance, score_breakdown
        )
        
        assert len(warnings) > 0
        assert any("Limited data" in warning for warning in warnings)
        assert any("declining" in warning for warning in warnings)
        assert any("Low confidence" in warning for warning in warnings)
        assert any("synergy issues" in warning for warning in warnings)
        assert any("meta-relevant" in warning for warning in warnings)
        assert any("Below-average" in warning for warning in warnings)


class TestMetaAnalysis:
    """Test meta-relevance analysis functionality."""
    
    def test_recent_meta_performance_calculation(self, recommendation_engine):
        """Test recent meta performance calculation."""
        # Mock recent matches with good performance
        recent_matches = [
            {'win': True}, {'win': True}, {'win': False}, {'win': True}  # 75% recent
        ]
        
        # Mock overall matches with average performance
        overall_matches = [
            {'win': True}, {'win': False}, {'win': True}, {'win': False},
            {'win': True}, {'win': False}, {'win': True}, {'win': False}  # 50% overall
        ]
        
        def mock_get_matches(champion_ids, filters=None):
            if filters and hasattr(filters, 'date_range'):
                return recent_matches
            return overall_matches
        
        recommendation_engine.analytics_engine.match_manager.get_matches_with_champions = mock_get_matches
        
        meta_score = recommendation_engine._calculate_recent_meta_performance(
            champion_id=1,
            role="middle",
            filters=None
        )
        
        # 75% recent vs 50% overall = +25% = +0.5 meta score = 1.0 total
        assert meta_score > 0.5
        assert meta_score <= 1.0
    
    def test_champion_popularity_score(self, recommendation_engine):
        """Test champion popularity score calculation."""
        # Mock role matches with champion picks
        role_matches = [
            {'champion_id': 1}, {'champion_id': 2}, {'champion_id': 1},
            {'champion_id': 3}, {'champion_id': 1}, {'champion_id': 4},
            {'champion_id': 1}, {'champion_id': 5}, {'champion_id': 1},
            {'champion_id': 6}  # Champion 1 picked 5/10 times = 50% pick rate
        ]
        
        recommendation_engine.analytics_engine.match_manager.get_matches_by_role = Mock(
            return_value=role_matches
        )
        
        popularity_score = recommendation_engine._calculate_champion_popularity_score(
            champion_id=1,
            role="middle"
        )
        
        # 50% pick rate should result in high popularity score
        assert popularity_score > 0.5
        assert popularity_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])