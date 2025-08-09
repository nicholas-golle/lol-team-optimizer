"""
Tests for Advanced Recommendation Customizer

This module tests the comprehensive customization options for champion recommendations,
including parameter tuning, champion pool filtering, ban phase simulation,
scenario testing, performance tracking, and learning from user feedback.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, List, Any

from lol_team_optimizer.advanced_recommendation_customizer import (
    AdvancedRecommendationCustomizer,
    RecommendationParameters,
    ChampionPoolFilter,
    BanPhaseSimulation,
    RecommendationScenario,
    UserFeedback,
    RecommendationPerformanceMetrics
)
from lol_team_optimizer.analytics_models import (
    ChampionRecommendation,
    TeamContext,
    ChampionPerformanceMetrics,
    AnalyticsError
)
from lol_team_optimizer.config import Config


class TestRecommendationParameters:
    """Test recommendation parameters validation and functionality."""
    
    def test_default_parameters_creation(self):
        """Test creating default recommendation parameters."""
        params = RecommendationParameters()
        
        assert params.individual_performance_weight == 0.35
        assert params.team_synergy_weight == 0.25
        assert params.recent_form_weight == 0.20
        assert params.meta_relevance_weight == 0.10
        assert params.confidence_weight == 0.10
        assert params.meta_emphasis == 1.0
        assert params.synergy_importance == 1.0
        assert params.risk_tolerance == 0.5
    
    def test_custom_parameters_creation(self):
        """Test creating custom recommendation parameters."""
        params = RecommendationParameters(
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            recent_form_weight=0.15,
            meta_relevance_weight=0.1,
            confidence_weight=0.05,
            meta_emphasis=1.5,
            risk_tolerance=0.8
        )
        
        assert params.individual_performance_weight == 0.4
        assert params.team_synergy_weight == 0.3
        assert params.meta_emphasis == 1.5
        assert params.risk_tolerance == 0.8
    
    def test_weight_validation_success(self):
        """Test that valid weights pass validation."""
        # Should not raise exception
        RecommendationParameters(
            individual_performance_weight=0.3,
            team_synergy_weight=0.3,
            recent_form_weight=0.2,
            meta_relevance_weight=0.1,
            confidence_weight=0.1
        )
    
    def test_weight_validation_failure(self):
        """Test that invalid weights fail validation."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            RecommendationParameters(
                individual_performance_weight=0.5,
                team_synergy_weight=0.5,
                recent_form_weight=0.2,
                meta_relevance_weight=0.1,
                confidence_weight=0.1
            )
    
    def test_range_validation_failure(self):
        """Test that out-of-range parameters fail validation."""
        with pytest.raises(ValueError, match="Meta emphasis must be between 0.0 and 2.0"):
            RecommendationParameters(meta_emphasis=3.0)
        
        with pytest.raises(ValueError, match="Risk tolerance must be between 0.0 and 1.0"):
            RecommendationParameters(risk_tolerance=1.5)
    
    def test_serialization(self):
        """Test parameter serialization and deserialization."""
        params = RecommendationParameters(
            individual_performance_weight=0.4,
            meta_emphasis=1.5,
            risk_tolerance=0.8
        )
        
        # Test to_dict
        params_dict = params.to_dict()
        assert isinstance(params_dict, dict)
        assert params_dict['individual_performance_weight'] == 0.4
        assert params_dict['meta_emphasis'] == 1.5
        
        # Test from_dict
        restored_params = RecommendationParameters.from_dict(params_dict)
        assert restored_params.individual_performance_weight == 0.4
        assert restored_params.meta_emphasis == 1.5
        assert restored_params.risk_tolerance == 0.8


class TestChampionPoolFilter:
    """Test champion pool filtering functionality."""
    
    def test_default_filter_creation(self):
        """Test creating default champion pool filter."""
        filter_obj = ChampionPoolFilter()
        
        assert filter_obj.allowed_champions is None
        assert len(filter_obj.banned_champions) == 0
        assert len(filter_obj.role_restrictions) == 0
        assert filter_obj.min_games_played == 5
        assert filter_obj.include_off_meta is True
        assert filter_obj.prioritize_comfort is False
    
    def test_custom_filter_creation(self):
        """Test creating custom champion pool filter."""
        filter_obj = ChampionPoolFilter(
            allowed_champions={1, 2, 3},
            banned_champions={4, 5},
            min_mastery_level=4,
            min_games_played=10,
            include_off_meta=False
        )
        
        assert filter_obj.allowed_champions == {1, 2, 3}
        assert filter_obj.banned_champions == {4, 5}
        assert filter_obj.min_mastery_level == 4
        assert filter_obj.min_games_played == 10
        assert filter_obj.include_off_meta is False
    
    def test_filter_application_allowed_champions(self):
        """Test filtering based on allowed champions."""
        filter_obj = ChampionPoolFilter(allowed_champions={1, 2, 3})
        player_data = {}
        
        assert filter_obj.apply_filter(1, 'top', player_data) is True
        assert filter_obj.apply_filter(4, 'top', player_data) is False
    
    def test_filter_application_banned_champions(self):
        """Test filtering based on banned champions."""
        filter_obj = ChampionPoolFilter(banned_champions={4, 5})
        player_data = {}
        
        assert filter_obj.apply_filter(1, 'top', player_data) is True
        assert filter_obj.apply_filter(4, 'top', player_data) is False
        assert filter_obj.apply_filter(5, 'top', player_data) is False
    
    def test_filter_application_mastery_requirements(self):
        """Test filtering based on mastery requirements."""
        filter_obj = ChampionPoolFilter(
            min_mastery_level=4,
            min_mastery_points=50000
        )
        
        # Champion with sufficient mastery
        player_data = {
            'mastery': {
                1: {'level': 5, 'points': 60000}
            }
        }
        assert filter_obj.apply_filter(1, 'top', player_data) is True
        
        # Champion with insufficient mastery level
        player_data = {
            'mastery': {
                2: {'level': 3, 'points': 60000}
            }
        }
        assert filter_obj.apply_filter(2, 'top', player_data) is False
        
        # Champion with insufficient mastery points
        player_data = {
            'mastery': {
                3: {'level': 5, 'points': 30000}
            }
        }
        assert filter_obj.apply_filter(3, 'top', player_data) is False
    
    def test_filter_application_performance_requirements(self):
        """Test filtering based on performance requirements."""
        filter_obj = ChampionPoolFilter(
            min_games_played=10,
            min_win_rate=0.6
        )
        
        # Champion with sufficient performance
        player_data = {
            'performance': {
                1: {'games_played': 15, 'win_rate': 0.65}
            }
        }
        assert filter_obj.apply_filter(1, 'top', player_data) is True
        
        # Champion with insufficient games
        player_data = {
            'performance': {
                2: {'games_played': 5, 'win_rate': 0.65}
            }
        }
        assert filter_obj.apply_filter(2, 'top', player_data) is False
        
        # Champion with insufficient win rate
        player_data = {
            'performance': {
                3: {'games_played': 15, 'win_rate': 0.45}
            }
        }
        assert filter_obj.apply_filter(3, 'top', player_data) is False


class TestBanPhaseSimulation:
    """Test ban phase simulation functionality."""
    
    def test_default_ban_phase_creation(self):
        """Test creating default ban phase simulation."""
        ban_phase = BanPhaseSimulation()
        
        assert ban_phase.current_phase == 'ban'
        assert ban_phase.current_turn == 0
        assert len(ban_phase.team1_bans) == 0
        assert len(ban_phase.team2_bans) == 0
        assert len(ban_phase.team1_picks) == 0
        assert len(ban_phase.team2_picks) == 0
    
    def test_ban_simulation(self):
        """Test simulating champion bans."""
        ban_phase = BanPhaseSimulation()
        
        # Simulate first ban (team1)
        result = ban_phase.simulate_ban(1)
        assert result is True
        assert 1 in ban_phase.team1_bans
        assert ban_phase.current_turn == 1
        
        # Simulate second ban (team2)
        result = ban_phase.simulate_ban(2)
        assert result is True
        assert 2 in ban_phase.team2_bans
        assert ban_phase.current_turn == 2
    
    def test_pick_simulation(self):
        """Test simulating champion picks."""
        ban_phase = BanPhaseSimulation()
        
        # Complete ban phase
        for i in range(10):  # 10 bans total
            ban_phase.simulate_ban(i + 1)
        
        assert ban_phase.current_phase == 'pick'
        assert ban_phase.current_turn == 0
        
        # Simulate first pick (team1)
        result = ban_phase.simulate_pick(11, 'top')
        assert result is True
        assert ('top', 11) in ban_phase.team1_picks
        assert ban_phase.current_turn == 1
        
        # Simulate second pick (team2)
        result = ban_phase.simulate_pick(12, 'jungle')
        assert result is True
        assert ('jungle', 12) in ban_phase.team2_picks
    
    def test_unavailable_champions(self):
        """Test getting unavailable champions."""
        ban_phase = BanPhaseSimulation()
        
        # Add some bans and picks
        ban_phase.team1_bans = [1, 2]
        ban_phase.team2_bans = [3, 4]
        ban_phase.team1_picks = [('top', 5)]
        ban_phase.team2_picks = [('jungle', 6)]
        
        banned = ban_phase.get_banned_champions()
        picked = ban_phase.get_picked_champions()
        unavailable = ban_phase.get_unavailable_champions()
        
        assert banned == {1, 2, 3, 4}
        assert picked == {5, 6}
        assert unavailable == {1, 2, 3, 4, 5, 6}
    
    def test_counter_pick_opportunities(self):
        """Test identifying counter-pick opportunities."""
        ban_phase = BanPhaseSimulation()
        ban_phase.current_phase = 'pick'
        
        # Set up some picks
        ban_phase.team1_picks = [('top', 1)]
        ban_phase.team2_picks = [('jungle', 2), ('middle', 3)]
        
        opportunities = ban_phase.get_counter_pick_opportunities('team1')
        
        assert len(opportunities) == 2
        assert any(opp['target_role'] == 'jungle' for opp in opportunities)
        assert any(opp['target_role'] == 'middle' for opp in opportunities)


class TestAdvancedRecommendationCustomizer:
    """Test the main advanced recommendation customizer."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        return config
    
    @pytest.fixture
    def mock_recommendation_engine(self):
        """Create mock recommendation engine."""
        engine = Mock()
        
        # Mock recommendation
        mock_rec = Mock(spec=ChampionRecommendation)
        mock_rec.champion_id = 1
        mock_rec.champion_name = "TestChampion"
        mock_rec.role = "top"
        mock_rec.recommendation_score = 0.85
        mock_rec.confidence = 0.75
        mock_rec.historical_performance = Mock()
        mock_rec.expected_performance = Mock()
        mock_rec.synergy_analysis = Mock()
        mock_rec.reasoning = Mock()
        mock_rec.reasoning.primary_reasons = ["High win rate", "Good synergy"]
        
        engine.get_champion_recommendations.return_value = [mock_rec]
        return engine
    
    @pytest.fixture
    def customizer(self, mock_config, mock_recommendation_engine):
        """Create advanced recommendation customizer instance."""
        return AdvancedRecommendationCustomizer(mock_config, mock_recommendation_engine)
    
    def test_initialization(self, customizer):
        """Test customizer initialization."""
        assert customizer.config is not None
        assert customizer.recommendation_engine is not None
        assert isinstance(customizer.user_parameters, dict)
        assert isinstance(customizer.user_filters, dict)
        assert isinstance(customizer.scenarios, dict)
        assert isinstance(customizer.feedback_history, list)
        assert isinstance(customizer.performance_metrics, RecommendationPerformanceMetrics)
    
    def test_create_custom_parameters(self, customizer):
        """Test creating custom parameters for a user."""
        user_id = "test_user"
        
        params = customizer.create_custom_parameters(
            user_id,
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            meta_emphasis=1.5
        )
        
        assert isinstance(params, RecommendationParameters)
        assert params.individual_performance_weight == 0.4
        assert params.team_synergy_weight == 0.3
        assert params.meta_emphasis == 1.5
        assert user_id in customizer.user_parameters
    
    def test_create_champion_pool_filter(self, customizer):
        """Test creating champion pool filter for a user."""
        user_id = "test_user"
        
        filter_obj = customizer.create_champion_pool_filter(
            user_id,
            banned_champions={1, 2, 3},
            min_games_played=10,
            include_off_meta=False
        )
        
        assert isinstance(filter_obj, ChampionPoolFilter)
        assert filter_obj.banned_champions == {1, 2, 3}
        assert filter_obj.min_games_played == 10
        assert filter_obj.include_off_meta is False
        assert user_id in customizer.user_filters
    
    def test_get_customized_recommendations(self, customizer, mock_recommendation_engine):
        """Test getting customized recommendations."""
        user_id = "test_user"
        puuid = "test_puuid"
        role = "top"
        
        # Create custom parameters
        customizer.create_custom_parameters(
            user_id,
            individual_performance_weight=0.4,
            max_recommendations=5
        )
        
        # Create champion filter
        customizer.create_champion_pool_filter(
            user_id,
            min_games_played=8
        )
        
        # Mock player data for filtering
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {1: {'games_played': 10, 'win_rate': 0.6}},
                'mastery': {},
                'meta': {}
            }
            
            recommendations = customizer.get_customized_recommendations(
                puuid=puuid,
                role=role,
                user_id=user_id
            )
        
        assert len(recommendations) > 0
        assert mock_recommendation_engine.get_champion_recommendations.called
        
        # Check that custom weights were used
        call_args = mock_recommendation_engine.get_champion_recommendations.call_args
        assert 'custom_weights' in call_args.kwargs
        assert call_args.kwargs['custom_weights']['individual_performance'] == 0.4
    
    def test_ban_phase_recommendations(self, customizer):
        """Test recommendations with ban phase simulation."""
        user_id = "test_user"
        puuid = "test_puuid"
        role = "top"
        
        # Create ban phase
        ban_phase = BanPhaseSimulation()
        ban_phase.team1_bans = [1, 2]
        ban_phase.team2_bans = [3, 4]
        
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {5: {'games_played': 10, 'win_rate': 0.6}},
                'mastery': {},
                'meta': {}
            }
            
            results = customizer.simulate_ban_phase_recommendations(
                puuid=puuid,
                role=role,
                user_id=user_id,
                ban_phase=ban_phase
            )
        
        assert 'current_state' in results
        assert 'recommendations' in results
        assert 'counter_pick_opportunities' in results
        assert 'ban_suggestions' in results
        
        # Check that banned champions are included in current state
        assert set(results['current_state']['banned_champions']) == {1, 2, 3, 4}
    
    def test_create_recommendation_scenario(self, customizer):
        """Test creating recommendation scenarios."""
        parameters = RecommendationParameters(meta_emphasis=1.5)
        champion_filter = ChampionPoolFilter(min_games_played=10)
        
        scenario = customizer.create_recommendation_scenario(
            name="Test Scenario",
            description="A test scenario",
            parameters=parameters,
            champion_pool_filter=champion_filter,
            expected_recommendations=[1, 2, 3]
        )
        
        assert isinstance(scenario, RecommendationScenario)
        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario"
        assert scenario.parameters == parameters
        assert scenario.champion_pool_filter == champion_filter
        assert scenario.expected_recommendations == [1, 2, 3]
        assert scenario.scenario_id in customizer.scenarios
    
    def test_run_scenario_test(self, customizer):
        """Test running scenario tests."""
        # Create scenario
        parameters = RecommendationParameters()
        champion_filter = ChampionPoolFilter()
        scenario = customizer.create_recommendation_scenario(
            name="Test Scenario",
            description="A test scenario",
            parameters=parameters,
            champion_pool_filter=champion_filter,
            expected_recommendations=[1]
        )
        
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {1: {'games_played': 10, 'win_rate': 0.6}},
                'mastery': {},
                'meta': {}
            }
            
            results = customizer.run_scenario_test(
                scenario_id=scenario.scenario_id,
                puuid="test_puuid",
                role="top",
                user_id="test_user"
            )
        
        assert 'scenario_id' in results
        assert 'scenario_name' in results
        assert 'recommendations' in results
        assert 'evaluation' in results
        assert 'performance_metrics' in results
        assert 'success' in results
        
        # Check that scenario was updated
        updated_scenario = customizer.scenarios[scenario.scenario_id]
        assert updated_scenario.actual_recommendations is not None
        assert updated_scenario.last_run is not None
    
    def test_record_user_feedback(self, customizer):
        """Test recording user feedback."""
        user_id = "test_user"
        recommendation_id = "test_rec_id"
        champion_id = 1
        role = "top"
        
        feedback = customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id=recommendation_id,
            champion_id=champion_id,
            role=role,
            feedback_type="positive",
            accuracy_rating=4,
            usefulness_rating=5,
            comments="Great recommendation!",
            match_outcome=True,
            tags=["accurate", "helpful"]
        )
        
        assert isinstance(feedback, UserFeedback)
        assert feedback.user_id == user_id
        assert feedback.recommendation_id == recommendation_id
        assert feedback.champion_id == champion_id
        assert feedback.role == role
        assert feedback.feedback_type == "positive"
        assert feedback.accuracy_rating == 4
        assert feedback.usefulness_rating == 5
        assert feedback.comments == "Great recommendation!"
        assert feedback.match_outcome is True
        assert "accurate" in feedback.tags
        
        # Check that feedback was stored
        assert len(customizer.feedback_history) == 1
        assert customizer.feedback_history[0] == feedback
    
    def test_feedback_learning_application(self, customizer, mock_recommendation_engine):
        """Test that user feedback is applied to future recommendations."""
        user_id = "test_user"
        
        # Record positive feedback for champion 1
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec1",
            champion_id=1,
            role="top",
            feedback_type="positive",
            accuracy_rating=5
        )
        
        # Record negative feedback for champion 2
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec2",
            champion_id=2,
            role="top",
            feedback_type="negative",
            accuracy_rating=2
        )
        
        # Mock multiple recommendations
        mock_rec1 = Mock(spec=ChampionRecommendation)
        mock_rec1.champion_id = 1
        mock_rec1.champion_name = "Champion1"
        mock_rec1.role = "top"
        mock_rec1.recommendation_score = 0.8
        mock_rec1.confidence = 0.7
        mock_rec1.historical_performance = Mock()
        mock_rec1.expected_performance = Mock()
        mock_rec1.synergy_analysis = Mock()
        mock_rec1.reasoning = Mock()
        
        mock_rec2 = Mock(spec=ChampionRecommendation)
        mock_rec2.champion_id = 2
        mock_rec2.champion_name = "Champion2"
        mock_rec2.role = "top"
        mock_rec2.recommendation_score = 0.8
        mock_rec2.confidence = 0.7
        mock_rec2.historical_performance = Mock()
        mock_rec2.expected_performance = Mock()
        mock_rec2.synergy_analysis = Mock()
        mock_rec2.reasoning = Mock()
        
        mock_recommendation_engine.get_champion_recommendations.return_value = [mock_rec1, mock_rec2]
        
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {1: {'games_played': 10}, 2: {'games_played': 10}},
                'mastery': {},
                'meta': {}
            }
            
            recommendations = customizer.get_customized_recommendations(
                puuid="test_puuid",
                role="top",
                user_id=user_id
            )
        
        # Champion 1 should be ranked higher due to positive feedback
        # Champion 2 should be ranked lower due to negative feedback
        champion_scores = {rec.champion_id: rec.recommendation_score for rec in recommendations}
        assert champion_scores[1] > champion_scores[2]
    
    def test_performance_report_generation(self, customizer):
        """Test generating performance reports."""
        user_id = "test_user"
        
        # Add some feedback
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec1",
            champion_id=1,
            role="top",
            feedback_type="positive",
            accuracy_rating=4,
            match_outcome=True
        )
        
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec2",
            champion_id=2,
            role="jungle",
            feedback_type="negative",
            accuracy_rating=2,
            match_outcome=False
        )
        
        report = customizer.get_recommendation_performance_report(user_id=user_id)
        
        assert 'summary' in report
        assert 'metrics' in report
        assert 'insights' in report
        assert 'improvement_recommendations' in report
        assert 'detailed_breakdown' in report
        
        # Check metrics
        metrics = report['metrics']
        assert metrics['total_feedback'] == 2
        assert metrics['positive_feedback_count'] == 1
        assert metrics['negative_feedback_count'] == 1
        assert metrics['avg_accuracy_rating'] == 3.0  # (4 + 2) / 2
        assert metrics['win_rate_with_recommendations'] == 0.5  # 1 win out of 2
    
    def test_customization_settings_export_import(self, customizer):
        """Test exporting and importing customization settings."""
        user_id = "test_user"
        
        # Create custom settings
        customizer.create_custom_parameters(
            user_id,
            individual_performance_weight=0.4,
            meta_emphasis=1.5
        )
        
        customizer.create_champion_pool_filter(
            user_id,
            banned_champions={1, 2, 3},
            min_games_played=10
        )
        
        # Add some feedback
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec1",
            champion_id=1,
            role="top",
            feedback_type="positive",
            accuracy_rating=4
        )
        
        # Export settings
        exported_settings = customizer.export_customization_settings(user_id)
        
        assert 'user_id' in exported_settings
        assert 'parameters' in exported_settings
        assert 'champion_filter' in exported_settings
        assert 'feedback_summary' in exported_settings
        assert 'export_timestamp' in exported_settings
        
        # Check exported parameters
        assert exported_settings['parameters']['individual_performance_weight'] == 0.4
        assert exported_settings['parameters']['meta_emphasis'] == 1.5
        
        # Check exported filter
        assert 1 in exported_settings['champion_filter']['banned_champions']
        assert exported_settings['champion_filter']['min_games_played'] == 10
        
        # Check feedback summary
        assert exported_settings['feedback_summary']['total_feedback'] == 1
        assert exported_settings['feedback_summary']['positive_feedback'] == 1
        
        # Clear settings and import
        customizer.user_parameters.clear()
        customizer.user_filters.clear()
        
        success = customizer.import_customization_settings(user_id, exported_settings)
        assert success is True
        
        # Verify imported settings
        assert user_id in customizer.user_parameters
        assert user_id in customizer.user_filters
        
        imported_params = customizer.user_parameters[user_id]
        assert imported_params.individual_performance_weight == 0.4
        assert imported_params.meta_emphasis == 1.5
        
        imported_filter = customizer.user_filters[user_id]
        assert 1 in imported_filter.banned_champions
        assert imported_filter.min_games_played == 10
    
    def test_error_handling(self, customizer):
        """Test error handling in various scenarios."""
        # Test invalid parameters
        with pytest.raises(AnalyticsError):
            customizer.create_custom_parameters(
                "test_user",
                individual_performance_weight=0.8,  # Invalid - weights don't sum to 1.0
                team_synergy_weight=0.8
            )
        
        # Test scenario not found
        with pytest.raises(AnalyticsError, match="Scenario .* not found"):
            customizer.run_scenario_test(
                scenario_id="nonexistent",
                puuid="test_puuid",
                role="top",
                user_id="test_user"
            )
    
    def test_risk_tolerance_filtering(self, customizer, mock_recommendation_engine):
        """Test that risk tolerance affects recommendation filtering."""
        user_id = "test_user"
        
        # Create mock recommendations with different confidence levels
        high_conf_rec = Mock(spec=ChampionRecommendation)
        high_conf_rec.champion_id = 1
        high_conf_rec.confidence = 0.8
        high_conf_rec.recommendation_score = 0.9
        high_conf_rec.champion_name = "HighConf"
        high_conf_rec.role = "top"
        high_conf_rec.historical_performance = Mock()
        high_conf_rec.expected_performance = Mock()
        high_conf_rec.synergy_analysis = Mock()
        high_conf_rec.reasoning = Mock()
        
        low_conf_rec = Mock(spec=ChampionRecommendation)
        low_conf_rec.champion_id = 2
        low_conf_rec.confidence = 0.3
        low_conf_rec.recommendation_score = 0.7
        low_conf_rec.champion_name = "LowConf"
        low_conf_rec.role = "top"
        low_conf_rec.historical_performance = Mock()
        low_conf_rec.expected_performance = Mock()
        low_conf_rec.synergy_analysis = Mock()
        low_conf_rec.reasoning = Mock()
        
        mock_recommendation_engine.get_champion_recommendations.return_value = [
            high_conf_rec, low_conf_rec
        ]
        
        # Test with low risk tolerance (should filter out low confidence)
        customizer.create_custom_parameters(
            user_id,
            risk_tolerance=0.2
        )
        
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {1: {'games_played': 10}, 2: {'games_played': 10}},
                'mastery': {},
                'meta': {}
            }
            
            recommendations = customizer.get_customized_recommendations(
                puuid="test_puuid",
                role="top",
                user_id=user_id
            )
        
        # Should only include high confidence recommendation
        champion_ids = [rec.champion_id for rec in recommendations]
        assert 1 in champion_ids  # High confidence champion
        assert 2 not in champion_ids  # Low confidence champion filtered out
    
    def test_meta_emphasis_application(self, customizer, mock_recommendation_engine):
        """Test that meta emphasis affects recommendation weights."""
        user_id = "test_user"
        
        # Create custom parameters with high meta emphasis
        customizer.create_custom_parameters(
            user_id,
            meta_emphasis=2.0
        )
        
        with patch.object(customizer, '_get_player_data_for_filtering') as mock_player_data:
            mock_player_data.return_value = {
                'performance': {1: {'games_played': 10}},
                'mastery': {},
                'meta': {}
            }
            
            customizer.get_customized_recommendations(
                puuid="test_puuid",
                role="top",
                user_id=user_id
            )
        
        # Check that meta weight was amplified
        call_args = mock_recommendation_engine.get_champion_recommendations.call_args
        custom_weights = call_args.kwargs['custom_weights']
        
        # Meta relevance weight should be amplified by meta_emphasis (0.1 * 2.0 = 0.2)
        assert custom_weights['meta_relevance'] == 0.2


if __name__ == "__main__":
    pytest.main([__file__])