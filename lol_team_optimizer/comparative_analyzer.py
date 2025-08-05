"""
Comparative Analysis and Ranking Systems for the League of Legends Team Optimizer.

This module provides comprehensive comparative analysis capabilities including
multi-player comparisons, percentile rankings, peer group analysis, and
statistical validation of performance differences.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from .models import Match, MatchParticipant
from .analytics_models import (
    AnalyticsFilters, PlayerAnalytics, PerformanceMetrics, PerformanceDelta,
    DateRange, ComparativeRankings, AnalyticsError, InsufficientDataError,
    SignificanceTest, ConfidenceInterval
)
from .baseline_manager import BaselineManager, BaselineContext
from .statistical_analyzer import StatisticalAnalyzer
from .config import Config


class RankingBasis(Enum):
    """Basis for ranking calculations."""
    ALL_PLAYERS = "all_players"
    SIMILAR_SKILL = "similar_skill"
    TEAM_MEMBERS = "team_members"
    ROLE_SPECIFIC = "role_specific"


class SkillTier(Enum):
    """Skill tier classifications for peer grouping."""
    IRON = "iron"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    CHALLENGER = "challenger"


@dataclass
class PlayerComparison:
    """Comparison between two players."""
    
    player1_puuid: str
    player2_puuid: str
    player1_name: str
    player2_name: str
    metric: str
    player1_value: float
    player2_value: float
    difference: float
    percentage_difference: float
    statistical_significance: Optional[SignificanceTest] = None
    confidence_interval: Optional[ConfidenceInterval] = None
    sample_sizes: Tuple[int, int] = (0, 0)
    
    @property
    def is_significant(self) -> bool:
        """Check if difference is statistically significant."""
        return (self.statistical_significance is not None and 
                self.statistical_significance.is_significant())
    
    @property
    def better_player(self) -> str:
        """Get PUUID of better performing player."""
        return self.player1_puuid if self.player1_value > self.player2_value else self.player2_puuid


@dataclass
class MultiPlayerComparison:
    """Comparison across multiple players for a specific metric."""
    
    metric: str
    players: List[str]  # PUUIDs
    player_names: Dict[str, str]  # puuid -> name
    values: Dict[str, float]  # puuid -> metric_value
    rankings: Dict[str, int]  # puuid -> rank (1-based)
    percentiles: Dict[str, float]  # puuid -> percentile
    statistical_tests: Dict[Tuple[str, str], SignificanceTest] = field(default_factory=dict)
    sample_sizes: Dict[str, int] = field(default_factory=dict)
    analysis_period: Optional[DateRange] = None
    
    def get_top_performers(self, n: int = 3) -> List[str]:
        """Get top N performing players."""
        sorted_players = sorted(self.players, key=lambda p: self.rankings[p])
        return sorted_players[:min(n, len(sorted_players))]
    
    def get_bottom_performers(self, n: int = 3) -> List[str]:
        """Get bottom N performing players."""
        sorted_players = sorted(self.players, key=lambda p: self.rankings[p], reverse=True)
        return sorted_players[:min(n, len(sorted_players))]


@dataclass
class PeerGroupAnalysis:
    """Analysis within a peer group of similar skill level."""
    
    target_player: str
    peer_group: List[str]  # PUUIDs of peer players
    skill_tier: SkillTier
    peer_group_size: int
    target_rankings: Dict[str, int]  # metric -> rank within peer group
    target_percentiles: Dict[str, float]  # metric -> percentile within peer group
    peer_averages: Dict[str, float]  # metric -> peer group average
    performance_vs_peers: Dict[str, PerformanceDelta]  # metric -> delta vs peer average
    strengths: List[str]  # metrics where player excels vs peers
    weaknesses: List[str]  # metrics where player underperforms vs peers


@dataclass
class RoleSpecificRanking:
    """Role-specific ranking analysis."""
    
    role: str
    player_puuid: str
    player_name: str
    role_player_pool: List[str]  # PUUIDs of players who play this role
    rankings: Dict[str, int]  # metric -> rank within role
    percentiles: Dict[str, float]  # metric -> percentile within role
    role_averages: Dict[str, float]  # metric -> role average
    performance_vs_role: Dict[str, PerformanceDelta]  # metric -> delta vs role average
    top_performers: Dict[str, List[str]]  # metric -> list of top performer PUUIDs
    total_role_players: int


@dataclass
class ChampionSpecificRanking:
    """Champion-specific ranking analysis."""
    
    champion_id: int
    champion_name: str
    player_puuid: str
    player_name: str
    champion_player_pool: List[str]  # PUUIDs of players who play this champion
    rankings: Dict[str, int]  # metric -> rank within champion players
    percentiles: Dict[str, float]  # metric -> percentile within champion players
    champion_averages: Dict[str, float]  # metric -> champion average
    performance_vs_champion: Dict[str, PerformanceDelta]  # metric -> delta vs champion average
    mastery_level: str  # "novice", "competent", "expert", "master"
    total_champion_players: int


class ComparativeAnalyzer:
    """
    Comprehensive comparative analysis and ranking system.
    
    Provides multi-player comparisons, percentile rankings, peer group analysis,
    and statistical validation of performance differences.
    """
    
    def __init__(self, config: Config, match_manager, baseline_manager: BaselineManager):
        """
        Initialize the comparative analyzer.
        
        Args:
            config: Configuration object
            match_manager: MatchManager instance for data access
            baseline_manager: BaselineManager for baseline calculations
        """
        self.config = config
        self.match_manager = match_manager
        self.baseline_manager = baseline_manager
        self.statistical_analyzer = StatisticalAnalyzer()
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.min_games_for_comparison = 10
        self.min_peer_group_size = 5
        self.significance_level = 0.05
        
        # Standard metrics for comparison
        self.comparison_metrics = [
            "win_rate", "avg_kda", "avg_cs_per_min", "avg_vision_score",
            "avg_damage_per_min", "avg_gold_per_min"
        ]
    
    def compare_players(
        self,
        player_puuids: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> Dict[str, MultiPlayerComparison]:
        """
        Perform comprehensive multi-player comparative analysis.
        
        Args:
            player_puuids: List of player PUUIDs to compare
            metrics: List of metrics to compare (defaults to standard metrics)
            filters: Optional filters to apply to analysis
            
        Returns:
            Dictionary mapping metric names to MultiPlayerComparison objects
            
        Raises:
            InsufficientDataError: If not enough data for comparison
            AnalyticsError: If comparison fails
        """
        try:
            if len(player_puuids) < 2:
                raise AnalyticsError("Need at least 2 players for comparison")
            
            if metrics is None:
                metrics = self.comparison_metrics
            
            self.logger.info(f"Comparing {len(player_puuids)} players across {len(metrics)} metrics")
            
            # Get performance data for all players
            player_data = {}
            player_names = {}
            
            for puuid in player_puuids:
                try:
                    matches = self._get_filtered_matches(puuid, filters)
                    
                    if len(matches) < self.min_games_for_comparison:
                        self.logger.warning(f"Insufficient data for player {puuid}: {len(matches)} games")
                        continue
                    
                    performance = self._calculate_performance_metrics(matches)
                    player_data[puuid] = {
                        'performance': performance,
                        'matches': matches,
                        'sample_size': len(matches)
                    }
                    
                    # Get player name from first match
                    player_names[puuid] = matches[0][1].summoner_name if matches else f"Player_{puuid[:8]}"
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get data for player {puuid}: {e}")
            
            if len(player_data) < 2:
                raise InsufficientDataError(
                    required_games=self.min_games_for_comparison,
                    available_games=len(player_data),
                    context="multi-player comparison"
                )
            
            # Determine analysis period
            if filters and filters.date_range:
                analysis_period = filters.date_range
            else:
                all_dates = []
                for data in player_data.values():
                    all_dates.extend([match.game_creation_datetime for match, _ in data['matches']])
                
                if all_dates:
                    analysis_period = DateRange(
                        start_date=min(all_dates),
                        end_date=max(all_dates)
                    )
                else:
                    analysis_period = None
            
            # Perform comparison for each metric
            comparisons = {}
            valid_puuids = list(player_data.keys())
            
            for metric in metrics:
                try:
                    comparison = self._compare_metric_across_players(
                        valid_puuids, player_data, player_names, metric, analysis_period
                    )
                    comparisons[metric] = comparison
                    
                except Exception as e:
                    self.logger.warning(f"Failed to compare metric {metric}: {e}")
            
            if not comparisons:
                raise AnalyticsError("No metrics could be compared successfully")
            
            self.logger.info(f"Successfully compared {len(valid_puuids)} players across {len(comparisons)} metrics")
            return comparisons
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to compare players: {e}")
    
    def calculate_percentile_rankings(
        self,
        target_player: str,
        comparison_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> ComparativeRankings:
        """
        Calculate percentile rankings for a player against a comparison pool.
        
        Args:
            target_player: PUUID of target player
            comparison_pool: List of player PUUIDs to compare against
            metrics: List of metrics to rank (defaults to standard metrics)
            filters: Optional filters to apply
            
        Returns:
            ComparativeRankings object
            
        Raises:
            InsufficientDataError: If not enough data for ranking
            AnalyticsError: If ranking calculation fails
        """
        try:
            if metrics is None:
                metrics = self.comparison_metrics
            
            if target_player not in comparison_pool:
                comparison_pool = [target_player] + comparison_pool
            
            self.logger.info(f"Calculating percentile rankings for {target_player} against {len(comparison_pool)} players")
            
            # Get performance data for all players
            player_performances = {}
            
            for puuid in comparison_pool:
                try:
                    matches = self._get_filtered_matches(puuid, filters)
                    
                    if len(matches) >= self.min_games_for_comparison:
                        performance = self._calculate_performance_metrics(matches)
                        player_performances[puuid] = performance
                    else:
                        self.logger.warning(f"Insufficient data for player {puuid} in ranking")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get performance data for {puuid}: {e}")
            
            if target_player not in player_performances:
                raise InsufficientDataError(
                    required_games=self.min_games_for_comparison,
                    available_games=0,
                    context=f"percentile ranking for {target_player}"
                )
            
            if len(player_performances) < self.min_peer_group_size:
                raise InsufficientDataError(
                    required_games=self.min_peer_group_size,
                    available_games=len(player_performances),
                    context="percentile ranking comparison pool"
                )
            
            # Calculate overall percentile
            overall_scores = []
            target_overall_score = 0
            
            for puuid, performance in player_performances.items():
                # Calculate composite score (weighted average of key metrics)
                score = (
                    performance.win_rate * 0.3 +
                    min(performance.avg_kda / 5.0, 1.0) * 0.25 +  # Cap KDA contribution
                    min(performance.avg_cs_per_min / 10.0, 1.0) * 0.2 +  # Cap CS contribution
                    min(performance.avg_vision_score / 100.0, 1.0) * 0.15 +  # Cap vision contribution
                    min(performance.avg_damage_per_min / 1000.0, 1.0) * 0.1  # Cap damage contribution
                )
                
                overall_scores.append(score)
                if puuid == target_player:
                    target_overall_score = score
            
            overall_percentile = self._calculate_percentile(target_overall_score, overall_scores)
            
            # Calculate role-specific percentiles
            role_percentiles = {}
            target_performance = player_performances[target_player]
            
            # For role-specific analysis, we'd need role information
            # For now, we'll calculate percentiles for key metrics
            for metric in metrics:
                try:
                    metric_values = []
                    target_value = getattr(target_performance, metric, 0)
                    
                    for performance in player_performances.values():
                        value = getattr(performance, metric, 0)
                        metric_values.append(value)
                    
                    percentile = self._calculate_percentile(target_value, metric_values)
                    role_percentiles[metric] = percentile
                    
                except AttributeError:
                    self.logger.warning(f"Metric {metric} not found in performance data")
            
            # Calculate champion-specific percentiles (simplified)
            champion_percentiles = {}
            
            rankings = ComparativeRankings(
                overall_percentile=overall_percentile,
                role_percentiles=role_percentiles,
                champion_percentiles=champion_percentiles,
                peer_group_size=len(player_performances),
                ranking_basis=RankingBasis.ALL_PLAYERS.value
            )
            
            self.logger.info(f"Calculated percentile rankings for {target_player}: {overall_percentile:.1f}th percentile")
            return rankings
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate percentile rankings: {e}")
    
    def analyze_peer_group(
        self,
        target_player: str,
        skill_tier: SkillTier,
        peer_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> PeerGroupAnalysis:
        """
        Analyze player performance within a peer group of similar skill level.
        
        Args:
            target_player: PUUID of target player
            skill_tier: Skill tier for peer grouping
            peer_pool: List of potential peer player PUUIDs
            metrics: List of metrics to analyze
            filters: Optional filters to apply
            
        Returns:
            PeerGroupAnalysis object
            
        Raises:
            InsufficientDataError: If not enough peer data
            AnalyticsError: If analysis fails
        """
        try:
            if metrics is None:
                metrics = self.comparison_metrics
            
            self.logger.info(f"Analyzing peer group for {target_player} in {skill_tier.value} tier")
            
            # Get performance data for target player and peers
            peer_performances = {}
            target_performance = None
            
            # Include target player in analysis
            all_players = [target_player] + [p for p in peer_pool if p != target_player]
            
            for puuid in all_players:
                try:
                    matches = self._get_filtered_matches(puuid, filters)
                    
                    if len(matches) >= self.min_games_for_comparison:
                        performance = self._calculate_performance_metrics(matches)
                        peer_performances[puuid] = performance
                        
                        if puuid == target_player:
                            target_performance = performance
                    else:
                        self.logger.warning(f"Insufficient data for peer {puuid}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get data for peer {puuid}: {e}")
            
            if target_performance is None:
                raise InsufficientDataError(
                    required_games=self.min_games_for_comparison,
                    available_games=0,
                    context=f"peer group analysis for {target_player}"
                )
            
            # Remove target player from peer group for comparison
            peer_performances.pop(target_player, None)
            
            if len(peer_performances) < self.min_peer_group_size:
                raise InsufficientDataError(
                    required_games=self.min_peer_group_size,
                    available_games=len(peer_performances),
                    context="peer group analysis"
                )
            
            # Calculate peer group statistics
            peer_averages = {}
            target_rankings = {}
            target_percentiles = {}
            performance_vs_peers = {}
            
            for metric in metrics:
                try:
                    # Get peer values for this metric
                    peer_values = []
                    for performance in peer_performances.values():
                        value = getattr(performance, metric, 0)
                        peer_values.append(value)
                    
                    if peer_values:
                        peer_average = statistics.mean(peer_values)
                        peer_averages[metric] = peer_average
                        
                        # Get target value
                        target_value = getattr(target_performance, metric, 0)
                        
                        # Calculate ranking within peer group
                        all_values = peer_values + [target_value]
                        sorted_values = sorted(all_values, reverse=True)  # Higher is better for most metrics
                        rank = sorted_values.index(target_value) + 1
                        target_rankings[metric] = rank
                        
                        # Calculate percentile
                        percentile = self._calculate_percentile(target_value, peer_values)
                        target_percentiles[metric] = percentile
                        
                        # Calculate performance delta vs peers
                        delta = PerformanceDelta(
                            metric_name=metric,
                            baseline_value=peer_average,
                            actual_value=target_value
                        )
                        performance_vs_peers[metric] = delta
                        
                except AttributeError:
                    self.logger.warning(f"Metric {metric} not found in performance data")
            
            # Identify strengths and weaknesses
            strengths = []
            weaknesses = []
            
            for metric, percentile in target_percentiles.items():
                if percentile >= 75:  # Top quartile
                    strengths.append(metric)
                elif percentile <= 25:  # Bottom quartile
                    weaknesses.append(metric)
            
            analysis = PeerGroupAnalysis(
                target_player=target_player,
                peer_group=list(peer_performances.keys()),
                skill_tier=skill_tier,
                peer_group_size=len(peer_performances),
                target_rankings=target_rankings,
                target_percentiles=target_percentiles,
                peer_averages=peer_averages,
                performance_vs_peers=performance_vs_peers,
                strengths=strengths,
                weaknesses=weaknesses
            )
            
            self.logger.info(f"Analyzed peer group for {target_player}: {len(strengths)} strengths, {len(weaknesses)} weaknesses")
            return analysis
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze peer group: {e}")
    
    def calculate_role_specific_rankings(
        self,
        player_puuid: str,
        role: str,
        role_player_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> RoleSpecificRanking:
        """
        Calculate role-specific rankings for a player.
        
        Args:
            player_puuid: PUUID of target player
            role: Role to analyze
            role_player_pool: List of player PUUIDs who play this role
            metrics: List of metrics to rank
            filters: Optional filters to apply
            
        Returns:
            RoleSpecificRanking object
            
        Raises:
            InsufficientDataError: If not enough role data
            AnalyticsError: If ranking calculation fails
        """
        try:
            if metrics is None:
                metrics = self.comparison_metrics
            
            self.logger.info(f"Calculating role-specific rankings for {player_puuid} in {role}")
            
            # Add role filter
            role_filters = filters or AnalyticsFilters()
            role_filters.roles = [role]
            
            # Get performance data for all role players
            role_performances = {}
            player_name = f"Player_{player_puuid[:8]}"
            
            for puuid in role_player_pool:
                try:
                    matches = self._get_filtered_matches(puuid, role_filters)
                    
                    if len(matches) >= self.min_games_for_comparison:
                        performance = self._calculate_performance_metrics(matches)
                        role_performances[puuid] = performance
                        
                        if puuid == player_puuid:
                            player_name = matches[0][1].summoner_name if matches else player_name
                    else:
                        self.logger.warning(f"Insufficient {role} data for player {puuid}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get {role} data for {puuid}: {e}")
            
            if player_puuid not in role_performances:
                raise InsufficientDataError(
                    required_games=self.min_games_for_comparison,
                    available_games=0,
                    context=f"role-specific ranking for {player_puuid} in {role}"
                )
            
            if len(role_performances) < self.min_peer_group_size:
                raise InsufficientDataError(
                    required_games=self.min_peer_group_size,
                    available_games=len(role_performances),
                    context=f"role-specific ranking pool for {role}"
                )
            
            # Calculate role statistics
            role_averages = {}
            rankings = {}
            percentiles = {}
            performance_vs_role = {}
            top_performers = {}
            
            target_performance = role_performances[player_puuid]
            
            for metric in metrics:
                try:
                    # Get all values for this metric
                    metric_values = []
                    player_metric_map = {}
                    
                    for puuid, performance in role_performances.items():
                        value = getattr(performance, metric, 0)
                        metric_values.append(value)
                        player_metric_map[puuid] = value
                    
                    if metric_values:
                        role_average = statistics.mean(metric_values)
                        role_averages[metric] = role_average
                        
                        # Get target value
                        target_value = getattr(target_performance, metric, 0)
                        
                        # Calculate ranking
                        sorted_values = sorted(metric_values, reverse=True)
                        rank = sorted_values.index(target_value) + 1
                        rankings[metric] = rank
                        
                        # Calculate percentile
                        percentile = self._calculate_percentile(target_value, metric_values)
                        percentiles[metric] = percentile
                        
                        # Calculate performance delta vs role average
                        delta = PerformanceDelta(
                            metric_name=metric,
                            baseline_value=role_average,
                            actual_value=target_value
                        )
                        performance_vs_role[metric] = delta
                        
                        # Identify top performers for this metric
                        sorted_players = sorted(
                            player_metric_map.items(),
                            key=lambda x: x[1],
                            reverse=True
                        )
                        top_performers[metric] = [puuid for puuid, _ in sorted_players[:3]]
                        
                except AttributeError:
                    self.logger.warning(f"Metric {metric} not found in performance data")
            
            ranking = RoleSpecificRanking(
                role=role,
                player_puuid=player_puuid,
                player_name=player_name,
                role_player_pool=list(role_performances.keys()),
                rankings=rankings,
                percentiles=percentiles,
                role_averages=role_averages,
                performance_vs_role=performance_vs_role,
                top_performers=top_performers,
                total_role_players=len(role_performances)
            )
            
            self.logger.info(f"Calculated role-specific rankings for {player_puuid} in {role}")
            return ranking
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate role-specific rankings: {e}")
    
    def calculate_champion_specific_rankings(
        self,
        player_puuid: str,
        champion_id: int,
        champion_player_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> ChampionSpecificRanking:
        """
        Calculate champion-specific rankings for a player.
        
        Args:
            player_puuid: PUUID of target player
            champion_id: Champion ID to analyze
            champion_player_pool: List of player PUUIDs who play this champion
            metrics: List of metrics to rank
            filters: Optional filters to apply
            
        Returns:
            ChampionSpecificRanking object
            
        Raises:
            InsufficientDataError: If not enough champion data
            AnalyticsError: If ranking calculation fails
        """
        try:
            if metrics is None:
                metrics = self.comparison_metrics
            
            self.logger.info(f"Calculating champion-specific rankings for {player_puuid} on champion {champion_id}")
            
            # Add champion filter
            champion_filters = filters or AnalyticsFilters()
            champion_filters.champions = [champion_id]
            
            # Get performance data for all champion players
            champion_performances = {}
            player_name = f"Player_{player_puuid[:8]}"
            champion_name = f"Champion_{champion_id}"
            
            for puuid in champion_player_pool:
                try:
                    matches = self._get_filtered_matches(puuid, champion_filters)
                    
                    if len(matches) >= self.min_games_for_comparison:
                        performance = self._calculate_performance_metrics(matches)
                        champion_performances[puuid] = {
                            'performance': performance,
                            'games': len(matches)
                        }
                        
                        if puuid == player_puuid:
                            player_name = matches[0][1].summoner_name if matches else player_name
                            champion_name = matches[0][1].champion_name if matches else champion_name
                    else:
                        self.logger.warning(f"Insufficient champion {champion_id} data for player {puuid}")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get champion {champion_id} data for {puuid}: {e}")
            
            if player_puuid not in champion_performances:
                raise InsufficientDataError(
                    required_games=self.min_games_for_comparison,
                    available_games=0,
                    context=f"champion-specific ranking for {player_puuid} on {champion_id}"
                )
            
            if len(champion_performances) < self.min_peer_group_size:
                raise InsufficientDataError(
                    required_games=self.min_peer_group_size,
                    available_games=len(champion_performances),
                    context=f"champion-specific ranking pool for {champion_id}"
                )
            
            # Calculate champion statistics
            champion_averages = {}
            rankings = {}
            percentiles = {}
            performance_vs_champion = {}
            
            target_data = champion_performances[player_puuid]
            target_performance = target_data['performance']
            target_games = target_data['games']
            
            for metric in metrics:
                try:
                    # Get all values for this metric
                    metric_values = []
                    
                    for data in champion_performances.values():
                        value = getattr(data['performance'], metric, 0)
                        metric_values.append(value)
                    
                    if metric_values:
                        champion_average = statistics.mean(metric_values)
                        champion_averages[metric] = champion_average
                        
                        # Get target value
                        target_value = getattr(target_performance, metric, 0)
                        
                        # Calculate ranking
                        sorted_values = sorted(metric_values, reverse=True)
                        rank = sorted_values.index(target_value) + 1
                        rankings[metric] = rank
                        
                        # Calculate percentile
                        percentile = self._calculate_percentile(target_value, metric_values)
                        percentiles[metric] = percentile
                        
                        # Calculate performance delta vs champion average
                        delta = PerformanceDelta(
                            metric_name=metric,
                            baseline_value=champion_average,
                            actual_value=target_value
                        )
                        performance_vs_champion[metric] = delta
                        
                except AttributeError:
                    self.logger.warning(f"Metric {metric} not found in performance data")
            
            # Determine mastery level based on games played and performance
            mastery_level = self._determine_mastery_level(target_games, percentiles)
            
            ranking = ChampionSpecificRanking(
                champion_id=champion_id,
                champion_name=champion_name,
                player_puuid=player_puuid,
                player_name=player_name,
                champion_player_pool=list(champion_performances.keys()),
                rankings=rankings,
                percentiles=percentiles,
                champion_averages=champion_averages,
                performance_vs_champion=performance_vs_champion,
                mastery_level=mastery_level,
                total_champion_players=len(champion_performances)
            )
            
            self.logger.info(f"Calculated champion-specific rankings for {player_puuid} on {champion_name}")
            return ranking
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate champion-specific rankings: {e}")
    
    def prepare_comparative_visualization_data(
        self,
        comparisons: Dict[str, MultiPlayerComparison],
        format_type: str = "radar_chart"
    ) -> Dict[str, Any]:
        """
        Prepare comparative analysis data for visualization.
        
        Args:
            comparisons: Dictionary of metric comparisons
            format_type: Type of visualization format ("radar_chart", "bar_chart", "heatmap")
            
        Returns:
            Dictionary containing visualization-ready data
            
        Raises:
            AnalyticsError: If data preparation fails
        """
        try:
            self.logger.info(f"Preparing comparative visualization data for {format_type}")
            
            if not comparisons:
                raise AnalyticsError("No comparison data provided")
            
            # Get all players from first comparison
            first_comparison = next(iter(comparisons.values()))
            players = first_comparison.players
            player_names = first_comparison.player_names
            
            if format_type == "radar_chart":
                return self._prepare_radar_chart_data(comparisons, players, player_names)
            elif format_type == "bar_chart":
                return self._prepare_bar_chart_data(comparisons, players, player_names)
            elif format_type == "heatmap":
                return self._prepare_heatmap_data(comparisons, players, player_names)
            else:
                raise AnalyticsError(f"Unknown visualization format: {format_type}")
                
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to prepare visualization data: {e}")
    
    # Private helper methods
    
    def _get_filtered_matches(
        self,
        puuid: str,
        filters: Optional[AnalyticsFilters]
    ) -> List[Tuple[Match, MatchParticipant]]:
        """Get filtered matches for a player."""
        try:
            # Get all matches for the player
            matches = self.match_manager.get_player_matches(puuid)
            
            if not matches:
                return []
            
            # Apply filters if provided
            if filters:
                filtered_matches = []
                
                for match, participant in matches:
                    # Date range filter
                    if filters.date_range:
                        if not filters.date_range.contains(match.game_creation_datetime):
                            continue
                    
                    # Champion filter
                    if filters.champions and participant.champion_id not in filters.champions:
                        continue
                    
                    # Role filter
                    if filters.roles and participant.individual_position.lower() not in [r.lower() for r in filters.roles]:
                        continue
                    
                    # Queue type filter
                    if filters.queue_types and match.queue_id not in filters.queue_types:
                        continue
                    
                    # Win filter
                    if filters.win_only is not None and participant.win != filters.win_only:
                        continue
                    
                    filtered_matches.append((match, participant))
                
                matches = filtered_matches
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Failed to get filtered matches for {puuid}: {e}")
            return []
    
    def _calculate_performance_metrics(
        self,
        matches: List[Tuple[Match, MatchParticipant]]
    ) -> PerformanceMetrics:
        """Calculate performance metrics from matches."""
        if not matches:
            return PerformanceMetrics()
        
        total_games = len(matches)
        wins = sum(1 for _, participant in matches if participant.win)
        losses = total_games - wins
        
        # Aggregate statistics
        total_kills = sum(participant.kills for _, participant in matches)
        total_deaths = sum(participant.deaths for _, participant in matches)
        total_assists = sum(participant.assists for _, participant in matches)
        total_cs = sum(participant.total_minions_killed + participant.neutral_minions_killed 
                     for _, participant in matches)
        total_vision_score = sum(participant.vision_score for _, participant in matches)
        total_damage = sum(participant.total_damage_dealt_to_champions for _, participant in matches)
        total_gold = sum(participant.gold_earned for _, participant in matches)
        total_duration = sum(match.game_duration for match, _ in matches)
        
        return PerformanceMetrics(
            games_played=total_games,
            wins=wins,
            losses=losses,
            win_rate=wins / total_games if total_games > 0 else 0,
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists,
            avg_kda=(total_kills + total_assists) / max(total_deaths, 1),
            total_cs=total_cs,
            avg_cs_per_min=total_cs / (total_duration / 60) if total_duration > 0 else 0,
            total_vision_score=total_vision_score,
            avg_vision_score=total_vision_score / total_games if total_games > 0 else 0,
            total_damage_to_champions=total_damage,
            avg_damage_per_min=total_damage / (total_duration / 60) if total_duration > 0 else 0,
            total_gold_earned=total_gold,
            avg_gold_per_min=total_gold / (total_duration / 60) if total_duration > 0 else 0,
            total_game_duration=total_duration,
            avg_game_duration=total_duration / (total_games * 60) if total_games > 0 else 0
        )
    
    def _compare_metric_across_players(
        self,
        player_puuids: List[str],
        player_data: Dict[str, Dict],
        player_names: Dict[str, str],
        metric: str,
        analysis_period: Optional[DateRange]
    ) -> MultiPlayerComparison:
        """Compare a specific metric across multiple players."""
        values = {}
        sample_sizes = {}
        
        # Extract metric values
        for puuid in player_puuids:
            performance = player_data[puuid]['performance']
            value = getattr(performance, metric, 0)
            values[puuid] = value
            sample_sizes[puuid] = player_data[puuid]['sample_size']
        
        # Calculate rankings
        sorted_players = sorted(player_puuids, key=lambda p: values[p], reverse=True)
        rankings = {puuid: rank + 1 for rank, puuid in enumerate(sorted_players)}
        
        # Calculate percentiles
        all_values = list(values.values())
        percentiles = {}
        for puuid in player_puuids:
            percentile = self._calculate_percentile(values[puuid], all_values)
            percentiles[puuid] = percentile
        
        # Perform statistical tests between all pairs
        statistical_tests = {}
        for i, puuid1 in enumerate(player_puuids):
            for puuid2 in player_puuids[i+1:]:
                try:
                    # Get raw data for statistical testing
                    data1 = self._extract_metric_values(player_data[puuid1]['matches'], metric)
                    data2 = self._extract_metric_values(player_data[puuid2]['matches'], metric)
                    
                    if len(data1) >= 5 and len(data2) >= 5:
                        test_result = self.statistical_analyzer.perform_significance_testing(
                            data1, data2, test_type="auto"
                        )
                        statistical_tests[(puuid1, puuid2)] = test_result
                        
                except Exception as e:
                    self.logger.warning(f"Failed to perform statistical test for {metric} between {puuid1} and {puuid2}: {e}")
        
        return MultiPlayerComparison(
            metric=metric,
            players=player_puuids,
            player_names=player_names,
            values=values,
            rankings=rankings,
            percentiles=percentiles,
            statistical_tests=statistical_tests,
            sample_sizes=sample_sizes,
            analysis_period=analysis_period
        )
    
    def _calculate_percentile(self, value: float, all_values: List[float]) -> float:
        """Calculate percentile rank of a value within a list."""
        if not all_values:
            return 50.0
        
        sorted_values = sorted(all_values)
        n = len(sorted_values)
        
        # Count values less than the target value
        less_than = sum(1 for v in sorted_values if v < value)
        equal_to = sum(1 for v in sorted_values if v == value)
        
        # Calculate percentile using the standard formula
        percentile = (less_than + 0.5 * equal_to) / n * 100
        
        return min(100.0, max(0.0, percentile))
    
    def _extract_metric_values(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        metric: str
    ) -> List[float]:
        """Extract individual metric values from matches for statistical testing."""
        values = []
        
        for match, participant in matches:
            if metric == "win_rate":
                values.append(1.0 if participant.win else 0.0)
            elif metric == "avg_kda":
                kda = (participant.kills + participant.assists) / max(participant.deaths, 1)
                values.append(kda)
            elif metric == "avg_cs_per_min":
                cs = participant.total_minions_killed + participant.neutral_minions_killed
                cs_per_min = cs / (match.game_duration / 60) if match.game_duration > 0 else 0
                values.append(cs_per_min)
            elif metric == "avg_vision_score":
                values.append(participant.vision_score)
            elif metric == "avg_damage_per_min":
                damage_per_min = participant.total_damage_dealt_to_champions / (match.game_duration / 60) if match.game_duration > 0 else 0
                values.append(damage_per_min)
            elif metric == "avg_gold_per_min":
                gold_per_min = participant.gold_earned / (match.game_duration / 60) if match.game_duration > 0 else 0
                values.append(gold_per_min)
        
        return values
    
    def _determine_mastery_level(
        self,
        games_played: int,
        percentiles: Dict[str, float]
    ) -> str:
        """Determine mastery level based on games played and performance percentiles."""
        if games_played < 10:
            return "novice"
        
        # Calculate average percentile
        if percentiles:
            avg_percentile = statistics.mean(percentiles.values())
            
            if games_played >= 50 and avg_percentile >= 90:
                return "master"
            elif games_played >= 30 and avg_percentile >= 75:
                return "expert"
            elif games_played >= 20 and avg_percentile >= 50:
                return "competent"
            else:
                return "novice"
        
        return "novice"
    
    def _prepare_radar_chart_data(
        self,
        comparisons: Dict[str, MultiPlayerComparison],
        players: List[str],
        player_names: Dict[str, str]
    ) -> Dict[str, Any]:
        """Prepare data for radar chart visualization."""
        metrics = list(comparisons.keys())
        
        # Normalize values to 0-100 scale for radar chart
        normalized_data = {}
        
        for player in players:
            player_data = []
            for metric in metrics:
                percentile = comparisons[metric].percentiles[player]
                player_data.append(percentile)
            normalized_data[player] = player_data
        
        return {
            "type": "radar_chart",
            "metrics": metrics,
            "players": players,
            "player_names": player_names,
            "data": normalized_data,
            "scale": {"min": 0, "max": 100, "unit": "percentile"}
        }
    
    def _prepare_bar_chart_data(
        self,
        comparisons: Dict[str, MultiPlayerComparison],
        players: List[str],
        player_names: Dict[str, str]
    ) -> Dict[str, Any]:
        """Prepare data for bar chart visualization."""
        chart_data = {}
        
        for metric, comparison in comparisons.items():
            metric_data = []
            for player in players:
                metric_data.append({
                    "player": player,
                    "player_name": player_names[player],
                    "value": comparison.values[player],
                    "rank": comparison.rankings[player],
                    "percentile": comparison.percentiles[player]
                })
            
            # Sort by value (descending)
            metric_data.sort(key=lambda x: x["value"], reverse=True)
            chart_data[metric] = metric_data
        
        return {
            "type": "bar_chart",
            "data": chart_data,
            "players": players,
            "player_names": player_names
        }
    
    def _prepare_heatmap_data(
        self,
        comparisons: Dict[str, MultiPlayerComparison],
        players: List[str],
        player_names: Dict[str, str]
    ) -> Dict[str, Any]:
        """Prepare data for heatmap visualization."""
        metrics = list(comparisons.keys())
        
        # Create matrix of percentile values
        heatmap_matrix = []
        
        for player in players:
            player_row = []
            for metric in metrics:
                percentile = comparisons[metric].percentiles[player]
                player_row.append(percentile)
            heatmap_matrix.append(player_row)
        
        return {
            "type": "heatmap",
            "matrix": heatmap_matrix,
            "players": players,
            "player_names": player_names,
            "metrics": metrics,
            "scale": {"min": 0, "max": 100, "unit": "percentile"},
            "color_scheme": "RdYlGn"  # Red-Yellow-Green
        }