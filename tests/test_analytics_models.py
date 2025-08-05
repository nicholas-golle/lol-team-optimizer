"""
Unit tests for analytics data models.

This module tests all analytics data models, their validation logic,
and error handling capabilities.
"""

import pytest
from datetime import datetime, timedelta
from lol_team_optimizer.analytics_models import (
    # Exceptions
    AnalyticsError, InsufficientDataError, BaselineCalculationError,
    StatisticalAnalysisError, DataValidationError,
    
    # Core data models
    DateRange, AnalyticsFilters, PerformanceMetrics, PerformanceDelta,
    ConfidenceInterval, SignificanceTest, ChampionPerformanceMetrics,
    RecentFormMetrics, PlayerRoleAssignment, TeamComposition,
    SynergyEffects, CompositionPerformance, RecommendationReasoning,
    PerformanceProjection, SynergyAnalysis, ChampionRecommendation,
    TeamContext, PlayerAnalytics, TrendAnalysis, ComparativeRankings
)


class TestExceptions:
    """Test analytics exception classes."""
    
    def test_insufficient_data_error(self):
        """Test InsufficientDataError creation and attributes."""
        error = InsufficientDataError(10, 5, "player analysis")
        assert error.required_games == 10
        assert error.available_games == 5
        assert error.context == "player analysis"
        assert "need 10, have 5" in str(error)
        assert "player analysis" in str(error)
    
    def test_insufficient_data_error_without_context(self):
        """Test InsufficientDataError without context."""
        error = InsufficientDataError(10, 5)
        assert error.context == ""
        assert "need 10, have 5" in str(error)
    
    def test_analytics_error_inheritance(self):
        """Test that all analytics errors inherit from AnalyticsError."""
        assert issubclass(InsufficientDataError, AnalyticsError)
        assert issubclass(BaselineCalculationError, AnalyticsError)
        assert issubclass(StatisticalAnalysisError, AnalyticsError)
        assert issubclass(DataValidationError, AnalyticsError)


class TestDateRange:
    """Test DateRange data model."""
    
    def test_valid_date_range(self):
        """Test creating a valid date range."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        date_range = DateRange(start, end)
        
        assert date_range.start_date == start
        assert date_range.end_date == end
        assert date_range.duration_days == 30
    
    def test_invalid_date_range(self):
        """Test creating an invalid date range."""
        start = datetime(2024, 1, 31)
        end = datetime(2024, 1, 1)
        
        with pytest.raises(DataValidationError, match="Start date must be before end date"):
            DateRange(start, end)
    
    def test_contains_method(self):
        """Test date range contains method."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        date_range = DateRange(start, end)
        
        assert date_range.contains(datetime(2024, 1, 15))
        assert date_range.contains(datetime(2024, 1, 1))  # boundary
        assert date_range.contains(datetime(2024, 1, 31))  # boundary
        assert not date_range.contains(datetime(2023, 12, 31))
        assert not date_range.contains(datetime(2024, 2, 1))


class TestAnalyticsFilters:
    """Test AnalyticsFilters data model."""
    
    def test_valid_filters(self):
        """Test creating valid analytics filters."""
        date_range = DateRange(datetime(2024, 1, 1), datetime(2024, 1, 31))
        filters = AnalyticsFilters(
            date_range=date_range,
            champions=[1, 2, 3],
            roles=["top", "jungle"],
            queue_types=[420, 440],
            teammates=["player1", "player2"],
            win_only=True,
            min_games=5
        )
        
        assert filters.date_range == date_range
        assert filters.champions == [1, 2, 3]
        assert filters.roles == ["top", "jungle"]
        assert filters.queue_types == [420, 440]
        assert filters.teammates == ["player1", "player2"]
        assert filters.win_only is True
        assert filters.min_games == 5
    
    def test_invalid_min_games(self):
        """Test invalid minimum games."""
        with pytest.raises(DataValidationError, match="Minimum games cannot be negative"):
            AnalyticsFilters(min_games=-1)
    
    def test_invalid_roles(self):
        """Test invalid roles."""
        with pytest.raises(DataValidationError, match="Invalid roles"):
            AnalyticsFilters(roles=["top", "invalid_role"])
    
    def test_default_values(self):
        """Test default filter values."""
        filters = AnalyticsFilters()
        assert filters.date_range is None
        assert filters.champions is None
        assert filters.roles is None
        assert filters.queue_types is None
        assert filters.teammates is None
        assert filters.win_only is None
        assert filters.min_games == 1


class TestPerformanceMetrics:
    """Test PerformanceMetrics data model."""
    
    def test_valid_performance_metrics(self):
        """Test creating valid performance metrics."""
        metrics = PerformanceMetrics(
            games_played=10,
            wins=7,
            losses=3,
            total_kills=50,
            total_deaths=25,
            total_assists=75,
            total_cs=1500,
            total_vision_score=200,
            total_damage_to_champions=150000,
            total_gold_earned=120000,
            total_game_duration=18000  # 5 hours in seconds
        )
        
        assert metrics.games_played == 10
        assert metrics.wins == 7
        assert metrics.losses == 3
        assert metrics.win_rate == 0.7
        assert metrics.avg_kda == 5.0  # (50 + 75) / 25
        assert metrics.avg_cs_per_min == 5.0  # 1500 / (18000/60)
        assert metrics.avg_vision_score == 20.0  # 200 / 10
        assert metrics.avg_damage_per_min == 500.0  # 150000 / (18000/60)
        assert metrics.avg_gold_per_min == 400.0  # 120000 / (18000/60)
        assert metrics.avg_game_duration == 30.0  # 18000 / (10 * 60)
    
    def test_invalid_games_played(self):
        """Test invalid games played."""
        with pytest.raises(DataValidationError, match="Games played cannot be negative"):
            PerformanceMetrics(games_played=-1)
    
    def test_invalid_wins_losses(self):
        """Test invalid wins and losses combination."""
        with pytest.raises(DataValidationError, match="Wins \\+ losses cannot exceed total games"):
            PerformanceMetrics(games_played=5, wins=3, losses=3)
    
    def test_zero_deaths_kda(self):
        """Test KDA calculation with zero deaths."""
        metrics = PerformanceMetrics(
            games_played=1,
            wins=1,
            total_kills=10,
            total_deaths=0,
            total_assists=5
        )
        assert metrics.avg_kda == 15.0  # (10 + 5) / max(0, 1)


class TestPerformanceDelta:
    """Test PerformanceDelta data model."""
    
    def test_positive_delta(self):
        """Test positive performance delta."""
        delta = PerformanceDelta(
            metric_name="win_rate",
            baseline_value=0.5,
            actual_value=0.7
        )
        
        assert abs(delta.delta_absolute - 0.2) < 1e-10
        assert abs(delta.delta_percentage - 40.0) < 1e-10
        assert delta.is_improvement is True
    
    def test_negative_delta(self):
        """Test negative performance delta."""
        delta = PerformanceDelta(
            metric_name="win_rate",
            baseline_value=0.7,
            actual_value=0.5
        )
        
        assert abs(delta.delta_absolute - (-0.2)) < 1e-10
        assert abs(delta.delta_percentage - (-28.571428571428573)) < 1e-10  # approximately -28.57%
        assert delta.is_improvement is False
    
    def test_zero_baseline(self):
        """Test delta with zero baseline."""
        delta = PerformanceDelta(
            metric_name="win_rate",
            baseline_value=0.0,
            actual_value=0.5
        )
        
        assert delta.delta_absolute == 0.5
        assert delta.delta_percentage == float('inf')
    
    def test_death_metric_improvement(self):
        """Test improvement logic for death-related metrics."""
        delta = PerformanceDelta(
            metric_name="avg_deaths",
            baseline_value=5.0,
            actual_value=3.0
        )
        
        assert delta.delta_absolute == -2.0
        assert delta.is_improvement is True  # Lower deaths is better


class TestConfidenceInterval:
    """Test ConfidenceInterval data model."""
    
    def test_valid_confidence_interval(self):
        """Test creating a valid confidence interval."""
        ci = ConfidenceInterval(
            lower_bound=0.4,
            upper_bound=0.6,
            confidence_level=0.95,
            sample_size=100
        )
        
        assert ci.lower_bound == 0.4
        assert ci.upper_bound == 0.6
        assert ci.confidence_level == 0.95
        assert ci.sample_size == 100
        assert abs(ci.margin_of_error - 0.1) < 1e-10
        assert ci.midpoint == 0.5
    
    def test_invalid_confidence_level(self):
        """Test invalid confidence level."""
        with pytest.raises(DataValidationError, match="Confidence level must be between 0 and 1"):
            ConfidenceInterval(0.4, 0.6, 1.5, 100)
    
    def test_invalid_bounds(self):
        """Test invalid bounds."""
        with pytest.raises(DataValidationError, match="Lower bound cannot be greater than upper bound"):
            ConfidenceInterval(0.6, 0.4, 0.95, 100)
    
    def test_invalid_sample_size(self):
        """Test invalid sample size."""
        with pytest.raises(DataValidationError, match="Sample size must be positive"):
            ConfidenceInterval(0.4, 0.6, 0.95, 0)


class TestSignificanceTest:
    """Test SignificanceTest data model."""
    
    def test_valid_significance_test(self):
        """Test creating a valid significance test."""
        test = SignificanceTest(
            test_type="t-test",
            statistic=2.5,
            p_value=0.02,
            degrees_of_freedom=98,
            effect_size=0.3
        )
        
        assert test.test_type == "t-test"
        assert test.statistic == 2.5
        assert test.p_value == 0.02
        assert test.degrees_of_freedom == 98
        assert test.effect_size == 0.3
        assert test.is_significant() is True
        assert test.is_significant(alpha=0.01) is False
    
    def test_invalid_p_value(self):
        """Test invalid p-value."""
        with pytest.raises(DataValidationError, match="P-value must be between 0 and 1"):
            SignificanceTest("t-test", 2.5, 1.5)


class TestChampionPerformanceMetrics:
    """Test ChampionPerformanceMetrics data model."""
    
    def test_valid_champion_performance(self):
        """Test creating valid champion performance metrics."""
        performance = PerformanceMetrics(games_played=10, wins=7)
        champion_perf = ChampionPerformanceMetrics(
            champion_id=1,
            champion_name="Annie",
            role="middle",
            performance=performance
        )
        
        assert champion_perf.champion_id == 1
        assert champion_perf.champion_name == "Annie"
        assert champion_perf.role == "middle"
        assert champion_perf.performance == performance
    
    def test_invalid_champion_id(self):
        """Test invalid champion ID."""
        performance = PerformanceMetrics()
        with pytest.raises(DataValidationError, match="Champion ID must be positive"):
            ChampionPerformanceMetrics(0, "Annie", "middle", performance)
    
    def test_empty_champion_name(self):
        """Test empty champion name."""
        performance = PerformanceMetrics()
        with pytest.raises(DataValidationError, match="Champion name cannot be empty"):
            ChampionPerformanceMetrics(1, "", "middle", performance)
    
    def test_empty_role(self):
        """Test empty role."""
        performance = PerformanceMetrics()
        with pytest.raises(DataValidationError, match="Role cannot be empty"):
            ChampionPerformanceMetrics(1, "Annie", "", performance)


class TestRecentFormMetrics:
    """Test RecentFormMetrics data model."""
    
    def test_valid_recent_form(self):
        """Test creating valid recent form metrics."""
        form = RecentFormMetrics(
            recent_games=10,
            recent_win_rate=0.7,
            recent_avg_kda=2.5,
            trend_direction="improving",
            trend_strength=0.8,
            form_score=0.6
        )
        
        assert form.recent_games == 10
        assert form.recent_win_rate == 0.7
        assert form.recent_avg_kda == 2.5
        assert form.trend_direction == "improving"
        assert form.trend_strength == 0.8
        assert form.form_score == 0.6
    
    def test_invalid_trend_direction(self):
        """Test invalid trend direction."""
        with pytest.raises(DataValidationError, match="Trend direction must be one of"):
            RecentFormMetrics(
                recent_games=10,
                recent_win_rate=0.7,
                recent_avg_kda=2.5,
                trend_direction="invalid",
                trend_strength=0.8,
                form_score=0.6
            )
    
    def test_invalid_form_score(self):
        """Test invalid form score."""
        with pytest.raises(DataValidationError, match="Form score must be between -1 and 1"):
            RecentFormMetrics(
                recent_games=10,
                recent_win_rate=0.7,
                recent_avg_kda=2.5,
                trend_direction="stable",
                trend_strength=0.8,
                form_score=1.5
            )


class TestPlayerRoleAssignment:
    """Test PlayerRoleAssignment data model."""
    
    def test_valid_assignment(self):
        """Test creating a valid player role assignment."""
        assignment = PlayerRoleAssignment(
            puuid="test-puuid",
            player_name="TestPlayer",
            role="top",
            champion_id=1,
            champion_name="Annie"
        )
        
        assert assignment.puuid == "test-puuid"
        assert assignment.player_name == "TestPlayer"
        assert assignment.role == "top"
        assert assignment.champion_id == 1
        assert assignment.champion_name == "Annie"
    
    def test_empty_puuid(self):
        """Test empty PUUID."""
        with pytest.raises(DataValidationError, match="PUUID cannot be empty"):
            PlayerRoleAssignment("", "TestPlayer", "top", 1, "Annie")
    
    def test_invalid_champion_id(self):
        """Test invalid champion ID."""
        with pytest.raises(DataValidationError, match="Champion ID must be positive"):
            PlayerRoleAssignment("test-puuid", "TestPlayer", "top", 0, "Annie")


class TestTeamComposition:
    """Test TeamComposition data model."""
    
    def test_valid_composition(self):
        """Test creating a valid team composition."""
        players = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Graves")
        }
        composition = TeamComposition(players=players)
        
        assert len(composition.players) == 2
        assert composition.player_count == 2
        assert "puuid1" in composition.get_player_puuids()
        assert "puuid2" in composition.get_player_puuids()
        assert 1 in composition.get_champion_ids()
        assert 2 in composition.get_champion_ids()
        assert composition.composition_id  # Should be auto-generated
    
    def test_empty_composition(self):
        """Test empty team composition."""
        with pytest.raises(DataValidationError, match="Team composition must have at least one player"):
            TeamComposition(players={})
    
    def test_invalid_role(self):
        """Test invalid role in composition."""
        players = {
            "invalid_role": PlayerRoleAssignment("puuid1", "Player1", "invalid_role", 1, "Annie")
        }
        with pytest.raises(DataValidationError, match="Invalid roles in composition"):
            TeamComposition(players=players)
    
    def test_custom_composition_id(self):
        """Test custom composition ID."""
        players = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie")
        }
        composition = TeamComposition(players=players, composition_id="custom-id")
        assert composition.composition_id == "custom-id"


class TestSynergyEffects:
    """Test SynergyEffects data model."""
    
    def test_valid_synergy_effects(self):
        """Test creating valid synergy effects."""
        synergy = SynergyEffects(
            overall_synergy=0.2,
            role_pair_synergies={("top", "jungle"): 0.3},
            champion_synergies={(1, 2): 0.1},
            player_synergies={("player1", "player2"): 0.25}
        )
        
        assert synergy.overall_synergy == 0.2
        assert synergy.role_pair_synergies[("top", "jungle")] == 0.3
        assert synergy.champion_synergies[(1, 2)] == 0.1
        assert synergy.player_synergies[("player1", "player2")] == 0.25
    
    def test_invalid_overall_synergy(self):
        """Test invalid overall synergy."""
        with pytest.raises(DataValidationError, match="Overall synergy must be between -1 and 1"):
            SynergyEffects(overall_synergy=1.5)
    
    def test_invalid_individual_synergy(self):
        """Test invalid individual synergy score."""
        with pytest.raises(DataValidationError, match="Synergy score .* must be between -1 and 1"):
            SynergyEffects(
                overall_synergy=0.2,
                role_pair_synergies={("top", "jungle"): 1.5}
            )


class TestCompositionPerformance:
    """Test CompositionPerformance data model."""
    
    def test_valid_composition_performance(self):
        """Test creating valid composition performance."""
        players = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie")
        }
        composition = TeamComposition(players=players)
        performance = PerformanceMetrics(games_played=10, wins=7)
        
        comp_perf = CompositionPerformance(
            composition=composition,
            total_games=10,
            performance=performance
        )
        
        assert comp_perf.composition == composition
        assert comp_perf.total_games == 10
        assert comp_perf.performance == performance
    
    def test_mismatched_games(self):
        """Test mismatched total games and performance games."""
        players = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie")
        }
        composition = TeamComposition(players=players)
        performance = PerformanceMetrics(games_played=5, wins=3)
        
        with pytest.raises(DataValidationError, match="Total games must match performance games played"):
            CompositionPerformance(
                composition=composition,
                total_games=10,
                performance=performance
            )


class TestChampionRecommendation:
    """Test ChampionRecommendation data model."""
    
    def test_valid_recommendation(self):
        """Test creating a valid champion recommendation."""
        recommendation = ChampionRecommendation(
            champion_id=1,
            champion_name="Annie",
            role="middle",
            recommendation_score=0.8,
            confidence=0.9
        )
        
        assert recommendation.champion_id == 1
        assert recommendation.champion_name == "Annie"
        assert recommendation.role == "middle"
        assert recommendation.recommendation_score == 0.8
        assert recommendation.confidence == 0.9
    
    def test_invalid_recommendation_score(self):
        """Test invalid recommendation score."""
        with pytest.raises(DataValidationError, match="Recommendation score must be between 0 and 1"):
            ChampionRecommendation(1, "Annie", "middle", 1.5, 0.9)
    
    def test_invalid_confidence(self):
        """Test invalid confidence score."""
        with pytest.raises(DataValidationError, match="Confidence must be between 0 and 1"):
            ChampionRecommendation(1, "Annie", "middle", 0.8, 1.5)


class TestTeamContext:
    """Test TeamContext data model."""
    
    def test_valid_team_context(self):
        """Test creating valid team context."""
        existing_picks = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie")
        }
        context = TeamContext(
            existing_picks=existing_picks,
            target_role="jungle",
            target_player_puuid="puuid2"
        )
        
        assert context.existing_picks == existing_picks
        assert context.target_role == "jungle"
        assert context.target_player_puuid == "puuid2"
    
    def test_invalid_target_role(self):
        """Test invalid target role."""
        with pytest.raises(DataValidationError, match="Target role must be one of"):
            TeamContext({}, "invalid_role", "puuid2")
    
    def test_target_role_already_assigned(self):
        """Test target role already assigned."""
        existing_picks = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Annie")
        }
        with pytest.raises(DataValidationError, match="Target role cannot already be assigned"):
            TeamContext(existing_picks, "top", "puuid2")


class TestPlayerAnalytics:
    """Test PlayerAnalytics data model."""
    
    def test_valid_player_analytics(self):
        """Test creating valid player analytics."""
        date_range = DateRange(datetime(2024, 1, 1), datetime(2024, 1, 31))
        performance = PerformanceMetrics(games_played=10, wins=7)
        
        analytics = PlayerAnalytics(
            puuid="test-puuid",
            player_name="TestPlayer",
            analysis_period=date_range,
            overall_performance=performance
        )
        
        assert analytics.puuid == "test-puuid"
        assert analytics.player_name == "TestPlayer"
        assert analytics.analysis_period == date_range
        assert analytics.overall_performance == performance
    
    def test_empty_puuid(self):
        """Test empty PUUID."""
        date_range = DateRange(datetime(2024, 1, 1), datetime(2024, 1, 31))
        performance = PerformanceMetrics()
        
        with pytest.raises(DataValidationError, match="PUUID cannot be empty"):
            PlayerAnalytics("", "TestPlayer", date_range, performance)


class TestTrendAnalysis:
    """Test TrendAnalysis data model."""
    
    def test_valid_trend_analysis(self):
        """Test creating valid trend analysis."""
        trend = TrendAnalysis(
            trend_direction="improving",
            trend_strength=0.8,
            trend_duration_days=30
        )
        
        assert trend.trend_direction == "improving"
        assert trend.trend_strength == 0.8
        assert trend.trend_duration_days == 30
    
    def test_invalid_trend_direction(self):
        """Test invalid trend direction."""
        with pytest.raises(DataValidationError, match="Trend direction must be one of"):
            TrendAnalysis("invalid", 0.8, 30)
    
    def test_invalid_trend_strength(self):
        """Test invalid trend strength."""
        with pytest.raises(DataValidationError, match="Trend strength must be between 0 and 1"):
            TrendAnalysis("improving", 1.5, 30)


class TestComparativeRankings:
    """Test ComparativeRankings data model."""
    
    def test_valid_rankings(self):
        """Test creating valid comparative rankings."""
        rankings = ComparativeRankings(
            overall_percentile=75.0,
            role_percentiles={"top": 80.0, "jungle": 70.0},
            champion_percentiles={1: 85.0, 2: 65.0},
            peer_group_size=100
        )
        
        assert rankings.overall_percentile == 75.0
        assert rankings.role_percentiles["top"] == 80.0
        assert rankings.champion_percentiles[1] == 85.0
        assert rankings.peer_group_size == 100
    
    def test_invalid_overall_percentile(self):
        """Test invalid overall percentile."""
        with pytest.raises(DataValidationError, match="Overall percentile must be between 0 and 100"):
            ComparativeRankings(overall_percentile=150.0)
    
    def test_invalid_role_percentile(self):
        """Test invalid role percentile."""
        with pytest.raises(DataValidationError, match="Role percentile .* must be between 0 and 100"):
            ComparativeRankings(
                overall_percentile=75.0,
                role_percentiles={"top": 150.0}
            )


if __name__ == "__main__":
    pytest.main([__file__])