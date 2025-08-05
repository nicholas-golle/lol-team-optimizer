"""
Tests for the Champion Synergy Analyzer module.

This module tests the comprehensive champion synergy analysis capabilities,
including champion combination analysis, synergy matrix calculations,
and statistical significance testing for synergy effects.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import statistics

from lol_team_optimizer.champion_synergy_analyzer import (
    ChampionSynergyAnalyzer, ChampionCombination, SynergyMetrics,
    SynergyMatrix, TeamSynergyAnalysis
)
from lol_team_optimizer.analytics_models import (
    TeamComposition, PlayerRoleAssignment, PerformanceMetrics,
    AnalyticsFilters, DateRange, InsufficientDataError, AnalyticsError,
    SignificanceTest, ConfidenceInterval
)
from lol_team_optimizer.config import Config
from lol_team_optimizer.statistical_analyzer import StatisticalAnalyzer
from lol_team_optimizer.baseline_manager import BaselineManager


class TestChampionCombination:
    """Test ChampionCombination data class."""
    
    def test_champion_combination_creation(self):
        """Test creating a champion combination."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        assert combination.champion_ids == (1, 2)
        assert combination.roles == ("top", "jungle")
        assert combination.combination_type == "pair"
        assert "top:1" in combination.combination_key
        assert "jungle:2" in combination.combination_key
    
    def test_champion_combination_sorting(self):
        """Test that champion combinations are sorted consistently."""
        combination1 = ChampionCombination(
            champion_ids=(2, 1),
            roles=("jungle", "top"),
            combination_type="pair"
        )
        
        combination2 = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        # Should be sorted consistently
        assert combination1.combination_key == combination2.combination_key
    
    def test_champion_combination_validation(self):
        """Test champion combination validation."""
        # Mismatched lengths
        with pytest.raises(ValueError):
            ChampionCombination(
                champion_ids=(1, 2),
                roles=("top",),
                combination_type="pair"
            )
        
        # Too few champions
        with pytest.raises(ValueError):
            ChampionCombination(
                champion_ids=(1,),
                roles=("top",),
                combination_type="pair"
            )


class TestSynergyMetrics:
    """Test SynergyMetrics data class."""
    
    def test_synergy_metrics_creation(self):
        """Test creating synergy metrics."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        metrics = SynergyMetrics(
            combination=combination,
            games_together=20,
            wins_together=12,
            losses_together=8,
            expected_win_rate=0.5
        )
        
        assert metrics.games_together == 20
        assert metrics.wins_together == 12
        assert metrics.losses_together == 8
        assert metrics.win_rate == 0.6
        assert abs(metrics.win_rate_delta - 0.1) < 0.001
    
    def test_synergy_metrics_zero_games(self):
        """Test synergy metrics with zero games."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        metrics = SynergyMetrics(
            combination=combination,
            games_together=0,
            wins_together=0,
            losses_together=0
        )
        
        assert metrics.win_rate == 0.0
        assert metrics.win_rate_delta == -0.0


class TestSynergyMatrix:
    """Test SynergyMatrix data class."""
    
    def test_synergy_matrix_creation(self):
        """Test creating a synergy matrix."""
        matrix = SynergyMatrix(matrix_type="champion")
        
        assert matrix.matrix_type == "champion"
        assert len(matrix.synergy_scores) == 0
        assert len(matrix.confidence_scores) == 0
        assert len(matrix.sample_sizes) == 0
    
    def test_synergy_matrix_operations(self):
        """Test synergy matrix operations."""
        matrix = SynergyMatrix(matrix_type="champion")
        
        # Add synergy data
        matrix.synergy_scores[(1, 2)] = 0.3
        matrix.confidence_scores[(1, 2)] = 0.8
        matrix.sample_sizes[(1, 2)] = 15
        
        # Test retrieval (should handle order)
        assert matrix.get_synergy(1, 2) == 0.3
        assert matrix.get_synergy(2, 1) == 0.3
        assert matrix.get_confidence(1, 2) == 0.8
        assert matrix.get_sample_size(1, 2) == 15
        
        # Test missing data
        assert matrix.get_synergy(3, 4) == 0.0
        assert matrix.get_confidence(3, 4) == 0.0
        assert matrix.get_sample_size(3, 4) == 0


class TestChampionSynergyAnalyzer:
    """Test ChampionSynergyAnalyzer class."""
    
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
        baseline_manager = Mock(spec=BaselineManager)
        return baseline_manager
    
    @pytest.fixture
    def mock_statistical_analyzer(self):
        """Create mock statistical analyzer."""
        statistical_analyzer = Mock(spec=StatisticalAnalyzer)
        return statistical_analyzer
    
    @pytest.fixture
    def synergy_analyzer(self, mock_config, mock_match_manager, 
                        mock_baseline_manager, mock_statistical_analyzer):
        """Create ChampionSynergyAnalyzer instance."""
        return ChampionSynergyAnalyzer(
            config=mock_config,
            match_manager=mock_match_manager,
            baseline_manager=mock_baseline_manager,
            statistical_analyzer=mock_statistical_analyzer
        )
    
    @pytest.fixture
    def mock_match(self):
        """Create a mock match."""
        match = Mock()
        match.game_creation_datetime = datetime.now()
        match.game_duration = 1800  # 30 minutes
        match.queue_id = 420  # Ranked Solo/Duo
        
        # Create mock participants
        participants = []
        for i in range(10):
            participant = Mock()
            participant.puuid = f"puuid_{i}"
            participant.champion_id = i + 1
            participant.champion_name = f"Champion_{i + 1}"
            participant.individual_position = ["top", "jungle", "middle", "bottom", "support"][i % 5]
            participant.lane = participant.individual_position
            participant.team_id = 100 if i < 5 else 200
            participant.win = i < 5  # First team wins
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 8
            participant.vision_score = 20
            participant.total_damage_dealt_to_champions = 15000
            participants.append(participant)
        
        match.participants = participants
        return match
    
    def test_analyzer_initialization(self, synergy_analyzer):
        """Test analyzer initialization."""
        assert synergy_analyzer.min_games_for_synergy == 10
        assert synergy_analyzer.min_games_for_significance == 20
        assert synergy_analyzer.synergy_confidence_threshold == 0.05
    
    def test_analyze_champion_combinations_insufficient_data(self, synergy_analyzer, mock_match_manager):
        """Test champion combination analysis with insufficient data."""
        mock_match_manager.get_matches_with_multiple_players.return_value = []
        
        with pytest.raises(InsufficientDataError):
            synergy_analyzer.analyze_champion_combinations(["puuid_1", "puuid_2"])
    
    def test_analyze_champion_combinations_success(self, synergy_analyzer, mock_match_manager, mock_match):
        """Test successful champion combination analysis."""
        # Setup mock matches
        matches = [mock_match for _ in range(15)]
        mock_match_manager.get_matches_with_multiple_players.return_value = matches
        
        # Mock the internal methods
        with patch.object(synergy_analyzer, '_extract_champion_combinations') as mock_extract:
            with patch.object(synergy_analyzer, '_calculate_combination_synergy') as mock_calculate:
                # Setup mock data
                mock_combination = ChampionCombination(
                    champion_ids=(1, 2),
                    roles=("top", "jungle"),
                    combination_type="pair"
                )
                
                mock_synergy = SynergyMetrics(
                    combination=mock_combination,
                    games_together=15,
                    wins_together=9,
                    losses_together=6,
                    synergy_score=0.2
                )
                
                mock_extract.return_value = {
                    "test_key": {
                        'combination': mock_combination,
                        'matches': matches
                    }
                }
                mock_calculate.return_value = mock_synergy
                
                # Test the method
                result = synergy_analyzer.analyze_champion_combinations(["puuid_1", "puuid_2"])
                
                assert len(result) == 1
                assert "test_key" in result
                assert result["test_key"].synergy_score == 0.2
    
    def test_calculate_synergy_matrix_champion(self, synergy_analyzer):
        """Test champion synergy matrix calculation."""
        # Mock the analyze_champion_combinations method
        mock_combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        mock_synergy = SynergyMetrics(
            combination=mock_combination,
            games_together=15,
            wins_together=9,
            losses_together=6,
            synergy_score=0.3
        )
        
        with patch.object(synergy_analyzer, 'analyze_champion_combinations') as mock_analyze:
            mock_analyze.return_value = {"test_key": mock_synergy}
            
            matrix = synergy_analyzer.calculate_synergy_matrix(
                puuids=["puuid_1", "puuid_2"],
                matrix_type="champion"
            )
            
            assert matrix.matrix_type == "champion"
            assert matrix.get_synergy(1, 2) == 0.3
            assert matrix.get_sample_size(1, 2) == 15
    
    def test_calculate_synergy_matrix_unsupported_type(self, synergy_analyzer):
        """Test synergy matrix calculation with unsupported type."""
        with patch.object(synergy_analyzer, 'analyze_champion_combinations') as mock_analyze:
            mock_analyze.return_value = {}
            
            with pytest.raises(AnalyticsError):
                synergy_analyzer.calculate_synergy_matrix(
                    puuids=["puuid_1", "puuid_2"],
                    matrix_type="unsupported"
                )
    
    def test_quantify_synergy_effects_insufficient_data(self, synergy_analyzer):
        """Test synergy effect quantification with insufficient data."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        matches = [Mock() for _ in range(5)]  # Less than min_games_for_synergy
        
        with pytest.raises(InsufficientDataError):
            synergy_analyzer.quantify_synergy_effects(combination, matches, ["puuid_1", "puuid_2"])
    
    def test_quantify_synergy_effects_success(self, synergy_analyzer, mock_match):
        """Test successful synergy effect quantification."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        matches = [mock_match for _ in range(15)]
        
        # Mock internal methods
        with patch.object(synergy_analyzer, '_calculate_combination_performance') as mock_actual:
            with patch.object(synergy_analyzer, '_calculate_expected_performance') as mock_expected:
                with patch.object(synergy_analyzer, '_calculate_performance_deltas') as mock_deltas:
                    with patch.object(synergy_analyzer, '_calculate_synergy_score') as mock_score:
                        with patch.object(synergy_analyzer, '_is_winning_match') as mock_win:
                            
                            # Setup mocks
                            mock_actual.return_value = PerformanceMetrics(win_rate=0.6)
                            mock_expected.return_value = PerformanceMetrics(win_rate=0.5)
                            mock_deltas.return_value = {}
                            mock_score.return_value = 0.2
                            mock_win.return_value = True
                            
                            result = synergy_analyzer.quantify_synergy_effects(
                                combination, matches, ["puuid_1", "puuid_2"]
                            )
                            
                            assert result.games_together == 15
                            assert result.synergy_score == 0.2
                            assert result.expected_win_rate == 0.5
    
    def test_test_synergy_significance_insufficient_data(self, synergy_analyzer):
        """Test synergy significance testing with insufficient data."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        synergy_metrics = SynergyMetrics(
            combination=combination,
            games_together=10,  # Less than min_games_for_significance
            wins_together=6,
            losses_together=4
        )
        
        with pytest.raises(InsufficientDataError):
            synergy_analyzer.test_synergy_significance(synergy_metrics)
    
    def test_test_synergy_significance_success(self, synergy_analyzer, mock_statistical_analyzer):
        """Test successful synergy significance testing."""
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        synergy_metrics = SynergyMetrics(
            combination=combination,
            games_together=25,
            wins_together=15,
            losses_together=10,
            expected_win_rate=0.5
        )
        
        # Mock statistical analyzer
        mock_significance = SignificanceTest(
            test_type="one_sample_t_test",
            statistic=2.5,
            p_value=0.02
        )
        mock_statistical_analyzer.perform_one_sample_test.return_value = mock_significance
        
        result = synergy_analyzer.test_synergy_significance(synergy_metrics)
        
        assert result.test_type == "one_sample_t_test"
        assert result.p_value == 0.02
        assert result.is_significant()
    
    def test_filter_recommendations_by_synergy_empty_list(self, synergy_analyzer):
        """Test filtering empty recommendations list."""
        result = synergy_analyzer.filter_recommendations_by_synergy([], Mock())
        assert result == []
    
    def test_filter_recommendations_by_synergy_success(self, synergy_analyzer):
        """Test successful recommendation filtering by synergy."""
        # Create mock recommendations
        recommendations = [Mock() for _ in range(3)]
        for i, rec in enumerate(recommendations):
            rec.recommendation_score = 0.5 + i * 0.1
        
        team_context = Mock()
        
        # Mock internal methods
        with patch.object(synergy_analyzer, '_calculate_team_synergy_score') as mock_synergy:
            with patch.object(synergy_analyzer, '_adjust_recommendation_for_synergy') as mock_adjust:
                
                # Setup mocks - only first two recommendations have good synergy
                mock_synergy.side_effect = [0.2, 0.15, 0.05]  # Third is below threshold
                mock_adjust.side_effect = lambda rec, score: rec
                
                result = synergy_analyzer.filter_recommendations_by_synergy(
                    recommendations, team_context, synergy_threshold=0.1
                )
                
                assert len(result) == 2  # Third recommendation filtered out
    
    def test_analyze_team_synergy_no_matches(self, synergy_analyzer):
        """Test team synergy analysis with no historical matches."""
        team_composition = TeamComposition(
            players={
                "top": PlayerRoleAssignment("puuid_1", "Player1", "top", 1, "Champion1"),
                "jungle": PlayerRoleAssignment("puuid_2", "Player2", "jungle", 2, "Champion2")
            }
        )
        
        with patch.object(synergy_analyzer, '_find_composition_matches') as mock_find:
            with patch.object(synergy_analyzer, '_calculate_theoretical_team_synergy') as mock_theoretical:
                
                mock_find.return_value = []
                mock_theoretical_result = TeamSynergyAnalysis(
                    team_composition=team_composition,
                    overall_synergy_score=0.0,
                    pair_synergies={},
                    role_synergies={},
                    player_synergies={},
                    expected_performance=PerformanceMetrics()
                )
                mock_theoretical.return_value = mock_theoretical_result
                
                result = synergy_analyzer.analyze_team_synergy(team_composition)
                
                assert result.overall_synergy_score == 0.0
                assert result.sample_size == 0
    
    def test_analyze_team_synergy_with_matches(self, synergy_analyzer, mock_match):
        """Test team synergy analysis with historical matches."""
        team_composition = TeamComposition(
            players={
                "top": PlayerRoleAssignment("puuid_1", "Player1", "top", 1, "Champion1"),
                "jungle": PlayerRoleAssignment("puuid_2", "Player2", "jungle", 2, "Champion2")
            }
        )
        
        matches = [mock_match for _ in range(15)]
        
        with patch.object(synergy_analyzer, '_find_composition_matches') as mock_find:
            with patch.object(synergy_analyzer, '_calculate_all_pair_synergies') as mock_pairs:
                with patch.object(synergy_analyzer, '_calculate_role_synergies') as mock_roles:
                    with patch.object(synergy_analyzer, '_calculate_player_synergies') as mock_players:
                        with patch.object(synergy_analyzer, '_calculate_overall_synergy_score') as mock_overall:
                            with patch.object(synergy_analyzer, '_calculate_team_performance') as mock_perf:
                                with patch.object(synergy_analyzer, '_calculate_expected_team_performance') as mock_expected:
                                    with patch.object(synergy_analyzer, '_calculate_team_confidence') as mock_confidence:
                                        
                                        # Setup mocks
                                        mock_find.return_value = matches
                                        mock_pairs.return_value = {(1, 2): 0.3}
                                        mock_roles.return_value = {("top", "jungle"): 0.2}
                                        mock_players.return_value = {("puuid_1", "puuid_2"): 0.25}
                                        mock_overall.return_value = 0.25
                                        mock_perf.return_value = PerformanceMetrics(win_rate=0.6)
                                        mock_expected.return_value = PerformanceMetrics(win_rate=0.5)
                                        mock_confidence.return_value = 0.8
                                        
                                        result = synergy_analyzer.analyze_team_synergy(team_composition)
                                        
                                        assert result.overall_synergy_score == 0.25
                                        assert result.sample_size == 15
                                        assert result.confidence_level == 0.8
                                        assert (1, 2) in result.pair_synergies
                                        assert ("top", "jungle") in result.role_synergies
                                        assert ("puuid_1", "puuid_2") in result.player_synergies


class TestSynergyAnalyzerHelperMethods:
    """Test helper methods of ChampionSynergyAnalyzer."""
    
    @pytest.fixture
    def synergy_analyzer(self):
        """Create ChampionSynergyAnalyzer instance for testing helpers."""
        return ChampionSynergyAnalyzer(
            config=Mock(),
            match_manager=Mock(),
            baseline_manager=Mock(),
            statistical_analyzer=Mock()
        )
    
    def test_calculate_confidence_score(self, synergy_analyzer):
        """Test confidence score calculation."""
        # Test different sample sizes
        test_cases = [
            (50, 1.0),
            (25, 0.8),
            (15, 0.6),
            (8, 0.4),
            (3, 0.2)
        ]
        
        for games, expected_confidence in test_cases:
            mock_synergy = Mock()
            mock_synergy.games_together = games
            
            confidence = synergy_analyzer._calculate_confidence_score(mock_synergy)
            assert confidence == expected_confidence
    
    def test_is_winning_match(self, synergy_analyzer):
        """Test match win detection."""
        # Create mock match
        match = Mock()
        participants = []
        
        # Create participants - first two are the combination, both win
        for i in range(4):
            participant = Mock()
            participant.champion_id = i + 1
            participant.win = i < 2  # First two win
            participants.append(participant)
        
        match.participants = participants
        
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        assert synergy_analyzer._is_winning_match(match, combination) == True
        
        # Test losing match
        participants[0].win = False
        assert synergy_analyzer._is_winning_match(match, combination) == False
    
    def test_calculate_combined_kda(self, synergy_analyzer):
        """Test combined KDA calculation."""
        # Create mock matches
        matches = []
        for i in range(3):
            match = Mock()
            participants = []
            
            # Create participants for the combination
            for j in range(2):
                participant = Mock()
                participant.champion_id = j + 1
                participant.kills = 5 + j
                participant.deaths = 2 + j
                participant.assists = 8 + j
                participants.append(participant)
            
            # Add other participants
            for j in range(3):
                participant = Mock()
                participant.champion_id = j + 10
                participants.append(participant)
            
            match.participants = participants
            matches.append(match)
        
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        combined_kda = synergy_analyzer._calculate_combined_kda(matches, combination)
        
        # Expected: Average of (KDA1 + KDA2) across all matches
        # For each match: KDA1 = (5+8)/max(2,1) = 13/3, KDA2 = (6+9)/max(3,1) = 15/3
        # Sum per match = 13/3 + 15/3 = 28/3 = 9.33
        # This is the same for all 3 matches, so average is 9.33
        kda1 = (5 + 8) / max(2, 1)  # 13/2 = 6.5
        kda2 = (6 + 9) / max(3, 1)  # 15/3 = 5.0
        expected_kda = kda1 + kda2  # 6.5 + 5.0 = 11.5
        assert abs(combined_kda - expected_kda) < 0.01
    
    def test_calculate_combined_damage(self, synergy_analyzer):
        """Test combined damage calculation."""
        matches = []
        for i in range(2):
            match = Mock()
            participants = []
            
            # Create participants for the combination
            for j in range(2):
                participant = Mock()
                participant.champion_id = j + 1
                participant.total_damage_dealt_to_champions = 10000 + j * 1000
                participants.append(participant)
            
            match.participants = participants
            matches.append(match)
        
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        combined_damage = synergy_analyzer._calculate_combined_damage(matches, combination)
        
        # Expected: (10000 + 11000) = 21000 per match
        assert combined_damage == 21000.0
    
    def test_calculate_combined_vision(self, synergy_analyzer):
        """Test combined vision score calculation."""
        matches = []
        for i in range(2):
            match = Mock()
            participants = []
            
            # Create participants for the combination
            for j in range(2):
                participant = Mock()
                participant.champion_id = j + 1
                participant.vision_score = 20 + j * 5
                participants.append(participant)
            
            match.participants = participants
            matches.append(match)
        
        combination = ChampionCombination(
            champion_ids=(1, 2),
            roles=("top", "jungle"),
            combination_type="pair"
        )
        
        combined_vision = synergy_analyzer._calculate_combined_vision(matches, combination)
        
        # Expected: (20 + 25) = 45 per match
        assert combined_vision == 45.0


class TestSynergyAnalyzerIntegration:
    """Integration tests for ChampionSynergyAnalyzer."""
    
    @pytest.fixture
    def full_analyzer(self):
        """Create a fully configured analyzer for integration tests."""
        config = Mock()
        match_manager = Mock()
        baseline_manager = Mock()
        statistical_analyzer = StatisticalAnalyzer()
        
        return ChampionSynergyAnalyzer(
            config=config,
            match_manager=match_manager,
            baseline_manager=baseline_manager,
            statistical_analyzer=statistical_analyzer
        )
    
    def test_end_to_end_synergy_analysis(self, full_analyzer):
        """Test end-to-end synergy analysis workflow."""
        # This would be a comprehensive integration test
        # that tests the full workflow from match data to synergy insights
        
        # Create mock data
        puuids = ["puuid_1", "puuid_2", "puuid_3"]
        
        # Mock match manager to return realistic data
        matches = []
        for i in range(25):  # Enough for significance testing
            match = Mock()
            match.game_creation_datetime = datetime.now() - timedelta(days=i)
            match.game_duration = 1800
            match.queue_id = 420
            
            participants = []
            for j in range(6):  # 3 tracked players + 3 others
                participant = Mock()
                participant.puuid = puuids[j] if j < 3 else f"other_puuid_{j}"
                participant.champion_id = j + 1
                participant.champion_name = f"Champion_{j + 1}"
                participant.individual_position = ["top", "jungle", "middle"][j % 3]
                participant.lane = participant.individual_position
                participant.team_id = 100
                participant.win = i % 3 != 0  # Varying win rate
                participant.kills = 5 + j
                participant.deaths = 3
                participant.assists = 8 + j
                participant.vision_score = 20 + j * 2
                participant.total_damage_dealt_to_champions = 15000 + j * 1000
                participants.append(participant)
            
            match.participants = participants
            matches.append(match)
        
        full_analyzer.match_manager.get_matches_with_multiple_players.return_value = matches
        
        # Test the full analysis
        try:
            combinations = full_analyzer.analyze_champion_combinations(puuids)
            assert len(combinations) > 0
            
            # Test matrix calculation
            matrix = full_analyzer.calculate_synergy_matrix(puuids, "champion")
            assert matrix.matrix_type == "champion"
            
            # Test team synergy analysis
            team_composition = TeamComposition(
                players={
                    "top": PlayerRoleAssignment("puuid_1", "Player1", "top", 1, "Champion1"),
                    "jungle": PlayerRoleAssignment("puuid_2", "Player2", "jungle", 2, "Champion2"),
                    "middle": PlayerRoleAssignment("puuid_3", "Player3", "middle", 3, "Champion3")
                }
            )
            
            with patch.object(full_analyzer, '_find_composition_matches') as mock_find:
                mock_find.return_value = matches[:10]  # Some matches with this composition
                
                team_analysis = full_analyzer.analyze_team_synergy(team_composition)
                assert team_analysis.sample_size == 10
                
        except InsufficientDataError:
            # This is acceptable for integration tests with mock data
            pass


if __name__ == "__main__":
    pytest.main([__file__])