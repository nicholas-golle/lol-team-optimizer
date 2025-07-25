"""
Tests for advanced features in the League of Legends Team Optimizer.

This module tests the advanced optimization features, performance trend analysis,
caching optimizations, and detailed explanation systems.
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from lol_team_optimizer.models import Player, TeamAssignment, PerformanceData
from lol_team_optimizer.optimizer import OptimizationEngine, OptimizationResult
from lol_team_optimizer.performance_calculator import PerformanceCalculator
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.config import Config


class TestAdvancedOptimization:
    """Test advanced optimization features."""
    
    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing."""
        players = []
        for i in range(7):  # More than 5 to test combinations
            player = Player(
                name=f"Player{i+1}",
                summoner_name=f"Summoner{i+1}#NA1",
                puuid=f"puuid{i+1}",
                role_preferences={
                    "top": (i % 5) + 1,
                    "jungle": ((i + 1) % 5) + 1,
                    "middle": ((i + 2) % 5) + 1,
                    "support": ((i + 3) % 5) + 1,
                    "bottom": ((i + 4) % 5) + 1
                },
                performance_cache={
                    role: {
                        "matches_played": 20 + i,
                        "win_rate": 0.5 + (i * 0.05),
                        "avg_kda": 1.5 + (i * 0.2),
                        "avg_cs_per_min": 6.0 + (i * 0.3),
                        "avg_vision_score": 20 + (i * 2),
                        "recent_form": -0.2 + (i * 0.1)
                    }
                    for role in ["top", "jungle", "middle", "support", "bottom"]
                }
            )
            players.append(player)
        return players
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer instance for testing."""
        return OptimizationEngine()
    
    def test_generate_alternative_compositions(self, optimizer, sample_players):
        """Test generation of alternative team compositions."""
        # Create a primary result
        primary_result = optimizer.optimize_team(sample_players[:5])
        
        # Generate alternatives
        alternatives = optimizer.generate_alternative_compositions(sample_players, primary_result)
        
        assert isinstance(alternatives, list)
        assert len(alternatives) <= 5  # Should return at most 5 alternatives
        
        # Each alternative should be a valid team assignment
        for alt in alternatives:
            assert isinstance(alt, TeamAssignment)
            assert alt.is_complete()
            assert alt.total_score > 0
    
    def test_preference_weighted_optimization(self, optimizer, sample_players):
        """Test preference-weighted optimization strategy."""
        alternatives = optimizer._optimize_with_preference_weight(sample_players[:5], 0.8)
        
        assert len(alternatives) > 0
        assignment = alternatives[0]
        assert assignment.is_complete()
        
        # Should favor players in their preferred roles
        player_dict = {p.name: p for p in sample_players[:5]}
        satisfaction_count = 0
        
        for role, player_name in assignment.assignments.items():
            player = player_dict[player_name]
            if player.role_preferences.get(role, 3) >= 4:
                satisfaction_count += 1
        
        # With high preference weight, should have good role satisfaction
        assert satisfaction_count >= 2
    
    def test_performance_weighted_optimization(self, optimizer, sample_players):
        """Test performance-weighted optimization strategy."""
        alternatives = optimizer._optimize_with_performance_weight(sample_players[:5], 0.9)
        
        assert len(alternatives) > 0
        assignment = alternatives[0]
        assert assignment.is_complete()
        
        # Should have high individual performance scores
        avg_individual_score = sum(assignment.individual_scores.values()) / len(assignment.individual_scores)
        assert avg_individual_score > 0.3  # Should be reasonably high with performance focus
    
    def test_synergy_focused_optimization(self, optimizer, sample_players):
        """Test synergy-focused optimization strategy."""
        alternatives = optimizer._optimize_with_synergy_focus(sample_players[:5])
        
        assert len(alternatives) > 0
        assignment = alternatives[0]
        assert assignment.is_complete()
        
        # Should have synergy scores calculated
        assert len(assignment.synergy_scores) > 0
        
        # Total synergy should contribute meaningfully to score
        total_synergy = sum(assignment.synergy_scores.values())
        assert abs(total_synergy) < 2.0  # Reasonable synergy range
    
    def test_role_balanced_optimization(self, optimizer, sample_players):
        """Test role-balanced optimization strategy."""
        alternatives = optimizer._optimize_role_balanced(sample_players[:5])
        
        assert len(alternatives) <= 3  # Should return limited alternatives
        
        for assignment in alternatives:
            assert assignment.is_complete()
            
            # Check that no player is assigned to a role they strongly dislike
            player_dict = {p.name: p for p in sample_players[:5]}
            for role, player_name in assignment.assignments.items():
                player = player_dict[player_name]
                preference = player.role_preferences.get(role, 3)
                assert preference >= 2  # Should not assign players to roles they strongly dislike
    
    def test_filter_unique_assignments(self, optimizer, sample_players):
        """Test filtering of duplicate assignments."""
        # Create some similar assignments
        assignment1 = TeamAssignment(
            assignments={"top": "Player1", "jungle": "Player2", "middle": "Player3", 
                        "support": "Player4", "bottom": "Player5"},
            total_score=10.0
        )
        
        assignment2 = TeamAssignment(
            assignments={"top": "Player1", "jungle": "Player2", "middle": "Player3", 
                        "support": "Player4", "bottom": "Player6"},  # Only bottom different
            total_score=9.5
        )
        
        assignment3 = TeamAssignment(
            assignments={"top": "Player2", "jungle": "Player3", "middle": "Player4", 
                        "support": "Player5", "bottom": "Player1"},  # Completely different
            total_score=9.0
        )
        
        primary_result = Mock()
        primary_result.best_assignment = assignment1
        
        assignments = [assignment2, assignment3]
        unique = optimizer._filter_unique_assignments(assignments, primary_result)
        
        # Should filter out assignment2 (too similar) but keep assignment3
        assert len(unique) == 1
        assert unique[0] == assignment3


class TestPerformanceTrendAnalysis:
    """Test performance trend analysis features."""
    
    @pytest.fixture
    def calculator(self):
        """Create performance calculator for testing."""
        return PerformanceCalculator()
    
    @pytest.fixture
    def sample_player_with_trends(self):
        """Create a player with trend data."""
        return Player(
            name="TrendPlayer",
            summoner_name="TrendPlayer#NA1",
            role_preferences={"middle": 5, "top": 4, "jungle": 3, "support": 2, "bottom": 1},
            performance_cache={
                "middle": {
                    "matches_played": 25,
                    "win_rate": 0.65,
                    "avg_kda": 2.3,
                    "avg_cs_per_min": 7.2,
                    "avg_vision_score": 18,
                    "recent_form": 0.3  # Improving
                },
                "top": {
                    "matches_played": 15,
                    "win_rate": 0.45,
                    "avg_kda": 1.8,
                    "avg_cs_per_min": 6.5,
                    "avg_vision_score": 15,
                    "recent_form": -0.25  # Declining
                },
                "jungle": {
                    "matches_played": 3,  # Low sample size
                    "win_rate": 0.67,
                    "avg_kda": 2.1,
                    "avg_cs_per_min": 5.8,
                    "avg_vision_score": 25,
                    "recent_form": 0.1
                }
            }
        )
    
    def test_analyze_performance_trends_improving(self, calculator, sample_player_with_trends):
        """Test trend analysis for improving performance."""
        trend = calculator.analyze_performance_trends(sample_player_with_trends, "middle")
        
        assert trend["trend"] == "positive"
        assert trend["direction"] == "improving"
        assert trend["confidence"] > 0.8  # High confidence with 25 games
        assert trend["recent_form"] == 0.3
        assert "prioritize" in trend["recommendation"].lower()
    
    def test_analyze_performance_trends_declining(self, calculator, sample_player_with_trends):
        """Test trend analysis for declining performance."""
        trend = calculator.analyze_performance_trends(sample_player_with_trends, "top")
        
        assert trend["trend"] == "negative"
        assert trend["direction"] == "declining"
        assert trend["confidence"] > 0.5  # Moderate confidence with 15 games
        assert trend["recent_form"] == -0.25
        assert any(word in trend["recommendation"].lower() for word in ["alternative", "practice", "recover", "dip"])
    
    def test_analyze_performance_trends_low_data(self, calculator, sample_player_with_trends):
        """Test trend analysis with insufficient data."""
        trend = calculator.analyze_performance_trends(sample_player_with_trends, "jungle")
        
        assert trend["confidence"] < 0.2  # Low confidence with 3 games
        assert trend["matches_analyzed"] == 3
        assert "more games" in trend["recommendation"].lower()
    
    def test_analyze_performance_trends_no_data(self, calculator):
        """Test trend analysis with no data."""
        player = Player(name="NoData", summoner_name="NoData#NA1")
        trend = calculator.analyze_performance_trends(player, "middle")
        
        assert trend["trend"] == "no_data"
        assert trend["direction"] == "unknown"
        assert trend["confidence"] == 0.0
        assert "need more" in trend["recommendation"].lower()
    
    def test_comprehensive_player_analysis(self, calculator, sample_player_with_trends):
        """Test comprehensive player analysis."""
        analysis = calculator.get_comprehensive_player_analysis(sample_player_with_trends)
        
        assert analysis["player_name"] == "TrendPlayer"
        assert len(analysis["role_scores"]) == 5
        assert len(analysis["role_trends"]) == 5
        assert isinstance(analysis["strengths"], list)
        assert isinstance(analysis["weaknesses"], list)
        assert isinstance(analysis["recommendations"], list)
        
        # Should identify middle as strength (high score and preference)
        middle_score = analysis["role_scores"]["middle"]
        assert middle_score > 0.5
        
        # Should have recommendations
        assert len(analysis["recommendations"]) > 0


class TestCachingOptimizations:
    """Test caching optimization features."""
    
    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config()
            config.data_directory = temp_dir
            config.cache_directory = temp_dir + "/cache"
            config.cache_duration_hours = 1.0
            config.max_cache_size_mb = 1.0
            yield config
    
    @pytest.fixture
    def data_manager(self, temp_config):
        """Create data manager with temporary configuration."""
        return DataManager(temp_config)
    
    def test_batch_cache_api_data(self, data_manager):
        """Test batch caching of API data."""
        data_batch = {
            "player1_middle": {"win_rate": 0.6, "matches": 20},
            "player1_top": {"win_rate": 0.5, "matches": 15},
            "player2_jungle": {"win_rate": 0.7, "matches": 25}
        }
        
        data_manager.batch_cache_api_data(data_batch, ttl_hours=2.0)
        
        # Verify all entries were cached
        cached_data = data_manager.get_multiple_cached_data(list(data_batch.keys()))
        assert len(cached_data) == 3
        
        for key, expected_data in data_batch.items():
            assert cached_data[key] == expected_data
    
    def test_get_multiple_cached_data(self, data_manager):
        """Test efficient retrieval of multiple cached entries."""
        # Cache some data
        data_manager.cache_api_data({"test": "data1"}, "key1")
        data_manager.cache_api_data({"test": "data2"}, "key2")
        data_manager.cache_api_data({"test": "data3"}, "key3")
        
        # Retrieve multiple entries
        keys = ["key1", "key2", "key3", "nonexistent"]
        cached_data = data_manager.get_multiple_cached_data(keys)
        
        assert len(cached_data) == 3  # Should not include nonexistent key
        assert cached_data["key1"]["test"] == "data1"
        assert cached_data["key2"]["test"] == "data2"
        assert cached_data["key3"]["test"] == "data3"
        assert "nonexistent" not in cached_data
    
    def test_cache_statistics(self, data_manager):
        """Test cache statistics functionality."""
        # Add some cache entries
        data_manager.cache_api_data({"test": "data1"}, "key1")
        data_manager.cache_api_data({"test": "data2"}, "key2")
        
        stats = data_manager.get_cache_statistics()
        
        assert stats["total_files"] == 2
        assert stats["valid_files"] == 2
        assert stats["expired_files"] == 0
        assert stats["corrupted_files"] == 0
        assert len(stats["cache_keys"]) == 2
        assert "key1" in stats["cache_keys"]
        assert "key2" in stats["cache_keys"]
        assert stats["oldest_entry"] is not None
        assert stats["newest_entry"] is not None
    
    def test_optimize_player_data_access(self, data_manager):
        """Test optimized player data access."""
        # Create and save test players
        players = [
            Player(name="Player1", summoner_name="P1#NA1"),
            Player(name="Player2", summoner_name="P2#NA1"),
            Player(name="Player3", summoner_name="P3#NA1")
        ]
        data_manager.save_player_data(players)
        
        # Test optimized access
        requested_names = ["Player1", "Player3", "NonExistent"]
        result = data_manager.optimize_player_data_access(requested_names)
        
        assert len(result) == 2  # Should return only existing players
        assert "Player1" in result
        assert "Player3" in result
        assert "NonExistent" not in result
        assert isinstance(result["Player1"], Player)
        assert isinstance(result["Player3"], Player)
    
    def test_preload_performance_data(self, data_manager):
        """Test performance data preloading."""
        players = [
            Player(name="Player1", summoner_name="P1#NA1", 
                  performance_cache={"middle": {"win_rate": 0.6}}),
            Player(name="Player2", summoner_name="P2#NA1",
                  performance_cache={"top": {"win_rate": 0.5}})
        ]
        
        # Save players first so they exist in the data store
        data_manager.save_player_data(players)
        
        roles = ["middle", "top", "jungle"]
        data_manager.preload_performance_data(players, roles)
        
        # Verify players were updated with access timestamps
        loaded_players = data_manager.load_player_data()
        player_dict = {p.name: p for p in loaded_players}
        
        assert "Player1" in player_dict
        assert "Player2" in player_dict
        
        # Check that last_updated was set
        for player in players:
            loaded_player = player_dict[player.name]
            assert loaded_player.last_updated is not None


class TestDetailedExplanations:
    """Test detailed explanation system."""
    
    @pytest.fixture
    def optimizer(self):
        """Create optimizer for testing explanations."""
        return OptimizationEngine()
    
    def test_preference_description(self, optimizer):
        """Test preference description conversion."""
        assert optimizer._preference_description(1) == "Strongly Dislikes"
        assert optimizer._preference_description(3) == "Neutral"
        assert optimizer._preference_description(5) == "Strongly Prefers"
        assert optimizer._preference_description(99) == "Unknown"
    
    def test_synergy_description(self, optimizer):
        """Test synergy description conversion."""
        assert optimizer._synergy_description(0.15) == "Excellent synergy"
        assert optimizer._synergy_description(0.07) == "Good synergy"
        assert optimizer._synergy_description(0.01) == "Neutral synergy"
        assert optimizer._synergy_description(-0.03) == "Minor conflict"
        assert optimizer._synergy_description(-0.1) == "Poor synergy"
    
    def test_strategic_analysis_generation(self, optimizer):
        """Test strategic analysis generation."""
        players = [
            Player(name="Player1", summoner_name="P1#NA1", 
                  role_preferences={"top": 5, "jungle": 3, "middle": 2, "support": 1, "bottom": 4}),
            Player(name="Player2", summoner_name="P2#NA1",
                  role_preferences={"top": 2, "jungle": 5, "middle": 4, "support": 3, "bottom": 1}),
            Player(name="Player3", summoner_name="P3#NA1",
                  role_preferences={"top": 1, "jungle": 2, "middle": 5, "support": 4, "bottom": 3}),
            Player(name="Player4", summoner_name="P4#NA1",
                  role_preferences={"top": 3, "jungle": 1, "middle": 2, "support": 5, "bottom": 4}),
            Player(name="Player5", summoner_name="P5#NA1",
                  role_preferences={"top": 4, "jungle": 4, "middle": 3, "support": 2, "bottom": 5})
        ]
        
        assignments = {
            "top": "Player1",      # Preference 5 - satisfied
            "jungle": "Player2",   # Preference 5 - satisfied  
            "middle": "Player3",   # Preference 5 - satisfied
            "support": "Player4",  # Preference 5 - satisfied
            "bottom": "Player5"    # Preference 5 - satisfied
        }
        
        individual_scores = {
            "Player1": 0.8,
            "Player2": 0.7,
            "Player3": 0.9,
            "Player4": 0.6,
            "Player5": 0.75
        }
        
        analysis = optimizer._generate_strategic_analysis(players, assignments, individual_scores)
        
        assert isinstance(analysis, list)
        assert len(analysis) > 5  # Should have multiple analysis points
        assert any("Role Satisfaction: 5/5" in line for line in analysis)
        assert any("Recommended Focus:" in line for line in analysis)
    
    def test_detailed_explanation_generation(self, optimizer):
        """Test detailed explanation generation."""
        players = [
            Player(name="TestPlayer", summoner_name="Test#NA1",
                  role_preferences={"middle": 4},
                  performance_cache={
                      "middle": {
                          "matches_played": 20,
                          "win_rate": 0.65,
                          "avg_kda": 2.1
                      }
                  })
        ]
        
        assignments = {"middle": "TestPlayer"}
        individual_scores = {"TestPlayer": 0.75}
        synergy_scores = {}
        
        explanation = optimizer._generate_explanation(
            players, assignments, individual_scores, synergy_scores
        )
        
        assert "Team Assignment Explanation:" in explanation
        assert "MIDDLE: TestPlayer" in explanation
        assert "Performance Score: 0.75" in explanation
        assert "Role Preference: 4/5 (Prefers)" in explanation
        assert "65.0% WR over 20 games" in explanation
        assert "Strategic Analysis:" in explanation
        assert "Score Breakdown:" in explanation


if __name__ == "__main__":
    pytest.main([__file__])