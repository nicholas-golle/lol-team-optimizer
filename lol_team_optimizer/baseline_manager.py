"""
Baseline Manager for performance baselines in the League of Legends Team Optimizer.

This module manages performance baselines for players across different contexts
(champions, roles, time periods) to enable comparative analysis and performance
evaluation relative to established benchmarks.
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import math

from .models import Match, MatchParticipant
from .analytics_models import (
    PerformanceMetrics, PerformanceDelta, ConfidenceInterval,
    BaselineCalculationError, InsufficientDataError, DateRange
)
from .config import Config


@dataclass
class BaselineContext:
    """Context for baseline calculations."""
    
    puuid: str
    champion_id: Optional[int] = None
    role: Optional[str] = None
    time_window_days: Optional[int] = None
    team_composition_context: Optional[List[str]] = None  # teammate puuids
    queue_types: Optional[List[int]] = None
    
    def __post_init__(self):
        """Validate baseline context."""
        if not self.puuid:
            raise ValueError("PUUID cannot be empty")
        
        if self.role:
            valid_roles = {"top", "jungle", "middle", "support", "bottom"}
            if self.role not in valid_roles:
                raise ValueError(f"Invalid role: {self.role}")
        
        if self.time_window_days is not None and self.time_window_days <= 0:
            raise ValueError("Time window must be positive")
        
        if self.champion_id is not None and self.champion_id <= 0:
            raise ValueError("Champion ID must be positive")
    
    @property
    def cache_key(self) -> str:
        """Generate cache key for this context."""
        key_parts = [self.puuid]
        
        if self.champion_id:
            key_parts.append(f"champ_{self.champion_id}")
        
        if self.role:
            key_parts.append(f"role_{self.role}")
        
        if self.time_window_days:
            key_parts.append(f"time_{self.time_window_days}")
        
        if self.team_composition_context:
            teammates = "_".join(sorted(self.team_composition_context))
            key_parts.append(f"team_{teammates}")
        
        if self.queue_types:
            queues = "_".join(map(str, sorted(self.queue_types)))
            key_parts.append(f"queue_{queues}")
        
        return "|".join(key_parts)


@dataclass
class PlayerBaseline:
    """Performance baseline for a player in a specific context."""
    
    puuid: str
    context: BaselineContext
    baseline_metrics: PerformanceMetrics
    sample_size: int
    confidence_interval: ConfidenceInterval
    calculation_date: datetime
    temporal_weight_applied: bool = False
    
    def __post_init__(self):
        """Validate player baseline."""
        if not self.puuid:
            raise ValueError("PUUID cannot be empty")
        
        if self.sample_size <= 0:
            raise ValueError("Sample size must be positive")
        
        if self.context.puuid != self.puuid:
            raise ValueError("Context PUUID must match baseline PUUID")
    
    def is_stale(self, max_age_days: int = 7) -> bool:
        """Check if baseline is stale and needs recalculation."""
        age = datetime.now() - self.calculation_date
        return age.days > max_age_days
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability score based on sample size and recency."""
        # Base reliability from sample size
        size_score = min(self.sample_size / 20.0, 1.0)  # Cap at 20 games
        
        # Recency penalty
        age_days = (datetime.now() - self.calculation_date).days
        recency_score = max(0.1, 1.0 - (age_days / 30.0))  # Decay over 30 days
        
        return size_score * recency_score


@dataclass
class ContextualBaseline:
    """Baseline for a specific champion-role-context combination."""
    
    puuid: str
    champion_id: int
    role: str
    baseline_metrics: PerformanceMetrics
    sample_size: int
    confidence_interval: ConfidenceInterval
    synergy_adjustments: Dict[str, float] = field(default_factory=dict)  # teammate_puuid -> adjustment
    meta_adjustment: float = 0.0
    calculation_date: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate contextual baseline."""
        if not self.puuid:
            raise ValueError("PUUID cannot be empty")
        
        if self.champion_id <= 0:
            raise ValueError("Champion ID must be positive")
        
        if not self.role:
            raise ValueError("Role cannot be empty")
        
        if self.sample_size <= 0:
            raise ValueError("Sample size must be positive")


class BaselineCache:
    """Cache for baseline calculations."""
    
    def __init__(self, cache_directory: Path):
        """Initialize baseline cache."""
        self.cache_directory = cache_directory
        self.cache_directory.mkdir(exist_ok=True)
        
        self.memory_cache: Dict[str, PlayerBaseline] = {}
        self.cache_file = cache_directory / "baselines_cache.json"
        
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            for key, baseline_data in cache_data.items():
                baseline = self._deserialize_baseline(baseline_data)
                self.memory_cache[key] = baseline
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load baseline cache: {e}")
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            cache_data = {}
            for key, baseline in self.memory_cache.items():
                cache_data[key] = self._serialize_baseline(baseline)
            
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
            temp_file.replace(self.cache_file)
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save baseline cache: {e}")
    
    def _serialize_baseline(self, baseline: PlayerBaseline) -> Dict[str, Any]:
        """Serialize baseline to JSON-compatible format."""
        baseline_dict = asdict(baseline)
        baseline_dict['calculation_date'] = baseline.calculation_date.isoformat()
        return baseline_dict
    
    def _deserialize_baseline(self, baseline_data: Dict[str, Any]) -> PlayerBaseline:
        """Deserialize baseline from JSON format."""
        # Make a copy to avoid modifying the original
        data = baseline_data.copy()
        
        # Convert datetime
        data['calculation_date'] = datetime.fromisoformat(data['calculation_date'])
        
        # Reconstruct nested objects
        context_data = data['context']
        data['context'] = BaselineContext(**context_data)
        
        metrics_data = data['baseline_metrics']
        data['baseline_metrics'] = PerformanceMetrics(**metrics_data)
        
        ci_data = data['confidence_interval']
        data['confidence_interval'] = ConfidenceInterval(**ci_data)
        
        return PlayerBaseline(**data)
    
    def get(self, cache_key: str) -> Optional[PlayerBaseline]:
        """Get baseline from cache."""
        baseline = self.memory_cache.get(cache_key)
        
        # Check if baseline is stale
        if baseline and baseline.is_stale():
            del self.memory_cache[cache_key]
            return None
        
        return baseline
    
    def put(self, cache_key: str, baseline: PlayerBaseline) -> None:
        """Put baseline in cache."""
        self.memory_cache[cache_key] = baseline
        self._save_cache()
    
    def invalidate(self, puuid: str) -> None:
        """Invalidate all baselines for a player."""
        keys_to_remove = [key for key in self.memory_cache.keys() if key.startswith(puuid)]
        for key in keys_to_remove:
            del self.memory_cache[key]
        self._save_cache()
    
    def cleanup_stale(self) -> int:
        """Remove stale baselines from cache."""
        stale_keys = [key for key, baseline in self.memory_cache.items() if baseline.is_stale()]
        for key in stale_keys:
            del self.memory_cache[key]
        
        if stale_keys:
            self._save_cache()
        
        return len(stale_keys)


class BaselineManager:
    """
    Manages performance baselines for players across different contexts.
    
    Provides baseline calculations for overall, role-specific, and champion-specific
    performance with temporal weighting and contextual adjustments.
    """
    
    def __init__(self, config: Config, match_manager):
        """Initialize the baseline manager."""
        self.config = config
        self.match_manager = match_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache
        cache_dir = Path(config.cache_directory) / "baselines"
        self.cache = BaselineCache(cache_dir)
        
        # Configuration
        self.min_games_for_baseline = 5
        self.temporal_decay_days = 60  # Days for temporal weighting
        self.confidence_level = 0.95
        self.recent_emphasis_days = 30  # Days to emphasize for recent performance
    
    def calculate_player_baseline(self, context: BaselineContext) -> PlayerBaseline:
        """
        Calculate performance baseline for a player in a specific context.
        
        Args:
            context: Baseline calculation context
            
        Returns:
            PlayerBaseline object with calculated metrics
            
        Raises:
            InsufficientDataError: If not enough data for reliable baseline
            BaselineCalculationError: If calculation fails
        """
        # Check cache first
        cache_key = context.cache_key
        cached_baseline = self.cache.get(cache_key)
        if cached_baseline:
            self.logger.debug(f"Using cached baseline for {cache_key}")
            return cached_baseline
        
        try:
            # Get matches for the context
            matches = self._get_matches_for_context(context)
            
            if len(matches) < self.min_games_for_baseline:
                raise InsufficientDataError(
                    required_games=self.min_games_for_baseline,
                    available_games=len(matches),
                    context=f"baseline calculation for {context.puuid}"
                )
            
            # Calculate baseline metrics
            baseline_metrics = self._calculate_baseline_metrics(matches, context)
            
            # Apply temporal weighting if requested
            if context.time_window_days:
                baseline_metrics = self._apply_temporal_weighting(
                    matches, baseline_metrics, context.time_window_days
                )
                temporal_weight_applied = True
            else:
                temporal_weight_applied = False
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(matches, baseline_metrics)
            
            # Create baseline
            baseline = PlayerBaseline(
                puuid=context.puuid,
                context=context,
                baseline_metrics=baseline_metrics,
                sample_size=len(matches),
                confidence_interval=confidence_interval,
                calculation_date=datetime.now(),
                temporal_weight_applied=temporal_weight_applied
            )
            
            # Cache the result
            self.cache.put(cache_key, baseline)
            
            self.logger.info(f"Calculated baseline for {context.puuid} with {len(matches)} games")
            return baseline
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, BaselineCalculationError)):
                raise
            raise BaselineCalculationError(f"Failed to calculate baseline: {e}")
    
    def get_overall_baseline(self, puuid: str, time_window_days: Optional[int] = None) -> PlayerBaseline:
        """
        Get overall performance baseline for a player across all champions and roles.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Optional time window for temporal weighting
            
        Returns:
            PlayerBaseline for overall performance
        """
        context = BaselineContext(
            puuid=puuid,
            time_window_days=time_window_days
        )
        return self.calculate_player_baseline(context)
    
    def get_role_specific_baseline(self, puuid: str, role: str, 
                                 time_window_days: Optional[int] = None) -> PlayerBaseline:
        """
        Get role-specific performance baseline for a player.
        
        Args:
            puuid: Player's PUUID
            role: Specific role (top, jungle, middle, support, bottom)
            time_window_days: Optional time window for temporal weighting
            
        Returns:
            PlayerBaseline for role-specific performance
        """
        context = BaselineContext(
            puuid=puuid,
            role=role,
            time_window_days=time_window_days
        )
        return self.calculate_player_baseline(context)
    
    def get_champion_specific_baseline(self, puuid: str, champion_id: int, role: str,
                                     time_window_days: Optional[int] = None) -> PlayerBaseline:
        """
        Get champion-specific performance baseline for a player.
        
        Args:
            puuid: Player's PUUID
            champion_id: Specific champion ID
            role: Role played with the champion
            time_window_days: Optional time window for temporal weighting
            
        Returns:
            PlayerBaseline for champion-specific performance
        """
        context = BaselineContext(
            puuid=puuid,
            champion_id=champion_id,
            role=role,
            time_window_days=time_window_days
        )
        return self.calculate_player_baseline(context)
    
    def get_contextual_baseline(self, puuid: str, champion_id: int, role: str,
                              teammate_puuids: Optional[List[str]] = None,
                              queue_types: Optional[List[int]] = None) -> ContextualBaseline:
        """
        Get contextual baseline for specific team composition contexts.
        
        Args:
            puuid: Player's PUUID
            champion_id: Champion ID
            role: Role
            teammate_puuids: Optional list of teammate PUUIDs for context
            queue_types: Optional list of queue types to consider
            
        Returns:
            ContextualBaseline with team composition adjustments
        """
        try:
            # Get base champion-role baseline
            base_context = BaselineContext(
                puuid=puuid,
                champion_id=champion_id,
                role=role,
                queue_types=queue_types
            )
            base_baseline = self.calculate_player_baseline(base_context)
            
            # Calculate synergy adjustments if teammates provided
            synergy_adjustments = {}
            if teammate_puuids:
                synergy_adjustments = self._calculate_synergy_adjustments(
                    puuid, champion_id, role, teammate_puuids
                )
            
            # Calculate meta adjustment
            meta_adjustment = self._calculate_meta_adjustment(champion_id, role)
            
            return ContextualBaseline(
                puuid=puuid,
                champion_id=champion_id,
                role=role,
                baseline_metrics=base_baseline.baseline_metrics,
                sample_size=base_baseline.sample_size,
                confidence_interval=base_baseline.confidence_interval,
                synergy_adjustments=synergy_adjustments,
                meta_adjustment=meta_adjustment,
                calculation_date=datetime.now()
            )
            
        except Exception as e:
            raise BaselineCalculationError(f"Failed to calculate contextual baseline: {e}")
    
    def calculate_performance_delta(self, performance: PerformanceMetrics, 
                                  baseline: PlayerBaseline) -> Dict[str, PerformanceDelta]:
        """
        Calculate performance deltas compared to baseline.
        
        Args:
            performance: Actual performance metrics
            baseline: Baseline to compare against
            
        Returns:
            Dictionary of metric name to PerformanceDelta
        """
        deltas = {}
        baseline_metrics = baseline.baseline_metrics
        
        # Define metrics to compare
        metrics_to_compare = [
            ('win_rate', performance.win_rate, baseline_metrics.win_rate),
            ('avg_kda', performance.avg_kda, baseline_metrics.avg_kda),
            ('avg_cs_per_min', performance.avg_cs_per_min, baseline_metrics.avg_cs_per_min),
            ('avg_vision_score', performance.avg_vision_score, baseline_metrics.avg_vision_score),
            ('avg_damage_per_min', performance.avg_damage_per_min, baseline_metrics.avg_damage_per_min),
            ('avg_gold_per_min', performance.avg_gold_per_min, baseline_metrics.avg_gold_per_min),
            ('avg_game_duration', performance.avg_game_duration, baseline_metrics.avg_game_duration)
        ]
        
        for metric_name, actual_value, baseline_value in metrics_to_compare:
            delta = PerformanceDelta(
                metric_name=metric_name,
                baseline_value=baseline_value,
                actual_value=actual_value
            )
            
            # Calculate percentile rank (simplified)
            delta.percentile_rank = self._calculate_percentile_rank(
                actual_value, baseline_value, baseline.confidence_interval
            )
            
            deltas[metric_name] = delta
        
        return deltas
    
    def update_baselines(self, puuid: str, new_matches: List[Match]) -> None:
        """
        Update baselines when new matches are available.
        
        Args:
            puuid: Player's PUUID
            new_matches: List of new matches to incorporate
        """
        if not new_matches:
            return
        
        # Invalidate cached baselines for this player
        self.cache.invalidate(puuid)
        
        self.logger.info(f"Invalidated baselines for {puuid} due to {len(new_matches)} new matches")
    
    def _get_matches_for_context(self, context: BaselineContext) -> List[Tuple[Match, MatchParticipant]]:
        """Get matches that match the baseline context."""
        all_matches = self.match_manager.get_matches_for_player(context.puuid)
        filtered_matches = []
        
        for match in all_matches:
            participant = match.get_participant_by_puuid(context.puuid)
            if not participant:
                continue
            
            # Apply filters based on context
            if context.champion_id and participant.champion_id != context.champion_id:
                continue
            
            if context.role and not self._normalize_role(participant.individual_position) == context.role:
                continue
            
            if context.queue_types and match.queue_id not in context.queue_types:
                continue
            
            if context.time_window_days:
                match_date = match.game_creation_datetime
                cutoff_date = datetime.now() - timedelta(days=context.time_window_days)
                if match_date < cutoff_date:
                    continue
            
            if context.team_composition_context:
                # Check if any of the specified teammates were in this match
                match_puuids = {p.puuid for p in match.participants}
                if not any(teammate in match_puuids for teammate in context.team_composition_context):
                    continue
            
            filtered_matches.append((match, participant))
        
        return filtered_matches
    
    def _calculate_baseline_metrics(self, matches: List[Tuple[Match, MatchParticipant]], 
                                  context: BaselineContext) -> PerformanceMetrics:
        """Calculate baseline performance metrics from matches."""
        if not matches:
            raise BaselineCalculationError("No matches provided for baseline calculation")
        
        # Aggregate statistics
        total_games = len(matches)
        total_wins = sum(1 for _, participant in matches if participant.win)
        total_kills = sum(participant.kills for _, participant in matches)
        total_deaths = sum(participant.deaths for _, participant in matches)
        total_assists = sum(participant.assists for _, participant in matches)
        total_cs = sum(participant.cs_total for _, participant in matches)
        total_vision = sum(participant.vision_score for _, participant in matches)
        total_damage = sum(participant.total_damage_dealt_to_champions for _, participant in matches)
        total_gold = sum(participant.gold_earned for _, participant in matches)
        total_duration = sum(match.game_duration for match, _ in matches)
        
        # Calculate averages
        win_rate = total_wins / total_games
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
        avg_cs_per_min = total_cs / (total_duration / 60) if total_duration > 0 else 0
        avg_vision_score = total_vision / total_games
        avg_damage_per_min = total_damage / (total_duration / 60) if total_duration > 0 else 0
        avg_gold_per_min = total_gold / (total_duration / 60) if total_duration > 0 else 0
        avg_game_duration = total_duration / (total_games * 60)  # in minutes
        
        return PerformanceMetrics(
            games_played=total_games,
            wins=total_wins,
            losses=total_games - total_wins,
            win_rate=win_rate,
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists,
            avg_kda=avg_kda,
            total_cs=total_cs,
            avg_cs_per_min=avg_cs_per_min,
            total_vision_score=total_vision,
            avg_vision_score=avg_vision_score,
            total_damage_to_champions=total_damage,
            avg_damage_per_min=avg_damage_per_min,
            total_gold_earned=total_gold,
            avg_gold_per_min=avg_gold_per_min,
            total_game_duration=total_duration,
            avg_game_duration=avg_game_duration
        )
    
    def _apply_temporal_weighting(self, matches: List[Tuple[Match, MatchParticipant]], 
                                baseline_metrics: PerformanceMetrics, 
                                time_window_days: int) -> PerformanceMetrics:
        """Apply temporal weighting to emphasize recent performance."""
        if not matches:
            return baseline_metrics
        
        # Calculate weights based on recency
        now = datetime.now()
        weighted_stats = defaultdict(float)
        total_weight = 0.0
        
        for match, participant in matches:
            match_date = match.game_creation_datetime
            days_ago = (now - match_date).days
            
            # Exponential decay weight (more recent = higher weight)
            weight = math.exp(-days_ago / (time_window_days / 3))
            total_weight += weight
            
            # Apply weights to individual match stats
            weighted_stats['wins'] += weight if participant.win else 0
            weighted_stats['kills'] += participant.kills * weight
            weighted_stats['deaths'] += participant.deaths * weight
            weighted_stats['assists'] += participant.assists * weight
            weighted_stats['cs'] += participant.cs_total * weight
            weighted_stats['vision'] += participant.vision_score * weight
            weighted_stats['damage'] += participant.total_damage_dealt_to_champions * weight
            weighted_stats['gold'] += participant.gold_earned * weight
            weighted_stats['duration'] += match.game_duration * weight
        
        if total_weight == 0:
            return baseline_metrics
        
        # Calculate weighted averages
        games_played = len(matches)
        win_rate = weighted_stats['wins'] / total_weight
        avg_kda = (weighted_stats['kills'] + weighted_stats['assists']) / max(weighted_stats['deaths'], total_weight)
        
        total_duration_weighted = weighted_stats['duration']
        avg_cs_per_min = weighted_stats['cs'] / (total_duration_weighted / 60) if total_duration_weighted > 0 else 0
        avg_vision_score = weighted_stats['vision'] / total_weight
        avg_damage_per_min = weighted_stats['damage'] / (total_duration_weighted / 60) if total_duration_weighted > 0 else 0
        avg_gold_per_min = weighted_stats['gold'] / (total_duration_weighted / 60) if total_duration_weighted > 0 else 0
        avg_game_duration = total_duration_weighted / (total_weight * 60)
        
        return PerformanceMetrics(
            games_played=games_played,
            wins=int(weighted_stats['wins'] / total_weight * games_played),
            losses=games_played - int(weighted_stats['wins'] / total_weight * games_played),
            win_rate=win_rate,
            total_kills=int(weighted_stats['kills'] / total_weight * games_played),
            total_deaths=int(weighted_stats['deaths'] / total_weight * games_played),
            total_assists=int(weighted_stats['assists'] / total_weight * games_played),
            avg_kda=avg_kda,
            total_cs=int(weighted_stats['cs'] / total_weight * games_played),
            avg_cs_per_min=avg_cs_per_min,
            total_vision_score=int(weighted_stats['vision'] / total_weight * games_played),
            avg_vision_score=avg_vision_score,
            total_damage_to_champions=int(weighted_stats['damage'] / total_weight * games_played),
            avg_damage_per_min=avg_damage_per_min,
            total_gold_earned=int(weighted_stats['gold'] / total_weight * games_played),
            avg_gold_per_min=avg_gold_per_min,
            total_game_duration=int(total_duration_weighted / total_weight * games_played),
            avg_game_duration=avg_game_duration
        )
    
    def _calculate_confidence_interval(self, matches: List[Tuple[Match, MatchParticipant]], 
                                     baseline_metrics: PerformanceMetrics) -> ConfidenceInterval:
        """Calculate confidence interval for baseline metrics."""
        sample_size = len(matches)
        
        # For win rate (binomial distribution)
        win_rate = baseline_metrics.win_rate
        
        # Standard error for binomial proportion
        if sample_size > 0 and 0 < win_rate < 1:
            se = math.sqrt(win_rate * (1 - win_rate) / sample_size)
            
            # Z-score for 95% confidence
            z_score = 1.96
            margin_of_error = z_score * se
            
            lower_bound = max(0, win_rate - margin_of_error)
            upper_bound = min(1, win_rate + margin_of_error)
        else:
            lower_bound = win_rate
            upper_bound = win_rate
        
        return ConfidenceInterval(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=self.confidence_level,
            sample_size=sample_size
        )
    
    def _calculate_percentile_rank(self, actual_value: float, baseline_value: float, 
                                 confidence_interval: ConfidenceInterval) -> float:
        """Calculate percentile rank for a performance metric."""
        if baseline_value == 0:
            return 50.0  # Neutral percentile
        
        # Simple percentile calculation based on deviation from baseline
        deviation = (actual_value - baseline_value) / baseline_value
        
        # Convert to percentile (simplified normal distribution assumption)
        if deviation > 0:
            percentile = 50 + min(deviation * 30, 45)  # Cap at 95th percentile
        else:
            percentile = 50 + max(deviation * 30, -45)  # Floor at 5th percentile
        
        return max(0, min(100, percentile))
    
    def _calculate_synergy_adjustments(self, puuid: str, champion_id: int, role: str,
                                     teammate_puuids: List[str]) -> Dict[str, float]:
        """Calculate synergy adjustments for team composition context."""
        adjustments = {}
        
        # Get matches with these teammates
        for teammate_puuid in teammate_puuids:
            # Find matches where both players were present
            player_matches = self.match_manager.get_matches_for_player(puuid)
            teammate_matches = set(match.match_id for match in self.match_manager.get_matches_for_player(teammate_puuid))
            
            shared_matches = [match for match in player_matches if match.match_id in teammate_matches]
            
            if len(shared_matches) >= 3:  # Minimum for synergy calculation
                # Calculate performance with this teammate vs without
                with_teammate_performance = self._calculate_performance_with_teammate(
                    puuid, champion_id, role, shared_matches
                )
                
                # Simple synergy adjustment based on win rate difference
                base_win_rate = 0.5  # Assume neutral baseline
                synergy_adjustment = with_teammate_performance - base_win_rate
                adjustments[teammate_puuid] = max(-0.2, min(0.2, synergy_adjustment))
        
        return adjustments
    
    def _calculate_performance_with_teammate(self, puuid: str, champion_id: int, role: str,
                                           shared_matches: List[Match]) -> float:
        """Calculate performance metrics when playing with a specific teammate."""
        relevant_matches = []
        
        for match in shared_matches:
            participant = match.get_participant_by_puuid(puuid)
            if (participant and 
                participant.champion_id == champion_id and 
                self._normalize_role(participant.individual_position) == role):
                relevant_matches.append(participant)
        
        if not relevant_matches:
            return 0.5  # Neutral performance
        
        win_rate = sum(1 for p in relevant_matches if p.win) / len(relevant_matches)
        return win_rate
    
    def _calculate_meta_adjustment(self, champion_id: int, role: str) -> float:
        """Calculate meta adjustment for champion-role combination."""
        # Simplified meta adjustment - in a real implementation, this would
        # analyze recent match data to determine champion strength in current meta
        
        # For now, return neutral adjustment
        return 0.0
    
    def _normalize_role(self, position: str) -> str:
        """Normalize Riot's position strings to our standard roles."""
        position_mapping = {
            'TOP': 'top',
            'JUNGLE': 'jungle',
            'MIDDLE': 'middle',
            'BOTTOM': 'bottom',
            'UTILITY': 'support'
        }
        return position_mapping.get(position, position.lower())
    
    def get_baseline_statistics(self) -> Dict[str, Any]:
        """Get statistics about cached baselines."""
        total_baselines = len(self.cache.memory_cache)
        
        # Count by type
        overall_count = sum(1 for key in self.cache.memory_cache.keys() if 'champ_' not in key and 'role_' not in key)
        role_specific_count = sum(1 for key in self.cache.memory_cache.keys() if 'role_' in key and 'champ_' not in key)
        champion_specific_count = sum(1 for key in self.cache.memory_cache.keys() if 'champ_' in key)
        
        # Calculate average sample sizes
        sample_sizes = [baseline.sample_size for baseline in self.cache.memory_cache.values()]
        avg_sample_size = statistics.mean(sample_sizes) if sample_sizes else 0
        
        return {
            'total_baselines': total_baselines,
            'overall_baselines': overall_count,
            'role_specific_baselines': role_specific_count,
            'champion_specific_baselines': champion_specific_count,
            'average_sample_size': avg_sample_size,
            'cache_hit_potential': total_baselines > 0
        }
    
    def cleanup_cache(self) -> int:
        """Clean up stale baselines from cache."""
        return self.cache.cleanup_stale()