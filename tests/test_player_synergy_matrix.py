"""
Tests for Player Synergy Matrix and Pairing Analysis System.

This module tests the comprehensive player-to-player synergy analysis,
role-specific synergy calculations, synergy matrix visualization data structures,
and synergy trend analysis functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from lol_team_optimizer.player_synergy_matrix import (
    PlayerSynergyMatrix, PlayerPairSynergy, RolePairSynergy,
    SynergyMatrix, SynergyMatrixEntry, SynergyTrendAnalysis,
    SynergyTrendPoint, TeamBuildingRecommendation
)
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters, DateRange, InsufficientDataError, AnalyticsError
)
from lol_team_optimizer.models import Match, MatchParticipant
from lol_team_optimizer.config import Config


class TestPlayerSynergyMatrix:
    """Test cases for PlayerSynergyMatrix class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "test_cache"
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
    def mock_statistical_analyzer(self):
        """Create mock statistical analyzer."""
        analyzer = Mock()
        analyzer.calculate_correlation.return_value = 0.5
        return analyzer
    
    @pytest.fixture
    def synergy_matrix(self, mock_config, mock_match_manager, mock_baseline_manager, mock_statistical_analyzer):
        """Create PlayerSynergyMatrix instance."""
        return PlayerSynergyMatrix(
            config=mock_config,
            match_manager=mock_match_manager,
            baseline_manager=mock_baseline_manager,
            statistical_analyzer=mock_statistical_analyzer
        )
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample matches for testing."""
        matches = []
        
        for i in range(10):
            match = Match(
                match_id=f"match_{i}",
                game_creation=int((datetime.now() - timedelta(days=i)).timestamp() * 1000),
                game_duration=1800 + i * 60,  # 30-39 minutes
                game_end_timestamp=int((datetime.now() - timedelta(days=i) + timedelta(seconds=1800)).timestamp() * 1000),
                queue_id=420,  # Ranked Solo
                winning_team=100 if i % 2 == 0 else 200
            )
            
            # Add participants
            participants = []
            for j in range(10):
                participant = MatchParticipant(
                    puuid=f"player_{j % 5}",  # 5 unique players
                    summoner_name=f"Player{j % 5}",
                    champion_id=1 + (j % 20),  # Various champions
                    team_id=100 if j < 5 else 200,
                    individual_position=["top", "jungle", "middle", "bottom", "support"][j % 5],
                    kills=2 + (i + j) % 8,
                    deaths=1 + (i + j) % 5,
                    assists=3 + (i + j) % 10,
                    total_damage_dealt_to_champions=15000 + i * 1000 + j * 500,
                    total_minions_killed=150 + i * 10 + j * 5,
                    neutral_minions_killed=20 + i * 2 + j,
                    vision_score=25 + i + j,
                    gold_earned=12000 + i * 500 + j * 200,
                    win=(100 if j < 5 else 200) == match.winning_team
                )
                participants.append(participant)
            
            match.participants = participants
            matches.append(match)
        
        return matches
    
    def test_calculate_player_synergy_success(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test successful player synergy calculation."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        # Filter matches to only include those with both players
        shared_matches = [m for m in sample_matches if 
                         any(p.puuid == player1_puuid for p in m.participants) and
                         any(p.puuid == player2_puuid for p in m.participants)]
        
        mock_match_manager.get_matches_with_multiple_players.return_value = shared_matches
        
        # Execute
        result = synergy_matrix.calculate_player_synergy(player1_puuid, player2_puuid)
        
        # Verify
        assert isinstance(result, PlayerPairSynergy)
        assert result.player1_puuid == player1_puuid
        assert result.player2_puuid == player2_puuid
        assert result.total_games_together > 0
        assert -1.0 <= result.synergy_score <= 1.0
        assert 0.0 <= result.confidence_level <= 1.0
        
        # Verify match manager was called correctly
        mock_match_manager.get_matches_with_multiple_players.assert_called_once_with(
            {player1_puuid, player2_puuid}
        )
    
    def test_calculate_player_synergy_insufficient_data(self, synergy_matrix, mock_match_manager):
        """Test player synergy calculation with insufficient data."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        # Return too few matches
        mock_match_manager.get_matches_with_multiple_players.return_value = []
        
        # Execute & Verify
        with pytest.raises(InsufficientDataError) as exc_info:
            synergy_matrix.calculate_player_synergy(player1_puuid, player2_puuid)
        
        assert "player synergy" in str(exc_info.value)
    
    def test_calculate_player_synergy_with_filters(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test player synergy calculation with filters applied."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        shared_matches = [m for m in sample_matches if 
                         any(p.puuid == player1_puuid for p in m.participants) and
                         any(p.puuid == player2_puuid for p in m.participants)]
        
        mock_match_manager.get_matches_with_multiple_players.return_value = shared_matches
        
        # Create filters
        filters = AnalyticsFilters(
            date_range=DateRange(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now()
            ),
            queue_types=[420]  # Ranked Solo only
        )
        
        # Execute
        result = synergy_matrix.calculate_player_synergy(player1_puuid, player2_puuid, filters)
        
        # Verify
        assert isinstance(result, PlayerPairSynergy)
        assert result.total_games_together >= 0
    
    def test_analyze_role_specific_synergy(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test role-specific synergy analysis."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        role1 = "top"
        role2 = "jungle"
        
        shared_matches = [m for m in sample_matches if 
                         any(p.puuid == player1_puuid for p in m.participants) and
                         any(p.puuid == player2_puuid for p in m.participants)]
        
        mock_match_manager.get_matches_with_multiple_players.return_value = shared_matches
        
        # Execute
        result = synergy_matrix.analyze_role_specific_synergy(
            player1_puuid, player2_puuid, role1, role2
        )
        
        # Verify
        assert isinstance(result, RolePairSynergy)
        assert result.role1 == role1
        assert result.role2 == role2
        assert result.games_together >= 0
        assert -1.0 <= result.synergy_score <= 1.0
    
    def test_create_synergy_matrix_player_type(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test creation of player synergy matrix."""
        # Setup
        player_puuids = ["player_0", "player_1", "player_2"]
        
        # Mock the calculate_player_synergy method to avoid complex setup
        with patch.object(synergy_matrix, 'calculate_player_synergy') as mock_calc:
            mock_synergy = PlayerPairSynergy(
                player1_puuid="player_0",
                player2_puuid="player_1",
                player1_name="Player0",
                player2_name="Player1",
                total_games_together=10,
                synergy_score=0.3,
                confidence_level=0.8
            )
            mock_calc.return_value = mock_synergy
            
            # Execute
            result = synergy_matrix.create_synergy_matrix(player_puuids, "player")
            
            # Verify
            assert isinstance(result, SynergyMatrix)
            assert result.matrix_type == "player"
            assert len(result.entries) > 0
            assert result.total_entities == len(player_puuids)
    
    def test_create_synergy_matrix_role_type(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test creation of role synergy matrix."""
        # Setup
        player_puuids = ["player_0", "player_1", "player_2"]
        
        # Mock the calculate_player_synergy method
        with patch.object(synergy_matrix, 'calculate_player_synergy') as mock_calc:
            mock_synergy = PlayerPairSynergy(
                player1_puuid="player_0",
                player2_puuid="player_1",
                player1_name="Player0",
                player2_name="Player1",
                total_games_together=10,
                synergy_score=0.3,
                confidence_level=0.8
            )
            # Add role synergies
            mock_synergy.role_synergies = {
                ("top", "jungle"): RolePairSynergy(
                    role1="top", role2="jungle", games_together=5,
                    wins_together=3, synergy_score=0.2
                )
            }
            mock_calc.return_value = mock_synergy
            
            # Execute
            result = synergy_matrix.create_synergy_matrix(player_puuids, "role")
            
            # Verify
            assert isinstance(result, SynergyMatrix)
            assert result.matrix_type == "role"
    
    def test_analyze_synergy_trends(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test synergy trend analysis over time."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        shared_matches = [m for m in sample_matches if 
                         any(p.puuid == player1_puuid for p in m.participants) and
                         any(p.puuid == player2_puuid for p in m.participants)]
        
        mock_match_manager.get_matches_with_multiple_players.return_value = shared_matches
        
        # Execute
        result = synergy_matrix.analyze_synergy_trends(player1_puuid, player2_puuid)
        
        # Verify
        assert isinstance(result, SynergyTrendAnalysis)
        assert result.player1_puuid == player1_puuid
        assert result.player2_puuid == player2_puuid
        assert result.trend_direction in ["improving", "declining", "stable"]
        assert 0.0 <= result.trend_strength <= 1.0
    
    def test_analyze_synergy_trends_insufficient_data(self, synergy_matrix, mock_match_manager):
        """Test synergy trend analysis with insufficient data."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        # Return too few matches
        mock_match_manager.get_matches_with_multiple_players.return_value = []
        
        # Execute & Verify
        with pytest.raises(InsufficientDataError) as exc_info:
            synergy_matrix.analyze_synergy_trends(player1_puuid, player2_puuid)
        
        assert "trend analysis" in str(exc_info.value)
    
    def test_generate_team_building_recommendations(self, synergy_matrix):
        """Test team building recommendations generation."""
        # Setup
        available_players = ["player_0", "player_1", "player_2", "player_3", "player_4"]
        required_roles = ["top", "jungle", "middle", "bottom", "support"]
        
        # Mock create_synergy_matrix to return a matrix with some synergies
        with patch.object(synergy_matrix, 'create_synergy_matrix') as mock_create:
            mock_matrix = SynergyMatrix(matrix_type="player")
            
            # Add some synergy entries
            for i, player1 in enumerate(available_players):
                for player2 in available_players[i+1:]:
                    entry = SynergyMatrixEntry(
                        entity1=player1,
                        entity2=player2,
                        synergy_score=0.1 * (i + 1),  # Varying synergy scores
                        confidence=0.8,
                        sample_size=10,
                        last_updated=datetime.now()
                    )
                    mock_matrix.set_synergy(player1, player2, entry)
            
            mock_create.return_value = mock_matrix
            
            # Execute
            result = synergy_matrix.generate_team_building_recommendations(
                available_players, required_roles
            )
            
            # Verify
            assert isinstance(result, list)
            assert len(result) > 0
            
            for recommendation in result:
                assert isinstance(recommendation, TeamBuildingRecommendation)
                assert len(recommendation.role_assignments) == len(required_roles)
                assert -1.0 <= recommendation.expected_team_synergy <= 1.0
                assert 0.0 <= recommendation.confidence <= 1.0
    
    def test_generate_team_building_recommendations_insufficient_players(self, synergy_matrix):
        """Test team building recommendations with insufficient players."""
        # Setup
        available_players = ["player_0", "player_1"]  # Only 2 players
        required_roles = ["top", "jungle", "middle", "bottom", "support"]  # Need 5
        
        # Execute & Verify
        with pytest.raises(AnalyticsError) as exc_info:
            synergy_matrix.generate_team_building_recommendations(available_players, required_roles)
        
        assert "Not enough players" in str(exc_info.value)
    
    def test_synergy_score_calculation(self, synergy_matrix):
        """Test synergy score calculation logic."""
        # Create a synergy object with known values
        synergy = PlayerPairSynergy(
            player1_puuid="player_0",
            player2_puuid="player_1",
            player1_name="Player0",
            player2_name="Player1",
            total_games_together=20,
            wins_together=15,  # 75% win rate
            losses_together=5,
            win_rate_together=0.75,
            avg_combined_kda=3.0,
            avg_combined_vision_score=60.0,
            recent_games_together=5
        )
        
        # Calculate synergy score
        score = synergy_matrix._calculate_synergy_score(synergy)
        
        # Verify
        assert -1.0 <= score <= 1.0
        assert score > 0  # Should be positive due to high win rate
    
    def test_role_normalization(self, synergy_matrix):
        """Test role position normalization."""
        # Test various role inputs
        test_cases = [
            ("TOP", "top"),
            ("JUNGLE", "jungle"),
            ("MIDDLE", "middle"),
            ("MID", "middle"),
            ("BOTTOM", "bottom"),
            ("BOT", "bottom"),
            ("ADC", "bottom"),
            ("SUPPORT", "support"),
            ("UTILITY", "support"),
            ("", "unknown"),
            (None, "unknown")
        ]
        
        for input_role, expected in test_cases:
            result = synergy_matrix._normalize_role(input_role)
            assert result == expected
    
    def test_confidence_calculation(self, synergy_matrix):
        """Test confidence level calculation based on sample size."""
        test_cases = [
            (0, 0.0),
            (1, 0.09),  # Approximately
            (5, 0.33),  # Approximately
            (10, 0.5),  # Approximately
            (20, 0.67), # Approximately
            (100, 0.91) # Approximately
        ]
        
        for sample_size, expected_min in test_cases:
            confidence = synergy_matrix._calculate_synergy_confidence(sample_size)
            assert 0.0 <= confidence <= 0.95
            if sample_size > 0:
                assert confidence >= expected_min - 0.1  # Allow some tolerance
    
    def test_cache_functionality(self, synergy_matrix, mock_match_manager, sample_matches):
        """Test synergy calculation caching."""
        # Setup
        player1_puuid = "player_0"
        player2_puuid = "player_1"
        
        shared_matches = [m for m in sample_matches if 
                         any(p.puuid == player1_puuid for p in m.participants) and
                         any(p.puuid == player2_puuid for p in m.participants)]
        
        mock_match_manager.get_matches_with_multiple_players.return_value = shared_matches
        
        # First call - should calculate and cache
        result1 = synergy_matrix.calculate_player_synergy(player1_puuid, player2_puuid)
        
        # Second call - should use cache
        result2 = synergy_matrix.calculate_player_synergy(player1_puuid, player2_puuid)
        
        # Verify results are identical (from cache)
        assert result1.synergy_score == result2.synergy_score
        assert result1.total_games_together == result2.total_games_together
        
        # Verify match manager was only called once (cache hit on second call)
        assert mock_match_manager.get_matches_with_multiple_players.call_count == 1


class TestSynergyDataStructures:
    """Test cases for synergy data structures."""
    
    def test_player_pair_synergy_creation(self):
        """Test PlayerPairSynergy data structure."""
        synergy = PlayerPairSynergy(
            player1_puuid="player_0",
            player2_puuid="player_1",
            player1_name="Player0",
            player2_name="Player1",
            total_games_together=10,
            wins_together=7,
            losses_together=3
        )
        
        assert synergy.win_rate_together == 0.7
        assert synergy.player1_puuid == "player_0"
        assert synergy.player2_puuid == "player_1"
    
    def test_role_pair_synergy_creation(self):
        """Test RolePairSynergy data structure."""
        role_synergy = RolePairSynergy(
            role1="top",
            role2="jungle",
            games_together=5,
            wins_together=3
        )
        
        assert role_synergy.win_rate == 0.6
        assert role_synergy.role1 == "top"
        assert role_synergy.role2 == "jungle"
    
    def test_synergy_matrix_entry(self):
        """Test SynergyMatrixEntry data structure."""
        entry = SynergyMatrixEntry(
            entity1="player_0",
            entity2="player_1",
            synergy_score=0.5,
            confidence=0.8,
            sample_size=15,
            last_updated=datetime.now()
        )
        
        assert entry.synergy_score == 0.5
        assert entry.confidence == 0.8
        assert entry.sample_size == 15
    
    def test_synergy_matrix_operations(self):
        """Test SynergyMatrix operations."""
        matrix = SynergyMatrix(matrix_type="player")
        
        # Test setting and getting synergy
        entry = SynergyMatrixEntry(
            entity1="player_0",
            entity2="player_1",
            synergy_score=0.3,
            confidence=0.7,
            sample_size=10,
            last_updated=datetime.now()
        )
        
        matrix.set_synergy("player_0", "player_1", entry)
        retrieved = matrix.get_synergy("player_0", "player_1")
        
        assert retrieved is not None
        assert retrieved.synergy_score == 0.3
        
        # Test symmetric access
        retrieved_reverse = matrix.get_synergy("player_1", "player_0")
        assert retrieved_reverse is not None
        assert retrieved_reverse.synergy_score == 0.3
    
    def test_synergy_trend_point(self):
        """Test SynergyTrendPoint data structure."""
        trend_point = SynergyTrendPoint(
            timestamp=datetime.now(),
            synergy_score=0.4,
            games_in_period=8,
            win_rate_in_period=0.625,
            confidence=0.75
        )
        
        assert trend_point.synergy_score == 0.4
        assert trend_point.games_in_period == 8
        assert trend_point.win_rate_in_period == 0.625
    
    def test_team_building_recommendation(self):
        """Test TeamBuildingRecommendation data structure."""
        recommendation = TeamBuildingRecommendation(
            recommended_pairs=[("player_0", "player_1", 0.5)],
            role_assignments={"top": "player_0", "jungle": "player_1"},
            expected_team_synergy=0.3,
            confidence=0.8,
            reasoning=["High synergy between top and jungle"],
            risk_factors=["Limited data for some pairs"]
        )
        
        assert len(recommendation.recommended_pairs) == 1
        assert recommendation.expected_team_synergy == 0.3
        assert len(recommendation.reasoning) == 1
        assert len(recommendation.risk_factors) == 1


if __name__ == "__main__":
    pytest.main([__file__])