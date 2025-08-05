"""
Data migration system for League of Legends Team Optimizer.

This module handles migration of existing player data and ensures backward compatibility
when the streamlined interface is introduced.
"""

import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .config import Config
from .models import Player, ChampionMastery, PlayerSynergyData, SynergyDatabase
from .data_manager import DataManager


class MigrationError(Exception):
    """Exception raised during migration operations."""
    pass


class DataMigrator:
    """
    Handles migration of existing data to new streamlined format.
    
    Provides backward compatibility and rollback capabilities.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the data migrator."""
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        
        # Migration tracking
        self.migration_log_file = Path(self.config.data_directory) / "migration_log.json"
        self.backup_directory = Path(self.config.data_directory) / "backups"
        
        # Ensure backup directory exists
        self.backup_directory.mkdir(parents=True, exist_ok=True)
    
    def check_migration_needed(self) -> Dict[str, Any]:
        """
        Check if migration is needed and what type of migration.
        
        Returns:
            Dictionary with migration status and recommendations
        """
        status = {
            'migration_needed': False,
            'backup_recommended': False,
            'issues_found': [],
            'data_summary': {},
            'compatibility_status': 'compatible'
        }
        
        try:
            # Check if player data exists
            player_data_file = Path(self.config.data_directory) / self.config.player_data_file
            if player_data_file.exists():
                with open(player_data_file, 'r', encoding='utf-8') as f:
                    player_data = json.load(f)
                
                status['data_summary']['player_count'] = len(player_data)
                
                # Check for old data format indicators
                if player_data and isinstance(player_data, list):
                    sample_player = player_data[0]
                    
                    # Check for missing fields that new system expects
                    missing_fields = []
                    expected_fields = ['name', 'summoner_name', 'role_preferences', 
                                     'performance_cache', 'champion_masteries', 
                                     'role_champion_pools', 'last_updated']
                    
                    for field in expected_fields:
                        if field not in sample_player:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        status['migration_needed'] = True
                        status['issues_found'].append(f"Missing fields: {missing_fields}")
                    
                    # Check for old datetime format
                    if 'last_updated' in sample_player:
                        if isinstance(sample_player['last_updated'], str):
                            try:
                                datetime.fromisoformat(sample_player['last_updated'])
                            except ValueError:
                                status['migration_needed'] = True
                                status['issues_found'].append("Old datetime format detected")
                    
                    # Check for old champion mastery format
                    if 'champion_masteries' in sample_player:
                        masteries = sample_player['champion_masteries']
                        if masteries and isinstance(masteries, dict):
                            # Check if masteries are in old format (missing required fields)
                            sample_mastery = next(iter(masteries.values()))
                            if isinstance(sample_mastery, dict):
                                required_mastery_fields = ['champion_id', 'champion_name', 
                                                         'mastery_level', 'mastery_points']
                                missing_mastery_fields = [f for f in required_mastery_fields 
                                                         if f not in sample_mastery]
                                if missing_mastery_fields:
                                    status['migration_needed'] = True
                                    status['issues_found'].append(f"Old mastery format: missing {missing_mastery_fields}")
            
            # Check cache data
            cache_dir = Path(self.config.cache_directory)
            if cache_dir.exists():
                cache_files = list(cache_dir.glob("*.json"))
                status['data_summary']['cache_files'] = len(cache_files)
                
                # Check for old cache format
                old_cache_file = cache_dir / "api_cache.json"
                if old_cache_file.exists():
                    try:
                        with open(old_cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        # Check if it's in old format (single large file vs individual files)
                        if len(cache_data) > 100:  # Arbitrary threshold
                            status['migration_needed'] = True
                            status['issues_found'].append("Large monolithic cache file detected")
                    except (json.JSONDecodeError, IOError) as e:
                        status['issues_found'].append(f"Cache file corruption: {e}")
            
            # Check synergy data
            synergy_file = cache_dir / "synergy_data.json"
            if synergy_file.exists():
                try:
                    with open(synergy_file, 'r', encoding='utf-8') as f:
                        synergy_data = json.load(f)
                    
                    status['data_summary']['synergy_pairs'] = len(synergy_data.get('synergies', {}))
                    
                    # Check for old synergy format
                    if 'synergies' in synergy_data:
                        synergies = synergy_data['synergies']
                        if synergies:
                            sample_key = next(iter(synergies.keys()))
                            sample_synergy = synergies[sample_key]
                            
                            # Check for missing fields in new format
                            expected_synergy_fields = ['games_together', 'wins_together', 
                                                     'role_combinations', 'champion_combinations']
                            missing_synergy_fields = [f for f in expected_synergy_fields 
                                                     if f not in sample_synergy]
                            if missing_synergy_fields:
                                status['migration_needed'] = True
                                status['issues_found'].append(f"Old synergy format: missing {missing_synergy_fields}")
                
                except (json.JSONDecodeError, IOError) as e:
                    status['issues_found'].append(f"Synergy file corruption: {e}")
            
            # Determine compatibility status
            if status['migration_needed']:
                status['compatibility_status'] = 'migration_required'
                status['backup_recommended'] = True
            elif status['issues_found']:
                status['compatibility_status'] = 'issues_detected'
                status['backup_recommended'] = True
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error checking migration status: {e}")
            status['issues_found'].append(f"Migration check failed: {e}")
            status['compatibility_status'] = 'unknown'
            return status
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        Create a backup of all current data.
        
        Args:
            backup_name: Optional custom backup name
            
        Returns:
            Path to the created backup directory
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        backup_path = self.backup_directory / backup_name
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except (OSError, FileExistsError) as e:
            if backup_path.exists() and backup_path.is_file():
                raise MigrationError(f"Cannot create backup directory - file exists with same name: {backup_path}")
            raise MigrationError(f"Failed to create backup directory: {e}")
        
        try:
            # Backup player data
            player_data_file = Path(self.config.data_directory) / self.config.player_data_file
            if player_data_file.exists():
                shutil.copy2(player_data_file, backup_path / self.config.player_data_file)
                self.logger.info(f"Backed up player data to {backup_path}")
            
            # Backup cache directory
            cache_dir = Path(self.config.cache_directory)
            if cache_dir.exists():
                cache_backup_dir = backup_path / "cache"
                shutil.copytree(cache_dir, cache_backup_dir, dirs_exist_ok=True)
                self.logger.info(f"Backed up cache data to {cache_backup_dir}")
            
            # Create backup manifest
            manifest = {
                'backup_name': backup_name,
                'created_at': datetime.now().isoformat(),
                'original_data_directory': str(self.config.data_directory),
                'original_cache_directory': str(self.config.cache_directory),
                'files_backed_up': []
            }
            
            # List all backed up files
            for file_path in backup_path.rglob("*"):
                if file_path.is_file():
                    manifest['files_backed_up'].append(str(file_path.relative_to(backup_path)))
            
            with open(backup_path / "backup_manifest.json", 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise MigrationError(f"Backup creation failed: {e}")
    
    def migrate_player_data(self) -> Dict[str, Any]:
        """
        Migrate player data to new format.
        
        Returns:
            Migration results summary
        """
        results = {
            'players_migrated': 0,
            'players_skipped': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            player_data_file = Path(self.config.data_directory) / self.config.player_data_file
            if not player_data_file.exists():
                results['warnings'].append("No player data file found")
                return results
            
            # Load existing data
            with open(player_data_file, 'r', encoding='utf-8') as f:
                player_data = json.load(f)
            
            if not isinstance(player_data, list):
                raise MigrationError("Player data is not in expected list format")
            
            migrated_players = []
            
            for player_dict in player_data:
                try:
                    migrated_player = self._migrate_single_player(player_dict)
                    migrated_players.append(migrated_player)
                    results['players_migrated'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate player {player_dict.get('name', 'unknown')}: {e}")
                    results['errors'].append(f"Player {player_dict.get('name', 'unknown')}: {e}")
                    results['players_skipped'] += 1
            
            # Save migrated data
            if migrated_players:
                data_manager = DataManager(self.config)
                data_manager.save_player_data(migrated_players)
                self.logger.info(f"Migrated {len(migrated_players)} players")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Player data migration failed: {e}")
            results['errors'].append(f"Migration failed: {e}")
            return results
    
    def _migrate_single_player(self, player_dict: Dict[str, Any]) -> Player:
        """
        Migrate a single player's data to new format.
        
        Args:
            player_dict: Player data dictionary
            
        Returns:
            Migrated Player object
        """
        # Ensure required fields exist with defaults
        migrated_data = {
            'name': player_dict.get('name', ''),
            'summoner_name': player_dict.get('summoner_name', ''),
            'puuid': player_dict.get('puuid', ''),
            'role_preferences': player_dict.get('role_preferences', {}),
            'performance_cache': player_dict.get('performance_cache', {}),
            'champion_masteries': {},
            'role_champion_pools': player_dict.get('role_champion_pools', {}),
            'last_updated': None
        }
        
        # Migrate datetime field
        if 'last_updated' in player_dict and player_dict['last_updated']:
            if isinstance(player_dict['last_updated'], str):
                try:
                    migrated_data['last_updated'] = datetime.fromisoformat(player_dict['last_updated'])
                except ValueError:
                    # Handle old datetime formats
                    try:
                        migrated_data['last_updated'] = datetime.strptime(
                            player_dict['last_updated'], "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        migrated_data['last_updated'] = datetime.now()
            else:
                migrated_data['last_updated'] = datetime.now()
        else:
            migrated_data['last_updated'] = datetime.now()
        
        # Migrate champion masteries
        if 'champion_masteries' in player_dict and player_dict['champion_masteries']:
            masteries = player_dict['champion_masteries']
            for champ_id_str, mastery_data in masteries.items():
                try:
                    champ_id = int(champ_id_str)
                    
                    if isinstance(mastery_data, dict):
                        # Ensure all required fields exist
                        mastery_dict = {
                            'champion_id': mastery_data.get('champion_id', champ_id),
                            'champion_name': mastery_data.get('champion_name', ''),
                            'mastery_level': mastery_data.get('mastery_level', 0),
                            'mastery_points': mastery_data.get('mastery_points', 0),
                            'chest_granted': mastery_data.get('chest_granted', False),
                            'tokens_earned': mastery_data.get('tokens_earned', 0),
                            'primary_roles': mastery_data.get('primary_roles', []),
                            'last_play_time': None
                        }
                        
                        # Handle last_play_time migration
                        if 'last_play_time' in mastery_data and mastery_data['last_play_time']:
                            if isinstance(mastery_data['last_play_time'], str):
                                try:
                                    mastery_dict['last_play_time'] = datetime.fromisoformat(mastery_data['last_play_time'])
                                except ValueError:
                                    mastery_dict['last_play_time'] = None
                        
                        migrated_data['champion_masteries'][champ_id] = ChampionMastery(**mastery_dict)
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Skipping invalid mastery data for champion {champ_id_str}: {e}")
        
        # Ensure role preferences have all roles
        if not migrated_data['role_preferences']:
            roles = ["top", "jungle", "middle", "support", "bottom"]
            migrated_data['role_preferences'] = {role: 3 for role in roles}
        else:
            # Fill missing roles with default preference
            roles = ["top", "jungle", "middle", "support", "bottom"]
            for role in roles:
                if role not in migrated_data['role_preferences']:
                    migrated_data['role_preferences'][role] = 3
        
        # Ensure role champion pools have all roles
        if not migrated_data['role_champion_pools']:
            roles = ["top", "jungle", "middle", "support", "bottom"]
            migrated_data['role_champion_pools'] = {role: [] for role in roles}
        else:
            # Fill missing roles with empty lists
            roles = ["top", "jungle", "middle", "support", "bottom"]
            for role in roles:
                if role not in migrated_data['role_champion_pools']:
                    migrated_data['role_champion_pools'][role] = []
        
        return Player(**migrated_data)
    
    def migrate_cache_data(self) -> Dict[str, Any]:
        """
        Migrate cache data to new format.
        
        Returns:
            Migration results summary
        """
        results = {
            'cache_files_processed': 0,
            'cache_entries_migrated': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            cache_dir = Path(self.config.cache_directory)
            if not cache_dir.exists():
                results['warnings'].append("No cache directory found")
                return results
            
            # Check for old monolithic cache file
            old_cache_file = cache_dir / "api_cache.json"
            if old_cache_file.exists():
                try:
                    with open(old_cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    # If it's a large monolithic file, split it into individual files
                    if len(cache_data) > 50:  # Threshold for splitting
                        for cache_key, cache_entry in cache_data.items():
                            individual_cache_file = cache_dir / f"{cache_key}.json"
                            
                            # Ensure cache entry has proper format
                            if isinstance(cache_entry, dict) and 'data' in cache_entry:
                                with open(individual_cache_file, 'w', encoding='utf-8') as f:
                                    json.dump(cache_entry, f, indent=2, ensure_ascii=False, default=str)
                                results['cache_entries_migrated'] += 1
                        
                        # Rename old file to avoid conflicts
                        old_cache_backup = cache_dir / "api_cache_old.json"
                        old_cache_file.rename(old_cache_backup)
                        results['warnings'].append(f"Old cache file renamed to {old_cache_backup}")
                    
                    results['cache_files_processed'] += 1
                    
                except (json.JSONDecodeError, IOError) as e:
                    results['errors'].append(f"Failed to process old cache file: {e}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cache data migration failed: {e}")
            results['errors'].append(f"Cache migration failed: {e}")
            return results
    
    def migrate_synergy_data(self) -> Dict[str, Any]:
        """
        Migrate synergy data to new format.
        
        Returns:
            Migration results summary
        """
        results = {
            'synergy_pairs_migrated': 0,
            'synergy_pairs_skipped': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            cache_dir = Path(self.config.cache_directory)
            synergy_file = cache_dir / "synergy_data.json"
            
            if not synergy_file.exists():
                results['warnings'].append("No synergy data file found")
                return results
            
            with open(synergy_file, 'r', encoding='utf-8') as f:
                synergy_data = json.load(f)
            
            if 'synergies' not in synergy_data:
                results['warnings'].append("No synergies found in data file")
                return results
            
            # Migrate synergy data format if needed
            migrated_synergies = {}
            
            for synergy_key, synergy_info in synergy_data['synergies'].items():
                try:
                    # Ensure all required fields exist
                    migrated_synergy = {
                        'games_together': synergy_info.get('games_together', 0),
                        'wins_together': synergy_info.get('wins_together', 0),
                        'losses_together': synergy_info.get('losses_together', 0),
                        'avg_combined_kda': synergy_info.get('avg_combined_kda', 0.0),
                        'avg_game_duration': synergy_info.get('avg_game_duration', 0.0),
                        'avg_vision_score_combined': synergy_info.get('avg_vision_score_combined', 0.0),
                        'recent_games_together': synergy_info.get('recent_games_together', 0),
                        'last_played_together': synergy_info.get('last_played_together'),
                        'role_combinations': synergy_info.get('role_combinations', {}),
                        'champion_combinations': synergy_info.get('champion_combinations', {})
                    }
                    
                    migrated_synergies[synergy_key] = migrated_synergy
                    results['synergy_pairs_migrated'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Skipping synergy pair {synergy_key}: {e}")
                    results['synergy_pairs_skipped'] += 1
            
            # Save migrated synergy data
            if migrated_synergies:
                migrated_data = {
                    'synergies': migrated_synergies,
                    'last_updated': datetime.now().isoformat()
                }
                
                with open(synergy_file, 'w', encoding='utf-8') as f:
                    json.dump(migrated_data, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"Migrated {len(migrated_synergies)} synergy pairs")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Synergy data migration failed: {e}")
            results['errors'].append(f"Synergy migration failed: {e}")
            return results
    
    def perform_full_migration(self) -> Dict[str, Any]:
        """
        Perform complete migration of all data.
        
        Returns:
            Comprehensive migration results
        """
        migration_start = datetime.now()
        
        # Create backup first
        try:
            backup_path = self.create_backup()
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to create backup: {e}",
                'backup_path': None
            }
        
        # Perform migrations
        player_results = self.migrate_player_data()
        cache_results = self.migrate_cache_data()
        synergy_results = self.migrate_synergy_data()
        
        # Compile overall results
        overall_results = {
            'success': True,
            'migration_start': migration_start.isoformat(),
            'migration_end': datetime.now().isoformat(),
            'backup_path': backup_path,
            'player_migration': player_results,
            'cache_migration': cache_results,
            'synergy_migration': synergy_results,
            'total_errors': len(player_results['errors']) + len(cache_results['errors']) + len(synergy_results['errors']),
            'total_warnings': len(player_results['warnings']) + len(cache_results['warnings']) + len(synergy_results['warnings'])
        }
        
        # Log migration results
        self._log_migration_results(overall_results)
        
        # Check if migration was successful
        if overall_results['total_errors'] > 0:
            overall_results['success'] = False
            self.logger.error(f"Migration completed with {overall_results['total_errors']} errors")
        else:
            self.logger.info("Migration completed successfully")
        
        return overall_results
    
    def rollback_migration(self, backup_name: str) -> Dict[str, Any]:
        """
        Rollback to a previous backup.
        
        Args:
            backup_name: Name of the backup to restore
            
        Returns:
            Rollback results
        """
        results = {
            'success': False,
            'files_restored': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            backup_path = self.backup_directory / backup_name
            if not backup_path.exists():
                raise MigrationError(f"Backup {backup_name} not found")
            
            # Load backup manifest
            manifest_file = backup_path / "backup_manifest.json"
            if not manifest_file.exists():
                raise MigrationError(f"Backup manifest not found for {backup_name}")
            
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            # Restore player data
            player_backup = backup_path / self.config.player_data_file
            if player_backup.exists():
                player_target = Path(self.config.data_directory) / self.config.player_data_file
                shutil.copy2(player_backup, player_target)
                results['files_restored'] += 1
                self.logger.info(f"Restored player data from {player_backup}")
            
            # Restore cache data
            cache_backup = backup_path / "cache"
            if cache_backup.exists():
                cache_target = Path(self.config.cache_directory)
                
                # Remove current cache directory
                if cache_target.exists():
                    shutil.rmtree(cache_target)
                
                # Restore from backup
                shutil.copytree(cache_backup, cache_target)
                
                # Count restored files
                restored_cache_files = len(list(cache_target.rglob("*")))
                results['files_restored'] += restored_cache_files
                self.logger.info(f"Restored {restored_cache_files} cache files")
            
            results['success'] = True
            self.logger.info(f"Successfully rolled back to backup {backup_name}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            results['errors'].append(f"Rollback failed: {e}")
            return results
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            if not self.backup_directory.exists():
                return backups
            
            for backup_dir in self.backup_directory.iterdir():
                if backup_dir.is_dir():
                    manifest_file = backup_dir / "backup_manifest.json"
                    
                    backup_info = {
                        'name': backup_dir.name,
                        'path': str(backup_dir),
                        'created_at': None,
                        'file_count': 0,
                        'size_mb': 0.0
                    }
                    
                    # Load manifest if available
                    if manifest_file.exists():
                        try:
                            with open(manifest_file, 'r', encoding='utf-8') as f:
                                manifest = json.load(f)
                            
                            backup_info['created_at'] = manifest.get('created_at')
                            backup_info['file_count'] = len(manifest.get('files_backed_up', []))
                        
                        except (json.JSONDecodeError, IOError):
                            pass
                    
                    # Calculate size
                    total_size = 0
                    for file_path in backup_dir.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                    
                    backup_info['size_mb'] = total_size / (1024 * 1024)
                    
                    backups.append(backup_info)
            
            # Sort by creation date (newest first)
            backups.sort(key=lambda x: x['created_at'] or '', reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def _log_migration_results(self, results: Dict[str, Any]) -> None:
        """Log migration results to file."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'migration_results': results
            }
            
            # Load existing log or create new
            migration_log = []
            if self.migration_log_file.exists():
                try:
                    with open(self.migration_log_file, 'r', encoding='utf-8') as f:
                        migration_log = json.load(f)
                except (json.JSONDecodeError, IOError):
                    migration_log = []
            
            # Add new entry
            migration_log.append(log_entry)
            
            # Keep only last 10 entries
            migration_log = migration_log[-10:]
            
            # Save log
            with open(self.migration_log_file, 'w', encoding='utf-8') as f:
                json.dump(migration_log, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            self.logger.error(f"Failed to log migration results: {e}")


def create_compatibility_layer() -> None:
    """
    Create compatibility layer for old interfaces.
    
    This ensures that any old scripts or interfaces can still function
    with the new streamlined system.
    """
    # This would create wrapper functions or compatibility shims
    # For now, we'll just ensure the data format is compatible
    pass


def run_migration_check() -> Dict[str, Any]:
    """
    Convenience function to check if migration is needed.
    
    Returns:
        Migration status dictionary
    """
    migrator = DataMigrator()
    return migrator.check_migration_needed()


def run_full_migration() -> Dict[str, Any]:
    """
    Convenience function to run full migration.
    
    Returns:
        Migration results dictionary
    """
    migrator = DataMigrator()
    return migrator.perform_full_migration()