"""
Champion Synergy Analysis System for the League of Legends Team Optimizer.

This module provides comprehensive champion synergy analysis capabilities,
including champion combination analysis, synergy matrix calculations,
and statistical significance testing for synergy effects.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import statistics
import itertools

from .analytics_models import (
    TeamComposition, SynergyEffects, PerformanceMetrics, PerformanceDelta,
    SignificanceTest, ConfidenceInterval, AnalyticsError, InsufficientDataError,
    AnalyticsFilters, DateRange
)
from .statistical_analyzer import StatisticalAnalyzer
from .baseline_manager import BaselineManager, BaselineContext
from .config import Config


@dataclass
class ChampionCombination:
    """Represents a champion combination for synergy analysis."""
    
    champion_ids: Tuple[int, ...]
    roles: Tuple[str, ...]
    combination_type: str  # "pair", "trio", "full_team"
    
    def __post_init__(self):
        """Validate champion combination."""
        if len(self.champion_ids) != len(self.roles):
            raise ValueError("Champion IDs and roles must have same length")
        
        if len(self.champion_ids) < 2:
            raise ValueError("Champion combination must have at least 2 champions")
        
        # Sort for consistent comparison
        sorted_pairs = sorted(zip(self.champion_ids, self.roles))
        self.champion_ids = tuple(pair[0] for pair in sorted_pairs)
        self.roles = tuple(pair[1] for pair in sorted_pairs)
    
    @property
    def combination_key(self) -> str:
        """Generate unique key for this combination."""
        pairs = [f"{role}:{champ_id}" for role, champ_id in zip(self.roles, self.champion_ids)]
        return "|".join(sorted(pairs))


@dataclass
class SynergyMetrics:
    """Metrics for champion synergy analysis."""
    
    combination: ChampionCombination
    games_together: int
    wins_together: int
    losses_together: int
    win_rate: float = 0.0
    
    # Performance metrics when playing together
    avg_combined_kda: float = 0.0
    avg_combined_damage: float = 0.0
    avg_combined_vision: float = 0.0
    avg_game_duration: float = 0.0
    
    # Baseline comparisons
    expected_win_rate: float = 0.0
    win_rate_delta: float = 0.0
    performance_deltas: Dict[str, PerformanceDelta] = field(default_factory=dict)
    
    # Statistical measures
    synergy_score: float = 0.0  # -1.0 to 1.0
    confidence_interval: Optional[ConfidenceInterval] = None
    statistical_significance: Optional[SignificanceTest] = None
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.games_together > 0:
            self.win_rate = self.wins_together / self.games_together
            self.win_rate_delta = self.win_rate - self.expected_win_rate


@dataclass
class SynergyMatrix:
    """Matrix of synergy scores between champions/players."""
    
    matrix_type: str  # "champion", "player", "role"
    synergy_scores: Dict[Tuple[Any, Any], float] = field(default_factory=dict)
    confidence_scores: Dict[Tuple[Any, Any], float] = field(default_factory=dict)
    sample_sizes: Dict[Tuple[Any, Any], int] = field(default_factory=dict)
    
    def get_synergy(self, entity1: Any, entity2: Any) -> float:
        """Get synergy score between two entities."""
        key = tuple(sorted([entity1, entity2]))
        return self.synergy_scores.get(key, 0.0)
    
    def get_confidence(self, entity1: Any, entity2: Any) -> float:
        """Get confidence score for synergy between two entities."""
        key = tuple(sorted([entity1, entity2]))
        return self.confidence_scores.get(key, 0.0)
    
    def get_sample_size(self, entity1: Any, entity2: Any) -> int:
        """Get sample size for synergy between two entities."""
        key = tuple(sorted([entity1, entity2]))
        return self.sample_sizes.get(key, 0)


@dataclass
class TeamSynergyAnalysis:
    """Comprehensive team synergy analysis result."""
    
    team_composition: TeamComposition
    overall_synergy_score: float
    pair_synergies: Dict[Tuple[int, int], float]  # (champion1, champion2) -> synergy
    role_synergies: Dict[Tuple[str, str], float]  # (role1, role2) -> synergy
    player_synergies: Dict[Tuple[str, str], float]  # (puuid1, puuid2) -> synergy
    
    # Performance analysis
    expected_performance: PerformanceMetrics
    actual_performance: Optional[PerformanceMetrics] = None
    performance_boost: Optional[Dict[str, PerformanceDelta]] = None
    
    # Statistical validation
    confidence_level: float = 0.0
    sample_size: int = 0
    statistical_significance: Optional[SignificanceTest] = None


class ChampionSynergyAnalyzer:
    """
    Comprehensive champion synergy analysis system.
    
    Analyzes champion combinations from historical matches to identify
    synergistic effects, calculate synergy matrices, and provide
    statistical validation of synergy effects.
    """
    
    def __init__(
        self,
        config: Config,
        match_manager,
        baseline_manager: BaselineManager,
        statistical_analyzer: StatisticalAnalyzer
    ):
        """
        Initialize the champion synergy analyzer.
        
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
        self.min_games_for_synergy = 10
        self.min_games_for_significance = 20
        self.synergy_confidence_threshold = 0.05
        self.recent_games_weight = 1.5  # Weight for recent games
        self.recent_cutoff_days = 60
    
    def analyze_champion_combinations(
        self,
        puuids: List[str],
        filters: Optional[AnalyticsFilters] = None
    ) -> Dict[str, SynergyMetrics]:
        """
        Analyze champion combinations from historical matches.
        
        Args:
            puuids: List of player PUUIDs to analyze
            filters: Optional filters for match selection
            
        Returns:
            Dictionary mapping combination keys to synergy metrics
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If analysis fails
        """
        try:
            self.logger.info(f"Analyzing champion combinations for {len(puuids)} players")
            
            # Get matches with multiple players
            team_matches = self.match_manager.get_matches_with_multiple_players(set(puuids))
            
            if not team_matches:
                raise InsufficientDataError(
                    required_games=1,
                    available_games=0,
                    context="champion combination analysis"
                )
            
            # Apply filters if provided
            if filters:
                team_matches = self._apply_filters_to_matches(team_matches, filters)
            
            self.logger.info(f"Found {len(team_matches)} matches with multiple team members")
            
            # Extract champion combinations from matches
            combinations = self._extract_champion_combinations(team_matches, puuids)
            
            # Calculate synergy metrics for each combination
            synergy_results = {}
            for combination_key, combination_data in combinations.items():
                try:
                    synergy_metrics = self._calculate_combination_synergy(
                        combination_data['combination'],
                        combination_data['matches'],
                        puuids
                    )
                    synergy_results[combination_key] = synergy_metrics
                except Exception as e:
                    self.logger.warning(f"Failed to calculate synergy for {combination_key}: {e}")
            
            self.logger.info(f"Calculated synergy metrics for {len(synergy_results)} combinations")
            return synergy_results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze champion combinations: {e}")
    
    def calculate_synergy_matrix(
        self,
        puuids: List[str],
        matrix_type: str = "champion",
        filters: Optional[AnalyticsFilters] = None
    ) -> SynergyMatrix:
        """
        Calculate synergy matrix for champion pairs and team compositions.
        
        Args:
            puuids: List of player PUUIDs
            matrix_type: Type of matrix ("champion", "player", "role")
            filters: Optional filters for match selection
            
        Returns:
            SynergyMatrix object with calculated synergies
            
        Raises:
            AnalyticsError: If matrix calculation fails
        """
        try:
            self.logger.info(f"Calculating {matrix_type} synergy matrix for {len(puuids)} players")
            
            # Get champion combinations
            combinations = self.analyze_champion_combinations(puuids, filters)
            
            # Initialize matrix
            synergy_matrix = SynergyMatrix(matrix_type=matrix_type)
            
            # Process combinations based on matrix type
            if matrix_type == "champion":
                self._populate_champion_matrix(synergy_matrix, combinations)
            elif matrix_type == "player":
                self._populate_player_matrix(synergy_matrix, combinations, puuids)
            elif matrix_type == "role":
                self._populate_role_matrix(synergy_matrix, combinations)
            else:
                raise AnalyticsError(f"Unsupported matrix type: {matrix_type}")
            
            self.logger.info(f"Calculated synergy matrix with {len(synergy_matrix.synergy_scores)} entries")
            return synergy_matrix
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to calculate synergy matrix: {e}")
    
    def quantify_synergy_effects(
        self,
        combination: ChampionCombination,
        matches: List[Any],
        puuids: List[str]
    ) -> SynergyMetrics:
        """
        Quantify synergy effects relative to individual performance.
        
        Args:
            combination: Champion combination to analyze
            matches: List of matches with this combination
            puuids: List of player PUUIDs
            
        Returns:
            SynergyMetrics with quantified effects
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If quantification fails
        """
        try:
            if len(matches) < self.min_games_for_synergy:
                raise InsufficientDataError(
                    required_games=self.min_games_for_synergy,
                    available_games=len(matches),
                    context=f"synergy quantification for {combination.combination_key}"
                )
            
            # Calculate actual performance when playing together
            actual_performance = self._calculate_combination_performance(matches, combination)
            
            # Calculate expected performance based on individual baselines
            expected_performance = self._calculate_expected_performance(combination, puuids)
            
            # Calculate performance deltas
            performance_deltas = self._calculate_performance_deltas(
                actual_performance, expected_performance
            )
            
            # Calculate synergy score
            synergy_score = self._calculate_synergy_score(performance_deltas)
            
            # Create synergy metrics
            synergy_metrics = SynergyMetrics(
                combination=combination,
                games_together=len(matches),
                wins_together=sum(1 for match in matches if self._is_winning_match(match, combination)),
                losses_together=len(matches) - sum(1 for match in matches if self._is_winning_match(match, combination)),
                expected_win_rate=expected_performance.win_rate,
                performance_deltas=performance_deltas,
                synergy_score=synergy_score
            )
            
            # Calculate statistical measures
            if len(matches) >= self.min_games_for_significance:
                synergy_metrics.confidence_interval = self._calculate_confidence_interval(matches)
                synergy_metrics.statistical_significance = self._test_statistical_significance(
                    matches, expected_performance
                )
            
            return synergy_metrics
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to quantify synergy effects: {e}")
    
    def test_synergy_significance(
        self,
        synergy_metrics: SynergyMetrics,
        alpha: float = 0.05
    ) -> SignificanceTest:
        """
        Test statistical significance of synergy effects.
        
        Args:
            synergy_metrics: Synergy metrics to test
            alpha: Significance level
            
        Returns:
            SignificanceTest result
            
        Raises:
            AnalyticsError: If significance testing fails
        """
        try:
            if synergy_metrics.games_together < self.min_games_for_significance:
                raise InsufficientDataError(
                    required_games=self.min_games_for_significance,
                    available_games=synergy_metrics.games_together,
                    context="statistical significance testing"
                )
            
            # Perform one-sample t-test against expected win rate
            observed_wins = [1.0] * synergy_metrics.wins_together + [0.0] * synergy_metrics.losses_together
            expected_win_rate = synergy_metrics.expected_win_rate
            
            # Use statistical analyzer for significance testing
            significance_test = self.statistical_analyzer.perform_one_sample_test(
                observed_wins, expected_win_rate
            )
            
            return significance_test
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to test synergy significance: {e}")
    
    def filter_recommendations_by_synergy(
        self,
        recommendations: List[Any],
        team_context: Any,
        synergy_threshold: float = 0.1
    ) -> List[Any]:
        """
        Filter and rank recommendations based on synergy analysis.
        
        Args:
            recommendations: List of champion recommendations
            team_context: Current team context
            synergy_threshold: Minimum synergy score threshold
            
        Returns:
            Filtered and ranked recommendations
        """
        try:
            if not recommendations:
                return recommendations
            
            # Calculate synergy scores for each recommendation
            synergy_adjusted_recommendations = []
            
            for recommendation in recommendations:
                try:
                    # Calculate synergy with existing team
                    synergy_score = self._calculate_team_synergy_score(
                        recommendation, team_context
                    )
                    
                    # Adjust recommendation score based on synergy
                    if synergy_score >= synergy_threshold:
                        adjusted_recommendation = self._adjust_recommendation_for_synergy(
                            recommendation, synergy_score
                        )
                        synergy_adjusted_recommendations.append(adjusted_recommendation)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to calculate synergy for recommendation: {e}")
                    # Include original recommendation if synergy calculation fails
                    synergy_adjusted_recommendations.append(recommendation)
            
            # Sort by adjusted scores
            synergy_adjusted_recommendations.sort(
                key=lambda x: getattr(x, 'recommendation_score', 0.0),
                reverse=True
            )
            
            self.logger.info(f"Filtered {len(recommendations)} recommendations to {len(synergy_adjusted_recommendations)} based on synergy")
            return synergy_adjusted_recommendations
            
        except Exception as e:
            self.logger.warning(f"Failed to filter recommendations by synergy: {e}")
            return recommendations
    
    def analyze_team_synergy(
        self,
        team_composition: TeamComposition,
        filters: Optional[AnalyticsFilters] = None
    ) -> TeamSynergyAnalysis:
        """
        Analyze synergy for a complete team composition.
        
        Args:
            team_composition: Team composition to analyze
            filters: Optional filters for match selection
            
        Returns:
            TeamSynergyAnalysis with comprehensive synergy analysis
            
        Raises:
            AnalyticsError: If team synergy analysis fails
        """
        try:
            self.logger.info(f"Analyzing team synergy for composition: {team_composition.composition_id}")
            
            # Get historical matches with this composition
            composition_matches = self._find_composition_matches(team_composition, filters)
            
            if not composition_matches:
                # Calculate expected synergy based on pair synergies
                return self._calculate_theoretical_team_synergy(team_composition)
            
            # Calculate pair synergies
            pair_synergies = self._calculate_all_pair_synergies(team_composition, composition_matches)
            
            # Calculate role synergies
            role_synergies = self._calculate_role_synergies(team_composition, composition_matches)
            
            # Calculate player synergies
            player_synergies = self._calculate_player_synergies(team_composition, composition_matches)
            
            # Calculate overall synergy score
            overall_synergy = self._calculate_overall_synergy_score(
                pair_synergies, role_synergies, player_synergies
            )
            
            # Calculate performance metrics
            actual_performance = self._calculate_team_performance(composition_matches)
            expected_performance = self._calculate_expected_team_performance(team_composition)
            performance_boost = self._calculate_performance_deltas(actual_performance, expected_performance)
            
            # Statistical validation
            confidence_level = self._calculate_team_confidence(composition_matches)
            statistical_significance = None
            if len(composition_matches) >= self.min_games_for_significance:
                statistical_significance = self._test_team_significance(
                    composition_matches, expected_performance
                )
            
            return TeamSynergyAnalysis(
                team_composition=team_composition,
                overall_synergy_score=overall_synergy,
                pair_synergies=pair_synergies,
                role_synergies=role_synergies,
                player_synergies=player_synergies,
                expected_performance=expected_performance,
                actual_performance=actual_performance,
                performance_boost=performance_boost,
                confidence_level=confidence_level,
                sample_size=len(composition_matches),
                statistical_significance=statistical_significance
            )
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to analyze team synergy: {e}")
    
    # Helper methods
    
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
                # This would need match-specific logic
                pass
            
            filtered_matches.append(match)
        
        return filtered_matches
    
    def _extract_champion_combinations(
        self,
        matches: List[Any],
        puuids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract champion combinations from matches."""
        combinations = defaultdict(lambda: {'combination': None, 'matches': []})
        
        for match in matches:
            # Get participants for tracked players
            tracked_participants = []
            for participant in match.participants:
                if participant.puuid in puuids:
                    tracked_participants.append(participant)
            
            if len(tracked_participants) < 2:
                continue
            
            # Group by team
            teams = defaultdict(list)
            for participant in tracked_participants:
                teams[participant.team_id].append(participant)
            
            # Create combinations for each team
            for team_participants in teams.values():
                if len(team_participants) < 2:
                    continue
                
                # Create all pair combinations
                for i in range(len(team_participants)):
                    for j in range(i + 1, len(team_participants)):
                        p1, p2 = team_participants[i], team_participants[j]
                        
                        combination = ChampionCombination(
                            champion_ids=(p1.champion_id, p2.champion_id),
                            roles=(p1.individual_position or p1.lane, p2.individual_position or p2.lane),
                            combination_type="pair"
                        )
                        
                        key = combination.combination_key
                        combinations[key]['combination'] = combination
                        combinations[key]['matches'].append(match)
        
        return dict(combinations)
    
    def _calculate_combination_synergy(
        self,
        combination: ChampionCombination,
        matches: List[Any],
        puuids: List[str]
    ) -> SynergyMetrics:
        """Calculate synergy metrics for a champion combination."""
        if len(matches) < self.min_games_for_synergy:
            raise InsufficientDataError(
                required_games=self.min_games_for_synergy,
                available_games=len(matches),
                context=f"combination synergy for {combination.combination_key}"
            )
        
        # Calculate basic metrics
        wins = sum(1 for match in matches if self._is_winning_match(match, combination))
        losses = len(matches) - wins
        win_rate = wins / len(matches)
        
        # Calculate performance metrics
        combined_kda = self._calculate_combined_kda(matches, combination)
        combined_damage = self._calculate_combined_damage(matches, combination)
        combined_vision = self._calculate_combined_vision(matches, combination)
        avg_duration = statistics.mean(match.game_duration for match in matches) / 60  # Convert to minutes
        
        # Calculate expected performance (simplified)
        expected_win_rate = 0.5  # This would be calculated from individual baselines
        
        # Calculate synergy score
        win_rate_delta = win_rate - expected_win_rate
        synergy_score = max(-1.0, min(1.0, win_rate_delta * 2))  # Scale to -1 to 1
        
        return SynergyMetrics(
            combination=combination,
            games_together=len(matches),
            wins_together=wins,
            losses_together=losses,
            win_rate=win_rate,
            avg_combined_kda=combined_kda,
            avg_combined_damage=combined_damage,
            avg_combined_vision=combined_vision,
            avg_game_duration=avg_duration,
            expected_win_rate=expected_win_rate,
            win_rate_delta=win_rate_delta,
            synergy_score=synergy_score
        )
    
    def _populate_champion_matrix(self, matrix: SynergyMatrix, combinations: Dict[str, SynergyMetrics]) -> None:
        """Populate champion synergy matrix."""
        for combination_key, synergy_metrics in combinations.items():
            if synergy_metrics.combination.combination_type == "pair":
                champ1, champ2 = synergy_metrics.combination.champion_ids
                key = tuple(sorted([champ1, champ2]))
                
                matrix.synergy_scores[key] = synergy_metrics.synergy_score
                matrix.confidence_scores[key] = self._calculate_confidence_score(synergy_metrics)
                matrix.sample_sizes[key] = synergy_metrics.games_together
    
    def _populate_player_matrix(self, matrix: SynergyMatrix, combinations: Dict[str, SynergyMetrics], puuids: List[str]) -> None:
        """Populate player synergy matrix."""
        # This would require mapping combinations back to specific players
        # Implementation depends on how player information is stored in matches
        pass
    
    def _populate_role_matrix(self, matrix: SynergyMatrix, combinations: Dict[str, SynergyMetrics]) -> None:
        """Populate role synergy matrix."""
        role_combinations = defaultdict(list)
        
        for synergy_metrics in combinations.values():
            if synergy_metrics.combination.combination_type == "pair":
                role1, role2 = synergy_metrics.combination.roles
                key = tuple(sorted([role1, role2]))
                role_combinations[key].append(synergy_metrics)
        
        # Aggregate synergy scores by role combination
        for role_key, synergy_list in role_combinations.items():
            if synergy_list:
                avg_synergy = statistics.mean(s.synergy_score for s in synergy_list)
                total_games = sum(s.games_together for s in synergy_list)
                avg_confidence = statistics.mean(self._calculate_confidence_score(s) for s in synergy_list)
                
                matrix.synergy_scores[role_key] = avg_synergy
                matrix.confidence_scores[role_key] = avg_confidence
                matrix.sample_sizes[role_key] = total_games
    
    def _is_winning_match(self, match: Any, combination: ChampionCombination) -> bool:
        """Check if a match was won by the combination."""
        # Find participants with the combination champions
        combination_participants = []
        for participant in match.participants:
            if participant.champion_id in combination.champion_ids:
                combination_participants.append(participant)
        
        # Check if all participants won (same team)
        if len(combination_participants) >= 2:
            return all(p.win for p in combination_participants[:2])
        
        return False
    
    def _calculate_combined_kda(self, matches: List[Any], combination: ChampionCombination) -> float:
        """Calculate average combined KDA for a combination."""
        total_kda = 0.0
        count = 0
        
        for match in matches:
            combination_participants = [
                p for p in match.participants 
                if p.champion_id in combination.champion_ids
            ]
            
            if len(combination_participants) >= 2:
                kda_sum = sum(
                    (p.kills + p.assists) / max(p.deaths, 1) 
                    for p in combination_participants[:2]
                )
                total_kda += kda_sum
                count += 1
        
        return total_kda / count if count > 0 else 0.0
    
    def _calculate_combined_damage(self, matches: List[Any], combination: ChampionCombination) -> float:
        """Calculate average combined damage for a combination."""
        total_damage = 0.0
        count = 0
        
        for match in matches:
            combination_participants = [
                p for p in match.participants 
                if p.champion_id in combination.champion_ids
            ]
            
            if len(combination_participants) >= 2:
                damage_sum = sum(
                    p.total_damage_dealt_to_champions 
                    for p in combination_participants[:2]
                )
                total_damage += damage_sum
                count += 1
        
        return total_damage / count if count > 0 else 0.0
    
    def _calculate_combined_vision(self, matches: List[Any], combination: ChampionCombination) -> float:
        """Calculate average combined vision score for a combination."""
        total_vision = 0.0
        count = 0
        
        for match in matches:
            combination_participants = [
                p for p in match.participants 
                if p.champion_id in combination.champion_ids
            ]
            
            if len(combination_participants) >= 2:
                vision_sum = sum(p.vision_score for p in combination_participants[:2])
                total_vision += vision_sum
                count += 1
        
        return total_vision / count if count > 0 else 0.0
    
    def _calculate_confidence_score(self, synergy_metrics: SynergyMetrics) -> float:
        """Calculate confidence score for synergy metrics."""
        # Simple confidence based on sample size
        games = synergy_metrics.games_together
        if games >= 50:
            return 1.0
        elif games >= 20:
            return 0.8
        elif games >= 10:
            return 0.6
        elif games >= 5:
            return 0.4
        else:
            return 0.2
    
    def _calculate_team_synergy_score(self, recommendation: Any, team_context: Any) -> float:
        """Calculate synergy score for a recommendation with existing team."""
        # Simplified implementation - would need access to synergy matrix
        return 0.0
    
    def _adjust_recommendation_for_synergy(self, recommendation: Any, synergy_score: float) -> Any:
        """Adjust recommendation score based on synergy."""
        # This would modify the recommendation object
        return recommendation
    
    def _find_composition_matches(self, team_composition: TeamComposition, filters: Optional[AnalyticsFilters]) -> List[Any]:
        """Find historical matches with the given team composition."""
        # This would search for matches with the exact composition
        return []
    
    def _calculate_theoretical_team_synergy(self, team_composition: TeamComposition) -> TeamSynergyAnalysis:
        """Calculate theoretical team synergy when no historical data exists."""
        return TeamSynergyAnalysis(
            team_composition=team_composition,
            overall_synergy_score=0.0,
            pair_synergies={},
            role_synergies={},
            player_synergies={},
            expected_performance=PerformanceMetrics(),
            confidence_level=0.0,
            sample_size=0
        )
    
    def _calculate_all_pair_synergies(self, team_composition: TeamComposition, matches: List[Any]) -> Dict[Tuple[int, int], float]:
        """Calculate synergies for all champion pairs in the composition."""
        pair_synergies = {}
        champions = team_composition.get_champion_ids()
        
        for i in range(len(champions)):
            for j in range(i + 1, len(champions)):
                champ1, champ2 = champions[i], champions[j]
                # Calculate synergy for this pair
                synergy_score = self._calculate_pair_synergy_from_matches(champ1, champ2, matches)
                pair_synergies[(champ1, champ2)] = synergy_score
        
        return pair_synergies
    
    def _calculate_role_synergies(self, team_composition: TeamComposition, matches: List[Any]) -> Dict[Tuple[str, str], float]:
        """Calculate synergies for all role pairs in the composition."""
        role_synergies = {}
        roles = list(team_composition.players.keys())
        
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                role1, role2 = roles[i], roles[j]
                # Calculate synergy for this role pair
                synergy_score = self._calculate_role_pair_synergy_from_matches(role1, role2, matches)
                role_synergies[(role1, role2)] = synergy_score
        
        return role_synergies
    
    def _calculate_player_synergies(self, team_composition: TeamComposition, matches: List[Any]) -> Dict[Tuple[str, str], float]:
        """Calculate synergies for all player pairs in the composition."""
        player_synergies = {}
        puuids = team_composition.get_player_puuids()
        
        for i in range(len(puuids)):
            for j in range(i + 1, len(puuids)):
                puuid1, puuid2 = puuids[i], puuids[j]
                # Calculate synergy for this player pair
                synergy_score = self._calculate_player_pair_synergy_from_matches(puuid1, puuid2, matches)
                player_synergies[(puuid1, puuid2)] = synergy_score
        
        return player_synergies
    
    def _calculate_overall_synergy_score(
        self,
        pair_synergies: Dict[Tuple[int, int], float],
        role_synergies: Dict[Tuple[str, str], float],
        player_synergies: Dict[Tuple[str, str], float]
    ) -> float:
        """Calculate overall team synergy score."""
        all_synergies = []
        all_synergies.extend(pair_synergies.values())
        all_synergies.extend(role_synergies.values())
        all_synergies.extend(player_synergies.values())
        
        if all_synergies:
            return statistics.mean(all_synergies)
        return 0.0
    
    def _calculate_team_performance(self, matches: List[Any]) -> PerformanceMetrics:
        """Calculate team performance from matches."""
        if not matches:
            return PerformanceMetrics()
        
        total_games = len(matches)
        total_wins = sum(1 for match in matches if self._is_team_win(match))
        
        return PerformanceMetrics(
            games_played=total_games,
            wins=total_wins,
            losses=total_games - total_wins,
            win_rate=total_wins / total_games
        )
    
    def _calculate_expected_team_performance(self, team_composition: TeamComposition) -> PerformanceMetrics:
        """Calculate expected team performance based on individual baselines."""
        # Simplified - would calculate based on individual player baselines
        return PerformanceMetrics(
            games_played=0,
            wins=0,
            losses=0,
            win_rate=0.5  # Default expectation
        )
    
    def _calculate_performance_deltas(self, actual: PerformanceMetrics, expected: PerformanceMetrics) -> Dict[str, PerformanceDelta]:
        """Calculate performance deltas between actual and expected."""
        deltas = {}
        
        if expected.win_rate > 0:
            deltas['win_rate'] = PerformanceDelta(
                metric_name='win_rate',
                baseline_value=expected.win_rate,
                actual_value=actual.win_rate
            )
        
        return deltas
    
    def _calculate_team_confidence(self, matches: List[Any]) -> float:
        """Calculate confidence level for team analysis."""
        return self._calculate_confidence_score(
            type('MockSynergy', (), {'games_together': len(matches)})()
        )
    
    def _is_team_win(self, match: Any) -> bool:
        """Check if the team won the match."""
        # This would need to check if the tracked team won
        return True  # Placeholder
    
    def _calculate_pair_synergy_from_matches(self, champ1: int, champ2: int, matches: List[Any]) -> float:
        """Calculate synergy score for a champion pair from matches."""
        return 0.0  # Placeholder
    
    def _calculate_role_pair_synergy_from_matches(self, role1: str, role2: str, matches: List[Any]) -> float:
        """Calculate synergy score for a role pair from matches."""
        return 0.0  # Placeholder
    
    def _calculate_player_pair_synergy_from_matches(self, puuid1: str, puuid2: str, matches: List[Any]) -> float:
        """Calculate synergy score for a player pair from matches."""
        return 0.0  # Placeholder
    
    def _calculate_combination_performance(self, matches: List[Any], combination: ChampionCombination) -> PerformanceMetrics:
        """Calculate performance metrics for a combination."""
        return PerformanceMetrics()  # Placeholder
    
    def _calculate_expected_performance(self, combination: ChampionCombination, puuids: List[str]) -> PerformanceMetrics:
        """Calculate expected performance for a combination."""
        return PerformanceMetrics()  # Placeholder
    
    def _calculate_synergy_score(self, performance_deltas: Dict[str, PerformanceDelta]) -> float:
        """Calculate overall synergy score from performance deltas."""
        if not performance_deltas:
            return 0.0
        
        # Average the delta percentages
        delta_values = [delta.delta_percentage for delta in performance_deltas.values()]
        avg_delta = statistics.mean(delta_values)
        
        # Scale to -1 to 1 range
        return max(-1.0, min(1.0, avg_delta / 100))
    
    def _calculate_confidence_interval(self, matches: List[Any]) -> ConfidenceInterval:
        """Calculate confidence interval for match results."""
        wins = sum(1 for match in matches if self._is_team_win(match))
        n = len(matches)
        p = wins / n
        
        # Simple binomial confidence interval
        z = 1.96  # 95% confidence
        margin = z * (p * (1 - p) / n) ** 0.5
        
        return ConfidenceInterval(
            lower_bound=max(0, p - margin),
            upper_bound=min(1, p + margin),
            confidence_level=0.95,
            sample_size=n
        )
    
    def _test_statistical_significance(self, matches: List[Any], expected_performance: PerformanceMetrics) -> SignificanceTest:
        """Test statistical significance of performance difference."""
        wins = sum(1 for match in matches if self._is_team_win(match))
        n = len(matches)
        observed_rate = wins / n
        expected_rate = expected_performance.win_rate
        
        # Simple z-test for proportions
        if expected_rate > 0 and expected_rate < 1:
            se = (expected_rate * (1 - expected_rate) / n) ** 0.5
            z_stat = (observed_rate - expected_rate) / se
            
            # Approximate p-value (simplified)
            p_value = 2 * (1 - abs(z_stat) / 2) if abs(z_stat) < 2 else 0.05
            
            return SignificanceTest(
                test_type="z_test_proportions",
                statistic=z_stat,
                p_value=max(0, min(1, p_value))
            )
        
        return SignificanceTest(
            test_type="insufficient_data",
            statistic=0.0,
            p_value=1.0
        )
    
    def _test_team_significance(self, matches: List[Any], expected_performance: PerformanceMetrics) -> SignificanceTest:
        """Test statistical significance of team performance."""
        return self._test_statistical_significance(matches, expected_performance)