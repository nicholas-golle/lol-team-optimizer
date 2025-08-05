"""
Champion Recommendation Engine for the League of Legends Team Optimizer.

This module provides intelligent champion recommendations based on historical
performance data, team composition synergies, and advanced scoring algorithms.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from collections import defaultdict
import statistics

from .analytics_models import (
    ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
    PerformanceProjection, SynergyAnalysis, RecommendationReasoning,
    AnalyticsFilters, DateRange, AnalyticsError, InsufficientDataError,
    ConfidenceInterval, RecentFormMetrics
)
from .historical_analytics_engine import HistoricalAnalyticsEngine
from .champion_data import ChampionDataManager
from .baseline_manager import BaselineManager, BaselineContext
from .config import Config


@dataclass
class RecommendationScore:
    """Detailed scoring breakdown for a champion recommendation."""
    
    champion_id: int
    total_score: float
    individual_performance_score: float
    team_synergy_score: float
    recent_form_score: float
    meta_relevance_score: float
    confidence_score: float
    
    # Weights used in calculation
    performance_weight: float
    synergy_weight: float
    form_weight: float
    meta_weight: float
    confidence_weight: float
    
    # Supporting data
    games_played: int
    data_quality_score: float
    sample_size_penalty: float


@dataclass
class TeamSynergyContext:
    """Context for team synergy analysis."""
    
    existing_champions: List[int]
    existing_roles: List[str]
    target_role: str
    historical_compositions: List[Dict[str, int]]  # List of role -> champion_id mappings
    synergy_scores: Dict[Tuple[int, int], float]  # (champion1, champion2) -> synergy_score


class ChampionRecommendationEngine:
    """
    Advanced champion recommendation system based on historical data.
    
    Provides intelligent champion recommendations that consider individual
    performance, team synergies, recent form, meta relevance, and data
    confidence to suggest optimal champion selections.
    """
    
    def __init__(
        self,
        config: Config,
        analytics_engine: HistoricalAnalyticsEngine,
        champion_data_manager: ChampionDataManager,
        baseline_manager: BaselineManager
    ):
        """
        Initialize the champion recommendation engine.
        
        Args:
            config: Configuration object
            analytics_engine: Historical analytics engine
            champion_data_manager: Champion data manager
            baseline_manager: Baseline manager for performance comparisons
        """
        self.config = config
        self.analytics_engine = analytics_engine
        self.champion_data_manager = champion_data_manager
        self.baseline_manager = baseline_manager
        self.logger = logging.getLogger(__name__)
        
        # Scoring configuration
        self.default_weights = {
            'individual_performance': 0.35,
            'team_synergy': 0.25,
            'recent_form': 0.20,
            'meta_relevance': 0.10,
            'confidence': 0.10
        }
        
        # Analysis configuration
        self.min_games_for_recommendation = 5
        self.recent_form_window_days = 30
        self.meta_analysis_window_days = 90
        self.max_recommendations = 10
        
        # Confidence scoring thresholds
        self.confidence_thresholds = {
            'high_confidence_games': 20,
            'medium_confidence_games': 10,
            'low_confidence_games': 5
        }
    
    def get_champion_recommendations(
        self,
        puuid: str,
        role: str,
        team_context: Optional[TeamContext] = None,
        filters: Optional[AnalyticsFilters] = None,
        max_recommendations: Optional[int] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[ChampionRecommendation]:
        """
        Get champion recommendations for a player in a specific role.
        
        Args:
            puuid: Player's PUUID
            role: Target role
            team_context: Current team composition context
            filters: Optional filters for historical data
            max_recommendations: Maximum number of recommendations
            custom_weights: Custom scoring weights
            
        Returns:
            List of ChampionRecommendation objects sorted by score
            
        Raises:
            AnalyticsError: If recommendation generation fails
            InsufficientDataError: If not enough data for recommendations
        """
        try:
            self.logger.info(f"Generating champion recommendations for {puuid} in {role}")
            
            # Use custom weights or defaults, with role-specific adjustments
            base_weights = custom_weights or self.default_weights
            weights = self._apply_role_specific_weight_adjustments(base_weights, role, team_context)
            max_recs = max_recommendations or self.max_recommendations
            
            # Get available champions for the role
            available_champions = self._get_available_champions(role, team_context)
            
            if not available_champions:
                raise AnalyticsError(f"No available champions found for role {role}")
            
            # Generate recommendations for each available champion
            recommendations = []
            
            for champion_id in available_champions:
                try:
                    recommendation = self._generate_single_recommendation(
                        puuid=puuid,
                        champion_id=champion_id,
                        role=role,
                        team_context=team_context,
                        filters=filters,
                        weights=weights
                    )
                    
                    if recommendation:
                        recommendations.append(recommendation)
                        
                except InsufficientDataError:
                    self.logger.debug(f"Insufficient data for {champion_id} recommendation")
                    continue
                except Exception as e:
                    self.logger.warning(f"Failed to generate recommendation for champion {champion_id}: {e}")
                    continue
            
            if not recommendations:
                raise InsufficientDataError(
                    required_games=self.min_games_for_recommendation,
                    available_games=0,
                    context=f"champion recommendations for {puuid} in {role}"
                )
            
            # Sort by recommendation score (descending)
            recommendations.sort(key=lambda r: r.recommendation_score, reverse=True)
            
            # Limit to max recommendations
            recommendations = recommendations[:max_recs]
            
            self.logger.info(f"Generated {len(recommendations)} recommendations for {puuid} in {role}")
            return recommendations
            
        except Exception as e:
            if isinstance(e, (AnalyticsError, InsufficientDataError)):
                raise
            raise AnalyticsError(f"Failed to generate champion recommendations: {e}")
    
    def calculate_recommendation_score(
        self,
        puuid: str,
        champion_id: int,
        role: str,
        team_context: Optional[TeamContext] = None,
        filters: Optional[AnalyticsFilters] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> RecommendationScore:
        """
        Calculate detailed recommendation score for a specific champion.
        
        Args:
            puuid: Player's PUUID
            champion_id: Champion ID
            role: Target role
            team_context: Team composition context
            filters: Optional filters for historical data
            weights: Scoring weights
            
        Returns:
            RecommendationScore object with detailed breakdown
            
        Raises:
            AnalyticsError: If scoring calculation fails
            InsufficientDataError: If not enough data for scoring
        """
        try:
            # Use default weights if not provided
            scoring_weights = weights or self.default_weights
            
            # Get champion performance data
            champion_performance = self.analytics_engine.analyze_champion_performance(
                puuid=puuid,
                champion_id=champion_id,
                role=role,
                filters=filters
            )
            
            # Calculate individual performance score
            performance_score = self._calculate_individual_performance_score(
                champion_performance, puuid, champion_id, role
            )
            
            # Calculate team synergy score
            synergy_score = self._calculate_team_synergy_score(
                champion_id, role, team_context, puuid
            )
            
            # Calculate recent form score
            form_score = self._calculate_recent_form_score(
                champion_performance.recent_form
            )
            
            # Calculate meta relevance score
            meta_score = self._calculate_meta_relevance_score(
                champion_id, role, filters
            )
            
            # Calculate confidence score
            confidence_score, data_quality, sample_penalty = self._calculate_confidence_score(
                champion_performance
            )
            
            # Calculate weighted total score
            total_score = (
                scoring_weights['individual_performance'] * performance_score +
                scoring_weights['team_synergy'] * synergy_score +
                scoring_weights['recent_form'] * form_score +
                scoring_weights['meta_relevance'] * meta_score +
                scoring_weights['confidence'] * confidence_score
            )
            
            return RecommendationScore(
                champion_id=champion_id,
                total_score=total_score,
                individual_performance_score=performance_score,
                team_synergy_score=synergy_score,
                recent_form_score=form_score,
                meta_relevance_score=meta_score,
                confidence_score=confidence_score,
                performance_weight=scoring_weights['individual_performance'],
                synergy_weight=scoring_weights['team_synergy'],
                form_weight=scoring_weights['recent_form'],
                meta_weight=scoring_weights['meta_relevance'],
                confidence_weight=scoring_weights['confidence'],
                games_played=champion_performance.performance.games_played,
                data_quality_score=data_quality,
                sample_size_penalty=sample_penalty
            )
            
        except Exception as e:
            if isinstance(e, (AnalyticsError, InsufficientDataError)):
                raise
            raise AnalyticsError(f"Failed to calculate recommendation score: {e}")
    
    def analyze_champion_synergies(
        self,
        champion_combinations: List[Tuple[int, int]],
        role_context: Optional[Dict[int, str]] = None
    ) -> Dict[Tuple[int, int], float]:
        """
        Analyze synergies between champion combinations.
        
        Args:
            champion_combinations: List of (champion1_id, champion2_id) tuples
            role_context: Optional mapping of champion_id to role
            
        Returns:
            Dictionary mapping champion pairs to synergy scores (-1.0 to 1.0)
            
        Raises:
            AnalyticsError: If synergy analysis fails
        """
        try:
            synergy_scores = {}
            
            for champion1_id, champion2_id in champion_combinations:
                try:
                    synergy_score = self._calculate_champion_pair_synergy(
                        champion1_id, champion2_id, role_context
                    )
                    synergy_scores[(champion1_id, champion2_id)] = synergy_score
                    
                except Exception as e:
                    self.logger.warning(f"Failed to calculate synergy for {champion1_id}-{champion2_id}: {e}")
                    synergy_scores[(champion1_id, champion2_id)] = 0.0
            
            return synergy_scores
            
        except Exception as e:
            raise AnalyticsError(f"Failed to analyze champion synergies: {e}")
    
    def get_meta_adjusted_recommendations(
        self,
        base_recommendations: List[ChampionRecommendation],
        meta_emphasis: float = 1.0
    ) -> List[ChampionRecommendation]:
        """
        Adjust recommendations based on current meta trends.
        
        Args:
            base_recommendations: Base recommendations to adjust
            meta_emphasis: Multiplier for meta adjustments (0.0 to 2.0)
            
        Returns:
            Adjusted recommendations sorted by new scores
        """
        try:
            adjusted_recommendations = []
            
            for recommendation in base_recommendations:
                # Calculate meta adjustment
                meta_adjustment = self._calculate_meta_adjustment(
                    recommendation.champion_id, meta_emphasis
                )
                
                # Apply meta adjustment to recommendation score
                adjusted_score = recommendation.recommendation_score * meta_adjustment
                
                # Create adjusted recommendation
                adjusted_recommendation = ChampionRecommendation(
                    champion_id=recommendation.champion_id,
                    champion_name=recommendation.champion_name,
                    role=recommendation.role,
                    recommendation_score=adjusted_score,
                    confidence=recommendation.confidence,
                    historical_performance=recommendation.historical_performance,
                    expected_performance=recommendation.expected_performance,
                    synergy_analysis=recommendation.synergy_analysis,
                    reasoning=recommendation.reasoning
                )
                
                adjusted_recommendations.append(adjusted_recommendation)
            
            # Re-sort by adjusted scores
            adjusted_recommendations.sort(key=lambda r: r.recommendation_score, reverse=True)
            
            return adjusted_recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to apply meta adjustments: {e}")
            return base_recommendations  # Return original on failure
    
    def _get_available_champions(
        self,
        role: str,
        team_context: Optional[TeamContext] = None
    ) -> List[int]:
        """Get list of available champions for the role."""
        # Get all champions that can play this role
        role_champions = self.champion_data_manager.get_champions_by_role(role)
        
        if not team_context:
            return role_champions
        
        # Filter out banned champions
        if team_context.banned_champions:
            role_champions = [
                champ_id for champ_id in role_champions
                if champ_id not in team_context.banned_champions
            ]
        
        # Filter to available champions if specified
        if team_context.available_champions:
            role_champions = [
                champ_id for champ_id in role_champions
                if champ_id in team_context.available_champions
            ]
        
        return role_champions
    
    def _generate_single_recommendation(
        self,
        puuid: str,
        champion_id: int,
        role: str,
        team_context: Optional[TeamContext],
        filters: Optional[AnalyticsFilters],
        weights: Dict[str, float]
    ) -> Optional[ChampionRecommendation]:
        """Generate a single champion recommendation."""
        try:
            # Calculate recommendation score
            score_breakdown = self.calculate_recommendation_score(
                puuid=puuid,
                champion_id=champion_id,
                role=role,
                team_context=team_context,
                filters=filters,
                weights=weights
            )
            
            # Get champion performance data
            champion_performance = self.analytics_engine.analyze_champion_performance(
                puuid=puuid,
                champion_id=champion_id,
                role=role,
                filters=filters
            )
            
            # Generate performance projection
            expected_performance = self._generate_performance_projection(
                champion_performance, score_breakdown
            )
            
            # Generate synergy analysis
            synergy_analysis = self._generate_synergy_analysis(
                champion_id, role, team_context, puuid
            )
            
            # Generate reasoning
            reasoning = self._generate_recommendation_reasoning(
                champion_performance, score_breakdown, synergy_analysis
            )
            
            # Get champion name
            champion_name = self.champion_data_manager.get_champion_name(champion_id)
            if not champion_name:
                champion_name = f"Champion_{champion_id}"
            
            return ChampionRecommendation(
                champion_id=champion_id,
                champion_name=champion_name,
                role=role,
                recommendation_score=score_breakdown.total_score,
                confidence=score_breakdown.confidence_score,
                historical_performance=champion_performance,
                expected_performance=expected_performance,
                synergy_analysis=synergy_analysis,
                reasoning=reasoning
            )
            
        except InsufficientDataError:
            # Re-raise insufficient data errors
            raise
        except Exception as e:
            self.logger.warning(f"Failed to generate recommendation for {champion_id}: {e}")
            return None  
  
    def _calculate_individual_performance_score(
        self,
        champion_performance: ChampionPerformanceMetrics,
        puuid: str,
        champion_id: int,
        role: str
    ) -> float:
        """
        Calculate individual performance score based on historical data.
        
        Args:
            champion_performance: Champion performance metrics
            puuid: Player's PUUID
            champion_id: Champion ID
            role: Role
            
        Returns:
            Performance score (0.0 to 1.0)
        """
        try:
            performance = champion_performance.performance
            
            # Base score from win rate (0.0 to 1.0)
            win_rate_score = performance.win_rate
            
            # KDA score (normalized to 0.0 to 1.0)
            # Excellent KDA is around 3.0+, good is 2.0+
            kda_score = min(performance.avg_kda / 3.0, 1.0)
            
            # Performance vs baseline score
            baseline_score = 0.5  # Default neutral score
            if champion_performance.performance_vs_baseline:
                # Calculate average performance delta across key metrics
                key_metrics = ['win_rate', 'avg_kda', 'avg_cs_per_min', 'avg_vision_score']
                delta_scores = []
                
                for metric in key_metrics:
                    if metric in champion_performance.performance_vs_baseline:
                        delta = champion_performance.performance_vs_baseline[metric]
                        # Convert percentage delta to score (-50% to +50% maps to 0.0 to 1.0)
                        delta_score = max(0.0, min(1.0, 0.5 + (delta.delta_percentage / 100.0)))
                        delta_scores.append(delta_score)
                
                if delta_scores:
                    baseline_score = statistics.mean(delta_scores)
            
            # Combine scores with weights
            individual_score = (
                0.4 * win_rate_score +
                0.3 * kda_score +
                0.3 * baseline_score
            )
            
            return max(0.0, min(1.0, individual_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate individual performance score: {e}")
            return 0.5  # Return neutral score on error
    
    def _calculate_team_synergy_score(
        self,
        champion_id: int,
        role: str,
        team_context: Optional[TeamContext],
        puuid: str
    ) -> float:
        """
        Calculate team synergy score based on composition analysis.
        
        Args:
            champion_id: Champion ID
            role: Target role
            team_context: Team composition context
            puuid: Player's PUUID
            
        Returns:
            Synergy score (0.0 to 1.0)
        """
        try:
            if not team_context:
                return 0.5  # Neutral score when no team context
            
            # Calculate ally synergy
            ally_synergy = self._calculate_ally_synergy_score(
                champion_id, role, team_context
            )
            
            # Calculate counter-pick advantage
            counter_pick_score = self._calculate_counter_pick_score(
                champion_id, role, team_context
            )
            
            # Combine scores (70% ally synergy, 30% counter-pick)
            total_synergy = (ally_synergy * 0.7 + counter_pick_score * 0.3)
            
            return max(0.0, min(1.0, total_synergy))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate team synergy score: {e}")
            return 0.5  # Return neutral score on error
    
    def _calculate_ally_synergy_score(
        self,
        champion_id: int,
        role: str,
        team_context: TeamContext
    ) -> float:
        """
        Calculate synergy score with allied champions.
        
        Args:
            champion_id: Champion ID
            role: Target role
            team_context: Team composition context
            
        Returns:
            Ally synergy score (0.0 to 1.0)
        """
        try:
            if not team_context.existing_picks:
                return 0.5  # Neutral score when no existing picks
            
            synergy_scores = []
            role_context = {champion_id: role}
            
            # Calculate synergy with each existing pick
            for existing_role, assignment in team_context.existing_picks.items():
                existing_champion_id = assignment.champion_id
                role_context[existing_champion_id] = existing_role
                
                # Calculate pairwise synergy
                pair_synergy = self._calculate_champion_pair_synergy(
                    champion_id, existing_champion_id, role_context
                )
                
                synergy_scores.append(pair_synergy)
            
            if not synergy_scores:
                return 0.5
            
            # Average synergy score, normalized to 0.0-1.0 range
            avg_synergy = statistics.mean(synergy_scores)
            normalized_synergy = (avg_synergy + 1.0) / 2.0  # Convert from [-1,1] to [0,1]
            
            return max(0.0, min(1.0, normalized_synergy))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate ally synergy score: {e}")
            return 0.5
    
    def _calculate_counter_pick_score(
        self,
        champion_id: int,
        role: str,
        team_context: TeamContext
    ) -> float:
        """
        Calculate counter-pick advantage score against enemy composition.
        
        Args:
            champion_id: Champion ID
            role: Target role
            team_context: Team composition context
            
        Returns:
            Counter-pick score (0.0 to 1.0)
        """
        try:
            if not team_context.enemy_composition:
                return 0.5  # Neutral score when no enemy info
            
            counter_scores = []
            
            # Calculate counter advantage against each enemy champion
            for enemy_role, enemy_champion_id in team_context.enemy_composition.items():
                counter_advantage = self._calculate_champion_counter_advantage(
                    champion_id, enemy_champion_id, role, enemy_role
                )
                
                # Weight lane matchups more heavily
                weight = 2.0 if role == enemy_role else 1.0
                counter_scores.append(counter_advantage * weight)
            
            if not counter_scores:
                return 0.5
            
            # Weighted average counter score
            total_weight = sum(2.0 if role == enemy_role else 1.0 
                             for enemy_role in team_context.enemy_composition.keys())
            
            weighted_avg = sum(counter_scores) / total_weight
            
            # Normalize to 0.0-1.0 range
            normalized_counter = (weighted_avg + 1.0) / 2.0
            
            return max(0.0, min(1.0, normalized_counter))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate counter-pick score: {e}")
            return 0.5
    
    def _calculate_champion_counter_advantage(
        self,
        champion_id: int,
        enemy_champion_id: int,
        role: str,
        enemy_role: str
    ) -> float:
        """
        Calculate counter advantage of one champion against another.
        
        Args:
            champion_id: Our champion ID
            enemy_champion_id: Enemy champion ID
            role: Our champion's role
            enemy_role: Enemy champion's role
            
        Returns:
            Counter advantage (-1.0 to 1.0)
        """
        try:
            # Get historical matchup data
            matchup_data = self._get_champion_matchup_data(
                champion_id, enemy_champion_id, role, enemy_role
            )
            
            if not matchup_data or matchup_data['games'] < 5:
                return 0.0  # Neutral when insufficient data
            
            # Calculate win rate advantage
            our_win_rate = matchup_data['win_rate']
            expected_win_rate = 0.5  # Neutral expectation
            
            # Counter advantage based on win rate difference
            advantage = (our_win_rate - expected_win_rate) / 0.5
            
            return max(-1.0, min(1.0, advantage))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate counter advantage: {e}")
            return 0.0
    
    def _get_champion_matchup_data(
        self,
        champion_id: int,
        enemy_champion_id: int,
        role: str,
        enemy_role: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical matchup data between two champions.
        
        Args:
            champion_id: Our champion ID
            enemy_champion_id: Enemy champion ID
            role: Our champion's role
            enemy_role: Enemy champion's role
            
        Returns:
            Matchup data dictionary or None
        """
        try:
            # Query matches where these champions faced each other
            matchup_matches = self.analytics_engine.match_manager.get_champion_matchups(
                champion_id, enemy_champion_id, role, enemy_role
            )
            
            if not matchup_matches:
                return None
            
            # Calculate matchup statistics
            total_games = len(matchup_matches)
            wins = sum(1 for match in matchup_matches if match.get('win', False))
            win_rate = wins / total_games if total_games > 0 else 0.0
            
            return {
                'games': total_games,
                'wins': wins,
                'win_rate': win_rate,
                'sample_size': 'high' if total_games >= 20 else 'medium' if total_games >= 10 else 'low'
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to get matchup data: {e}")
            return None
    
    def _calculate_recent_form_score(
        self,
        recent_form: Optional[RecentFormMetrics]
    ) -> float:
        """
        Calculate recent form score based on recent performance.
        
        Args:
            recent_form: Recent form metrics
            
        Returns:
            Form score (0.0 to 1.0)
        """
        try:
            if not recent_form:
                return 0.5  # Neutral score when no recent form data
            
            # Form score is already normalized to [-1, 1], convert to [0, 1]
            form_score = (recent_form.form_score + 1.0) / 2.0
            
            # Weight by trend strength
            if recent_form.trend_direction == "improving":
                form_score += 0.1 * recent_form.trend_strength
            elif recent_form.trend_direction == "declining":
                form_score -= 0.1 * recent_form.trend_strength
            
            return max(0.0, min(1.0, form_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate recent form score: {e}")
            return 0.5  # Return neutral score on error
    
    def _calculate_meta_relevance_score(
        self,
        champion_id: int,
        role: str,
        filters: Optional[AnalyticsFilters]
    ) -> float:
        """
        Calculate meta relevance score based on recent champion performance trends.
        
        Args:
            champion_id: Champion ID
            role: Role
            filters: Optional filters
            
        Returns:
            Meta relevance score (0.0 to 1.0)
        """
        try:
            # Calculate recent performance trends
            recent_performance_score = self._calculate_recent_meta_performance(
                champion_id, role, filters
            )
            
            # Calculate pick/ban rate influence
            popularity_score = self._calculate_champion_popularity_score(
                champion_id, role
            )
            
            # Combine scores
            meta_score = (recent_performance_score * 0.7 + popularity_score * 0.3)
            
            return max(0.0, min(1.0, meta_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate meta relevance score: {e}")
            return 0.5  # Return neutral score on error
    
    def _calculate_recent_meta_performance(
        self,
        champion_id: int,
        role: str,
        filters: Optional[AnalyticsFilters]
    ) -> float:
        """
        Calculate recent meta performance for a champion.
        
        Args:
            champion_id: Champion ID
            role: Role
            filters: Optional filters
            
        Returns:
            Recent performance score (0.0 to 1.0)
        """
        try:
            # Create recent time filter (last 30 days)
            recent_end = datetime.now()
            recent_start = recent_end - timedelta(days=self.meta_analysis_window_days)
            
            recent_filters = AnalyticsFilters(
                date_range=DateRange(start_date=recent_start, end_date=recent_end),
                roles=[role],
                min_games=3
            )
            
            # Get recent matches for this champion
            recent_matches = self.analytics_engine.match_manager.get_matches_with_champions(
                [champion_id], filters=recent_filters
            )
            
            if len(recent_matches) < 3:
                return 0.5  # Neutral score for insufficient data
            
            # Calculate recent win rate
            recent_wins = sum(1 for match in recent_matches if match.get('win', False))
            recent_win_rate = recent_wins / len(recent_matches)
            
            # Compare to overall champion win rate
            all_matches = self.analytics_engine.match_manager.get_matches_with_champions(
                [champion_id], filters=AnalyticsFilters(roles=[role], min_games=10)
            )
            
            if len(all_matches) < 10:
                return recent_win_rate  # Use recent win rate as score
            
            overall_wins = sum(1 for match in all_matches if match.get('win', False))
            overall_win_rate = overall_wins / len(all_matches)
            
            # Score based on recent vs overall performance
            performance_delta = recent_win_rate - overall_win_rate
            
            # Normalize to 0-1 scale (±25% difference = 0/1 score)
            meta_score = 0.5 + (performance_delta / 0.5)
            
            return max(0.0, min(1.0, meta_score))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate recent meta performance: {e}")
            return 0.5
    
    def _calculate_champion_popularity_score(
        self,
        champion_id: int,
        role: str
    ) -> float:
        """
        Calculate champion popularity score based on pick frequency.
        
        Args:
            champion_id: Champion ID
            role: Role
            
        Returns:
            Popularity score (0.0 to 1.0)
        """
        try:
            # Get recent matches for role
            recent_end = datetime.now()
            recent_start = recent_end - timedelta(days=30)
            
            role_filters = AnalyticsFilters(
                date_range=DateRange(start_date=recent_start, end_date=recent_end),
                roles=[role]
            )
            
            all_role_matches = self.analytics_engine.match_manager.get_matches_by_role(
                role, filters=role_filters
            )
            
            if not all_role_matches:
                return 0.5  # Neutral score
            
            # Count champion picks
            champion_picks = sum(
                1 for match in all_role_matches 
                if match.get('champion_id') == champion_id
            )
            
            # Calculate pick rate
            pick_rate = champion_picks / len(all_role_matches)
            
            # Normalize pick rate to score (5% pick rate = 0.5, 10%+ = 1.0)
            popularity_score = min(1.0, pick_rate / 0.1) * 0.5 + 0.25
            
            return max(0.0, min(1.0, popularity_score))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate champion popularity: {e}")
            return 0.5
    
    def _calculate_confidence_score(
        self,
        champion_performance: ChampionPerformanceMetrics
    ) -> Tuple[float, float, float]:
        """
        Calculate confidence score based on data quality and sample size.
        
        Args:
            champion_performance: Champion performance metrics
            
        Returns:
            Tuple of (confidence_score, data_quality_score, sample_size_penalty)
        """
        try:
            games_played = champion_performance.performance.games_played
            
            # Sample size scoring
            if games_played >= self.confidence_thresholds['high_confidence_games']:
                sample_size_score = 1.0
                sample_size_penalty = 0.0
            elif games_played >= self.confidence_thresholds['medium_confidence_games']:
                sample_size_score = 0.7
                sample_size_penalty = 0.1
            elif games_played >= self.confidence_thresholds['low_confidence_games']:
                sample_size_score = 0.4
                sample_size_penalty = 0.2
            else:
                sample_size_score = 0.2
                sample_size_penalty = 0.3
            
            # Data quality scoring (simplified)
            data_quality_score = 1.0  # Assume good data quality for now
            
            # Check for confidence scores in champion performance
            if champion_performance.confidence_scores:
                avg_confidence = statistics.mean(champion_performance.confidence_scores.values())
                data_quality_score = avg_confidence
            
            # Overall confidence score
            confidence_score = sample_size_score * data_quality_score
            
            return confidence_score, data_quality_score, sample_size_penalty
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate confidence score: {e}")
            return 0.5, 0.5, 0.2  # Return moderate confidence on error
    
    def _calculate_champion_pair_synergy(
        self,
        champion1_id: int,
        champion2_id: int,
        role_context: Optional[Dict[int, str]] = None
    ) -> float:
        """
        Calculate synergy score between two champions.
        
        Args:
            champion1_id: First champion ID
            champion2_id: Second champion ID
            role_context: Optional role context
            
        Returns:
            Synergy score (-1.0 to 1.0)
        """
        try:
            # Get historical data for champion combinations
            synergy_score = self._analyze_historical_champion_synergy(
                champion1_id, champion2_id, role_context
            )
            
            # Apply role-specific synergy adjustments
            if role_context:
                role_adjustment = self._calculate_role_synergy_adjustment(
                    champion1_id, champion2_id, role_context
                )
                synergy_score = (synergy_score + role_adjustment) / 2
            
            return max(-1.0, min(1.0, synergy_score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate champion pair synergy: {e}")
            return 0.0  # Return neutral synergy on error
    
    def _analyze_historical_champion_synergy(
        self,
        champion1_id: int,
        champion2_id: int,
        role_context: Optional[Dict[int, str]] = None
    ) -> float:
        """
        Analyze historical synergy between two champions.
        
        Args:
            champion1_id: First champion ID
            champion2_id: Second champion ID
            role_context: Optional role context
            
        Returns:
            Historical synergy score (-1.0 to 1.0)
        """
        try:
            # Query match manager for games with both champions
            matches_with_both = self.analytics_engine.match_manager.get_matches_with_champions(
                [champion1_id, champion2_id], same_team=True
            )
            
            if len(matches_with_both) < 5:  # Insufficient data
                return 0.0
            
            # Calculate win rate with both champions
            wins_together = sum(1 for match in matches_with_both if match.get('win', False))
            win_rate_together = wins_together / len(matches_with_both)
            
            # Get individual champion win rates for comparison
            individual_win_rates = []
            for champion_id in [champion1_id, champion2_id]:
                champion_matches = self.analytics_engine.match_manager.get_matches_with_champions(
                    [champion_id]
                )
                if champion_matches:
                    wins = sum(1 for match in champion_matches if match.get('win', False))
                    individual_win_rates.append(wins / len(champion_matches))
            
            if not individual_win_rates:
                return 0.0
            
            # Calculate expected win rate (average of individual rates)
            expected_win_rate = statistics.mean(individual_win_rates)
            
            # Synergy score based on performance vs expectation
            synergy_delta = win_rate_together - expected_win_rate
            
            # Normalize to [-1, 1] range (±50% difference = ±1.0 synergy)
            synergy_score = synergy_delta / 0.5
            
            return max(-1.0, min(1.0, synergy_score))
            
        except Exception as e:
            self.logger.debug(f"Failed to analyze historical synergy: {e}")
            return 0.0
    
    def _calculate_role_synergy_adjustment(
        self,
        champion1_id: int,
        champion2_id: int,
        role_context: Dict[int, str]
    ) -> float:
        """
        Calculate role-specific synergy adjustments.
        
        Args:
            champion1_id: First champion ID
            champion2_id: Second champion ID
            role_context: Role context mapping
            
        Returns:
            Role synergy adjustment (-0.5 to 0.5)
        """
        try:
            role1 = role_context.get(champion1_id)
            role2 = role_context.get(champion2_id)
            
            if not role1 or not role2:
                return 0.0
            
            # Define role synergy patterns
            synergy_patterns = {
                # High synergy combinations
                ('jungle', 'middle'): 0.3,  # Jungle-mid coordination
                ('support', 'bottom'): 0.4,  # Bot lane synergy
                ('top', 'jungle'): 0.2,     # Top-jungle coordination
                ('jungle', 'support'): 0.2,  # Vision control synergy
                
                # Neutral combinations
                ('top', 'middle'): 0.0,
                ('top', 'bottom'): 0.0,
                ('top', 'support'): 0.0,
                ('middle', 'bottom'): 0.0,
                ('middle', 'support'): 0.1,
                ('bottom', 'jungle'): 0.1,
            }
            
            # Check both role orders
            role_pair = (role1, role2)
            reverse_pair = (role2, role1)
            
            return synergy_patterns.get(role_pair, synergy_patterns.get(reverse_pair, 0.0))
            
        except Exception as e:
            self.logger.debug(f"Failed to calculate role synergy adjustment: {e}")
            return 0.0
    
    def _calculate_meta_adjustment(
        self,
        champion_id: int,
        meta_emphasis: float
    ) -> float:
        """
        Calculate meta adjustment multiplier for a champion.
        
        Args:
            champion_id: Champion ID
            meta_emphasis: Meta emphasis factor
            
        Returns:
            Meta adjustment multiplier (0.5 to 1.5)
        """
        try:
            # Placeholder implementation
            # In a full implementation, this would consider:
            # - Recent patch changes
            # - Professional play trends
            # - Solo queue statistics
            
            base_adjustment = 1.0
            meta_factor = 0.0  # Neutral meta position
            
            adjustment = base_adjustment + (meta_factor * meta_emphasis * 0.5)
            return max(0.5, min(1.5, adjustment))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate meta adjustment: {e}")
            return 1.0  # Return neutral adjustment on error
    
    def _generate_performance_projection(
        self,
        champion_performance: ChampionPerformanceMetrics,
        score_breakdown: RecommendationScore
    ) -> PerformanceProjection:
        """
        Generate performance projection for the recommendation.
        
        Args:
            champion_performance: Historical champion performance
            score_breakdown: Recommendation score breakdown
            
        Returns:
            PerformanceProjection object
        """
        try:
            performance = champion_performance.performance
            
            # Base projections on historical performance
            expected_win_rate = performance.win_rate
            expected_kda = performance.avg_kda
            expected_cs_per_min = performance.avg_cs_per_min
            expected_vision_score = performance.avg_vision_score
            
            # Adjust based on recent form if available
            if champion_performance.recent_form:
                form_adjustment = (champion_performance.recent_form.form_score * 0.1)
                expected_win_rate = max(0.0, min(1.0, expected_win_rate + form_adjustment))
                expected_kda = max(0.0, expected_kda * (1.0 + form_adjustment))
            
            # Create confidence interval based on sample size
            margin_of_error = 0.1 / max(1, (performance.games_played / 10))
            
            confidence_interval = ConfidenceInterval(
                lower_bound=max(0.0, expected_win_rate - margin_of_error),
                upper_bound=min(1.0, expected_win_rate + margin_of_error),
                confidence_level=0.95,
                sample_size=performance.games_played
            )
            
            return PerformanceProjection(
                expected_win_rate=expected_win_rate,
                expected_kda=expected_kda,
                expected_cs_per_min=expected_cs_per_min,
                expected_vision_score=expected_vision_score,
                confidence_interval=confidence_interval,
                projection_basis="historical"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to generate performance projection: {e}")
            # Return default projection
            return PerformanceProjection(
                expected_win_rate=0.5,
                expected_kda=1.0,
                expected_cs_per_min=5.0,
                expected_vision_score=20.0,
                confidence_interval=ConfidenceInterval(0.4, 0.6, 0.95, 1),
                projection_basis="baseline_adjusted"
            )
    
    def _generate_synergy_analysis(
        self,
        champion_id: int,
        role: str,
        team_context: Optional[TeamContext],
        puuid: str
    ) -> SynergyAnalysis:
        """
        Generate synergy analysis for the recommendation.
        
        Args:
            champion_id: Champion ID
            role: Target role
            team_context: Team composition context
            puuid: Player's PUUID
            
        Returns:
            SynergyAnalysis object
        """
        try:
            if not team_context or not team_context.existing_picks:
                return SynergyAnalysis(
                    team_synergy_score=0.0,
                    individual_synergies={},
                    synergy_explanation="No team context available for synergy analysis",
                    historical_data_points=0
                )
            
            individual_synergies = {}
            synergy_scores = []
            
            # Calculate synergies with existing picks
            for existing_role, assignment in team_context.existing_picks.items():
                existing_champion_id = assignment.champion_id
                synergy_score = self._calculate_champion_pair_synergy(
                    champion_id, existing_champion_id
                )
                individual_synergies[existing_champion_id] = synergy_score
                synergy_scores.append(synergy_score)
            
            # Calculate overall team synergy
            team_synergy_score = statistics.mean(synergy_scores) if synergy_scores else 0.0
            
            # Generate explanation
            if team_synergy_score > 0.2:
                synergy_explanation = "Strong synergy with current team composition"
            elif team_synergy_score < -0.2:
                synergy_explanation = "Potential conflicts with current team composition"
            else:
                synergy_explanation = "Neutral synergy with current team composition"
            
            return SynergyAnalysis(
                team_synergy_score=team_synergy_score,
                individual_synergies=individual_synergies,
                synergy_explanation=synergy_explanation,
                historical_data_points=len(synergy_scores) * 10  # Placeholder
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to generate synergy analysis: {e}")
            return SynergyAnalysis(
                team_synergy_score=0.0,
                individual_synergies={},
                synergy_explanation="Unable to analyze synergy due to data limitations",
                historical_data_points=0
            )
    
    def _generate_recommendation_reasoning(
        self,
        champion_performance: ChampionPerformanceMetrics,
        score_breakdown: RecommendationScore,
        synergy_analysis: SynergyAnalysis
    ) -> RecommendationReasoning:
        """
        Generate detailed reasoning for champion recommendation.
        
        Args:
            champion_performance: Historical champion performance
            score_breakdown: Recommendation score breakdown
            synergy_analysis: Team synergy analysis
            
        Returns:
            RecommendationReasoning object with detailed explanations
        """
        try:
            # Identify primary factors influencing the recommendation
            primary_factors = self._identify_primary_factors(score_breakdown)
            
            # Generate performance summary
            performance_summary = self._generate_performance_summary(
                champion_performance, score_breakdown
            )
            
            # Generate synergy summary
            synergy_summary = self._generate_synergy_summary(synergy_analysis)
            
            # Generate confidence explanation
            confidence_explanation = self._generate_confidence_explanation(
                score_breakdown, champion_performance
            )
            
            # Identify potential warnings
            warnings = self._identify_recommendation_warnings(
                champion_performance, score_breakdown
            )
            
            return RecommendationReasoning(
                primary_factors=primary_factors,
                performance_summary=performance_summary,
                synergy_summary=synergy_summary,
                confidence_explanation=confidence_explanation,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to generate recommendation reasoning: {e}")
            # Return basic reasoning on error
            return RecommendationReasoning(
                primary_factors=["Historical performance"],
                performance_summary="Based on historical match data",
                synergy_summary="Team synergy analysis included",
                confidence_explanation="Confidence based on available data",
                warnings=[]
            )
    
    def _identify_primary_factors(self, score_breakdown: RecommendationScore) -> List[str]:
        """
        Identify the primary factors driving the recommendation.
        
        Args:
            score_breakdown: Recommendation score breakdown
            
        Returns:
            List of primary factor descriptions
        """
        factors = []
        
        # Check which scores are significantly above/below average
        if score_breakdown.individual_performance_score > 0.7:
            factors.append("Strong historical performance")
        elif score_breakdown.individual_performance_score < 0.3:
            factors.append("Below-average historical performance")
        
        if score_breakdown.team_synergy_score > 0.7:
            factors.append("Excellent team synergy")
        elif score_breakdown.team_synergy_score < 0.3:
            factors.append("Poor team synergy")
        
        if score_breakdown.recent_form_score > 0.7:
            factors.append("Strong recent form")
        elif score_breakdown.recent_form_score < 0.3:
            factors.append("Declining recent form")
        
        if score_breakdown.meta_relevance_score > 0.7:
            factors.append("High meta relevance")
        elif score_breakdown.meta_relevance_score < 0.3:
            factors.append("Low meta relevance")
        
        if score_breakdown.confidence_score < 0.4:
            factors.append("Limited data available")
        
        # Default factor if none identified
        if not factors:
            factors.append("Balanced performance profile")
        
        return factors
    
    def _generate_performance_summary(
        self,
        champion_performance: ChampionPerformanceMetrics,
        score_breakdown: RecommendationScore
    ) -> str:
        """
        Generate performance summary text.
        
        Args:
            champion_performance: Historical champion performance
            score_breakdown: Recommendation score breakdown
            
        Returns:
            Performance summary string
        """
        try:
            performance = champion_performance.performance
            
            # Build performance summary
            summary_parts = []
            
            # Win rate summary
            win_rate_pct = performance.win_rate * 100
            if win_rate_pct >= 60:
                summary_parts.append(f"Excellent {win_rate_pct:.1f}% win rate")
            elif win_rate_pct >= 50:
                summary_parts.append(f"Solid {win_rate_pct:.1f}% win rate")
            else:
                summary_parts.append(f"Below-average {win_rate_pct:.1f}% win rate")
            
            # KDA summary
            if performance.avg_kda >= 2.5:
                summary_parts.append(f"strong {performance.avg_kda:.1f} KDA")
            elif performance.avg_kda >= 1.5:
                summary_parts.append(f"decent {performance.avg_kda:.1f} KDA")
            else:
                summary_parts.append(f"struggling {performance.avg_kda:.1f} KDA")
            
            # Games played context
            if performance.games_played >= 20:
                sample_desc = "extensive"
            elif performance.games_played >= 10:
                sample_desc = "solid"
            else:
                sample_desc = "limited"
            
            summary_parts.append(f"over {sample_desc} {performance.games_played} games")
            
            # Recent form if available
            if champion_performance.recent_form:
                form = champion_performance.recent_form
                if form.trend_direction == "improving":
                    summary_parts.append("with improving recent form")
                elif form.trend_direction == "declining":
                    summary_parts.append("but declining recent form")
            
            return f"Shows {', '.join(summary_parts)}."
            
        except Exception as e:
            self.logger.debug(f"Failed to generate performance summary: {e}")
            return "Performance analysis based on historical data."
    
    def _generate_synergy_summary(self, synergy_analysis: SynergyAnalysis) -> str:
        """
        Generate synergy summary text.
        
        Args:
            synergy_analysis: Team synergy analysis
            
        Returns:
            Synergy summary string
        """
        try:
            if not synergy_analysis:
                return "No team synergy data available."
            
            team_synergy = synergy_analysis.team_synergy_score
            
            if team_synergy > 0.3:
                synergy_desc = "Strong positive synergy"
            elif team_synergy > 0.1:
                synergy_desc = "Good synergy"
            elif team_synergy > -0.1:
                synergy_desc = "Neutral synergy"
            elif team_synergy > -0.3:
                synergy_desc = "Some synergy concerns"
            else:
                synergy_desc = "Poor team synergy"
            
            summary = f"{synergy_desc} with current team composition"
            
            # Add specific synergy details if available
            if synergy_analysis.individual_synergies:
                best_synergy = max(synergy_analysis.individual_synergies.values())
                worst_synergy = min(synergy_analysis.individual_synergies.values())
                
                if best_synergy > 0.3:
                    summary += ", particularly strong with some teammates"
                elif worst_synergy < -0.3:
                    summary += ", with some challenging matchups"
            
            # Add data confidence
            if synergy_analysis.historical_data_points >= 10:
                summary += " (high confidence)"
            elif synergy_analysis.historical_data_points >= 5:
                summary += " (medium confidence)"
            else:
                summary += " (limited data)"
            
            return summary + "."
            
        except Exception as e:
            self.logger.debug(f"Failed to generate synergy summary: {e}")
            return "Team synergy analysis included in recommendation."
    
    def _generate_confidence_explanation(
        self,
        score_breakdown: RecommendationScore,
        champion_performance: ChampionPerformanceMetrics
    ) -> str:
        """
        Generate confidence explanation text.
        
        Args:
            score_breakdown: Recommendation score breakdown
            champion_performance: Historical champion performance
            
        Returns:
            Confidence explanation string
        """
        try:
            confidence = score_breakdown.confidence_score
            games_played = score_breakdown.games_played
            
            if confidence >= 0.8:
                confidence_level = "Very high"
            elif confidence >= 0.6:
                confidence_level = "High"
            elif confidence >= 0.4:
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
            
            explanation = f"{confidence_level} confidence"
            
            # Add reasoning based on data quality
            if games_played >= 20:
                explanation += f" based on extensive {games_played} game sample"
            elif games_played >= 10:
                explanation += f" based on solid {games_played} game sample"
            elif games_played >= 5:
                explanation += f" based on limited {games_played} game sample"
            else:
                explanation += f" due to very limited {games_played} game sample"
            
            # Add data quality factors
            if score_breakdown.data_quality_score < 0.6:
                explanation += " with some data quality concerns"
            
            if score_breakdown.sample_size_penalty > 0.2:
                explanation += " and sample size limitations"
            
            return explanation + "."
            
        except Exception as e:
            self.logger.debug(f"Failed to generate confidence explanation: {e}")
            return "Confidence assessment based on available data quality and sample size."
    
    def _identify_recommendation_warnings(
        self,
        champion_performance: ChampionPerformanceMetrics,
        score_breakdown: RecommendationScore
    ) -> List[str]:
        """
        Identify potential warnings for the recommendation.
        
        Args:
            champion_performance: Historical champion performance
            score_breakdown: Recommendation score breakdown
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        try:
            # Low sample size warning
            if score_breakdown.games_played < 10:
                warnings.append(f"Limited data: Only {score_breakdown.games_played} games played")
            
            # Poor recent form warning
            if score_breakdown.recent_form_score < 0.3:
                warnings.append("Recent performance has been declining")
            
            # Low confidence warning
            if score_breakdown.confidence_score < 0.4:
                warnings.append("Low confidence due to data limitations")
            
            # Poor team synergy warning
            if score_breakdown.team_synergy_score < 0.3:
                warnings.append("Potential team synergy issues")
            
            # Meta relevance warning
            if score_breakdown.meta_relevance_score < 0.3:
                warnings.append("Champion may not be meta-relevant currently")
            
            # Overall performance warning
            if score_breakdown.individual_performance_score < 0.3:
                warnings.append("Below-average historical performance on this champion")
            
            return warnings
            
        except Exception as e:
            self.logger.debug(f"Failed to identify warnings: {e}")
            return []
    
    def _apply_role_specific_weight_adjustments(
        self,
        base_weights: Dict[str, float],
        role: str,
        team_context: Optional[TeamContext]
    ) -> Dict[str, float]:
        """
        Apply role-specific adjustments to recommendation weights.
        
        Args:
            base_weights: Base scoring weights
            role: Target role
            team_context: Team composition context
            
        Returns:
            Adjusted weights dictionary
        """
        try:
            # Copy base weights
            adjusted_weights = base_weights.copy()
            
            # Role-specific weight adjustments
            role_adjustments = {
                'top': {
                    'individual_performance': 0.05,  # Slightly more emphasis on individual skill
                    'team_synergy': -0.05,           # Less emphasis on synergy (more isolated)
                    'meta_relevance': 0.02           # Slightly more meta-sensitive
                },
                'jungle': {
                    'individual_performance': -0.05,  # Less individual, more team-focused
                    'team_synergy': 0.08,            # Much more emphasis on synergy
                    'recent_form': 0.02              # Recent form important for jungle
                },
                'middle': {
                    'individual_performance': 0.03,  # Slight emphasis on individual skill
                    'meta_relevance': 0.05,          # Very meta-sensitive role
                    'team_synergy': -0.02            # Slightly less synergy dependent
                },
                'bottom': {
                    'team_synergy': 0.06,           # High synergy with support
                    'individual_performance': -0.02, # Less individual focus
                    'recent_form': 0.03             # Recent form important
                },
                'support': {
                    'team_synergy': 0.10,           # Highest synergy importance
                    'individual_performance': -0.08, # Least individual focus
                    'meta_relevance': -0.02         # Less meta-dependent
                }
            }
            
            # Apply role adjustments
            if role in role_adjustments:
                for weight_key, adjustment in role_adjustments[role].items():
                    if weight_key in adjusted_weights:
                        adjusted_weights[weight_key] += adjustment
            
            # Apply team context adjustments
            if team_context:
                adjusted_weights = self._apply_team_context_weight_adjustments(
                    adjusted_weights, team_context
                )
            
            # Normalize weights to sum to 1.0
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                for key in adjusted_weights:
                    adjusted_weights[key] /= total_weight
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.warning(f"Failed to apply role-specific weight adjustments: {e}")
            return base_weights
    
    def _apply_team_context_weight_adjustments(
        self,
        weights: Dict[str, float],
        team_context: TeamContext
    ) -> Dict[str, float]:
        """
        Apply team context-specific weight adjustments.
        
        Args:
            weights: Current weights
            team_context: Team composition context
            
        Returns:
            Context-adjusted weights
        """
        try:
            adjusted_weights = weights.copy()
            
            # If enemy composition is known, increase counter-pick importance
            if team_context.enemy_composition:
                # Increase synergy weight (which includes counter-pick analysis)
                synergy_boost = 0.05
                adjusted_weights['team_synergy'] += synergy_boost
                
                # Reduce other weights proportionally
                other_keys = [k for k in adjusted_weights.keys() if k != 'team_synergy']
                reduction_per_key = synergy_boost / len(other_keys)
                for key in other_keys:
                    adjusted_weights[key] = max(0.05, adjusted_weights[key] - reduction_per_key)
            
            # If many champions are banned, increase meta relevance
            if team_context.banned_champions and len(team_context.banned_champions) > 5:
                meta_boost = 0.03
                adjusted_weights['meta_relevance'] += meta_boost
                
                # Reduce individual performance weight
                adjusted_weights['individual_performance'] = max(
                    0.1, adjusted_weights['individual_performance'] - meta_boost
                )
            
            # If limited champion pool, increase individual performance weight
            if team_context.available_champions and len(team_context.available_champions) < 10:
                performance_boost = 0.04
                adjusted_weights['individual_performance'] += performance_boost
                
                # Reduce meta relevance weight
                adjusted_weights['meta_relevance'] = max(
                    0.05, adjusted_weights['meta_relevance'] - performance_boost
                )
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.debug(f"Failed to apply team context adjustments: {e}")
            return weights
        """
        Generate reasoning explanation for the recommendation.
        
        Args:
            champion_performance: Champion performance metrics
            score_breakdown: Score breakdown
            synergy_analysis: Synergy analysis
            
        Returns:
            RecommendationReasoning object
        """
        try:
            primary_factors = []
            warnings = []
            
            # Identify primary factors
            if score_breakdown.individual_performance_score > 0.7:
                primary_factors.append("Strong historical performance")
            elif score_breakdown.individual_performance_score < 0.3:
                primary_factors.append("Below-average historical performance")
                warnings.append("Consider practicing this champion more before ranked play")
            
            if score_breakdown.team_synergy_score > 0.7:
                primary_factors.append("Excellent team synergy")
            elif score_breakdown.team_synergy_score < 0.3:
                primary_factors.append("Limited team synergy")
            
            if score_breakdown.recent_form_score > 0.7:
                primary_factors.append("Strong recent form")
            elif score_breakdown.recent_form_score < 0.3:
                primary_factors.append("Declining recent form")
                warnings.append("Recent performance has been below average")
            
            if score_breakdown.confidence_score < 0.5:
                warnings.append("Limited data available - recommendation based on small sample size")
            
            # Generate performance summary
            performance = champion_performance.performance
            performance_summary = (
                f"Historical performance: {performance.win_rate:.1%} win rate, "
                f"{performance.avg_kda:.1f} KDA over {performance.games_played} games"
            )
            
            # Generate synergy summary
            synergy_summary = synergy_analysis.synergy_explanation
            
            # Generate confidence explanation
            if score_breakdown.confidence_score > 0.8:
                confidence_explanation = "High confidence based on substantial historical data"
            elif score_breakdown.confidence_score > 0.5:
                confidence_explanation = "Moderate confidence with adequate data sample"
            else:
                confidence_explanation = "Low confidence due to limited historical data"
            
            if not primary_factors:
                primary_factors = ["Balanced performance across all factors"]
            
            return RecommendationReasoning(
                primary_factors=primary_factors,
                performance_summary=performance_summary,
                synergy_summary=synergy_summary,
                confidence_explanation=confidence_explanation,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to generate recommendation reasoning: {e}")
            return RecommendationReasoning(
                primary_factors=["Unable to analyze factors"],
                performance_summary="Performance data unavailable",
                synergy_summary="Synergy analysis unavailable",
                confidence_explanation="Confidence assessment unavailable",
                warnings=["Recommendation generated with limited analysis"]
            )