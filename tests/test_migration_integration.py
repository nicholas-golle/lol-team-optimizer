"""
Integration tests for migration with the core engine and streamlined CLI.

This module tests that migration works properly with the overall system.
"""

import json
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from lol_team_optimizer.migration import DataMigrator
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.config import Config
from lol_team_optimizer.data_manager import DataManager


class TestMigrationIntegration:
    """Test migration integration with the core system."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.cache_dir = Path(self.temp_dir) / "cache"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test config
        self.config = Config()
        self.config.data_directory = str(self.data_dir)
        self.config.cache_directory = str(self.cache_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_old_format_data(self):
        """Create old format data that needs migration."""
        # Old format player data
        old_player_data = [
            {
                "name": "TestPlayer1",
                "summoner_name": "TestPlayer1#NA1",
                "role_preferences": {"top": 4, "jungle": 2},
                "last_updated": "2025-01-01 12:00:00"  # Old datetime format
            },
            {
                "name": "TestPlayer2", 
                "summoner_name": "TestPlayer2#NA1",
                "role_preferences": {"middle": 5, "support": 1},
                "champion_masteries": {
                    "1": {
                        "mastery_level": 7,
                        "mastery_points": 100000
                        # Missing required fields
                    }
                }
            }
        ]
        
        player_file = self.data_dir / "players.json"
        with open(player_file, 'w', encoding='utf-8') as f:
            json.dump(old_player_data, f, indent=2)
        
        # Large monolithic cache file
        cache_data = {}
        for i in range(100):
            cache_data[f"test_key_{i}"] = {
                "data": f"test_data_{i}",
                "timestamp": datetime.now().isoformat(),
                "ttl_hours": 1
            }
        
        cache_file = self.cache_dir / "api_cache.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2)
        
        # Old synergy data
        synergy_data = {
            "synergies": {
                "TestPlayer1|TestPlayer2": {
                    "games_together": 10,
                    "wins_together": 6
                    # Missing some fields
                }
            }
        }
        
        synergy_file = self.cache_dir / "synergy_data.json"
        with open(synergy_file, 'w', encoding='utf-8') as f:
            json.dump(synergy_data, f, indent=2)
    
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_core_engine_detects_migration_need(self, mock_riot_client):
        """Test that core engine detects when migration is needed."""
        # Mock the RiotAPIClient to avoid API calls
        mock_riot_client.return_value = MagicMock()
        
        # Create old format data
        self.create_old_format_data()
        
        # Patch config to use our test directories
        with patch('lol_team_optimizer.core_engine.Config') as mock_config:
            mock_config.return_value = self.config
            
            # Initialize core engine
            engine = CoreEngine()
            
            # Check that migration status was detected
            migration_status = engine.get_migration_status()
            assert migration_status is not None
            assert migration_status['migration_needed']
            assert migration_status['compatibility_status'] == 'migration_required'
    
    @patch('lol_team_optimizer.core_engine.RiotAPIClient')
    def test_core_engine_works_after_migration(self, mock_riot_client):
        """Test that core engine works properly after migration."""
        # Mock the RiotAPIClient to avoid API calls
        mock_riot_client.return_value = MagicMock()
        
        # Create old format data
        self.create_old_format_data()
        
        # Perform migration
        migrator = DataMigrator(self.config)
        migration_results = migrator.perform_full_migration()
        
        assert migration_results['success']
        assert migration_results['player_migration']['players_migrated'] == 2
        
        # Patch config to use our test directories
        with patch('lol_team_optimizer.core_engine.Config') as mock_config:
            mock_config.return_value = self.config
            
            # Initialize core engine after migration
            engine = CoreEngine()
            
            # Check that no migration is needed now
            migration_status = engine.get_migration_status()
            assert migration_status is None  # No migration needed
            
            # Verify system status
            system_status = engine.system_status
            assert system_status['player_count'] == 2
            assert not system_status.get('error')
    
    def test_data_manager_reads_migrated_data(self):
        """Test that DataManager can read migrated data correctly."""
        # Create old format data
        self.create_old_format_data()
        
        # Perform migration
        migrator = DataMigrator(self.config)
        migration_results = migrator.perform_full_migration()
        
        assert migration_results['success']
        
        # Use DataManager to read migrated data
        data_manager = DataManager(self.config)
        players = data_manager.load_player_data()
        
        assert len(players) == 2
        
        # Verify first player
        player1 = next(p for p in players if p.name == "TestPlayer1")
        assert player1.summoner_name == "TestPlayer1#NA1"
        assert len(player1.role_preferences) == 5  # All roles should be present
        assert player1.role_preferences['top'] == 4
        assert player1.role_preferences['middle'] == 3  # Default value
        assert isinstance(player1.last_updated, datetime)
        
        # Verify second player
        player2 = next(p for p in players if p.name == "TestPlayer2")
        assert player2.summoner_name == "TestPlayer2#NA1"
        assert len(player2.champion_masteries) == 1
        mastery = next(iter(player2.champion_masteries.values()))
        assert mastery.champion_id == 1
        assert mastery.mastery_level == 7
        assert mastery.mastery_points == 100000
    
    def test_cache_migration_creates_individual_files(self):
        """Test that cache migration creates individual cache files."""
        # Create old format data
        self.create_old_format_data()
        
        # Verify monolithic cache file exists
        old_cache_file = self.cache_dir / "api_cache.json"
        assert old_cache_file.exists()
        
        # Perform migration
        migrator = DataMigrator(self.config)
        migration_results = migrator.perform_full_migration()
        
        assert migration_results['success']
        assert migration_results['cache_migration']['cache_entries_migrated'] == 100
        
        # Verify individual cache files were created
        cache_files = list(self.cache_dir.glob("test_key_*.json"))
        assert len(cache_files) == 100
        
        # Verify old cache file was renamed
        old_cache_backup = self.cache_dir / "api_cache_old.json"
        assert old_cache_backup.exists()
        assert not old_cache_file.exists()
        
        # Verify individual cache file format
        sample_cache_file = cache_files[0]
        with open(sample_cache_file, 'r') as f:
            cache_data = json.load(f)
        
        assert 'data' in cache_data
        assert 'timestamp' in cache_data
        assert 'ttl_hours' in cache_data
    
    def test_rollback_restores_original_data(self):
        """Test that rollback properly restores original data."""
        # Create old format data
        self.create_old_format_data()
        
        # Create backup before migration
        migrator = DataMigrator(self.config)
        backup_path = migrator.create_backup("test_rollback")
        
        # Perform migration
        migration_results = migrator.perform_full_migration()
        assert migration_results['success']
        
        # Verify migration changed the data
        data_manager = DataManager(self.config)
        migrated_players = data_manager.load_player_data()
        assert len(migrated_players[0].role_preferences) == 5  # All roles filled
        
        # Perform rollback
        rollback_results = migrator.rollback_migration("test_rollback")
        assert rollback_results['success']
        assert rollback_results['files_restored'] > 0
        
        # Verify data was restored to original format
        with open(self.data_dir / "players.json", 'r') as f:
            restored_data = json.load(f)
        
        # Should have original format (missing some role preferences)
        assert len(restored_data[0]['role_preferences']) == 2  # Original format
        assert restored_data[0]['role_preferences']['top'] == 4
    
    def test_migration_preserves_existing_good_data(self):
        """Test that migration preserves data that's already in good format."""
        # Create new format data (no migration needed)
        new_player_data = [
            {
                "name": "GoodPlayer",
                "summoner_name": "GoodPlayer#NA1",
                "puuid": "test-puuid",
                "role_preferences": {
                    "top": 4, "jungle": 2, "middle": 3, "support": 3, "bottom": 3
                },
                "performance_cache": {},
                "champion_masteries": {},
                "role_champion_pools": {
                    "top": [], "jungle": [], "middle": [], "support": [], "bottom": []
                },
                "last_updated": "2025-01-01T12:00:00"
            }
        ]
        
        player_file = self.data_dir / "players.json"
        with open(player_file, 'w', encoding='utf-8') as f:
            json.dump(new_player_data, f, indent=2)
        
        # Check migration status
        migrator = DataMigrator(self.config)
        status = migrator.check_migration_needed()
        
        # Should not need migration
        assert not status['migration_needed']
        assert status['compatibility_status'] == 'compatible'
        
        # Run migration anyway (should be safe)
        migration_results = migrator.perform_full_migration()
        assert migration_results['success']
        
        # Verify data is unchanged
        data_manager = DataManager(self.config)
        players = data_manager.load_player_data()
        
        assert len(players) == 1
        player = players[0]
        assert player.name == "GoodPlayer"
        assert player.puuid == "test-puuid"
        assert len(player.role_preferences) == 5
    
    def test_migration_handles_corrupted_data_gracefully(self):
        """Test that migration handles corrupted data gracefully."""
        # Create corrupted player data
        corrupted_data = "invalid json content"
        player_file = self.data_dir / "players.json"
        with open(player_file, 'w') as f:
            f.write(corrupted_data)
        
        # Attempt migration
        migrator = DataMigrator(self.config)
        migration_results = migrator.perform_full_migration()
        
        # Should handle gracefully with errors reported
        assert not migration_results['success']  # Should fail due to corruption
        assert len(migration_results['player_migration']['errors']) > 0
        
        # Backup should still be created
        assert migration_results['backup_path'] is not None
        assert Path(migration_results['backup_path']).exists()


if __name__ == "__main__":
    pytest.main([__file__])