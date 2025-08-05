"""
Analytics data models for the League of Legends Team Optimizer.

This module contains data structures specifically designed for advanced historical
analytics, performance analysis, and champion recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any, Union
from enum import Enum
import statistics


class AnalyticsError(Exception):
    """Base exception for analytics operations."""
    pass


class InsufficientDataError(AnalyticsError):
    """Raised when insufficient data exists for analysis."""
    
    def __init__(self, required_games: int, available_games: int, context: str = ""):
        self.required_games = required_games
        self.available_games = available_games
        self.context = context
        message = f"Insufficient data: need {required_games}, have {available_games}"
        if context:
            message += f" for {context}"
        super().__init__(message)


class BaselineCalculationError(AnalyticsError):
    """Raised when baseline calculation fails."""
    pass


class StatisticalAnalysisError(AnalyticsError):
    """Raised when statistical analysis fails."""
    pass


class DataValidationError(AnalyticsError):
    """Raised when data validation fails."""
    pass


@dataclass
class DateRange:
    """Represents a date range for filtering analytics."""
    
    start_date: datetime
    end_date: datetime
    
    def __post_init__(self):
        """Validate date range."""
        if self.start_date >= self.end_date:
            raise DataValidationError("Start date must be before end date")
    
    @property
    def duration_days(self) -> int:
        """Get duration in days."""
        return (self.end_date - self.start_date).days
    
    def contains(self, date: datetime) -> bool:
        """Check if date is within range."""
        return self.start_date <= date <= self.end_date


@dataclass
class AnalyticsFilters:
    """Filtering options for analytics queries."""
    
    date_range: Optional[DateRange] = None
    champions: Optional[List[int]] = None
    roles: Optional[List[str]] = None
    queue_types: Optional[List[int]] = None
    teammates: Optional[List[str]] = None
    win_only: Optional[bool] = None
    min_games: int = 1
    
    def __post_init__(self):
        """Validate filters."""
        if self.min_games < 0:
            raise DataValidationError("Minimum games cannot be negative")
        
        if self.roles:
            valid_roles = {"top", "jungle", "middle", "support", "bottom"}
            invalid_roles = set(self.roles) - valid_roles
            if invalid_roles:
                raise DataValidationError(f"Invalid roles: {invalid_roles}")


@dataclass
class PerformanceMetrics:
    """Core performance metrics for analysis."""
    
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    
    # KDA metrics
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    avg_kda: float = 0.0
    
    # Farm metrics
    total_cs: int = 0
    avg_cs_per_min: float = 0.0
    
    # Vision metrics
    total_vision_score: int = 0
    avg_vision_score: float = 0.0
    
    # Damage metrics
    total_damage_to_champions: int = 0
    avg_damage_per_min: float = 0.0
    
    # Gold metrics
    total_gold_earned: int = 0
    avg_gold_per_min: float = 0.0
    
    # Game duration
    total_game_duration: int = 0  # in seconds
    avg_game_duration: float = 0.0  # in minutes
    
    def __post_init__(self):
        """Validate and calculate derived metrics."""
        if self.games_played < 0:
            raise DataValidationError("Games played cannot be negative")
        
        if self.wins + self.losses > self.games_played:
            raise DataValidationError("Wins + losses cannot exceed total games")
        
        # Calculate derived metrics if not provided
        if self.games_played > 0:
            if self.win_rate == 0.0:
                self.win_rate = self.wins / self.games_played
            
            if self.avg_kda == 0.0:
                self.avg_kda = (self.total_kills + self.total_assists) / max(self.total_deaths, 1)
            
            if self.avg_cs_per_min == 0.0 and self.total_game_duration > 0:
                self.avg_cs_per_min = self.total_cs / (self.total_game_duration / 60)
            
            if self.avg_vision_score == 0.0:
                self.avg_vision_score = self.total_vision_score / self.games_played
            
            if self.avg_damage_per_min == 0.0 and self.total_game_duration > 0:
                self.avg_damage_per_min = self.total_damage_to_champions / (self.total_game_duration / 60)
            
            if self.avg_gold_per_min == 0.0 and self.total_game_duration > 0:
                self.avg_gold_per_min = self.total_gold_earned / (self.total_game_duration / 60)
            
            if self.avg_game_duration == 0.0:
                self.avg_game_duration = self.total_game_duration / (self.games_played * 60)


@dataclass
class PerformanceDelta:
    """Represents performance difference from baseline."""
    
    metric_name: str
    baseline_value: float
    actual_value: float
    delta_absolute: float = 0.0
    delta_percentage: float = 0.0
    percentile_rank: float = 0.0
    statistical_significance: float = 0.0
    
    def __post_init__(self):
        """Calculate delta values."""
        self.delta_absolute = self.actual_value - self.baseline_value
        
        if self.baseline_value != 0:
            self.delta_percentage = (self.delta_absolute / self.baseline_value) * 100
        else:
            self.delta_percentage = 0.0 if self.actual_value == 0 else float('inf')
    
    @property
    def is_improvement(self) -> bool:
        """Check if delta represents an improvement."""
        # For most metrics, higher is better
        improvement_metrics = {
            'win_rate', 'avg_kda', 'avg_cs_per_min', 'avg_vision_score',
            'avg_damage_per_min', 'avg_gold_per_min'
        }
        
        if self.metric_name in improvement_metrics:
            return self.delta_absolute > 0
        
        # For some metrics, lower might be better (e.g., deaths)
        if 'death' in self.metric_name.lower():
            return self.delta_absolute < 0
        
        return self.delta_absolute > 0


@dataclass
class ConfidenceInterval:
    """Statistical confidence interval."""
    
    lower_bound: float
    upper_bound: float
    confidence_level: float
    sample_size: int
    
    def __post_init__(self):
        """Validate confidence interval."""
        if not 0 < self.confidence_level < 1:
            raise DataValidationError("Confidence level must be between 0 and 1")
        
        if self.lower_bound > self.upper_bound:
            raise DataValidationError("Lower bound cannot be greater than upper bound")
        
        if self.sample_size <= 0:
            raise DataValidationError("Sample size must be positive")
    
    @property
    def margin_of_error(self) -> float:
        """Calculate margin of error."""
        return (self.upper_bound - self.lower_bound) / 2
    
    @property
    def midpoint(self) -> float:
        """Calculate midpoint of interval."""
        return (self.lower_bound + self.upper_bound) / 2


@dataclass
class SignificanceTest:
    """Statistical significance test result."""
    
    test_type: str
    statistic: float
    p_value: float
    degrees_of_freedom: Optional[int] = None
    effect_size: Optional[float] = None
    
    def __post_init__(self):
        """Validate significance test."""
        if not 0 <= self.p_value <= 1:
            raise DataValidationError("P-value must be between 0 and 1")
    
    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if result is statistically significant."""
        return self.p_value < alpha


@dataclass
class ChampionPerformanceMetrics:
    """Detailed performance metrics for a champion."""
    
    champion_id: int
    champion_name: str
    role: str
    performance: PerformanceMetrics
    performance_vs_baseline: Optional[Dict[str, PerformanceDelta]] = None
    recent_form: Optional['RecentFormMetrics'] = None
    synergy_scores: Dict[str, float] = field(default_factory=dict)  # teammate_puuid -> synergy_score
    confidence_scores: Dict[str, float] = field(default_factory=dict)  # metric -> confidence
    
    def __post_init__(self):
        """Validate champion performance metrics."""
        if self.champion_id <= 0:
            raise DataValidationError("Champion ID must be positive")
        
        if not self.champion_name:
            raise DataValidationError("Champion name cannot be empty")
        
        if not self.role:
            raise DataValidationError("Role cannot be empty")


@dataclass
class RecentFormMetrics:
    """Recent performance form analysis."""
    
    recent_games: int
    recent_win_rate: float
    recent_avg_kda: float
    trend_direction: str  # "improving", "declining", "stable"
    trend_strength: float  # 0.0 to 1.0
    form_score: float  # -1.0 to 1.0, where 1.0 is excellent recent form
    
    def __post_init__(self):
        """Validate recent form metrics."""
        if self.recent_games < 0:
            raise DataValidationError("Recent games cannot be negative")
        
        if not 0 <= self.recent_win_rate <= 1:
            raise DataValidationError("Recent win rate must be between 0 and 1")
        
        if self.recent_avg_kda < 0:
            raise DataValidationError("Recent average KDA cannot be negative")
        
        valid_trends = {"improving", "declining", "stable"}
        if self.trend_direction not in valid_trends:
            raise DataValidationError(f"Trend direction must be one of: {valid_trends}")
        
        if not 0 <= self.trend_strength <= 1:
            raise DataValidationError("Trend strength must be between 0 and 1")
        
        if not -1 <= self.form_score <= 1:
            raise DataValidationError("Form score must be between -1 and 1")


@dataclass
class PlayerRoleAssignment:
    """Player assignment within a team composition."""
    
    puuid: str
    player_name: str
    role: str
    champion_id: int
    champion_name: str
    
    def __post_init__(self):
        """Validate player role assignment."""
        if not self.puuid:
            raise DataValidationError("PUUID cannot be empty")
        
        if not self.player_name:
            raise DataValidationError("Player name cannot be empty")
        
        if not self.role:
            raise DataValidationError("Role cannot be empty")
        
        if self.champion_id <= 0:
            raise DataValidationError("Champion ID must be positive")
        
        if not self.champion_name:
            raise DataValidationError("Champion name cannot be empty")


@dataclass
class TeamComposition:
    """Represents a team composition for analysis."""
    
    players: Dict[str, PlayerRoleAssignment]  # role -> PlayerRoleAssignment
    composition_id: str = ""
    historical_matches: List[str] = field(default_factory=list)  # match_ids
    
    def __post_init__(self):
        """Validate and generate composition ID."""
        if not self.players:
            raise DataValidationError("Team composition must have at least one player")
        
        # Validate roles
        valid_roles = {"top", "jungle", "middle", "support", "bottom"}
        invalid_roles = set(self.players.keys()) - valid_roles
        if invalid_roles:
            raise DataValidationError(f"Invalid roles in composition: {invalid_roles}")
        
        # Generate composition ID if not provided
        if not self.composition_id:
            role_assignments = []
            for role in sorted(self.players.keys()):
                assignment = self.players[role]
                role_assignments.append(f"{role}:{assignment.puuid}:{assignment.champion_id}")
            self.composition_id = "|".join(role_assignments)
    
    @property
    def player_count(self) -> int:
        """Get number of players in composition."""
        return len(self.players)
    
    def get_player_puuids(self) -> List[str]:
        """Get list of all player PUUIDs."""
        return [assignment.puuid for assignment in self.players.values()]
    
    def get_champion_ids(self) -> List[int]:
        """Get list of all champion IDs."""
        return [assignment.champion_id for assignment in self.players.values()]


@dataclass
class SynergyEffects:
    """Synergy effects analysis for team composition."""
    
    overall_synergy: float  # -1.0 to 1.0
    role_pair_synergies: Dict[Tuple[str, str], float] = field(default_factory=dict)
    champion_synergies: Dict[Tuple[int, int], float] = field(default_factory=dict)
    player_synergies: Dict[Tuple[str, str], float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate synergy effects."""
        if not -1 <= self.overall_synergy <= 1:
            raise DataValidationError("Overall synergy must be between -1 and 1")
        
        # Validate individual synergy scores
        for synergy_dict in [self.role_pair_synergies, self.champion_synergies, self.player_synergies]:
            for key, value in synergy_dict.items():
                if not -1 <= value <= 1:
                    raise DataValidationError(f"Synergy score for {key} must be between -1 and 1")


@dataclass
class CompositionPerformance:
    """Performance analysis for a team composition."""
    
    composition: TeamComposition
    total_games: int
    performance: PerformanceMetrics
    performance_vs_individual_baselines: Dict[str, Dict[str, PerformanceDelta]] = field(default_factory=dict)
    synergy_effects: Optional[SynergyEffects] = None
    statistical_significance: Optional[SignificanceTest] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    
    def __post_init__(self):
        """Validate composition performance."""
        if self.total_games < 0:
            raise DataValidationError("Total games cannot be negative")
        
        if self.total_games != self.performance.games_played:
            raise DataValidationError("Total games must match performance games played")


@dataclass
class RecommendationReasoning:
    """Explanation for champion recommendation."""
    
    primary_factors: List[str]
    performance_summary: str
    synergy_summary: str
    confidence_explanation: str
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate recommendation reasoning."""
        if not self.primary_factors:
            raise DataValidationError("Primary factors cannot be empty")
        
        if not self.performance_summary:
            raise DataValidationError("Performance summary cannot be empty")
        
        if not self.synergy_summary:
            raise DataValidationError("Synergy summary cannot be empty")
        
        if not self.confidence_explanation:
            raise DataValidationError("Confidence explanation cannot be empty")


@dataclass
class PerformanceProjection:
    """Projected performance for a champion recommendation."""
    
    expected_win_rate: float
    expected_kda: float
    expected_cs_per_min: float
    expected_vision_score: float
    confidence_interval: ConfidenceInterval
    projection_basis: str  # "historical", "similar_champions", "baseline_adjusted"
    
    def __post_init__(self):
        """Validate performance projection."""
        if not 0 <= self.expected_win_rate <= 1:
            raise DataValidationError("Expected win rate must be between 0 and 1")
        
        if self.expected_kda < 0:
            raise DataValidationError("Expected KDA cannot be negative")
        
        if self.expected_cs_per_min < 0:
            raise DataValidationError("Expected CS per minute cannot be negative")
        
        if self.expected_vision_score < 0:
            raise DataValidationError("Expected vision score cannot be negative")
        
        valid_bases = {"historical", "similar_champions", "baseline_adjusted"}
        if self.projection_basis not in valid_bases:
            raise DataValidationError(f"Projection basis must be one of: {valid_bases}")


@dataclass
class SynergyAnalysis:
    """Champion synergy analysis."""
    
    team_synergy_score: float
    individual_synergies: Dict[int, float]  # champion_id -> synergy_score
    synergy_explanation: str
    historical_data_points: int
    
    def __post_init__(self):
        """Validate synergy analysis."""
        if not -1 <= self.team_synergy_score <= 1:
            raise DataValidationError("Team synergy score must be between -1 and 1")
        
        for champion_id, score in self.individual_synergies.items():
            if not -1 <= score <= 1:
                raise DataValidationError(f"Individual synergy score for champion {champion_id} must be between -1 and 1")
        
        if self.historical_data_points < 0:
            raise DataValidationError("Historical data points cannot be negative")
        
        if not self.synergy_explanation:
            raise DataValidationError("Synergy explanation cannot be empty")


@dataclass
class ChampionRecommendation:
    """Enhanced champion recommendation with historical context."""
    
    champion_id: int
    champion_name: str
    role: str
    recommendation_score: float
    confidence: float
    historical_performance: Optional[ChampionPerformanceMetrics] = None
    expected_performance: Optional[PerformanceProjection] = None
    synergy_analysis: Optional[SynergyAnalysis] = None
    reasoning: Optional[RecommendationReasoning] = None
    
    def __post_init__(self):
        """Validate champion recommendation."""
        if self.champion_id <= 0:
            raise DataValidationError("Champion ID must be positive")
        
        if not self.champion_name:
            raise DataValidationError("Champion name cannot be empty")
        
        if not self.role:
            raise DataValidationError("Role cannot be empty")
        
        if not 0 <= self.recommendation_score <= 1:
            raise DataValidationError("Recommendation score must be between 0 and 1")
        
        if not 0 <= self.confidence <= 1:
            raise DataValidationError("Confidence must be between 0 and 1")


@dataclass
class TeamContext:
    """Current team composition context for recommendations."""
    
    existing_picks: Dict[str, PlayerRoleAssignment]  # role -> assignment
    target_role: str
    target_player_puuid: str
    available_champions: Optional[List[int]] = None
    banned_champions: Optional[List[int]] = None
    enemy_composition: Optional[Dict[str, int]] = None  # role -> champion_id
    
    def __post_init__(self):
        """Validate team context."""
        if not self.target_role:
            raise DataValidationError("Target role cannot be empty")
        
        if not self.target_player_puuid:
            raise DataValidationError("Target player PUUID cannot be empty")
        
        valid_roles = {"top", "jungle", "middle", "support", "bottom"}
        if self.target_role not in valid_roles:
            raise DataValidationError(f"Target role must be one of: {valid_roles}")
        
        # Validate existing picks don't include target role
        if self.target_role in self.existing_picks:
            raise DataValidationError("Target role cannot already be assigned")


@dataclass
class PlayerAnalytics:
    """Comprehensive analytics for a player."""
    
    puuid: str
    player_name: str
    analysis_period: DateRange
    overall_performance: PerformanceMetrics
    role_performance: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    champion_performance: Dict[int, ChampionPerformanceMetrics] = field(default_factory=dict)
    trend_analysis: Optional['TrendAnalysis'] = None
    comparative_rankings: Optional['ComparativeRankings'] = None
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate player analytics."""
        if not self.puuid:
            raise DataValidationError("PUUID cannot be empty")
        
        if not self.player_name:
            raise DataValidationError("Player name cannot be empty")


@dataclass
class TimeSeriesPoint:
    """A single point in a time series for trend analysis."""
    
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TrendAnalysis:
    """Performance trend analysis over time."""
    
    trend_direction: str  # "improving", "declining", "stable"
    trend_strength: float  # 0.0 to 1.0
    trend_duration_days: int
    key_metrics_trends: Dict[str, float] = field(default_factory=dict)  # metric -> trend_slope
    inflection_points: List[datetime] = field(default_factory=list)
    seasonal_patterns: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate trend analysis."""
        valid_directions = {"improving", "declining", "stable"}
        if self.trend_direction not in valid_directions:
            raise DataValidationError(f"Trend direction must be one of: {valid_directions}")
        
        if not 0 <= self.trend_strength <= 1:
            raise DataValidationError("Trend strength must be between 0 and 1")
        
        if self.trend_duration_days < 0:
            raise DataValidationError("Trend duration cannot be negative")


@dataclass
class ComparativeRankings:
    """Comparative rankings against other players."""
    
    overall_percentile: float
    role_percentiles: Dict[str, float] = field(default_factory=dict)
    champion_percentiles: Dict[int, float] = field(default_factory=dict)
    peer_group_size: int = 0
    ranking_basis: str = "all_players"  # "all_players", "similar_skill", "team_members"
    
    def __post_init__(self):
        """Validate comparative rankings."""
        if not 0 <= self.overall_percentile <= 100:
            raise DataValidationError("Overall percentile must be between 0 and 100")
        
        for role, percentile in self.role_percentiles.items():
            if not 0 <= percentile <= 100:
                raise DataValidationError(f"Role percentile for {role} must be between 0 and 100")
        
        for champion_id, percentile in self.champion_percentiles.items():
            if not 0 <= percentile <= 100:
                raise DataValidationError(f"Champion percentile for {champion_id} must be between 0 and 100")
        
        if self.peer_group_size < 0:
            raise DataValidationError("Peer group size cannot be negative")
        
        valid_bases = {"all_players", "similar_skill", "team_members"}
        if self.ranking_basis not in valid_bases:
            raise DataValidationError(f"Ranking basis must be one of: {valid_bases}")