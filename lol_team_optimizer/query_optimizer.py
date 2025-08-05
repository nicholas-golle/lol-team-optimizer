"""
Query Optimizer for the League of Legends Team Optimizer.

This module provides efficient database query optimization for match data,
including query planning, indexing strategies, and result caching.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps
import threading

from .analytics_models import AnalyticsFilters, DateRange, AnalyticsError
from .models import Match, MatchParticipant
from .config import Config


logger = logging.getLogger(__name__)


class QueryOptimizationError(AnalyticsError):
    """Base exception for query optimization operations."""
    pass


@dataclass
class QueryPlan:
    """Represents an optimized query execution plan."""
    
    query_id: str
    filters: AnalyticsFilters
    estimated_cost: float
    execution_steps: List[str] = field(default_factory=list)
    use_indexes: List[str] = field(default_factory=list)
    cache_strategy: str = "memory"
    parallel_execution: bool = False
    
    def add_step(self, step: str, cost: float = 1.0):
        """Add an execution step to the plan."""
        self.execution_steps.append(step)
        self.estimated_cost += cost


@dataclass
class QueryStatistics:
    """Statistics for query performance monitoring."""
    
    query_type: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    results_returned: int = 0
    last_executed: Optional[datetime] = None
    
    def update(self, execution_time: float, result_count: int, cache_hit: bool = False):
        """Update statistics with new execution data."""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.average_execution_time = self.total_execution_time / self.execution_count
        self.results_returned += result_count
        self.last_executed = datetime.now()
        
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100.0


class MatchIndex:
    """In-memory index for efficient match querying."""
    
    def __init__(self):
        """Initialize match index."""
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        
        # Primary indexes
        self.by_player: Dict[str, Set[str]] = defaultdict(set)  # puuid -> match_ids
        self.by_champion: Dict[int, Set[str]] = defaultdict(set)  # champion_id -> match_ids
        self.by_role: Dict[str, Set[str]] = defaultdict(set)  # role -> match_ids
        self.by_queue: Dict[int, Set[str]] = defaultdict(set)  # queue_id -> match_ids
        self.by_date: Dict[str, Set[str]] = defaultdict(set)  # date_key -> match_ids
        
        # Composite indexes
        self.by_player_champion: Dict[Tuple[str, int], Set[str]] = defaultdict(set)
        self.by_player_role: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        self.by_champion_role: Dict[Tuple[int, str], Set[str]] = defaultdict(set)
        self.by_player_champion_role: Dict[Tuple[str, int, str], Set[str]] = defaultdict(set)
        
        # Statistics
        self.total_matches_indexed = 0
        self.last_updated = datetime.now()
    
    def add_match(self, match: Match):
        """Add a match to the index.
        
        Args:
            match: Match to index
        """
        with self._lock:
            match_id = match.match_id
            
            # Date index (by day)
            match_date = datetime.fromtimestamp(match.game_creation / 1000)
            date_key = match_date.strftime("%Y-%m-%d")
            self.by_date[date_key].add(match_id)
            
            # Queue index
            self.by_queue[match.queue_id].add(match_id)
            
            # Participant-based indexes
            for participant in match.participants:
                puuid = participant.puuid
                champion_id = participant.champion_id
                role = participant.individual_position.lower()
                
                # Primary indexes
                self.by_player[puuid].add(match_id)
                self.by_champion[champion_id].add(match_id)
                self.by_role[role].add(match_id)
                
                # Composite indexes
                self.by_player_champion[(puuid, champion_id)].add(match_id)
                self.by_player_role[(puuid, role)].add(match_id)
                self.by_champion_role[(champion_id, role)].add(match_id)
                self.by_player_champion_role[(puuid, champion_id, role)].add(match_id)
            
            self.total_matches_indexed += 1
            self.last_updated = datetime.now()
    
    def remove_match(self, match: Match):
        """Remove a match from the index.
        
        Args:
            match: Match to remove
        """
        with self._lock:
            match_id = match.match_id
            
            # Date index
            match_date = datetime.fromtimestamp(match.game_creation / 1000)
            date_key = match_date.strftime("%Y-%m-%d")
            self.by_date[date_key].discard(match_id)
            
            # Queue index
            self.by_queue[match.queue_id].discard(match_id)
            
            # Participant-based indexes
            for participant in match.participants:
                puuid = participant.puuid
                champion_id = participant.champion_id
                role = participant.individual_position.lower()
                
                # Primary indexes
                self.by_player[puuid].discard(match_id)
                self.by_champion[champion_id].discard(match_id)
                self.by_role[role].discard(match_id)
                
                # Composite indexes
                self.by_player_champion[(puuid, champion_id)].discard(match_id)
                self.by_player_role[(puuid, role)].discard(match_id)
                self.by_champion_role[(champion_id, role)].discard(match_id)
                self.by_player_champion_role[(puuid, champion_id, role)].discard(match_id)
            
            self.total_matches_indexed -= 1
            self.last_updated = datetime.now()
    
    def find_matches(self, filters: AnalyticsFilters) -> Set[str]:
        """Find match IDs matching the given filters.
        
        Args:
            filters: Filters to apply
            
        Returns:
            Set of matching match IDs
        """
        with self._lock:
            # Start with all matches if no specific filters
            candidate_matches: Optional[Set[str]] = None
            
            # Apply player filter (most selective usually)
            if filters.player_puuids:
                player_matches = set()
                for puuid in filters.player_puuids:
                    player_matches.update(self.by_player.get(puuid, set()))
                candidate_matches = self._intersect_candidates(candidate_matches, player_matches)
            
            # Apply champion filter
            if filters.champions:
                champion_matches = set()
                for champion_id in filters.champions:
                    champion_matches.update(self.by_champion.get(champion_id, set()))
                candidate_matches = self._intersect_candidates(candidate_matches, champion_matches)
            
            # Apply role filter
            if filters.roles:
                role_matches = set()
                for role in filters.roles:
                    role_matches.update(self.by_role.get(role.lower(), set()))
                candidate_matches = self._intersect_candidates(candidate_matches, role_matches)
            
            # Apply queue filter
            if filters.queue_types:
                queue_matches = set()
                for queue_id in filters.queue_types:
                    queue_matches.update(self.by_queue.get(queue_id, set()))
                candidate_matches = self._intersect_candidates(candidate_matches, queue_matches)
            
            # Apply date filter (requires match object access)
            if filters.date_range and candidate_matches is not None:
                # This is less efficient and should be done last
                # In a real database, this would use a date index
                pass  # Will be handled by the query optimizer
            
            return candidate_matches or set()
    
    def _intersect_candidates(self, current: Optional[Set[str]], new: Set[str]) -> Set[str]:
        """Intersect candidate sets efficiently.
        
        Args:
            current: Current candidate set (None means all matches)
            new: New candidate set to intersect
            
        Returns:
            Intersection of the sets
        """
        if current is None:
            return new
        return current.intersection(new)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics.
        
        Returns:
            Dictionary containing index statistics
        """
        with self._lock:
            return {
                'total_matches_indexed': self.total_matches_indexed,
                'unique_players': len(self.by_player),
                'unique_champions': len(self.by_champion),
                'unique_roles': len(self.by_role),
                'unique_queues': len(self.by_queue),
                'date_range_days': len(self.by_date),
                'last_updated': self.last_updated.isoformat()
            }


class QueryOptimizer:
    """Optimizes database queries for match data."""
    
    def __init__(self, config: Config, match_manager):
        """Initialize query optimizer.
        
        Args:
            config: Application configuration
            match_manager: MatchManager instance
        """
        self.config = config
        self.match_manager = match_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize index
        self.index = MatchIndex()
        self._build_initial_index()
        
        # Query statistics
        self.query_stats: Dict[str, QueryStatistics] = defaultdict(
            lambda: QueryStatistics(query_type="unknown")
        )
        self._stats_lock = threading.RLock()
        
        # Query cache
        self.query_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl_seconds = 300  # 5 minutes
        self._cache_lock = threading.RLock()
    
    def _build_initial_index(self):
        """Build initial index from existing matches."""
        try:
            # Get all matches from match manager
            all_matches = []
            
            # This is a simplified approach - in practice, you'd want to
            # iterate through matches more efficiently
            stats = self.match_manager.get_match_statistics()
            if stats['total_matches'] > 0:
                # Get recent matches to build initial index
                recent_matches = self.match_manager.get_recent_matches(days=365, limit=10000)
                
                for match in recent_matches:
                    self.index.add_match(match)
                
                self.logger.info(f"Built initial index with {len(recent_matches)} matches")
            
        except Exception as e:
            self.logger.error(f"Failed to build initial index: {e}")
    
    def optimize_query(self, filters: AnalyticsFilters, query_type: str = "general") -> QueryPlan:
        """Create an optimized query plan.
        
        Args:
            filters: Query filters
            query_type: Type of query for optimization
            
        Returns:
            Optimized query plan
        """
        plan = QueryPlan(
            query_id=f"{query_type}_{hash(str(filters))}",
            filters=filters
        )
        
        # Estimate selectivity of different filters
        selectivity_scores = self._calculate_filter_selectivity(filters)
        
        # Order filters by selectivity (most selective first)
        ordered_filters = sorted(selectivity_scores.items(), key=lambda x: x[1])
        
        # Build execution plan
        for filter_type, selectivity in ordered_filters:
            if selectivity > 0:
                if filter_type == "player":
                    plan.add_step("Apply player filter", cost=1.0)
                    plan.use_indexes.append("by_player")
                elif filter_type == "champion":
                    plan.add_step("Apply champion filter", cost=2.0)
                    plan.use_indexes.append("by_champion")
                elif filter_type == "role":
                    plan.add_step("Apply role filter", cost=2.0)
                    plan.use_indexes.append("by_role")
                elif filter_type == "queue":
                    plan.add_step("Apply queue filter", cost=1.5)
                    plan.use_indexes.append("by_queue")
                elif filter_type == "date":
                    plan.add_step("Apply date filter", cost=3.0)
                    plan.use_indexes.append("by_date")
        
        # Determine cache strategy
        if plan.estimated_cost > 10.0:
            plan.cache_strategy = "persistent"
        elif plan.estimated_cost > 5.0:
            plan.cache_strategy = "memory"
        else:
            plan.cache_strategy = "none"
        
        # Determine if parallel execution would help
        if plan.estimated_cost > 20.0:
            plan.parallel_execution = True
        
        return plan
    
    def execute_optimized_query(self, filters: AnalyticsFilters, 
                              query_type: str = "general") -> List[Match]:
        """Execute an optimized query.
        
        Args:
            filters: Query filters
            query_type: Type of query
            
        Returns:
            List of matching matches
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = f"{query_type}_{hash(str(filters))}"
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            execution_time = time.time() - start_time
            self._update_query_stats(query_type, execution_time, len(cached_result), cache_hit=True)
            return cached_result
        
        # Create and execute query plan
        plan = self.optimize_query(filters, query_type)
        
        try:
            # Use index to find candidate matches
            candidate_match_ids = self.index.find_matches(filters)
            
            # Get actual match objects
            matches = []
            for match_id in candidate_match_ids:
                match = self.match_manager.get_match(match_id)
                if match and self._match_passes_filters(match, filters):
                    matches.append(match)
            
            # Sort matches by game creation time (newest first)
            matches.sort(key=lambda m: m.game_creation, reverse=True)
            
            # Apply limit if specified
            if filters.limit and len(matches) > filters.limit:
                matches = matches[:filters.limit]
            
            # Cache result if appropriate
            if plan.cache_strategy != "none":
                self._cache_result(cache_key, matches, plan.cache_strategy == "persistent")
            
            execution_time = time.time() - start_time
            self._update_query_stats(query_type, execution_time, len(matches), cache_hit=False)
            
            self.logger.debug(f"Executed optimized query: {len(matches)} results in {execution_time:.3f}s")
            return matches
            
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise QueryOptimizationError(f"Query execution failed: {e}")
    
    def _calculate_filter_selectivity(self, filters: AnalyticsFilters) -> Dict[str, float]:
        """Calculate selectivity scores for filters.
        
        Args:
            filters: Query filters
            
        Returns:
            Dictionary mapping filter types to selectivity scores
        """
        selectivity = {}
        
        # Player filter selectivity
        if filters.player_puuids:
            # More players = less selective
            selectivity["player"] = 1.0 / len(filters.player_puuids)
        else:
            selectivity["player"] = 0.0
        
        # Champion filter selectivity
        if filters.champions:
            # Fewer champions = more selective
            selectivity["champion"] = 1.0 / len(filters.champions)
        else:
            selectivity["champion"] = 0.0
        
        # Role filter selectivity
        if filters.roles:
            # Roles are fairly selective (5 main roles)
            selectivity["role"] = 1.0 / max(len(filters.roles), 1)
        else:
            selectivity["role"] = 0.0
        
        # Queue filter selectivity
        if filters.queue_types:
            # Queue types are moderately selective
            selectivity["queue"] = 1.0 / max(len(filters.queue_types), 1)
        else:
            selectivity["queue"] = 0.0
        
        # Date filter selectivity
        if filters.date_range:
            # Date ranges can be very selective
            days_span = (filters.date_range.end_date - filters.date_range.start_date).days
            selectivity["date"] = 1.0 / max(days_span, 1)
        else:
            selectivity["date"] = 0.0
        
        return selectivity
    
    def _match_passes_filters(self, match: Match, filters: AnalyticsFilters) -> bool:
        """Check if a match passes all filters.
        
        Args:
            match: Match to check
            filters: Filters to apply
            
        Returns:
            True if match passes all filters
        """
        # Date filter
        if filters.date_range:
            match_date = datetime.fromtimestamp(match.game_creation / 1000)
            if not filters.date_range.contains(match_date):
                return False
        
        # Queue filter
        if filters.queue_types and match.queue_id not in filters.queue_types:
            return False
        
        # Win filter
        if filters.win_only is not None:
            # This requires checking specific participants
            if filters.player_puuids:
                for puuid in filters.player_puuids:
                    participant = match.get_participant_by_puuid(puuid)
                    if participant and participant.win != filters.win_only:
                        return False
        
        # Minimum games filter is handled at a higher level
        
        return True
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[Match]]:
        """Get cached query result.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached result if found and not expired, None otherwise
        """
        with self._cache_lock:
            if cache_key in self.query_cache:
                result, timestamp = self.query_cache[cache_key]
                
                # Check if expired
                if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl_seconds):
                    return result
                else:
                    # Remove expired entry
                    del self.query_cache[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: List[Match], persistent: bool = False):
        """Cache query result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
            persistent: Whether to use persistent cache
        """
        with self._cache_lock:
            # For now, just use memory cache
            # In a full implementation, persistent would use disk cache
            self.query_cache[cache_key] = (result, datetime.now())
            
            # Limit cache size
            if len(self.query_cache) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(
                    self.query_cache.keys(),
                    key=lambda k: self.query_cache[k][1]
                )[:100]
                
                for key in oldest_keys:
                    del self.query_cache[key]
    
    def _update_query_stats(self, query_type: str, execution_time: float, 
                          result_count: int, cache_hit: bool = False):
        """Update query statistics.
        
        Args:
            query_type: Type of query
            execution_time: Execution time in seconds
            result_count: Number of results returned
            cache_hit: Whether this was a cache hit
        """
        with self._stats_lock:
            if query_type not in self.query_stats:
                self.query_stats[query_type] = QueryStatistics(query_type=query_type)
            
            self.query_stats[query_type].update(execution_time, result_count, cache_hit)
    
    def get_query_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get query performance statistics.
        
        Returns:
            Dictionary containing query statistics
        """
        with self._stats_lock:
            stats = {}
            for query_type, stat in self.query_stats.items():
                stats[query_type] = {
                    'execution_count': stat.execution_count,
                    'average_execution_time': stat.average_execution_time,
                    'cache_hit_rate': stat.cache_hit_rate,
                    'total_results_returned': stat.results_returned,
                    'last_executed': stat.last_executed.isoformat() if stat.last_executed else None
                }
            
            return stats
    
    def clear_cache(self):
        """Clear query cache."""
        with self._cache_lock:
            self.query_cache.clear()
            self.logger.info("Query cache cleared")
    
    def rebuild_index(self):
        """Rebuild the match index."""
        self.index = MatchIndex()
        self._build_initial_index()
        self.logger.info("Match index rebuilt")
    
    def add_match_to_index(self, match: Match):
        """Add a new match to the index.
        
        Args:
            match: Match to add
        """
        self.index.add_match(match)
    
    def remove_match_from_index(self, match: Match):
        """Remove a match from the index.
        
        Args:
            match: Match to remove
        """
        self.index.remove_match(match)


def query_performance_monitor(func: Callable) -> Callable:
    """Decorator to monitor query performance.
    
    Args:
        func: Function to monitor
        
    Returns:
        Wrapped function with performance monitoring
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow queries
            if execution_time > 1.0:
                logger.warning(f"Slow query detected: {func.__name__} took {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Query failed: {func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper