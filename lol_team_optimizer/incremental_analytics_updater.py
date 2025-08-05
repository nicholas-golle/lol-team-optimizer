"""
Incremental Analytics Updater for the League of Legends Team Optimizer.

This module provides incremental update capabilities for analytics data,
allowing efficient processing of new match data without recalculating
entire datasets.
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import threading

from .analytics_models import AnalyticsError, AnalyticsFilters, DateRange
from .config import Config
from .models import Match


logger = logging.getLogger(__name__)


class IncrementalUpdateError(AnalyticsError):
    """Base exception for incremental update operations."""
    pass


@dataclass
class UpdateCheckpoint:
    """Represents a checkpoint for incremental updates."""
    
    checkpoint_id: str
    player_puuid: str
    last_processed_match_id: Optional[str] = None
    last_processed_timestamp: Optional[datetime] = None
    processed_match_count: int = 0
    analytics_version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, match_id: str, match_timestamp: datetime):
        """Update checkpoint with new match information."""
        self.last_processed_match_id = match_id
        self.last_processed_timestamp = match_timestamp
        self.processed_match_count += 1
        self.updated_at = datetime.now()


@dataclass
class IncrementalUpdateResult:
    """Result of an incremental update operation."""
    
    player_puuid: str
    new_matches_processed: int
    updated_analytics: List[str] = field(default_factory=list)  # Types of analytics updated
    processing_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    checkpoint_updated: bool = False
    
    @property
    def success(self) -> bool:
        """Check if update was successful."""
        return len(self.errors) == 0


class CheckpointManager:
    """Manages update checkpoints for incremental analytics."""
    
    def __init__(self, config: Config):
        """Initialize checkpoint manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Storage paths
        self.data_dir = Path(config.data_directory)
        self.checkpoints_file = self.data_dir / "analytics_checkpoints.json"
        
        # In-memory cache
        self._checkpoints: Dict[str, UpdateCheckpoint] = {}
        self._lock = threading.RLock()
        
        # Load existing checkpoints
        self._load_checkpoints()
    
    def _load_checkpoints(self):
        """Load checkpoints from storage."""
        try:
            if self.checkpoints_file.exists():
                with open(self.checkpoints_file, 'r', encoding='utf-8') as f:
                    checkpoints_data = json.load(f)
                
                self._checkpoints = {}
                for checkpoint_data in checkpoints_data:
                    checkpoint = self._deserialize_checkpoint(checkpoint_data)
                    self._checkpoints[checkpoint.checkpoint_id] = checkpoint
                
                self.logger.info(f"Loaded {len(self._checkpoints)} analytics checkpoints")
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoints: {e}")
            self._checkpoints = {}
    
    def _save_checkpoints(self):
        """Save checkpoints to storage."""
        try:
            checkpoints_data = []
            for checkpoint in self._checkpoints.values():
                checkpoint_data = self._serialize_checkpoint(checkpoint)
                checkpoints_data.append(checkpoint_data)
            
            # Atomic write
            temp_file = self.checkpoints_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoints_data, f, indent=2, ensure_ascii=False, default=str)
            temp_file.replace(self.checkpoints_file)
            
            self.logger.debug(f"Saved {len(self._checkpoints)} analytics checkpoints")
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoints: {e}")
            raise
    
    def _serialize_checkpoint(self, checkpoint: UpdateCheckpoint) -> Dict[str, Any]:
        """Convert checkpoint to JSON-serializable dictionary."""
        checkpoint_dict = asdict(checkpoint)
        
        # Convert datetime objects to ISO strings
        if checkpoint_dict.get('last_processed_timestamp'):
            checkpoint_dict['last_processed_timestamp'] = checkpoint.last_processed_timestamp.isoformat()
        if checkpoint_dict.get('created_at'):
            checkpoint_dict['created_at'] = checkpoint.created_at.isoformat()
        if checkpoint_dict.get('updated_at'):
            checkpoint_dict['updated_at'] = checkpoint.updated_at.isoformat()
        
        return checkpoint_dict
    
    def _deserialize_checkpoint(self, checkpoint_data: Dict[str, Any]) -> UpdateCheckpoint:
        """Convert dictionary to UpdateCheckpoint object."""
        # Convert ISO strings back to datetime objects
        if checkpoint_data.get('last_processed_timestamp'):
            checkpoint_data['last_processed_timestamp'] = datetime.fromisoformat(
                checkpoint_data['last_processed_timestamp']
            )
        if checkpoint_data.get('created_at'):
            checkpoint_data['created_at'] = datetime.fromisoformat(checkpoint_data['created_at'])
        if checkpoint_data.get('updated_at'):
            checkpoint_data['updated_at'] = datetime.fromisoformat(checkpoint_data['updated_at'])
        
        return UpdateCheckpoint(**checkpoint_data)
    
    def get_checkpoint(self, player_puuid: str) -> Optional[UpdateCheckpoint]:
        """Get checkpoint for a player.
        
        Args:
            player_puuid: Player's PUUID
            
        Returns:
            UpdateCheckpoint if exists, None otherwise
        """
        with self._lock:
            checkpoint_id = f"player_{player_puuid}"
            return self._checkpoints.get(checkpoint_id)
    
    def create_or_update_checkpoint(self, player_puuid: str, match_id: str, 
                                  match_timestamp: datetime) -> UpdateCheckpoint:
        """Create or update checkpoint for a player.
        
        Args:
            player_puuid: Player's PUUID
            match_id: Latest processed match ID
            match_timestamp: Timestamp of the match
            
        Returns:
            Updated checkpoint
        """
        with self._lock:
            checkpoint_id = f"player_{player_puuid}"
            
            if checkpoint_id in self._checkpoints:
                # Update existing checkpoint
                checkpoint = self._checkpoints[checkpoint_id]
                checkpoint.update(match_id, match_timestamp)
            else:
                # Create new checkpoint
                checkpoint = UpdateCheckpoint(
                    checkpoint_id=checkpoint_id,
                    player_puuid=player_puuid,
                    last_processed_match_id=match_id,
                    last_processed_timestamp=match_timestamp,
                    processed_match_count=1
                )
                self._checkpoints[checkpoint_id] = checkpoint
            
            # Save to disk
            self._save_checkpoints()
            
            return checkpoint
    
    def get_all_checkpoints(self) -> List[UpdateCheckpoint]:
        """Get all checkpoints.
        
        Returns:
            List of all checkpoints
        """
        with self._lock:
            return list(self._checkpoints.values())
    
    def delete_checkpoint(self, player_puuid: str) -> bool:
        """Delete checkpoint for a player.
        
        Args:
            player_puuid: Player's PUUID
            
        Returns:
            True if checkpoint was deleted, False if not found
        """
        with self._lock:
            checkpoint_id = f"player_{player_puuid}"
            if checkpoint_id in self._checkpoints:
                del self._checkpoints[checkpoint_id]
                self._save_checkpoints()
                return True
            return False
    
    def cleanup_old_checkpoints(self, days: int = 90) -> int:
        """Clean up old checkpoints.
        
        Args:
            days: Number of days to keep checkpoints
            
        Returns:
            Number of checkpoints removed
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with self._lock:
            checkpoints_to_remove = []
            for checkpoint_id, checkpoint in self._checkpoints.items():
                if checkpoint.updated_at < cutoff_time:
                    checkpoints_to_remove.append(checkpoint_id)
            
            removed_count = 0
            for checkpoint_id in checkpoints_to_remove:
                del self._checkpoints[checkpoint_id]
                removed_count += 1
            
            if removed_count > 0:
                self._save_checkpoints()
                self.logger.info(f"Cleaned up {removed_count} old checkpoints")
            
            return removed_count


class IncrementalAnalyticsUpdater:
    """Handles incremental updates of analytics data."""
    
    def __init__(self, config: Config, analytics_engine, match_manager, cache_manager):
        """Initialize incremental analytics updater.
        
        Args:
            config: Application configuration
            analytics_engine: HistoricalAnalyticsEngine instance
            match_manager: MatchManager instance
            cache_manager: AnalyticsCacheManager instance
        """
        self.config = config
        self.analytics_engine = analytics_engine
        self.match_manager = match_manager
        self.cache_manager = cache_manager
        self.checkpoint_manager = CheckpointManager(config)
        self.logger = logging.getLogger(__name__)
        
        # Update configuration
        self.batch_size = 50  # Process matches in batches
        self.max_lookback_days = 365  # Maximum days to look back for new matches
    
    def update_player_analytics(self, player_puuid: str, 
                              force_full_update: bool = False) -> IncrementalUpdateResult:
        """Update analytics for a specific player incrementally.
        
        Args:
            player_puuid: Player's PUUID
            force_full_update: If True, recalculate all analytics
            
        Returns:
            IncrementalUpdateResult with update information
        """
        start_time = datetime.now()
        result = IncrementalUpdateResult(player_puuid=player_puuid)
        
        try:
            # Get checkpoint
            checkpoint = self.checkpoint_manager.get_checkpoint(player_puuid)
            
            if force_full_update or not checkpoint:
                # Full update - process all matches
                new_matches = self.match_manager.get_matches_for_player(player_puuid)
                self.logger.info(f"Performing full analytics update for {player_puuid} with {len(new_matches)} matches")
            else:
                # Incremental update - process only new matches
                new_matches = self._get_new_matches_since_checkpoint(player_puuid, checkpoint)
                self.logger.info(f"Performing incremental analytics update for {player_puuid} with {len(new_matches)} new matches")
            
            if not new_matches:
                self.logger.debug(f"No new matches found for {player_puuid}")
                return result
            
            # Process new matches in batches
            processed_count = 0
            for i in range(0, len(new_matches), self.batch_size):
                batch = new_matches[i:i + self.batch_size]
                
                try:
                    # Update analytics for this batch
                    self._process_match_batch(player_puuid, batch, result)
                    processed_count += len(batch)
                    
                except Exception as e:
                    error_msg = f"Failed to process batch {i//self.batch_size + 1}: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            result.new_matches_processed = processed_count
            
            # Update checkpoint if we processed any matches
            if processed_count > 0:
                latest_match = new_matches[0]  # Matches are sorted newest first
                match_timestamp = datetime.fromtimestamp(latest_match.game_creation / 1000)
                
                self.checkpoint_manager.create_or_update_checkpoint(
                    player_puuid, latest_match.match_id, match_timestamp
                )
                result.checkpoint_updated = True
            
            # Invalidate relevant cache entries
            self._invalidate_player_cache(player_puuid)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time_seconds = processing_time
            
            self.logger.info(f"Updated analytics for {player_puuid}: {processed_count} matches processed in {processing_time:.2f}s")
            
        except Exception as e:
            error_msg = f"Failed to update analytics for {player_puuid}: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def update_multiple_players(self, player_puuids: List[str], 
                              force_full_update: bool = False) -> Dict[str, IncrementalUpdateResult]:
        """Update analytics for multiple players.
        
        Args:
            player_puuids: List of player PUUIDs
            force_full_update: If True, recalculate all analytics
            
        Returns:
            Dictionary mapping PUUIDs to update results
        """
        results = {}
        
        for puuid in player_puuids:
            try:
                result = self.update_player_analytics(puuid, force_full_update)
                results[puuid] = result
            except Exception as e:
                error_result = IncrementalUpdateResult(player_puuid=puuid)
                error_result.errors.append(f"Update failed: {str(e)}")
                results[puuid] = error_result
                self.logger.error(f"Failed to update analytics for {puuid}: {e}")
        
        return results
    
    def get_players_needing_updates(self, max_age_hours: int = 24) -> List[str]:
        """Get list of players whose analytics need updating.
        
        Args:
            max_age_hours: Maximum age of analytics before update is needed
            
        Returns:
            List of player PUUIDs needing updates
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        players_needing_update = []
        
        # Get all players with matches
        all_players = set()
        recent_matches = self.match_manager.get_recent_matches(days=self.max_lookback_days)
        
        for match in recent_matches:
            for participant in match.participants:
                all_players.add(participant.puuid)
        
        # Check which players need updates
        for puuid in all_players:
            checkpoint = self.checkpoint_manager.get_checkpoint(puuid)
            
            if not checkpoint:
                # No checkpoint - needs full update
                players_needing_update.append(puuid)
            elif checkpoint.updated_at < cutoff_time:
                # Checkpoint is old - check for new matches
                new_matches = self._get_new_matches_since_checkpoint(puuid, checkpoint)
                if new_matches:
                    players_needing_update.append(puuid)
        
        self.logger.info(f"Found {len(players_needing_update)} players needing analytics updates")
        return players_needing_update
    
    def _get_new_matches_since_checkpoint(self, player_puuid: str, 
                                        checkpoint: UpdateCheckpoint) -> List[Match]:
        """Get new matches for a player since the last checkpoint.
        
        Args:
            player_puuid: Player's PUUID
            checkpoint: Last checkpoint
            
        Returns:
            List of new matches
        """
        # Get all matches for the player
        all_matches = self.match_manager.get_matches_for_player(player_puuid)
        
        if not checkpoint.last_processed_timestamp:
            return all_matches
        
        # Filter to matches newer than checkpoint
        new_matches = []
        for match in all_matches:
            match_timestamp = datetime.fromtimestamp(match.game_creation / 1000)
            if match_timestamp > checkpoint.last_processed_timestamp:
                new_matches.append(match)
        
        return new_matches
    
    def _process_match_batch(self, player_puuid: str, matches: List[Match], 
                           result: IncrementalUpdateResult):
        """Process a batch of matches for analytics updates.
        
        Args:
            player_puuid: Player's PUUID
            matches: List of matches to process
            result: Result object to update
        """
        try:
            # Update baseline calculations
            if hasattr(self.analytics_engine, 'baseline_manager'):
                baseline_manager = self.analytics_engine.baseline_manager
                
                # Update baselines with new matches
                for match in matches:
                    participant = match.get_participant_by_puuid(player_puuid)
                    if participant:
                        try:
                            baseline_manager.update_player_baseline_with_match(player_puuid, match, participant)
                        except Exception as e:
                            self.logger.warning(f"Failed to update baseline for match {match.match_id}: {e}")
                
                result.updated_analytics.append("baselines")
            
            # Update champion-specific analytics
            champion_roles = set()
            for match in matches:
                participant = match.get_participant_by_puuid(player_puuid)
                if participant:
                    champion_roles.add((participant.champion_id, participant.individual_position))
            
            for champion_id, role in champion_roles:
                try:
                    # Trigger recalculation of champion analytics
                    # This will use the updated baseline data
                    self.analytics_engine.analyze_champion_performance(
                        player_puuid, champion_id, role
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to update champion analytics for {champion_id}-{role}: {e}")
            
            if champion_roles:
                result.updated_analytics.append("champion_performance")
            
            # Update trend analysis
            try:
                # Recalculate trends with new data
                self.analytics_engine.calculate_performance_trends(player_puuid)
                result.updated_analytics.append("trends")
            except Exception as e:
                self.logger.warning(f"Failed to update trend analysis: {e}")
            
        except Exception as e:
            raise IncrementalUpdateError(f"Failed to process match batch: {e}")
    
    def _invalidate_player_cache(self, player_puuid: str):
        """Invalidate cache entries for a player.
        
        Args:
            player_puuid: Player's PUUID
        """
        try:
            # Invalidate player-specific cache entries
            patterns = [
                f"*{player_puuid}*",
                f"player_analytics_{player_puuid}*",
                f"champion_analytics_{player_puuid}*",
                f"trends_{player_puuid}*",
                f"baseline_{player_puuid}*"
            ]
            
            for pattern in patterns:
                invalidated_count = self.cache_manager.invalidate_cache(pattern)
                if invalidated_count > 0:
                    self.logger.debug(f"Invalidated {invalidated_count} cache entries matching {pattern}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to invalidate cache for {player_puuid}: {e}")
    
    def get_update_statistics(self) -> Dict[str, Any]:
        """Get statistics about incremental updates.
        
        Returns:
            Dictionary containing update statistics
        """
        checkpoints = self.checkpoint_manager.get_all_checkpoints()
        
        if not checkpoints:
            return {
                'total_players_tracked': 0,
                'average_matches_processed': 0,
                'oldest_checkpoint': None,
                'newest_checkpoint': None,
                'players_needing_update': 0
            }
        
        # Calculate statistics
        total_matches = sum(cp.processed_match_count for cp in checkpoints)
        avg_matches = total_matches / len(checkpoints) if checkpoints else 0
        
        oldest_checkpoint = min(checkpoints, key=lambda cp: cp.created_at)
        newest_checkpoint = max(checkpoints, key=lambda cp: cp.updated_at)
        
        # Count players needing updates (last 24 hours)
        players_needing_update = len(self.get_players_needing_updates(max_age_hours=24))
        
        return {
            'total_players_tracked': len(checkpoints),
            'total_matches_processed': total_matches,
            'average_matches_processed': avg_matches,
            'oldest_checkpoint': oldest_checkpoint.created_at.isoformat(),
            'newest_checkpoint': newest_checkpoint.updated_at.isoformat(),
            'players_needing_update': players_needing_update
        }
    
    def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """Clean up old incremental update data.
        
        Args:
            days: Number of days to keep data
            
        Returns:
            Dictionary with cleanup statistics
        """
        checkpoints_removed = self.checkpoint_manager.cleanup_old_checkpoints(days)
        
        return {
            'checkpoints_removed': checkpoints_removed
        }