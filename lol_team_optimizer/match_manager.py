"""
Centralized match storage and management system.

This module handles storing, retrieving, and deduplicating match data
to enable efficient analysis across all players.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import asdict

from .models import Match, MatchParticipant, ExtractionTracker, PlayerExtractionRange
from .config import Config


class MatchManager:
    """
    Manages centralized storage and retrieval of match data.
    
    Handles deduplication, efficient querying, and maintains relationships
    between matches and players in our database.
    """
    
    def __init__(self, config: Config):
        """Initialize the match manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Storage paths
        self.data_dir = Path(config.data_directory)
        self.matches_file = self.data_dir / "matches.json"
        self.match_index_file = self.data_dir / "match_index.json"
        self.extraction_tracker_file = self.data_dir / "extraction_tracker.json"
        
        # In-memory caches
        self._matches_cache: Dict[str, Match] = {}
        self._match_index: Dict[str, Set[str]] = {}  # puuid -> set of match_ids
        self._extraction_tracker: ExtractionTracker = ExtractionTracker()
        self._cache_last_loaded: Optional[datetime] = None
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Load existing data
        self._load_match_data()
    
    def _load_match_data(self) -> None:
        """Load match data and index from storage."""
        try:
            # Load matches
            if self.matches_file.exists():
                with open(self.matches_file, 'r', encoding='utf-8') as f:
                    matches_data = json.load(f)
                
                self._matches_cache = {}
                for match_data in matches_data:
                    match = self._deserialize_match(match_data)
                    self._matches_cache[match.match_id] = match
                
                self.logger.info(f"Loaded {len(self._matches_cache)} matches from storage")
            
            # Load match index
            if self.match_index_file.exists():
                with open(self.match_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                self._match_index = {}
                for puuid, match_ids in index_data.items():
                    self._match_index[puuid] = set(match_ids)
                
                self.logger.info(f"Loaded match index for {len(self._match_index)} players")
            
            # Load extraction tracker
            if self.extraction_tracker_file.exists():
                with open(self.extraction_tracker_file, 'r', encoding='utf-8') as f:
                    tracker_data = json.load(f)
                
                # Deserialize extraction tracker
                self._extraction_tracker = self._deserialize_extraction_tracker(tracker_data)
                self.logger.info(f"Loaded extraction tracker for {len(self._extraction_tracker.player_ranges)} players")
            
            self._cache_last_loaded = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to load match data: {e}")
            self._matches_cache = {}
            self._match_index = {}
    
    def _save_match_data(self) -> None:
        """Save match data and index to storage."""
        try:
            # Save matches
            matches_data = []
            for match in self._matches_cache.values():
                match_data = self._serialize_match(match)
                matches_data.append(match_data)
            
            # Atomic write for matches
            temp_file = self.matches_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(matches_data, f, indent=2, ensure_ascii=False, default=str)
            temp_file.replace(self.matches_file)
            
            # Save match index
            index_data = {}
            for puuid, match_ids in self._match_index.items():
                index_data[puuid] = list(match_ids)
            
            temp_index_file = self.match_index_file.with_suffix('.tmp')
            with open(temp_index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            temp_index_file.replace(self.match_index_file)
            
            # Save extraction tracker
            tracker_data = self._serialize_extraction_tracker(self._extraction_tracker)
            temp_tracker_file = self.extraction_tracker_file.with_suffix('.tmp')
            with open(temp_tracker_file, 'w', encoding='utf-8') as f:
                json.dump(tracker_data, f, indent=2, ensure_ascii=False, default=str)
            temp_tracker_file.replace(self.extraction_tracker_file)
            
            self.logger.info(f"Saved {len(self._matches_cache)} matches, index, and extraction tracker")
            
        except Exception as e:
            self.logger.error(f"Failed to save match data: {e}")
            raise
    
    def _serialize_match(self, match: Match) -> Dict[str, Any]:
        """Convert Match object to JSON-serializable dictionary."""
        match_dict = asdict(match)
        
        # Convert datetime objects to ISO strings
        if match_dict.get('stored_at'):
            match_dict['stored_at'] = match.stored_at.isoformat()
        if match_dict.get('last_updated'):
            match_dict['last_updated'] = match.last_updated.isoformat()
        
        return match_dict
    
    def _deserialize_match(self, match_data: Dict[str, Any]) -> Match:
        """Convert dictionary to Match object."""
        # Convert ISO strings back to datetime objects
        if match_data.get('stored_at'):
            match_data['stored_at'] = datetime.fromisoformat(match_data['stored_at'])
        if match_data.get('last_updated'):
            match_data['last_updated'] = datetime.fromisoformat(match_data['last_updated'])
        
        # Convert participants
        participants = []
        for p_data in match_data.get('participants', []):
            participant = MatchParticipant(**p_data)
            participants.append(participant)
        
        match_data['participants'] = participants
        
        return Match(**match_data)
    
    def _serialize_extraction_tracker(self, tracker: ExtractionTracker) -> Dict[str, Any]:
        """Convert ExtractionTracker to JSON-serializable dictionary."""
        tracker_dict = {
            'last_updated': tracker.last_updated.isoformat() if tracker.last_updated else None,
            'player_ranges': {}
        }
        
        for puuid, player_range in tracker.player_ranges.items():
            tracker_dict['player_ranges'][puuid] = {
                'puuid': player_range.puuid,
                'start_index': player_range.start_index,
                'end_index': player_range.end_index,
                'total_matches_available': player_range.total_matches_available,
                'last_extraction': player_range.last_extraction.isoformat() if player_range.last_extraction else None,
                'extraction_complete': player_range.extraction_complete
            }
        
        return tracker_dict
    
    def _deserialize_extraction_tracker(self, tracker_data: Dict[str, Any]) -> ExtractionTracker:
        """Convert dictionary to ExtractionTracker object."""
        tracker = ExtractionTracker()
        
        if tracker_data.get('last_updated'):
            tracker.last_updated = datetime.fromisoformat(tracker_data['last_updated'])
        
        for puuid, range_data in tracker_data.get('player_ranges', {}).items():
            player_range = PlayerExtractionRange(
                puuid=range_data['puuid'],
                start_index=range_data.get('start_index', 0),
                end_index=range_data.get('end_index', 0),
                total_matches_available=range_data.get('total_matches_available'),
                extraction_complete=range_data.get('extraction_complete', False)
            )
            
            if range_data.get('last_extraction'):
                player_range.last_extraction = datetime.fromisoformat(range_data['last_extraction'])
            
            tracker.player_ranges[puuid] = player_range
        
        return tracker
    
    def store_match(self, match_data: Dict[str, Any]) -> bool:
        """
        Store a match with deduplication.
        
        Args:
            match_data: Raw match data from Riot API
            
        Returns:
            True if match was stored (new), False if already existed
        """
        try:
            match = self._parse_riot_match_data(match_data)
            
            # Check if match already exists
            if match.match_id in self._matches_cache:
                self.logger.debug(f"Match {match.match_id} already exists, skipping")
                return False
            
            # Store the match
            self._matches_cache[match.match_id] = match
            
            # Update index for all participants
            for participant in match.participants:
                if participant.puuid not in self._match_index:
                    self._match_index[participant.puuid] = set()
                self._match_index[participant.puuid].add(match.match_id)
            
            # Save to disk immediately for single match storage
            self._save_match_data()
            
            self.logger.info(f"Stored new match {match.match_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store match: {e}")
            return False
    
    def store_matches_batch(self, matches_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Store multiple matches with deduplication.
        
        Args:
            matches_data: List of raw match data from Riot API
            
        Returns:
            Tuple of (new_matches_stored, duplicates_skipped)
        """
        new_count = 0
        duplicate_count = 0
        
        for match_data in matches_data:
            if self.store_match(match_data):
                new_count += 1
            else:
                duplicate_count += 1
        
        # Save to disk after batch operation
        if new_count > 0:
            self._save_match_data()
        
        self.logger.info(f"Batch stored {new_count} new matches, skipped {duplicate_count} duplicates")
        return new_count, duplicate_count
    
    def _parse_riot_match_data(self, match_data: Dict[str, Any]) -> Match:
        """Parse raw Riot API match data into our Match model."""
        info = match_data.get('info', {})
        metadata = match_data.get('metadata', {})
        
        # Parse participants
        participants = []
        for p_data in info.get('participants', []):
            participant = MatchParticipant(
                puuid=p_data.get('puuid', ''),
                summoner_name=p_data.get('riotIdGameName', '') + '#' + p_data.get('riotIdTagline', ''),
                champion_id=p_data.get('championId', 0),
                champion_name=p_data.get('championName', ''),
                team_id=p_data.get('teamId', 0),
                role=p_data.get('role', ''),
                lane=p_data.get('lane', ''),
                individual_position=p_data.get('individualPosition', ''),
                kills=p_data.get('kills', 0),
                deaths=p_data.get('deaths', 0),
                assists=p_data.get('assists', 0),
                total_damage_dealt_to_champions=p_data.get('totalDamageDealtToChampions', 0),
                total_minions_killed=p_data.get('totalMinionsKilled', 0),
                neutral_minions_killed=p_data.get('neutralMinionsKilled', 0),
                vision_score=p_data.get('visionScore', 0),
                gold_earned=p_data.get('goldEarned', 0),
                win=p_data.get('win', False)
            )
            participants.append(participant)
        
        # Determine winning team
        winning_team = 0
        for team in info.get('teams', []):
            if team.get('win', False):
                winning_team = team.get('teamId', 0)
                break
        
        match = Match(
            match_id=metadata.get('matchId', ''),
            game_creation=info.get('gameCreation', 0),
            game_duration=info.get('gameDuration', 0),
            game_end_timestamp=info.get('gameEndTimestamp', 0),
            game_mode=info.get('gameMode', 'CLASSIC'),
            game_type=info.get('gameType', 'MATCHED_GAME'),
            map_id=info.get('mapId', 11),
            queue_id=info.get('queueId', 0),
            game_version=info.get('gameVersion', ''),
            participants=participants,
            winning_team=winning_team
        )
        
        return match
    
    def get_match(self, match_id: str) -> Optional[Match]:
        """Get a specific match by ID."""
        return self._matches_cache.get(match_id)
    
    def get_matches_for_player(self, puuid: str, limit: Optional[int] = None) -> List[Match]:
        """
        Get all matches for a specific player.
        
        Args:
            puuid: Player's PUUID
            limit: Maximum number of matches to return (most recent first)
            
        Returns:
            List of Match objects sorted by game creation time (newest first)
        """
        match_ids = self._match_index.get(puuid, set())
        matches = []
        
        for match_id in match_ids:
            match = self._matches_cache.get(match_id)
            if match:
                matches.append(match)
        
        # Sort by game creation time (newest first)
        matches.sort(key=lambda m: m.game_creation, reverse=True)
        
        if limit:
            matches = matches[:limit]
        
        return matches
    
    def get_matches_with_multiple_players(self, puuids: Set[str], limit: Optional[int] = None) -> List[Match]:
        """
        Get matches that contain multiple players from our database.
        
        Args:
            puuids: Set of PUUIDs to look for
            limit: Maximum number of matches to return
            
        Returns:
            List of matches containing 2+ of the specified players
        """
        match_candidates = set()
        
        # Find all matches that contain any of the specified players
        for puuid in puuids:
            match_ids = self._match_index.get(puuid, set())
            match_candidates.update(match_ids)
        
        # Filter to matches with multiple specified players
        multi_player_matches = []
        for match_id in match_candidates:
            match = self._matches_cache.get(match_id)
            if match:
                known_players = match.get_known_players(puuids)
                if len(known_players) >= 2:
                    multi_player_matches.append(match)
        
        # Sort by game creation time (newest first)
        multi_player_matches.sort(key=lambda m: m.game_creation, reverse=True)
        
        if limit:
            multi_player_matches = multi_player_matches[:limit]
        
        return multi_player_matches
    
    def get_recent_matches(self, days: int = 30, limit: Optional[int] = None) -> List[Match]:
        """
        Get recent matches within the specified time period.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of matches to return
            
        Returns:
            List of recent matches sorted by game creation time (newest first)
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000)
        
        recent_matches = []
        for match in self._matches_cache.values():
            if match.game_creation >= cutoff_timestamp:
                recent_matches.append(match)
        
        # Sort by game creation time (newest first)
        recent_matches.sort(key=lambda m: m.game_creation, reverse=True)
        
        if limit:
            recent_matches = recent_matches[:limit]
        
        return recent_matches
    
    def get_match_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored matches."""
        total_matches = len(self._matches_cache)
        total_players_indexed = len(self._match_index)
        
        # Calculate date range
        if self._matches_cache:
            timestamps = [m.game_creation for m in self._matches_cache.values()]
            oldest_match = datetime.fromtimestamp(min(timestamps) / 1000)
            newest_match = datetime.fromtimestamp(max(timestamps) / 1000)
        else:
            oldest_match = None
            newest_match = None
        
        # Queue distribution
        queue_distribution = {}
        for match in self._matches_cache.values():
            queue_id = match.queue_id
            queue_distribution[queue_id] = queue_distribution.get(queue_id, 0) + 1
        
        return {
            'total_matches': total_matches,
            'total_players_indexed': total_players_indexed,
            'oldest_match': oldest_match.isoformat() if oldest_match else None,
            'newest_match': newest_match.isoformat() if newest_match else None,
            'queue_distribution': queue_distribution,
            'storage_file_size_mb': self.matches_file.stat().st_size / (1024 * 1024) if self.matches_file.exists() else 0
        }
    
    def cleanup_old_matches(self, days: int = 90) -> int:
        """
        Remove matches older than the specified number of days.
        
        Args:
            days: Number of days to keep matches
            
        Returns:
            Number of matches removed
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_timestamp = int(cutoff_time.timestamp() * 1000)
        
        matches_to_remove = []
        for match_id, match in self._matches_cache.items():
            if match.game_creation < cutoff_timestamp:
                matches_to_remove.append(match_id)
        
        # Remove matches and update index
        removed_count = 0
        for match_id in matches_to_remove:
            match = self._matches_cache.pop(match_id, None)
            if match:
                # Remove from index
                for participant in match.participants:
                    if participant.puuid in self._match_index:
                        self._match_index[participant.puuid].discard(match_id)
                        # Remove empty entries
                        if not self._match_index[participant.puuid]:
                            del self._match_index[participant.puuid]
                removed_count += 1
        
        if removed_count > 0:
            self._save_match_data()
            self.logger.info(f"Cleaned up {removed_count} old matches")
        
        return removed_count
    
    def rebuild_index(self) -> None:
        """Rebuild the match index from stored matches."""
        self._match_index = {}
        
        for match in self._matches_cache.values():
            for participant in match.participants:
                if participant.puuid not in self._match_index:
                    self._match_index[participant.puuid] = set()
                self._match_index[participant.puuid].add(match.match_id)
        
        self._save_match_data()
        self.logger.info(f"Rebuilt match index for {len(self._match_index)} players")
    
    def get_player_extraction_info(self, puuid: str) -> Dict[str, Any]:
        """
        Get extraction information for a specific player.
        
        Args:
            puuid: Player's PUUID
            
        Returns:
            Dictionary with extraction information
        """
        player_range = self._extraction_tracker.get_player_range(puuid)
        
        return {
            'puuid': puuid,
            'matches_extracted': player_range.matches_extracted,
            'start_index': player_range.start_index,
            'end_index': player_range.end_index,
            'total_matches_available': player_range.total_matches_available,
            'extraction_progress': player_range.extraction_progress,
            'extraction_complete': player_range.extraction_complete,
            'last_extraction': player_range.last_extraction.isoformat() if player_range.last_extraction else None,
            'next_extraction_start': player_range.end_index
        }
    
    def get_all_extraction_info(self) -> Dict[str, Any]:
        """
        Get extraction information for all players.
        
        Returns:
            Dictionary with comprehensive extraction information
        """
        summary = self._extraction_tracker.get_extraction_summary()
        
        player_details = {}
        for puuid in self._extraction_tracker.player_ranges:
            player_details[puuid] = self.get_player_extraction_info(puuid)
        
        return {
            'summary': summary,
            'players': player_details
        }
    
    def update_player_extraction_progress(self, puuid: str, matches_fetched: int, 
                                        total_available: Optional[int] = None) -> None:
        """
        Update extraction progress for a player.
        
        Args:
            puuid: Player's PUUID
            matches_fetched: Number of matches successfully fetched
            total_available: Total matches available from API (if known)
        """
        self._extraction_tracker.update_player_extraction(puuid, matches_fetched, total_available)
        # Save immediately to persist progress
        self._save_match_data()
    
    def get_next_extraction_batch(self, puuid: str, batch_size: int = 20) -> Tuple[int, int]:
        """
        Get the next batch of matches to extract for a player.
        
        Args:
            puuid: Player's PUUID
            batch_size: Size of the batch to extract
            
        Returns:
            Tuple of (start_index, count) for next extraction
        """
        player_range = self._extraction_tracker.get_player_range(puuid)
        return player_range.get_next_extraction_range(batch_size)
    
    def reset_player_extraction(self, puuid: str) -> None:
        """
        Reset extraction progress for a player (useful for re-scraping).
        
        Args:
            puuid: Player's PUUID
        """
        if puuid in self._extraction_tracker.player_ranges:
            del self._extraction_tracker.player_ranges[puuid]
        self._save_match_data()
        self.logger.info(f"Reset extraction progress for player {puuid}")
    
    def mark_extraction_complete(self, puuid: str) -> None:
        """
        Mark extraction as complete for a player.
        
        Args:
            puuid: Player's PUUID
        """
        player_range = self._extraction_tracker.get_player_range(puuid)
        player_range.extraction_complete = True
        self._save_match_data()
        self.logger.info(f"Marked extraction complete for player {puuid}")
    
    def get_matches_with_champions(
        self, 
        champion_ids: List[int], 
        same_team: bool = False,
        filters: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get matches containing specific champions.
        
        Args:
            champion_ids: List of champion IDs to search for
            same_team: If True, all champions must be on the same team
            filters: Optional filters to apply
            
        Returns:
            List of match data dictionaries
        """
        try:
            matching_matches = []
            
            for match in self._matches_cache.values():
                # Apply date filter if provided
                if filters and hasattr(filters, 'date_range') and filters.date_range:
                    match_date = datetime.fromtimestamp(match.game_creation / 1000)
                    if not filters.date_range.contains(match_date):
                        continue
                
                # Check if match contains the required champions
                if same_team:
                    # Check if all champions are on the same team
                    team_champions = {100: [], 200: []}
                    for participant in match.participants:
                        team_champions[participant.team_id].append(participant.champion_id)
                    
                    # Check if any team has all required champions
                    found_team = None
                    for team_id, team_champs in team_champions.items():
                        if all(champ_id in team_champs for champ_id in champion_ids):
                            found_team = team_id
                            break
                    
                    if found_team:
                        # Return match data with win status for the team
                        match_data = {
                            'match_id': match.match_id,
                            'win': match.winning_team == found_team,
                            'game_creation': match.game_creation,
                            'game_duration': match.game_duration,
                            'champions': champion_ids
                        }
                        matching_matches.append(match_data)
                else:
                    # Check if match contains any of the required champions
                    match_champions = [p.champion_id for p in match.participants]
                    if any(champ_id in match_champions for champ_id in champion_ids):
                        # Find the participant with the champion
                        for participant in match.participants:
                            if participant.champion_id in champion_ids:
                                match_data = {
                                    'match_id': match.match_id,
                                    'champion_id': participant.champion_id,
                                    'win': participant.win,
                                    'game_creation': match.game_creation,
                                    'game_duration': match.game_duration,
                                    'role': participant.individual_position.lower()
                                }
                                matching_matches.append(match_data)
                                break
            
            return matching_matches
            
        except Exception as e:
            self.logger.error(f"Failed to get matches with champions: {e}")
            return []
    
    def get_matches_by_role(self, role: str, filters: Optional[Any] = None) -> List[Dict[str, Any]]:
        """
        Get matches for a specific role.
        
        Args:
            role: Role to filter by
            filters: Optional filters to apply
            
        Returns:
            List of match data dictionaries
        """
        try:
            role_matches = []
            
            for match in self._matches_cache.values():
                # Apply date filter if provided
                if filters and hasattr(filters, 'date_range') and filters.date_range:
                    match_date = datetime.fromtimestamp(match.game_creation / 1000)
                    if not filters.date_range.contains(match_date):
                        continue
                
                # Find participants in the specified role
                for participant in match.participants:
                    participant_role = participant.individual_position.lower()
                    if participant_role == role.lower():
                        match_data = {
                            'match_id': match.match_id,
                            'champion_id': participant.champion_id,
                            'puuid': participant.puuid,
                            'win': participant.win,
                            'game_creation': match.game_creation,
                            'role': participant_role
                        }
                        role_matches.append(match_data)
            
            return role_matches
            
        except Exception as e:
            self.logger.error(f"Failed to get matches by role: {e}")
            return []
    
    def get_champion_matchups(
        self,
        champion_id: int,
        enemy_champion_id: int,
        role: str,
        enemy_role: str
    ) -> List[Dict[str, Any]]:
        """
        Get historical matchups between two champions.
        
        Args:
            champion_id: Our champion ID
            enemy_champion_id: Enemy champion ID
            role: Our champion's role
            enemy_role: Enemy champion's role
            
        Returns:
            List of matchup data dictionaries
        """
        try:
            matchup_data = []
            
            for match in self._matches_cache.values():
                our_participant = None
                enemy_participant = None
                
                # Find both participants in the match
                for participant in match.participants:
                    if (participant.champion_id == champion_id and 
                        participant.individual_position.lower() == role.lower()):
                        our_participant = participant
                    elif (participant.champion_id == enemy_champion_id and 
                          participant.individual_position.lower() == enemy_role.lower()):
                        enemy_participant = participant
                
                # If both participants found and on opposite teams
                if (our_participant and enemy_participant and 
                    our_participant.team_id != enemy_participant.team_id):
                    
                    matchup_data.append({
                        'match_id': match.match_id,
                        'our_champion': champion_id,
                        'enemy_champion': enemy_champion_id,
                        'win': our_participant.win,
                        'our_kda': (our_participant.kills + our_participant.assists) / max(our_participant.deaths, 1),
                        'enemy_kda': (enemy_participant.kills + enemy_participant.assists) / max(enemy_participant.deaths, 1),
                        'game_creation': match.game_creation,
                        'game_duration': match.game_duration
                    })
            
            return matchup_data
            
        except Exception as e:
            self.logger.error(f"Failed to get champion matchups: {e}")
            return []