"""
Unit tests for the DataManager class.

Tests data persistence, preference management, and cache functionality.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from lol_team_optimizer.data_manager import DataManager
from lol_team_optimizer.models import Player, PerformanceData
from lol_team_optimizer.config import Config


class TestDataManager:
    """Test cases for DataManager class."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                riot_api_key="test_key",
                data_directory=os.path.join(temp_dir, "data"),
                cache_directory=os.path.join(temp_dir, "cache"),
                player_data_file="test_players.json",
                cache_duration_hours=1,
                player_data_cache_hours=24,
                max_cache_size_mb=1
            )
            yield config
    
    @pytest.fixture
    def data_manager(self, temp_config):
        """Create a DataManager instance for testing."""
        return DataManager(temp_config)
    
    @pytest.fixture
    def sample_players(self):
        """Create sample player data for testing."""
        return [
            Player(
                name="TestPlayer1",
                summoner_name="TestSummoner1",
                puuid="test_puuid_1",
                role_preferences={"top": 5, "jungle": 3, "middle": 2, "support": 1, "bottom": 4},
                performance_cache={"top": {"win_rate": 0.65, "matches": 10}},
                last_updated=datetime(2024, 1, 1, 12, 0, 0)
            ),
            Player(
                name="TestPlayer2",
                summoner_name="TestSummoner2",
                puuid="test_puuid_2",
                role_preferences={"top": 2, "jungle": 5, "middle": 4, "support": 3, "bottom": 1},
                performance_cache={"jungle": {"win_rate": 0.70, "matches": 15}},
                last_updated=datetime(2024, 1, 2, 14, 30, 0)
            )
        ]
    
    def test_init_creates_directories(self, temp_config):
        """Test that DataManager creates necessary directories."""
        data_manager = DataManager(temp_config)
        
        assert Path(temp_config.data_directory).exists()
        assert Path(temp_config.cache_directory).exists()
    
    def test_save_and_load_player_data(self, data_manager, sample_players):
        """Test saving and loading player data."""
        # Save players
        data_manager.save_player_data(sample_players)
        
        # Load players
        loaded_players = data_manager.load_player_data()
        
        assert len(loaded_players) == 2
        
        # Check first player
        player1 = next(p for p in loaded_players if p.name == "TestPlayer1")
        assert player1.summoner_name == "TestSummoner1"
        assert player1.puuid == "test_puuid_1"
        assert player1.role_preferences["top"] == 5
        assert player1.performance_cache["top"]["win_rate"] == 0.65
        assert player1.last_updated == datetime(2024, 1, 1, 12, 0, 0)
        
        # Check second player
        player2 = next(p for p in loaded_players if p.name == "TestPlayer2")
        assert player2.summoner_name == "TestSummoner2"
        assert player2.role_preferences["jungle"] == 5
    
    def test_load_empty_data(self, data_manager):
        """Test loading when no data file exists."""
        players = data_manager.load_player_data()
        assert players == []
    
    def test_save_invalid_data_raises_error(self, data_manager):
        """Test that saving invalid data raises appropriate errors."""
        # Test with non-serializable data
        invalid_player = Player(
            name="Invalid",
            summoner_name="Invalid",
            performance_cache={"test": object()}  # Non-serializable object
        )
        
        with pytest.raises(ValueError, match="Invalid player data format"):
            data_manager.save_player_data([invalid_player])
    
    def test_load_corrupted_data_raises_error(self, data_manager, temp_config):
        """Test that loading corrupted data raises appropriate errors."""
        # Create corrupted JSON file
        corrupted_file = Path(temp_config.data_directory) / temp_config.player_data_file
        with open(corrupted_file, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(ValueError, match="Invalid player data format"):
            data_manager.load_player_data()
    
    def test_get_player_by_name(self, data_manager, sample_players):
        """Test retrieving a specific player by name."""
        data_manager.save_player_data(sample_players)
        
        # Test existing player
        player = data_manager.get_player_by_name("TestPlayer1")
        assert player is not None
        assert player.summoner_name == "TestSummoner1"
        
        # Test non-existing player
        player = data_manager.get_player_by_name("NonExistent")
        assert player is None
    
    def test_update_player_existing(self, data_manager, sample_players):
        """Test updating an existing player."""
        data_manager.save_player_data(sample_players)
        
        # Update player
        updated_player = Player(
            name="TestPlayer1",
            summoner_name="UpdatedSummoner",
            puuid="updated_puuid",
            role_preferences={"top": 1, "jungle": 2, "middle": 3, "support": 4, "bottom": 5}
        )
        
        data_manager.update_player(updated_player)
        
        # Verify update
        loaded_player = data_manager.get_player_by_name("TestPlayer1")
        assert loaded_player.summoner_name == "UpdatedSummoner"
        assert loaded_player.puuid == "updated_puuid"
        assert loaded_player.role_preferences["bottom"] == 5
    
    def test_update_player_new(self, data_manager, sample_players):
        """Test adding a new player via update."""
        data_manager.save_player_data(sample_players)
        
        # Add new player
        new_player = Player(
            name="NewPlayer",
            summoner_name="NewSummoner",
            puuid="new_puuid"
        )
        
        data_manager.update_player(new_player)
        
        # Verify addition
        players = data_manager.load_player_data()
        assert len(players) == 3
        
        new_loaded_player = data_manager.get_player_by_name("NewPlayer")
        assert new_loaded_player is not None
        assert new_loaded_player.summoner_name == "NewSummoner"
    
    def test_update_preferences_valid(self, data_manager, sample_players):
        """Test updating player preferences with valid data."""
        data_manager.save_player_data(sample_players)
        
        new_preferences = {
            "top": 1,
            "jungle": 5,
            "middle": 3
        }
        
        data_manager.update_preferences("TestPlayer1", new_preferences)
        
        # Verify update
        updated_player = data_manager.get_player_by_name("TestPlayer1")
        assert updated_player.role_preferences["top"] == 1
        assert updated_player.role_preferences["jungle"] == 5
        assert updated_player.role_preferences["middle"] == 3
        # Original preferences for other roles should remain
        assert updated_player.role_preferences["support"] == 1
        assert updated_player.role_preferences["bottom"] == 4
    
    def test_update_preferences_invalid_role(self, data_manager, sample_players):
        """Test updating preferences with invalid role."""
        data_manager.save_player_data(sample_players)
        
        invalid_preferences = {"invalid_role": 3}
        
        with pytest.raises(ValueError, match="Invalid role: invalid_role"):
            data_manager.update_preferences("TestPlayer1", invalid_preferences)
    
    def test_update_preferences_invalid_score(self, data_manager, sample_players):
        """Test updating preferences with invalid score."""
        data_manager.save_player_data(sample_players)
        
        invalid_preferences = {"top": 6}  # Score out of range
        
        with pytest.raises(ValueError, match="Preference score must be integer between 1-5"):
            data_manager.update_preferences("TestPlayer1", invalid_preferences)
    
    def test_update_preferences_nonexistent_player(self, data_manager):
        """Test updating preferences for non-existent player."""
        preferences = {"top": 3}
        
        with pytest.raises(ValueError, match="Player 'NonExistent' not found"):
            data_manager.update_preferences("NonExistent", preferences)
    
    def test_cache_api_data(self, data_manager):
        """Test caching API data."""
        test_data = {"key": "value", "number": 42}
        cache_key = "test_cache_key"
        
        data_manager.cache_api_data(test_data, cache_key)
        
        # Verify cache file was created
        cache_file = Path(data_manager.cache_dir) / f"{cache_key}.json"
        assert cache_file.exists()
        
        # Verify cache content
        with open(cache_file, 'r') as f:
            cache_entry = json.load(f)
        
        assert cache_entry['data'] == test_data
        assert 'timestamp' in cache_entry
        assert cache_entry['ttl_hours'] == 1  # Default from config
    
    def test_get_cached_data_valid(self, data_manager):
        """Test retrieving valid cached data."""
        test_data = {"cached": "data"}
        cache_key = "valid_cache"
        
        data_manager.cache_api_data(test_data, cache_key)
        
        retrieved_data = data_manager.get_cached_data(cache_key)
        assert retrieved_data == test_data
    
    def test_get_cached_data_expired(self, data_manager):
        """Test retrieving expired cached data."""
        test_data = {"expired": "data"}
        cache_key = "expired_cache"
        
        # Cache with very short TTL
        data_manager.cache_api_data(test_data, cache_key, ttl_hours=0.001)  # ~3.6 seconds
        
        # Wait for expiration
        time.sleep(4)
        
        retrieved_data = data_manager.get_cached_data(cache_key)
        assert retrieved_data is None
        
        # Verify cache file was removed
        cache_file = Path(data_manager.cache_dir) / f"{cache_key}.json"
        assert not cache_file.exists()
    
    def test_get_cached_data_nonexistent(self, data_manager):
        """Test retrieving non-existent cached data."""
        retrieved_data = data_manager.get_cached_data("nonexistent_key")
        assert retrieved_data is None
    
    def test_clear_expired_cache(self, data_manager):
        """Test clearing expired cache files."""
        # Create some cache entries
        data_manager.cache_api_data({"data": 1}, "key1", ttl_hours=0.001)  # Will expire
        data_manager.cache_api_data({"data": 2}, "key2", ttl_hours=24)     # Won't expire
        
        # Wait for first cache to expire
        time.sleep(4)
        
        removed_count = data_manager.clear_expired_cache()
        
        assert removed_count == 1
        assert data_manager.get_cached_data("key1") is None
        assert data_manager.get_cached_data("key2") == {"data": 2}
    
    def test_get_cache_size_mb(self, data_manager):
        """Test getting cache size in MB."""
        # Initially empty
        assert data_manager.get_cache_size_mb() == 0
        
        # Add some cache data
        large_data = {"data": "x" * 1000}  # ~1KB of data
        data_manager.cache_api_data(large_data, "large_cache")
        
        cache_size = data_manager.get_cache_size_mb()
        assert cache_size > 0
        assert cache_size < 1  # Should be less than 1MB
    
    def test_cleanup_cache_if_needed(self, data_manager):
        """Test cache cleanup when size limit is exceeded."""
        # Create multiple cache entries to exceed limit
        for i in range(25):
            large_data = {"data": "x" * 50000}  # ~50KB each
            data_manager.cache_api_data(large_data, f"cache_{i}")
        
        # Should exceed 1MB limit
        cache_size_before = data_manager.get_cache_size_mb()
        assert cache_size_before > 1, f"Cache size {cache_size_before} MB should exceed 1MB"
        
        # Cleanup should reduce size
        data_manager.cleanup_cache_if_needed()
        
        # Size should be under limit now
        cache_size_after = data_manager.get_cache_size_mb()
        assert cache_size_after <= 1, f"Cache size {cache_size_after} MB should be under 1MB limit"
    
    def test_delete_player_existing(self, data_manager, sample_players):
        """Test deleting an existing player."""
        data_manager.save_player_data(sample_players)
        
        result = data_manager.delete_player("TestPlayer1")
        
        assert result is True
        
        # Verify player was deleted
        players = data_manager.load_player_data()
        assert len(players) == 1
        assert players[0].name == "TestPlayer2"
    
    def test_delete_player_nonexistent(self, data_manager, sample_players):
        """Test deleting a non-existent player."""
        data_manager.save_player_data(sample_players)
        
        result = data_manager.delete_player("NonExistent")
        
        assert result is False
        
        # Verify no players were deleted
        players = data_manager.load_player_data()
        assert len(players) == 2
    
    def test_get_all_player_names(self, data_manager, sample_players):
        """Test getting all player names."""
        data_manager.save_player_data(sample_players)
        
        names = data_manager.get_all_player_names()
        
        assert len(names) == 2
        assert "TestPlayer1" in names
        assert "TestPlayer2" in names
    
    def test_get_all_player_names_empty(self, data_manager):
        """Test getting player names when no players exist."""
        names = data_manager.get_all_player_names()
        assert names == []
    
    def test_player_cache_functionality(self, data_manager, sample_players):
        """Test that player data caching works correctly."""
        # Save players
        data_manager.save_player_data(sample_players)
        
        # Load players (should cache)
        players1 = data_manager.load_player_data()
        
        # Modify the file directly
        player_file = Path(data_manager.config.data_directory) / data_manager.config.player_data_file
        with open(player_file, 'w') as f:
            json.dump([], f)  # Empty the file
        
        # Load again - should still return cached data
        players2 = data_manager.load_player_data()
        
        assert len(players2) == 2  # Should return cached data, not empty file
        
        # Clear cache by setting old timestamp
        data_manager._cache_last_loaded = datetime.now() - timedelta(hours=25)
        
        # Load again - should read from file now
        players3 = data_manager.load_player_data()
        assert len(players3) == 0  # Should read empty file now
    
    @patch('builtins.print')
    def test_cache_failure_handling(self, mock_print, data_manager):
        """Test that cache failures don't break the application."""
        # Mock file operations to fail
        with patch('builtins.open', side_effect=IOError("Disk full")):
            # Should not raise exception
            data_manager.cache_api_data({"test": "data"}, "test_key")
            
            # Should print warning
            mock_print.assert_called_once()
            assert "Warning: Failed to cache data" in mock_print.call_args[0][0]