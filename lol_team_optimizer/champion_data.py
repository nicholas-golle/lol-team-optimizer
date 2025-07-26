"""
Champion data management for the League of Legends Team Optimizer.

This module handles fetching and caching champion information from the Data Dragon API,
including champion names, IDs, and role classifications.
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .config import Config


@dataclass
class ChampionInfo:
    """Information about a League of Legends champion."""
    champion_id: int
    name: str
    title: str
    tags: List[str]  # Primary roles/classifications
    key: str  # Champion key (string ID)


class ChampionDataManager:
    """
    Manages champion data from Riot's Data Dragon API.
    
    Handles fetching, caching, and mapping champion information including
    champion IDs, names, and role classifications.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the champion data manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Data Dragon configuration
        self.data_dragon_version = "15.14.1"  # Current patch version
        self.data_dragon_language = "en_US"
        self.base_url = f"https://ddragon.leagueoflegends.com/cdn/{self.data_dragon_version}/data/{self.data_dragon_language}"
        
        # Cache configuration
        self.cache_dir = Path(config.cache_directory) / "champion_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "champions.json"
        self.cache_duration = timedelta(days=7)  # Champions don't change often
        
        # Champion data storage
        self.champions: Dict[int, ChampionInfo] = {}
        self.champion_name_to_id: Dict[str, int] = {}
        self.role_mappings: Dict[str, Set[int]] = {
            'top': set(),
            'jungle': set(), 
            'middle': set(),
            'support': set(),
            'bottom': set()
        }
        
        # Load cached data on initialization
        self._load_cached_data()
        
        # Clean up any old champion data files
        self._cleanup_old_champion_files()
    
    def fetch_champion_list(self, force_refresh: bool = False) -> bool:
        """
        Fetch champion data from Data Dragon API.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            True if data was successfully fetched, False otherwise
        """
        try:
            # Check if we need to refresh
            if not force_refresh and self._is_cache_valid():
                self.logger.info("Champion data cache is valid, skipping fetch")
                return True
            
            self.logger.info("Fetching champion data from Data Dragon API")
            
            # Fetch champion data
            url = f"{self.base_url}/champion.json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse champion data
            self._parse_champion_data(data)
            
            # Cache the data
            self._save_cache(data)
            
            self.logger.info(f"Successfully fetched data for {len(self.champions)} champions")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch champion data: {e}")
            return False
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(f"Failed to parse champion data: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error fetching champion data: {e}")
            return False
    
    def get_champion_name(self, champion_id: int) -> Optional[str]:
        """
        Get champion name by ID.
        
        Args:
            champion_id: Champion ID
            
        Returns:
            Champion name or None if not found
        """
        champion = self.champions.get(champion_id)
        return champion.name if champion else None
    
    def get_champion_id(self, champion_name: str) -> Optional[int]:
        """
        Get champion ID by name.
        
        Args:
            champion_name: Champion name
            
        Returns:
            Champion ID or None if not found
        """
        return self.champion_name_to_id.get(champion_name)
    
    def get_champion_info(self, champion_id: int) -> Optional[ChampionInfo]:
        """
        Get complete champion information by ID.
        
        Args:
            champion_id: Champion ID
            
        Returns:
            ChampionInfo object or None if not found
        """
        return self.champions.get(champion_id)
    
    def get_champion_roles(self, champion_id: int) -> List[str]:
        """
        Determine primary roles for a champion based on their tags.
        
        Args:
            champion_id: Champion ID
            
        Returns:
            List of roles this champion can play
        """
        champion = self.champions.get(champion_id)
        if not champion:
            return []
        
        # Map champion tags to our role system
        roles = []
        tags = [tag.lower() for tag in champion.tags]
        
        # Role mapping logic based on champion tags
        if 'fighter' in tags or 'tank' in tags:
            roles.append('top')
            if 'tank' in tags:
                roles.append('jungle')  # Many tanks can jungle
        
        if 'assassin' in tags:
            roles.extend(['middle', 'jungle'])
        
        if 'mage' in tags:
            roles.append('middle')
            if 'support' in champion.name.lower() or any(word in champion.name.lower() for word in ['lux', 'brand', 'zyra', 'vel']):
                roles.append('support')
        
        if 'marksman' in tags:
            roles.append('bottom')
        
        if 'support' in tags:
            roles.append('support')
        
        # Special cases for champions that don't fit standard patterns
        special_cases = self._get_special_role_cases()
        if champion_id in special_cases:
            roles = special_cases[champion_id]
        
        # Default to middle if no roles determined
        if not roles:
            roles = ['middle']
        
        return list(set(roles))  # Remove duplicates
    
    def get_champions_by_role(self, role: str) -> List[int]:
        """
        Get all champions that can play a specific role.
        
        Args:
            role: Role name (top, jungle, middle, support, bottom)
            
        Returns:
            List of champion IDs for that role
        """
        if role not in self.role_mappings:
            return []
        
        return list(self.role_mappings[role])
    
    def update_champion_cache(self) -> bool:
        """
        Force update of champion cache from Data Dragon.
        
        Returns:
            True if update was successful
        """
        return self.fetch_champion_list(force_refresh=True)
    
    def get_cache_info(self) -> Dict:
        """
        Get information about the champion data cache.
        
        Returns:
            Dictionary with cache information
        """
        cache_exists = self.cache_file.exists()
        cache_age = None
        cache_valid = False
        
        if cache_exists:
            cache_time = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
            cache_age = datetime.now() - cache_time
            cache_valid = cache_age < self.cache_duration
        
        return {
            'cache_exists': cache_exists,
            'cache_age_hours': cache_age.total_seconds() / 3600 if cache_age else None,
            'cache_valid': cache_valid,
            'champion_count': len(self.champions),
            'last_update': cache_time.isoformat() if cache_exists else None
        }
    
    def _load_cached_data(self) -> bool:
        """
        Load champion data from cache if available and valid.
        
        Returns:
            True if cache was loaded successfully
        """
        try:
            if not self.cache_file.exists():
                self.logger.info("No champion data cache found")
                return self.fetch_champion_list()
            
            if not self._is_cache_valid():
                self.logger.info("Champion data cache is expired")
                return self.fetch_champion_list()
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._parse_champion_data(data)
            self.logger.info(f"Loaded {len(self.champions)} champions from cache")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load cached champion data: {e}")
            return self.fetch_champion_list()
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache file is valid and not expired."""
        if not self.cache_file.exists():
            return False
        
        cache_time = datetime.fromtimestamp(self.cache_file.stat().st_mtime)
        return datetime.now() - cache_time < self.cache_duration
    
    def _save_cache(self, data: Dict) -> None:
        """
        Save champion data to cache file only if content has changed.
        
        Args:
            data: Champion data from Data Dragon API
        """
        try:
            # Check if file exists and compare content
            if self.cache_file.exists():
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Compare the actual champion data (ignore metadata like version)
                    existing_champions = existing_data.get('data', {})
                    new_champions = data.get('data', {})
                    
                    if existing_champions == new_champions:
                        self.logger.info("Champion data unchanged, skipping cache update")
                        return
                    else:
                        self.logger.info("Champion data has changed, updating cache")
                        
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Existing cache file corrupted, will overwrite: {e}")
            
            # Save the new data
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Champion data cached successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save champion data cache: {e}")
    
    def _cleanup_old_champion_files(self) -> None:
        """
        Clean up old champion data files that may have accumulated.
        
        Removes any files in the champion_data directory that aren't the main champions.json file.
        """
        try:
            if not self.cache_dir.exists():
                return
            
            # List all files in the champion data directory
            all_files = list(self.cache_dir.iterdir())
            
            # Keep only the main champions.json file
            files_to_remove = []
            for file_path in all_files:
                if file_path.is_file() and file_path.name != "champions.json":
                    files_to_remove.append(file_path)
            
            # Remove old files
            removed_count = 0
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                    removed_count += 1
                    self.logger.debug(f"Removed old champion data file: {file_path.name}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove old file {file_path.name}: {e}")
            
            if removed_count > 0:
                self.logger.info(f"Cleaned up {removed_count} old champion data files")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old champion files: {e}")
    
    def get_cache_info(self) -> Dict[str, any]:
        """
        Get information about the champion data cache.
        
        Returns:
            Dictionary with cache information
        """
        info = {
            'cache_file_exists': self.cache_file.exists(),
            'cache_file_path': str(self.cache_file),
            'cache_valid': self._is_cache_valid(),
            'champions_loaded': len(self.champions),
            'data_dragon_version': self.data_dragon_version
        }
        
        if self.cache_file.exists():
            try:
                stat = self.cache_file.stat()
                info['cache_file_size'] = stat.st_size
                info['cache_file_modified'] = datetime.fromtimestamp(stat.st_mtime)
            except Exception as e:
                self.logger.warning(f"Failed to get cache file stats: {e}")
        
        # Check for any remaining old files
        try:
            if self.cache_dir.exists():
                all_files = list(self.cache_dir.iterdir())
                old_files = [f for f in all_files if f.is_file() and f.name != "champions.json"]
                info['old_files_count'] = len(old_files)
                if old_files:
                    info['old_files'] = [f.name for f in old_files]
        except Exception:
            info['old_files_count'] = 0
        
        return info
    
    def _parse_champion_data(self, data: Dict) -> None:
        """
        Parse champion data from Data Dragon API response.
        
        Args:
            data: Raw champion data from API
        """
        self.champions.clear()
        self.champion_name_to_id.clear()
        
        # Reset role mappings
        for role in self.role_mappings:
            self.role_mappings[role].clear()
        
        champion_data = data.get('data', {})
        
        for champion_key, champion_info in champion_data.items():
            try:
                champion_id = int(champion_info['key'])
                name = champion_info['name']
                title = champion_info['title']
                tags = champion_info.get('tags', [])
                
                # Create champion info object
                champion = ChampionInfo(
                    champion_id=champion_id,
                    name=name,
                    title=title,
                    tags=tags,
                    key=champion_key
                )
                
                # Store champion data
                self.champions[champion_id] = champion
                self.champion_name_to_id[name] = champion_id
                
                # Map champion to roles
                roles = self.get_champion_roles(champion_id)
                for role in roles:
                    if role in self.role_mappings:
                        self.role_mappings[role].add(champion_id)
                
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Failed to parse champion {champion_key}: {e}")
                continue
    
    def _get_special_role_cases(self) -> Dict[int, List[str]]:
        """
        Get special cases for champions that don't fit standard role mappings.
        
        Returns:
            Dictionary mapping champion IDs to their actual roles
        """
        # This would be expanded based on game knowledge
        # For now, just a few examples
        special_cases = {
            # Graves (104) - Primarily jungle despite being marksman
            104: ['jungle'],
            # Kindred (203) - Jungle marksman
            203: ['jungle'],
            # Teemo (17) - Can play top despite being marksman
            17: ['top'],
            # Yasuo (157) - Can play both mid and bottom
            157: ['middle', 'bottom'],
            # Pyke (555) - Support assassin
            555: ['support'],
            # Senna (235) - Can play both support and bottom
            235: ['support', 'bottom'],
        }
        
        return special_cases