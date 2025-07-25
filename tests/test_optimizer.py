"""
Unit tests for the optimization engine.

Tests the core optimization algorithm, cost matrix generation, constraint handling,
and result ranking functionality.
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

from lol_team_optimizer.optimizer import OptimizationEngine, OptimizationResult
from lol_team_optimizer.models import Player, TeamAssignment, PerformanceData
from lol_team_optimizer.performance_calculator import PerformanceCalculator


class TestOptimizationEngine:
    """Test cases for the OptimizationEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = OptimizationEngine()
        
        # Create test players with different preferences and performance
        self.players = [
            Player(
                name="Alice",
                summoner_name="alice_lol",
                puuid="alice_puuid",
                role_preferences={"top": 5, "jungle": 2, "middle": 3, "support": 1, "bottom": 2},
                performance_cache={
                    "top": {
                        "matches_played": 20,
                        "win_rate": 0.65,
                        "avg_kda": 2.1,
                        "avg_cs_per_min": 7.2,
                        "avg_vision_score": 25.0,
                        "recent_form": 0.3
                    }
                }
            ),
            Player(
                name="Bob",
                summoner_name="bob_jungle",
                puuid="bob_puuid",
                role_preferences={"top": 2, "jungle": 5, "middle": 3, "support": 1, "bottom": 2},
                performance_cache={
                    "jungle": {
                        "matches_played": 25,
                        "win_rate": 0.72,
                        "avg_kda": 2.8,
                        "avg_cs_per_min": 5.5,
                        "avg_vision_score": 35.0,
                        "recent_form": 0.5
                    }
                }
            ),
            Player(
                name="Charlie",
                summoner_name="charlie_mid",
                puuid="charlie_puuid",
                role_preferences={"top": 2, "jungle": 1, "middle": 5, "support": 2, "bottom": 3},
                performance_cache={
                    "middle": {
                        "matches_played": 30,
                        "win_rate": 0.58,
                        "avg_kda": 2.5,
                        "avg_cs_per_min": 8.1,
                        "avg_vision_score": 20.0,
                        "recent_form": 0.1
                    }
                }
            ),
            Player(
                name="Diana",
                summoner_name="diana_support",
                puuid="diana_puuid",
                role_preferences={"top": 1, "jungle": 2, "middle": 2, "support": 5, "bottom": 3},
                performance_cache={
                    "support": {
                        "matches_played": 18,
                        "win_rate": 0.61,
                        "avg_kda": 1.8,
                        "avg_cs_per_min": 1.2,
                        "avg_vision_score": 45.0,
                        "recent_form": 0.2
                    }
                }
            ),
            Player(
                name="Eve",
                summoner_name="eve_adc",
                puuid="eve_puuid",
                role_preferences={"top": 2, "jungle": 1, "middle": 3, "support": 2, "bottom": 5},
                performance_cache={
                    "bottom": {
                        "matches_played": 22,
                        "win_rate": 0.68,
                        "avg_kda": 2.9,
                        "avg_cs_per_min": 7.8,
                        "avg_vision_score": 15.0,
                        "recent_form": 0.4
                    }
                }
            )
        ]
    
    def test_init(self):
        """Test OptimizationEngine initialization."""
        engine = OptimizationEngine()
        assert engine.performance_calculator is not None
        assert engine.roles == ["top", "jungle", "middle", "support", "bottom"]
        assert "individual_performance" in engine.weights
        assert "role_preference" in engine.weights
        assert "team_synergy" in engine.weights
        
        # Test with custom performance calculator
        mock_calc = Mock(spec=PerformanceCalculator)
        engine_custom = OptimizationEngine(mock_calc)
        assert engine_custom.performance_calculator is mock_calc
    
    def test_optimize_team_success(self):
        """Test successful team optimization with exactly 5 players."""
        result = self.engine.optimize_team(self.players)
        
        assert isinstance(result, OptimizationResult)
        assert len(result.assignments) >= 1
        assert result.best_assignment is not None
        assert result.best_assignment.is_complete()
        assert result.optimization_time >= 0
        
        # Check that all roles are assigned
        assignment = result.best_assignment
        assert len(assignment.assignments) == 5
        assert set(assignment.assignments.keys()) == {"top", "jungle", "middle", "support", "bottom"}
        
        # Check that all players are assigned exactly once
        assigned_players = list(assignment.assignments.values())
        assert len(assigned_players) == len(set(assigned_players))
    
    def test_optimize_team_insufficient_players(self):
        """Test optimization with fewer than 5 players."""
        with pytest.raises(ValueError, match="At least 5 players required"):
            self.engine.optimize_team(self.players[:4])
    
    def test_optimize_team_more_than_five_players(self):
        """Test optimization with more than 5 players."""
        # Add a 6th player
        extra_player = Player(
            name="Frank",
            summoner_name="frank_flex",
            puuid="frank_puuid",
            role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3}
        )
        
        extended_players = self.players + [extra_player]
        result = self.engine.optimize_team(extended_players)
        
        assert isinstance(result, OptimizationResult)
        assert result.best_assignment.is_complete()
        # Should have multiple combinations to choose from
        assert len(result.assignments) >= 1
    
    def test_build_cost_matrix(self):
        """Test cost matrix generation."""
        cost_matrix = self.engine._build_cost_matrix(self.players)
        
        assert cost_matrix.shape == (5, 5)  # 5 players x 5 roles
        assert isinstance(cost_matrix, np.ndarray)
        
        # All costs should be negative (since we use negative scores)
        assert np.all(cost_matrix <= 0)
        
        # Players should have lower costs (higher scores) for preferred roles
        alice_idx = 0  # Alice is first player
        top_role_idx = 0  # Top is first role
        jungle_role_idx = 1  # Jungle is second role
        
        # Alice prefers top (5) over jungle (2), so top should have lower cost
        assert cost_matrix[alice_idx, top_role_idx] < cost_matrix[alice_idx, jungle_role_idx]
    
    def test_calculate_team_synergy(self):
        """Test team synergy calculation."""
        assignments = {
            "top": "Alice",
            "jungle": "Bob", 
            "middle": "Charlie",
            "support": "Diana",
            "bottom": "Eve"
        }
        
        synergy_scores = self.engine._calculate_team_synergy(self.players, assignments)
        
        assert isinstance(synergy_scores, dict)
        # Should have synergy scores for all player pairs (10 pairs for 5 players)
        assert len(synergy_scores) == 10
        
        # All synergy scores should be in reasonable range
        for score in synergy_scores.values():
            assert -1.0 <= score <= 1.0
    
    def test_generate_explanation(self):
        """Test explanation generation."""
        assignments = {
            "top": "Alice",
            "jungle": "Bob",
            "middle": "Charlie", 
            "support": "Diana",
            "bottom": "Eve"
        }
        individual_scores = {
            "Alice": 0.8,
            "Bob": 0.9,
            "Charlie": 0.7,
            "Diana": 0.75,
            "Eve": 0.85
        }
        synergy_scores = {
            ("Alice", "Bob"): 0.1,
            ("Bob", "Charlie"): 0.15,
            ("Charlie", "Diana"): 0.05,
            ("Diana", "Eve"): 0.2,
            ("Alice", "Charlie"): 0.05
        }
        
        explanation = self.engine._generate_explanation(
            self.players, assignments, individual_scores, synergy_scores
        )
        
        assert isinstance(explanation, str)
        assert "Team Assignment Explanation" in explanation
        assert "Role Assignments" in explanation
        assert "Score Breakdown" in explanation
        
        # Should contain all player names and roles
        for player_name in individual_scores.keys():
            assert player_name in explanation
        for role in assignments.keys():
            assert role.upper() in explanation
    
    def test_get_alternative_assignments(self):
        """Test getting alternative assignments."""
        result = self.engine.optimize_team(self.players)
        alternatives = self.engine.get_alternative_assignments(result, count=2)
        
        assert isinstance(alternatives, list)
        assert len(alternatives) <= 2
        
        # If there are alternatives, they should be different from the best
        if alternatives:
            for alt in alternatives:
                assert isinstance(alt, TeamAssignment)
                assert alt != result.best_assignment
    
    def test_compare_assignments(self):
        """Test assignment comparison."""
        result = self.engine.optimize_team(self.players)
        
        if len(result.assignments) >= 2:
            assignment1 = result.assignments[0]
            assignment2 = result.assignments[1]
            
            comparison = self.engine.compare_assignments(assignment1, assignment2)
            
            assert isinstance(comparison, str)
            assert "Assignment Comparison" in comparison
            assert "Score Difference" in comparison
    
    def test_optimization_with_no_performance_data(self):
        """Test optimization when players have no performance data."""
        players_no_data = [
            Player(
                name=f"Player{i}",
                summoner_name=f"player{i}",
                puuid=f"puuid{i}",
                role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3}
            )
            for i in range(5)
        ]
        
        result = self.engine.optimize_team(players_no_data)
        
        assert isinstance(result, OptimizationResult)
        assert result.best_assignment.is_complete()
        # Should still produce valid assignments even without performance data
        assert result.best_assignment.total_score >= 0
    
    def test_optimization_with_conflicting_preferences(self):
        """Test optimization when multiple players prefer the same role."""
        # Create players who all prefer middle lane
        conflicting_players = []
        for i in range(5):
            player = Player(
                name=f"MidLaner{i}",
                summoner_name=f"mid{i}",
                puuid=f"mid_puuid{i}",
                role_preferences={"top": 2, "jungle": 2, "middle": 5, "support": 1, "bottom": 2}
            )
            conflicting_players.append(player)
        
        result = self.engine.optimize_team(conflicting_players)
        
        assert isinstance(result, OptimizationResult)
        assert result.best_assignment.is_complete()
        
        # Only one player should get middle lane
        assignments = result.best_assignment.assignments
        middle_players = [player for role, player in assignments.items() if role == "middle"]
        assert len(middle_players) == 1
    
    def test_optimization_result_validation(self):
        """Test OptimizationResult validation."""
        assignment = TeamAssignment(
            assignments={"top": "Alice", "jungle": "Bob", "middle": "Charlie", "support": "Diana", "bottom": "Eve"},
            total_score=10.0
        )
        
        # Valid result
        result = OptimizationResult(
            assignments=[assignment],
            best_assignment=assignment,
            optimization_time=0.1
        )
        assert result.best_assignment == assignment
        
        # Invalid: empty assignments
        with pytest.raises(ValueError, match="must contain at least one assignment"):
            OptimizationResult(
                assignments=[],
                best_assignment=assignment,
                optimization_time=0.1
            )
        
        # Invalid: best assignment not in list
        other_assignment = TeamAssignment()
        with pytest.raises(ValueError, match="Best assignment must be in the assignments list"):
            OptimizationResult(
                assignments=[assignment],
                best_assignment=other_assignment,
                optimization_time=0.1
            )
    
    @patch('lol_team_optimizer.optimizer.linear_sum_assignment')
    def test_optimization_algorithm_failure(self, mock_assignment):
        """Test handling of optimization algorithm failures."""
        # Make the Hungarian algorithm fail
        mock_assignment.side_effect = Exception("Algorithm failed")
        
        with pytest.raises(ValueError, match="No valid team assignments could be generated"):
            self.engine.optimize_team(self.players)
    
    def test_weight_configuration(self):
        """Test that optimization weights can be configured."""
        # Test default weights
        assert self.engine.weights["individual_performance"] == 0.6
        assert self.engine.weights["role_preference"] == 0.25
        assert self.engine.weights["team_synergy"] == 0.15
        
        # Test weight modification
        self.engine.weights["individual_performance"] = 0.8
        self.engine.weights["role_preference"] = 0.2
        self.engine.weights["team_synergy"] = 0.0
        
        result = self.engine.optimize_team(self.players)
        assert isinstance(result, OptimizationResult)
        # Should still produce valid results with different weights
        assert result.best_assignment.is_complete()
    
    def test_performance_calculator_integration(self):
        """Test integration with PerformanceCalculator."""
        mock_calc = Mock(spec=PerformanceCalculator)
        mock_calc.calculate_individual_score.return_value = 0.8
        mock_calc.calculate_synergy_score.return_value = 0.1
        
        engine = OptimizationEngine(mock_calc)
        result = engine.optimize_team(self.players)
        
        assert isinstance(result, OptimizationResult)
        
        # Verify performance calculator was called
        assert mock_calc.calculate_individual_score.called
        assert mock_calc.calculate_synergy_score.called