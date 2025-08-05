"""
Performance tests for the streamlined system.
"""

import pytest
import time
from unittest.mock import Mock, patch
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player


def create_mock_config():
    """Create a properly configured mock config object."""
    mock_config = Mock()
    mock_config.cache_directory = "/tmp/cache"
    mock_config.data_directory = "/tmp/data"
    mock_config.individual_weight = 0.4
    mock_config.preference_weight = 0.3
    mock_config.synergy_weight = 0.3
    return mock_config


class TestOptimizationPerformance:
    """Test optimization performance and speed."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_optimization_speed_small_dataset(self, mock_riot_client, mock_data_manager, mock_config):
        """Test optimization speed with small dataset (5 players)."""
        # Setup mocks
        mock_config.return_value = create_mock_config()
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create 5 test players
        test_players = [
            Player(name=f"Player{i}", summoner_name=f"player{i}#tag", puuid=f"puuid{i}",
                  role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3})
            for i in range(1, 6)
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock optimization result
        mock_result = Mock()
        mock_result.best_assignment = Mock()
        mock_result.best_assignment.assignments = {"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"}
        mock_result.best_assignment.total_score = 85.5
        mock_result.assignments = [mock_result.best_assignment]
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine') as mock_opt_engine:
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            mock_opt_engine_instance = Mock()
            mock_opt_engine.return_value = mock_opt_engine_instance
            mock_opt_engine_instance.optimize_team.return_value = mock_result
            
            engine = CoreEngine()
            
            # Measure optimization time
            start_time = time.time()
            success, message, result = engine.optimize_team_smart()
            end_time = time.time()
            
            optimization_time = end_time - start_time
            
            assert success is True
            assert result is not None
            # Should complete within 5 seconds for small dataset
            assert optimization_time < 5.0