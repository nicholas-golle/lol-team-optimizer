"""
Player Synergy Matrix and Pairing Analysis System.

This module implements comprehensive player-to-player synergy analysis,
role-specific synergy calculations, synergy matrix visualization data structures,
and synergy trend analysis over time periods for team building recommendations.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import itertools

from .analytics_models import (
    AnalyticsFilters, DateRange, PerformanceMetrics, PerformanceDelta,
    SignificanceTest, ConfidenceInterval, InsufficientDataError,
    AnalyticsError, TimeSeriesPoint, TrendAnalysis
)
from .statistical_analyzer import StatisticalAnalyzer
from .baseline_manager import BaselineManager
from .config import Config


@dataclass
class PlayerPairSynergy:
    """Represents synergy data between two specific players."""
    
    player1_puuid: str
    player2_puuid: str
    player1_name: str
    player2_name: str
    
    # Overall synergy metrics
    total_games_together: int = 0
    wins_together: int = 0
    losses_together: int = 0
    win_rate_together: float = 0.0
    
    # Performance metrics when playing together
    avg_combined_kda: float = 0.0
    avg_combined_cs_per_min: float = 0.0
    avg_combined_vision_score: float = 0.0
    avg_combined_damage_per_min: float = 0.0
    avg_game_duration_minutes: float = 0.0
    
    # Synergy score (-1.0 to 1.0)
    synergy_score: float = 0.0
    confidence_level: float = 0.0
    
    # Role-specific synergy breakdown
    role_synergies: Dict[Tuple[str, str], 'RolePairSynergy'] = field(default_factory=dict)
    
    # Temporal data
    last_played_together: Optional[datetime] = None
    recent_games_together: int = 0  # Games in last 60 days
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_games_together > 0:
            self.win_rate_together = self.wins_together / self.total_games_together


@dataclass
class RolePairSynergy:
    """Represents synergy between two players in specific roles."""
    
    role1: str
    role2: str
    games_together: int = 0
    wins_together: int = 0
    win_rate: float = 0.0
    
    # Performance metrics for this role combination
    avg_combined_performance: float = 0.0
    synergy_score: float = 0.0
    
    # Champion combinations in these roles
    champion_combinations: Dict[Tuple[int, int], Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.games_together > 0:
            self.win_rate = self.wins_together / self.games_together


@dataclass
class SynergyMatrixEntry:
    """Single entry in a synergy matrix."""
    
    entity1: str  # Player PUUID, champion ID, or role
    entity2: str
    synergy_score: float
    confidence: float
    sample_size: int
    last_updated: datetime
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynergyMatrix:
    """Complete synergy matrix with visualization data structures."""
    
    matrix_type: str  # "player", "role", "champion"
    entries: Dict[Tuple[str, str], SynergyMatrixEntry] = field(default_factory=dict)
    
    # Matrix metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    total_entities: int = 0
    
    # Visualization data
    entity_labels: Dict[str, str] = field(default_factory=dict)  # entity_id -> display_name
    color_scale_bounds: Tuple[float, float] = (-1.0, 1.0)
    
    def get_synergy(self, entity1: str, entity2: str) -> Optional[SynergyMatrixEntry]:
        """Get synergy entry between two entities."""
        key = tuple(sorted([entity1, entity2]))
        return self.entries.get(key)
    
    def set_synergy(self, entity1: str, entity2: str, entry: SynergyMatrixEntry) -> None:
        """Set synergy entry between two entities."""
        key = tuple(sorted([entity1, entity2]))
        self.entries[key] = entry
        self.last_updated = datetime.now()


@dataclass
class SynergyTrendPoint:
    """Single point in synergy trend analysis."""
    
    timestamp: datetime
    synergy_score: float
    games_in_period: int
    win_rate_in_period: float
    confidence: float


@dataclass
class SynergyTrendAnalysis:
    """Trend analysis for player pair synergy over time."""
    
    player1_puuid: str
    player2_puuid: str
    trend_points: List[SynergyTrendPoint] = field(default_factory=list)
    
    # Trend metrics
    trend_direction: str = "stable"  # "improving", "declining", "stable"
    trend_strength: float = 0.0  # 0.0 to 1.0
    trend_duration_days: int = 0
    
    # Statistical measures
    correlation_coefficient: float = 0.0
    trend_significance: Optional[SignificanceTest] = None
    
    # Key insights
    peak_synergy_period: Optional[Tuple[datetime, datetime]] = None
    lowest_synergy_period: Optional[Tuple[datetime, datetime]] = None
    most_active_period: Optional[Tuple[datetime, datetime]] = None


@dataclass
class TeamBuildingRecommendation:
    """Recommendation for team building based on synergy analysis."""
    
    recommended_pairs: List[Tuple[str, str, float]] = field(default_factory=list)  # (puuid1, puuid2, synergy)
    role_assignments: Dict[str, str] = field(default_factory=dict)  # role -> puuid
    expected_team_synergy: float = 0.0
    confidence: float = 0.0
    
    # Supporting data
    reasoning: List[str] = field(default_factory=list)
    alternative_options: List[Dict[str, Any]] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


class PlayerSynergyMatrix:
    """
    Comprehensive player synergy matrix and pairing analysis system.
    
    Implements player-to-player synergy calculation from match history,
    role-specific synergy analysis, synergy matrix visualization data structures,
    synergy trend analysis over time periods, and synergy-based team building
    recommendations.
    """
    
    def __init__(
        self,
        config: Config,
        match_manager,
        baseline_manager: BaselineManager,
        statistical_analyzer: StatisticalAnalyzer
    ):
        """
        Initialize the player synergy matrix system.
        
        Args:
            config: Configuration object
            match_manager: Match manager for data access
            baseline_manager: Baseline manager for performance comparisons
            statistical_analyzer: Statistical analyzer for significance testing
        """
        self.config = config
        self.match_manager = match_manager
        self.baseline_manager = baseline_manager
        self.statistical_analyzer = statistical_analyzer
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.min_games_for_synergy = 5
        self.min_games_for_trend = 10
        self.synergy_confidence_threshold = 0.05
        self.recent_cutoff_days = 60
        self.trend_window_days = 30
        
        # Cache for computed synergies
        self._synergy_cache: Dict[Tuple[str, str], PlayerPairSynergy] = {}
        self._cache_expiry: Dict[Tuple[str, str], datetime] = {}
        self.cache_duration_hours = 6   
 
    def calculate_player_synergy(
        self,
        player1_puuid: str,
        player2_puuid: str,
        filters: Optional[AnalyticsFilters] = None
    ) -> PlayerPairSynergy:
        """
        Calculate synergy between two specific players from match history.
        
        Args:
            player1_puuid: First player's PUUID
            player2_puuid: Second player's PUUID
            filters: Optional filters for match selection
            
        Returns:
            PlayerPairSynergy object with detailed synergy analysis
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If calculation fails
        """
        try:
            # Check cache first
            cache_key = tuple(sorted([player1_puuid, player2_puuid]))
            if self._is_cache_valid(cache_key):
                self.logger.debug(f"Using cached synergy for {cache_key}")
                return self._synergy_cache[cache_key]
            
            self.logger.info(f"Calculating player synergy between {player1_puuid} and {player2_puuid}")
            
            # Get matches where both players played together
            shared_matches = self.match_manager.get_matches_with_multiple_players(
                {player1_puuid, player2_puuid}
            )
            
            if not shared_matches:
                raise InsufficientDataError(
                    required_games=1,
                    available_games=0,
                    context=f"player synergy between {player1_puuid} and {player2_puuid}"
                )
            
            # Apply filters if provided
            if filters:
                shared_matches = self._apply_filters_to_matches(shared_matches, filters)
            
            if len(shared_matches) < self.min_games_for_synergy:
                raise InsufficientDataError(
                    required_games=self.min_games_for_synergy,
                    available_games=len(shared_matches),
                    context=f"player synergy calculation"
                )
            
            # Extract player names for display
            player1_name = self._get_player_name(player1_puuid)
            player2_name = self._get_player_name(player2_puuid)
            
            # Calculate synergy metrics
            synergy = self._calculate_synergy_from_matches(
                player1_puuid, player2_puuid, player1_name, player2_name, shared_matches
            )
            
            # Calculate role-specific synergies
            synergy.role_synergies = self._calculate_role_specific_synergies(
                player1_puuid, player2_puuid, shared_matches
            )
            
            # Calculate confidence level
            synergy.confidence_level = self._calculate_synergy_confidence(len(shared_matches))
            
            # Cache the result
            self._synergy_cache[cache_key] = synergy
            self._cache_expiry[cache_key] = datetime.now() + timedelta(hours=self.cache_duration_hours)
            
            self.logger.info(f"Calculated synergy: {synergy.synergy_score:.3f} from {len(shared_matches)} games")
            return synergy
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate player synergy: {e}")
    
    def analyze_role_specific_synergy(
        self,
        player1_puuid: str,
        player2_puuid: str,
        role1: str,
        role2: str,
        filters: Optional[AnalyticsFilters] = None
    ) -> RolePairSynergy:
        """
        Analyze synergy between two players in specific roles.
        
        Args:
            player1_puuid: First player's PUUID
            player2_puuid: Second player's PUUID
            role1: First player's role
            role2: Second player's role
            filters: Optional filters for match selection
            
        Returns:
            RolePairSynergy object with role-specific analysis
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If analysis fails
        """
        try:
            self.logger.info(f"Analyzing role synergy: {role1}-{role2} for players {player1_puuid}, {player2_puuid}")
            
            # Get matches where both players played together
            shared_matches = self.match_manager.get_matches_with_multiple_players(
                {player1_puuid, player2_puuid}
            )
            
            # Filter matches by role assignments
            role_filtered_matches = []
            for match in shared_matches:
                p1_participant = match.get_participant_by_puuid(player1_puuid)
                p2_participant = match.get_participant_by_puuid(player2_puuid)
                
                if (p1_participant and p2_participant and
                    self._normalize_role(p1_participant.individual_position) == role1 and
                    self._normalize_role(p2_participant.individual_position) == role2):
                    role_filtered_matches.append(match)
            
            if not role_filtered_matches:
                raise InsufficientDataError(
                    required_games=1,
                    available_games=0,
                    context=f"role synergy {role1}-{role2}"
                )
            
            # Apply additional filters if provided
            if filters:
                role_filtered_matches = self._apply_filters_to_matches(role_filtered_matches, filters)
            
            # Calculate role-specific synergy
            role_synergy = self._calculate_role_synergy_from_matches(
                role1, role2, role_filtered_matches, player1_puuid, player2_puuid
            )
            
            self.logger.info(f"Role synergy {role1}-{role2}: {role_synergy.synergy_score:.3f} from {len(role_filtered_matches)} games")
            return role_synergy
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze role-specific synergy: {e}")
    
    def create_synergy_matrix(
        self,
        player_puuids: List[str],
        matrix_type: str = "player",
        filters: Optional[AnalyticsFilters] = None
    ) -> SynergyMatrix:
        """
        Create synergy matrix visualization data structures.
        
        Args:
            player_puuids: List of player PUUIDs to include in matrix
            matrix_type: Type of matrix ("player", "role", "champion")
            filters: Optional filters for match selection
            
        Returns:
            SynergyMatrix object with visualization data
            
        Raises:
            AnalyticsError: If matrix creation fails
        """
        try:
            self.logger.info(f"Creating {matrix_type} synergy matrix for {len(player_puuids)} players")
            
            matrix = SynergyMatrix(
                matrix_type=matrix_type,
                total_entities=len(player_puuids)
            )
            
            if matrix_type == "player":
                matrix = self._create_player_synergy_matrix(player_puuids, filters, matrix)
            elif matrix_type == "role":
                matrix = self._create_role_synergy_matrix(player_puuids, filters, matrix)
            elif matrix_type == "champion":
                matrix = self._create_champion_synergy_matrix(player_puuids, filters, matrix)
            else:
                raise AnalyticsError(f"Unsupported matrix type: {matrix_type}")
            
            self.logger.info(f"Created synergy matrix with {len(matrix.entries)} entries")
            return matrix
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to create synergy matrix: {e}")
    
    def analyze_synergy_trends(
        self,
        player1_puuid: str,
        player2_puuid: str,
        time_window_days: int = 180,
        trend_window_days: Optional[int] = None
    ) -> SynergyTrendAnalysis:
        """
        Implement synergy trend analysis over time periods.
        
        Args:
            player1_puuid: First player's PUUID
            player2_puuid: Second player's PUUID
            time_window_days: Total time window to analyze
            trend_window_days: Size of each trend window (defaults to self.trend_window_days)
            
        Returns:
            SynergyTrendAnalysis object with trend data
            
        Raises:
            InsufficientDataError: If not enough data for trend analysis
            AnalyticsError: If analysis fails
        """
        try:
            if trend_window_days is None:
                trend_window_days = self.trend_window_days
            
            self.logger.info(f"Analyzing synergy trends for {player1_puuid}, {player2_puuid} over {time_window_days} days")
            
            # Get all matches between the players in the time window
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            shared_matches = self.match_manager.get_matches_with_multiple_players(
                {player1_puuid, player2_puuid}
            )
            shared_matches = self._apply_filters_to_matches(shared_matches, filters)
            
            if len(shared_matches) < self.min_games_for_trend:
                raise InsufficientDataError(
                    required_games=self.min_games_for_trend,
                    available_games=len(shared_matches),
                    context="synergy trend analysis"
                )
            
            # Create trend points by time windows
            trend_points = self._create_trend_points(
                shared_matches, player1_puuid, player2_puuid, trend_window_days
            )
            
            # Analyze trend characteristics
            trend_analysis = SynergyTrendAnalysis(
                player1_puuid=player1_puuid,
                player2_puuid=player2_puuid,
                trend_points=trend_points
            )
            
            # Calculate trend metrics
            self._calculate_trend_metrics(trend_analysis)
            
            # Identify key periods
            self._identify_key_periods(trend_analysis)
            
            self.logger.info(f"Trend analysis complete: {trend_analysis.trend_direction} trend with strength {trend_analysis.trend_strength:.3f}")
            return trend_analysis
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze synergy trends: {e}")
    
    def generate_team_building_recommendations(
        self,
        available_players: List[str],
        required_roles: List[str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> List[TeamBuildingRecommendation]:
        """
        Add synergy-based team building recommendations.
        
        Args:
            available_players: List of available player PUUIDs
            required_roles: List of roles that need to be filled
            constraints: Optional constraints for team building
            
        Returns:
            List of TeamBuildingRecommendation objects sorted by expected synergy
            
        Raises:
            AnalyticsError: If recommendation generation fails
        """
        try:
            self.logger.info(f"Generating team building recommendations for {len(available_players)} players")
            
            if len(available_players) < len(required_roles):
                raise AnalyticsError("Not enough players for required roles")
            
            # Calculate synergy matrix for all available players
            synergy_matrix = self.create_synergy_matrix(available_players, "player")
            
            # Generate possible team compositions
            possible_teams = self._generate_possible_teams(
                available_players, required_roles, constraints
            )
            
            # Evaluate each team composition
            recommendations = []
            for team_composition in possible_teams:
                try:
                    recommendation = self._evaluate_team_composition(
                        team_composition, synergy_matrix, constraints
                    )
                    recommendations.append(recommendation)
                except Exception as e:
                    self.logger.warning(f"Failed to evaluate team composition: {e}")
                    continue
            
            # Sort by expected team synergy
            recommendations.sort(key=lambda x: x.expected_team_synergy, reverse=True)
            
            # Limit to top recommendations
            max_recommendations = constraints.get('max_recommendations', 5) if constraints else 5
            recommendations = recommendations[:max_recommendations]
            
            self.logger.info(f"Generated {len(recommendations)} team building recommendations")
            return recommendations
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to generate team building recommendations: {e}")    

    # Helper methods
    
    def _is_cache_valid(self, cache_key: Tuple[str, str]) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self._synergy_cache:
            return False
        
        if cache_key not in self._cache_expiry:
            return False
        
        return datetime.now() < self._cache_expiry[cache_key]
    
    def _get_player_name(self, puuid: str) -> str:
        """Get player display name from PUUID."""
        # This would typically query the player database
        # For now, return a truncated PUUID
        return puuid[:8] if puuid else "Unknown"
    
    def _apply_filters_to_matches(self, matches: List[Any], filters: AnalyticsFilters) -> List[Any]:
        """Apply analytics filters to match list."""
        filtered_matches = []
        
        for match in matches:
            # Date range filter
            if filters.date_range:
                if not filters.date_range.contains(match.game_creation_datetime):
                    continue
            
            # Queue type filter
            if filters.queue_types and match.queue_id not in filters.queue_types:
                continue
            
            # Win only filter
            if filters.win_only is not None:
                # This would need match-specific logic based on the players
                pass
            
            filtered_matches.append(match)
        
        return filtered_matches
    
    def _calculate_synergy_from_matches(
        self,
        player1_puuid: str,
        player2_puuid: str,
        player1_name: str,
        player2_name: str,
        matches: List[Any]
    ) -> PlayerPairSynergy:
        """Calculate synergy metrics from match data."""
        synergy = PlayerPairSynergy(
            player1_puuid=player1_puuid,
            player2_puuid=player2_puuid,
            player1_name=player1_name,
            player2_name=player2_name
        )
        
        total_games = len(matches)
        wins = 0
        
        # Aggregate performance metrics
        total_combined_kda = 0.0
        total_combined_cs = 0.0
        total_combined_vision = 0.0
        total_combined_damage = 0.0
        total_duration = 0.0
        recent_games = 0
        
        recent_cutoff = datetime.now() - timedelta(days=self.recent_cutoff_days)
        
        for match in matches:
            p1_participant = match.get_participant_by_puuid(player1_puuid)
            p2_participant = match.get_participant_by_puuid(player2_puuid)
            
            if not p1_participant or not p2_participant:
                continue
            
            # Check if both players won (same team)
            if p1_participant.win and p2_participant.win:
                wins += 1
            
            # Calculate combined performance metrics
            p1_kda = p1_participant.kda
            p2_kda = p2_participant.kda
            combined_kda = (p1_kda + p2_kda) / 2
            
            p1_cs_per_min = p1_participant.cs_total / (match.game_duration / 60) if match.game_duration > 0 else 0
            p2_cs_per_min = p2_participant.cs_total / (match.game_duration / 60) if match.game_duration > 0 else 0
            combined_cs_per_min = (p1_cs_per_min + p2_cs_per_min) / 2
            
            combined_vision = p1_participant.vision_score + p2_participant.vision_score
            
            p1_damage_per_min = p1_participant.total_damage_dealt_to_champions / (match.game_duration / 60) if match.game_duration > 0 else 0
            p2_damage_per_min = p2_participant.total_damage_dealt_to_champions / (match.game_duration / 60) if match.game_duration > 0 else 0
            combined_damage_per_min = (p1_damage_per_min + p2_damage_per_min) / 2
            
            # Accumulate totals
            total_combined_kda += combined_kda
            total_combined_cs += combined_cs_per_min
            total_combined_vision += combined_vision
            total_combined_damage += combined_damage_per_min
            total_duration += match.game_duration / 60  # Convert to minutes
            
            # Check if recent game
            if match.game_creation_datetime >= recent_cutoff:
                recent_games += 1
            
            # Update last played together
            if (synergy.last_played_together is None or 
                match.game_creation_datetime > synergy.last_played_together):
                synergy.last_played_together = match.game_creation_datetime
        
        # Calculate averages
        synergy.total_games_together = total_games
        synergy.wins_together = wins
        synergy.losses_together = total_games - wins
        synergy.win_rate_together = wins / total_games if total_games > 0 else 0.0
        
        synergy.avg_combined_kda = total_combined_kda / total_games if total_games > 0 else 0.0
        synergy.avg_combined_cs_per_min = total_combined_cs / total_games if total_games > 0 else 0.0
        synergy.avg_combined_vision_score = total_combined_vision / total_games if total_games > 0 else 0.0
        synergy.avg_combined_damage_per_min = total_combined_damage / total_games if total_games > 0 else 0.0
        synergy.avg_game_duration_minutes = total_duration / total_games if total_games > 0 else 0.0
        synergy.recent_games_together = recent_games
        
        # Calculate synergy score
        synergy.synergy_score = self._calculate_synergy_score(synergy)
        
        return synergy
    
    def _calculate_synergy_score(self, synergy: PlayerPairSynergy) -> float:
        """Calculate overall synergy score from metrics."""
        if synergy.total_games_together == 0:
            return 0.0
        
        # Base score from win rate (centered around 0.5)
        win_rate_score = (synergy.win_rate_together - 0.5) * 2  # Scale to -1 to 1
        
        # Performance bonuses/penalties
        performance_score = 0.0
        
        # KDA bonus
        if synergy.avg_combined_kda > 2.5:
            performance_score += 0.1
        elif synergy.avg_combined_kda < 1.5:
            performance_score -= 0.1
        
        # Vision bonus
        if synergy.avg_combined_vision_score > 50:
            performance_score += 0.05
        
        # Recent activity bonus
        recency_bonus = 0.0
        if synergy.recent_games_together >= 5:
            recency_bonus = 0.1
        elif synergy.recent_games_together >= 2:
            recency_bonus = 0.05
        
        # Sample size confidence adjustment
        confidence = min(synergy.total_games_together / 20.0, 1.0)
        
        # Combine scores
        final_score = (win_rate_score * 0.7 + performance_score * 0.2 + recency_bonus * 0.1) * confidence
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, final_score))
    
    def _calculate_role_specific_synergies(
        self,
        player1_puuid: str,
        player2_puuid: str,
        matches: List[Any]
    ) -> Dict[Tuple[str, str], RolePairSynergy]:
        """Calculate synergies for all role combinations."""
        role_synergies = {}
        role_matches = defaultdict(list)
        
        # Group matches by role combinations
        for match in matches:
            p1_participant = match.get_participant_by_puuid(player1_puuid)
            p2_participant = match.get_participant_by_puuid(player2_puuid)
            
            if not p1_participant or not p2_participant:
                continue
            
            role1 = self._normalize_role(p1_participant.individual_position)
            role2 = self._normalize_role(p2_participant.individual_position)
            
            role_key = tuple(sorted([role1, role2]))
            role_matches[role_key].append(match)
        
        # Calculate synergy for each role combination
        for role_key, role_match_list in role_matches.items():
            if len(role_match_list) >= 2:  # Minimum games for role synergy
                role_synergy = self._calculate_role_synergy_from_matches(
                    role_key[0], role_key[1], role_match_list, player1_puuid, player2_puuid
                )
                role_synergies[role_key] = role_synergy
        
        return role_synergies
    
    def _calculate_role_synergy_from_matches(
        self,
        role1: str,
        role2: str,
        matches: List[Any],
        player1_puuid: str,
        player2_puuid: str
    ) -> RolePairSynergy:
        """Calculate synergy for a specific role combination."""
        role_synergy = RolePairSynergy(role1=role1, role2=role2)
        
        total_games = len(matches)
        wins = 0
        total_performance = 0.0
        
        for match in matches:
            p1_participant = match.get_participant_by_puuid(player1_puuid)
            p2_participant = match.get_participant_by_puuid(player2_puuid)
            
            if not p1_participant or not p2_participant:
                continue
            
            # Check win
            if p1_participant.win and p2_participant.win:
                wins += 1
            
            # Calculate combined performance for this role combination
            performance = (p1_participant.kda + p2_participant.kda) / 2
            total_performance += performance
        
        role_synergy.games_together = total_games
        role_synergy.wins_together = wins
        role_synergy.win_rate = wins / total_games if total_games > 0 else 0.0
        role_synergy.avg_combined_performance = total_performance / total_games if total_games > 0 else 0.0
        
        # Calculate role-specific synergy score
        role_synergy.synergy_score = self._calculate_role_synergy_score(role_synergy)
        
        return role_synergy
    
    def _calculate_role_synergy_score(self, role_synergy: RolePairSynergy) -> float:
        """Calculate synergy score for a role combination."""
        if role_synergy.games_together == 0:
            return 0.0
        
        # Base score from win rate
        win_rate_score = (role_synergy.win_rate - 0.5) * 2
        
        # Performance adjustment
        performance_adjustment = 0.0
        if role_synergy.avg_combined_performance > 2.5:
            performance_adjustment = 0.1
        elif role_synergy.avg_combined_performance < 1.5:
            performance_adjustment = -0.1
        
        # Sample size confidence
        confidence = min(role_synergy.games_together / 10.0, 1.0)
        
        final_score = (win_rate_score + performance_adjustment) * confidence
        return max(-1.0, min(1.0, final_score))
    
    def _normalize_role(self, position: str) -> str:
        """Normalize role position to standard format."""
        if not position:
            return "unknown"
        
        position = position.lower()
        role_mapping = {
            "top": "top",
            "jungle": "jungle",
            "middle": "middle",
            "mid": "middle",
            "bottom": "bottom",
            "bot": "bottom",
            "adc": "bottom",
            "support": "support",
            "supp": "support",
            "utility": "support"
        }
        
        return role_mapping.get(position, position)
    
    def _calculate_synergy_confidence(self, sample_size: int) -> float:
        """Calculate confidence level based on sample size."""
        if sample_size == 0:
            return 0.0
        
        # Confidence increases with sample size, asymptotically approaching 1.0
        confidence = 1.0 - (1.0 / (1.0 + sample_size / 10.0))
        return min(confidence, 0.95)  # Cap at 95% confidence   
 
    def _create_player_synergy_matrix(
        self,
        player_puuids: List[str],
        filters: Optional[AnalyticsFilters],
        matrix: SynergyMatrix
    ) -> SynergyMatrix:
        """Create player-to-player synergy matrix."""
        # Set up entity labels
        for puuid in player_puuids:
            matrix.entity_labels[puuid] = self._get_player_name(puuid)
        
        # Calculate synergy for all player pairs
        for i, puuid1 in enumerate(player_puuids):
            for puuid2 in player_puuids[i+1:]:
                try:
                    synergy = self.calculate_player_synergy(puuid1, puuid2, filters)
                    
                    entry = SynergyMatrixEntry(
                        entity1=puuid1,
                        entity2=puuid2,
                        synergy_score=synergy.synergy_score,
                        confidence=synergy.confidence_level,
                        sample_size=synergy.total_games_together,
                        last_updated=datetime.now(),
                        metadata={
                            'win_rate': synergy.win_rate_together,
                            'recent_games': synergy.recent_games_together,
                            'avg_kda': synergy.avg_combined_kda
                        }
                    )
                    
                    matrix.set_synergy(puuid1, puuid2, entry)
                    
                except InsufficientDataError:
                    # Create entry with neutral synergy for insufficient data
                    entry = SynergyMatrixEntry(
                        entity1=puuid1,
                        entity2=puuid2,
                        synergy_score=0.0,
                        confidence=0.0,
                        sample_size=0,
                        last_updated=datetime.now(),
                        metadata={'insufficient_data': True}
                    )
                    matrix.set_synergy(puuid1, puuid2, entry)
        
        return matrix
    
    def _create_role_synergy_matrix(
        self,
        player_puuids: List[str],
        filters: Optional[AnalyticsFilters],
        matrix: SynergyMatrix
    ) -> SynergyMatrix:
        """Create role-to-role synergy matrix."""
        roles = ["top", "jungle", "middle", "bottom", "support"]
        
        # Set up entity labels
        for role in roles:
            matrix.entity_labels[role] = role.title()
        
        # Calculate synergy for all role pairs
        role_synergy_data = defaultdict(list)
        
        # Collect synergy data from all player pairs
        for i, puuid1 in enumerate(player_puuids):
            for puuid2 in player_puuids[i+1:]:
                try:
                    synergy = self.calculate_player_synergy(puuid1, puuid2, filters)
                    
                    # Add role synergies to aggregation
                    for role_pair, role_synergy in synergy.role_synergies.items():
                        role_synergy_data[role_pair].append(role_synergy)
                        
                except InsufficientDataError:
                    continue
        
        # Aggregate role synergies
        for role_pair, synergy_list in role_synergy_data.items():
            if synergy_list:
                avg_synergy = statistics.mean(s.synergy_score for s in synergy_list)
                total_games = sum(s.games_together for s in synergy_list)
                avg_confidence = statistics.mean(
                    self._calculate_synergy_confidence(s.games_together) for s in synergy_list
                )
                
                entry = SynergyMatrixEntry(
                    entity1=role_pair[0],
                    entity2=role_pair[1],
                    synergy_score=avg_synergy,
                    confidence=avg_confidence,
                    sample_size=total_games,
                    last_updated=datetime.now(),
                    metadata={
                        'pair_count': len(synergy_list),
                        'avg_win_rate': statistics.mean(s.win_rate for s in synergy_list)
                    }
                )
                
                matrix.set_synergy(role_pair[0], role_pair[1], entry)
        
        return matrix
    
    def _create_champion_synergy_matrix(
        self,
        player_puuids: List[str],
        filters: Optional[AnalyticsFilters],
        matrix: SynergyMatrix
    ) -> SynergyMatrix:
        """Create champion-to-champion synergy matrix."""
        # This would require champion data analysis
        # For now, return empty matrix with placeholder
        self.logger.warning("Champion synergy matrix not fully implemented")
        return matrix
    
    def _create_trend_points(
        self,
        matches: List[Any],
        player1_puuid: str,
        player2_puuid: str,
        window_days: int
    ) -> List[SynergyTrendPoint]:
        """Create trend points from matches over time windows."""
        if not matches:
            return []
        
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda m: m.game_creation_datetime)
        
        # Create time windows
        start_date = sorted_matches[0].game_creation_datetime
        end_date = sorted_matches[-1].game_creation_datetime
        
        trend_points = []
        current_date = start_date
        
        while current_date < end_date:
            window_end = current_date + timedelta(days=window_days)
            
            # Get matches in this window
            window_matches = [
                m for m in sorted_matches
                if current_date <= m.game_creation_datetime < window_end
            ]
            
            if window_matches:
                # Calculate synergy for this window
                wins = 0
                total_games = len(window_matches)
                
                for match in window_matches:
                    p1_participant = match.get_participant_by_puuid(player1_puuid)
                    p2_participant = match.get_participant_by_puuid(player2_puuid)
                    
                    if (p1_participant and p2_participant and 
                        p1_participant.win and p2_participant.win):
                        wins += 1
                
                win_rate = wins / total_games if total_games > 0 else 0.0
                synergy_score = (win_rate - 0.5) * 2  # Scale to -1 to 1
                confidence = self._calculate_synergy_confidence(total_games)
                
                trend_point = SynergyTrendPoint(
                    timestamp=current_date + timedelta(days=window_days/2),  # Midpoint
                    synergy_score=synergy_score,
                    games_in_period=total_games,
                    win_rate_in_period=win_rate,
                    confidence=confidence
                )
                
                trend_points.append(trend_point)
            
            current_date = window_end
        
        return trend_points
    
    def _calculate_trend_metrics(self, trend_analysis: SynergyTrendAnalysis) -> None:
        """Calculate trend direction, strength, and other metrics."""
        if len(trend_analysis.trend_points) < 2:
            return
        
        # Extract synergy scores and timestamps
        scores = [point.synergy_score for point in trend_analysis.trend_points]
        timestamps = [point.timestamp for point in trend_analysis.trend_points]
        
        # Calculate correlation coefficient (trend strength)
        if len(scores) > 1:
            try:
                trend_analysis.correlation_coefficient = self.statistical_analyzer.calculate_correlation(
                    [t.timestamp() for t in timestamps], scores
                )
            except Exception:
                trend_analysis.correlation_coefficient = 0.0
        
        # Determine trend direction
        if len(scores) >= 3:
            recent_avg = statistics.mean(scores[-3:])
            early_avg = statistics.mean(scores[:3])
            
            if recent_avg > early_avg + 0.1:
                trend_analysis.trend_direction = "improving"
                trend_analysis.trend_strength = min(abs(recent_avg - early_avg), 1.0)
            elif recent_avg < early_avg - 0.1:
                trend_analysis.trend_direction = "declining"
                trend_analysis.trend_strength = min(abs(recent_avg - early_avg), 1.0)
            else:
                trend_analysis.trend_direction = "stable"
                trend_analysis.trend_strength = 0.0
        
        # Calculate trend duration
        if timestamps:
            trend_analysis.trend_duration_days = (timestamps[-1] - timestamps[0]).days
    
    def _identify_key_periods(self, trend_analysis: SynergyTrendAnalysis) -> None:
        """Identify peak, lowest, and most active periods."""
        if not trend_analysis.trend_points:
            return
        
        # Find peak synergy period
        peak_point = max(trend_analysis.trend_points, key=lambda p: p.synergy_score)
        peak_start = peak_point.timestamp - timedelta(days=self.trend_window_days/2)
        peak_end = peak_point.timestamp + timedelta(days=self.trend_window_days/2)
        trend_analysis.peak_synergy_period = (peak_start, peak_end)
        
        # Find lowest synergy period
        lowest_point = min(trend_analysis.trend_points, key=lambda p: p.synergy_score)
        lowest_start = lowest_point.timestamp - timedelta(days=self.trend_window_days/2)
        lowest_end = lowest_point.timestamp + timedelta(days=self.trend_window_days/2)
        trend_analysis.lowest_synergy_period = (lowest_start, lowest_end)
        
        # Find most active period
        most_active_point = max(trend_analysis.trend_points, key=lambda p: p.games_in_period)
        active_start = most_active_point.timestamp - timedelta(days=self.trend_window_days/2)
        active_end = most_active_point.timestamp + timedelta(days=self.trend_window_days/2)
        trend_analysis.most_active_period = (active_start, active_end)
    
    def _generate_possible_teams(
        self,
        available_players: List[str],
        required_roles: List[str],
        constraints: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Generate possible team compositions."""
        # For simplicity, generate a few random valid combinations
        # In a full implementation, this would use more sophisticated algorithms
        
        if len(available_players) < len(required_roles):
            return []
        
        possible_teams = []
        
        # Generate combinations of players for roles
        from itertools import permutations
        
        for player_combination in itertools.combinations(available_players, len(required_roles)):
            for role_assignment in permutations(required_roles):
                team = dict(zip(role_assignment, player_combination))
                possible_teams.append(team)
                
                # Limit number of combinations to avoid explosion
                if len(possible_teams) >= 20:
                    break
            
            if len(possible_teams) >= 20:
                break
        
        return possible_teams
    
    def _evaluate_team_composition(
        self,
        team_composition: Dict[str, str],
        synergy_matrix: SynergyMatrix,
        constraints: Optional[Dict[str, Any]]
    ) -> TeamBuildingRecommendation:
        """Evaluate a team composition and create recommendation."""
        players = list(team_composition.values())
        
        # Calculate team synergy
        total_synergy = 0.0
        synergy_count = 0
        recommended_pairs = []
        
        for i, player1 in enumerate(players):
            for player2 in players[i+1:]:
                synergy_entry = synergy_matrix.get_synergy(player1, player2)
                if synergy_entry:
                    synergy_score = synergy_entry.synergy_score
                    total_synergy += synergy_score
                    synergy_count += 1
                    recommended_pairs.append((player1, player2, synergy_score))
        
        expected_team_synergy = total_synergy / synergy_count if synergy_count > 0 else 0.0
        
        # Calculate confidence
        confidence = 0.0
        if synergy_count > 0:
            confidences = []
            for player1, player2, _ in recommended_pairs:
                synergy_entry = synergy_matrix.get_synergy(player1, player2)
                if synergy_entry:
                    confidences.append(synergy_entry.confidence)
            confidence = statistics.mean(confidences) if confidences else 0.0
        
        # Generate reasoning
        reasoning = []
        if expected_team_synergy > 0.2:
            reasoning.append("High overall team synergy expected")
        elif expected_team_synergy < -0.2:
            reasoning.append("Low team synergy - potential conflicts")
        else:
            reasoning.append("Neutral team synergy - balanced composition")
        
        # Identify risk factors
        risk_factors = []
        if confidence < 0.3:
            risk_factors.append("Low confidence due to insufficient data")
        
        low_synergy_pairs = [pair for pair in recommended_pairs if pair[2] < -0.3]
        if low_synergy_pairs:
            risk_factors.append(f"Potential conflicts between {len(low_synergy_pairs)} player pairs")
        
        return TeamBuildingRecommendation(
            recommended_pairs=recommended_pairs,
            role_assignments=team_composition,
            expected_team_synergy=expected_team_synergy,
            confidence=confidence,
            reasoning=reasoning,
            risk_factors=risk_factors
        )