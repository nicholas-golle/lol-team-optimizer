"""
Tests for the data migration system.

This module tests migration of existing player data and backward compatibility.
"""

import json
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from lol_team_optimizer.migration import DataMigrator, MigrationError, run_migration_check, run_full_migration
from lol_team_optimizer.config import Config
from lol_team_optimizer.models import Player, ChampionMastery


class TestDataMigrator:
    """Test cases for the DataMigrator class."""
    
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
        
        self.migrator = DataMigrator(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_player_data(self, old_format=False):
        """Create test player data in old or new format."""
        if old_format:
            # Old format missing some fields
            player_data = [
                {
                    "name": "TestPlayer1",
                    "summoner_name": "TestPlayer1#NA1",
                    "role_preferences": {"top": 4, "jungle": 2},
                    "last_updated": "2025-01-01 12:00:00"  # Old datetime format
                },
                {
                    "name": "TestPlayer2",
                    "summoner_name": "TestPlayer2#NA1",
                    "champion_masteries": {
                        "1": {
                            "mastery_level": 7,
                            "mastery_points": 100000
                            # Missing required fields
                        }
                    }
                }
            ]
        else:
            # New format with all fields
            player_data = [
                {
                    "name": "TestPlayer1",
                    "summoner_name": "TestPlayer1#NA1",
                    "puuid": "test-puuid-1",
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
            json.dump(player_data, f, indent=2)
        
        return player_data
    
    def create_test_cache_data(self, monolithic=False):
        """Create test cache data."""
        if monolithic:
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
        else:
            # Individual cache files
            for i in range(5):
                cache_data = {
                    "data": f"test_data_{i}",
                    "timestamp": datetime.now().isoformat(),
                    "ttl_hours": 1
                }
                
                cache_file = self.cache_dir / f"test_key_{i}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2)
    
    def create_test_synergy_data(self, old_format=False):
        """Create test synergy data."""
        if old_format:
            synergy_data = {
                "synergies": {
                    "Player1|Player2": {
                        "games_together": 10,
                        "wins_together": 6
                        # Missing some fields
                    }
                }
            }
        else:
            synergy_data = {
                "synergies": {
                    "Player1|Player2": {
                        "games_together": 10,
                        "wins_together": 6,
                        "losses_together": 4,
                        "avg_combined_kda": 2.5,
                        "avg_game_duration": 1800.0,
                        "avg_vision_score_combined": 50.0,
                        "recent_games_together": 3,
                        "last_played_together": "2025-01-01T12:00:00",
                        "role_combinations": {},
                        "champion_combinations": {}
                    }
                },
                "last_updated": "2025-01-01T12:00:00"
            }
        
        synergy_file = self.cache_dir / "synergy_data.json"
        with open(synergy_file, 'w', encoding='utf-8') as f:
            json.dump(synergy_data, f, indent=2)
    
    def test_check_migration_needed_no_data(self):
        """Test migration check with no existing data."""
        status = self.migrator.check_migration_needed()
        
        assert not status['migration_needed']
        assert status['compatibility_status'] == 'compatible'
        # Cache directory exists so cache_files will be 0
        assert 'cache_files' in status['data_summary']
    
    def test_check_migration_needed_old_format(self):
        """Test migration check with old format data."""
        self.create_test_player_data(old_format=True)
        self.create_test_cache_data(monolithic=True)
        self.create_test_synergy_data(old_format=True)
        
        status = self.migrator.check_migration_needed()
        
        assert status['migration_needed']
        assert status['compatibility_status'] == 'migration_required'
        assert status['backup_recommended']
        assert len(status['issues_found']) > 0
        assert status['data_summary']['player_count'] == 2
    
    def test_check_migration_needed_new_format(self):
        """Test migration check with new format data."""
        self.create_test_player_data(old_format=False)
        self.create_test_cache_data(monolithic=False)
        self.create_test_synergy_data(old_format=False)
        
        status = self.migrator.check_migration_needed()
        
        assert not status['migration_needed']
        assert status['compatibility_status'] == 'compatible'
        assert status['data_summary']['player_count'] == 1
    
    def test_create_backup(self):
        """Test backup creation."""
        self.create_test_player_data()
        self.create_test_cache_data()
        
        backup_path = self.migrator.create_backup("test_backup")
        
        assert Path(backup_path).exists()
        assert (Path(backup_path) / "players.json").exists()
        assert (Path(backup_path) / "cache").exists()
        assert (Path(backup_path) / "backup_manifest.json").exists()
        
        # Check manifest
        with open(Path(backup_path) / "backup_manifest.json", 'r') as f:
            manifest = json.load(f)
        
        assert manifest['backup_name'] == "test_backup"
        assert 'created_at' in manifest
        assert len(manifest['files_backed_up']) > 0
    
    def test_migrate_player_data_old_format(self):
        """Test player data migration from old format."""
        self.create_test_player_data(old_format=True)
        
        results = self.migrator.migrate_player_data()
        
        assert results['players_migrated'] == 2
        assert results['players_skipped'] == 0
        assert len(results['errors']) == 0
        
        # Verify migrated data
        from lol_team_optimizer.data_manager import DataManager
        data_manager = DataManager(self.config)
        players = data_manager.load_player_data()
        
        assert len(players) == 2
        
        # Check first player
        player1 = next(p for p in players if p.name == "TestPlayer1")
        assert player1.puuid == ""  # Default value
        assert len(player1.role_preferences) == 5  # All roles filled
        assert player1.role_preferences['middle'] == 3  # Default value
        assert isinstance(player1.last_updated, datetime)
        
        # Check second player
        player2 = next(p for p in players if p.name == "TestPlayer2")
        assert len(player2.champion_masteries) == 1
        mastery = next(iter(player2.champion_masteries.values()))
        assert isinstance(mastery, ChampionMastery)
        assert mastery.champion_id == 1
    
    def test_migrate_cache_data_monolithic(self):
        """Test cache data migration from monolithic format."""
        self.create_test_cache_data(monolithic=True)
        
        results = self.migrator.migrate_cache_data()
        
        assert results['cache_files_processed'] == 1
        assert results['cache_entries_migrated'] == 100
        assert len(results['errors']) == 0
        
        # Verify individual cache files were created
        cache_files = list(self.cache_dir.glob("test_key_*.json"))
        assert len(cache_files) == 100
        
        # Verify old file was renamed
        assert (self.cache_dir / "api_cache_old.json").exists()
    
    def test_migrate_synergy_data(self):
        """Test synergy data migration."""
        self.create_test_synergy_data(old_format=True)
        
        results = self.migrator.migrate_synergy_data()
        
        assert results['synergy_pairs_migrated'] == 1
        assert results['synergy_pairs_skipped'] == 0
        assert len(results['errors']) == 0
        
        # Verify migrated synergy data
        synergy_file = self.cache_dir / "synergy_data.json"
        with open(synergy_file, 'r') as f:
            synergy_data = json.load(f)
        
        synergy = synergy_data['synergies']['Player1|Player2']
        assert synergy['games_together'] == 10
        assert synergy['wins_together'] == 6
        assert synergy['losses_together'] == 0  # Default value
        assert 'role_combinations' in synergy
        assert 'champion_combinations' in synergy
    
    def test_perform_full_migration(self):
        """Test complete migration process."""
        self.create_test_player_data(old_format=True)
        self.create_test_cache_data(monolithic=True)
        self.create_test_synergy_data(old_format=True)
        
        results = self.migrator.perform_full_migration()
        
        assert results['success']
        assert results['backup_path'] is not None
        assert Path(results['backup_path']).exists()
        assert results['total_errors'] == 0
        
        # Verify all migrations completed
        assert results['player_migration']['players_migrated'] == 2
        assert results['cache_migration']['cache_entries_migrated'] == 100
        assert results['synergy_migration']['synergy_pairs_migrated'] == 1
    
    def test_rollback_migration(self):
        """Test migration rollback."""
        # Create initial data
        self.create_test_player_data(old_format=False)
        
        # Create backup
        backup_path = self.migrator.create_backup("rollback_test")
        
        # Modify data
        self.create_test_player_data(old_format=True)
        
        # Rollback
        results = self.migrator.rollback_migration("rollback_test")
        
        assert results['success']
        assert results['files_restored'] > 0
        assert len(results['errors']) == 0
        
        # Verify data was restored
        from lol_team_optimizer.data_manager import DataManager
        data_manager = DataManager(self.config)
        players = data_manager.load_player_data()
        
        # Should have the original new format data
        assert len(players) == 1
        player = players[0]
        assert player.puuid == "test-puuid-1"
    
    def test_list_backups(self):
        """Test backup listing."""
        # Create multiple backups
        self.create_test_player_data()
        
        backup1 = self.migrator.create_backup("backup1")
        backup2 = self.migrator.create_backup("backup2")
        
        backups = self.migrator.list_backups()
        
        assert len(backups) == 2
        
        # Check backup info
        backup_names = [b['name'] for b in backups]
        assert 'backup1' in backup_names
        assert 'backup2' in backup_names
        
        for backup in backups:
            assert 'created_at' in backup
            assert backup['file_count'] > 0
            assert backup['size_mb'] > 0
    
    def test_migration_error_handling(self):
        """Test error handling during migration."""
        # Create invalid player data
        invalid_data = "invalid json"
        player_file = self.data_dir / "players.json"
        with open(player_file, 'w') as f:
            f.write(invalid_data)
        
        results = self.migrator.migrate_player_data()
        
        assert len(results['errors']) > 0
        assert results['players_migrated'] == 0
    
    def test_backup_creation_failure(self):
        """Test backup creation failure handling."""
        # Create a file with the same name as the backup directory to simulate failure
        test_backup_path = self.migrator.backup_directory / "test_backup"
        test_backup_path.touch()  # Create a file instead of directory
        
        try:
            with pytest.raises(MigrationError):
                self.migrator.create_backup("test_backup")
        finally:
            # Clean up
            test_backup_path.unlink(missing_ok=True)


class TestMigrationConvenienceFunctions:
    """Test convenience functions for migration."""
    
    @patch('lol_team_optimizer.migration.DataMigrator')
    def test_run_migration_check(self, mock_migrator_class):
        """Test migration check convenience function."""
        mock_migrator = MagicMock()
        mock_migrator.check_migration_needed.return_value = {'migration_needed': True}
        mock_migrator_class.return_value = mock_migrator
        
        result = run_migration_check()
        
        assert result['migration_needed']
        mock_migrator.check_migration_needed.assert_called_once()
    
    @patch('lol_team_optimizer.migration.DataMigrator')
    def test_run_full_migration(self, mock_migrator_class):
        """Test full migration convenience function."""
        mock_migrator = MagicMock()
        mock_migrator.perform_full_migration.return_value = {'success': True}
        mock_migrator_class.return_value = mock_migrator
        
        result = run_full_migration()
        
        assert result['success']
        mock_migrator.perform_full_migration.assert_called_once()


class TestBackwardCompatibility:
    """Test backward compatibility features."""
    
    def test_old_data_format_compatibility(self):
        """Test that old data formats can still be read."""
        # This would test that the new system can read old data formats
        # without requiring migration in simple cases
        pass
    
    def test_api_compatibility(self):
        """Test that old API calls still work."""
        # This would test that any old function calls or interfaces
        # still work with the new system
        pass


if __name__ == "__main__":
    pytest.main([__file__])