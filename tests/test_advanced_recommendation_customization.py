"""
Tests for Advanced Recommendation Customization and Filtering System

This module tests the comprehensive customization options for champion recommendations,
including parameter tuning, champion pool filtering, ban phase simulation,
scenario testing, performance tracking, and learning from user feedback.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from lol_team_optimizer.advanced_recommendation_customizer import (
    AdvancedRecommendationCustomizer, RecommendationParameters,
    ChampionPoolFilter, BanPhaseSimulation, RecommendationScenario,
    UserFeedback, RecommendationPerformanceMetrics
)
from lol_team_optimizer.analytics_models import (
    ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
    AnalyticsError, InsufficientDataError
)
from lol_team_optimizer.config import Config


class TestRecommendationParameters:
    """Test recommendation parameters validation and functionality."""
    
    def test_default_parameters(self):
        """Test default parameter values."""
        params = RecommendationParameters()
        
        assert params.individual_performance_weight == 0.35
        assert params.team_synergy_weight == 0.25
        assert params.recent_form_weight == 0.20
        assert params.meta_relevance_weight == 0.10
        assert params.confidence_weight == 0.10
        assert params.meta_emphasis == 1.0
        assert params.synergy_importance == 1.0
        assert params.risk_tolerance == 0.5
        assert params.min_confidence == 0.3
        assert params.max_recommendations == 10
    
    def test_weight_validation(self):
        """Test weight validation ensures they sum to 1.0."""
        # Valid weights
        params = RecommendationParameters(
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            recent_form_weight=0.2,
            meta_relevance_weight=0.05,
            confidence_weight=0.05
        )
        assert abs(sum([
            params.individual_performance_weight,
            params.team_synergy_weight,
            params.recent_form_weight,
            params.meta_relevance_weight,
            params.confidence_weight
        ]) - 1.0) < 0.01
        
        # Invalid weights should raise error
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            RecommendationParameters(
                individual_performance_weight=0.5,
                team_synergy_weight=0.5,
                recent_form_weight=0.2,
                meta_relevance_weight=0.1,
                confidence_weight=0.1
            )
    
    def test_parameter_range_validation(self):
        """Test parameter range validation."""
        # Invalid meta emphasis
        with pytest.raises(ValueError, match="Meta emphasis must be between 0.0 and 2.0"):
            RecommendationParameters(meta_emphasis=3.0)
        
        # Invalid synergy importance
        with pytest.raises(ValueError, match="Synergy importance must be between 0.0 and 2.0"):
            RecommendationParameters(synergy_importance=-0.5)
        
        # Invalid risk tolerance
        with pytest.raises(ValueError, match="Risk tolerance must be between 0.0 and 1.0"):
            RecommendationParameters(risk_tolerance=1.5)
        
        # Invalid confidence threshold
        with pytest.raises(ValueError, match="Minimum confidence must be between 0.0 and 1.0"):
            RecommendationParameters(min_confidence=-0.1)
    
    def test_serialization(self):
        """Test parameter serialization and deserialization."""
        params = RecommendationParameters(
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            recent_form_weight=0.15,
            meta_relevance_weight=0.1,
            confidence_weight=0.05,
            meta_emphasis=1.2,
            risk_tolerance=0.7
        )
        
        # Test to_dict
        params_dict = params.to_dict()
        assert isinstance(params_dict, dict)
        assert params_dict['individual_performance_weight'] == 0.4
        assert params_dict['meta_emphasis'] == 1.2
        
        # Test from_dict
        restored_params = RecommendationParameters.from_dict(params_dict)
        assert restored_params.individual_performance_weight == params.individual_performance_weight
        assert restored_params.meta_emphasis == params.meta_emphasis


class TestChampionPoolFilter:
    """Test champion pool filtering functionality."""
    
    def test_default_filter(self):
        """Test default filter allows all champions."""
        champion_filter = ChampionPoolFilter()
        
        # Mock player data
        player_data = {
            'mastery': {1: {'level': 5, 'points': 50000}},
            'performance': {1: {'games_played': 10, 'win_rate': 0.6}},
            'meta': {1: {'tier': 'A'}}
        }
        
        # Should pass with default settings
        assert champion_filter.apply_filter(1, 'top', player_data) == True
    
    def test_allowed_champions_filter(self):
        """Test allowed champions filtering."""
        champion_filter = ChampionPoolFilter(
            allowed_champions={1, 2, 3},
            min_games_played=0  # Disable games requirement for this test
        )
        
        player_data = {'mastery': {}, 'performance': {}, 'meta': {}}
        
        assert champion_filter.apply_filter(1, 'top', player_data) == True
        assert champion_filter.apply_filter(4, 'top', player_data) == False
    
    def test_banned_champions_filter(self):
        """Test banned champions filtering."""
        champion_filter = ChampionPoolFilter(
            banned_champions={1, 2},
            min_games_played=0  # Disable games requirement for this test
        )
        
        player_data = {'mastery': {}, 'performance': {}, 'meta': {}}
        
        assert champion_filter.apply_filter(1, 'top', player_data) == False
        assert champion_filter.apply_filter(3, 'top', player_data) == True
    
    def test_role_restrictions(self):
        """Test role-specific champion restrictions."""
        champion_filter = ChampionPoolFilter(
            role_restrictions={'top': {1, 2}, 'jungle': {3, 4}},
            min_games_played=0  # Disable games requirement for this test
        )
        
        player_data = {'mastery': {}, 'performance': {}, 'meta': {}}
        
        assert champion_filter.apply_filter(1, 'top', player_data) == True
        assert champion_filter.apply_filter(3, 'top', player_data) == False
        assert champion_filter.apply_filter(3, 'jungle', player_data) == True
    
    def test_mastery_requirements(self):
        """Test mastery level and points requirements."""
        champion_filter = ChampionPoolFilter(
            min_mastery_level=4,
            min_mastery_points=30000
        )
        
        # Champion with sufficient mastery
        player_data = {
            'mastery': {1: {'level': 5, 'points': 50000}},
            'performance': {1: {'games_played': 10, 'win_rate': 0.6}},
            'meta': {}
        }
        assert champion_filter.apply_filter(1, 'top', player_data) == True
        
        # Champion with insufficient mastery level
        player_data['mastery'][2] = {'level': 3, 'points': 50000}
        assert champion_filter.apply_filter(2, 'top', player_data) == False
        
        # Champion with insufficient mastery points
        player_data['mastery'][3] = {'level': 5, 'points': 20000}
        assert champion_filter.apply_filter(3, 'top', player_data) == False
    
    def test_performance_requirements(self):
        """Test performance-based filtering."""
        champion_filter = ChampionPoolFilter(
            min_games_played=10,
            min_win_rate=0.6
        )
        
        # Champion with sufficient performance
        player_data = {
            'mastery': {},
            'performance': {1: {'games_played': 15, 'win_rate': 0.7}},
            'meta': {}
        }
        assert champion_filter.apply_filter(1, 'top', player_data) == True
        
        # Champion with insufficient games
        player_data['performance'][2] = {'games_played': 5, 'win_rate': 0.8}
        assert champion_filter.apply_filter(2, 'top', player_data) == False
        
        # Champion with insufficient win rate
        player_data['performance'][3] = {'games_played': 20, 'win_rate': 0.4}
        assert champion_filter.apply_filter(3, 'top', player_data) == False
    
    def test_meta_filtering(self):
        """Test meta tier filtering."""
        champion_filter = ChampionPoolFilter(
            include_off_meta=False,
            meta_tier_threshold='B'
        )
        
        # S tier champion (should pass)
        player_data = {
            'mastery': {},
            'performance': {1: {'games_played': 10, 'win_rate': 0.6}},
            'meta': {1: {'tier': 'S'}}
        }
        assert champion_filter.apply_filter(1, 'top', player_data) == True
        
        # A tier champion (should pass)
        player_data['meta'][2] = {'tier': 'A'}
        player_data['performance'][2] = {'games_played': 10, 'win_rate': 0.6}
        assert champion_filter.apply_filter(2, 'top', player_data) == True
        
        # C tier champion (should fail with B threshold)
        player_data['meta'][3] = {'tier': 'C'}
        player_data['performance'][3] = {'games_played': 10, 'win_rate': 0.6}
        assert champion_filter.apply_filter(3, 'top', player_data) == False


class TestBanPhaseSimulation:
    """Test ban phase simulation functionality."""
    
    def test_default_ban_phase(self):
        """Test default ban phase initialization."""
        ban_phase = BanPhaseSimulation()
        
        assert ban_phase.current_phase == 'ban'
        assert ban_phase.current_turn == 0
        assert len(ban_phase.team1_bans) == 0
        assert len(ban_phase.team2_bans) == 0
        assert len(ban_phase.team1_picks) == 0
        assert len(ban_phase.team2_picks) == 0
    
    def test_ban_simulation(self):
        """Test champion banning simulation."""
        ban_phase = BanPhaseSimulation()
        
        # Ban first champion for team1
        assert ban_phase.simulate_ban(1, 'team1') == True
        assert 1 in ban_phase.team1_bans
        assert ban_phase.current_turn == 1
        
        # Ban second champion for team2
        assert ban_phase.simulate_ban(2, 'team2') == True
        assert 2 in ban_phase.team2_bans
        assert ban_phase.current_turn == 2
    
    def test_pick_simulation(self):
        """Test champion picking simulation."""
        ban_phase = BanPhaseSimulation()
        
        # Complete ban phase first
        for i in range(10):  # 10 bans total
            team = 'team1' if i % 2 == 0 else 'team2'
            ban_phase.simulate_ban(i + 1, team)
        
        assert ban_phase.current_phase == 'pick'
        assert ban_phase.current_turn == 0
        
        # Pick first champion for team1
        assert ban_phase.simulate_pick(11, 'top', 'team1') == True
        assert ('top', 11) in ban_phase.team1_picks
        assert ban_phase.current_turn == 1
        
        # Try to pick banned champion (should fail)
        assert ban_phase.simulate_pick(1, 'jungle', 'team2') == False
    
    def test_unavailable_champions(self):
        """Test getting unavailable champions."""
        ban_phase = BanPhaseSimulation()
        
        ban_phase.team1_bans = [1, 2]
        ban_phase.team2_bans = [3, 4]
        ban_phase.team1_picks = [('top', 5), ('jungle', 6)]
        ban_phase.team2_picks = [('top', 7)]
        
        unavailable = ban_phase.get_unavailable_champions()
        expected = {1, 2, 3, 4, 5, 6, 7}
        
        assert unavailable == expected
    
    def test_counter_pick_opportunities(self):
        """Test counter-pick opportunity identification."""
        ban_phase = BanPhaseSimulation()
        
        ban_phase.team1_picks = [('top', 1)]
        ban_phase.team2_picks = [('jungle', 2), ('middle', 3)]
        
        opportunities = ban_phase.get_counter_pick_opportunities('team1')
        
        # Should identify jungle and middle as counter-pick opportunities
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
        engine.get_champion_recommendations.return_value = [
            Mock(
                champion_id=1,
                champion_name="TestChampion1",
                role="top",
                recommendation_score=0.8,
                confidence=0.7,
                historical_performance=Mock(),
                expected_performance=Mock(),
                synergy_analysis=Mock(),
                reasoning=Mock()
            )
        ]
        return engine
    
    @pytest.fixture
    def customizer(self, mock_config, mock_recommendation_engine):
        """Create customizer instance."""
        return AdvancedRecommendationCustomizer(mock_config, mock_recommendation_engine)
    
    def test_create_custom_parameters(self, customizer):
        """Test creating custom parameters for a user."""
        user_id = "test_user"
        
        params = customizer.create_custom_parameters(
            user_id,
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            recent_form_weight=0.15,
            meta_relevance_weight=0.1,
            confidence_weight=0.05
        )
        
        assert isinstance(params, RecommendationParameters)
        assert params.individual_performance_weight == 0.4
        assert user_id in customizer.user_parameters
        assert customizer.user_parameters[user_id] == params
    
    def test_create_champion_pool_filter(self, customizer):
        """Test creating champion pool filter for a user."""
        user_id = "test_user"
        
        champion_filter = customizer.create_champion_pool_filter(
            user_id,
            banned_champions={1, 2, 3},
            min_games_played=10
        )
        
        assert isinstance(champion_filter, ChampionPoolFilter)
        assert champion_filter.banned_champions == {1, 2, 3}
        assert champion_filter.min_games_played == 10
        assert user_id in customizer.user_filters
    
    def test_get_customized_recommendations(self, customizer, mock_recommendation_engine):
        """Test getting customized recommendations."""
        user_id = "test_user"
        puuid = "test_puuid"
        role = "top"
        
        # Set up custom parameters
        customizer.create_custom_parameters(user_id, meta_emphasis=1.5)
        customizer.create_champion_pool_filter(user_id, min_games_played=5)
        
        recommendations = customizer.get_customized_recommendations(
            puuid=puuid,
            role=role,
            user_id=user_id
        )
        
        assert len(recommendations) > 0
        mock_recommendation_engine.get_champion_recommendations.assert_called_once()
    
    def test_ban_phase_simulation(self, customizer):
        """Test ban phase recommendation simulation."""
        user_id = "test_user"
        puuid = "test_puuid"
        role = "top"
        
        ban_phase = BanPhaseSimulation()
        ban_phase.team1_bans = [1, 2]
        ban_phase.team2_bans = [3, 4]
        
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
    
    def test_scenario_creation_and_testing(self, customizer):
        """Test scenario creation and testing."""
        params = RecommendationParameters()
        champion_filter = ChampionPoolFilter()
        
        scenario = customizer.create_recommendation_scenario(
            name="Test Scenario",
            description="A test scenario",
            parameters=params,
            champion_pool_filter=champion_filter,
            expected_recommendations=[1, 2, 3],
            success_criteria={'min_confidence': 0.5}
        )
        
        assert isinstance(scenario, RecommendationScenario)
        assert scenario.name == "Test Scenario"
        assert scenario.scenario_id in customizer.scenarios
        
        # Test running the scenario
        results = customizer.run_scenario_test(
            scenario_id=scenario.scenario_id,
            puuid="test_puuid",
            role="top",
            user_id="test_user"
        )
        
        assert 'scenario_id' in results
        assert 'recommendations' in results
        assert 'evaluation' in results
        assert 'performance_metrics' in results
    
    def test_user_feedback_recording(self, customizer):
        """Test recording and processing user feedback."""
        user_id = "test_user"
        
        feedback = customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec_123",
            champion_id=1,
            role="top",
            feedback_type="positive",
            accuracy_rating=4,
            usefulness_rating=5,
            comments="Great recommendation!",
            match_outcome=True
        )
        
        assert isinstance(feedback, UserFeedback)
        assert feedback.user_id == user_id
        assert feedback.feedback_type == "positive"
        assert feedback.accuracy_rating == 4
        assert feedback in customizer.feedback_history
    
    def test_performance_report_generation(self, customizer):
        """Test performance report generation."""
        user_id = "test_user"
        
        # Add some mock feedback
        for i in range(5):
            customizer.record_user_feedback(
                user_id=user_id,
                recommendation_id=f"rec_{i}",
                champion_id=i + 1,
                role="top",
                feedback_type="positive" if i % 2 == 0 else "negative",
                accuracy_rating=4 if i % 2 == 0 else 2
            )
        
        report = customizer.get_recommendation_performance_report(user_id=user_id)
        
        assert 'summary' in report
        assert 'metrics' in report
        assert 'insights' in report
        assert 'improvement_recommendations' in report
    
    def test_parameter_optimization_from_feedback(self, customizer):
        """Test parameter optimization based on user feedback."""
        user_id = "test_user"
        
        # Add sufficient feedback for optimization
        for i in range(15):
            customizer.record_user_feedback(
                user_id=user_id,
                recommendation_id=f"rec_{i}",
                champion_id=i + 1,
                role="top",
                feedback_type="positive" if i % 3 == 0 else "negative",
                accuracy_rating=4 if i % 3 == 0 else 2,
                tags=["good_synergy"] if i % 3 == 0 else ["poor_synergy"]
            )
        
        optimized_params = customizer.optimize_parameters_from_feedback(
            user_id=user_id,
            min_feedback_count=10
        )
        
        assert optimized_params is not None
        assert isinstance(optimized_params, RecommendationParameters)
        assert user_id in customizer.user_parameters
    
    def test_customization_settings_export_import(self, customizer):
        """Test exporting and importing customization settings."""
        user_id = "test_user"
        
        # Create custom settings
        customizer.create_custom_parameters(user_id, meta_emphasis=1.5)
        customizer.create_champion_pool_filter(user_id, banned_champions={1, 2})
        
        # Add some feedback
        customizer.record_user_feedback(
            user_id=user_id,
            recommendation_id="rec_1",
            champion_id=1,
            role="top",
            feedback_type="positive"
        )
        
        # Export settings
        settings = customizer.export_customization_settings(user_id)
        
        assert 'user_id' in settings
        assert 'parameters' in settings
        assert 'champion_filter' in settings
        assert 'feedback_summary' in settings
        
        # Import settings for new user
        new_user_id = "new_user"
        success = customizer.import_customization_settings(new_user_id, settings)
        
        assert success == True
        assert new_user_id in customizer.user_parameters
        assert new_user_id in customizer.user_filters
    
    def test_recommendation_presets(self, customizer):
        """Test recommendation preset functionality."""
        params = RecommendationParameters(meta_emphasis=1.5)
        champion_filter = ChampionPoolFilter(min_games_played=10)
        
        # Create preset
        preset_id = customizer.create_recommendation_preset(
            name="Meta Focused",
            description="Focus on meta champions",
            parameters=params,
            champion_filter=champion_filter,
            tags=["meta", "competitive"]
        )
        
        assert preset_id is not None
        
        # Get available presets
        presets = customizer.get_available_presets(tags=["meta"])
        assert len(presets) > 0
        assert any(preset['name'] == "Meta Focused" for preset in presets)
        
        # Apply preset
        user_id = "test_user"
        success = customizer.apply_preset(user_id, preset_id)
        
        assert success == True
        assert user_id in customizer.user_parameters
        assert user_id in customizer.user_filters
    
    def test_recommendation_insights(self, customizer):
        """Test recommendation insights generation."""
        user_id = "test_user"
        
        # Add varied feedback
        feedback_data = [
            ("positive", 4, ["good_synergy", "meta_relevant"]),
            ("negative", 2, ["poor_synergy", "off_meta"]),
            ("positive", 5, ["good_individual_performance"]),
            ("negative", 1, ["poor_individual_performance"])
        ]
        
        for i, (feedback_type, rating, tags) in enumerate(feedback_data):
            customizer.record_user_feedback(
                user_id=user_id,
                recommendation_id=f"rec_{i}",
                champion_id=i + 1,
                role="top",
                feedback_type=feedback_type,
                accuracy_rating=rating,
                tags=tags
            )
        
        insights = customizer.get_recommendation_insights(user_id)
        
        assert 'summary' in insights
        assert 'patterns' in insights
        assert 'recommendations' in insights
        assert 'performance_trends' in insights
    
    def test_error_handling(self, customizer):
        """Test error handling in various scenarios."""
        # Test invalid parameter creation
        with pytest.raises(AnalyticsError):
            customizer.create_custom_parameters(
                "test_user",
                individual_performance_weight=2.0  # Invalid weight
            )
        
        # Test scenario with non-existent ID
        with pytest.raises(AnalyticsError):
            customizer.run_scenario_test(
                scenario_id="non_existent",
                puuid="test_puuid",
                role="top",
                user_id="test_user"
            )
        
        # Test optimization with insufficient feedback
        result = customizer.optimize_parameters_from_feedback(
            user_id="user_with_no_feedback",
            min_feedback_count=10
        )
        assert result is None


class TestAdvancedRecommendationInterface:
    """Test the Gradio interface for advanced recommendation customization."""
    
    @pytest.fixture
    def mock_core_engine(self):
        """Create mock core engine."""
        engine = Mock()
        engine.config = Mock()
        engine.champion_recommendation_engine = Mock()
        engine.data_manager = Mock()
        engine.data_manager.get_all_players.return_value = [
            Mock(name="Player1", summoner_name="summoner1"),
            Mock(name="Player2", summoner_name="summoner2")
        ]
        return engine
    
    @pytest.fixture
    def interface(self, mock_core_engine):
        """Create interface instance."""
        from lol_team_optimizer.advanced_recommendation_interface import AdvancedRecommendationInterface
        return AdvancedRecommendationInterface(mock_core_engine)
    
    def test_interface_initialization(self, interface):
        """Test interface initialization."""
        assert interface.core_engine is not None
        assert interface.customizer is not None
        assert interface.current_user_id == "default_user"
    
    def test_player_choices_generation(self, interface):
        """Test player choices generation for dropdowns."""
        choices = interface._get_player_choices()
        
        assert len(choices) > 0
        assert all(isinstance(choice, tuple) and len(choice) == 2 for choice in choices)
    
    def test_html_formatting_methods(self, interface):
        """Test HTML formatting methods."""
        # Test ban phase recommendations formatting
        recommendations = [
            {'champion_name': 'TestChamp', 'confidence': 0.8, 'score': 0.75, 'reasoning': ['Good synergy']}
        ]
        html = interface._format_ban_phase_recommendations(recommendations)
        assert 'TestChamp' in html
        assert '80.0%' in html
        
        # Test counter-pick opportunities formatting
        opportunities = [
            {'target_role': 'top', 'enemy_champion': 'EnemyChamp', 'counter_priority': 'high'}
        ]
        html = interface._format_counter_pick_opportunities(opportunities)
        assert 'top' in html
        assert 'EnemyChamp' in html
        
        # Test ban suggestions formatting
        suggestions = [
            {'champion_name': 'BanChamp', 'priority': 'high', 'reason': 'Strong meta pick'}
        ]
        html = interface._format_ban_suggestions(suggestions)
        assert 'BanChamp' in html
        assert 'Strong meta pick' in html
    
    def test_chart_creation_methods(self, interface):
        """Test chart creation methods."""
        # Mock report data
        report = {'metrics': {}, 'role_metrics': {}}
        
        # Test performance overview chart
        chart = interface._create_performance_overview_chart(report)
        assert chart is not None
        
        # Test role performance chart
        chart = interface._create_role_performance_chart(report)
        assert chart is not None
        
        # Test trend analysis chart
        chart = interface._create_trend_analysis_chart(report)
        assert chart is not None


if __name__ == "__main__":
    pytest.main([__file__])