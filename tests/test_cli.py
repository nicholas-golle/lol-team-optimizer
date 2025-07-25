"""
Integration tests for the CLI module.

Tests user workflows and CLI functionality with mocked components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys
from datetime import datetime

from lol_team_optimizer.cli import CLI
from lol_team_optimizer.models import Player, TeamAssignment, PerformanceData
from lol_team_optimizer.optimizer import OptimizationResult


@pytest.fixture
def cli():
    """Create CLI instance with mocked dependencies."""
    with patch('lol_team_optimizer.cli.Config'), \
         patch('lol_team_optimizer.cli.DataManager'), \
         patch('lol_team_optimizer.cli.RiotAPIClient'), \
         patch('lol_team_optimizer.cli.PerformanceCalculator'), \
         patch('lol_team_optimizer.cli.OptimizationEngine'):
        
        cli = CLI()
        
        # Mock the components
        cli.data_manager = Mock()
        cli.riot_client = Mock()
        cli.performance_calculator = Mock()
        cli.optimizer = Mock()
        
        return cli

@pytest.fixture
def sample_players():
    """Create sample players for testing."""
    return [
        Player(
            name="Player1",
            summoner_name="Summoner1",
            puuid="puuid1",
            role_preferences={"top": 5, "jungle": 3, "middle": 2, "support": 1, "bottom": 4}
        ),
        Player(
            name="Player2", 
            summoner_name="Summoner2",
            puuid="puuid2",
            role_preferences={"top": 2, "jungle": 5, "middle": 3, "support": 1, "bottom": 4}
        ),
        Player(
            name="Player3",
            summoner_name="Summoner3", 
            puuid="puuid3",
            role_preferences={"top": 1, "jungle": 2, "middle": 5, "support": 3, "bottom": 4}
        ),
        Player(
            name="Player4",
            summoner_name="Summoner4",
            puuid="puuid4", 
            role_preferences={"top": 1, "jungle": 2, "middle": 3, "support": 5, "bottom": 4}
        ),
        Player(
            name="Player5",
            summoner_name="Summoner5",
            puuid="puuid5",
            role_preferences={"top": 3, "jungle": 2, "middle": 1, "support": 4, "bottom": 5}
        )
    ]

@pytest.fixture
def sample_optimization_result(sample_players):
    """Create sample optimization result."""
    assignment = TeamAssignment(
        assignments={
            "top": "Player1",
            "jungle": "Player2", 
            "middle": "Player3",
            "support": "Player4",
            "bottom": "Player5"
        },
        total_score=85.5,
        individual_scores={
            "Player1": 18.2,
            "Player2": 17.8,
            "Player3": 19.1,
            "Player4": 16.9,
            "Player5": 18.5
        },
        synergy_scores={
            ("Player1", "Player2"): 2.1,
            ("Player3", "Player4"): 1.8
        },
        champion_recommendations={
            "top": [],
            "jungle": [],
            "middle": [],
            "support": [],
            "bottom": []
        },
        explanation="Optimal assignment based on performance and preferences"
    )
    
    return OptimizationResult(
        assignments=[assignment],
        best_assignment=assignment,
        optimization_time=1.23
    )


class TestCLI:
    """Test cases for CLI functionality."""


class TestPlayerManagement:
    """Test player management workflows."""
    
    def test_add_player_success(self, cli, sample_players):
        """Test successful player addition workflow."""
        cli.data_manager.get_player_by_name.return_value = None
        cli.data_manager.load_player_data.return_value = []
        cli.riot_client.get_summoner_data.return_value = {"puuid": "test_puuid"}
        
        # Mock user input
        with patch('builtins.input', side_effect=[
            "TestPlayer",  # player name
            "TestSummoner#NA1",  # riot id
            "5",  # top preference
            "4",  # jungle preference  
            "3",  # middle preference
            "2",  # support preference
            "1"   # bottom preference
        ]):
            cli._add_player()
        
        # Verify player was saved
        cli.data_manager.save_player_data.assert_called_once()
        saved_players = cli.data_manager.save_player_data.call_args[0][0]
        assert len(saved_players) == 1
        assert saved_players[0].name == "TestPlayer"
        assert saved_players[0].summoner_name == "TestSummoner#NA1"
        assert saved_players[0].role_preferences["top"] == 5
    
    def test_add_player_duplicate_name(self, cli, sample_players):
        """Test adding player with duplicate name."""
        # Mock the get_player_by_name to return existing player first, then None
        cli.data_manager.get_player_by_name.side_effect = [sample_players[0], None]
        
        with patch('builtins.input', side_effect=[
            "Player1",  # duplicate name
            "NewPlayer",  # new unique name
            "NewSummoner#NA1",  # riot id
            "", "", "", "", ""  # default preferences
        ]):
            with patch('builtins.print') as mock_print:
                cli.riot_client.get_summoner_data.return_value = {"puuid": "new_puuid"}
                cli.data_manager.load_player_data.return_value = []
                cli._add_player()
                
                # Check that duplicate warning was printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("already exists" in call for call in print_calls)
    
    def test_remove_player_success(self, cli, sample_players):
        """Test successful player removal."""
        cli.data_manager.load_player_data.return_value = sample_players
        cli.data_manager.delete_player.return_value = True
        
        with patch('builtins.input', side_effect=["1", "y"]):  # select first player, confirm
            cli._remove_player()
        
        cli.data_manager.delete_player.assert_called_once_with("Player1")
    
    def test_remove_player_cancel(self, cli, sample_players):
        """Test canceling player removal."""
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["0"]):  # cancel
            cli._remove_player()
        
        cli.data_manager.delete_player.assert_not_called()
    
    def test_list_players_empty(self, cli):
        """Test listing players when none exist."""
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.print') as mock_print:
            cli._list_players()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("No players found" in call for call in print_calls)
    
    def test_list_players_with_data(self, cli, sample_players):
        """Test listing players with data."""
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.print') as mock_print:
            cli._list_players()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            # Check that player names appear in output
            assert any("Player1" in call for call in print_calls)
            assert any("Player2" in call for call in print_calls)


class TestPreferenceManagement:
    """Test role preference management workflows."""
    
    def test_update_preferences_success(self, cli, sample_players):
        """Test successful preference update."""
        player = sample_players[0]
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=[
            "1",  # select first player
            "5",  # top preference
            "",   # jungle (keep current)
            "1",  # middle preference
            "",   # support (keep current)
            ""    # bottom (keep current)
        ]):
            cli._manage_preferences()
        
        # Verify preferences were updated
        cli.data_manager.update_preferences.assert_called_once()
        call_args = cli.data_manager.update_preferences.call_args
        assert call_args[0][0] == "Player1"  # player name
        updated_prefs = call_args[0][1]
        assert updated_prefs["top"] == 5
        assert updated_prefs["middle"] == 1
    
    def test_update_preferences_invalid_input(self, cli, sample_players):
        """Test handling invalid preference input."""
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=[
            "1",    # select first player
            "10",   # invalid preference (too high)
            "0",    # invalid preference (too low)
            "abc",  # invalid preference (not number)
            "3",    # valid preference
            "", "", "", ""  # rest default
        ]):
            with patch('builtins.print') as mock_print:
                cli._manage_preferences()
                
                # Check that error messages were printed
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("between 1-5" in call for call in print_calls)
    
    def test_preferences_no_players(self, cli):
        """Test preference management with no players."""
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.print') as mock_print:
            cli._manage_preferences()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("No players found" in call for call in print_calls)


class TestTeamOptimization:
    """Test team optimization workflows."""
    
    def test_optimize_team_success(self, cli, sample_players, sample_optimization_result):
        """Test successful team optimization."""
        cli.data_manager.load_player_data.return_value = sample_players
        cli.optimizer.optimize_team.return_value = sample_optimization_result
        
        with patch('builtins.input', side_effect=["n"]):  # don't show alternatives
            with patch('builtins.print') as mock_print:
                cli._optimize_team()
                
                # Verify optimization was called
                cli.optimizer.optimize_team.assert_called_once_with(sample_players)
                
                # Check that results were displayed
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("OPTIMAL TEAM COMPOSITION" in call for call in print_calls)
                assert any("85.5" in call for call in print_calls)  # total score
    
    def test_optimize_team_insufficient_players(self, cli):
        """Test optimization with insufficient players."""
        cli.data_manager.load_player_data.return_value = [
            Player("Player1", "Summoner1"),
            Player("Player2", "Summoner2")
        ]
        
        with patch('builtins.print') as mock_print:
            cli._optimize_team()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Need at least 5 players" in call for call in print_calls)
    
    def test_optimize_team_with_alternatives(self, cli, sample_players, sample_optimization_result):
        """Test showing alternative team compositions."""
        # Add alternative assignment
        alt_assignment = TeamAssignment(
            assignments={
                "top": "Player2",
                "jungle": "Player1", 
                "middle": "Player3",
                "support": "Player4",
                "bottom": "Player5"
            },
            total_score=82.1,
            individual_scores={"Player1": 16.0, "Player2": 17.0, "Player3": 18.0, "Player4": 15.5, "Player5": 17.6},
            champion_recommendations={
                "top": [],
                "jungle": [],
                "middle": [],
                "support": [],
                "bottom": []
            },
            explanation="Alternative assignment"
        )
        sample_optimization_result.assignments.append(alt_assignment)
        
        cli.data_manager.load_player_data.return_value = sample_players
        cli.optimizer.optimize_team.return_value = sample_optimization_result
        cli.optimizer.get_alternative_assignments.return_value = [alt_assignment]
        cli.optimizer.compare_assignments.return_value = "Comparison text\n\nRole changes here"
        
        with patch('builtins.input', side_effect=["n", "n", "y"]):  # no champion analysis, no trends, show alternatives
            with patch('builtins.print') as mock_print:
                cli._optimize_team()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Alternative #1" in call for call in print_calls)
    
    def test_optimize_team_player_selection(self, cli, sample_players):
        """Test player selection for optimization with more than 5 players."""
        # Add extra players
        extra_players = sample_players + [
            Player("Player6", "Summoner6"),
            Player("Player7", "Summoner7")
        ]
        cli.data_manager.load_player_data.return_value = extra_players
        
        # Mock optimization result
        result = OptimizationResult(
            assignments=[TeamAssignment()],
            best_assignment=TeamAssignment(),
            optimization_time=1.0
        )
        cli.optimizer.optimize_team.return_value = result
        
        with patch('builtins.input', side_effect=["1 2 3 4 5", "n"]):  # select first 5 players
            cli._optimize_team()
            
            # Verify optimization was called with selected players
            cli.optimizer.optimize_team.assert_called_once()
            called_players = cli.optimizer.optimize_team.call_args[0][0]
            assert len(called_players) == 5
            assert all(p.name in ["Player1", "Player2", "Player3", "Player4", "Player5"] for p in called_players)
    
    def test_optimize_team_error_handling(self, cli, sample_players):
        """Test error handling during optimization."""
        cli.data_manager.load_player_data.return_value = sample_players
        cli.optimizer.optimize_team.side_effect = Exception("API Error")
        
        with patch('builtins.print') as mock_print:
            cli._optimize_team()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Optimization failed" in call for call in print_calls)
            assert any("API Error" in call for call in print_calls)


class TestPlayerDataViewer:
    """Test player data viewing functionality."""
    
    def test_view_player_data_success(self, cli, sample_players):
        """Test viewing detailed player data."""
        player = sample_players[0]
        player.performance_cache = {
            "top": {"win_rate": 0.65, "avg_kda": 2.1, "matches_played": 20}
        }
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["1"]):  # select first player
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("PLAYER DETAILS: PLAYER1" in call for call in print_calls)
                assert any("Summoner1" in call for call in print_calls)
                assert any("ROLE PREFERENCES" in call for call in print_calls)
    
    def test_view_player_data_no_players(self, cli):
        """Test viewing player data when none exist."""
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.print') as mock_print:
            cli._view_player_data()
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("No players found" in call for call in print_calls)


class TestSystemMaintenance:
    """Test system maintenance functionality."""
    
    def test_clear_expired_cache(self, cli):
        """Test clearing expired cache files."""
        cli.data_manager.clear_expired_cache.return_value = 5
        
        with patch('builtins.input', side_effect=["1", "", "9"]):  # clear expired cache, continue, exit
            with patch('builtins.print') as mock_print:
                cli._system_maintenance()
                
                cli.data_manager.clear_expired_cache.assert_called_once()
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Removed 5 expired" in call for call in print_calls)
    
    def test_view_cache_statistics(self, cli):
        """Test viewing cache statistics."""
        cli.data_manager.get_cache_size_mb.return_value = 15.5
        cli.config.max_cache_size_mb = 50.0
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.input', side_effect=["2", "", "9"]):  # view cache stats, continue, exit
            with patch('builtins.print') as mock_print:
                cli._system_maintenance()
                
                # Check that the system statistics method was called
                cli.data_manager.get_cache_size_mb.assert_called()
    
    def test_cleanup_cache(self, cli):
        """Test cache cleanup functionality."""
        cli.data_manager.get_cache_size_mb.return_value = 25.0
        
        with patch('builtins.input', side_effect=["3", "", "9"]):  # cleanup cache, continue, exit
            with patch('builtins.print') as mock_print:
                cli._system_maintenance()
                
                cli.data_manager.cleanup_cache_if_needed.assert_called_once()
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Cache cleanup complete" in call for call in print_calls)


class TestInputValidation:
    """Test input validation and error handling."""
    
    def test_select_player_invalid_input(self, cli, sample_players):
        """Test player selection with invalid input."""
        with patch('builtins.input', side_effect=["abc", "10", "0"]):  # invalid, out of range, cancel
            result = cli._select_player(sample_players, "test")
            assert result is None
    
    def test_select_player_valid_input(self, cli, sample_players):
        """Test player selection with valid input."""
        with patch('builtins.input', side_effect=["2"]):  # select second player
            result = cli._select_player(sample_players, "test")
            assert result == sample_players[1]
    
    def test_main_menu_invalid_choice(self, cli):
        """Test main menu with invalid choice."""
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.input', side_effect=["abc", "10", "6"]):  # invalid inputs, then exit
            with patch('builtins.print') as mock_print:
                cli.main()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("Invalid choice" in call for call in print_calls)


class TestIntegrationWorkflows:
    """Test complete user workflows end-to-end."""
    
    def test_complete_workflow_add_players_and_optimize(self, cli):
        """Test complete workflow: add players, set preferences, optimize."""
        # Test adding a player
        cli.data_manager.get_player_by_name.return_value = None
        cli.data_manager.load_player_data.return_value = []
        cli.riot_client.get_summoner_data.return_value = {"puuid": "test_puuid"}
        
        with patch('builtins.input', side_effect=[
            "TestPlayer", "TestSummoner#NA1", "", "", "", "", ""
        ]):
            cli._add_player()
        
        # Verify player was saved
        cli.data_manager.save_player_data.assert_called_once()
        
        # Test optimization with 5 players
        players = [Player(f"Player{i}", f"Summoner{i}") for i in range(1, 6)]
        cli.data_manager.load_player_data.return_value = players
        
        result = OptimizationResult(
            assignments=[TeamAssignment(
                assignments={"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"},
                total_score=80.0
            )],
            best_assignment=TeamAssignment(
                assignments={"top": "Player1", "jungle": "Player2", "middle": "Player3", "support": "Player4", "bottom": "Player5"},
                total_score=80.0
            ),
            optimization_time=1.0
        )
        cli.optimizer.optimize_team.return_value = result
        
        with patch('builtins.input', side_effect=["n"]):  # don't show alternatives
            cli._optimize_team()
        
        # Verify optimization was called
        cli.optimizer.optimize_team.assert_called_once()
    
    def test_error_recovery_workflow(self, cli, sample_players):
        """Test error recovery in workflows."""
        cli.data_manager.load_player_data.return_value = sample_players
        cli.optimizer.optimize_team.side_effect = Exception("Network error")
        
        with patch('builtins.print') as mock_print:
            cli._optimize_team()
            
            # Check that error was handled gracefully
            print_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Optimization failed" in call for call in print_calls)
            assert any("Network error" in call for call in print_calls)


class TestChampionDisplayFeatures:
    """Test enhanced champion display features in CLI."""
    
    def test_display_optimization_results_with_champion_recommendations(self, cli, sample_optimization_result):
        """Test that optimization results display champion recommendations."""
        from lol_team_optimizer.models import ChampionRecommendation
        
        # Add champion recommendations to the result
        sample_optimization_result.best_assignment.champion_recommendations = {
            "top": [
                ChampionRecommendation(
                    champion_id=1,
                    champion_name="Garen",
                    mastery_level=7,
                    mastery_points=150000,
                    role_suitability=0.9,
                    confidence=0.85
                ),
                ChampionRecommendation(
                    champion_id=2,
                    champion_name="Darius",
                    mastery_level=6,
                    mastery_points=80000,
                    role_suitability=0.8,
                    confidence=0.75
                )
            ],
            "jungle": [],
            "middle": [],
            "support": [],
            "bottom": []
        }
        
        with patch('builtins.print') as mock_print:
            cli._display_optimization_results(sample_optimization_result)
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            
            # Check that champion recommendations are displayed
            assert any("Recommended Champions" in call for call in print_calls)
            assert any("Garen" in call for call in print_calls)
            assert any("Level 7" in call for call in print_calls)
            assert any("150,000 pts" in call for call in print_calls)
            assert any("Excellent" in call for call in print_calls)  # suitability description
    
    def test_enhanced_player_data_viewer_menu(self, cli, sample_players):
        """Test the enhanced player data viewer menu options."""
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["5"]):  # Exit menu
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check that new menu options are displayed
                assert any("Champion Analysis Across All Players" in call for call in print_calls)
                assert any("Role Suitability Analysis" in call for call in print_calls)
                assert any("Champion Pool Comparison" in call for call in print_calls)
    
    def test_individual_player_data_with_champion_mastery(self, cli, sample_players):
        """Test individual player data display with champion mastery information."""
        from lol_team_optimizer.models import ChampionMastery
        from datetime import datetime, timedelta
        
        # Add champion mastery data to a player
        player = sample_players[0]
        player.champion_masteries = {
            1: ChampionMastery(
                champion_id=1,
                champion_name="Garen",
                mastery_level=7,
                mastery_points=150000,
                chest_granted=True,
                tokens_earned=2,
                primary_roles=["top"],
                last_play_time=datetime.now() - timedelta(days=1)
            ),
            2: ChampionMastery(
                champion_id=2,
                champion_name="Darius", 
                mastery_level=6,
                mastery_points=80000,
                chest_granted=False,
                tokens_earned=1,
                primary_roles=["top"],
                last_play_time=datetime.now() - timedelta(days=7)
            )
        }
        player.role_champion_pools = {
            "top": [1, 2],
            "jungle": [],
            "middle": [],
            "support": [],
            "bottom": []
        }
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["1", "1", "4", "5"]):  # Individual player, select first, return, exit menu
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check champion mastery display
                assert any("CHAMPION MASTERY BY ROLE" in call for call in print_calls)
                assert any("Garen" in call for call in print_calls)
                assert any("Level 7" in call for call in print_calls)
                assert any("150,000 points" in call for call in print_calls)
                assert any("Chest earned" in call for call in print_calls)
                assert any("played yesterday" in call for call in print_calls)
                assert any("CHAMPION POOL ANALYSIS" in call for call in print_calls)
    
    def test_champion_recommendations_for_role(self, cli, sample_players):
        """Test champion recommendations for a specific role."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Setup player with champion mastery
        player = sample_players[0]
        player.champion_masteries = {
            1: ChampionMastery(
                champion_id=1,
                champion_name="Garen",
                mastery_level=7,
                mastery_points=150000,
                primary_roles=["top"]
            )
        }
        player.role_champion_pools = {"top": [1], "jungle": [], "middle": [], "support": [], "bottom": []}
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["1", "1", "1", "1", "5"]):  # Individual player, select first, champion recs, top role, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check champion recommendations display
                assert any("Champion Recommendations" in call for call in print_calls)
                assert any("Top" in call for call in print_calls)
                assert any("Garen" in call for call in print_calls)
                assert any("Excellent" in call for call in print_calls)  # recommendation strength
    
    def test_player_comparison_functionality(self, cli, sample_players):
        """Test player comparison functionality."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Setup players with different champion masteries
        player1 = sample_players[0]
        player1.champion_masteries = {
            1: ChampionMastery(champion_id=1, champion_name="Garen", mastery_level=7, mastery_points=150000, primary_roles=["top"])
        }
        
        player2 = sample_players[1]
        player2.champion_masteries = {
            1: ChampionMastery(champion_id=1, champion_name="Garen", mastery_level=5, mastery_points=50000, primary_roles=["top"]),
            2: ChampionMastery(champion_id=2, champion_name="Graves", mastery_level=6, mastery_points=80000, primary_roles=["jungle"])
        }
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["1", "1", "2", "1", "5"]):  # Individual player, select first, compare, select second, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check comparison display
                assert any("PLAYER COMPARISON" in call for call in print_calls)
                assert any("Role Preferences Comparison" in call for call in print_calls)
                assert any("Champion Pool Comparison" in call for call in print_calls)
                assert any("Common: Garen" in call for call in print_calls)
    
    def test_champion_analysis_all_players(self, cli, sample_players):
        """Test champion analysis across all players."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Setup multiple players with overlapping champions
        for i, player in enumerate(sample_players[:3]):
            player.champion_masteries = {
                1: ChampionMastery(
                    champion_id=1,
                    champion_name="Garen",
                    mastery_level=7 - i,
                    mastery_points=100000 - (i * 20000),
                    primary_roles=["top"]
                )
            }
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["2", "5"]):  # Champion analysis all players, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check analysis display
                assert any("CHAMPION ANALYSIS - ALL PLAYERS" in call for call in print_calls)
                assert any("Most Popular Champions" in call for call in print_calls)
                assert any("Role Coverage Analysis" in call for call in print_calls)
                assert any("Team Champion Overlap" in call for call in print_calls)
                assert any("Garen" in call for call in print_calls)
    
    def test_role_suitability_analysis(self, cli, sample_players):
        """Test role suitability analysis functionality."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Setup players with different role suitabilities
        for player in sample_players:
            player.champion_masteries = {
                1: ChampionMastery(
                    champion_id=1,
                    champion_name="Garen",
                    mastery_level=5,
                    mastery_points=50000,
                    primary_roles=["top"]
                )
            }
            player.role_champion_pools = {"top": [1], "jungle": [], "middle": [], "support": [], "bottom": []}
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["3", "5"]):  # Role suitability analysis, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check suitability analysis display
                assert any("ROLE SUITABILITY ANALYSIS" in call for call in print_calls)
                assert any("Role Suitability Matrix" in call for call in print_calls)
                assert any("Best Player for Each Role" in call for call in print_calls)
                assert any("Role Competition Analysis" in call for call in print_calls)
    
    def test_champion_pool_comparison(self, cli, sample_players):
        """Test champion pool comparison functionality."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Setup players with different pool sizes
        for i, player in enumerate(sample_players):
            masteries = {}
            for j in range(i + 1):  # Different pool sizes
                masteries[j] = ChampionMastery(
                    champion_id=j,
                    champion_name=f"Champion{j}",
                    mastery_level=5 + (j % 3),
                    mastery_points=50000 + (j * 10000),
                    primary_roles=["top"]
                )
            player.champion_masteries = masteries
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["4", "5"]):  # Champion pool comparison, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check pool comparison display
                assert any("CHAMPION POOL COMPARISON" in call for call in print_calls)
                assert any("Champion Pool Depth by Role" in call for call in print_calls)
                assert any("Mastery Level Distribution" in call for call in print_calls)
                assert any("Champion Overlap Analysis" in call for call in print_calls)
    
    def test_enhanced_main_menu_display(self, cli):
        """Test that the enhanced main menu displays new features."""
        cli.data_manager.load_player_data.return_value = []
        
        with patch('builtins.input', side_effect=["6"]):  # Exit
            with patch('builtins.print') as mock_print:
                cli.main()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check enhanced menu display
                assert any("View Player Data & Champion Analysis" in call for call in print_calls)
                assert any("New Features:" in call for call in print_calls)
                assert any("Champion mastery integration" in call for call in print_calls)
                assert any("Champion recommendations" in call for call in print_calls)
                assert any("Enhanced player analysis" in call for call in print_calls)
    
    def test_optimization_results_with_empty_champion_recommendations(self, cli, sample_optimization_result):
        """Test optimization results display when no champion recommendations are available."""
        # Ensure empty champion recommendations
        sample_optimization_result.best_assignment.champion_recommendations = {
            role: [] for role in ["top", "jungle", "middle", "support", "bottom"]
        }
        
        with patch('builtins.print') as mock_print:
            cli._display_optimization_results(sample_optimization_result)
            
            print_calls = [str(call) for call in mock_print.call_args_list]
            
            # Check that "no recommendations" message is displayed
            assert any("No champion recommendations available" in call for call in print_calls)
    
    def test_champion_mastery_display_with_time_information(self, cli, sample_players):
        """Test champion mastery display includes time-based information."""
        from lol_team_optimizer.models import ChampionMastery
        from datetime import datetime, timedelta
        
        player = sample_players[0]
        player.champion_masteries = {
            1: ChampionMastery(
                champion_id=1,
                champion_name="Garen",
                mastery_level=7,
                mastery_points=150000,
                primary_roles=["top"],
                last_play_time=datetime.now()  # Played today
            ),
            2: ChampionMastery(
                champion_id=2,
                champion_name="Darius",
                mastery_level=6,
                mastery_points=80000,
                primary_roles=["top"],
                last_play_time=datetime.now() - timedelta(days=30)  # Played a month ago
            )
        }
        player.role_champion_pools = {"top": [1, 2], "jungle": [], "middle": [], "support": [], "bottom": []}
        
        cli.data_manager.load_player_data.return_value = sample_players
        
        with patch('builtins.input', side_effect=["1", "1", "4", "5"]):  # Individual player, select first, return, exit
            with patch('builtins.print') as mock_print:
                cli._view_player_data()
                
                print_calls = [str(call) for call in mock_print.call_args_list]
                
                # Check time-based information
                assert any("played today" in call for call in print_calls)
                assert any("month" in call for call in print_calls)


if __name__ == "__main__":
    pytest.main([__file__])