"""
Tests for champion recommendation functionality.

This module tests the champion recommendation system that suggests champions
for each role assignment based on player mastery and role suitability.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from lol_team_optimizer.models import (
    Player, TeamAssignment, ChampionMastery, ChampionRecommendation
)
from lol_team_optimizer.optimizer import OptimizationEngine
from lol_team_optimizer.performance_calculator import PerformanceCalculator
from lol_team_optimizer.champion_data import ChampionDataManager


class TestChampionRecommendations:
    """Test champion recommendation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock champion data manager
        self.mock_champion_data = Mock(spec=ChampionDataManager)
        self.mock_champion_data.get_champion_roles.return_value = ['middle', 'top']
        
        # Create performance calculator and optimizer
        self.performance_calculator = PerformanceCalculator(self.mock_champion_data)
        self.optimizer = OptimizationEngine(self.performance_calculator, self.mock_champion_data)
        
        # Create test players with champion mastery data
        self.players = self._create_test_players()
    
    def _create_test_players(self):
        """Create test players with champion mastery data."""
        players = []
        
        # Player 1: Strong mid laner
        player1 = Player(
            name="MidLaner",
            summoner_name="MidLaner#NA1",
            puuid="test_puuid_1",
            role_preferences={
                "top": 2, "jungle": 2, "middle": 5, "support": 1, "bottom": 2
            }
        )
        
        # Add champion masteries for player 1
        player1.champion_masteries = {
            103: ChampionMastery(  # Ahri
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                primary_roles=["middle"]
            ),
            157: ChampionMastery(  # Yasuo
                champion_id=157,
                champion_name="Yasuo",
                mastery_level=6,
                mastery_points=80000,
                primary_roles=["middle", "bottom"]
            ),
            238: ChampionMastery(  # Zed
                champion_id=238,
                champion_name="Zed",
                mastery_level=5,
                mastery_points=45000,
                primary_roles=["middle"]
            )
        }
        
        # Set up role champion pools
        player1.role_champion_pools = {
            "top": [],
            "jungle": [],
            "middle": [103, 157, 238],
            "support": [],
            "bottom": [157]
        }
        
        players.append(player1)
        
        # Player 2: ADC player
        player2 = Player(
            name="ADCPlayer",
            summoner_name="ADCPlayer#NA1",
            puuid="test_puuid_2",
            role_preferences={
                "top": 1, "jungle": 2, "middle": 2, "support": 1, "bottom": 5
            }
        )
        
        player2.champion_masteries = {
            22: ChampionMastery(  # Ashe
                champion_id=22,
                champion_name="Ashe",
                mastery_level=7,
                mastery_points=200000,
                primary_roles=["bottom"]
            ),
            51: ChampionMastery(  # Caitlyn
                champion_id=51,
                champion_name="Caitlyn",
                mastery_level=6,
                mastery_points=120000,
                primary_roles=["bottom"]
            )
        }
        
        player2.role_champion_pools = {
            "top": [],
            "jungle": [],
            "middle": [],
            "support": [],
            "bottom": [22, 51]
        }
        
        players.append(player2)
        
        # Add 3 more players with basic data
        for i in range(3, 6):
            player = Player(
                name=f"Player{i}",
                summoner_name=f"Player{i}#NA1",
                puuid=f"test_puuid_{i}",
                role_preferences={
                    "top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3
                }
            )
            players.append(player)
        
        return players
    
    def test_champion_recommendations_generated(self):
        """Test that champion recommendations are generated for team assignments."""
        # Test the champion recommendation generation directly
        assignments = {
            "top": "Player3",
            "jungle": "Player4", 
            "middle": "MidLaner",
            "support": "Player5",
            "bottom": "ADCPlayer"
        }
        
        # Generate champion recommendations
        recommendations = self.optimizer._generate_champion_recommendations(self.players, assignments)
        
        # Check that recommendations were generated
        assert isinstance(recommendations, dict)
        
        # Check that recommendations exist for roles with champion data
        assert "middle" in recommendations
        assert "bottom" in recommendations
        
        # Check middle lane recommendations
        middle_recs = recommendations["middle"]
        assert len(middle_recs) > 0
        assert all(isinstance(rec, ChampionRecommendation) for rec in middle_recs)
        
        # Check that Ahri (highest mastery) is recommended for middle
        champion_names = [rec.champion_name for rec in middle_recs]
        assert "Ahri" in champion_names
    
    def test_champion_recommendation_properties(self):
        """Test that champion recommendations have correct properties."""
        # Create a test mastery
        mastery = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            primary_roles=["middle"]
        )
        
        # Test confidence calculation
        confidence = self.optimizer._calculate_recommendation_confidence(mastery, 0.9)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # Should be high for level 7 champion
    
    def test_champion_recommendations_with_no_mastery_data(self):
        """Test champion recommendations when player has no mastery data."""
        # Create player with no champion masteries
        player_no_mastery = Player(
            name="NoMastery",
            summoner_name="NoMastery#NA1",
            puuid="test_puuid_no_mastery",
            role_preferences={
                "top": 3, "jungle": 3, "middle": 5, "support": 3, "bottom": 3
            }
        )
        
        players_with_no_mastery = self.players[1:] + [player_no_mastery]  # Replace first player
        
        # Generate recommendations
        assignments = {
            "top": "Player3",
            "jungle": "Player4",
            "middle": "NoMastery",
            "support": "Player5", 
            "bottom": "ADCPlayer"
        }
        
        recommendations = self.optimizer._generate_champion_recommendations(
            players_with_no_mastery, assignments
        )
        
        # Should still generate recommendations (empty or default)
        assert "middle" in recommendations
        middle_recs = recommendations["middle"]
        
        # Should be empty list since no mastery data
        assert len(middle_recs) == 0
    
    def test_champion_recommendation_sorting(self):
        """Test that champion recommendations are sorted by confidence and suitability."""
        # Create player with multiple champions of different mastery levels
        player = Player(
            name="TestPlayer",
            summoner_name="TestPlayer#NA1",
            puuid="test_puuid_sort",
            role_preferences={"middle": 5}
        )
        
        # Add champions with different mastery levels
        player.champion_masteries = {
            1: ChampionMastery(
                champion_id=1,
                champion_name="LowMastery",
                mastery_level=3,
                mastery_points=10000,
                primary_roles=["middle"]
            ),
            2: ChampionMastery(
                champion_id=2,
                champion_name="HighMastery",
                mastery_level=7,
                mastery_points=200000,
                primary_roles=["middle"]
            ),
            3: ChampionMastery(
                champion_id=3,
                champion_name="MediumMastery",
                mastery_level=5,
                mastery_points=50000,
                primary_roles=["middle"]
            )
        }
        
        player.role_champion_pools = {
            "middle": [1, 2, 3]
        }
        
        # Generate recommendations
        assignments = {"middle": "TestPlayer"}
        recommendations = self.optimizer._generate_champion_recommendations([player], assignments)
        
        middle_recs = recommendations["middle"]
        
        # Should be sorted by confidence * suitability (highest first)
        assert len(middle_recs) >= 2
        assert middle_recs[0].champion_name == "HighMastery"  # Highest mastery should be first
        
        # Confidence should be decreasing
        for i in range(len(middle_recs) - 1):
            current_score = middle_recs[i].confidence * middle_recs[i].role_suitability
            next_score = middle_recs[i + 1].confidence * middle_recs[i + 1].role_suitability
            assert current_score >= next_score
    
    def test_champion_recommendation_validation(self):
        """Test that champion recommendations are properly validated."""
        # Test valid recommendation
        valid_rec = ChampionRecommendation(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            role_suitability=0.9,
            confidence=0.8
        )
        
        # Should not raise any exceptions
        assert valid_rec.role_suitability == 0.9
        assert valid_rec.confidence == 0.8
        
        # Test invalid role suitability
        with pytest.raises(ValueError, match="Role suitability must be between 0 and 1"):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=1.5,  # Invalid
                confidence=0.8
            )
        
        # Test invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=0.9,
                confidence=1.2  # Invalid
            )
    
    def test_champion_recommendations_limit(self):
        """Test that champion recommendations are limited to top 3 per role."""
        # Create player with many champions
        player = Player(
            name="ManyChamps",
            summoner_name="ManyChamps#NA1",
            puuid="test_puuid_many",
            role_preferences={"middle": 5}
        )
        
        # Add 10 champions
        player.champion_masteries = {}
        player.role_champion_pools = {"middle": []}
        
        for i in range(1, 11):
            player.champion_masteries[i] = ChampionMastery(
                champion_id=i,
                champion_name=f"Champion{i}",
                mastery_level=5,
                mastery_points=50000,
                primary_roles=["middle"]
            )
            player.role_champion_pools["middle"].append(i)
        
        # Generate recommendations
        assignments = {"middle": "ManyChamps"}
        recommendations = self.optimizer._generate_champion_recommendations([player], assignments)
        
        middle_recs = recommendations["middle"]
        
        # Should be limited to 3 recommendations
        assert len(middle_recs) <= 3
    
    def test_role_suitability_calculation(self):
        """Test role suitability calculation based on champion data."""
        # Mock champion data manager to return specific roles
        self.mock_champion_data.get_champion_roles.return_value = ["middle", "top"]
        
        mastery = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            primary_roles=["middle"]
        )
        
        # Test with matching role
        confidence_match = self.optimizer._calculate_recommendation_confidence(mastery, 0.9)
        
        # Test with non-matching role
        confidence_no_match = self.optimizer._calculate_recommendation_confidence(mastery, 0.3)
        
        # Matching role should have higher confidence
        assert confidence_match > confidence_no_match
    
    def test_integration_with_optimization(self):
        """Test integration of champion recommendations with full optimization."""
        # Mock the cost matrix and assignment to avoid complex optimization logic
        with patch.object(self.optimizer, '_build_cost_matrix') as mock_cost_matrix, \
             patch('scipy.optimize.linear_sum_assignment') as mock_assignment:
            
            # Mock cost matrix
            import numpy as np
            mock_cost_matrix.return_value = np.array([
                [1.0, 2.0, 0.5, 3.0, 2.5],  # Player 1 costs for each role
                [2.5, 3.0, 2.0, 3.5, 0.5],  # Player 2 costs for each role
                [0.8, 1.5, 2.0, 2.5, 3.0],  # Player 3 costs for each role
                [1.5, 0.7, 2.5, 1.0, 3.0],  # Player 4 costs for each role
                [3.0, 2.5, 2.0, 2.0, 2.0],  # Player 5 costs for each role
            ])
            
            # Mock assignment result (player indices, role indices)
            mock_assignment.return_value = ([0, 1, 2, 3, 4], [2, 4, 0, 1, 3])
            
            # Run optimization
            result = self.optimizer.optimize_team(self.players)
            
            # Verify champion recommendations were added
            best = result.best_assignment
            assert hasattr(best, 'champion_recommendations')
            assert isinstance(best.champion_recommendations, dict)
            
            # Check that we have recommendations for all roles
            assert len(best.champion_recommendations) == 5
            
            # Check specific role recommendations where we have data
            for role, recommendations in best.champion_recommendations.items():
                if recommendations:  # If recommendations exist
                    assert all(isinstance(rec, ChampionRecommendation) for rec in recommendations)
                    assert all(0 <= rec.confidence <= 1 for rec in recommendations)
                    assert all(0 <= rec.role_suitability <= 1 for rec in recommendations)


class TestChampionRecommendationModel:
    """Test the ChampionRecommendation model."""
    
    def test_champion_recommendation_creation(self):
        """Test creating a ChampionRecommendation object."""
        rec = ChampionRecommendation(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            role_suitability=0.9,
            confidence=0.85
        )
        
        assert rec.champion_id == 103
        assert rec.champion_name == "Ahri"
        assert rec.mastery_level == 7
        assert rec.mastery_points == 150000
        assert rec.role_suitability == 0.9
        assert rec.confidence == 0.85
    
    def test_champion_recommendation_validation(self):
        """Test validation of ChampionRecommendation fields."""
        # Valid recommendation should work
        ChampionRecommendation(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            role_suitability=0.0,  # Minimum valid
            confidence=1.0  # Maximum valid
        )
        
        # Invalid role suitability (too high)
        with pytest.raises(ValueError):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=1.1,
                confidence=0.8
            )
        
        # Invalid role suitability (negative)
        with pytest.raises(ValueError):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=-0.1,
                confidence=0.8
            )
        
        # Invalid confidence (too high)
        with pytest.raises(ValueError):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=0.9,
                confidence=1.1
            )
        
        # Invalid confidence (negative)
        with pytest.raises(ValueError):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=0.9,
                confidence=-0.1
            )