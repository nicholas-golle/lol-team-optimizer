"""
Unit tests for the ChampionDataManager.

Tests champion data fetching, caching, and role mapping functionality.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

from lol_team_optimizer.champion_data import ChampionDataManager, ChampionInfo
from lol_team_optimizer.config import Config


class TestChampionDataManager:
    """Test cases for ChampionDataManager."""
    
    @pytest.fixture
    def temp_config(self):
        """Create a temporary configuration for testing."""
        temp_dir = tempfile.mkdtemp()
        config = Config()
        config.cache_directory = str(Path(temp_dir) / "cache")
        yield config
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_champion_data(self):
        """Sample champion data from Data Dragon API."""
        return {
            "type": "champion",
            "format": "standAloneComplex",
            "version": "15.14.1",
            "data": {
                "Aatrox": {
                    "version": "15.14.1",
                    "id": "Aatrox",
                    "key": "266",
                    "name": "Aatrox",
                    "title": "the Darkin Blade",
                    "tags": ["Fighter", "Tank"]
                },
                "Ahri": {
                    "version": "15.14.1",
                    "id": "Ahri",
                    "key": "103",
                    "name": "Ahri",
                    "title": "the Nine-Tailed Fox",
                    "tags": ["Mage", "Assassin"]
                },
                "Ashe": {
                    "version": "15.14.1",
                    "id": "Ashe",
                    "key": "22",
                    "name": "Ashe",
                    "title": "the Frost Archer",
                    "tags": ["Marksman", "Support"]
                }
            }
        }
    
    @pytest.fixture
    def champion_manager(self, temp_config):
        """Create a ChampionDataManager instance for testing."""
        with patch.object(ChampionDataManager, '_load_cached_data', return_value=True):
            return ChampionDataManager(temp_config)
    
    def test_initialization(self, temp_config):
        """Test ChampionDataManager initialization."""
        with patch.object(ChampionDataManager, '_load_cached_data', return_value=True):
            manager = ChampionDataManager(temp_config)
            
            assert manager.config == temp_config
            assert manager.data_dragon_version == "15.14.1"
            assert manager.data_dragon_language == "en_US"
            assert "ddragon.leagueoflegends.com" in manager.base_url
            assert manager.cache_dir.exists()
    
    def test_fetch_champion_list_success(self, champion_manager, sample_champion_data):
        """Test successful champion data fetching."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_champion_data
            mock_get.return_value = mock_response
            
            with patch.object(champion_manager, '_save_cache'):
                result = champion_manager.fetch_champion_list()
            
            assert result is True
            assert len(champion_manager.champions) == 3
            assert 266 in champion_manager.champions  # Aatrox
            assert 103 in champion_manager.champions  # Ahri
            assert 22 in champion_manager.champions   # Ashe
    
    def test_fetch_champion_list_network_error(self, champion_manager):
        """Test champion data fetching with network error."""
        with patch('requests.get', side_effect=Exception("Network error")):
            result = champion_manager.fetch_champion_list()
            assert result is False
    
    def test_parse_champion_data(self, champion_manager, sample_champion_data):
        """Test parsing of champion data."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        # Check champions were parsed correctly
        assert len(champion_manager.champions) == 3
        
        # Check Aatrox
        aatrox = champion_manager.champions[266]
        assert aatrox.name == "Aatrox"
        assert aatrox.title == "the Darkin Blade"
        assert aatrox.tags == ["Fighter", "Tank"]
        assert aatrox.key == "Aatrox"
        
        # Check name-to-ID mapping
        assert champion_manager.champion_name_to_id["Aatrox"] == 266
        assert champion_manager.champion_name_to_id["Ahri"] == 103
    
    def test_get_champion_name(self, champion_manager, sample_champion_data):
        """Test getting champion name by ID."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        assert champion_manager.get_champion_name(266) == "Aatrox"
        assert champion_manager.get_champion_name(103) == "Ahri"
        assert champion_manager.get_champion_name(999) is None
    
    def test_get_champion_id(self, champion_manager, sample_champion_data):
        """Test getting champion ID by name."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        assert champion_manager.get_champion_id("Aatrox") == 266
        assert champion_manager.get_champion_id("Ahri") == 103
        assert champion_manager.get_champion_id("NonExistent") is None
    
    def test_get_champion_info(self, champion_manager, sample_champion_data):
        """Test getting complete champion information."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        aatrox_info = champion_manager.get_champion_info(266)
        assert aatrox_info is not None
        assert aatrox_info.name == "Aatrox"
        assert aatrox_info.champion_id == 266
        assert aatrox_info.title == "the Darkin Blade"
        
        assert champion_manager.get_champion_info(999) is None
    
    def test_get_champion_roles(self, champion_manager, sample_champion_data):
        """Test champion role determination."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        # Aatrox (Fighter, Tank) should be top/jungle
        aatrox_roles = champion_manager.get_champion_roles(266)
        assert 'top' in aatrox_roles
        assert 'jungle' in aatrox_roles
        
        # Ahri (Mage, Assassin) should be middle/jungle
        ahri_roles = champion_manager.get_champion_roles(103)
        assert 'middle' in ahri_roles
        assert 'jungle' in ahri_roles
        
        # Ashe (Marksman, Support) should be bottom
        ashe_roles = champion_manager.get_champion_roles(22)
        assert 'bottom' in ashe_roles
        
        # Non-existent champion
        assert champion_manager.get_champion_roles(999) == []
    
    def test_get_champions_by_role(self, champion_manager, sample_champion_data):
        """Test getting champions by role."""
        champion_manager._parse_champion_data(sample_champion_data)
        
        # Get top lane champions
        top_champions = champion_manager.get_champions_by_role('top')
        assert 266 in top_champions  # Aatrox
        
        # Get middle lane champions
        mid_champions = champion_manager.get_champions_by_role('middle')
        assert 103 in mid_champions  # Ahri
        
        # Get bottom lane champions
        bot_champions = champion_manager.get_champions_by_role('bottom')
        assert 22 in bot_champions  # Ashe
        
        # Invalid role
        assert champion_manager.get_champions_by_role('invalid') == []
    
    def test_cache_functionality(self, champion_manager, sample_champion_data):
        """Test caching functionality."""
        # Test saving cache
        champion_manager._save_cache(sample_champion_data)
        assert champion_manager.cache_file.exists()
        
        # Test loading cache
        with open(champion_manager.cache_file, 'r') as f:
            cached_data = json.load(f)
        assert cached_data == sample_champion_data
    
    def test_cache_validation(self, champion_manager):
        """Test cache validation logic."""
        # No cache file
        assert not champion_manager._is_cache_valid()
        
        # Create cache file
        champion_manager.cache_file.touch()
        assert champion_manager._is_cache_valid()
        
        # Expired cache (simulate old file)
        old_time = datetime.now() - timedelta(days=8)
        champion_manager.cache_file.touch()
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_mtime = old_time.timestamp()
            assert not champion_manager._is_cache_valid()
    
    def test_get_cache_info(self, champion_manager, sample_champion_data):
        """Test cache information retrieval."""
        # No cache initially
        cache_info = champion_manager.get_cache_info()
        assert cache_info['cache_exists'] is False
        assert cache_info['champion_count'] == 0
        
        # After parsing data
        champion_manager._parse_champion_data(sample_champion_data)
        cache_info = champion_manager.get_cache_info()
        assert cache_info['champion_count'] == 3
        
        # After saving cache
        champion_manager._save_cache(sample_champion_data)
        cache_info = champion_manager.get_cache_info()
        assert cache_info['cache_exists'] is True
        assert cache_info['cache_valid'] is True
    
    def test_update_champion_cache(self, champion_manager):
        """Test forced cache update."""
        with patch.object(champion_manager, 'fetch_champion_list', return_value=True) as mock_fetch:
            result = champion_manager.update_champion_cache()
            assert result is True
            mock_fetch.assert_called_once_with(force_refresh=True)
    
    def test_special_role_cases(self, champion_manager):
        """Test special role case handling."""
        special_cases = champion_manager._get_special_role_cases()
        
        # Test some known special cases
        assert 104 in special_cases  # Graves - jungle marksman
        assert 'jungle' in special_cases[104]
        
        assert 555 in special_cases  # Pyke - support assassin
        assert 'support' in special_cases[555]
    
    def test_error_handling_in_parsing(self, champion_manager):
        """Test error handling during champion data parsing."""
        # Malformed champion data
        bad_data = {
            "data": {
                "BadChampion": {
                    "name": "BadChampion",
                    # Missing 'key' field
                    "title": "Bad Champion",
                    "tags": ["Fighter"]
                },
                "GoodChampion": {
                    "key": "123",
                    "name": "GoodChampion",
                    "title": "Good Champion",
                    "tags": ["Mage"]
                }
            }
        }
        
        champion_manager._parse_champion_data(bad_data)
        
        # Should only parse the good champion
        assert len(champion_manager.champions) == 1
        assert 123 in champion_manager.champions
        assert champion_manager.champions[123].name == "GoodChampion"
    
    def test_concurrent_access_safety(self, champion_manager, sample_champion_data):
        """Test thread safety of champion data operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def access_champion_data():
            try:
                champion_manager._parse_champion_data(sample_champion_data)
                name = champion_manager.get_champion_name(266)
                results.append(name)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads accessing champion data
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_champion_data)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        # Should handle concurrent access without errors
        assert len(errors) == 0
        assert all(result == "Aatrox" for result in results)
    
    def test_large_dataset_handling(self, champion_manager):
        """Test handling of large champion datasets."""
        # Create a large dataset
        large_data = {
            "data": {
                f"Champion{i}": {
                    "key": str(i),
                    "name": f"Champion{i}",
                    "title": f"Champion {i}",
                    "tags": ["Fighter"]
                }
                for i in range(200)  # Simulate 200 champions
            }
        }
        
        champion_manager._parse_champion_data(large_data)
        
        # Should handle large datasets efficiently
        assert len(champion_manager.champions) == 200
        assert champion_manager.get_champion_name(0) == "Champion0"
        assert champion_manager.get_champion_name(199) == "Champion199"