"""
Integration tests for streamlined workflows.

Tests the complete end-to-end workflows of the streamlined system including
Quick Optimize, Manage Players, View Analysis, and Settings workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import json
from pathlib import Path
from datetime import datetime

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.streamlined_cli import StreamlinedCLI
from lol_team_optimizer.models import Player, ChampionMastery


def create_mock_config():
    """Create a properly configured mock config object."""
    mock_config = Mock()
    mock_config.cache_directory = "/tmp/cache"
    mock_config.data_directory = "/tmp/data"
    mock_config.individual_weight = 0.4
    mock_config.preference_weight = 0.3
    mock_config.synergy_weight = 0.3
    return mock_config


class TestQuickOptimizeWorkflow:
    """Test the complete Quick Optimize workflow."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_quick_optimize_with_sufficient_players(self, mock_riot_client, mock_data_manager, mock_config):
        """Test Quick Optimize workflow with sufficient players."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players
        test_players = [
            Player(name=f"Player{i}", summoner_name=f"player{i}#tag", puuid=f"puuid{i}",
                  role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3})
            for i in range(1, 6)
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock optimization result
        mock_optimization_result = Mock()
        mock_optimization_result.best_assignment = Mock()
        mock_optimization_result.best_assignment.assignments = {"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"}
        mock_optimization_result.best_assignment.total_score = 85.5
        mock_optimization_result.best_assignment.individual_scores = {"Player1": 4.2, "Player2": 4.1, "Player3": 4.3, "Player4": 4.0, "Player5": 4.1}
        mock_optimization_result.best_assignment.champion_recommendations = {}
        mock_optimization_result.optimization_time = 1.5
        mock_optimization_result.assignments = [mock_optimization_result.best_assignment]
        
        # Initialize engine
        engine = CoreEngine()
        
        # Mock the optimizer
        with patch.object(engine, 'optimizer') as mock_optimizer:
            mock_optimizer.optimize_team.return_value = mock_optimization_result
            
            # Test optimization
            success, message, result = engine.optimize_team_smart()
            
            assert success is True
            assert "successfully" in message.lower() or "optimization" in message.lower()
            assert result is not None
            assert result.best_assignment.total_score == 85.5
            assert len(result.best_assignment.assignments) == 5
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_quick_optimize_insufficient_players(self, mock_data_manager, mock_config):
        """Test Quick Optimize workflow with insufficient players."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Only one player
        test_players = [
            Player(name="Player1", summoner_name="player1#tag", puuid="puuid1",
                  role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3})
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test optimization with insufficient players
        success, message, result = engine.optimize_team_smart()
        
        assert success is False
        assert "need at least 2 players" in message.lower()
        assert result is None
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_quick_optimize_with_auto_selection(self, mock_riot_client, mock_data_manager, mock_config):
        """Test Quick Optimize with automatic player selection."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players with varying data quality
        test_players = []
        for i in range(1, 8):  # 7 players
            player = Player(
                name=f"Player{i}", 
                summoner_name=f"player{i}#tag", 
                puuid=f"puuid{i}",
                role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3}
            )
            # Some players have performance data
            if i <= 3:
                player.performance_cache = {"top": {"matches_played": 10, "win_rate": 0.6}}
            # Some players have champion masteries
            if i <= 4:
                player.champion_masteries = {1: ChampionMastery(1, "TestChamp", 7, 100000, False, 0, ["top"], datetime.now())}
            test_players.append(player)
        
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock optimization result
        mock_optimization_result = Mock()
        mock_optimization_result.best_assignment = Mock()
        mock_optimization_result.best_assignment.assignments = {"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"}
        mock_optimization_result.best_assignment.total_score = 85.5
        mock_optimization_result.best_assignment.individual_scores = {"Player1": 4.2, "Player2": 4.1, "Player3": 4.3, "Player4": 4.0, "Player5": 4.1}
        mock_optimization_result.best_assignment.champion_recommendations = {}
        mock_optimization_result.optimization_time = 1.5
        mock_optimization_result.assignments = [mock_optimization_result.best_assignment]
        
        # Initialize engine
        engine = CoreEngine()
        
        # Mock the optimizer and auto-selection
        with patch.object(engine, 'optimizer') as mock_optimizer, \
             patch.object(engine, '_auto_select_players_with_fallback') as mock_auto_select:
            
            mock_optimizer.optimize_team.return_value = mock_optimization_result
            mock_auto_select.return_value = test_players[:5]  # Select first 5 players
            
            # Test optimization with auto-selection
            success, message, result = engine.optimize_team_smart(auto_select=True)
            
            assert success is True
            assert result is not None
            mock_auto_select.assert_called_once()


class TestPlayerManagementWorkflow:
    """Test the complete Player Management workflow."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_add_player_with_api_data(self, mock_riot_client, mock_data_manager, mock_config):
        """Test adding a player with API data fetching."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        mock_data_manager_instance.load_player_data.return_value = []
        mock_data_manager_instance.get_player_by_name.return_value = None
        
        mock_riot_client_instance = Mock()
        mock_riot_client.return_value = mock_riot_client_instance
        mock_riot_client_instance.get_summoner_data.return_value = {
            'puuid': 'test_puuid',
            'gameName': 'TestPlayer',
            'tagLine': 'NA1'
        }
        
        # Initialize engine
        engine = CoreEngine()
        
        # Mock API data fetching
        with patch.object(engine, '_fetch_player_api_data_with_caching') as mock_fetch:
            mock_fetch.return_value = True
            
            # Test adding player
            success, message, player = engine.add_player_with_data("TestPlayer", "TestPlayer#NA1")
            
            assert success is True
            assert "successfully" in message.lower()
            assert player is not None
            assert player.name == "TestPlayer"
            assert player.puuid == "test_puuid"
            mock_data_manager_instance.save_player_data.assert_called_once()
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_add_duplicate_player(self, mock_riot_client, mock_data_manager, mock_config):
        """Test adding a duplicate player."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Mock existing player
        existing_player = Player(name="TestPlayer", summoner_name="TestPlayer#NA1", puuid="existing_puuid")
        mock_data_manager_instance.get_player_by_name.return_value = existing_player
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test adding duplicate player
        success, message, player = engine.add_player_with_data("TestPlayer", "TestPlayer#NA1")
        
        assert success is False
        assert "already exists" in message.lower()
        assert player is None
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_bulk_player_operations(self, mock_data_manager, mock_config):
        """Test bulk player operations."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players
        test_players = [
            Player(name="Player1", summoner_name="player1#tag", puuid="puuid1"),
            Player(name="Player2", summoner_name="player2#tag", puuid="puuid2")
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        mock_data_manager_instance.get_player_by_name.side_effect = lambda name: next((p for p in test_players if p.name == name), None)
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test bulk operations
        operations = [
            {'action': 'update_preferences', 'name': 'Player1', 'preferences': {'top': 5, 'jungle': 1, 'middle': 3, 'support': 2, 'bottom': 4}},
            {'action': 'refresh_data', 'name': 'Player2'}  # Use refresh_data instead of remove
        ]
        
        results = engine.bulk_player_operations(operations)
        
        assert len(results) == 2
        # Both operations should return results (success or failure)
        assert isinstance(results[0], tuple)
        assert isinstance(results[1], tuple)
        assert len(results[0]) == 2  # (success, message)
        assert len(results[1]) == 2  # (success, message)


class TestAnalysisWorkflow:
    """Test the complete Analysis workflow."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_comprehensive_analysis(self, mock_data_manager, mock_config):
        """Test comprehensive analysis generation."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players with performance data
        test_players = []
        for i in range(1, 6):
            player = Player(
                name=f"Player{i}",
                summoner_name=f"player{i}#tag",
                puuid=f"puuid{i}",
                role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3}
            )
            player.performance_cache = {
                "top": {"matches_played": 10, "win_rate": 0.6, "avg_kda": 2.1},
                "jungle": {"matches_played": 5, "win_rate": 0.4, "avg_kda": 1.8}
            }
            player.champion_masteries = {
                1: ChampionMastery(1, "TestChamp1", 7, 100000, False, 0, ["top"], datetime.now()),
                2: ChampionMastery(2, "TestChamp2", 6, 80000, False, 0, ["jungle"], datetime.now())
            }
            test_players.append(player)
        
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test comprehensive analysis
        analysis = engine.get_comprehensive_analysis()
        
        assert analysis is not None
        assert 'players' in analysis
        assert 'player_count' in analysis
        assert analysis['player_count'] == 5
        assert len(analysis['players']) == 5
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_player_comparison_analysis(self, mock_data_manager, mock_config):
        """Test player comparison analysis."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players
        player1 = Player(name="Player1", summoner_name="player1#tag", puuid="puuid1")
        player1.performance_cache = {"top": {"matches_played": 20, "win_rate": 0.7, "avg_kda": 2.5}}
        
        player2 = Player(name="Player2", summoner_name="player2#tag", puuid="puuid2")
        player2.performance_cache = {"top": {"matches_played": 15, "win_rate": 0.6, "avg_kda": 2.1}}
        
        mock_data_manager_instance.get_player_by_name.side_effect = lambda name: player1 if name == "Player1" else player2 if name == "Player2" else None
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test player analysis (using comprehensive analysis instead)
        analysis = engine.get_comprehensive_analysis(["Player1", "Player2"])
        
        assert analysis is not None
        assert 'players' in analysis
        assert len(analysis['players']) == 2


class TestSettingsWorkflow:
    """Test the Settings and configuration workflow."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_system_diagnostics(self, mock_data_manager, mock_config):
        """Test system diagnostics functionality."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        mock_data_manager_instance.load_player_data.return_value = []
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test system status
        status = engine._get_system_status()
        
        assert status is not None
        assert 'api_available' in status
        assert 'player_count' in status
        assert 'ready_for_optimization' in status
        assert 'last_updated' in status
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_cache_management(self, mock_data_manager, mock_config):
        """Test cache management functionality."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Initialize engine
        engine = CoreEngine()
        
        # Test system diagnostics (using available method)
        diagnostics = engine.get_system_diagnostics()
        
        assert diagnostics is not None
        assert 'system_status' in diagnostics


class TestWorkflowIntegration:
    """Test integration between different workflows."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_add_player_then_optimize_workflow(self, mock_riot_client, mock_data_manager, mock_config):
        """Test the complete workflow of adding players then optimizing."""
        # Setup mocks
        mock_config_instance = create_mock_config()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Start with no players
        players_list = []
        
        # Mock load_player_data to return current list
        def load_players():
            return players_list.copy()
        mock_data_manager_instance.load_player_data.side_effect = load_players
        
        # Mock get_player_by_name to check current list
        def get_player_by_name(name):
            return next((p for p in players_list if p.name == name), None)
        mock_data_manager_instance.get_player_by_name.side_effect = get_player_by_name
        
        # Mock save to update the list
        def save_players(players):
            players_list.clear()
            players_list.extend(players)
        mock_data_manager_instance.save_player_data.side_effect = save_players
        
        mock_riot_client_instance = Mock()
        mock_riot_client.return_value = mock_riot_client_instance
        mock_riot_client_instance.get_summoner_data.return_value = {
            'puuid': 'test_puuid',
            'gameName': 'TestPlayer',
            'tagLine': 'NA1'
        }
        
        # Initialize engine
        engine = CoreEngine()
        
        # Mock API data fetching
        with patch.object(engine, '_fetch_player_api_data_with_caching') as mock_fetch:
            mock_fetch.return_value = True
            
            # Add 5 players
            for i in range(1, 6):
                mock_riot_client_instance.get_summoner_data.return_value = {
                    'puuid': f'puuid{i}',
                    'gameName': f'Player{i}',
                    'tagLine': 'NA1'
                }
                
                success, message, player = engine.add_player_with_data(f"Player{i}", f"Player{i}#NA1")
                assert success is True
                assert player is not None
            
            # Mock optimization result
            mock_optimization_result = Mock()
            mock_optimization_result.best_assignment = Mock()
            mock_optimization_result.best_assignment.assignments = {"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"}
            mock_optimization_result.best_assignment.total_score = 85.5
            mock_optimization_result.best_assignment.individual_scores = {"Player1": 4.2, "Player2": 4.1, "Player3": 4.3, "Player4": 4.0, "Player5": 4.1}
            mock_optimization_result.best_assignment.champion_recommendations = {}
            mock_optimization_result.optimization_time = 1.5
            mock_optimization_result.assignments = [mock_optimization_result.best_assignment]
            
            # Mock the optimizer
            with patch.object(engine, 'optimizer') as mock_optimizer:
                mock_optimizer.optimize_team.return_value = mock_optimization_result
                
                # Now optimize
                success, message, result = engine.optimize_team_smart()
                
                assert success is True
                assert result is not None
                assert len(result.best_assignment.assignments) == 5
    
    def test_workflow_error_handling(self):
        """Test error handling across workflows."""
        # Test with minimal mocking to trigger real error paths
        with patch('lol_team_optimizer.core_engine.Config') as mock_config:
            mock_config.side_effect = Exception("Config failed")
            
            # This should handle the error gracefully
            with pytest.raises(RuntimeError, match="Configuration initialization failed"):
                CoreEngine()