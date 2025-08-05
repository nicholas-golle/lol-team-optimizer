"""
Tests for TeamCompositionAnalyzer.

This module tests the team composition analysis functionality including
composition matching, performance calculation, synergy analysis, and
optimization recommendations.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import statistics

from lol_team_optimizer.team_composition_analyzer import (
    TeamCompositionAnalyzer, CompositionSimilarity, OptimalComposition,
    CompositionConstraints, CompositionCache
)
from lol_team_optimizer.analytics_models import (
    TeamComposition, PlayerRoleAssignment, CompositionPerformance,
    PerformanceMetrics, PerformanceDelta, SynergyEffects, SignificanceTest,
    ConfidenceInterval, InsufficientDataError, StatisticalAnalysisError,
    DataValidationError
)
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestCompositionCache:
    """Test composition cache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = CompositionCache()
        
        assert isinstance(cache.performance_cache, dict)
        assert isinstance(cache.similarity_cache, dict)
        assert isinstance(cache.synergy_cache, dict)
        assert isinstance(cache.cache_timestamps, dict)
        assert cache.max_cache_age_hours == 24
    
    def test_performance_caching(self):
        """Test performance caching and retrieval."""
        cache = CompositionCache()
        
        # Create mock composition performance
        composition = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1")
        })
        performance = CompositionPerformance(
            composition=composition,
            total_games=10,
            performance=PerformanceMetrics(games_played=10, wins=6, win_rate=0.6)
        )
        
        # Test caching
        cache.cache_performance("test_comp", performance)
        assert "test_comp" in cache.performance_cache
        assert "test_comp" in cache.cache_timestamps
        
        # Test retrieval
        cached_performance = cache.get_performance("test_comp")
        assert cached_performance == performance
        
        # Test non-existent key
        assert cache.get_performance("non_existent") is None
    
    def test_similarity_caching(self):
        """Test similarity caching and retrieval."""
        cache = CompositionCache()
        
        # Test caching
        cache.cache_similarity("comp1", "comp2", 0.8)
        
        # Test retrieval (order should not matter)
        assert cache.get_similarity("comp1", "comp2") == 0.8
        assert cache.get_similarity("comp2", "comp1") == 0.8
        
        # Test non-existent pair
        assert cache.get_similarity("comp1", "comp3") is None
    
    def test_cache_staleness(self):
        """Test cache staleness detection."""
        cache = CompositionCache()
        cache.max_cache_age_hours = 0.001  # Very short for testing
        
        # Cache performance
        composition = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1")
        })
        performance = CompositionPerformance(
            composition=composition,
            total_games=10,
            performance=PerformanceMetrics(games_played=10, wins=6, win_rate=0.6)
        )
        
        cache.cache_performance("test_comp", performance)
        
        # Should be available immediately
        assert cache.get_performance("test_comp") is not None
        
        # Mock time passage
        with patch('lol_team_optimizer.team_composition_analyzer.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(hours=1)
            
            # Should be stale now
            assert cache.get_performance("test_comp") is None


class TestCompositionConstraints:
    """Test composition constraints validation."""
    
    def test_valid_constraints(self):
        """Test valid constraint creation."""
        constraints = CompositionConstraints(
            required_players={"top": "puuid1"},
            available_champions={"puuid1": [1, 2, 3]},
            banned_champions=[4, 5],
            min_synergy_score=0.5,
            max_risk_tolerance=0.8
        )
        
        assert constraints.required_players == {"top": "puuid1"}
        assert constraints.available_champions == {"puuid1": [1, 2, 3]}
        assert constraints.banned_champions == [4, 5]
        assert constraints.min_synergy_score == 0.5
        assert constraints.max_risk_tolerance == 0.8
    
    def test_invalid_synergy_score(self):
        """Test invalid synergy score validation."""
        with pytest.raises(DataValidationError, match="Min synergy score must be between -1 and 1"):
            CompositionConstraints(min_synergy_score=2.0)
        
        with pytest.raises(DataValidationError, match="Min synergy score must be between -1 and 1"):
            CompositionConstraints(min_synergy_score=-2.0)
    
    def test_invalid_risk_tolerance(self):
        """Test invalid risk tolerance validation."""
        with pytest.raises(DataValidationError, match="Max risk tolerance must be between 0 and 1"):
            CompositionConstraints(max_risk_tolerance=2.0)
        
        with pytest.raises(DataValidationError, match="Max risk tolerance must be between 0 and 1"):
            CompositionConstraints(max_risk_tolerance=-0.5)


class TestTeamCompositionAnalyzer:
    """Test team composition analyzer functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.data_directory = "/tmp/test_data"
        config.cache_directory = "/tmp/test_cache"
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        return Mock()
    
    @pytest.fixture
    def mock_baseline_manager(self):
        """Create mock baseline manager."""
        return Mock()
    
    @pytest.fixture
    def analyzer(self, mock_match_manager, mock_baseline_manager, mock_config):
        """Create team composition analyzer instance."""
        return TeamCompositionAnalyzer(mock_match_manager, mock_baseline_manager, mock_config)
    
    @pytest.fixture
    def sample_composition(self):
        """Create sample team composition."""
        players = {
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Champion2"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        }
        return TeamComposition(players=players)
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample matches for testing."""
        matches = []
        
        for i in range(5):
            # Create match
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            match.game_duration = 1800  # 30 minutes
            match.game_creation_datetime = datetime.now() - timedelta(days=i)
            
            # Create participants
            participants = {}
            team_won = i % 2 == 0  # Alternate wins/losses
            
            for j, (role, puuid) in enumerate([("top", "puuid1"), ("jungle", "puuid2"), 
                                             ("middle", "puuid3"), ("bottom", "puuid4"), 
                                             ("support", "puuid5")]):
                participant = Mock(spec=MatchParticipant)
                participant.puuid = puuid
                participant.champion_id = j + 1
                participant.champion_name = f"Champion{j + 1}"
                participant.individual_position = role
                participant.team_id = 100
                participant.win = team_won
                participant.kills = 5 + j
                participant.deaths = 3
                participant.assists = 8 + j
                participant.cs_total = 150 + j * 10
                participant.vision_score = 20 + j * 2
                participant.total_damage_dealt_to_champions = 15000 + j * 1000
                participant.gold_earned = 12000 + j * 500
                participant.summoner_name = f"Player{j + 1}"
                
                participants[puuid] = participant
            
            matches.append((match, participants))
        
        return matches
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.match_manager is not None
        assert analyzer.baseline_manager is not None
        assert analyzer.config is not None
        assert analyzer.statistical_analyzer is not None
        assert analyzer.composition_cache is not None
        assert analyzer.min_games_for_analysis == 3
        assert analyzer.similarity_threshold == 0.7
        assert analyzer.confidence_level == 0.95
    
    def test_analyze_composition_performance_success(self, analyzer, sample_composition, sample_matches):
        """Test successful composition performance analysis."""
        # Mock finding matches
        analyzer._find_composition_matches = Mock(return_value=sample_matches)
        
        # Mock baseline calculations
        mock_baseline = Mock()
        mock_baseline.baseline_metrics = PerformanceMetrics(
            games_played=10, wins=5, win_rate=0.5, avg_kda=2.0
        )
        analyzer.baseline_manager.get_champion_specific_baseline = Mock(return_value=mock_baseline)
        analyzer.baseline_manager.calculate_performance_delta = Mock(return_value={
            "win_rate": PerformanceDelta("win_rate", 0.5, 0.6, 0.1, 20.0)
        })
        
        # Mock player synergy calculations for synergy effects
        analyzer._calculate_player_synergy = Mock(return_value=0.2)
        analyzer._calculate_champion_synergy = Mock(return_value=0.1)
        
        # Mock statistical analysis
        mock_significance = SignificanceTest("t_test", 2.5, 0.02)
        analyzer.statistical_analyzer.perform_one_sample_test = Mock(return_value=mock_significance)
        analyzer.statistical_analyzer.calculate_confidence_interval = Mock(
            return_value=ConfidenceInterval(0.4, 0.8, 0.95, 5)
        )
        
        # Analyze composition
        result = analyzer.analyze_composition_performance(sample_composition)
        
        # Verify result
        assert isinstance(result, CompositionPerformance)
        assert result.composition == sample_composition
        assert result.total_games == 5
        assert result.performance.games_played == 5
        assert result.performance.win_rate == 0.6  # 3 wins out of 5
        assert result.statistical_significance == mock_significance
    
    def test_analyze_composition_performance_insufficient_data(self, analyzer, sample_composition):
        """Test composition analysis with insufficient data."""
        # Mock finding no matches
        analyzer._find_composition_matches = Mock(return_value=[])
        
        # Should raise InsufficientDataError
        with pytest.raises(InsufficientDataError):
            analyzer.analyze_composition_performance(sample_composition)
    
    def test_analyze_composition_performance_cached(self, analyzer, sample_composition):
        """Test composition analysis with cached result."""
        # Create cached performance
        cached_performance = CompositionPerformance(
            composition=sample_composition,
            total_games=10,
            performance=PerformanceMetrics(games_played=10, wins=7, win_rate=0.7)
        )
        
        # Mock cache to return cached result
        analyzer.composition_cache.get_performance = Mock(return_value=cached_performance)
        
        # Analyze composition
        result = analyzer.analyze_composition_performance(sample_composition)
        
        # Should return cached result
        assert result == cached_performance
        
        # Should not call _find_composition_matches
        analyzer._find_composition_matches = Mock()
        analyzer._find_composition_matches.assert_not_called()
    
    def test_find_similar_compositions(self, analyzer, sample_composition):
        """Test finding similar compositions."""
        # Create similar compositions
        similar_comp1 = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),
            "jungle": PlayerRoleAssignment("puuid6", "Player6", "jungle", 6, "Champion6"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        })
        
        similar_comp2 = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid7", "Player7", "top", 7, "Champion7"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Champion2"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        })
        
        # Mock getting all compositions
        analyzer._get_all_historical_compositions = Mock(return_value=[similar_comp1, similar_comp2])
        
        # Mock similarity calculations
        analyzer._calculate_composition_similarity = Mock(side_effect=[0.8, 0.6])
        
        # Mock finding matches
        analyzer._find_composition_matches = Mock(return_value=[Mock(), Mock(), Mock()])
        
        # Mock matching elements
        analyzer._identify_matching_elements = Mock(return_value={"matching_players": []})
        
        # Find similar compositions
        result = analyzer.find_similar_compositions(sample_composition, similarity_threshold=0.5)
        
        # Verify results
        assert len(result) == 2
        assert all(isinstance(sim, CompositionSimilarity) for sim in result)
        assert result[0].similarity_score == 0.8  # Should be sorted by similarity
        assert result[1].similarity_score == 0.6
        assert all(sim.total_matches == 3 for sim in result)
    
    def test_calculate_synergy_matrix(self, analyzer):
        """Test synergy matrix calculation."""
        player_puuids = ["puuid1", "puuid2", "puuid3"]
        
        # Mock player synergy calculations
        analyzer._calculate_player_synergy = Mock(side_effect=[0.3, 0.5, 0.2])
        
        # Mock cache misses
        analyzer.composition_cache.get_similarity = Mock(return_value=None)
        analyzer.composition_cache.cache_similarity = Mock()
        
        # Calculate synergy matrix
        result = analyzer.calculate_synergy_matrix(player_puuids)
        
        # Verify results
        expected_pairs = [("puuid1", "puuid2"), ("puuid1", "puuid3"), ("puuid2", "puuid3")]
        assert len(result) == 3
        assert all(pair in result for pair in expected_pairs)
        assert result[("puuid1", "puuid2")] == 0.3
        assert result[("puuid1", "puuid3")] == 0.5
        assert result[("puuid2", "puuid3")] == 0.2
    
    def test_identify_optimal_compositions_insufficient_players(self, analyzer):
        """Test optimal composition identification with insufficient players."""
        player_pool = ["puuid1", "puuid2", "puuid3"]  # Only 3 players
        constraints = CompositionConstraints()
        
        # Should raise DataValidationError
        with pytest.raises(DataValidationError, match="Player pool must have at least 5 players"):
            analyzer.identify_optimal_compositions(player_pool, constraints)
    
    def test_identify_optimal_compositions_success(self, analyzer, sample_matches):
        """Test successful optimal composition identification."""
        player_pool = ["puuid1", "puuid2", "puuid3", "puuid4", "puuid5", "puuid6"]
        constraints = CompositionConstraints(min_synergy_score=0.0)
        
        # Mock composition generation
        sample_comp = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Champion2"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        })
        
        analyzer._generate_possible_compositions = Mock(return_value=[sample_comp])
        
        # Mock historical analysis
        analyzer._find_composition_matches = Mock(return_value=sample_matches)
        analyzer.analyze_composition_performance = Mock(return_value=CompositionPerformance(
            composition=sample_comp,
            total_games=5,
            performance=PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            synergy_effects=SynergyEffects(overall_synergy=0.2)
        ))
        
        # Mock confidence calculation
        analyzer._calculate_historical_confidence = Mock(return_value=0.8)
        
        # Identify optimal compositions
        result = analyzer.identify_optimal_compositions(player_pool, constraints)
        
        # Verify results
        assert len(result) == 1
        assert isinstance(result[0], OptimalComposition)
        assert result[0].composition == sample_comp
        assert result[0].expected_performance.win_rate == 0.6
        assert result[0].confidence_score == 0.8
        assert result[0].synergy_score == 0.2
    
    def test_find_composition_matches(self, analyzer, sample_composition):
        """Test finding matches for a composition."""
        # Create mock matches
        matching_match = Mock(spec=Match)
        matching_match.match_id = "match1"
        matching_match.participants = []
        
        # Create participants for the matching match
        for i, (role, assignment) in enumerate(sample_composition.players.items()):
            participant = Mock(spec=MatchParticipant)
            participant.puuid = assignment.puuid
            participant.champion_id = assignment.champion_id
            participant.individual_position = role
            participant.champion_name = assignment.champion_name
            matching_match.participants.append(participant)
        
        # Mock match manager
        analyzer.match_manager.get_matches_for_player = Mock(return_value=[matching_match])
        
        # Mock role normalization
        analyzer._normalize_role = Mock(side_effect=lambda x: x)
        
        # Find matches
        result = analyzer._find_composition_matches(sample_composition)
        
        # Should find the matching match
        assert len(result) == 1
        assert result[0][0] == matching_match
    
    def test_calculate_composition_metrics(self, analyzer, sample_matches):
        """Test composition metrics calculation."""
        # Calculate metrics
        result = analyzer._calculate_composition_metrics(sample_matches)
        
        # Verify results
        assert isinstance(result, PerformanceMetrics)
        assert result.games_played == 5
        assert result.wins == 3  # Based on sample_matches fixture
        assert result.win_rate == 0.6
        assert result.avg_kda > 0
        assert result.avg_cs_per_min > 0
    
    def test_calculate_baseline_deltas(self, analyzer, sample_composition, sample_matches):
        """Test baseline delta calculations."""
        # Mock baseline manager
        mock_baseline = Mock()
        mock_baseline.baseline_metrics = PerformanceMetrics(
            games_played=10, wins=5, win_rate=0.5, avg_kda=2.0
        )
        analyzer.baseline_manager.get_champion_specific_baseline = Mock(return_value=mock_baseline)
        analyzer.baseline_manager.calculate_performance_delta = Mock(return_value={
            "win_rate": PerformanceDelta("win_rate", 0.5, 0.6, 0.1, 20.0)
        })
        
        # Calculate deltas
        result = analyzer._calculate_baseline_deltas(sample_composition, sample_matches)
        
        # Verify results
        assert isinstance(result, dict)
        assert len(result) == 5  # One for each player
        for puuid in result:
            assert "win_rate" in result[puuid]
            assert isinstance(result[puuid]["win_rate"], PerformanceDelta)
    
    def test_calculate_synergy_effects(self, analyzer, sample_composition, sample_matches):
        """Test synergy effects calculation."""
        # Mock baseline deltas
        baseline_deltas = {
            "puuid1": {"win_rate": PerformanceDelta("win_rate", 0.5, 0.6, 0.1, 20.0)},
            "puuid2": {"win_rate": PerformanceDelta("win_rate", 0.5, 0.55, 0.05, 10.0)}
        }
        
        # Mock player synergy calculations
        analyzer._calculate_player_synergy = Mock(return_value=0.3)
        analyzer._calculate_champion_synergy = Mock(return_value=0.2)
        
        # Calculate synergy effects
        result = analyzer._calculate_synergy_effects(sample_composition, sample_matches, baseline_deltas)
        
        # Verify results
        assert isinstance(result, SynergyEffects)
        assert -1.0 <= result.overall_synergy <= 1.0
        assert len(result.role_pair_synergies) > 0
        assert len(result.champion_synergies) > 0
        assert len(result.player_synergies) > 0
    
    def test_calculate_composition_similarity(self, analyzer):
        """Test composition similarity calculation."""
        # Create two similar compositions
        comp1 = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Champion2"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        })
        
        comp2 = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),  # Same player, champion, role
            "jungle": PlayerRoleAssignment("puuid6", "Player6", "jungle", 2, "Champion2"),  # Same champion, different player
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 7, "Champion7"),  # Same player, different champion
            "bottom": PlayerRoleAssignment("puuid8", "Player8", "bottom", 8, "Champion8"),  # Different player and champion
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")  # Same player, champion, role
        })
        
        # Mock cache miss
        analyzer.composition_cache.get_similarity = Mock(return_value=None)
        analyzer.composition_cache.cache_similarity = Mock()
        
        # Calculate similarity
        result = analyzer._calculate_composition_similarity(comp1, comp2)
        
        # Verify result
        assert 0.0 <= result <= 1.0
        assert result > 0  # Should have some similarity
    
    def test_calculate_player_synergy(self, analyzer):
        """Test player synergy calculation."""
        puuid1, puuid2 = "puuid1", "puuid2"
        
        # Create mock matches where players played together
        common_matches = []
        for i in range(5):
            match = Mock(spec=Match)
            match.match_id = f"match_{i}"
            
            # Create participants
            p1 = Mock(spec=MatchParticipant)
            p1.puuid = puuid1
            p1.team_id = 100
            p1.win = i % 2 == 0  # Alternate wins
            
            p2 = Mock(spec=MatchParticipant)
            p2.puuid = puuid2
            p2.team_id = 100  # Same team
            p2.win = i % 2 == 0
            
            match.get_participant_by_puuid = Mock(side_effect=lambda puuid: p1 if puuid == puuid1 else p2)
            common_matches.append(match)
        
        # Mock match manager
        analyzer.match_manager.get_matches_for_player = Mock(side_effect=lambda puuid: common_matches)
        
        # Mock baseline manager
        mock_baseline = Mock()
        mock_baseline.baseline_metrics = PerformanceMetrics(win_rate=0.5)
        analyzer.baseline_manager.get_overall_baseline = Mock(return_value=mock_baseline)
        
        # Calculate synergy
        result = analyzer._calculate_player_synergy(puuid1, puuid2)
        
        # Verify result
        assert -1.0 <= result <= 1.0
    
    def test_normalize_role(self, analyzer):
        """Test role normalization."""
        # Test standard roles
        assert analyzer._normalize_role("top") == "top"
        assert analyzer._normalize_role("jungle") == "jungle"
        assert analyzer._normalize_role("middle") == "middle"
        assert analyzer._normalize_role("bottom") == "bottom"
        assert analyzer._normalize_role("support") == "support"
        
        # Test alternative names
        assert analyzer._normalize_role("mid") == "middle"
        assert analyzer._normalize_role("bot") == "bottom"
        assert analyzer._normalize_role("adc") == "bottom"
        assert analyzer._normalize_role("supp") == "support"
        
        # Test case insensitivity
        assert analyzer._normalize_role("TOP") == "top"
        assert analyzer._normalize_role("Middle") == "middle"
        
        # Test empty/invalid input
        assert analyzer._normalize_role("") == ""
        assert analyzer._normalize_role("invalid") == "invalid"
    
    def test_error_handling(self, analyzer, sample_composition):
        """Test error handling in various scenarios."""
        # Test with mock that raises exception
        analyzer._find_composition_matches = Mock(side_effect=Exception("Test error"))
        
        with pytest.raises(StatisticalAnalysisError, match="Failed to analyze composition performance"):
            analyzer.analyze_composition_performance(sample_composition)
    
    def test_performance_metrics_calculation_edge_cases(self, analyzer):
        """Test performance metrics calculation with edge cases."""
        # Test with empty matches
        result = analyzer._calculate_composition_metrics([])
        assert isinstance(result, PerformanceMetrics)
        assert result.games_played == 0
        
        # Test with single match
        match = Mock(spec=Match)
        match.game_duration = 1800
        participants = {
            "puuid1": Mock(spec=MatchParticipant, 
                          win=True, kills=5, deaths=2, assists=8, cs_total=150,
                          vision_score=25, total_damage_dealt_to_champions=15000,
                          gold_earned=12000)
        }
        
        result = analyzer._calculate_composition_metrics([(match, participants)])
        assert result.games_played == 1
        assert result.wins == 1
        assert result.win_rate == 1.0
    
    def test_generate_alternative_compositions(self, analyzer, sample_composition):
        """Test generation of alternative compositions."""
        player_pool = ["puuid1", "puuid2", "puuid3", "puuid4", "puuid5", "puuid6", "puuid7"]
        constraints = CompositionConstraints(min_synergy_score=0.0)
        
        # Mock the helper methods
        analyzer._generate_role_swap_alternatives = Mock(return_value=[])
        analyzer._generate_substitution_alternatives = Mock(return_value=[])
        analyzer._generate_champion_alternatives = Mock(return_value=[])
        analyzer._generate_synergy_optimized_alternatives = Mock(return_value=[])
        
        # Create a mock alternative
        alt_composition = OptimalComposition(
            composition=sample_composition,
            expected_performance=PerformanceMetrics(games_played=3, wins=2, win_rate=0.67),
            confidence_score=0.6,
            historical_sample_size=3,
            synergy_score=0.15,
            reasoning=["Alternative composition strategy"]
        )
        
        analyzer._generate_substitution_alternatives.return_value = [alt_composition]
        
        # Generate alternatives
        result = analyzer.generate_alternative_compositions(
            sample_composition, player_pool, constraints, max_alternatives=3
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) <= 3
        
        # Verify all helper methods were called
        analyzer._generate_role_swap_alternatives.assert_called_once()
        analyzer._generate_substitution_alternatives.assert_called_once()
        analyzer._generate_champion_alternatives.assert_called_once()
        analyzer._generate_synergy_optimized_alternatives.assert_called_once()
    
    def test_generate_composition_explanation(self, analyzer, sample_composition):
        """Test generation of detailed composition explanations."""
        optimal_comp = OptimalComposition(
            composition=sample_composition,
            expected_performance=PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            confidence_score=0.75,
            historical_sample_size=5,
            synergy_score=0.12,
            reasoning=["Strong historical performance"]
        )
        
        # Mock baseline manager
        mock_baseline = Mock()
        mock_baseline.baseline_metrics.win_rate = 0.55
        mock_baseline.baseline_metrics.avg_kda = 2.1
        analyzer.baseline_manager.get_champion_specific_baseline = Mock(return_value=mock_baseline)
        
        # Generate explanation
        result = analyzer.generate_composition_explanation(optimal_comp)
        
        # Verify explanation structure
        assert isinstance(result, dict)
        expected_keys = [
            "overall_assessment", "performance_analysis", "synergy_analysis",
            "individual_contributions", "risk_assessment", "recommendations",
            "confidence_factors"
        ]
        
        for key in expected_keys:
            assert key in result
        
        # Verify content types
        assert isinstance(result["overall_assessment"], str)
        assert isinstance(result["performance_analysis"], dict)
        assert isinstance(result["synergy_analysis"], dict)
        assert isinstance(result["individual_contributions"], dict)
        assert isinstance(result["risk_assessment"], dict)
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["confidence_factors"], dict)
    
    def test_composition_risk_calculation(self, analyzer, sample_composition):
        """Test composition risk calculation."""
        # Mock match manager for role familiarity check (with some matches)
        mock_matches = [Mock() for _ in range(10)]  # Sufficient matches for familiarity
        for match in mock_matches:
            participant = Mock()
            participant.puuid = "puuid1"  # Match one of the players
            participant.individual_position = "top"
            match.participants = [participant]
        
        analyzer.match_manager.get_matches_for_player = Mock(return_value=mock_matches)
        analyzer._normalize_role = Mock(return_value="top")
        
        # High performance, high confidence = low risk
        high_perf = PerformanceMetrics(win_rate=0.65)
        risk_low = analyzer._calculate_composition_risk(sample_composition, high_perf, 0.8)
        assert 0.0 <= risk_low <= 1.0  # Valid risk range
        
        # Low performance, low confidence = high risk
        low_perf = PerformanceMetrics(win_rate=0.35)
        risk_high = analyzer._calculate_composition_risk(sample_composition, low_perf, 0.2)
        assert 0.0 <= risk_high <= 1.0  # Valid risk range
        assert risk_high > risk_low  # High risk should be greater than low risk
        
        # Test with no matches (unfamiliar roles should increase risk)
        analyzer.match_manager.get_matches_for_player = Mock(return_value=[])
        risk_unfamiliar = analyzer._calculate_composition_risk(sample_composition, high_perf, 0.8)
        assert 0.0 <= risk_unfamiliar <= 1.0  # Valid risk range
    
    def test_enhanced_optimization_algorithm(self, analyzer):
        """Test the enhanced optimization algorithm with multiple criteria."""
        player_pool = ["puuid1", "puuid2", "puuid3", "puuid4", "puuid5", "puuid6"]
        constraints = CompositionConstraints(
            min_synergy_score=0.05,
            max_risk_tolerance=0.6
        )
        
        # Create mock compositions with different characteristics
        high_win_rate_comp = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid1", "Player1", "top", 1, "Champion1"),
            "jungle": PlayerRoleAssignment("puuid2", "Player2", "jungle", 2, "Champion2"),
            "middle": PlayerRoleAssignment("puuid3", "Player3", "middle", 3, "Champion3"),
            "bottom": PlayerRoleAssignment("puuid4", "Player4", "bottom", 4, "Champion4"),
            "support": PlayerRoleAssignment("puuid5", "Player5", "support", 5, "Champion5")
        })
        
        high_synergy_comp = TeamComposition(players={
            "top": PlayerRoleAssignment("puuid2", "Player2", "top", 6, "Champion6"),
            "jungle": PlayerRoleAssignment("puuid3", "Player3", "jungle", 7, "Champion7"),
            "middle": PlayerRoleAssignment("puuid4", "Player4", "middle", 8, "Champion8"),
            "bottom": PlayerRoleAssignment("puuid5", "Player5", "bottom", 9, "Champion9"),
            "support": PlayerRoleAssignment("puuid6", "Player6", "support", 10, "Champion10")
        })
        
        # Mock composition generation
        analyzer._generate_possible_compositions = Mock(return_value=[high_win_rate_comp, high_synergy_comp])
        
        # Mock analysis results
        def mock_analyze_performance(comp):
            if comp == high_win_rate_comp:
                return CompositionPerformance(
                    composition=comp,
                    total_games=10,
                    performance=PerformanceMetrics(games_played=10, wins=7, win_rate=0.7),
                    synergy_effects=SynergyEffects(overall_synergy=0.08)
                )
            else:
                return CompositionPerformance(
                    composition=comp,
                    total_games=8,
                    performance=PerformanceMetrics(games_played=8, wins=4, win_rate=0.5),
                    synergy_effects=SynergyEffects(overall_synergy=0.2)
                )
        
        analyzer._find_composition_matches = Mock(side_effect=lambda comp: 
            [(Mock(), {})] * (10 if comp == high_win_rate_comp else 8))
        analyzer.analyze_composition_performance = Mock(side_effect=mock_analyze_performance)
        analyzer._calculate_historical_confidence = Mock(return_value=0.8)
        analyzer._generate_historical_reasoning = Mock(return_value=["Historical analysis"])
        analyzer._calculate_composition_risk = Mock(return_value=0.3)
        
        # Test optimization
        result = analyzer.identify_optimal_compositions(player_pool, constraints)
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) <= 10
        
        # Verify sorting considers multiple criteria (win rate, synergy, confidence)
        if len(result) > 1:
            # First result should have the best combined score
            first_score = (result[0].expected_performance.win_rate * 0.4 + 
                          result[0].synergy_score * 0.3 + 
                          result[0].confidence_score * 0.3)
            second_score = (result[1].expected_performance.win_rate * 0.4 + 
                           result[1].synergy_score * 0.3 + 
                           result[1].confidence_score * 0.3)
            assert first_score >= second_score


if __name__ == "__main__":
    pytest.main([__file__])