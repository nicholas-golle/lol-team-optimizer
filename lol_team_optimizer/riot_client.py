"""
Riot Games API client with rate limiting and caching.

This module provides an interface to the Riot Games API for fetching player data,
match history, and ranked statistics with proper rate limiting and error handling.
"""

import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass

from .config import Config


@dataclass
class CacheEntry:
    """Represents a cached API response with expiration."""
    data: Any
    timestamp: datetime
    expires_at: datetime


class RateLimiter:
    """Implements rate limiting with exponential backoff for API requests."""
    
    def __init__(self, max_requests: int = 120, time_window: int = 120):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (default: 120 for 2 minutes)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []  # List of request timestamps
        
    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits."""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.time_window]
        
        return len(self.requests) < self.max_requests
    
    def record_request(self):
        """Record a request timestamp."""
        self.requests.append(time.time())
    
    def wait_time(self) -> float:
        """Calculate how long to wait before next request is allowed."""
        if self.can_make_request():
            return 0.0
        
        now = time.time()
        oldest_request = min(self.requests)
        return self.time_window - (now - oldest_request)


class RiotAPIClient:
    """
    Client for interacting with the Riot Games API.
    
    Provides methods for fetching summoner data, match history, and ranked statistics
    with built-in rate limiting, caching, and error handling.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the Riot API client.
        
        Args:
            config: Application configuration containing API key and settings
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rate_limiter = RateLimiter(
            max_requests=config.riot_api_rate_limit,
            time_window=120  # 2 minutes
        )
        self.cache: Dict[str, CacheEntry] = {}
        self.session = requests.Session()
        self.session.headers.update({
            'X-Riot-Token': config.riot_api_key,
            'Accept': 'application/json'
        })
        
        # Ensure cache directory exists
        self.cache_dir = Path(config.cache_directory)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load persistent cache
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk."""
        cache_file = self.cache_dir / "api_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                for key, entry_data in cache_data.items():
                    expires_at = datetime.fromisoformat(entry_data['expires_at'])
                    if expires_at > datetime.now():
                        self.cache[key] = CacheEntry(
                            data=entry_data['data'],
                            timestamp=datetime.fromisoformat(entry_data['timestamp']),
                            expires_at=expires_at
                        )
            except (json.JSONDecodeError, KeyError, ValueError):
                # If cache is corrupted, start fresh
                pass
    
    def _save_cache(self):
        """Save cache to disk."""
        cache_file = self.cache_dir / "api_cache.json"
        cache_data = {}
        
        for key, entry in self.cache.items():
            if entry.expires_at > datetime.now():
                cache_data[key] = {
                    'data': entry.data,
                    'timestamp': entry.timestamp.isoformat(),
                    'expires_at': entry.expires_at.isoformat()
                }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for an API request."""
        # Create a deterministic key from endpoint and parameters
        param_str = json.dumps(params, sort_keys=True)
        key_data = f"{endpoint}:{param_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from cache if available and not expired."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if entry.expires_at > datetime.now():
                return entry.data
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    def _store_in_cache(self, cache_key: str, data: Any):
        """Store data in cache with expiration."""
        expires_at = datetime.now() + timedelta(hours=self.config.cache_duration_hours)
        self.cache[cache_key] = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            expires_at=expires_at
        )
        self._save_cache()
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        if params is None:
            params = {}
        
        # Check cache first
        cache_key = self._get_cache_key(endpoint, params)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        url = f"{self.config.riot_api_base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            # Wait for rate limit if necessary
            if not self.rate_limiter.can_make_request():
                wait_time = self.rate_limiter.wait_time()
                if wait_time > 0:
                    time.sleep(wait_time)
            
            try:
                self.rate_limiter.record_request()
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.request_timeout_seconds
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._store_in_cache(cache_key, data)
                    return data
                elif response.status_code == 404:
                    # Not found - don't retry, raise immediately
                    raise requests.RequestException(f"Resource not found: {url}")
                elif response.status_code == 429:  # Rate limited
                    # Extract retry-after header if available
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        time.sleep(int(retry_after))
                    else:
                        # Exponential backoff
                        backoff_time = (self.config.retry_backoff_factor ** attempt)
                        time.sleep(backoff_time)
                    continue  # Continue to next iteration
                else:
                    # For other status codes, raise for status which will be caught and retried
                    response.raise_for_status()
                    
            except requests.RequestException as e:
                # If this is our custom 404 exception, don't retry
                if "Resource not found" in str(e):
                    raise e
                
                if attempt == self.config.max_retries - 1:
                    raise e
                
                # Exponential backoff for retries
                backoff_time = (self.config.retry_backoff_factor ** attempt)
                time.sleep(backoff_time)
        
        raise requests.RequestException(f"Failed to fetch data from {url} after {self.config.max_retries} attempts")
    
    def get_account_by_riot_id(self, game_name: str, tag_line: str, region: str = "americas") -> Dict[str, Any]:
        """
        Fetch account data by Riot ID (gameName#tagLine).
        
        Args:
            game_name: The account's game name (before the #)
            tag_line: The account's tag line (after the #)
            region: Regional routing value (americas, asia, europe)
            
        Returns:
            Account data including puuid
        """
        endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        # Use regional routing endpoint
        regional_url = f"https://{region}.api.riotgames.com"
        
        # Temporarily override base URL for this request
        original_base_url = self.config.riot_api_base_url
        self.config.riot_api_base_url = regional_url
        
        try:
            return self._make_request(endpoint)
        finally:
            self.config.riot_api_base_url = original_base_url
    
    def get_summoner_by_puuid(self, puuid: str, region: str = "na1") -> Dict[str, Any]:
        """
        Fetch summoner data by PUUID.
        
        Args:
            puuid: The account's PUUID
            region: Platform routing value (na1, euw1, etc.)
            
        Returns:
            Summoner data including summoner level, etc.
        """
        endpoint = f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        # Use platform endpoint for summoner data
        platform_url = f"https://{region}.api.riotgames.com"
        
        # Temporarily override base URL for this request
        original_base_url = self.config.riot_api_base_url
        self.config.riot_api_base_url = platform_url
        
        try:
            return self._make_request(endpoint)
        finally:
            self.config.riot_api_base_url = original_base_url
    
    def get_summoner_data(self, riot_id: str, region: str = "americas", platform: str = "na1") -> Dict[str, Any]:
        """
        Fetch complete summoner data by Riot ID.
        
        Args:
            riot_id: The Riot ID in format "gameName#tagLine"
            region: Regional routing value (americas, asia, europe)
            platform: Platform routing value (na1, euw1, etc.)
            
        Returns:
            Combined account and summoner data
        """
        # Parse Riot ID
        if '#' not in riot_id:
            raise ValueError("Riot ID must be in format 'gameName#tagLine'")
        
        game_name, tag_line = riot_id.split('#', 1)
        
        # Get account data first
        account_data = self.get_account_by_riot_id(game_name, tag_line, region)
        puuid = account_data.get('puuid')
        
        if not puuid:
            raise ValueError(f"Could not retrieve PUUID for {riot_id}")
        
        # Get summoner data using PUUID
        summoner_data = self.get_summoner_by_puuid(puuid, platform)
        
        # Combine the data
        return {
            **account_data,
            **summoner_data
        }
    
    def get_match_history(self, puuid: str, count: int = 20, queue: Optional[int] = None, start: int = 0) -> List[str]:
        """
        Fetch match history for a player, filtered for Summoner's Rift games.
        
        Args:
            puuid: Player's PUUID
            count: Number of matches to retrieve (max 100)
            queue: Queue ID to filter by (optional, defaults to Summoner's Rift queues)
            start: Starting index for pagination (default 0)
            
        Returns:
            List of match IDs from Summoner's Rift games
        """
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {
            "count": min(count, 100),
            "start": start
        }
        
        if queue is not None:
            params["queue"] = queue
        else:
            # Filter for Summoner's Rift queues only
            # 420 = Ranked Solo/Duo, 440 = Ranked Flex, 400 = Normal Draft, 430 = Normal Blind
            summoners_rift_queues = [420, 440, 400, 430]
            # Note: API doesn't support multiple queue filters, so we'll filter after fetching
            pass
        
        match_ids = self._make_request(endpoint, params)
        
        # If no specific queue was requested, filter for Summoner's Rift games
        if queue is None and match_ids:
            filtered_matches = []
            summoners_rift_queues = {420, 440, 400, 430}  # Ranked Solo/Duo, Ranked Flex, Normal Draft, Normal Blind
            
            for match_id in match_ids:
                try:
                    match_details = self.get_match_details(match_id)
                    queue_id = match_details.get('info', {}).get('queueId')
                    if queue_id in summoners_rift_queues:
                        filtered_matches.append(match_id)
                    
                    # Stop when we have enough Summoner's Rift matches
                    if len(filtered_matches) >= count:
                        break
                        
                except Exception as e:
                    # Skip matches that can't be fetched
                    continue
            
            return filtered_matches
        
        return match_ids
    
    def get_match_details(self, match_id: str) -> Dict[str, Any]:
        """
        Fetch detailed match data.
        
        Args:
            match_id: Match identifier
            
        Returns:
            Detailed match information
        """
        endpoint = f"/lol/match/v5/matches/{match_id}"
        return self._make_request(endpoint)
    
    def get_ranked_stats(self, summoner_id: str, region: str = "na1") -> List[Dict[str, Any]]:
        """
        Fetch ranked statistics for a summoner.
        
        Args:
            summoner_id: Summoner's encrypted ID
            region: Region to query (default: na1)
            
        Returns:
            List of ranked queue entries
        """
        endpoint = f"/lol/league/v4/entries/by-summoner/{summoner_id}"
        # Use regional endpoint for ranked data
        regional_url = f"https://{region}.api.riotgames.com"
        
        # Temporarily override base URL for this request
        original_base_url = self.config.riot_api_base_url
        self.config.riot_api_base_url = regional_url
        
        try:
            return self._make_request(endpoint)
        finally:
            self.config.riot_api_base_url = original_base_url
    
    def calculate_role_performance(self, matches: List[Dict[str, Any]], puuid: str, role: str) -> Dict[str, float]:
        """
        Calculate performance metrics for a specific role from match data.
        
        Args:
            matches: List of match detail objects
            puuid: Player's PUUID to identify their data in matches
            role: Role to analyze performance for
            
        Returns:
            Dictionary containing performance metrics
        """
        role_matches = []
        
        for match in matches:
            participants = match.get('info', {}).get('participants', [])
            
            # Find the player's data in this match
            player_data = None
            for participant in participants:
                if participant.get('puuid') == puuid:
                    player_data = participant
                    break
            
            if player_data and self._normalize_role(player_data.get('teamPosition', '')) == role:
                role_matches.append(player_data)
        
        if not role_matches:
            return {
                'matches_played': 0,
                'win_rate': 0.0,
                'avg_kda': 0.0,
                'avg_cs_per_min': 0.0,
                'avg_vision_score': 0.0,
                'recent_form': 0.0
            }
        
        # Calculate metrics
        wins = sum(1 for match in role_matches if match.get('win', False))
        total_kills = sum(match.get('kills', 0) for match in role_matches)
        total_deaths = sum(match.get('deaths', 0) for match in role_matches)
        total_assists = sum(match.get('assists', 0) for match in role_matches)
        total_cs = sum(match.get('totalMinionsKilled', 0) + match.get('neutralMinionsKilled', 0) 
                     for match in role_matches)
        total_vision = sum(match.get('visionScore', 0) for match in role_matches)
        
        # Calculate game durations (in minutes)
        total_duration = 0
        for i, match_data in enumerate(matches):
            if i < len(role_matches):
                duration_seconds = match_data.get('info', {}).get('gameDuration', 0)
                total_duration += duration_seconds / 60  # Convert to minutes
        
        num_matches = len(role_matches)
        avg_duration = total_duration / num_matches if num_matches > 0 else 1
        
        # Calculate KDA (avoid division by zero)
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1) / num_matches
        
        # Calculate recent form (simple trend based on recent wins)
        if num_matches >= 3:
            recent_matches = role_matches[-min(5, num_matches):]  # Last 5 matches or all if less
            recent_wins = sum(1 for match in recent_matches if match.get('win', False))
            recent_form = (recent_wins / len(recent_matches) - 0.5) * 2  # Scale to -1 to 1
        else:
            recent_form = 0.0
        
        return {
            'matches_played': num_matches,
            'win_rate': wins / num_matches,
            'avg_kda': avg_kda,
            'avg_cs_per_min': total_cs / total_duration if total_duration > 0 else 0,
            'avg_vision_score': total_vision / num_matches,
            'recent_form': recent_form
        }
    
    def _normalize_role(self, riot_role: str) -> str:
        """
        Normalize Riot API role names to our internal role names.
        
        Args:
            riot_role: Role name from Riot API
            
        Returns:
            Normalized role name
        """
        role_mapping = {
            'TOP': 'top',
            'JUNGLE': 'jungle',
            'MIDDLE': 'middle',
            'BOTTOM': 'bottom',
            'UTILITY': 'support'
        }
        return role_mapping.get(riot_role.upper(), 'unknown')
    
    def get_champion_mastery(self, puuid: str, champion_id: Optional[int] = None, region: str = "na1") -> Dict[str, Any]:
        """
        Fetch champion mastery data for a player.
        
        Args:
            puuid: Player's PUUID
            champion_id: Specific champion ID (optional, if None gets all masteries)
            region: Region to query (default: na1)
            
        Returns:
            Champion mastery data
        """
        # Store original base URL
        original_base_url = self.config.riot_api_base_url
        
        try:
            # Set platform-specific base URL
            self.config.riot_api_base_url = f"https://{region}.api.riotgames.com"
            
            if champion_id:
                # Get mastery for specific champion
                endpoint = f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_id}"
            else:
                # Get all champion masteries
                endpoint = f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}"
            
            return self._make_request(endpoint)
            
        finally:
            # Restore original base URL
            self.config.riot_api_base_url = original_base_url
    
    def get_all_champion_masteries(self, puuid: str, region: str = "na1") -> List[Dict[str, Any]]:
        """
        Fetch all champion mastery data for a player.
        
        Args:
            puuid: Player's PUUID
            region: Region to query (default: na1)
            
        Returns:
            List of champion mastery data
        """
        try:
            result = self.get_champion_mastery(puuid, region=region)
            # Ensure we return a list
            if isinstance(result, list):
                return result
            else:
                return [result] if result else []
        except Exception as e:
            self.logger.warning(f"Failed to fetch champion masteries for {puuid}: {e}")
            return []
    
    def get_top_champion_masteries(self, puuid: str, count: int = 10, region: str = "na1") -> List[Dict[str, Any]]:
        """
        Fetch top champion masteries for a player.
        
        Args:
            puuid: Player's PUUID
            count: Number of top masteries to return
            region: Region to query (default: na1)
            
        Returns:
            List of top champion mastery data, sorted by mastery points
        """
        try:
            all_masteries = self.get_all_champion_masteries(puuid, region)
            
            # Sort by mastery points (descending) and take top N
            sorted_masteries = sorted(
                all_masteries, 
                key=lambda x: x.get('championPoints', 0), 
                reverse=True
            )
            
            return sorted_masteries[:count]
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch top champion masteries for {puuid}: {e}")
            return []
    
    def get_champion_mastery_score(self, puuid: str, region: str = "na1") -> int:
        """
        Fetch total mastery score for a player.
        
        Args:
            puuid: Player's PUUID
            region: Region to query (default: na1)
            
        Returns:
            Total mastery score
        """
        # Store original base URL
        original_base_url = self.config.riot_api_base_url
        
        try:
            # Set platform-specific base URL
            self.config.riot_api_base_url = f"https://{region}.api.riotgames.com"
            
            endpoint = f"/lol/champion-mastery/v4/scores/by-puuid/{puuid}"
            result = self._make_request(endpoint)
            
            # The API returns just a number
            return result if isinstance(result, int) else 0
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch mastery score for {puuid}: {e}")
            return 0
        finally:
            # Restore original base URL
            self.config.riot_api_base_url = original_base_url
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        cache_file = self.cache_dir / "api_cache.json"
        if cache_file.exists():
            cache_file.unlink()