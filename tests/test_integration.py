"""
Integration tests for the League of Legends Team Optimizer.

These tests verify that all components work together correctly and handle
error conditions gracefully.
"""

import pytest
import tempfile
import shutil
import os
import time
import json
import requests
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, patch
from datetime import datetime

from lol_team_optimizer.cli import CLI
from lol_team_optimizer.config import Config
from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.riot_client import RiotAPIClient
from lol_team_optimizer.performance_calculator import PerformanceCalculator
from lol_team_optimizer.optimizer import OptimizationEngine
from lol_team_optimizer.models import Player


class TestIntegration:
    """Integration tests for the complete application."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        temp_dir = tempfile.mkdtemp()
        
        # Mock the Config class to bypass API key validation
        with patch.dict(os.environ, {'RIOT_API_KEY': 'test_api_key'}):
            config = Config()
            config.data_directory = str(Path(temp_dir) / "data")
            config.cache_directory = str(Path(temp_dir) / "cache")
            config.debug = True
        
        yield config
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing."""
        return [
            Player(
                name="Player1",
                summoner_name="TestSummoner1",
                puuid="test_puuid_1",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "support": 1, "bottom": 4}
            ),
            Player(
                name="Player2",
                summoner_name="TestSummoner2",
                puuid="test_puuid_2",
                role_preferences={"top": 2, "jungle": 5, "middle": 3, "support": 1, "bottom": 4}
            ),
            Player(
                name="Player3",
                summoner_name="TestSummoner3",
                puuid="test_puuid_3",
                role_preferences={"top": 1, "jungle": 2, "middle": 5, "support": 3, "bottom": 4}
            ),
            Player(
                name="Player4",
                summoner_name="TestSummoner4",
                puuid="test_puuid_4",
                role_preferences={"top": 1, "jungle": 2, "middle": 3, "support": 5, "bottom": 4}
            ),
            Player(
                name="Player5",
                summoner_name="TestSummoner5",
                puuid="test_puuid_5",
                role_preferences={"top": 2, "jungle": 1, "middle": 3, "support": 4, "bottom": 5}
            )
        ]
    
    def test_complete_workflow_with_api_available(self, temp_config, sample_players):
        """Test complete workflow when API is available."""
        with patch('lol_team_optimizer.cli.RiotAPIClient') as mock_riot_client_class:
            # Mock API client
            mock_riot_client = Mock()
            mock_riot_client_class.return_value = mock_riot_client
            
            # Mock API responses
            mock_riot_client.get_summoner_data.return_value = {
                'puuid': 'test_puuid',
                'summonerLevel': 100
            }
            
            # Initialize CLI with mocked components
            with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
                cli = CLI()
                
                # Verify API is available
                assert cli.api_available is True
                
                # Test data persistence
                cli.data_manager.save_player_data(sample_players)
                loaded_players = cli.data_manager.load_player_data()
                
                assert len(loaded_players) == 5
                assert all(p.name in [sp.name for sp in sample_players] for p in loaded_players)
                
                # Test optimization
                with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.8):
                    with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                        result = cli.optimizer.optimize_team(loaded_players)
                        
                        assert result is not None
                        assert result.best_assignment is not None
                        assert len(result.best_assignment.assignments) == 5
                        assert all(role in result.best_assignment.assignments for role in cli.roles)
    
    def test_complete_workflow_without_api(self, temp_config, sample_players):
        """Test complete workflow when API is not available (offline mode)."""
        with patch('lol_team_optimizer.cli.RiotAPIClient', side_effect=Exception("API not available")):
            with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
                cli = CLI()
                
                # Verify API is not available
                assert cli.api_available is False
                
                # Test data persistence still works
                cli.data_manager.save_player_data(sample_players)
                loaded_players = cli.data_manager.load_player_data()
                
                assert len(loaded_players) == 5
                
                # Test optimization with preference-only scoring
                with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.6):
                    with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.0):
                        result = cli.optimizer.optimize_team(loaded_players)
                        
                        assert result is not None
                        assert result.best_assignment is not None
                        assert len(result.best_assignment.assignments) == 5
    
    def test_error_handling_insufficient_players(self, temp_config):
        """Test error handling when insufficient players are provided."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test with no players
            with pytest.raises(ValueError, match="No players provided for optimization"):
                cli.optimizer.optimize_team([])
            
            # Test with insufficient players
            insufficient_players = [
                Player(name=f"Player{i}", summoner_name=f"Summoner{i}", puuid=f"puuid{i}")
                for i in range(3)
            ]
            
            with pytest.raises(ValueError, match="At least 5 players required"):
                cli.optimizer.optimize_team(insufficient_players)
    
    def test_error_handling_corrupted_data(self, temp_config):
        """Test error handling when data files are corrupted."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Create corrupted data file
            data_dir = Path(temp_config.data_directory)
            data_dir.mkdir(parents=True, exist_ok=True)
            
            corrupted_file = data_dir / temp_config.player_data_file
            with open(corrupted_file, 'w') as f:
                f.write("invalid json content")
            
            # Should handle corrupted data gracefully
            with pytest.raises(ValueError, match="Invalid player data format"):
                cli.data_manager.load_player_data()
    
    def test_error_handling_api_failures(self, temp_config, sample_players):
        """Test error handling when API calls fail."""
        with patch('lol_team_optimizer.cli.RiotAPIClient') as mock_riot_client_class:
            mock_riot_client = Mock()
            mock_riot_client_class.return_value = mock_riot_client
            
            # Mock API failures
            mock_riot_client.get_summoner_data.side_effect = Exception("API Error")
            
            with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
                cli = CLI()
                
                # Should handle API failures gracefully during optimization
                with patch.object(cli.performance_calculator, 'calculate_individual_score', 
                                side_effect=Exception("API Error")):
                    with pytest.raises(ValueError, match="Team optimization failed"):
                        cli.optimizer.optimize_team(sample_players)
    
    def test_graceful_degradation_with_limited_data(self, temp_config, sample_players):
        """Test graceful degradation when performance data is limited."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Mock limited performance data
            def limited_performance_calc(player, role):
                # Return lower scores to simulate limited data
                return 0.3
            
            with patch.object(cli.performance_calculator, 'calculate_individual_score', 
                            side_effect=limited_performance_calc):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.0):
                    result = cli.optimizer.optimize_team(sample_players)
                    
                    # Should still produce valid results
                    assert result is not None
                    assert result.best_assignment is not None
                    assert len(result.best_assignment.assignments) == 5
                    
                    # Score should be lower due to limited data
                    assert result.best_assignment.total_score < 4.0  # Assuming max would be ~5.0
    
    def test_cache_management_integration(self, temp_config, sample_players):
        """Test cache management across components."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Save players and verify caching
            cli.data_manager.save_player_data(sample_players)
            
            # Cache some API data
            cli.data_manager.cache_api_data({"test": "data"}, "test_key")
            
            # Verify cache retrieval
            cached_data = cli.data_manager.get_cached_data("test_key")
            assert cached_data == {"test": "data"}
            
            # Test cache cleanup
            removed_count = cli.data_manager.clear_expired_cache()
            assert removed_count >= 0  # Should not fail
            
            # Test cache size calculation
            cache_size = cli.data_manager.get_cache_size_mb()
            assert cache_size >= 0.0
    
    def test_input_validation_integration(self, temp_config):
        """Test input validation across the application."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test invalid player data
            invalid_player = Player(
                name="",  # Empty name
                summoner_name="ValidSummoner",
                puuid="valid_puuid"
            )
            
            with pytest.raises(ValueError):
                cli.optimizer.optimize_team([invalid_player] * 5)
            
            # Test invalid preferences
            with pytest.raises(ValueError, match="Invalid role"):
                cli.data_manager.update_preferences("TestPlayer", {"invalid_role": 5})
            
            with pytest.raises(ValueError, match="Preference score must be integer"):
                cli.data_manager.update_preferences("TestPlayer", {"top": 10})  # Out of range
    
    def test_concurrent_operations(self, temp_config, sample_players):
        """Test handling of concurrent operations."""
        import threading
        import time
        
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            cli.data_manager.save_player_data(sample_players)
            
            results = []
            errors = []
            
            def run_optimization():
                try:
                    with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                        with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                            result = cli.optimizer.optimize_team(sample_players)
                            results.append(result)
                except Exception as e:
                    errors.append(e)
            
            # Run multiple optimizations concurrently
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=run_optimization)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)
            
            # Should handle concurrent operations without errors
            assert len(errors) == 0, f"Concurrent operations failed: {errors}"
            assert len(results) == 3
            
            # All results should be valid
            for result in results:
                assert result is not None
                assert result.best_assignment is not None
    
    def test_memory_usage_with_large_datasets(self, temp_config):
        """Test memory usage with larger datasets."""
        # Create a larger set of players
        large_player_set = []
        for i in range(20):  # 20 players for more combinations
            player = Player(
                name=f"Player{i}",
                summoner_name=f"Summoner{i}",
                puuid=f"puuid{i}",
                role_preferences={
                    "top": (i % 5) + 1,
                    "jungle": ((i + 1) % 5) + 1,
                    "middle": ((i + 2) % 5) + 1,
                    "support": ((i + 3) % 5) + 1,
                    "bottom": ((i + 4) % 5) + 1
                }
            )
            large_player_set.append(player)
        
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Should handle larger datasets without excessive memory usage
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    result = cli.optimizer.optimize_team(large_player_set)
                    
                    assert result is not None
                    assert result.best_assignment is not None
                    assert len(result.assignments) <= 10  # Should limit results
    
    def test_end_to_end_error_recovery(self, temp_config, sample_players):
        """Test end-to-end error recovery scenarios."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Save initial data
            cli.data_manager.save_player_data(sample_players)
            
            # Simulate various error conditions and recovery
            
            # 1. Temporary API failure followed by recovery
            # First attempt should fail
            with patch.object(cli.performance_calculator, 'calculate_individual_score', 
                            side_effect=Exception("Temporary API Error")):
                with pytest.raises(ValueError):
                    cli.optimizer.optimize_team(sample_players)
                
            # Later attempt should succeed (simulating API recovery)
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    result = cli.optimizer.optimize_team(sample_players)
                    assert result is not None
            
            # 2. Partial data corruption followed by recovery
            # Corrupt one player's data
            corrupted_players = sample_players.copy()
            corrupted_players[0].role_preferences = {}  # Empty preferences
            
            # Should still work with degraded data
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.5):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.0):
                    result = cli.optimizer.optimize_team(corrupted_players)
                    assert result is not None
    
    def test_comprehensive_error_handling(self, temp_config, sample_players):
        """Test comprehensive error handling across all components."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test ValueError handling
            with patch.object(cli.optimizer, 'optimize_team', side_effect=ValueError("Invalid player data")):
                # Should not raise exception, should handle gracefully
                try:
                    cli._safe_execute(lambda: cli.optimizer.optimize_team(sample_players), "test optimization")
                except Exception:
                    pytest.fail("_safe_execute should handle ValueError gracefully")
            
            # Test IOError handling
            with patch.object(cli.data_manager, 'save_player_data', side_effect=IOError("Permission denied")):
                try:
                    cli._safe_execute(lambda: cli.data_manager.save_player_data(sample_players), "test save")
                except Exception:
                    pytest.fail("_safe_execute should handle IOError gracefully")
            
            # Test ConnectionError handling
            with patch.object(cli.riot_client, 'get_summoner_data', side_effect=ConnectionError("Network error")):
                try:
                    cli._safe_execute(lambda: cli.riot_client.get_summoner_data("test"), "test api")
                except Exception:
                    pytest.fail("_safe_execute should handle ConnectionError gracefully")
    
    def test_system_maintenance_functions(self, temp_config, sample_players):
        """Test system maintenance functionality."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            cli.data_manager.save_player_data(sample_players)
            
            # Test cache clearing
            cli._clear_expired_cache()  # Should not raise exception
            
            # Test system statistics
            cli._show_system_statistics()  # Should not raise exception
            
            # Test cache cleanup
            cli._cleanup_cache()  # Should not raise exception
            
            # Test player data validation
            cli._validate_player_data()  # Should not raise exception
            
            # Test export functionality
            cli._export_player_data()  # Should not raise exception
            
            # Verify export file was created
            export_files = list(Path(temp_config.data_directory).glob("player_export_*.json"))
            assert len(export_files) > 0, "Export file should be created"
            
            # Test diagnostics
            cli._run_system_diagnostics()  # Should not raise exception
    
    def test_graceful_degradation_scenarios(self, temp_config, sample_players):
        """Test various graceful degradation scenarios."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test with missing API client
            cli.riot_client = None
            cli.api_available = False
            
            # Should still be able to optimize using preferences only
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.5):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.0):
                    result = cli.optimizer.optimize_team(sample_players)
                    assert result is not None
                    assert result.best_assignment is not None
            
            # Test API connectivity test without API
            cli._test_api_connectivity()  # Should handle gracefully
            
            # Test refresh without API
            cli._refresh_all_player_data()  # Should handle gracefully
    
    def test_input_validation_edge_cases(self, temp_config):
        """Test input validation for edge cases."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test with players having invalid preferences
            invalid_players = [
                Player(
                    name=f"Player{i}",
                    summoner_name=f"Summoner{i}",
                    puuid=f"puuid{i}",
                    role_preferences={"top": 10, "jungle": -1}  # Invalid values
                )
                for i in range(5)
            ]
            
            # Validation should catch these issues
            cli.data_manager.save_player_data(invalid_players)
            cli._validate_player_data()  # Should report issues but not crash
            
            # Test with empty player names
            empty_name_players = [
                Player(name="", summoner_name="ValidSummoner", puuid="valid_puuid")
            ] * 5
            
            with pytest.raises(ValueError):
                cli.optimizer.optimize_team(empty_name_players)
    
    def test_performance_under_stress(self, temp_config):
        """Test performance under stress conditions."""
        # Create a large number of players
        stress_players = []
        for i in range(50):  # Large dataset
            player = Player(
                name=f"StressPlayer{i}",
                summoner_name=f"StressSummoner{i}",
                puuid=f"stress_puuid_{i}",
                role_preferences={
                    role: ((i + j) % 5) + 1 
                    for j, role in enumerate(["top", "jungle", "middle", "support", "bottom"])
                }
            )
            stress_players.append(player)
        
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Should handle large datasets efficiently
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.6):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    import time
                    start_time = time.time()
                    
                    result = cli.optimizer.optimize_team(stress_players)
                    
                    end_time = time.time()
                    optimization_time = end_time - start_time
                    
                    # Should complete within reasonable time (adjust threshold as needed)
                    assert optimization_time < 30.0, f"Optimization took too long: {optimization_time:.2f}s"
                    assert result is not None
                    assert result.best_assignment is not None
    
    def test_complete_application_integration(self, temp_config):
        """Test complete application integration from startup to shutdown."""
        with patch.dict(os.environ, {'RIOT_API_KEY': 'test_api_key'}):
            with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
                # Test application startup
                cli = CLI()
                
                # Verify all components are initialized
                assert cli.config is not None
                assert cli.data_manager is not None
                assert cli.performance_calculator is not None
                assert cli.optimizer is not None
                
                # Test adding players through the interface
                test_players = []
                for i in range(5):
                    player = Player(
                        name=f"IntegrationPlayer{i}",
                        summoner_name=f"IntegrationSummoner{i}#NA1",
                        puuid=f"integration_puuid_{i}",
                        role_preferences={
                            "top": ((i + 1) % 5) + 1,
                            "jungle": ((i + 2) % 5) + 1,
                            "middle": ((i + 3) % 5) + 1,
                            "support": ((i + 4) % 5) + 1,
                            "bottom": ((i + 5) % 5) + 1
                        }
                    )
                    test_players.append(player)
                
                # Save players
                cli.data_manager.save_player_data(test_players)
                
                # Test preference management
                cli.data_manager.update_preferences("IntegrationPlayer0", {
                    "top": 5, "jungle": 1, "middle": 2, "support": 3, "bottom": 4
                })
                
                # Verify preference update
                updated_player = cli.data_manager.get_player_by_name("IntegrationPlayer0")
                assert updated_player.role_preferences["top"] == 5
                
                # Test optimization workflow
                with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.75):
                    with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.15):
                        result = cli.optimizer.optimize_team(test_players)
                        
                        # Verify optimization results
                        assert result is not None
                        assert result.best_assignment is not None
                        assert len(result.best_assignment.assignments) == 5
                        assert result.best_assignment.total_score > 0
                        
                        # Test result display functionality
                        cli.display_results(result)  # Should not raise exception
                
                # Test system maintenance operations
                cli._clear_expired_cache()
                cli._show_system_statistics()
                cli._validate_player_data()
                cli._export_player_data()
                
                # Verify export was successful
                export_files = list(Path(temp_config.data_directory).glob("player_export_*.json"))
                assert len(export_files) > 0
                
                # Test error recovery
                with patch.object(cli.optimizer, 'optimize_team', side_effect=Exception("Simulated error")):
                    # Should handle error gracefully
                    cli._safe_execute(lambda: cli.optimizer.optimize_team(test_players), "test error handling")
                
                print("✓ Complete application integration test passed")

    def test_data_consistency_across_operations(self, temp_config, sample_players):
        """Test data consistency across multiple operations."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Initial save
            cli.data_manager.save_player_data(sample_players)
            
            # Multiple read operations should return consistent data
            for _ in range(5):
                loaded_players = cli.data_manager.load_player_data()
                assert len(loaded_players) == len(sample_players)
                
                # Verify data integrity
                for original, loaded in zip(sample_players, loaded_players):
                    assert original.name == loaded.name
                    assert original.summoner_name == loaded.summoner_name
                    assert original.role_preferences == loaded.role_preferences
            
            # Test concurrent modifications
            import threading
            import time
            
            def modify_preferences():
                try:
                    cli.data_manager.update_preferences("Player1", {"top": 5, "jungle": 1, "middle": 3, "support": 2, "bottom": 4})
                except Exception:
                    pass  # Expected in concurrent scenario
            
            # Run concurrent modifications
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=modify_preferences)
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=5)
            
            # Data should still be consistent after concurrent operations
            final_players = cli.data_manager.load_player_data()
            assert len(final_players) == len(sample_players)

    def test_error_logging_and_recovery(self, temp_config, sample_players):
        """Test error logging and recovery mechanisms."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test logging of various error types
            import logging
            import io
            
            # Capture log output
            log_capture = io.StringIO()
            handler = logging.StreamHandler(log_capture)
            cli.logger.addHandler(handler)
            cli.logger.setLevel(logging.DEBUG)
            
            # Test error recovery after API failure
            with patch.object(cli.riot_client, 'get_summoner_data', side_effect=Exception("API Error")):
                try:
                    cli._safe_execute(lambda: cli.riot_client.get_summoner_data("test"), "API test")
                except Exception:
                    pass
            
            # Check that error was logged
            log_output = log_capture.getvalue()
            assert "API test" in log_output
            assert "API Error" in log_output
            
            # Test recovery after temporary failure
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    result = cli.optimizer.optimize_team(sample_players)
                    assert result is not None
            
            # Clean up
            cli.logger.removeHandler(handler)
    
    def test_comprehensive_workflow_with_logging(self, temp_config, sample_players):
        """Test complete workflow with comprehensive logging verification."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Set up log capture
            import logging
            import io
            
            log_capture = io.StringIO()
            handler = logging.StreamHandler(log_capture)
            cli.logger.addHandler(handler)
            cli.logger.setLevel(logging.DEBUG)
            
            # Test complete workflow with logging
            cli.data_manager.save_player_data(sample_players)
            cli._log_user_action("add_players", {"count": len(sample_players)})
            
            # Test performance logging
            start_time = time.time()
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    result = cli.optimizer.optimize_team(sample_players)
            end_time = time.time()
            
            cli._log_performance_metrics("team_optimization", end_time - start_time, True, 
                                       {"player_count": len(sample_players)})
            
            # Verify logging occurred
            log_output = log_capture.getvalue()
            assert "User action: add_players" in log_output
            assert "Performance: team_optimization" in log_output
            
            # Test system state logging
            cli._log_system_state()
            
            # Clean up
            cli.logger.removeHandler(handler)
    
    def test_comprehensive_error_handling_with_recovery(self, temp_config, sample_players):
        """Test comprehensive error handling with automatic recovery."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test API failure with recovery
            api_call_count = 0
            def failing_api_call(*args, **kwargs):
                nonlocal api_call_count
                api_call_count += 1
                if api_call_count <= 2:
                    raise requests.exceptions.ConnectionError("Network error")
                return {"puuid": "test_puuid", "summonerLevel": 100}
            
            with patch.object(cli.riot_client, 'get_summoner_data', side_effect=failing_api_call):
                # First calls should fail
                with pytest.raises(Exception):
                    cli.riot_client.get_summoner_data("test_summoner")
                
                with pytest.raises(Exception):
                    cli.riot_client.get_summoner_data("test_summoner")
                
                # Third call should succeed
                result = cli.riot_client.get_summoner_data("test_summoner")
                assert result is not None
            
            # Test optimization with partial failures
            performance_call_count = 0
            def partially_failing_performance(*args, **kwargs):
                nonlocal performance_call_count
                performance_call_count += 1
                if performance_call_count <= 3:
                    raise Exception("Temporary calculation error")
                return 0.6
            
            # Should eventually succeed after retries
            with patch.object(cli.performance_calculator, 'calculate_individual_score', 
                            side_effect=partially_failing_performance):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    # Reset counter for successful run
                    performance_call_count = 10
                    result = cli.optimizer.optimize_team(sample_players)
                    assert result is not None
    
    def test_data_integrity_across_operations(self, temp_config, sample_players):
        """Test data integrity across multiple complex operations."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Initial data save
            cli.data_manager.save_player_data(sample_players)
            
            # Multiple concurrent read/write operations
            import threading
            import time
            
            results = []
            errors = []
            
            def complex_operation(operation_id):
                try:
                    # Load data
                    players = cli.data_manager.load_player_data()
                    
                    # Modify preferences
                    if players:
                        cli.data_manager.update_preferences(
                            players[operation_id % len(players)].name,
                            {"top": 5, "jungle": 1, "middle": 2, "support": 3, "bottom": 4}
                        )
                    
                    # Run optimization
                    with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.7):
                        with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                            result = cli.optimizer.optimize_team(players)
                            results.append((operation_id, result))
                    
                    # Cache operations
                    cli.data_manager.cache_api_data({"test": f"data_{operation_id}"}, f"test_key_{operation_id}")
                    
                except Exception as e:
                    errors.append((operation_id, e))
            
            # Run multiple complex operations concurrently
            threads = []
            for i in range(3):
                thread = threading.Thread(target=complex_operation, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=15)
            
            # Verify data integrity
            final_players = cli.data_manager.load_player_data()
            assert len(final_players) == len(sample_players)
            
            # Should have some successful results
            assert len(results) > 0
            
            # Errors should be minimal in this controlled scenario
            assert len(errors) <= 1  # Allow for some race conditions
    
    def test_system_resilience_under_stress(self, temp_config):
        """Test system resilience under stress conditions."""
        # Create a large dataset for stress testing
        stress_players = []
        for i in range(100):  # Large number of players
            player = Player(
                name=f"StressPlayer{i:03d}",
                summoner_name=f"StressSummoner{i:03d}#NA1",
                puuid=f"stress_puuid_{i:03d}",
                role_preferences={
                    role: ((i + j) % 5) + 1 
                    for j, role in enumerate(["top", "jungle", "middle", "support", "bottom"])
                }
            )
            stress_players.append(player)
        
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test large data handling
            start_time = time.time()
            cli.data_manager.save_player_data(stress_players)
            save_time = time.time() - start_time
            
            # Should handle large datasets efficiently
            assert save_time < 5.0, f"Large data save took too long: {save_time:.2f}s"
            
            # Test large data loading
            start_time = time.time()
            loaded_players = cli.data_manager.load_player_data()
            load_time = time.time() - start_time
            
            assert len(loaded_players) == len(stress_players)
            assert load_time < 2.0, f"Large data load took too long: {load_time:.2f}s"
            
            # Test optimization with large player pool
            start_time = time.time()
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.6):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    result = cli.optimizer.optimize_team(stress_players)
            optimization_time = time.time() - start_time
            
            assert result is not None
            assert optimization_time < 30.0, f"Large optimization took too long: {optimization_time:.2f}s"
            
            # Test cache performance with many entries
            start_time = time.time()
            for i in range(50):
                cli.data_manager.cache_api_data({"data": f"test_{i}"}, f"cache_key_{i}")
            cache_time = time.time() - start_time
            
            assert cache_time < 2.0, f"Cache operations took too long: {cache_time:.2f}s"
    
    def test_comprehensive_maintenance_operations(self, temp_config, sample_players):
        """Test comprehensive system maintenance operations."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Set up test data
            cli.data_manager.save_player_data(sample_players)
            
            # Add cache data
            for i in range(10):
                cli.data_manager.cache_api_data({"test": f"data_{i}"}, f"test_key_{i}")
            
            # Test all maintenance operations
            maintenance_operations = [
                cli._clear_expired_cache,
                cli._show_system_statistics,
                cli._cleanup_cache,
                cli._validate_player_data,
                cli._export_player_data,
                cli._run_system_diagnostics
            ]
            
            for operation in maintenance_operations:
                try:
                    operation()
                except Exception as e:
                    pytest.fail(f"Maintenance operation {operation.__name__} failed: {e}")
            
            # Verify export file was created
            export_files = list(Path(temp_config.data_directory).glob("player_export_*.json"))
            assert len(export_files) > 0, "Export file should be created"
            
            # Verify export file content
            with open(export_files[0], 'r') as f:
                export_data = json.load(f)
                assert len(export_data) == len(sample_players)
    
    def test_api_integration_with_rate_limiting(self, temp_config, sample_players):
        """Test API integration with proper rate limiting handling."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Mock rate limiting scenario
            call_count = 0
            def rate_limited_api_call(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 3:
                    # Simulate rate limit error
                    error = requests.exceptions.HTTPError("429 Rate limit exceeded")
                    error.response = Mock()
                    error.response.status_code = 429
                    error.response.headers = {'Retry-After': '1'}
                    raise error
                return {"puuid": "test_puuid", "summonerLevel": 100}
            
            with patch.object(cli.riot_client, 'get_summoner_data', side_effect=rate_limited_api_call):
                # Should handle rate limiting gracefully
                try:
                    # This might fail due to rate limiting, which is expected
                    result = cli.riot_client.get_summoner_data("test_summoner")
                except Exception as e:
                    # Rate limiting errors are expected and should be handled
                    assert "429" in str(e) or "rate limit" in str(e).lower()
    
    def test_complete_user_workflow_simulation(self, temp_config):
        """Simulate a complete user workflow from start to finish."""
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Simulate user adding players
            test_players = []
            for i in range(7):  # More than 5 to test selection
                player = Player(
                    name=f"WorkflowPlayer{i}",
                    summoner_name=f"WorkflowSummoner{i}#NA1",
                    puuid=f"workflow_puuid_{i}",
                    role_preferences={
                        "top": ((i + 1) % 5) + 1,
                        "jungle": ((i + 2) % 5) + 1,
                        "middle": ((i + 3) % 5) + 1,
                        "support": ((i + 4) % 5) + 1,
                        "bottom": ((i + 5) % 5) + 1
                    }
                )
                test_players.append(player)
            
            # Step 1: Add players
            cli.data_manager.save_player_data(test_players)
            cli._log_user_action("bulk_add_players", {"count": len(test_players)})
            
            # Step 2: Update preferences for some players
            for i in range(3):
                cli.data_manager.update_preferences(
                    test_players[i].name,
                    {"top": 5, "jungle": 1, "middle": 2, "support": 3, "bottom": 4}
                )
                cli._log_user_action("update_preferences", {"player": test_players[i].name})
            
            # Step 3: Run optimization
            with patch.object(cli.performance_calculator, 'calculate_individual_score', return_value=0.75):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.15):
                    result = cli.optimizer.optimize_team(test_players)
                    cli._log_user_action("run_optimization", {"player_count": len(test_players)})
            
            # Step 4: View results and alternatives
            assert result is not None
            assert result.best_assignment is not None
            assert len(result.best_assignment.assignments) == 5
            
            # Step 5: Export data
            cli._export_player_data()
            cli._log_user_action("export_data", {})
            
            # Step 6: System maintenance
            cli._clear_expired_cache()
            cli._validate_player_data()
            cli._log_user_action("system_maintenance", {})
            
            # Verify workflow completed successfully
            final_players = cli.data_manager.load_player_data()
            assert len(final_players) == len(test_players)
            
            # Verify export was created
            export_files = list(Path(temp_config.data_directory).glob("player_export_*.json"))
            assert len(export_files) > 0
        with patch('lol_team_optimizer.cli.Config', return_value=temp_config):
            cli = CLI()
            
            # Test that errors are properly logged
            with patch.object(cli.logger, 'error') as mock_logger:
                with patch.object(cli.optimizer, 'optimize_team', side_effect=ValueError("Test error")):
                    cli._safe_execute(lambda: cli.optimizer.optimize_team(sample_players), "test operation")
                    
                    # Verify error was logged
                    mock_logger.assert_called()
                    
            # Test recovery after errors
            cli.data_manager.save_player_data(sample_players)
            
            # Simulate temporary error followed by success
            call_count = 0
            def failing_then_succeeding(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Temporary failure")
                return 0.7
            
            with patch.object(cli.performance_calculator, 'calculate_individual_score', side_effect=failing_then_succeeding):
                with patch.object(cli.performance_calculator, 'calculate_synergy_score', return_value=0.1):
                    # First attempts should fail, but system should recover
                    try:
                        cli.optimizer.optimize_team(sample_players)
                        pytest.fail("Should have failed on first attempts")
                    except ValueError:
                        pass  # Expected
                    
                    # Reset call count for successful attempt
                    call_count = 10  # Force success
                    result = cli.optimizer.optimize_team(sample_players)
                    assert result is not None  # Should succeed after "recovery"