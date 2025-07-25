"""
Data persistence and management system for the League of Legends Team Optimizer.

This module handles saving/loading player data, preference management, and caching
with TTL (Time To Live) functionality.
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict, fields
from pathlib import Path

from .models import Player, PerformanceData
from .config import Config


class DataManager:
    """Manages data persistence and caching for the application."""
    
    def __init__(self, config: Config):
        """Initialize the DataManager with configuration."""
        self.config = config
        self.data_dir = Path(config.data_directory)
        self.cache_dir = Path(config.cache_directory)
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.player_data_file = self.data_dir / config.player_data_file
        self._players_cache: Dict[str, Player] = {}
        self._cache_last_loaded: Optional[datetime] = None
    
    def save_player_data(self, players: List[Player]) -> None:
        """
        Save player data to JSON file.
        
        Args:
            players: List of Player objects to save
            
        Raises:
            IOError: If unable to write to file
            ValueError: If player data is invalid
        """
        try:
            # Convert players to serializable format
            players_data = []
            for player in players:
                player_dict = asdict(player)
                # Convert datetime to ISO string for JSON serialization
                if player_dict['last_updated']:
                    player_dict['last_updated'] = player.last_updated.isoformat()
                
                # Convert ChampionMastery objects to dicts for JSON serialization
                if 'champion_masteries' in player_dict and player_dict['champion_masteries']:
                    masteries_dict = {}
                    for champ_id, mastery in player_dict['champion_masteries'].items():
                        mastery_dict = asdict(mastery) if hasattr(mastery, '__dict__') else mastery
                        # Convert datetime to ISO string if present
                        if mastery_dict.get('last_play_time'):
                            mastery_dict['last_play_time'] = mastery_dict['last_play_time'].isoformat()
                        masteries_dict[str(champ_id)] = mastery_dict
                    player_dict['champion_masteries'] = masteries_dict
                
                players_data.append(player_dict)
            
            # Write to temporary file first, then rename for atomic operation
            temp_file = self.player_data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(players_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_file.replace(self.player_data_file)
            
            # Update cache
            self._players_cache = {player.name: player for player in players}
            self._cache_last_loaded = datetime.now()
            
        except (IOError, OSError) as e:
            raise IOError(f"Failed to save player data: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid player data format: {e}")
    
    def load_player_data(self) -> List[Player]:
        """
        Load player data from JSON file.
        
        Returns:
            List of Player objects
            
        Raises:
            IOError: If unable to read file
            ValueError: If data format is invalid
        """
        # Check if we can use cached data
        if (self._players_cache and self._cache_last_loaded and 
            datetime.now() - self._cache_last_loaded < timedelta(hours=self.config.player_data_cache_hours)):
            return list(self._players_cache.values())
        
        if not self.player_data_file.exists():
            return []
        
        try:
            with open(self.player_data_file, 'r', encoding='utf-8') as f:
                players_data = json.load(f)
            
            # Validate that we have a list
            if not isinstance(players_data, list):
                raise ValueError("Player data must be a list of player objects")
            
            players = []
            for player_dict in players_data:
                # Validate that each item is a dictionary
                if not isinstance(player_dict, dict):
                    raise ValueError("Each player entry must be a dictionary")
                
                # Convert ISO string back to datetime
                if player_dict.get('last_updated'):
                    player_dict['last_updated'] = datetime.fromisoformat(player_dict['last_updated'])
                
                # Convert champion masteries from dicts to ChampionMastery objects
                if 'champion_masteries' in player_dict and player_dict['champion_masteries']:
                    from .models import ChampionMastery
                    masteries = {}
                    for champ_id_str, mastery_dict in player_dict['champion_masteries'].items():
                        if isinstance(mastery_dict, dict):
                            # Convert last_play_time if present
                            if mastery_dict.get('last_play_time'):
                                try:
                                    mastery_dict['last_play_time'] = datetime.fromisoformat(mastery_dict['last_play_time'])
                                except (ValueError, TypeError):
                                    mastery_dict['last_play_time'] = None
                            
                            mastery = ChampionMastery(**mastery_dict)
                            masteries[int(champ_id_str)] = mastery
                    player_dict['champion_masteries'] = masteries
                
                # Create Player object
                player = Player(**player_dict)
                players.append(player)
            
            # Update cache
            self._players_cache = {player.name: player for player in players}
            self._cache_last_loaded = datetime.now()
            
            return players
            
        except (IOError, OSError) as e:
            raise IOError(f"Failed to load player data: {e}")
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as e:
            raise ValueError(f"Invalid player data format in file: {e}")
    
    def get_player_by_name(self, name: str) -> Optional[Player]:
        """
        Get a specific player by name.
        
        Args:
            name: Player name to search for
            
        Returns:
            Player object if found, None otherwise
        """
        players = self.load_player_data()
        for player in players:
            if player.name == name:
                return player
        return None
    
    def update_player(self, updated_player: Player) -> None:
        """
        Update a specific player's data.
        
        Args:
            updated_player: Player object with updated data
        """
        players = self.load_player_data()
        
        # Find and update the player
        for i, player in enumerate(players):
            if player.name == updated_player.name:
                players[i] = updated_player
                break
        else:
            # Player not found, add as new
            players.append(updated_player)
        
        self.save_player_data(players)
    
    def update_preferences(self, player_name: str, preferences: Dict[str, int]) -> None:
        """
        Update role preferences for a specific player.
        
        Args:
            player_name: Name of the player to update
            preferences: Dictionary mapping role names to preference scores (1-5)
            
        Raises:
            ValueError: If player not found or preferences are invalid
        """
        # Validate preferences
        valid_roles = {"top", "jungle", "middle", "support", "bottom"}
        for role, score in preferences.items():
            if role not in valid_roles:
                raise ValueError(f"Invalid role: {role}")
            if not isinstance(score, int) or not 1 <= score <= 5:
                raise ValueError(f"Preference score must be integer between 1-5, got {score} for {role}")
        
        player = self.get_player_by_name(player_name)
        if not player:
            raise ValueError(f"Player '{player_name}' not found")
        
        # Update preferences and last_updated timestamp
        player.role_preferences.update(preferences)
        player.last_updated = datetime.now()
        
        self.update_player(player)
    
    def cache_api_data(self, data: Any, cache_key: str, ttl_hours: Optional[float] = None) -> None:
        """
        Cache API response data with TTL.
        
        Args:
            data: Data to cache (must be JSON serializable)
            cache_key: Unique key for the cached data
            ttl_hours: Time to live in hours (defaults to config cache_duration_hours)
        """
        if ttl_hours is None:
            ttl_hours = self.config.cache_duration_hours
        
        cache_entry = {
            'data': data,
            'timestamp': time.time(),
            'ttl_hours': ttl_hours
        }
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, indent=2, ensure_ascii=False, default=str)
        except (IOError, OSError, TypeError) as e:
            # Cache failures shouldn't break the application
            print(f"Warning: Failed to cache data for key '{cache_key}': {e}")
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached data if it hasn't expired.
        
        Args:
            cache_key: Key for the cached data
            
        Returns:
            Cached data if valid and not expired, None otherwise
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_entry = json.load(f)
            
            # Check if cache has expired
            cache_time = cache_entry['timestamp']
            ttl_seconds = cache_entry['ttl_hours'] * 3600
            
            if time.time() - cache_time > ttl_seconds:
                # Cache expired, remove file
                cache_file.unlink(missing_ok=True)
                return None
            
            return cache_entry['data']
            
        except (IOError, OSError, json.JSONDecodeError, KeyError) as e:
            # Remove corrupted cache file
            cache_file.unlink(missing_ok=True)
            return None
    
    def clear_expired_cache(self) -> int:
        """
        Remove all expired cache files.
        
        Returns:
            Number of files removed
        """
        removed_count = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                
                cache_time = cache_entry['timestamp']
                ttl_seconds = cache_entry['ttl_hours'] * 3600
                
                if current_time - cache_time > ttl_seconds:
                    cache_file.unlink()
                    removed_count += 1
                    
            except (IOError, OSError, json.JSONDecodeError, KeyError):
                # Remove corrupted cache files
                cache_file.unlink(missing_ok=True)
                removed_count += 1
        
        return removed_count
    
    def get_cache_size_mb(self) -> float:
        """
        Get the total size of cache directory in MB.
        
        Returns:
            Cache size in megabytes
        """
        total_size = 0
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                total_size += cache_file.stat().st_size
        
        return total_size / (1024 * 1024)  # Convert bytes to MB
    
    def cleanup_cache_if_needed(self) -> None:
        """
        Clean up cache if it exceeds the maximum size limit.
        Removes expired files first, then oldest files if still over limit.
        """
        # First remove expired files
        self.clear_expired_cache()
        
        # Check if still over limit
        if self.get_cache_size_mb() <= self.config.max_cache_size_mb:
            return
        
        # Get all cache files with their modification times
        cache_files = []
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.is_file():
                cache_files.append((cache_file.stat().st_mtime, cache_file))
        
        # Sort by modification time (oldest first)
        cache_files.sort()
        
        # Remove oldest files until under limit
        for _, cache_file in cache_files:
            if self.get_cache_size_mb() <= self.config.max_cache_size_mb:
                break
            cache_file.unlink(missing_ok=True)
    
    def batch_cache_api_data(self, data_batch: Dict[str, Any], ttl_hours: Optional[float] = None) -> None:
        """
        Cache multiple API responses in a single operation for efficiency.
        
        Args:
            data_batch: Dictionary of cache_key -> data mappings
            ttl_hours: Time to live in hours for all entries
        """
        if ttl_hours is None:
            ttl_hours = self.config.cache_duration_hours
        
        timestamp = time.time()
        
        for cache_key, data in data_batch.items():
            cache_entry = {
                'data': data,
                'timestamp': timestamp,
                'ttl_hours': ttl_hours
            }
            
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_entry, f, indent=2, ensure_ascii=False, default=str)
            except (IOError, OSError, TypeError) as e:
                print(f"Warning: Failed to cache data for key '{cache_key}': {e}")
    
    def get_multiple_cached_data(self, cache_keys: List[str]) -> Dict[str, Any]:
        """
        Retrieve multiple cached data entries efficiently.
        
        Args:
            cache_keys: List of cache keys to retrieve
            
        Returns:
            Dictionary of cache_key -> data for valid, non-expired entries
        """
        results = {}
        current_time = time.time()
        
        for cache_key in cache_keys:
            cache_file = self.cache_dir / f"{cache_key}.json"
            
            if not cache_file.exists():
                continue
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                
                # Check if cache has expired
                cache_time = cache_entry['timestamp']
                ttl_seconds = cache_entry['ttl_hours'] * 3600
                
                if current_time - cache_time <= ttl_seconds:
                    results[cache_key] = cache_entry['data']
                else:
                    # Cache expired, remove file
                    cache_file.unlink(missing_ok=True)
                    
            except (IOError, OSError, json.JSONDecodeError, KeyError):
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)
        
        return results
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get detailed cache statistics for monitoring and optimization.
        
        Returns:
            Dictionary containing cache statistics
        """
        stats = {
            'total_files': 0,
            'total_size_mb': 0.0,
            'expired_files': 0,
            'valid_files': 0,
            'corrupted_files': 0,
            'oldest_entry': None,
            'newest_entry': None,
            'cache_keys': []
        }
        
        current_time = time.time()
        oldest_time = float('inf')
        newest_time = 0
        
        for cache_file in self.cache_dir.glob("*.json"):
            if not cache_file.is_file():
                continue
            
            stats['total_files'] += 1
            stats['total_size_mb'] += cache_file.stat().st_size / (1024 * 1024)
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                
                cache_time = cache_entry['timestamp']
                ttl_seconds = cache_entry['ttl_hours'] * 3600
                
                if current_time - cache_time > ttl_seconds:
                    stats['expired_files'] += 1
                else:
                    stats['valid_files'] += 1
                
                # Track oldest and newest entries
                if cache_time < oldest_time:
                    oldest_time = cache_time
                    stats['oldest_entry'] = datetime.fromtimestamp(cache_time).isoformat()
                
                if cache_time > newest_time:
                    newest_time = cache_time
                    stats['newest_entry'] = datetime.fromtimestamp(cache_time).isoformat()
                
                # Extract cache key from filename
                cache_key = cache_file.stem
                stats['cache_keys'].append(cache_key)
                
            except (IOError, OSError, json.JSONDecodeError, KeyError):
                stats['corrupted_files'] += 1
        
        return stats
    
    def optimize_player_data_access(self, player_names: List[str]) -> Dict[str, Player]:
        """
        Efficiently load multiple players with optimized caching.
        
        Args:
            player_names: List of player names to load
            
        Returns:
            Dictionary of player_name -> Player object
        """
        # Check if we can use the full cache
        if (self._players_cache and self._cache_last_loaded and 
            datetime.now() - self._cache_last_loaded < timedelta(hours=self.config.player_data_cache_hours)):
            
            return {name: self._players_cache[name] for name in player_names 
                   if name in self._players_cache}
        
        # Load all players and filter
        all_players = self.load_player_data()
        player_dict = {player.name: player for player in all_players}
        
        return {name: player_dict[name] for name in player_names 
               if name in player_dict}
    
    def preload_performance_data(self, players: List[Player], roles: List[str]) -> None:
        """
        Preload performance data for multiple players and roles to optimize API calls.
        
        Args:
            players: List of players to preload data for
            roles: List of roles to preload data for
        """
        # This would be used by the riot client to batch API calls
        # For now, we'll update the performance cache timestamps to indicate freshness
        current_time = datetime.now()
        
        for player in players:
            for role in roles:
                if role in player.performance_cache:
                    # Mark as recently accessed for cache optimization
                    if 'last_accessed' not in player.performance_cache[role]:
                        player.performance_cache[role]['last_accessed'] = current_time.isoformat()
            
            # Update player's last_updated timestamp
            player.last_updated = current_time
        
        # Save updated player data
        all_players = self.load_player_data()
        player_dict = {p.name: p for p in all_players}
        
        for player in players:
            if player.name in player_dict:
                player_dict[player.name] = player
        
        self.save_player_data(list(player_dict.values()))
    
    def delete_player(self, player_name: str) -> bool:
        """
        Delete a player from the data store.
        
        Args:
            player_name: Name of the player to delete
            
        Returns:
            True if player was found and deleted, False otherwise
        """
        players = self.load_player_data()
        original_count = len(players)
        
        players = [p for p in players if p.name != player_name]
        
        if len(players) < original_count:
            self.save_player_data(players)
            return True
        
        return False
    
    def get_all_player_names(self) -> List[str]:
        """
        Get a list of all player names in the data store.
        
        Returns:
            List of player names
        """
        players = self.load_player_data()
        return [player.name for player in players]