"""
Tests for the Comparative Analyzer module.

This module tests the comparative analysis and ranking systems including
multi-player comparisons, percentile rankings, peer group analysis, and
statistical validation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import statistics

from lol_team_optimizer.comparative_analyzer import (
    ComparativeAnalyzer, RankingBasis, SkillTier, PlayerComparison,
    MultiPlayerComparison, PeerGroupAnalysis, RoleSpecificRanking,
    ChampionSpecificRanking
)
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters, PerformanceMetrics, PerformanceDelta, DateRange,
    ComparativeRankings, AnalyticsError, InsufficientDataError
)
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestComparativeAnalyzer:
    """Test suite for ComparativeAnalyzer class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        match_manager = Mock()
        return match_manager
    
    @pytest.fixture
    def mock_baseline_manager(self):
        """Create mock baseline manager."""
        baseline_manager = Mock()
        return baseline_manager
    
    @pytest.fixture
    def analyzer(self, mock_config, mock_match_manager, mock_baseline_manager):
        """Create ComparativeAnalyzer instance."""
        return ComparativeAnalyzer(mock_config, mock_match_manager, mock_baseline_manager)
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample match data."""
        matches = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(20):
            match = Mock(spec=Match)
            match.game_creation_datetime = base_date + timedelta(days=i)
            match.game_duration = 1800 + (i * 60)  # 30-50 minutes
            match.queue_id = 420  # Ranked Solo/Duo
            
            participant = Mock(spec=MatchParticipant)
            participant.summoner_name = f"Player_{i % 3}"
            participant.champion_id = 1 + (i % 5)
            participant.champion_name = f"Champion_{participant.champion_id}"
            participant.individual_position = ["top", "jungle", "middle", "bottom", "support"][i % 5]
            participant.win = i % 3 != 0  # ~67% win rate
            participant.kills = 5 + (i % 10)
            participant.deaths = 3 + (i % 5)
            participant.assists = 8 + (i % 7)
            participant.total_minions_killed = 150 + (i * 5)
            participant.neutral_minions_killed = 20 + (i * 2)
            participant.vision_score = 40 + (i * 3)
            participant.total_damage_dealt_to_champions = 15000 + (i * 1000)
            participant.gold_earned = 12000 + (i * 500)
            
            matches.append((match, participant))
        
        return matches
    
    @pytest.fixture
    def sample_performance_metrics(self):
        """Create sample performance metrics."""
        return PerformanceMetrics(
            games_played=20,
            wins=14,
            losses=6,
            win_rate=0.7,
            total_kills=120,
            total_deaths=60,
            total_assists=160,
            avg_kda=4.67,
            total_cs=3600,
            avg_cs_per_min=6.0,
            total_vision_score=1000,
            avg_vision_score=50.0,
            total_damage_to_champions=320000,
            avg_damage_per_min=533.33,
            total_gold_earned=250000,
            avg_gold_per_min=416.67,
            total_game_duration=36000,
            avg_game_duration=30.0
        )
    
    def test_initialization(self, analyzer, mock_config, mock_match_manager, mock_baseline_manager):
        """Test ComparativeAnalyzer initialization."""
        assert analyzer.config == mock_config
        assert analyzer.match_manager == mock_match_manager
        assert analyzer.baseline_manager == mock_baseline_manager
        assert analyzer.min_games_for_comparison == 10
        assert analyzer.min_peer_group_size == 5
        assert analyzer.significance_level == 0.05
        assert len(analyzer.comparison_metrics) == 6
    
    def test_compare_players_success(self, analyzer, sample_matches):
        """Test successful multi-player comparison."""
        # Mock match manager to return different data for each player
        def mock_get_matches(puuid):
            # Return different subsets of matches for each player
            if puuid == "player1":
                return sample_matches[:15]  # 15 matches
            elif puuid == "player2":
                return sample_matches[5:20]  # 15 matches
            else:
                return sample_matches[10:]  # 10 matches
        
        analyzer.match_manager.get_player_matches.side_effect = mock_get_matches
        
        # Test comparison
        player_puuids = ["player1", "player2", "player3"]
        comparisons = analyzer.compare_players(player_puuids)
        
        # Verify results
        assert isinstance(comparisons, dict)
        assert len(comparisons) > 0
        
        for metric, comparison in comparisons.items():
            assert isinstance(comparison, MultiPlayerComparison)
            assert comparison.metric == metric
            assert len(comparison.players) <= 3  # Some players might be filtered out
            assert len(comparison.values) == len(comparison.players)
            assert len(comparison.rankings) == len(comparison.players)
            assert len(comparison.percentiles) == len(comparison.players)
    
    def test_compare_players_insufficient_data(self, analyzer):
        """Test comparison with insufficient data."""
        # Mock match manager to return insufficient matches
        analyzer.match_manager.get_player_matches.return_value = []
        
        player_puuids = ["player1", "player2"]
        
        with pytest.raises(InsufficientDataError):
            analyzer.compare_players(player_puuids)
    
    def test_compare_players_too_few_players(self, analyzer):
        """Test comparison with too few players."""
        with pytest.raises(AnalyticsError, match="Need at least 2 players"):
            analyzer.compare_players(["player1"])
    
    def test_calculate_percentile_rankings_success(self, analyzer, sample_matches):
        """Test successful percentile ranking calculation."""
        # Mock match manager
        analyzer.match_manager.get_player_matches.return_value = sample_matches
        
        target_player = "target_player"
        comparison_pool = ["player1", "player2", "player3", "player4", "player5"]
        
        rankings = analyzer.calculate_percentile_rankings(target_player, comparison_pool)
        
        # Verify results
        assert isinstance(rankings, ComparativeRankings)
        assert 0 <= rankings.overall_percentile <= 100
        assert len(rankings.role_percentiles) > 0
        assert rankings.peer_group_size > 0
        assert rankings.ranking_basis == RankingBasis.ALL_PLAYERS.value
        
        # Check that all percentiles are valid
        for percentile in rankings.role_percentiles.values():
            assert 0 <= percentile <= 100
    
    def test_calculate_percentile_rankings_insufficient_data(self, analyzer):
        """Test percentile ranking with insufficient data."""
        # Mock match manager to return insufficient matches
        analyzer.match_manager.get_player_matches.return_value = []
        
        target_player = "target_player"
        comparison_pool = ["player1", "player2"]
        
        with pytest.raises(InsufficientDataError):
            analyzer.calculate_percentile_rankings(target_player, comparison_pool)
    
    def test_analyze_peer_group_success(self, analyzer, sample_matches):
        """Test successful peer group analysis."""
        # Mock match manager
        analyzer.match_manager.get_player_matches.return_value = sample_matches
        
        target_player = "target_player"
        peer_pool = ["peer1", "peer2", "peer3", "peer4", "peer5", "peer6"]
        skill_tier = SkillTier.GOLD
        
        analysis = analyzer.analyze_peer_group(target_player, skill_tier, peer_pool)
        
        # Verify results
        assert isinstance(analysis, PeerGroupAnalysis)
        assert analysis.target_player == target_player
        assert analysis.skill_tier == skill_tier
        assert analysis.peer_group_size >= analyzer.min_peer_group_size
        assert len(analysis.target_rankings) > 0
        assert len(analysis.target_percentiles) > 0
        assert len(analysis.peer_averages) > 0
        assert len(analysis.performance_vs_peers) > 0
        
        # Check that rankings are valid
        for rank in analysis.target_rankings.values():
            assert rank >= 1
            assert rank <= analysis.peer_group_size + 1  # +1 for target player
        
        # Check that percentiles are valid
        for percentile in analysis.target_percentiles.values():
            assert 0 <= percentile <= 100
    
    def test_analyze_peer_group_insufficient_peers(self, analyzer, sample_matches):
        """Test peer group analysis with insufficient peers."""
        # Mock match manager to return data for target but not enough peers
        def mock_get_matches(puuid):
            if puuid == "target_player":
                return sample_matches
            else:
                return []  # No data for peers
        
        analyzer.match_manager.get_player_matches.side_effect = mock_get_matches
        
        target_player = "target_player"
        peer_pool = ["peer1", "peer2"]  # Too few peers
        skill_tier = SkillTier.GOLD
        
        with pytest.raises(InsufficientDataError):
            analyzer.analyze_peer_group(target_player, skill_tier, peer_pool)
    
    def test_calculate_role_specific_rankings_success(self, analyzer, sample_matches):
        """Test successful role-specific ranking calculation."""
        # Create matches with specific role
        role_matches = []
        for i, (match, participant) in enumerate(sample_matches):
            # Set all participants to middle role for this test
            participant.individual_position = "middle"
            role_matches.append((match, participant))
        
        # Mock the _get_filtered_matches method directly to return role_matches for all players
        def mock_get_filtered_matches(puuid, filters):
            return role_matches
        
        analyzer._get_filtered_matches = mock_get_filtered_matches
        
        player_puuid = "test_player"
        role = "middle"
        role_player_pool = ["test_player", "player1", "player2", "player3", "player4", "player5", "player6"]
        
        ranking = analyzer.calculate_role_specific_rankings(
            player_puuid, role, role_player_pool
        )
        
        # Verify results
        assert isinstance(ranking, RoleSpecificRanking)
        assert ranking.role == role
        assert ranking.player_puuid == player_puuid
        assert ranking.total_role_players >= analyzer.min_peer_group_size
        assert len(ranking.rankings) > 0
        assert len(ranking.percentiles) > 0
        assert len(ranking.role_averages) > 0
        assert len(ranking.performance_vs_role) > 0
        assert len(ranking.top_performers) > 0
        
        # Check that rankings are valid
        for rank in ranking.rankings.values():
            assert rank >= 1
            assert rank <= ranking.total_role_players
        
        # Check that percentiles are valid
        for percentile in ranking.percentiles.values():
            assert 0 <= percentile <= 100
    
    def test_calculate_champion_specific_rankings_success(self, analyzer, sample_matches):
        """Test successful champion-specific ranking calculation."""
        # Create matches with specific champion
        champion_matches = []
        for i, (match, participant) in enumerate(sample_matches):
            # Set all participants to champion 1 for this test
            participant.champion_id = 1
            participant.champion_name = "Champion_1"
            champion_matches.append((match, participant))
        
        # Mock the _get_filtered_matches method directly to return champion_matches for all players
        def mock_get_filtered_matches(puuid, filters):
            return champion_matches
        
        analyzer._get_filtered_matches = mock_get_filtered_matches
        
        player_puuid = "test_player"
        champion_id = 1
        champion_player_pool = ["test_player", "player1", "player2", "player3", "player4", "player5", "player6"]
        
        ranking = analyzer.calculate_champion_specific_rankings(
            player_puuid, champion_id, champion_player_pool
        )
        
        # Verify results
        assert isinstance(ranking, ChampionSpecificRanking)
        assert ranking.champion_id == champion_id
        assert ranking.player_puuid == player_puuid
        assert ranking.total_champion_players >= analyzer.min_peer_group_size
        assert len(ranking.rankings) > 0
        assert len(ranking.percentiles) > 0
        assert len(ranking.champion_averages) > 0
        assert len(ranking.performance_vs_champion) > 0
        assert ranking.mastery_level in ["novice", "competent", "expert", "master"]
        
        # Check that rankings are valid
        for rank in ranking.rankings.values():
            assert rank >= 1
            assert rank <= ranking.total_champion_players
        
        # Check that percentiles are valid
        for percentile in ranking.percentiles.values():
            assert 0 <= percentile <= 100
    
    def test_prepare_comparative_visualization_data_radar_chart(self, analyzer):
        """Test preparation of radar chart visualization data."""
        # Create mock comparison data
        comparisons = {}
        players = ["player1", "player2", "player3"]
        player_names = {"player1": "Alice", "player2": "Bob", "player3": "Charlie"}
        
        for metric in ["win_rate", "avg_kda", "avg_cs_per_min"]:
            comparison = Mock(spec=MultiPlayerComparison)
            comparison.players = players
            comparison.player_names = player_names
            comparison.percentiles = {
                "player1": 75.0,
                "player2": 60.0,
                "player3": 85.0
            }
            comparisons[metric] = comparison
        
        viz_data = analyzer.prepare_comparative_visualization_data(
            comparisons, format_type="radar_chart"
        )
        
        # Verify results
        assert viz_data["type"] == "radar_chart"
        assert viz_data["metrics"] == list(comparisons.keys())
        assert viz_data["players"] == players
        assert viz_data["player_names"] == player_names
        assert "data" in viz_data
        assert viz_data["scale"]["min"] == 0
        assert viz_data["scale"]["max"] == 100
        assert viz_data["scale"]["unit"] == "percentile"
        
        # Check data structure
        for player in players:
            assert player in viz_data["data"]
            assert len(viz_data["data"][player]) == len(comparisons)
    
    def test_prepare_comparative_visualization_data_bar_chart(self, analyzer):
        """Test preparation of bar chart visualization data."""
        # Create mock comparison data
        comparisons = {}
        players = ["player1", "player2"]
        player_names = {"player1": "Alice", "player2": "Bob"}
        
        comparison = Mock(spec=MultiPlayerComparison)
        comparison.players = players
        comparison.player_names = player_names
        comparison.values = {"player1": 0.75, "player2": 0.60}
        comparison.rankings = {"player1": 1, "player2": 2}
        comparison.percentiles = {"player1": 75.0, "player2": 60.0}
        comparisons["win_rate"] = comparison
        
        viz_data = analyzer.prepare_comparative_visualization_data(
            comparisons, format_type="bar_chart"
        )
        
        # Verify results
        assert viz_data["type"] == "bar_chart"
        assert "data" in viz_data
        assert "win_rate" in viz_data["data"]
        assert len(viz_data["data"]["win_rate"]) == 2
        
        # Check data structure
        for item in viz_data["data"]["win_rate"]:
            assert "player" in item
            assert "player_name" in item
            assert "value" in item
            assert "rank" in item
            assert "percentile" in item
    
    def test_prepare_comparative_visualization_data_heatmap(self, analyzer):
        """Test preparation of heatmap visualization data."""
        # Create mock comparison data
        comparisons = {}
        players = ["player1", "player2"]
        player_names = {"player1": "Alice", "player2": "Bob"}
        
        for metric in ["win_rate", "avg_kda"]:
            comparison = Mock(spec=MultiPlayerComparison)
            comparison.players = players
            comparison.player_names = player_names
            comparison.percentiles = {
                "player1": 75.0,
                "player2": 60.0
            }
            comparisons[metric] = comparison
        
        viz_data = analyzer.prepare_comparative_visualization_data(
            comparisons, format_type="heatmap"
        )
        
        # Verify results
        assert viz_data["type"] == "heatmap"
        assert "matrix" in viz_data
        assert len(viz_data["matrix"]) == len(players)
        assert len(viz_data["matrix"][0]) == len(comparisons)
        assert viz_data["players"] == players
        assert viz_data["player_names"] == player_names
        assert viz_data["metrics"] == list(comparisons.keys())
        assert viz_data["scale"]["min"] == 0
        assert viz_data["scale"]["max"] == 100
        assert viz_data["color_scheme"] == "RdYlGn"
    
    def test_prepare_comparative_visualization_data_invalid_format(self, analyzer):
        """Test visualization data preparation with invalid format."""
        comparisons = {"win_rate": Mock()}
        
        with pytest.raises(AnalyticsError, match="Unknown visualization format"):
            analyzer.prepare_comparative_visualization_data(
                comparisons, format_type="invalid_format"
            )
    
    def test_prepare_comparative_visualization_data_empty_comparisons(self, analyzer):
        """Test visualization data preparation with empty comparisons."""
        with pytest.raises(AnalyticsError, match="No comparison data provided"):
            analyzer.prepare_comparative_visualization_data({})
    
    def test_calculate_percentile_edge_cases(self, analyzer):
        """Test percentile calculation edge cases."""
        # Test with empty list
        percentile = analyzer._calculate_percentile(50.0, [])
        assert percentile == 50.0
        
        # Test with single value
        percentile = analyzer._calculate_percentile(50.0, [50.0])
        assert percentile == 50.0
        
        # Test with all same values
        percentile = analyzer._calculate_percentile(50.0, [50.0, 50.0, 50.0])
        assert percentile == 50.0
        
        # Test with minimum value
        percentile = analyzer._calculate_percentile(10.0, [10.0, 20.0, 30.0, 40.0, 50.0])
        assert percentile == 10.0
        
        # Test with maximum value
        percentile = analyzer._calculate_percentile(50.0, [10.0, 20.0, 30.0, 40.0, 50.0])
        assert percentile == 90.0
        
        # Test with middle value
        percentile = analyzer._calculate_percentile(30.0, [10.0, 20.0, 30.0, 40.0, 50.0])
        assert percentile == 50.0
    
    def test_extract_metric_values(self, analyzer, sample_matches):
        """Test extraction of metric values from matches."""
        # Test win rate extraction
        win_values = analyzer._extract_metric_values(sample_matches, "win_rate")
        assert len(win_values) == len(sample_matches)
        assert all(v in [0.0, 1.0] for v in win_values)
        
        # Test KDA extraction
        kda_values = analyzer._extract_metric_values(sample_matches, "avg_kda")
        assert len(kda_values) == len(sample_matches)
        assert all(v >= 0 for v in kda_values)
        
        # Test CS per minute extraction
        cs_values = analyzer._extract_metric_values(sample_matches, "avg_cs_per_min")
        assert len(cs_values) == len(sample_matches)
        assert all(v >= 0 for v in cs_values)
        
        # Test vision score extraction
        vision_values = analyzer._extract_metric_values(sample_matches, "avg_vision_score")
        assert len(vision_values) == len(sample_matches)
        assert all(v >= 0 for v in vision_values)
    
    def test_determine_mastery_level(self, analyzer):
        """Test mastery level determination."""
        # Test novice (few games)
        mastery = analyzer._determine_mastery_level(5, {"win_rate": 50.0})
        assert mastery == "novice"
        
        # Test novice (many games, low performance)
        mastery = analyzer._determine_mastery_level(30, {"win_rate": 25.0, "avg_kda": 30.0})
        assert mastery == "novice"
        
        # Test competent
        mastery = analyzer._determine_mastery_level(25, {"win_rate": 60.0, "avg_kda": 55.0})
        assert mastery == "competent"
        
        # Test expert
        mastery = analyzer._determine_mastery_level(35, {"win_rate": 80.0, "avg_kda": 75.0})
        assert mastery == "expert"
        
        # Test master
        mastery = analyzer._determine_mastery_level(60, {"win_rate": 95.0, "avg_kda": 90.0})
        assert mastery == "master"
    
    def test_calculate_performance_metrics(self, analyzer, sample_matches):
        """Test performance metrics calculation."""
        performance = analyzer._calculate_performance_metrics(sample_matches)
        
        # Verify basic metrics
        assert isinstance(performance, PerformanceMetrics)
        assert performance.games_played == len(sample_matches)
        assert performance.wins + performance.losses == performance.games_played
        assert 0 <= performance.win_rate <= 1
        assert performance.avg_kda >= 0
        assert performance.avg_cs_per_min >= 0
        assert performance.avg_vision_score >= 0
        assert performance.avg_damage_per_min >= 0
        assert performance.avg_gold_per_min >= 0
        assert performance.avg_game_duration >= 0
    
    def test_calculate_performance_metrics_empty_matches(self, analyzer):
        """Test performance metrics calculation with empty matches."""
        performance = analyzer._calculate_performance_metrics([])
        
        assert isinstance(performance, PerformanceMetrics)
        assert performance.games_played == 0
        assert performance.wins == 0
        assert performance.losses == 0
        assert performance.win_rate == 0
        assert performance.avg_kda == 0
        assert performance.avg_cs_per_min == 0
        assert performance.avg_vision_score == 0


class TestPlayerComparison:
    """Test suite for PlayerComparison dataclass."""
    
    def test_player_comparison_creation(self):
        """Test PlayerComparison creation and properties."""
        comparison = PlayerComparison(
            player1_puuid="player1",
            player2_puuid="player2",
            player1_name="Alice",
            player2_name="Bob",
            metric="win_rate",
            player1_value=0.75,
            player2_value=0.60,
            difference=0.15,
            percentage_difference=25.0,
            sample_sizes=(20, 18)
        )
        
        assert comparison.player1_puuid == "player1"
        assert comparison.player2_puuid == "player2"
        assert comparison.metric == "win_rate"
        assert comparison.difference == 0.15
        assert comparison.percentage_difference == 25.0
        assert comparison.better_player == "player1"
        assert not comparison.is_significant  # No statistical test provided
    
    def test_player_comparison_with_significance(self):
        """Test PlayerComparison with statistical significance."""
        from lol_team_optimizer.analytics_models import SignificanceTest
        
        sig_test = SignificanceTest(
            test_type="t_test",
            statistic=2.5,
            p_value=0.02,
            degrees_of_freedom=36
        )
        
        comparison = PlayerComparison(
            player1_puuid="player1",
            player2_puuid="player2",
            player1_name="Alice",
            player2_name="Bob",
            metric="win_rate",
            player1_value=0.75,
            player2_value=0.60,
            difference=0.15,
            percentage_difference=25.0,
            statistical_significance=sig_test,
            sample_sizes=(20, 18)
        )
        
        assert comparison.is_significant
        assert comparison.better_player == "player1"


class TestMultiPlayerComparison:
    """Test suite for MultiPlayerComparison dataclass."""
    
    def test_multi_player_comparison_creation(self):
        """Test MultiPlayerComparison creation and methods."""
        comparison = MultiPlayerComparison(
            metric="win_rate",
            players=["player1", "player2", "player3"],
            player_names={"player1": "Alice", "player2": "Bob", "player3": "Charlie"},
            values={"player1": 0.75, "player2": 0.60, "player3": 0.80},
            rankings={"player1": 2, "player2": 3, "player3": 1},
            percentiles={"player1": 66.7, "player2": 33.3, "player3": 100.0}
        )
        
        assert comparison.metric == "win_rate"
        assert len(comparison.players) == 3
        
        # Test top performers
        top_performers = comparison.get_top_performers(2)
        assert len(top_performers) == 2
        assert "player3" in top_performers  # Rank 1
        assert "player1" in top_performers  # Rank 2
        
        # Test bottom performers
        bottom_performers = comparison.get_bottom_performers(1)
        assert len(bottom_performers) == 1
        assert "player2" in bottom_performers  # Rank 3


class TestPeerGroupAnalysis:
    """Test suite for PeerGroupAnalysis dataclass."""
    
    def test_peer_group_analysis_creation(self):
        """Test PeerGroupAnalysis creation."""
        from lol_team_optimizer.analytics_models import PerformanceDelta
        
        analysis = PeerGroupAnalysis(
            target_player="target",
            peer_group=["peer1", "peer2", "peer3"],
            skill_tier=SkillTier.GOLD,
            peer_group_size=3,
            target_rankings={"win_rate": 2, "avg_kda": 1},
            target_percentiles={"win_rate": 66.7, "avg_kda": 100.0},
            peer_averages={"win_rate": 0.60, "avg_kda": 2.5},
            performance_vs_peers={
                "win_rate": PerformanceDelta("win_rate", 0.60, 0.70),
                "avg_kda": PerformanceDelta("avg_kda", 2.5, 3.0)
            },
            strengths=["avg_kda"],
            weaknesses=[]
        )
        
        assert analysis.target_player == "target"
        assert analysis.skill_tier == SkillTier.GOLD
        assert analysis.peer_group_size == 3
        assert len(analysis.strengths) == 1
        assert len(analysis.weaknesses) == 0


class TestRoleSpecificRanking:
    """Test suite for RoleSpecificRanking dataclass."""
    
    def test_role_specific_ranking_creation(self):
        """Test RoleSpecificRanking creation."""
        from lol_team_optimizer.analytics_models import PerformanceDelta
        
        ranking = RoleSpecificRanking(
            role="middle",
            player_puuid="player1",
            player_name="Alice",
            role_player_pool=["player1", "player2", "player3"],
            rankings={"win_rate": 1, "avg_kda": 2},
            percentiles={"win_rate": 100.0, "avg_kda": 66.7},
            role_averages={"win_rate": 0.55, "avg_kda": 2.2},
            performance_vs_role={
                "win_rate": PerformanceDelta("win_rate", 0.55, 0.75),
                "avg_kda": PerformanceDelta("avg_kda", 2.2, 2.8)
            },
            top_performers={"win_rate": ["player1"], "avg_kda": ["player3", "player1"]},
            total_role_players=3
        )
        
        assert ranking.role == "middle"
        assert ranking.player_puuid == "player1"
        assert ranking.total_role_players == 3
        assert len(ranking.role_player_pool) == 3


class TestChampionSpecificRanking:
    """Test suite for ChampionSpecificRanking dataclass."""
    
    def test_champion_specific_ranking_creation(self):
        """Test ChampionSpecificRanking creation."""
        from lol_team_optimizer.analytics_models import PerformanceDelta
        
        ranking = ChampionSpecificRanking(
            champion_id=1,
            champion_name="Annie",
            player_puuid="player1",
            player_name="Alice",
            champion_player_pool=["player1", "player2", "player3"],
            rankings={"win_rate": 1, "avg_kda": 1},
            percentiles={"win_rate": 100.0, "avg_kda": 100.0},
            champion_averages={"win_rate": 0.50, "avg_kda": 2.0},
            performance_vs_champion={
                "win_rate": PerformanceDelta("win_rate", 0.50, 0.80),
                "avg_kda": PerformanceDelta("avg_kda", 2.0, 3.5)
            },
            mastery_level="expert",
            total_champion_players=3
        )
        
        assert ranking.champion_id == 1
        assert ranking.champion_name == "Annie"
        assert ranking.mastery_level == "expert"
        assert ranking.total_champion_players == 3


if __name__ == "__main__":
    pytest.main([__file__])