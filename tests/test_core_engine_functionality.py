"""
Tests for core engine functionality and shared logic.

Tests the CoreEngine class methods, business logic, and shared functionality
across all interfaces.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player, ChampionMastery, TeamAssignment
from lol_team_optimizer.optimizer import OptimizationResult


class TestCoreEngineInitialization:
    """Test CoreEngine initialization and component setup."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    @patch('lol_team_optimizer.core_engine.ChampionDataManager')
    @patch('lol_team_optimizer.core_engine.PerformanceCalculator')
    @patch('lol_team_optimizer.core_engine.SynergyManager')
    @patch('lol_team_optimizer.core_engine.OptimizationEngine')
    def test_successful_initialization(self, mock_opt_engine, mock_synergy, mock_perf_calc, 
                                     mock_champ_data, mock_riot_client, mock_data_manager, mock_config):
        """Test successful CoreEngine initialization."""
        # Setup all mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        mock_riot_client_instance = Mock()
        mock_riot_client.return_value = mock_riot_client_instance
        
        mock_champ_data_instance = Mock()
        mock_champ_data.return_value = mock_champ_data_instance
        
        mock_perf_calc_instance = Mock()
        mock_perf_calc.return_value = mock_perf_calc_instance
        
        mock_synergy_instance = Mock()
        mock_synergy.return_value = mock_synergy_instance
        mock_synergy_instance.get_synergy_database.return_value = {}
        
        mock_opt_engine_instance = Mock()
        mock_opt_engine.return_value = mock_opt_engine_instance
        
        # Initialize engine
        engine = CoreEngine()
        
        # Verify all components were initialized
        assert engine.config == mock_config_instance
        assert engine.data_manager == mock_data_manager_instance
        assert engine.riot_client == mock_riot_client_instance
        assert engine.champion_data_manager == mock_champ_data_instance
        assert engine.performance_calculator == mock_perf_calc_instance
        assert engine.synergy_manager == mock_synergy_instance
        assert engine.optimizer == mock_opt_engine_instance
        assert engine.api_available is True
        assert engine.roles == ["top", "jungle", "middle", "support", "bottom"]
    
    @patch('lol_team_optimizer.core_engine.Config')
    def test_config_initialization_failure(self, mock_config):
        """Test handling of configuration initialization failure."""
        mock_config.side_effect = Exception("Config failed")
        
        with pytest.raises(RuntimeError, match="Configuration initialization failed"):
            CoreEngine()
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_data_manager_initialization_failure(self, mock_data_manager, mock_config):
        """Test handling of data manager initialization failure."""
        mock_config.return_value = Mock()
        mock_data_manager.side_effect = Exception("DataManager failed")
        
        with pytest.raises(RuntimeError, match="Data manager initialization failed"):
            CoreEngine()
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_api_client_initialization_failure_graceful_degradation(self, mock_riot_client, mock_data_manager, mock_config):
        """Test graceful degradation when API client fails to initialize."""
        # Setup basic mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        # Make API client fail
        mock_riot_client.side_effect = Exception("API client failed")
        
        # Mock other components to succeed
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            # Should not raise exception, but set api_available to False
            engine = CoreEngine()
            
            assert engine.api_available is False
            assert engine.riot_client is None


class TestPlayerManagement:
    """Test player management functionality."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_add_player_with_data_success(self, mock_riot_client, mock_data_manager, mock_config):
        """Test successful player addition with data fetching."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        mock_data_manager_instance.load_player_data.return_value = []
        mock_data_manager_instance.get_player_by_name.return_value = None
        
        mock_riot_client_instance = Mock()
        mock_riot_client.return_value = mock_riot_client_instance
        mock_riot_client_instance.get_summoner_data.return_value = {
            'puuid': 'test_puuid_123',
            'gameName': 'TestPlayer',
            'tagLine': 'NA1'
        }
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            # Mock API data fetching
            with patch.object(engine, '_fetch_player_api_data_with_caching') as mock_fetch:
                mock_fetch.return_value = True
                
                success, message, player = engine.add_player_with_data("TestPlayer", "TestPlayer#NA1")
                
                assert success is True
                assert "successfully" in message.lower()
                assert player is not None
                assert player.name == "TestPlayer"
                assert player.summoner_name == "TestPlayer#NA1"
                assert player.puuid == "test_puuid_123"
                mock_data_manager_instance.save_player_data.assert_called_once()
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_add_player_validation_errors(self, mock_data_manager, mock_config):
        """Test player addition validation errors."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            # Test empty name
            success, message, player = engine.add_player_with_data("", "test#tag")
            assert success is False
            assert "required" in message.lower()
            assert player is None
            
            # Test empty riot ID
            success, message, player = engine.add_player_with_data("TestPlayer", "")
            assert success is False
            assert "required" in message.lower()
            assert player is None
            
            # Test invalid riot ID format
            success, message, player = engine.add_player_with_data("TestPlayer", "invalidformat")
            assert success is False
            assert "tag" in message.lower()
            assert player is None
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_add_duplicate_player(self, mock_data_manager, mock_config):
        """Test adding a duplicate player."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Mock existing player
        existing_player = Player(name="TestPlayer", summoner_name="TestPlayer#NA1", puuid="existing_puuid")
        mock_data_manager_instance.get_player_by_name.return_value = existing_player
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            success, message, player = engine.add_player_with_data("TestPlayer", "TestPlayer#NA1")
            
            assert success is False
            assert "already exists" in message.lower()
            assert player is None
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_refresh_player_data(self, mock_data_manager, mock_config):
        """Test refreshing player data."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Mock existing player
        test_player = Player(name="TestPlayer", summoner_name="TestPlayer#NA1", puuid="test_puuid")
        mock_data_manager_instance.get_player_by_name.return_value = test_player
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            engine.api_available = True
            
            # Mock API data fetching
            with patch.object(engine, '_fetch_player_api_data_with_caching') as mock_fetch:
                mock_fetch.return_value = True
                
                success, message = engine.refresh_player_data("TestPlayer")
                
                assert success is True
                assert "successfully refreshed" in message.lower()
                mock_fetch.assert_called_once_with(test_player)
                mock_data_manager_instance.update_player.assert_called_once_with(test_player)
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_refresh_player_data_not_found(self, mock_data_manager, mock_config):
        """Test refreshing data for non-existent player."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        mock_data_manager_instance.get_player_by_name.return_value = None
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            success, message = engine.refresh_player_data("NonExistentPlayer")
            
            assert success is False
            assert "not found" in message.lower()


class TestOptimizationLogic:
    """Test optimization logic and smart team building."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_optimize_team_smart_success(self, mock_data_manager, mock_config):
        """Test successful smart team optimization."""
        # Setup mocks
        mock_config.return_value = Mock()
        
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
        mock_assignment = Mock()
        mock_assignment.assignments = {"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"}
        mock_assignment.total_score = 85.5
        mock_assignment.individual_scores = {"Player1": 4.2, "Player2": 4.1, "Player3": 4.3, "Player4": 4.0, "Player5": 4.1}
        mock_assignment.champion_recommendations = {}
        
        mock_result = Mock()
        mock_result.best_assignment = mock_assignment
        mock_result.assignments = [mock_assignment]
        mock_result.optimization_time = 1.5
        
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
            
            success, message, result = engine.optimize_team_smart()
            
            assert success is True
            assert result is not None
            assert result.best_assignment.total_score == 85.5
            assert len(result.best_assignment.assignments) == 5
            mock_opt_engine_instance.optimize_team.assert_called_once()
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_optimize_team_smart_insufficient_players(self, mock_data_manager, mock_config):
        """Test optimization with insufficient players."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Only one player
        test_players = [
            Player(name="Player1", summoner_name="player1#tag", puuid="puuid1",
                  role_preferences={"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3})
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            success, message, result = engine.optimize_team_smart()
            
            assert success is False
            assert "need at least 2 players" in message.lower()
            assert result is None
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_auto_select_players_with_fallback(self, mock_data_manager, mock_config):
        """Test automatic player selection with fallback logic."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
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
            # Some players have custom preferences
            if i <= 2:
                player.role_preferences = {"top": 5, "jungle": 1, "middle": 3, "support": 2, "bottom": 4}
            test_players.append(player)
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            selected_players = engine._auto_select_players_with_fallback(test_players, max_players=5)
            
            assert len(selected_players) <= 5
            assert len(selected_players) >= min(5, len(test_players))
            # Should prefer players with more data
            selected_names = [p.name for p in selected_players]
            assert "Player1" in selected_names  # Has all types of data
            assert "Player2" in selected_names  # Has all types of data


class TestDataProcessing:
    """Test data processing and caching functionality."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_process_champion_masteries(self, mock_data_manager, mock_config):
        """Test processing of raw champion mastery data."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        # Mock champion data manager
        mock_champ_data = Mock()
        mock_champ_data.get_champion_by_id.return_value = {
            'name': 'TestChampion',
            'tags': ['Fighter', 'Tank']
        }
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager') as mock_champ_data_class, \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_champ_data_class.return_value = mock_champ_data
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            # Test data
            raw_masteries = [
                {
                    'championId': 1,
                    'championLevel': 7,
                    'championPoints': 150000,
                    'chestGranted': True,
                    'tokensEarned': 2,
                    'lastPlayTime': int(datetime.now().timestamp() * 1000)
                },
                {
                    'championId': 2,
                    'championLevel': 5,
                    'championPoints': 75000,
                    'chestGranted': False,
                    'tokensEarned': 0,
                    'lastPlayTime': int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
                }
            ]
            
            processed = engine._process_champion_masteries(raw_masteries)
            
            assert len(processed) == 2
            assert 1 in processed
            assert 2 in processed
            
            mastery1 = processed[1]
            assert mastery1.champion_id == 1
            assert mastery1.champion_name == 'TestChampion'
            assert mastery1.mastery_level == 7
            assert mastery1.mastery_points == 150000
            assert mastery1.chest_granted is True
            assert mastery1.tokens_earned == 2
            assert 'top' in mastery1.primary_roles  # From Fighter/Tank tags
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_calculate_performance_from_matches(self, mock_riot_client, mock_data_manager, mock_config):
        """Test calculation of performance data from match history."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        mock_riot_client_instance = Mock()
        mock_riot_client.return_value = mock_riot_client_instance
        
        # Mock performance calculation
        mock_riot_client_instance.calculate_role_performance.return_value = {
            'matches_played': 10,
            'win_rate': 0.65,
            'avg_kda': 2.3,
            'avg_cs_per_min': 6.5
        }
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            # Test player and matches
            test_player = Player(name="TestPlayer", summoner_name="test#tag", puuid="test_puuid")
            test_matches = [{'matchId': 'match1'}, {'matchId': 'match2'}]
            
            performance_cache = engine._calculate_performance_from_matches(test_player, test_matches)
            
            assert isinstance(performance_cache, dict)
            # Should have performance data for all roles
            for role in engine.roles:
                assert role in performance_cache
                role_perf = performance_cache[role]
                assert role_perf['matches_played'] == 10
                assert role_perf['win_rate'] == 0.65
                assert role_perf['avg_kda'] == 2.3
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_generate_intelligent_default_preferences(self, mock_data_manager, mock_config):
        """Test generation of intelligent default preferences."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            
            preferences = engine._generate_intelligent_default_preferences()
            
            assert isinstance(preferences, dict)
            assert len(preferences) == 5
            
            # Check all roles are present
            for role in engine.roles:
                assert role in preferences
                assert 1 <= preferences[role] <= 5
            
            # Support should be slightly higher (common need)
            assert preferences["support"] >= preferences["jungle"]  # Support easier than jungle


class TestSystemStatus:
    """Test system status and diagnostics functionality."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_get_system_status(self, mock_data_manager, mock_config):
        """Test system status generation."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players with varying data completeness
        test_players = []
        for i in range(1, 4):
            player = Player(name=f"Player{i}", summoner_name=f"player{i}#tag", puuid=f"puuid{i}")
            if i <= 2:  # 2 players have API data
                player.performance_cache = {"top": {"matches_played": 10}}
                player.champion_masteries = {1: ChampionMastery(1, "TestChamp", 7, 100000, False, 0, ["top"], datetime.now())}
            if i == 1:  # 1 player has custom preferences
                player.role_preferences = {"top": 5, "jungle": 1, "middle": 3, "support": 2, "bottom": 4}
            else:
                player.role_preferences = {"top": 3, "jungle": 3, "middle": 3, "support": 3, "bottom": 3}
            test_players.append(player)
        
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock champion data manager
        mock_champ_data = Mock()
        mock_champ_data.champions = {'1': {'name': 'TestChamp'}, '2': {'name': 'TestChamp2'}}
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager') as mock_champ_data_class, \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_champ_data_class.return_value = mock_champ_data
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            engine.api_available = True
            
            status = engine._get_system_status()
            
            assert isinstance(status, dict)
            assert status['api_available'] is True
            assert status['player_count'] == 3
            assert status['players_with_api_data'] == 2
            assert status['players_with_preferences'] == 1
            assert status['ready_for_optimization'] is False  # Less than 5 players
            assert status['champion_data_loaded'] is True
            assert 'last_updated' in status
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_get_system_status_error_handling(self, mock_data_manager, mock_config):
        """Test system status error handling."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        mock_data_manager_instance.load_player_data.side_effect = Exception("Data load failed")
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            engine.api_available = False
            
            status = engine._get_system_status()
            
            assert isinstance(status, dict)
            assert status['api_available'] is False
            assert 'error' in status
            assert status['error'] == "Data load failed"
            assert 'last_updated' in status


class TestBulkOperations:
    """Test bulk operations functionality."""
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_bulk_refresh_player_data(self, mock_data_manager, mock_config):
        """Test bulk refresh of player data."""
        # Setup mocks
        mock_config.return_value = Mock()
        
        mock_data_manager_instance = Mock()
        mock_data_manager.return_value = mock_data_manager_instance
        
        # Create test players
        test_players = [
            Player(name="Player1", summoner_name="player1#tag", puuid="puuid1"),
            Player(name="Player2", summoner_name="player2#tag", puuid="puuid2")
        ]
        mock_data_manager_instance.load_player_data.return_value = test_players
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            engine.api_available = True
            
            # Mock API data fetching
            with patch.object(engine, '_fetch_player_api_data_with_caching') as mock_fetch:
                mock_fetch.return_value = True
                
                results = engine.bulk_refresh_player_data()
                
                assert isinstance(results, dict)
                assert len(results) == 2
                assert "Player1" in results
                assert "Player2" in results
                assert results["Player1"][0] is True  # Success
                assert results["Player2"][0] is True  # Success
    
    @patch('lol_team_optimizer.core_engine.Config')
    @patch('lol_team_optimizer.core_engine.DataManager')
    def test_bulk_refresh_api_unavailable(self, mock_data_manager, mock_config):
        """Test bulk refresh when API is unavailable."""
        # Setup mocks
        mock_config.return_value = Mock()
        mock_data_manager.return_value = Mock()
        
        # Mock other components
        with patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager') as mock_synergy, \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'):
            
            mock_synergy.return_value.get_synergy_database.return_value = {}
            
            engine = CoreEngine()
            engine.api_available = False
            
            results = engine.bulk_refresh_player_data()
            
            assert isinstance(results, dict)
            assert "error" in results
            assert results["error"][0] is False
            assert "unavailable" in results["error"][1].lower()