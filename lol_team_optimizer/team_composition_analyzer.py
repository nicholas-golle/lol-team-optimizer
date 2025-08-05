"""
Team Composition Analyzer for historical composition analysis.

This module analyzes team compositions and their historical performance,
providing insights into composition effectiveness, synergy effects, and
optimal team setups based on actual match data.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
import itertools

from .models import Match, MatchParticipant
from .analytics_models import (
    TeamComposition, PlayerRoleAssignment, CompositionPerformance,
    PerformanceMetrics, PerformanceDelta, SynergyEffects, SignificanceTest,
    ConfidenceInterval, AnalyticsFilters, InsufficientDataError,
    StatisticalAnalysisError, DataValidationError
)
from .baseline_manager import BaselineManager
from .statistical_analyzer import StatisticalAnalyzer
from .config import Config


@dataclass
class CompositionSimilarity:
    """Represents similarity between two team compositions."""
    
    composition_id: str
    similarity_score: float  # 0.0 to 1.0
    matching_elements: Dict[str, Any]  # What elements match
    total_matches: int
    
    def __post_init__(self):
        """Validate composition similarity."""
        if not 0 <= self.similarity_score <= 1:
            raise DataValidationError("Similarity score must be between 0 and 1")
        
        if self.total_matches < 0:
            raise DataValidationError("Total matches cannot be negative")


@dataclass
class OptimalComposition:
    """Represents an optimal team composition recommendation."""
    
    composition: TeamComposition
    expected_performance: PerformanceMetrics
    confidence_score: float
    historical_sample_size: int
    synergy_score: float
    reasoning: List[str]
    
    def __post_init__(self):
        """Validate optimal composition."""
        if not 0 <= self.confidence_score <= 1:
            raise DataValidationError("Confidence score must be between 0 and 1")
        
        if not -1 <= self.synergy_score <= 1:
            raise DataValidationError("Synergy score must be between -1 and 1")
        
        if self.historical_sample_size < 0:
            raise DataValidationError("Historical sample size cannot be negative")


@dataclass
class CompositionConstraints:
    """Constraints for composition optimization."""
    
    required_players: Optional[Dict[str, str]] = None  # role -> puuid
    available_champions: Optional[Dict[str, List[int]]] = None  # puuid -> champion_ids
    banned_champions: Optional[List[int]] = None
    role_preferences: Optional[Dict[str, List[str]]] = None  # puuid -> preferred_roles
    min_synergy_score: float = -1.0
    max_risk_tolerance: float = 1.0  # 0.0 = very safe, 1.0 = high risk/reward
    
    def __post_init__(self):
        """Validate composition constraints."""
        if not -1 <= self.min_synergy_score <= 1:
            raise DataValidationError("Min synergy score must be between -1 and 1")
        
        if not 0 <= self.max_risk_tolerance <= 1:
            raise DataValidationError("Max risk tolerance must be between 0 and 1")


class CompositionCache:
    """Cache for composition analysis results."""
    
    def __init__(self):
        """Initialize composition cache."""
        self.performance_cache: Dict[str, CompositionPerformance] = {}
        self.similarity_cache: Dict[Tuple[str, str], float] = {}
        self.synergy_cache: Dict[Tuple[str, str], float] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.max_cache_age_hours = 24
    
    def get_performance(self, composition_id: str) -> Optional[CompositionPerformance]:
        """Get cached composition performance."""
        if composition_id not in self.performance_cache:
            return None
        
        # Check if cache is stale
        if self._is_cache_stale(composition_id):
            del self.performance_cache[composition_id]
            return None
        
        return self.performance_cache[composition_id]
    
    def cache_performance(self, composition_id: str, performance: CompositionPerformance) -> None:
        """Cache composition performance."""
        self.performance_cache[composition_id] = performance
        self.cache_timestamps[composition_id] = datetime.now()
    
    def get_similarity(self, comp1_id: str, comp2_id: str) -> Optional[float]:
        """Get cached similarity score."""
        key = tuple(sorted([comp1_id, comp2_id]))
        return self.similarity_cache.get(key)
    
    def cache_similarity(self, comp1_id: str, comp2_id: str, similarity: float) -> None:
        """Cache similarity score."""
        key = tuple(sorted([comp1_id, comp2_id]))
        self.similarity_cache[key] = similarity
    
    def _is_cache_stale(self, key: str) -> bool:
        """Check if cache entry is stale."""
        if key not in self.cache_timestamps:
            return True
        
        age = datetime.now() - self.cache_timestamps[key]
        return age.total_seconds() > (self.max_cache_age_hours * 3600)


class TeamCompositionAnalyzer:
    """
    Analyzes team compositions and their historical performance.
    
    Provides comprehensive analysis of team compositions including performance
    metrics, synergy effects, similarity matching, and optimization recommendations.
    """
    
    def __init__(self, match_manager, baseline_manager: BaselineManager, config: Config):
        """
        Initialize the team composition analyzer.
        
        Args:
            match_manager: Match manager for accessing historical data
            baseline_manager: Baseline manager for performance comparisons
            config: Configuration object
        """
        self.match_manager = match_manager
        self.baseline_manager = baseline_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.statistical_analyzer = StatisticalAnalyzer()
        self.composition_cache = CompositionCache()
        
        # Configuration
        self.min_games_for_analysis = 3
        self.similarity_threshold = 0.7
        self.confidence_level = 0.95
        self.synergy_significance_threshold = 0.05
    
    def analyze_composition_performance(self, composition: TeamComposition) -> CompositionPerformance:
        """
        Analyze the historical performance of a specific team composition.
        
        Args:
            composition: Team composition to analyze
            
        Returns:
            CompositionPerformance with detailed analysis
            
        Raises:
            InsufficientDataError: If not enough historical data exists
            StatisticalAnalysisError: If analysis fails
        """
        # Check cache first
        cached_performance = self.composition_cache.get_performance(composition.composition_id)
        if cached_performance:
            self.logger.debug(f"Using cached performance for composition {composition.composition_id}")
            return cached_performance
        
        try:
            # Find historical matches for this composition
            historical_matches = self._find_composition_matches(composition)
            
            if len(historical_matches) < self.min_games_for_analysis:
                raise InsufficientDataError(
                    required_games=self.min_games_for_analysis,
                    available_games=len(historical_matches),
                    context=f"composition analysis for {composition.composition_id}"
                )
            
            # Calculate composition performance metrics
            performance_metrics = self._calculate_composition_metrics(historical_matches)
            
            # Calculate performance vs individual baselines
            baseline_deltas = self._calculate_baseline_deltas(composition, historical_matches)
            
            # Calculate synergy effects
            synergy_effects = self._calculate_synergy_effects(composition, historical_matches, baseline_deltas)
            
            # Perform statistical significance testing
            significance_test = self._test_composition_significance(historical_matches, baseline_deltas)
            
            # Calculate confidence interval
            confidence_interval = self._calculate_composition_confidence_interval(historical_matches)
            
            # Create composition performance object
            composition_performance = CompositionPerformance(
                composition=composition,
                total_games=len(historical_matches),
                performance=performance_metrics,
                performance_vs_individual_baselines=baseline_deltas,
                synergy_effects=synergy_effects,
                statistical_significance=significance_test,
                confidence_interval=confidence_interval
            )
            
            # Cache the result
            self.composition_cache.cache_performance(composition.composition_id, composition_performance)
            
            self.logger.info(f"Analyzed composition {composition.composition_id} with {len(historical_matches)} games")
            return composition_performance
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, StatisticalAnalysisError)):
                raise
            raise StatisticalAnalysisError(f"Failed to analyze composition performance: {e}")
    
    def find_similar_compositions(self, composition: TeamComposition, 
                                similarity_threshold: Optional[float] = None) -> List[CompositionSimilarity]:
        """
        Find compositions similar to the given composition.
        
        Args:
            composition: Target composition to find similarities for
            similarity_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of similar compositions sorted by similarity score
            
        Raises:
            StatisticalAnalysisError: If similarity calculation fails
        """
        if similarity_threshold is None:
            similarity_threshold = self.similarity_threshold
        
        try:
            # Get all unique compositions from historical data
            all_compositions = self._get_all_historical_compositions()
            
            similar_compositions = []
            
            for other_composition in all_compositions:
                if other_composition.composition_id == composition.composition_id:
                    continue
                
                # Calculate similarity
                similarity_score = self._calculate_composition_similarity(composition, other_composition)
                
                if similarity_score >= similarity_threshold:
                    # Get match count for this composition
                    matches = self._find_composition_matches(other_composition)
                    
                    # Determine matching elements
                    matching_elements = self._identify_matching_elements(composition, other_composition)
                    
                    similar_compositions.append(CompositionSimilarity(
                        composition_id=other_composition.composition_id,
                        similarity_score=similarity_score,
                        matching_elements=matching_elements,
                        total_matches=len(matches)
                    ))
            
            # Sort by similarity score (descending)
            similar_compositions.sort(key=lambda x: x.similarity_score, reverse=True)
            
            self.logger.info(f"Found {len(similar_compositions)} similar compositions")
            return similar_compositions
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to find similar compositions: {e}")
    
    def calculate_synergy_matrix(self, player_puuids: List[str]) -> Dict[Tuple[str, str], float]:
        """
        Calculate synergy matrix for player pairings.
        
        Args:
            player_puuids: List of player PUUIDs to analyze
            
        Returns:
            Dictionary mapping player pairs to synergy scores
            
        Raises:
            StatisticalAnalysisError: If calculation fails
        """
        try:
            synergy_matrix = {}
            
            # Calculate synergy for all player pairs
            for i, puuid1 in enumerate(player_puuids):
                for j, puuid2 in enumerate(player_puuids):
                    if i >= j:  # Skip self and duplicate pairs
                        continue
                    
                    # Check cache first
                    cached_synergy = self.composition_cache.get_similarity(puuid1, puuid2)
                    if cached_synergy is not None:
                        synergy_matrix[(puuid1, puuid2)] = cached_synergy
                        continue
                    
                    # Calculate synergy between players
                    synergy_score = self._calculate_player_synergy(puuid1, puuid2)
                    synergy_matrix[(puuid1, puuid2)] = synergy_score
                    
                    # Cache the result
                    self.composition_cache.cache_similarity(puuid1, puuid2, synergy_score)
            
            self.logger.info(f"Calculated synergy matrix for {len(player_puuids)} players")
            return synergy_matrix
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to calculate synergy matrix: {e}")
    
    def identify_optimal_compositions(self, player_pool: List[str], 
                                    constraints: CompositionConstraints) -> List[OptimalComposition]:
        """
        Identify optimal team compositions from a player pool.
        
        Args:
            player_pool: List of available player PUUIDs
            constraints: Constraints for composition generation
            
        Returns:
            List of optimal compositions sorted by expected performance
            
        Raises:
            StatisticalAnalysisError: If optimization fails
            DataValidationError: If constraints are invalid
        """
        if len(player_pool) < 5:
            raise DataValidationError("Player pool must have at least 5 players")
        
        try:
            optimal_compositions = []
            
            # Generate possible compositions based on constraints
            possible_compositions = self._generate_possible_compositions(player_pool, constraints)
            
            if not possible_compositions:
                self.logger.warning("No valid compositions found with given constraints")
                return []
            
            # Analyze each possible composition
            for composition in possible_compositions:
                try:
                    # Get historical performance if available
                    historical_matches = self._find_composition_matches(composition)
                    
                    if len(historical_matches) >= self.min_games_for_analysis:
                        # Use historical data
                        performance_analysis = self.analyze_composition_performance(composition)
                        expected_performance = performance_analysis.performance
                        confidence_score = self._calculate_historical_confidence(len(historical_matches))
                        synergy_score = performance_analysis.synergy_effects.overall_synergy if performance_analysis.synergy_effects else 0.0
                        reasoning = self._generate_historical_reasoning(composition, performance_analysis, len(historical_matches))
                    else:
                        # Estimate performance from individual baselines and synergies
                        expected_performance = self._estimate_composition_performance(composition)
                        confidence_score = self._calculate_estimation_confidence(composition)
                        synergy_score = self._estimate_composition_synergy(composition)
                        reasoning = self._generate_estimation_reasoning(composition, expected_performance, synergy_score)
                    
                    # Apply constraint filters
                    if synergy_score < constraints.min_synergy_score:
                        continue
                    
                    # Calculate risk score based on constraints
                    risk_score = self._calculate_composition_risk(composition, expected_performance, confidence_score)
                    if risk_score > constraints.max_risk_tolerance:
                        continue
                    
                    optimal_compositions.append(OptimalComposition(
                        composition=composition,
                        expected_performance=expected_performance,
                        confidence_score=confidence_score,
                        historical_sample_size=len(historical_matches),
                        synergy_score=synergy_score,
                        reasoning=reasoning
                    ))
                    
                except InsufficientDataError:
                    # Skip compositions without enough data
                    continue
            
            # Enhanced sorting with multiple criteria
            optimal_compositions.sort(
                key=lambda x: (
                    x.expected_performance.win_rate * 0.4 +  # Win rate weight
                    x.synergy_score * 0.3 +                 # Synergy weight
                    x.confidence_score * 0.3                # Confidence weight
                ),
                reverse=True
            )
            
            # Limit results to top compositions
            max_results = 10
            optimal_compositions = optimal_compositions[:max_results]
            
            self.logger.info(f"Identified {len(optimal_compositions)} optimal compositions")
            return optimal_compositions
            
        except Exception as e:
            if isinstance(e, DataValidationError):
                raise
            raise StatisticalAnalysisError(f"Failed to identify optimal compositions: {e}")
    
    def generate_alternative_compositions(self, primary_composition: TeamComposition, 
                                        player_pool: List[str], 
                                        constraints: CompositionConstraints,
                                        max_alternatives: int = 5) -> List[OptimalComposition]:
        """
        Generate alternative team compositions to a primary composition.
        
        Args:
            primary_composition: The primary composition to generate alternatives for
            player_pool: List of available player PUUIDs
            constraints: Constraints for composition generation
            max_alternatives: Maximum number of alternatives to generate
            
        Returns:
            List of alternative compositions sorted by expected performance
            
        Raises:
            StatisticalAnalysisError: If generation fails
            DataValidationError: If constraints are invalid
        """
        try:
            alternatives = []
            
            # Strategy 1: Role swapping within existing players
            role_swap_alternatives = self._generate_role_swap_alternatives(
                primary_composition, constraints
            )
            alternatives.extend(role_swap_alternatives)
            
            # Strategy 2: Player substitution
            if len(player_pool) > 5:
                substitution_alternatives = self._generate_substitution_alternatives(
                    primary_composition, player_pool, constraints
                )
                alternatives.extend(substitution_alternatives)
            
            # Strategy 3: Champion variation for same players
            champion_alternatives = self._generate_champion_alternatives(
                primary_composition, constraints
            )
            alternatives.extend(champion_alternatives)
            
            # Strategy 4: Synergy-optimized alternatives
            synergy_alternatives = self._generate_synergy_optimized_alternatives(
                primary_composition, player_pool, constraints
            )
            alternatives.extend(synergy_alternatives)
            
            # Remove duplicates and primary composition
            unique_alternatives = []
            seen_compositions = {primary_composition.composition_id}
            
            for alt in alternatives:
                if alt.composition.composition_id not in seen_compositions:
                    unique_alternatives.append(alt)
                    seen_compositions.add(alt.composition.composition_id)
            
            # Sort by performance and limit results
            unique_alternatives.sort(
                key=lambda x: (
                    x.expected_performance.win_rate * 0.4 +
                    x.synergy_score * 0.3 +
                    x.confidence_score * 0.3
                ),
                reverse=True
            )
            
            result = unique_alternatives[:max_alternatives]
            
            self.logger.info(f"Generated {len(result)} alternative compositions")
            return result
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to generate alternative compositions: {e}")
    
    def generate_composition_explanation(self, composition: OptimalComposition) -> Dict[str, Any]:
        """
        Generate detailed explanation for why a composition is recommended.
        
        Args:
            composition: The composition to explain
            
        Returns:
            Dictionary containing detailed explanation components
        """
        try:
            explanation = {
                "overall_assessment": self._generate_overall_assessment(composition),
                "performance_analysis": self._generate_performance_explanation(composition),
                "synergy_analysis": self._generate_synergy_explanation(composition),
                "individual_contributions": self._generate_individual_explanations(composition),
                "risk_assessment": self._generate_risk_explanation(composition),
                "recommendations": self._generate_improvement_recommendations(composition),
                "confidence_factors": self._generate_confidence_explanation(composition)
            }
            
            return explanation
            
        except Exception as e:
            self.logger.error(f"Failed to generate composition explanation: {e}")
            return {"error": f"Failed to generate explanation: {e}"}
    
    def _find_composition_matches(self, composition: TeamComposition) -> List[Tuple[Match, Dict[str, MatchParticipant]]]:
        """Find historical matches that match the given composition."""
        matching_matches = []
        
        # Get all matches for players in the composition
        all_player_matches = {}
        for role, assignment in composition.players.items():
            player_matches = self.match_manager.get_matches_for_player(assignment.puuid)
            all_player_matches[assignment.puuid] = player_matches
        
        # Find matches where all players played together with specified champions/roles
        if not all_player_matches:
            return matching_matches
        
        # Get matches from the first player as a starting point
        first_player_puuid = list(composition.players.values())[0].puuid
        candidate_matches = all_player_matches[first_player_puuid]
        
        for match in candidate_matches:
            # Check if this match contains all players in the composition
            match_participants = {p.puuid: p for p in match.participants}
            
            composition_match = True
            match_assignments = {}
            
            for role, assignment in composition.players.items():
                if assignment.puuid not in match_participants:
                    composition_match = False
                    break
                
                participant = match_participants[assignment.puuid]
                
                # Check if champion and role match (if specified)
                if assignment.champion_id != participant.champion_id:
                    composition_match = False
                    break
                
                # Normalize and check role
                participant_role = self._normalize_role(participant.individual_position)
                if assignment.role != participant_role:
                    composition_match = False
                    break
                
                match_assignments[assignment.puuid] = participant
            
            if composition_match and len(match_assignments) == len(composition.players):
                matching_matches.append((match, match_assignments))
        
        return matching_matches
    
    def _calculate_composition_metrics(self, matches: List[Tuple[Match, Dict[str, MatchParticipant]]]) -> PerformanceMetrics:
        """Calculate performance metrics for a composition from historical matches."""
        if not matches:
            return PerformanceMetrics()
        
        total_games = len(matches)
        total_wins = 0
        total_kills = 0
        total_deaths = 0
        total_assists = 0
        total_cs = 0
        total_vision = 0
        total_damage = 0
        total_gold = 0
        total_duration = 0
        
        for match, participants in matches:
            # Determine if team won (check any participant's win status)
            team_won = any(p.win for p in participants.values())
            if team_won:
                total_wins += 1
            
            # Aggregate team stats
            match_kills = sum(p.kills for p in participants.values())
            match_deaths = sum(p.deaths for p in participants.values())
            match_assists = sum(p.assists for p in participants.values())
            match_cs = sum(p.cs_total for p in participants.values())
            match_vision = sum(p.vision_score for p in participants.values())
            match_damage = sum(p.total_damage_dealt_to_champions for p in participants.values())
            match_gold = sum(p.gold_earned for p in participants.values())
            
            total_kills += match_kills
            total_deaths += match_deaths
            total_assists += match_assists
            total_cs += match_cs
            total_vision += match_vision
            total_damage += match_damage
            total_gold += match_gold
            total_duration += match.game_duration
        
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
    
    def _calculate_baseline_deltas(self, composition: TeamComposition, 
                                 matches: List[Tuple[Match, Dict[str, MatchParticipant]]]) -> Dict[str, Dict[str, PerformanceDelta]]:
        """Calculate performance deltas compared to individual baselines."""
        baseline_deltas = {}
        
        for role, assignment in composition.players.items():
            try:
                # Get player's baseline for this champion/role
                baseline = self.baseline_manager.get_champion_specific_baseline(
                    assignment.puuid, assignment.champion_id, assignment.role
                )
                
                # Calculate actual performance in these matches
                player_matches = [(match, participants[assignment.puuid]) 
                                for match, participants in matches 
                                if assignment.puuid in participants]
                
                if player_matches:
                    actual_performance = self._calculate_player_performance_in_matches(player_matches)
                    deltas = self.baseline_manager.calculate_performance_delta(actual_performance, baseline)
                    baseline_deltas[assignment.puuid] = deltas
                
            except InsufficientDataError:
                # Skip players without sufficient baseline data
                self.logger.debug(f"Insufficient baseline data for {assignment.puuid}")
                continue
        
        return baseline_deltas
    
    def _calculate_synergy_effects(self, composition: TeamComposition, 
                                 matches: List[Tuple[Match, Dict[str, MatchParticipant]]],
                                 baseline_deltas: Dict[str, Dict[str, PerformanceDelta]]) -> SynergyEffects:
        """Calculate synergy effects for the composition."""
        if not baseline_deltas:
            return SynergyEffects(overall_synergy=0.0)
        
        # Calculate overall synergy from performance deltas
        win_rate_deltas = []
        for puuid, deltas in baseline_deltas.items():
            if 'win_rate' in deltas:
                win_rate_deltas.append(deltas['win_rate'].delta_percentage)
        
        overall_synergy = statistics.mean(win_rate_deltas) / 100.0 if win_rate_deltas else 0.0
        overall_synergy = max(-1.0, min(1.0, overall_synergy))  # Clamp to [-1, 1]
        
        # Calculate role pair synergies
        role_pair_synergies = {}
        roles = list(composition.players.keys())
        for i, role1 in enumerate(roles):
            for j, role2 in enumerate(roles):
                if i >= j:
                    continue
                
                puuid1 = composition.players[role1].puuid
                puuid2 = composition.players[role2].puuid
                
                # Calculate synergy between these two players
                pair_synergy = self._calculate_player_synergy(puuid1, puuid2)
                role_pair_synergies[(role1, role2)] = pair_synergy
        
        # Calculate champion synergies
        champion_synergies = {}
        champion_ids = [assignment.champion_id for assignment in composition.players.values()]
        for i, champ1 in enumerate(champion_ids):
            for j, champ2 in enumerate(champion_ids):
                if i >= j:
                    continue
                
                # Simplified champion synergy calculation
                synergy_score = self._calculate_champion_synergy(champ1, champ2)
                champion_synergies[(champ1, champ2)] = synergy_score
        
        # Calculate player synergies
        player_synergies = {}
        puuids = [assignment.puuid for assignment in composition.players.values()]
        for i, puuid1 in enumerate(puuids):
            for j, puuid2 in enumerate(puuids):
                if i >= j:
                    continue
                
                synergy_score = self._calculate_player_synergy(puuid1, puuid2)
                player_synergies[(puuid1, puuid2)] = synergy_score
        
        return SynergyEffects(
            overall_synergy=overall_synergy,
            role_pair_synergies=role_pair_synergies,
            champion_synergies=champion_synergies,
            player_synergies=player_synergies
        )
    
    def _test_composition_significance(self, matches: List[Tuple[Match, Dict[str, MatchParticipant]]],
                                    baseline_deltas: Dict[str, Dict[str, PerformanceDelta]]) -> Optional[SignificanceTest]:
        """Test statistical significance of composition effects."""
        if not baseline_deltas or len(matches) < 3:
            return None
        
        try:
            # Collect win rate deltas for significance testing
            win_rate_deltas = []
            for puuid, deltas in baseline_deltas.items():
                if 'win_rate' in deltas:
                    win_rate_deltas.append(deltas['win_rate'].delta_absolute)
            
            if len(win_rate_deltas) < 2:
                return None
            
            # Perform one-sample t-test against zero (no effect)
            significance_test = self.statistical_analyzer.perform_one_sample_test(
                sample=win_rate_deltas,
                expected_value=0.0,
                test_type="t_test",
                alternative="two-sided"
            )
            
            return significance_test
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate significance test: {e}")
            return None
    
    def _calculate_composition_confidence_interval(self, matches: List[Tuple[Match, Dict[str, MatchParticipant]]]) -> ConfidenceInterval:
        """Calculate confidence interval for composition win rate."""
        if not matches:
            return ConfidenceInterval(0.0, 0.0, 0.95, 0)
        
        wins = sum(1 for match, participants in matches if any(p.win for p in participants.values()))
        total_games = len(matches)
        
        # Use Wilson score interval for proportions
        win_rates = [1.0 if any(p.win for p in participants.values()) else 0.0 
                    for match, participants in matches]
        
        try:
            confidence_interval = self.statistical_analyzer.calculate_confidence_interval(
                data=win_rates,
                confidence_level=self.confidence_level,
                method=self.statistical_analyzer.ConfidenceIntervalMethod.WILSON
            )
            return confidence_interval
        except Exception as e:
            self.logger.warning(f"Failed to calculate confidence interval: {e}")
            return ConfidenceInterval(0.0, 1.0, self.confidence_level, total_games)
    
    def _get_all_historical_compositions(self) -> List[TeamComposition]:
        """Get all unique team compositions from historical data."""
        compositions = []
        composition_ids_seen = set()
        
        # This is a simplified implementation
        # In practice, you'd want to efficiently extract compositions from match data
        all_matches = self.match_manager.get_all_matches()
        
        for match in all_matches:
            if len(match.participants) != 10:  # Skip non-standard matches
                continue
            
            # Group participants by team
            team1_participants = [p for p in match.participants if p.team_id == 100]
            team2_participants = [p for p in match.participants if p.team_id == 200]
            
            for team_participants in [team1_participants, team2_participants]:
                if len(team_participants) != 5:
                    continue
                
                # Create composition from team
                players = {}
                for participant in team_participants:
                    role = self._normalize_role(participant.individual_position)
                    if role and role not in players:  # Avoid duplicate roles
                        players[role] = PlayerRoleAssignment(
                            puuid=participant.puuid,
                            player_name=participant.summoner_name or "Unknown",
                            role=role,
                            champion_id=participant.champion_id,
                            champion_name=participant.champion_name or f"Champion_{participant.champion_id}"
                        )
                
                if len(players) == 5:  # Complete team
                    composition = TeamComposition(players=players)
                    
                    if composition.composition_id not in composition_ids_seen:
                        compositions.append(composition)
                        composition_ids_seen.add(composition.composition_id)
        
        return compositions
    
    def _calculate_composition_similarity(self, comp1: TeamComposition, comp2: TeamComposition) -> float:
        """Calculate similarity score between two compositions."""
        # Check cache first
        cached_similarity = self.composition_cache.get_similarity(comp1.composition_id, comp2.composition_id)
        if cached_similarity is not None:
            return cached_similarity
        
        similarity_score = 0.0
        total_weight = 0.0
        
        # Player similarity (40% weight)
        player_weight = 0.4
        matching_players = 0
        for role in comp1.players:
            if role in comp2.players:
                if comp1.players[role].puuid == comp2.players[role].puuid:
                    matching_players += 1
        player_similarity = matching_players / 5.0
        similarity_score += player_similarity * player_weight
        total_weight += player_weight
        
        # Champion similarity (35% weight)
        champion_weight = 0.35
        matching_champions = 0
        comp1_champions = set(assignment.champion_id for assignment in comp1.players.values())
        comp2_champions = set(assignment.champion_id for assignment in comp2.players.values())
        matching_champions = len(comp1_champions.intersection(comp2_champions))
        champion_similarity = matching_champions / 5.0
        similarity_score += champion_similarity * champion_weight
        total_weight += champion_weight
        
        # Role similarity (25% weight)
        role_weight = 0.25
        matching_roles = 0
        for role in comp1.players:
            if role in comp2.players:
                if (comp1.players[role].champion_id == comp2.players[role].champion_id and
                    comp1.players[role].puuid == comp2.players[role].puuid):
                    matching_roles += 1
        role_similarity = matching_roles / 5.0
        similarity_score += role_similarity * role_weight
        total_weight += role_weight
        
        final_similarity = similarity_score / total_weight if total_weight > 0 else 0.0
        
        # Cache the result
        self.composition_cache.cache_similarity(comp1.composition_id, comp2.composition_id, final_similarity)
        
        return final_similarity
    
    def _identify_matching_elements(self, comp1: TeamComposition, comp2: TeamComposition) -> Dict[str, Any]:
        """Identify what elements match between two compositions."""
        matching_elements = {
            "matching_players": [],
            "matching_champions": [],
            "matching_role_assignments": [],
            "common_champion_pool": []
        }
        
        # Matching players
        for role in comp1.players:
            if role in comp2.players:
                if comp1.players[role].puuid == comp2.players[role].puuid:
                    matching_elements["matching_players"].append({
                        "role": role,
                        "puuid": comp1.players[role].puuid,
                        "player_name": comp1.players[role].player_name
                    })
        
        # Matching champions
        comp1_champions = {assignment.champion_id for assignment in comp1.players.values()}
        comp2_champions = {assignment.champion_id for assignment in comp2.players.values()}
        matching_elements["matching_champions"] = list(comp1_champions.intersection(comp2_champions))
        
        # Matching role assignments (same player, same champion, same role)
        for role in comp1.players:
            if role in comp2.players:
                if (comp1.players[role].puuid == comp2.players[role].puuid and
                    comp1.players[role].champion_id == comp2.players[role].champion_id):
                    matching_elements["matching_role_assignments"].append({
                        "role": role,
                        "puuid": comp1.players[role].puuid,
                        "champion_id": comp1.players[role].champion_id
                    })
        
        # Common champion pool
        matching_elements["common_champion_pool"] = list(comp1_champions.union(comp2_champions))
        
        return matching_elements
    
    def _calculate_player_synergy(self, puuid1: str, puuid2: str) -> float:
        """Calculate synergy score between two players."""
        # Get matches where both players played together
        player1_matches = self.match_manager.get_matches_for_player(puuid1)
        player2_matches = self.match_manager.get_matches_for_player(puuid2)
        
        # Find common matches
        common_matches = []
        player1_match_ids = {match.match_id for match in player1_matches}
        
        for match in player2_matches:
            if match.match_id in player1_match_ids:
                # Verify they were on the same team
                p1_participant = match.get_participant_by_puuid(puuid1)
                p2_participant = match.get_participant_by_puuid(puuid2)
                
                if p1_participant and p2_participant and p1_participant.team_id == p2_participant.team_id:
                    common_matches.append(match)
        
        if len(common_matches) < 3:
            return 0.0  # Insufficient data
        
        # Calculate win rate when playing together
        together_wins = sum(1 for match in common_matches 
                          if match.get_participant_by_puuid(puuid1).win)
        together_win_rate = together_wins / len(common_matches)
        
        # Get individual baselines
        try:
            baseline1 = self.baseline_manager.get_overall_baseline(puuid1)
            baseline2 = self.baseline_manager.get_overall_baseline(puuid2)
            
            expected_combined_win_rate = (baseline1.baseline_metrics.win_rate + 
                                        baseline2.baseline_metrics.win_rate) / 2
            
            # Synergy is the difference from expected
            synergy = together_win_rate - expected_combined_win_rate
            
            # Normalize to [-1, 1] range
            return max(-1.0, min(1.0, synergy * 2))  # Scale by 2 for more sensitivity
            
        except InsufficientDataError:
            return 0.0
    
    def _calculate_champion_synergy(self, champion1_id: int, champion2_id: int) -> float:
        """Calculate synergy score between two champions."""
        # This is a simplified implementation
        # In practice, you'd analyze historical data for champion combinations
        
        # Get all matches where these champions were on the same team
        all_matches = self.match_manager.get_all_matches()
        synergy_matches = []
        
        for match in all_matches:
            team1_champions = [p.champion_id for p in match.participants if p.team_id == 100]
            team2_champions = [p.champion_id for p in match.participants if p.team_id == 200]
            
            if champion1_id in team1_champions and champion2_id in team1_champions:
                team_won = any(p.win for p in match.participants if p.team_id == 100)
                synergy_matches.append(team_won)
            elif champion1_id in team2_champions and champion2_id in team2_champions:
                team_won = any(p.win for p in match.participants if p.team_id == 200)
                synergy_matches.append(team_won)
        
        if len(synergy_matches) < 5:
            return 0.0  # Insufficient data
        
        # Calculate win rate for this champion combination
        combo_win_rate = sum(synergy_matches) / len(synergy_matches)
        
        # Compare to average win rate (simplified)
        average_win_rate = 0.5  # Assume 50% baseline
        synergy = combo_win_rate - average_win_rate
        
        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, synergy * 2))
    
    def _generate_possible_compositions(self, player_pool: List[str], 
                                      constraints: CompositionConstraints) -> List[TeamComposition]:
        """Generate possible team compositions from player pool."""
        possible_compositions = []
        
        # Define roles
        roles = ["top", "jungle", "middle", "support", "bottom"]
        
        # Apply required players constraint
        if constraints.required_players:
            fixed_assignments = constraints.required_players
            remaining_roles = [role for role in roles if role not in fixed_assignments]
            remaining_players = [puuid for puuid in player_pool 
                               if puuid not in fixed_assignments.values()]
        else:
            fixed_assignments = {}
            remaining_roles = roles
            remaining_players = player_pool
        
        # Generate combinations for remaining roles
        if len(remaining_players) >= len(remaining_roles):
            for player_combination in itertools.permutations(remaining_players, len(remaining_roles)):
                players = {}
                
                # Add fixed assignments
                for role, puuid in fixed_assignments.items():
                    # Get available champions for this player
                    available_champions = self._get_available_champions_for_player(
                        puuid, role, constraints
                    )
                    if available_champions:
                        # Use the first available champion (simplified)
                        champion_id = available_champions[0]
                        players[role] = PlayerRoleAssignment(
                            puuid=puuid,
                            player_name=f"Player_{puuid[:8]}",
                            role=role,
                            champion_id=champion_id,
                            champion_name=f"Champion_{champion_id}"
                        )
                
                # Add remaining assignments
                for i, puuid in enumerate(player_combination):
                    role = remaining_roles[i]
                    available_champions = self._get_available_champions_for_player(
                        puuid, role, constraints
                    )
                    if available_champions:
                        champion_id = available_champions[0]
                        players[role] = PlayerRoleAssignment(
                            puuid=puuid,
                            player_name=f"Player_{puuid[:8]}",
                            role=role,
                            champion_id=champion_id,
                            champion_name=f"Champion_{champion_id}"
                        )
                
                if len(players) == 5:
                    composition = TeamComposition(players=players)
                    possible_compositions.append(composition)
                
                # Limit to prevent excessive combinations
                if len(possible_compositions) >= 100:
                    break
        
        return possible_compositions
    
    def _get_available_champions_for_player(self, puuid: str, role: str, 
                                          constraints: CompositionConstraints) -> List[int]:
        """Get available champions for a player in a specific role."""
        # Start with all champions if no constraints
        if constraints.available_champions and puuid in constraints.available_champions:
            available = constraints.available_champions[puuid]
        else:
            # Get champions this player has played in this role
            player_matches = self.match_manager.get_matches_for_player(puuid)
            role_champions = set()
            
            for match in player_matches:
                participant = match.get_participant_by_puuid(puuid)
                if participant and self._normalize_role(participant.individual_position) == role:
                    role_champions.add(participant.champion_id)
            
            available = list(role_champions) if role_champions else [1]  # Default champion
        
        # Remove banned champions
        if constraints.banned_champions:
            available = [champ_id for champ_id in available 
                        if champ_id not in constraints.banned_champions]
        
        return available
    
    def _estimate_composition_performance(self, composition: TeamComposition) -> PerformanceMetrics:
        """Estimate composition performance from individual baselines."""
        estimated_metrics = PerformanceMetrics()
        
        total_win_rate = 0.0
        total_kda = 0.0
        total_cs_per_min = 0.0
        total_vision = 0.0
        total_damage_per_min = 0.0
        total_gold_per_min = 0.0
        valid_players = 0
        
        for role, assignment in composition.players.items():
            try:
                baseline = self.baseline_manager.get_champion_specific_baseline(
                    assignment.puuid, assignment.champion_id, assignment.role
                )
                
                total_win_rate += baseline.baseline_metrics.win_rate
                total_kda += baseline.baseline_metrics.avg_kda
                total_cs_per_min += baseline.baseline_metrics.avg_cs_per_min
                total_vision += baseline.baseline_metrics.avg_vision_score
                total_damage_per_min += baseline.baseline_metrics.avg_damage_per_min
                total_gold_per_min += baseline.baseline_metrics.avg_gold_per_min
                valid_players += 1
                
            except InsufficientDataError:
                # Use default values for players without baselines
                total_win_rate += 0.5  # 50% win rate
                total_kda += 2.0  # Default KDA
                total_cs_per_min += 6.0  # Default CS/min
                total_vision += 20.0  # Default vision score
                total_damage_per_min += 500.0  # Default damage/min
                total_gold_per_min += 350.0  # Default gold/min
                valid_players += 1
        
        if valid_players > 0:
            estimated_metrics.win_rate = total_win_rate / valid_players
            estimated_metrics.avg_kda = total_kda / valid_players
            estimated_metrics.avg_cs_per_min = total_cs_per_min / valid_players
            estimated_metrics.avg_vision_score = total_vision / valid_players
            estimated_metrics.avg_damage_per_min = total_damage_per_min / valid_players
            estimated_metrics.avg_gold_per_min = total_gold_per_min / valid_players
            estimated_metrics.games_played = 1  # Estimated
        
        return estimated_metrics
    
    def _calculate_historical_confidence(self, sample_size: int) -> float:
        """Calculate confidence score based on historical sample size."""
        # Confidence increases with sample size, capped at 1.0
        return min(1.0, sample_size / 20.0)
    
    def _calculate_estimation_confidence(self, composition: TeamComposition) -> float:
        """Calculate confidence score for estimated performance."""
        # Lower confidence for estimated performance
        baseline_confidence = 0.0
        valid_baselines = 0
        
        for role, assignment in composition.players.items():
            try:
                baseline = self.baseline_manager.get_champion_specific_baseline(
                    assignment.puuid, assignment.champion_id, assignment.role
                )
                baseline_confidence += baseline.reliability_score
                valid_baselines += 1
            except InsufficientDataError:
                baseline_confidence += 0.1  # Low confidence for missing baselines
                valid_baselines += 1
        
        if valid_baselines > 0:
            avg_confidence = baseline_confidence / valid_baselines
            return min(0.7, avg_confidence)  # Cap estimated confidence at 70%
        
        return 0.1  # Very low confidence if no baselines
    
    def _estimate_composition_synergy(self, composition: TeamComposition) -> float:
        """Estimate synergy score for a composition."""
        synergy_scores = []
        
        puuids = [assignment.puuid for assignment in composition.players.values()]
        for i, puuid1 in enumerate(puuids):
            for j, puuid2 in enumerate(puuids):
                if i >= j:
                    continue
                
                synergy = self._calculate_player_synergy(puuid1, puuid2)
                synergy_scores.append(synergy)
        
        return statistics.mean(synergy_scores) if synergy_scores else 0.0
    
    def _calculate_player_performance_in_matches(self, matches: List[Tuple[Match, MatchParticipant]]) -> PerformanceMetrics:
        """Calculate performance metrics for a player in specific matches."""
        if not matches:
            return PerformanceMetrics()
        
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
        avg_game_duration = total_duration / (total_games * 60)
        
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
    
    def _normalize_role(self, position: str) -> str:
        """Normalize position string to standard role."""
        if not position:
            return ""
        
        position_lower = position.lower()
        
        # Map various position strings to standard roles
        role_mapping = {
            'top': 'top',
            'jungle': 'jungle',
            'middle': 'middle',
            'mid': 'middle',
            'bottom': 'bottom',
            'bot': 'bottom',
            'adc': 'bottom',
            'support': 'support',
            'supp': 'support'
        }
        
        return role_mapping.get(position_lower, position_lower)
    
    def _generate_historical_reasoning(self, composition: TeamComposition, 
                                     performance_analysis: CompositionPerformance,
                                     sample_size: int) -> List[str]:
        """Generate reasoning based on historical performance data."""
        reasoning = []
        
        # Sample size assessment
        if sample_size >= 10:
            reasoning.append(f"Strong historical evidence with {sample_size} matches")
        elif sample_size >= 5:
            reasoning.append(f"Moderate historical evidence with {sample_size} matches")
        else:
            reasoning.append(f"Limited historical evidence with {sample_size} matches")
        
        # Performance assessment
        win_rate = performance_analysis.performance.win_rate
        if win_rate >= 0.65:
            reasoning.append(f"Excellent historical win rate of {win_rate:.1%}")
        elif win_rate >= 0.55:
            reasoning.append(f"Good historical win rate of {win_rate:.1%}")
        elif win_rate >= 0.45:
            reasoning.append(f"Average historical win rate of {win_rate:.1%}")
        else:
            reasoning.append(f"Below-average historical win rate of {win_rate:.1%}")
        
        # Synergy assessment
        if performance_analysis.synergy_effects:
            synergy = performance_analysis.synergy_effects.overall_synergy
            if synergy > 0.1:
                reasoning.append("Strong positive team synergy observed")
            elif synergy > 0.05:
                reasoning.append("Moderate positive team synergy observed")
            elif synergy < -0.1:
                reasoning.append("Negative team synergy detected - consider alternatives")
            else:
                reasoning.append("Neutral team synergy")
        
        # Statistical significance
        if performance_analysis.statistical_significance and performance_analysis.statistical_significance.p_value < 0.05:
            reasoning.append("Performance difference is statistically significant")
        
        return reasoning
    
    def _generate_estimation_reasoning(self, composition: TeamComposition, 
                                     expected_performance: PerformanceMetrics,
                                     synergy_score: float) -> List[str]:
        """Generate reasoning based on estimated performance."""
        reasoning = []
        
        reasoning.append("Performance estimated from individual player baselines")
        
        # Individual performance assessment
        win_rate = expected_performance.win_rate
        if win_rate >= 0.6:
            reasoning.append(f"High expected win rate of {win_rate:.1%} based on player strengths")
        elif win_rate >= 0.5:
            reasoning.append(f"Balanced expected win rate of {win_rate:.1%}")
        else:
            reasoning.append(f"Lower expected win rate of {win_rate:.1%} - consider player development")
        
        # Synergy assessment
        if synergy_score > 0.1:
            reasoning.append("Players have shown strong synergy in past matches")
        elif synergy_score > 0.05:
            reasoning.append("Players have moderate synergy potential")
        elif synergy_score < -0.05:
            reasoning.append("Players may have synergy challenges - monitor closely")
        else:
            reasoning.append("Neutral synergy expected between players")
        
        reasoning.append("Recommendation confidence will improve with more match data")
        
        return reasoning
    
    def _calculate_composition_risk(self, composition: TeamComposition, 
                                  expected_performance: PerformanceMetrics,
                                  confidence_score: float) -> float:
        """Calculate risk score for a composition (0.0 = low risk, 1.0 = high risk)."""
        risk_factors = []
        
        # Performance risk
        if expected_performance.win_rate < 0.45:
            risk_factors.append(0.3)  # High performance risk
        elif expected_performance.win_rate < 0.5:
            risk_factors.append(0.15)  # Moderate performance risk
        else:
            risk_factors.append(0.0)  # Low performance risk
        
        # Confidence risk (inverse of confidence)
        confidence_risk = 1.0 - confidence_score
        risk_factors.append(confidence_risk * 0.4)
        
        # Role familiarity risk
        role_risk = 0.0
        for role, assignment in composition.players.items():
            try:
                # Check if player has experience in this role
                player_matches = self.match_manager.get_matches_for_player(assignment.puuid)
                role_matches = [m for m in player_matches 
                              if any(p.puuid == assignment.puuid and 
                                   self._normalize_role(p.individual_position) == role 
                                   for p in m.participants)]
                
                if len(role_matches) < 5:
                    role_risk += 0.1  # Risk for unfamiliar role
                    
            except Exception:
                role_risk += 0.1
        
        risk_factors.append(min(0.3, role_risk))
        
        # Calculate overall risk
        total_risk = sum(risk_factors)
        return min(1.0, total_risk)
    
    def _generate_role_swap_alternatives(self, primary_composition: TeamComposition,
                                       constraints: CompositionConstraints) -> List[OptimalComposition]:
        """Generate alternatives by swapping player roles."""
        alternatives = []
        
        # Get players who can play multiple roles
        flexible_players = {}
        for role, assignment in primary_composition.players.items():
            player_roles = self._get_player_roles(assignment.puuid)
            if len(player_roles) > 1:
                flexible_players[assignment.puuid] = player_roles
        
        # Generate role swap combinations
        if len(flexible_players) >= 2:
            player_pairs = list(itertools.combinations(flexible_players.keys(), 2))
            
            for puuid1, puuid2 in player_pairs[:3]:  # Limit to 3 combinations
                # Find current roles
                current_role1 = None
                current_role2 = None
                
                for role, assignment in primary_composition.players.items():
                    if assignment.puuid == puuid1:
                        current_role1 = role
                    elif assignment.puuid == puuid2:
                        current_role2 = role
                
                if current_role1 and current_role2:
                    # Check if swap is valid
                    if (current_role2 in flexible_players[puuid1] and 
                        current_role1 in flexible_players[puuid2]):
                        
                        # Create swapped composition
                        swapped_composition = self._create_role_swapped_composition(
                            primary_composition, puuid1, puuid2, current_role1, current_role2
                        )
                        
                        if swapped_composition:
                            # Analyze the swapped composition
                            alt_composition = self._analyze_alternative_composition(
                                swapped_composition, "Role swap optimization"
                            )
                            if alt_composition:
                                alternatives.append(alt_composition)
        
        return alternatives
    
    def _generate_substitution_alternatives(self, primary_composition: TeamComposition,
                                          player_pool: List[str],
                                          constraints: CompositionConstraints) -> List[OptimalComposition]:
        """Generate alternatives by substituting players."""
        alternatives = []
        
        # Get players not in primary composition
        primary_players = {assignment.puuid for assignment in primary_composition.players.values()}
        available_substitutes = [p for p in player_pool if p not in primary_players]
        
        if not available_substitutes:
            return alternatives
        
        # Try substituting each position
        for role, assignment in primary_composition.players.items():
            # Find suitable substitutes for this role
            suitable_substitutes = []
            
            for substitute_puuid in available_substitutes:
                substitute_roles = self._get_player_roles(substitute_puuid)
                if role in substitute_roles:
                    suitable_substitutes.append(substitute_puuid)
            
            # Create substitution alternatives (limit to 2 per role)
            for substitute_puuid in suitable_substitutes[:2]:
                substituted_composition = self._create_substituted_composition(
                    primary_composition, role, substitute_puuid
                )
                
                if substituted_composition:
                    alt_composition = self._analyze_alternative_composition(
                        substituted_composition, f"Player substitution in {role}"
                    )
                    if alt_composition:
                        alternatives.append(alt_composition)
        
        return alternatives
    
    def _generate_champion_alternatives(self, primary_composition: TeamComposition,
                                      constraints: CompositionConstraints) -> List[OptimalComposition]:
        """Generate alternatives by changing champion selections."""
        alternatives = []
        
        # Try different champions for each player
        for role, assignment in primary_composition.players.items():
            available_champions = self._get_available_champions_for_player(
                assignment.puuid, role, constraints
            )
            
            # Remove current champion and try alternatives
            alternative_champions = [c for c in available_champions 
                                   if c != assignment.champion_id]
            
            # Create alternatives with different champions (limit to 2 per role)
            for champion_id in alternative_champions[:2]:
                champion_alt_composition = self._create_champion_alternative_composition(
                    primary_composition, role, champion_id
                )
                
                if champion_alt_composition:
                    alt_composition = self._analyze_alternative_composition(
                        champion_alt_composition, f"Champion variation for {role}"
                    )
                    if alt_composition:
                        alternatives.append(alt_composition)
        
        return alternatives
    
    def _generate_synergy_optimized_alternatives(self, primary_composition: TeamComposition,
                                               player_pool: List[str],
                                               constraints: CompositionConstraints) -> List[OptimalComposition]:
        """Generate alternatives optimized for team synergy."""
        alternatives = []
        
        # Calculate current synergy matrix
        primary_players = [assignment.puuid for assignment in primary_composition.players.values()]
        current_synergy = self._estimate_composition_synergy(primary_composition)
        
        # Try to improve synergy by strategic substitutions
        available_players = [p for p in player_pool if p not in primary_players]
        
        if available_players:
            # Find the weakest synergy link in current composition
            weakest_synergy = float('inf')
            weakest_player = None
            
            for puuid in primary_players:
                player_synergy = 0.0
                synergy_count = 0
                
                for other_puuid in primary_players:
                    if puuid != other_puuid:
                        synergy = self._calculate_player_synergy(puuid, other_puuid)
                        player_synergy += synergy
                        synergy_count += 1
                
                avg_synergy = player_synergy / synergy_count if synergy_count > 0 else 0.0
                if avg_synergy < weakest_synergy:
                    weakest_synergy = avg_synergy
                    weakest_player = puuid
            
            # Try replacing the weakest synergy player
            if weakest_player:
                weakest_role = None
                for role, assignment in primary_composition.players.items():
                    if assignment.puuid == weakest_player:
                        weakest_role = role
                        break
                
                if weakest_role:
                    # Find better synergy replacements
                    for substitute_puuid in available_players:
                        substitute_roles = self._get_player_roles(substitute_puuid)
                        if weakest_role in substitute_roles:
                            # Calculate potential synergy improvement
                            potential_synergy = 0.0
                            synergy_count = 0
                            
                            for other_puuid in primary_players:
                                if other_puuid != weakest_player:
                                    synergy = self._calculate_player_synergy(substitute_puuid, other_puuid)
                                    potential_synergy += synergy
                                    synergy_count += 1
                            
                            avg_potential_synergy = potential_synergy / synergy_count if synergy_count > 0 else 0.0
                            
                            # If synergy improvement is significant, create alternative
                            if avg_potential_synergy > weakest_synergy + 0.05:
                                synergy_composition = self._create_substituted_composition(
                                    primary_composition, weakest_role, substitute_puuid
                                )
                                
                                if synergy_composition:
                                    alt_composition = self._analyze_alternative_composition(
                                        synergy_composition, "Synergy optimization"
                                    )
                                    if alt_composition:
                                        alternatives.append(alt_composition)
        
        return alternatives
    
    def _get_player_roles(self, puuid: str) -> List[str]:
        """Get roles that a player has experience in."""
        try:
            player_matches = self.match_manager.get_matches_for_player(puuid)
            role_counts = defaultdict(int)
            
            for match in player_matches:
                participant = match.get_participant_by_puuid(puuid)
                if participant:
                    role = self._normalize_role(participant.individual_position)
                    if role:
                        role_counts[role] += 1
            
            # Return roles with at least 3 games of experience
            experienced_roles = [role for role, count in role_counts.items() if count >= 3]
            return experienced_roles if experienced_roles else ['middle']  # Default role
            
        except Exception:
            return ['middle']  # Default role if error
    
    def _create_role_swapped_composition(self, primary_composition: TeamComposition,
                                       puuid1: str, puuid2: str,
                                       role1: str, role2: str) -> Optional[TeamComposition]:
        """Create a composition with two players' roles swapped."""
        try:
            new_players = {}
            
            for role, assignment in primary_composition.players.items():
                if role == role1:
                    # Assign puuid2 to role1
                    new_players[role] = PlayerRoleAssignment(
                        puuid=puuid2,
                        player_name=f"Player_{puuid2[:8]}",
                        role=role,
                        champion_id=assignment.champion_id,  # Keep same champion for now
                        champion_name=assignment.champion_name
                    )
                elif role == role2:
                    # Assign puuid1 to role2
                    new_players[role] = PlayerRoleAssignment(
                        puuid=puuid1,
                        player_name=f"Player_{puuid1[:8]}",
                        role=role,
                        champion_id=assignment.champion_id,  # Keep same champion for now
                        champion_name=assignment.champion_name
                    )
                else:
                    # Keep original assignment
                    new_players[role] = assignment
            
            return TeamComposition(players=new_players)
            
        except Exception as e:
            self.logger.warning(f"Failed to create role swapped composition: {e}")
            return None
    
    def _create_substituted_composition(self, primary_composition: TeamComposition,
                                      role: str, substitute_puuid: str) -> Optional[TeamComposition]:
        """Create a composition with a player substituted in a specific role."""
        try:
            new_players = {}
            
            for comp_role, assignment in primary_composition.players.items():
                if comp_role == role:
                    # Substitute the player
                    available_champions = self._get_available_champions_for_player(
                        substitute_puuid, role, CompositionConstraints()
                    )
                    champion_id = available_champions[0] if available_champions else 1
                    
                    new_players[comp_role] = PlayerRoleAssignment(
                        puuid=substitute_puuid,
                        player_name=f"Player_{substitute_puuid[:8]}",
                        role=role,
                        champion_id=champion_id,
                        champion_name=f"Champion_{champion_id}"
                    )
                else:
                    # Keep original assignment
                    new_players[comp_role] = assignment
            
            return TeamComposition(players=new_players)
            
        except Exception as e:
            self.logger.warning(f"Failed to create substituted composition: {e}")
            return None
    
    def _create_champion_alternative_composition(self, primary_composition: TeamComposition,
                                               role: str, champion_id: int) -> Optional[TeamComposition]:
        """Create a composition with a different champion for a specific role."""
        try:
            new_players = {}
            
            for comp_role, assignment in primary_composition.players.items():
                if comp_role == role:
                    # Change the champion
                    new_players[comp_role] = PlayerRoleAssignment(
                        puuid=assignment.puuid,
                        player_name=assignment.player_name,
                        role=role,
                        champion_id=champion_id,
                        champion_name=f"Champion_{champion_id}"
                    )
                else:
                    # Keep original assignment
                    new_players[comp_role] = assignment
            
            return TeamComposition(players=new_players)
            
        except Exception as e:
            self.logger.warning(f"Failed to create champion alternative composition: {e}")
            return None
    
    def _analyze_alternative_composition(self, composition: TeamComposition,
                                       strategy: str) -> Optional[OptimalComposition]:
        """Analyze an alternative composition and return OptimalComposition if viable."""
        try:
            # Get historical performance if available
            historical_matches = self._find_composition_matches(composition)
            
            if len(historical_matches) >= self.min_games_for_analysis:
                # Use historical data
                performance_analysis = self.analyze_composition_performance(composition)
                expected_performance = performance_analysis.performance
                confidence_score = self._calculate_historical_confidence(len(historical_matches))
                synergy_score = performance_analysis.synergy_effects.overall_synergy if performance_analysis.synergy_effects else 0.0
                reasoning = self._generate_historical_reasoning(composition, performance_analysis, len(historical_matches))
            else:
                # Estimate performance
                expected_performance = self._estimate_composition_performance(composition)
                confidence_score = self._calculate_estimation_confidence(composition)
                synergy_score = self._estimate_composition_synergy(composition)
                reasoning = self._generate_estimation_reasoning(composition, expected_performance, synergy_score)
            
            # Add strategy to reasoning
            reasoning.insert(0, f"Generated using {strategy}")
            
            return OptimalComposition(
                composition=composition,
                expected_performance=expected_performance,
                confidence_score=confidence_score,
                historical_sample_size=len(historical_matches),
                synergy_score=synergy_score,
                reasoning=reasoning
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze alternative composition: {e}")
            return None
    
    def _generate_overall_assessment(self, composition: OptimalComposition) -> str:
        """Generate overall assessment of the composition."""
        win_rate = composition.expected_performance.win_rate
        synergy = composition.synergy_score
        confidence = composition.confidence_score
        
        if win_rate >= 0.6 and synergy >= 0.1 and confidence >= 0.7:
            return "Excellent composition with strong performance potential and high confidence"
        elif win_rate >= 0.55 and synergy >= 0.05 and confidence >= 0.5:
            return "Good composition with solid performance potential"
        elif win_rate >= 0.5 and synergy >= 0.0 and confidence >= 0.3:
            return "Balanced composition with moderate performance potential"
        elif win_rate >= 0.45:
            return "Below-average composition that may need adjustments"
        else:
            return "High-risk composition requiring significant improvements"
    
    def _generate_performance_explanation(self, composition: OptimalComposition) -> Dict[str, Any]:
        """Generate detailed performance explanation."""
        perf = composition.expected_performance
        
        return {
            "win_rate_assessment": f"Expected win rate of {perf.win_rate:.1%}",
            "kda_analysis": f"Average team KDA of {perf.avg_kda:.2f}",
            "cs_efficiency": f"CS per minute: {perf.avg_cs_per_min:.1f}",
            "vision_control": f"Vision score: {perf.avg_vision_score:.1f}",
            "damage_output": f"Damage per minute: {perf.avg_damage_per_min:.0f}",
            "sample_size": f"Based on {composition.historical_sample_size} historical matches" if composition.historical_sample_size > 0 else "Estimated from player baselines"
        }
    
    def _generate_synergy_explanation(self, composition: OptimalComposition) -> Dict[str, Any]:
        """Generate synergy analysis explanation."""
        synergy = composition.synergy_score
        
        synergy_level = "neutral"
        if synergy > 0.15:
            synergy_level = "excellent"
        elif synergy > 0.1:
            synergy_level = "strong"
        elif synergy > 0.05:
            synergy_level = "good"
        elif synergy < -0.05:
            synergy_level = "poor"
        elif synergy < -0.1:
            synergy_level = "problematic"
        
        return {
            "overall_synergy": f"{synergy_level.title()} team synergy (score: {synergy:.3f})",
            "synergy_score": synergy,
            "interpretation": self._interpret_synergy_score(synergy)
        }
    
    def _generate_individual_explanations(self, composition: OptimalComposition) -> Dict[str, str]:
        """Generate explanations for individual player contributions."""
        explanations = {}
        
        for role, assignment in composition.composition.players.items():
            try:
                # Get player baseline for context
                baseline = self.baseline_manager.get_champion_specific_baseline(
                    assignment.puuid, assignment.champion_id, assignment.role
                )
                
                explanations[role] = (
                    f"{assignment.player_name} on {assignment.champion_name}: "
                    f"Win rate {baseline.baseline_metrics.win_rate:.1%}, "
                    f"KDA {baseline.baseline_metrics.avg_kda:.2f}"
                )
                
            except InsufficientDataError:
                explanations[role] = (
                    f"{assignment.player_name} on {assignment.champion_name}: "
                    f"Limited historical data available"
                )
        
        return explanations
    
    def _generate_risk_explanation(self, composition: OptimalComposition) -> Dict[str, Any]:
        """Generate risk assessment explanation."""
        risk_score = self._calculate_composition_risk(
            composition.composition, 
            composition.expected_performance, 
            composition.confidence_score
        )
        
        risk_level = "low"
        if risk_score > 0.7:
            risk_level = "high"
        elif risk_score > 0.4:
            risk_level = "moderate"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": self._identify_risk_factors(composition),
            "mitigation_suggestions": self._suggest_risk_mitigation(composition)
        }
    
    def _generate_improvement_recommendations(self, composition: OptimalComposition) -> List[str]:
        """Generate recommendations for improving the composition."""
        recommendations = []
        
        # Performance-based recommendations
        if composition.expected_performance.win_rate < 0.5:
            recommendations.append("Consider player substitutions to improve overall performance")
        
        # Synergy-based recommendations
        if composition.synergy_score < 0.0:
            recommendations.append("Focus on team coordination and communication to improve synergy")
        
        # Confidence-based recommendations
        if composition.confidence_score < 0.5:
            recommendations.append("Gather more match data with this composition to improve confidence")
        
        # Role-specific recommendations
        for role, assignment in composition.composition.players.items():
            try:
                player_roles = self._get_player_roles(assignment.puuid)
                if role not in player_roles:
                    recommendations.append(f"Consider role training for {assignment.player_name} in {role}")
            except Exception:
                pass
        
        return recommendations if recommendations else ["Composition appears well-optimized"]
    
    def _generate_confidence_explanation(self, composition: OptimalComposition) -> Dict[str, Any]:
        """Generate confidence factors explanation."""
        confidence = composition.confidence_score
        
        confidence_level = "low"
        if confidence >= 0.8:
            confidence_level = "high"
        elif confidence >= 0.6:
            confidence_level = "moderate"
        
        factors = []
        if composition.historical_sample_size > 10:
            factors.append("Strong historical data sample")
        elif composition.historical_sample_size > 5:
            factors.append("Moderate historical data sample")
        else:
            factors.append("Limited historical data - based on estimates")
        
        return {
            "confidence_level": confidence_level,
            "confidence_score": confidence,
            "contributing_factors": factors,
            "reliability_note": self._generate_reliability_note(composition)
        }
    
    def _interpret_synergy_score(self, synergy: float) -> str:
        """Interpret synergy score for user understanding."""
        if synergy > 0.15:
            return "Players work exceptionally well together"
        elif synergy > 0.1:
            return "Strong team chemistry and coordination"
        elif synergy > 0.05:
            return "Good team compatibility"
        elif synergy > -0.05:
            return "Neutral team dynamics"
        elif synergy > -0.1:
            return "Some coordination challenges expected"
        else:
            return "Significant synergy issues - consider alternatives"
    
    def _identify_risk_factors(self, composition: OptimalComposition) -> List[str]:
        """Identify specific risk factors for the composition."""
        risk_factors = []
        
        if composition.expected_performance.win_rate < 0.45:
            risk_factors.append("Low expected win rate")
        
        if composition.confidence_score < 0.4:
            risk_factors.append("Low confidence due to insufficient data")
        
        if composition.synergy_score < -0.05:
            risk_factors.append("Negative team synergy")
        
        if composition.historical_sample_size < 3:
            risk_factors.append("Very limited historical data")
        
        return risk_factors if risk_factors else ["No significant risk factors identified"]
    
    def _suggest_risk_mitigation(self, composition: OptimalComposition) -> List[str]:
        """Suggest ways to mitigate identified risks."""
        suggestions = []
        
        if composition.confidence_score < 0.5:
            suggestions.append("Play more matches with this composition to gather data")
        
        if composition.synergy_score < 0.0:
            suggestions.append("Focus on team building and communication exercises")
        
        if composition.expected_performance.win_rate < 0.5:
            suggestions.append("Consider strategic coaching for underperforming roles")
        
        return suggestions if suggestions else ["Continue monitoring performance"]
    
    def _generate_reliability_note(self, composition: OptimalComposition) -> str:
        """Generate a note about the reliability of the analysis."""
        if composition.historical_sample_size >= 10:
            return "Analysis based on substantial historical data - high reliability"
        elif composition.historical_sample_size >= 5:
            return "Analysis based on moderate historical data - good reliability"
        elif composition.historical_sample_size >= 1:
            return "Analysis based on limited historical data - moderate reliability"
        else:
            return "Analysis based on player baselines and estimates - lower reliability"