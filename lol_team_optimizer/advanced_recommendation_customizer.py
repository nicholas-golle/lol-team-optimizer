"""
Advanced Recommendation Customization and Filtering System

This module provides comprehensive customization options for champion recommendations,
including parameter tuning, champion pool filtering, ban phase simulation,
scenario testing, performance tracking, and learning from user feedback.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics
import numpy as np

from .analytics_models import (
    ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
    AnalyticsFilters, DateRange, AnalyticsError, InsufficientDataError
)
from .champion_recommendation_engine import ChampionRecommendationEngine, RecommendationScore
from .models import Player
from .config import Config


@dataclass
class RecommendationParameters:
    """Customizable parameters for recommendation generation."""
    
    # Weight customization (must sum to 1.0)
    individual_performance_weight: float = 0.35
    team_synergy_weight: float = 0.25
    recent_form_weight: float = 0.20
    meta_relevance_weight: float = 0.10
    confidence_weight: float = 0.10
    
    # Meta emphasis (0.0 to 2.0)
    meta_emphasis: float = 1.0
    
    # Synergy importance (0.0 to 2.0)
    synergy_importance: float = 1.0
    
    # Risk tolerance (0.0 to 1.0)
    risk_tolerance: float = 0.5
    
    # Minimum confidence threshold
    min_confidence: float = 0.3
    
    # Maximum recommendations to return
    max_recommendations: int = 10
    
    # Time windows (in days)
    recent_form_window: int = 30
    meta_analysis_window: int = 90
    
    def __post_init__(self):
        """Validate parameters after initialization."""
        self._validate_weights()
        self._validate_ranges()
    
    def _validate_weights(self):
        """Validate that weights sum to 1.0."""
        total_weight = (
            self.individual_performance_weight +
            self.team_synergy_weight +
            self.recent_form_weight +
            self.meta_relevance_weight +
            self.confidence_weight
        )
        
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
    
    def _validate_ranges(self):
        """Validate parameter ranges."""
        if not (0.0 <= self.meta_emphasis <= 2.0):
            raise ValueError("Meta emphasis must be between 0.0 and 2.0")
        
        if not (0.0 <= self.synergy_importance <= 2.0):
            raise ValueError("Synergy importance must be between 0.0 and 2.0")
        
        if not (0.0 <= self.risk_tolerance <= 1.0):
            raise ValueError("Risk tolerance must be between 0.0 and 1.0")
        
        if not (0.0 <= self.min_confidence <= 1.0):
            raise ValueError("Minimum confidence must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecommendationParameters':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ChampionPoolFilter:
    """Filters for champion pool restrictions."""
    
    # Allowed champions (None means all allowed)
    allowed_champions: Optional[Set[int]] = None
    
    # Banned champions
    banned_champions: Set[int] = field(default_factory=set)
    
    # Role restrictions
    role_restrictions: Dict[str, Set[int]] = field(default_factory=dict)
    
    # Mastery requirements
    min_mastery_level: Optional[int] = None
    min_mastery_points: Optional[int] = None
    
    # Performance requirements
    min_games_played: int = 5
    min_win_rate: Optional[float] = None
    
    # Meta filters
    include_off_meta: bool = True
    meta_tier_threshold: Optional[str] = None  # 'S', 'A', 'B', 'C', 'D'
    
    # Comfort picks
    prioritize_comfort: bool = False
    comfort_threshold: int = 10  # Minimum games for comfort
    
    def apply_filter(self, champion_id: int, role: str, player_data: Dict[str, Any]) -> bool:
        """Check if champion passes all filters."""
        # Check allowed champions
        if self.allowed_champions is not None and champion_id not in self.allowed_champions:
            return False
        
        # Check banned champions
        if champion_id in self.banned_champions:
            return False
        
        # Check role restrictions
        if role in self.role_restrictions and champion_id not in self.role_restrictions[role]:
            return False
        
        # Check mastery requirements
        mastery_data = player_data.get('mastery', {}).get(champion_id, {})
        if self.min_mastery_level and mastery_data.get('level', 0) < self.min_mastery_level:
            return False
        
        if self.min_mastery_points and mastery_data.get('points', 0) < self.min_mastery_points:
            return False
        
        # Check performance requirements
        performance_data = player_data.get('performance', {}).get(champion_id, {})
        games_played = performance_data.get('games_played', 0)
        
        if games_played < self.min_games_played:
            return False
        
        if self.min_win_rate and performance_data.get('win_rate', 0) < self.min_win_rate:
            return False
        
        # Check meta filters
        if not self.include_off_meta:
            meta_tier = player_data.get('meta', {}).get(champion_id, {}).get('tier', 'D')
            if self.meta_tier_threshold:
                tier_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
                if tier_order.get(meta_tier, 4) > tier_order.get(self.meta_tier_threshold, 4):
                    return False
        
        return True


@dataclass
class BanPhaseSimulation:
    """Simulation of draft ban phase."""
    
    # Ban order (team1_ban1, team2_ban1, team1_ban2, team2_ban2, ...)
    ban_order: List[str] = field(default_factory=lambda: ['team1', 'team2'] * 5)
    
    # Current bans
    team1_bans: List[int] = field(default_factory=list)
    team2_bans: List[int] = field(default_factory=list)
    
    # Pick order
    pick_order: List[str] = field(default_factory=lambda: [
        'team1', 'team2', 'team2', 'team1', 'team1', 'team2', 'team2', 'team1', 'team1', 'team2'
    ])
    
    # Current picks
    team1_picks: List[Tuple[str, int]] = field(default_factory=list)  # (role, champion_id)
    team2_picks: List[Tuple[str, int]] = field(default_factory=list)
    
    # Current phase
    current_phase: str = 'ban'  # 'ban' or 'pick'
    current_turn: int = 0
    
    def get_banned_champions(self) -> Set[int]:
        """Get all currently banned champions."""
        return set(self.team1_bans + self.team2_bans)
    
    def get_picked_champions(self) -> Set[int]:
        """Get all currently picked champions."""
        picked = set()
        for _, champion_id in self.team1_picks + self.team2_picks:
            picked.add(champion_id)
        return picked
    
    def get_unavailable_champions(self) -> Set[int]:
        """Get all unavailable champions (banned or picked)."""
        return self.get_banned_champions() | self.get_picked_champions()
    
    def simulate_ban(self, champion_id: int, team: str = None) -> bool:
        """Simulate banning a champion."""
        if self.current_phase != 'ban':
            return False
        
        if self.current_turn >= len(self.ban_order):
            return False
        
        current_team = team or self.ban_order[self.current_turn]
        
        if current_team == 'team1':
            self.team1_bans.append(champion_id)
        else:
            self.team2_bans.append(champion_id)
        
        self.current_turn += 1
        
        # Check if ban phase is complete
        if self.current_turn >= len(self.ban_order):
            self.current_phase = 'pick'
            self.current_turn = 0
        
        return True
    
    def simulate_pick(self, champion_id: int, role: str, team: str = None) -> bool:
        """Simulate picking a champion."""
        if self.current_phase != 'pick':
            return False
        
        if self.current_turn >= len(self.pick_order):
            return False
        
        if champion_id in self.get_unavailable_champions():
            return False
        
        current_team = team or self.pick_order[self.current_turn]
        
        if current_team == 'team1':
            self.team1_picks.append((role, champion_id))
        else:
            self.team2_picks.append((role, champion_id))
        
        self.current_turn += 1
        return True
    
    def get_counter_pick_opportunities(self, target_team: str = 'team1') -> List[Dict[str, Any]]:
        """Identify counter-pick opportunities."""
        opportunities = []
        
        if target_team == 'team1':
            our_picks = self.team1_picks
            enemy_picks = self.team2_picks
        else:
            our_picks = self.team2_picks
            enemy_picks = self.team1_picks
        
        # Find roles where we can counter-pick
        our_roles = {role for role, _ in our_picks}
        enemy_roles = {role for role, _ in enemy_picks}
        
        for enemy_role, enemy_champion in enemy_picks:
            if enemy_role not in our_roles:  # We haven't picked for this role yet
                opportunities.append({
                    'target_role': enemy_role,
                    'enemy_champion': enemy_champion,
                    'counter_priority': 'high' if enemy_role in ['middle', 'bottom'] else 'medium'
                })
        
        return opportunities


@dataclass
class RecommendationScenario:
    """A what-if scenario for recommendation testing."""
    
    scenario_id: str
    name: str
    description: str
    
    # Scenario parameters
    parameters: RecommendationParameters
    champion_pool_filter: ChampionPoolFilter
    ban_phase: Optional[BanPhaseSimulation] = None
    
    # Team context
    team_context: Optional[TeamContext] = None
    
    # Expected outcomes
    expected_recommendations: Optional[List[int]] = None
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    actual_recommendations: Optional[List[ChampionRecommendation]] = None
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None


@dataclass
class UserFeedback:
    """User feedback on recommendations."""
    
    feedback_id: str
    user_id: str
    recommendation_id: str
    champion_id: int
    role: str
    
    # Feedback type
    feedback_type: str  # 'positive', 'negative', 'neutral'
    
    # Specific feedback
    accuracy_rating: Optional[int] = None  # 1-5 scale
    usefulness_rating: Optional[int] = None  # 1-5 scale
    
    # Detailed feedback
    comments: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Context
    match_outcome: Optional[bool] = None  # Did they win with this pick?
    performance_rating: Optional[int] = None  # How well did they perform?
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    session_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationPerformanceMetrics:
    """Performance tracking for recommendations."""
    
    # Accuracy metrics
    prediction_accuracy: float = 0.0
    confidence_calibration: float = 0.0
    
    # User satisfaction
    avg_user_rating: float = 0.0
    positive_feedback_rate: float = 0.0
    
    # Usage metrics
    recommendation_adoption_rate: float = 0.0
    match_win_rate_with_recommendations: float = 0.0
    
    # Performance by category
    performance_by_role: Dict[str, float] = field(default_factory=dict)
    performance_by_strategy: Dict[str, float] = field(default_factory=dict)
    performance_by_confidence: Dict[str, float] = field(default_factory=dict)
    
    # Temporal metrics
    last_updated: datetime = field(default_factory=datetime.now)
    sample_size: int = 0


class AdvancedRecommendationCustomizer:
    """
    Advanced recommendation customization and filtering system.
    
    Provides comprehensive customization options including parameter tuning,
    champion pool filtering, ban phase simulation, scenario testing,
    performance tracking, and learning from user feedback.
    """
    
    def __init__(
        self,
        config: Config,
        recommendation_engine: ChampionRecommendationEngine
    ):
        """Initialize the advanced recommendation customizer."""
        self.config = config
        self.recommendation_engine = recommendation_engine
        self.logger = logging.getLogger(__name__)
        
        # Storage for customizations and feedback
        self.user_parameters: Dict[str, RecommendationParameters] = {}
        self.user_filters: Dict[str, ChampionPoolFilter] = {}
        self.scenarios: Dict[str, RecommendationScenario] = {}
        self.feedback_history: List[UserFeedback] = []
        self.performance_metrics = RecommendationPerformanceMetrics()
        
        # Learning system
        self.feedback_weights: Dict[str, float] = {}
        self.adaptation_rate = 0.1
        
        self.logger.info("Advanced recommendation customizer initialized")
    
    def create_custom_parameters(
        self,
        user_id: str,
        **kwargs
    ) -> RecommendationParameters:
        """Create custom recommendation parameters for a user."""
        try:
            parameters = RecommendationParameters(**kwargs)
            self.user_parameters[user_id] = parameters
            
            self.logger.info(f"Created custom parameters for user {user_id}")
            return parameters
            
        except Exception as e:
            self.logger.error(f"Error creating custom parameters: {e}")
            raise AnalyticsError(f"Failed to create custom parameters: {e}")
    
    def create_champion_pool_filter(
        self,
        user_id: str,
        **kwargs
    ) -> ChampionPoolFilter:
        """Create champion pool filter for a user."""
        try:
            champion_filter = ChampionPoolFilter(**kwargs)
            self.user_filters[user_id] = champion_filter
            
            self.logger.info(f"Created champion pool filter for user {user_id}")
            return champion_filter
            
        except Exception as e:
            self.logger.error(f"Error creating champion pool filter: {e}")
            raise AnalyticsError(f"Failed to create champion pool filter: {e}")
    
    def get_customized_recommendations(
        self,
        puuid: str,
        role: str,
        user_id: str,
        team_context: Optional[TeamContext] = None,
        ban_phase: Optional[BanPhaseSimulation] = None,
        override_parameters: Optional[RecommendationParameters] = None,
        override_filter: Optional[ChampionPoolFilter] = None
    ) -> List[ChampionRecommendation]:
        """Get customized recommendations with user-specific parameters and filters."""
        try:
            # Get user customizations or defaults
            parameters = override_parameters or self.user_parameters.get(
                user_id, RecommendationParameters()
            )
            champion_filter = override_filter or self.user_filters.get(
                user_id, ChampionPoolFilter()
            )
            
            # Apply ban phase restrictions if provided
            if ban_phase:
                unavailable_champions = ban_phase.get_unavailable_champions()
                champion_filter.banned_champions.update(unavailable_champions)
                
                # Update team context with current picks
                if team_context:
                    team_context = self._update_team_context_with_ban_phase(
                        team_context, ban_phase
                    )
            
            # Get base recommendations
            base_recommendations = self.recommendation_engine.get_champion_recommendations(
                puuid=puuid,
                role=role,
                team_context=team_context,
                max_recommendations=parameters.max_recommendations * 2,  # Get more for filtering
                custom_weights={
                    'individual_performance': parameters.individual_performance_weight,
                    'team_synergy': parameters.team_synergy_weight * parameters.synergy_importance,
                    'recent_form': parameters.recent_form_weight,
                    'meta_relevance': parameters.meta_relevance_weight * parameters.meta_emphasis,
                    'confidence': parameters.confidence_weight
                }
            )
            
            # Apply champion pool filtering
            filtered_recommendations = self._apply_champion_pool_filter(
                base_recommendations, champion_filter, puuid, role
            )
            
            # Apply confidence filtering
            filtered_recommendations = [
                rec for rec in filtered_recommendations
                if rec.confidence >= parameters.min_confidence
            ]
            
            # Apply risk tolerance
            filtered_recommendations = self._apply_risk_tolerance(
                filtered_recommendations, parameters.risk_tolerance
            )
            
            # Limit to max recommendations
            final_recommendations = filtered_recommendations[:parameters.max_recommendations]
            
            # Apply user feedback learning
            final_recommendations = self._apply_feedback_learning(
                final_recommendations, user_id, role
            )
            
            self.logger.info(
                f"Generated {len(final_recommendations)} customized recommendations "
                f"for {puuid} in {role}"
            )
            
            return final_recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting customized recommendations: {e}")
            raise AnalyticsError(f"Failed to get customized recommendations: {e}")
    
    def simulate_ban_phase_recommendations(
        self,
        puuid: str,
        role: str,
        user_id: str,
        ban_phase: BanPhaseSimulation,
        team_context: Optional[TeamContext] = None
    ) -> Dict[str, Any]:
        """Simulate recommendations during different ban phase states."""
        try:
            results = {
                'current_state': {
                    'phase': ban_phase.current_phase,
                    'turn': ban_phase.current_turn,
                    'banned_champions': list(ban_phase.get_banned_champions()),
                    'picked_champions': list(ban_phase.get_picked_champions())
                },
                'recommendations': [],
                'counter_pick_opportunities': [],
                'ban_suggestions': []
            }
            
            # Get current recommendations
            current_recommendations = self.get_customized_recommendations(
                puuid=puuid,
                role=role,
                user_id=user_id,
                team_context=team_context,
                ban_phase=ban_phase
            )
            
            results['recommendations'] = [
                {
                    'champion_id': rec.champion_id,
                    'champion_name': rec.champion_name,
                    'score': rec.recommendation_score,
                    'confidence': rec.confidence,
                    'reasoning': rec.reasoning.primary_reasons if rec.reasoning else []
                }
                for rec in current_recommendations
            ]
            
            # Identify counter-pick opportunities
            if ban_phase.current_phase == 'pick':
                counter_opportunities = ban_phase.get_counter_pick_opportunities()
                results['counter_pick_opportunities'] = counter_opportunities
                
                # Get counter-pick recommendations
                for opportunity in counter_opportunities:
                    if opportunity['target_role'] == role:
                        counter_recs = self._get_counter_pick_recommendations(
                            puuid, role, opportunity['enemy_champion'], user_id
                        )
                        results['counter_pick_recommendations'] = counter_recs
            
            # Suggest strategic bans
            if ban_phase.current_phase == 'ban':
                ban_suggestions = self._get_strategic_ban_suggestions(
                    team_context, ban_phase
                )
                results['ban_suggestions'] = ban_suggestions
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error simulating ban phase recommendations: {e}")
            raise AnalyticsError(f"Failed to simulate ban phase recommendations: {e}")
    
    def create_recommendation_scenario(
        self,
        name: str,
        description: str,
        parameters: RecommendationParameters,
        champion_pool_filter: ChampionPoolFilter,
        team_context: Optional[TeamContext] = None,
        ban_phase: Optional[BanPhaseSimulation] = None,
        expected_recommendations: Optional[List[int]] = None,
        success_criteria: Optional[Dict[str, Any]] = None
    ) -> RecommendationScenario:
        """Create a what-if scenario for recommendation testing."""
        try:
            scenario_id = str(uuid.uuid4())
            
            scenario = RecommendationScenario(
                scenario_id=scenario_id,
                name=name,
                description=description,
                parameters=parameters,
                champion_pool_filter=champion_pool_filter,
                ban_phase=ban_phase,
                team_context=team_context,
                expected_recommendations=expected_recommendations,
                success_criteria=success_criteria or {}
            )
            
            self.scenarios[scenario_id] = scenario
            
            self.logger.info(f"Created recommendation scenario: {name}")
            return scenario
            
        except Exception as e:
            self.logger.error(f"Error creating recommendation scenario: {e}")
            raise AnalyticsError(f"Failed to create recommendation scenario: {e}")
    
    def run_scenario_test(
        self,
        scenario_id: str,
        puuid: str,
        role: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Run a recommendation scenario test."""
        try:
            scenario = self.scenarios.get(scenario_id)
            if not scenario:
                raise AnalyticsError(f"Scenario {scenario_id} not found")
            
            # Run recommendations with scenario parameters
            recommendations = self.get_customized_recommendations(
                puuid=puuid,
                role=role,
                user_id=user_id,
                team_context=scenario.team_context,
                ban_phase=scenario.ban_phase,
                override_parameters=scenario.parameters,
                override_filter=scenario.champion_pool_filter
            )
            
            # Store results
            scenario.actual_recommendations = recommendations
            scenario.last_run = datetime.now()
            
            # Evaluate against success criteria
            evaluation_results = self._evaluate_scenario_results(scenario)
            
            # Calculate performance metrics
            performance_metrics = self._calculate_scenario_performance(scenario)
            scenario.performance_metrics = performance_metrics
            
            results = {
                'scenario_id': scenario_id,
                'scenario_name': scenario.name,
                'recommendations': [
                    {
                        'champion_id': rec.champion_id,
                        'champion_name': rec.champion_name,
                        'score': rec.recommendation_score,
                        'confidence': rec.confidence
                    }
                    for rec in recommendations
                ],
                'evaluation': evaluation_results,
                'performance_metrics': performance_metrics,
                'success': evaluation_results.get('overall_success', False)
            }
            
            self.logger.info(f"Completed scenario test: {scenario.name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error running scenario test: {e}")
            raise AnalyticsError(f"Failed to run scenario test: {e}")
    
    def record_user_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        champion_id: int,
        role: str,
        feedback_type: str,
        accuracy_rating: Optional[int] = None,
        usefulness_rating: Optional[int] = None,
        comments: Optional[str] = None,
        match_outcome: Optional[bool] = None,
        performance_rating: Optional[int] = None,
        tags: Optional[List[str]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> UserFeedback:
        """Record user feedback on a recommendation."""
        try:
            feedback_id = str(uuid.uuid4())
            
            feedback = UserFeedback(
                feedback_id=feedback_id,
                user_id=user_id,
                recommendation_id=recommendation_id,
                champion_id=champion_id,
                role=role,
                feedback_type=feedback_type,
                accuracy_rating=accuracy_rating,
                usefulness_rating=usefulness_rating,
                comments=comments,
                match_outcome=match_outcome,
                performance_rating=performance_rating,
                tags=tags or [],
                session_context=session_context or {}
            )
            
            self.feedback_history.append(feedback)
            
            # Update learning system
            self._update_feedback_learning(feedback)
            
            # Update performance metrics
            self._update_performance_metrics(feedback)
            
            self.logger.info(f"Recorded user feedback: {feedback_type} for champion {champion_id}")
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error recording user feedback: {e}")
            raise AnalyticsError(f"Failed to record user feedback: {e}")
    
    def get_recommendation_performance_report(
        self,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive performance report for recommendations."""
        try:
            # Filter feedback based on criteria
            filtered_feedback = self._filter_feedback(user_id, role, time_range)
            
            if not filtered_feedback:
                return {
                    'summary': 'No feedback data available for the specified criteria',
                    'metrics': {},
                    'recommendations': []
                }
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(filtered_feedback)
            
            # Generate insights and recommendations
            insights = self._generate_performance_insights(filtered_feedback, metrics)
            
            # Create improvement recommendations
            improvement_recommendations = self._generate_improvement_recommendations(
                filtered_feedback, metrics
            )
            
            report = {
                'summary': {
                    'total_feedback': len(filtered_feedback),
                    'time_range': time_range,
                    'user_id': user_id,
                    'role': role
                },
                'metrics': metrics,
                'insights': insights,
                'improvement_recommendations': improvement_recommendations,
                'detailed_breakdown': self._create_detailed_breakdown(filtered_feedback)
            }
            
            self.logger.info("Generated recommendation performance report")
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            raise AnalyticsError(f"Failed to generate performance report: {e}")
    
    def export_customization_settings(self, user_id: str) -> Dict[str, Any]:
        """Export user's customization settings."""
        try:
            settings = {
                'user_id': user_id,
                'parameters': None,
                'champion_filter': None,
                'feedback_summary': {},
                'scenarios': [],
                'performance_metrics': {}
            }
            
            # Export parameters
            if user_id in self.user_parameters:
                settings['parameters'] = self.user_parameters[user_id].to_dict()
            
            # Export champion filter
            if user_id in self.user_filters:
                filter_data = asdict(self.user_filters[user_id])
                # Convert sets to lists for JSON serialization
                if 'allowed_champions' in filter_data and filter_data['allowed_champions']:
                    filter_data['allowed_champions'] = list(filter_data['allowed_champions'])
                if 'banned_champions' in filter_data:
                    filter_data['banned_champions'] = list(filter_data['banned_champions'])
                if 'role_restrictions' in filter_data:
                    filter_data['role_restrictions'] = {
                        role: list(champions) for role, champions in filter_data['role_restrictions'].items()
                    }
                settings['champion_filter'] = filter_data
            
            # Export user scenarios
            user_scenarios = [
                scenario for scenario in self.scenarios.values()
                if scenario.name.startswith(f"user_{user_id}_")
            ]
            settings['scenarios'] = [
                {
                    'scenario_id': s.scenario_id,
                    'name': s.name,
                    'description': s.description,
                    'created_at': s.created_at.isoformat(),
                    'performance_metrics': s.performance_metrics
                }
                for s in user_scenarios
            ]
            
            # Export feedback summary
            user_feedback = [f for f in self.feedback_history if f.user_id == user_id]
            if user_feedback:
                settings['feedback_summary'] = {
                    'total_feedback': len(user_feedback),
                    'positive_feedback': len([f for f in user_feedback if f.feedback_type == 'positive']),
                    'negative_feedback': len([f for f in user_feedback if f.feedback_type == 'negative']),
                    'avg_accuracy_rating': statistics.mean([
                        f.accuracy_rating for f in user_feedback 
                        if f.accuracy_rating is not None
                    ]) if any(f.accuracy_rating for f in user_feedback) else None,
                    'avg_usefulness_rating': statistics.mean([
                        f.usefulness_rating for f in user_feedback 
                        if f.usefulness_rating is not None
                    ]) if any(f.usefulness_rating for f in user_feedback) else None
                }
            
            # Export performance metrics
            settings['performance_metrics'] = asdict(self.performance_metrics)
            
            self.logger.info(f"Exported customization settings for user {user_id}")
            return settings
            
        except Exception as e:
            self.logger.error(f"Error exporting customization settings: {e}")
            raise AnalyticsError(f"Failed to export customization settings: {e}")
    
    def import_customization_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Import user's customization settings."""
        try:
            # Import parameters
            if settings.get('parameters'):
                self.user_parameters[user_id] = RecommendationParameters.from_dict(
                    settings['parameters']
                )
            
            # Import champion filter
            if settings.get('champion_filter'):
                filter_data = settings['champion_filter'].copy()
                # Convert lists back to sets
                if 'allowed_champions' in filter_data and filter_data['allowed_champions']:
                    filter_data['allowed_champions'] = set(filter_data['allowed_champions'])
                if 'banned_champions' in filter_data:
                    filter_data['banned_champions'] = set(filter_data['banned_champions'])
                if 'role_restrictions' in filter_data:
                    filter_data['role_restrictions'] = {
                        role: set(champions) for role, champions in filter_data['role_restrictions'].items()
                    }
                self.user_filters[user_id] = ChampionPoolFilter(**filter_data)
            
            self.logger.info(f"Imported customization settings for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing customization settings: {e}")
            return False
    
    def get_recommendation_insights(
        self,
        user_id: str,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get insights about recommendation performance and patterns."""
        try:
            # Filter feedback for user and time range
            user_feedback = [f for f in self.feedback_history if f.user_id == user_id]
            
            if time_range:
                start_time, end_time = time_range
                user_feedback = [
                    f for f in user_feedback
                    if start_time <= f.created_at <= end_time
                ]
            
            if not user_feedback:
                return {
                    'message': 'No feedback data available for insights',
                    'recommendations': []
                }
            
            insights = {
                'summary': {
                    'total_feedback': len(user_feedback),
                    'time_range': time_range,
                    'feedback_distribution': {
                        'positive': len([f for f in user_feedback if f.feedback_type == 'positive']),
                        'negative': len([f for f in user_feedback if f.feedback_type == 'negative']),
                        'neutral': len([f for f in user_feedback if f.feedback_type == 'neutral'])
                    }
                },
                'patterns': self._analyze_feedback_patterns(user_feedback),
                'recommendations': self._generate_insight_recommendations(user_feedback),
                'performance_trends': self._analyze_performance_trends(user_feedback)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error getting recommendation insights: {e}")
            raise AnalyticsError(f"Failed to get recommendation insights: {e}")
    
    def optimize_parameters_from_feedback(
        self,
        user_id: str,
        min_feedback_count: int = 10
    ) -> Optional[RecommendationParameters]:
        """Optimize recommendation parameters based on user feedback."""
        try:
            user_feedback = [f for f in self.feedback_history if f.user_id == user_id]
            
            if len(user_feedback) < min_feedback_count:
                self.logger.info(f"Insufficient feedback for optimization: {len(user_feedback)} < {min_feedback_count}")
                return None
            
            # Analyze feedback patterns
            positive_feedback = [f for f in user_feedback if f.feedback_type == 'positive']
            negative_feedback = [f for f in user_feedback if f.feedback_type == 'negative']
            
            # Get current parameters or defaults
            current_params = self.user_parameters.get(user_id, RecommendationParameters())
            
            # Calculate optimization adjustments
            adjustments = self._calculate_parameter_adjustments(
                positive_feedback, negative_feedback, current_params
            )
            
            # Apply adjustments
            optimized_params = self._apply_parameter_adjustments(current_params, adjustments)
            
            # Store optimized parameters
            self.user_parameters[user_id] = optimized_params
            
            self.logger.info(f"Optimized parameters for user {user_id} based on {len(user_feedback)} feedback items")
            return optimized_params
            
        except Exception as e:
            self.logger.error(f"Error optimizing parameters from feedback: {e}")
            return None
    
    def create_recommendation_preset(
        self,
        name: str,
        description: str,
        parameters: RecommendationParameters,
        champion_filter: ChampionPoolFilter,
        tags: Optional[List[str]] = None
    ) -> str:
        """Create a reusable recommendation preset."""
        try:
            preset_id = str(uuid.uuid4())
            
            preset = {
                'preset_id': preset_id,
                'name': name,
                'description': description,
                'parameters': parameters.to_dict(),
                'champion_filter': asdict(champion_filter),
                'tags': tags or [],
                'created_at': datetime.now(),
                'usage_count': 0
            }
            
            # Store preset (in a real implementation, this would be in a database)
            if not hasattr(self, 'presets'):
                self.presets = {}
            self.presets[preset_id] = preset
            
            self.logger.info(f"Created recommendation preset: {name}")
            return preset_id
            
        except Exception as e:
            self.logger.error(f"Error creating recommendation preset: {e}")
            raise AnalyticsError(f"Failed to create recommendation preset: {e}")
    
    def get_available_presets(self, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get available recommendation presets."""
        try:
            if not hasattr(self, 'presets'):
                return []
            
            presets = list(self.presets.values())
            
            # Filter by tags if provided
            if tags:
                presets = [
                    preset for preset in presets
                    if any(tag in preset.get('tags', []) for tag in tags)
                ]
            
            # Sort by usage count and creation date
            presets.sort(key=lambda p: (p.get('usage_count', 0), p.get('created_at', datetime.min)), reverse=True)
            
            return [
                {
                    'preset_id': preset['preset_id'],
                    'name': preset['name'],
                    'description': preset['description'],
                    'tags': preset.get('tags', []),
                    'usage_count': preset.get('usage_count', 0),
                    'created_at': preset.get('created_at', datetime.min).isoformat()
                }
                for preset in presets
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting available presets: {e}")
            return []
    
    def apply_preset(self, user_id: str, preset_id: str) -> bool:
        """Apply a recommendation preset to a user."""
        try:
            if not hasattr(self, 'presets') or preset_id not in self.presets:
                raise AnalyticsError(f"Preset {preset_id} not found")
            
            preset = self.presets[preset_id]
            
            # Apply parameters
            self.user_parameters[user_id] = RecommendationParameters.from_dict(
                preset['parameters']
            )
            
            # Apply champion filter
            filter_data = preset['champion_filter'].copy()
            # Convert lists back to sets if needed
            if 'allowed_champions' in filter_data and filter_data['allowed_champions']:
                filter_data['allowed_champions'] = set(filter_data['allowed_champions'])
            if 'banned_champions' in filter_data:
                filter_data['banned_champions'] = set(filter_data['banned_champions'])
            if 'role_restrictions' in filter_data:
                filter_data['role_restrictions'] = {
                    role: set(champions) for role, champions in filter_data['role_restrictions'].items()
                }
            
            self.user_filters[user_id] = ChampionPoolFilter(**filter_data)
            
            # Update usage count
            preset['usage_count'] = preset.get('usage_count', 0) + 1
            
            self.logger.info(f"Applied preset {preset['name']} to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying preset: {e}")
            return False
    
    # Helper methods for the new functionality
    
    def _analyze_feedback_patterns(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Analyze patterns in user feedback."""
        patterns = {
            'role_preferences': defaultdict(lambda: {'positive': 0, 'negative': 0}),
            'champion_preferences': defaultdict(lambda: {'positive': 0, 'negative': 0}),
            'common_tags': defaultdict(int),
            'temporal_patterns': {}
        }
        
        for feedback in feedback_list:
            # Role patterns
            patterns['role_preferences'][feedback.role][feedback.feedback_type] += 1
            
            # Champion patterns
            patterns['champion_preferences'][feedback.champion_id][feedback.feedback_type] += 1
            
            # Tag patterns
            for tag in feedback.tags:
                patterns['common_tags'][tag] += 1
        
        # Convert defaultdicts to regular dicts for JSON serialization
        patterns['role_preferences'] = dict(patterns['role_preferences'])
        patterns['champion_preferences'] = dict(patterns['champion_preferences'])
        patterns['common_tags'] = dict(patterns['common_tags'])
        
        return patterns
    
    def _generate_insight_recommendations(self, feedback_list: List[UserFeedback]) -> List[str]:
        """Generate actionable recommendations based on feedback analysis."""
        recommendations = []
        
        # Analyze feedback distribution
        positive_count = len([f for f in feedback_list if f.feedback_type == 'positive'])
        negative_count = len([f for f in feedback_list if f.feedback_type == 'negative'])
        total_count = len(feedback_list)
        
        if negative_count > positive_count:
            recommendations.append(
                "Consider adjusting recommendation parameters - negative feedback exceeds positive"
            )
        
        # Analyze role-specific patterns
        role_feedback = defaultdict(list)
        for feedback in feedback_list:
            role_feedback[feedback.role].append(feedback)
        
        for role, role_feedbacks in role_feedback.items():
            role_negative = len([f for f in role_feedbacks if f.feedback_type == 'negative'])
            if role_negative > len(role_feedbacks) * 0.6:
                recommendations.append(
                    f"Consider reviewing {role} recommendations - high negative feedback rate"
                )
        
        # Analyze accuracy ratings
        accuracy_ratings = [f.accuracy_rating for f in feedback_list if f.accuracy_rating is not None]
        if accuracy_ratings:
            avg_accuracy = statistics.mean(accuracy_ratings)
            if avg_accuracy < 3.0:
                recommendations.append(
                    "Recommendation accuracy is below average - consider parameter tuning"
                )
        
        return recommendations
    
    def _analyze_performance_trends(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        if not feedback_list:
            return {}
        
        # Sort feedback by date
        sorted_feedback = sorted(feedback_list, key=lambda f: f.created_at)
        
        # Calculate rolling averages
        window_size = min(10, len(sorted_feedback) // 2)
        if window_size < 3:
            return {'message': 'Insufficient data for trend analysis'}
        
        trends = {
            'accuracy_trend': [],
            'satisfaction_trend': [],
            'feedback_volume_trend': []
        }
        
        for i in range(window_size, len(sorted_feedback) + 1):
            window_feedback = sorted_feedback[i-window_size:i]
            
            # Accuracy trend
            accuracy_ratings = [f.accuracy_rating for f in window_feedback if f.accuracy_rating is not None]
            if accuracy_ratings:
                trends['accuracy_trend'].append({
                    'date': window_feedback[-1].created_at.isoformat(),
                    'value': statistics.mean(accuracy_ratings)
                })
            
            # Satisfaction trend (positive feedback ratio)
            positive_count = len([f for f in window_feedback if f.feedback_type == 'positive'])
            satisfaction_ratio = positive_count / len(window_feedback)
            trends['satisfaction_trend'].append({
                'date': window_feedback[-1].created_at.isoformat(),
                'value': satisfaction_ratio
            })
        
        return trends
    
    def _calculate_parameter_adjustments(
        self,
        positive_feedback: List[UserFeedback],
        negative_feedback: List[UserFeedback],
        current_params: RecommendationParameters
    ) -> Dict[str, float]:
        """Calculate parameter adjustments based on feedback."""
        adjustments = {}
        
        # Analyze feedback tags for parameter hints
        positive_tags = []
        negative_tags = []
        
        for feedback in positive_feedback:
            positive_tags.extend(feedback.tags)
        
        for feedback in negative_feedback:
            negative_tags.extend(feedback.tags)
        
        # Map tags to parameter adjustments
        tag_adjustments = {
            'individual_performance': {
                'good_individual_performance': 0.05,
                'poor_individual_performance': -0.05
            },
            'team_synergy': {
                'good_synergy': 0.05,
                'poor_synergy': -0.05
            },
            'meta_relevance': {
                'meta_relevant': 0.03,
                'off_meta': -0.03
            }
        }
        
        # Calculate adjustments
        for param, tag_map in tag_adjustments.items():
            adjustment = 0.0
            for tag, adj_value in tag_map.items():
                positive_tag_count = positive_tags.count(tag)
                negative_tag_count = negative_tags.count(tag)
                
                if positive_tag_count > negative_tag_count:
                    adjustment += adj_value
                elif negative_tag_count > positive_tag_count:
                    adjustment -= adj_value
            
            adjustments[param] = adjustment
        
        return adjustments
    
    def _apply_parameter_adjustments(
        self,
        current_params: RecommendationParameters,
        adjustments: Dict[str, float]
    ) -> RecommendationParameters:
        """Apply parameter adjustments while maintaining constraints."""
        # Create new parameters with adjustments
        new_params = RecommendationParameters(
            individual_performance_weight=max(0.1, min(0.6, 
                current_params.individual_performance_weight + adjustments.get('individual_performance', 0)
            )),
            team_synergy_weight=max(0.1, min(0.6,
                current_params.team_synergy_weight + adjustments.get('team_synergy', 0)
            )),
            recent_form_weight=current_params.recent_form_weight,
            meta_relevance_weight=max(0.05, min(0.3,
                current_params.meta_relevance_weight + adjustments.get('meta_relevance', 0)
            )),
            confidence_weight=current_params.confidence_weight,
            meta_emphasis=current_params.meta_emphasis,
            synergy_importance=current_params.synergy_importance,
            risk_tolerance=current_params.risk_tolerance,
            min_confidence=current_params.min_confidence,
            max_recommendations=current_params.max_recommendations,
            recent_form_window=current_params.recent_form_window,
            meta_analysis_window=current_params.meta_analysis_window
        )
        
        # Normalize weights to sum to 1.0
        total_weight = (
            new_params.individual_performance_weight +
            new_params.team_synergy_weight +
            new_params.recent_form_weight +
            new_params.meta_relevance_weight +
            new_params.confidence_weight
        )
        
        if total_weight != 1.0:
            new_params.individual_performance_weight /= total_weight
            new_params.team_synergy_weight /= total_weight
            new_params.recent_form_weight /= total_weight
            new_params.meta_relevance_weight /= total_weight
            new_params.confidence_weight /= total_weight
        
        return new_params
    
    def _update_team_context_with_ban_phase(
        self,
        team_context: TeamContext,
        ban_phase: BanPhaseSimulation
    ) -> TeamContext:
        """Update team context with ban phase information."""
        # Create a copy of team context
        updated_context = TeamContext(
            existing_picks=team_context.existing_picks.copy() if team_context.existing_picks else {},
            banned_champions=team_context.banned_champions.copy() if team_context.banned_champions else set(),
            enemy_composition=team_context.enemy_composition.copy() if team_context.enemy_composition else {},
            available_champions=team_context.available_champions.copy() if team_context.available_champions else None
        )
        
        # Add banned champions from ban phase
        updated_context.banned_champions.update(ban_phase.get_banned_champions())
        
        # Update enemy composition from ban phase picks
        for role, champion_id in ban_phase.team2_picks:
            updated_context.enemy_composition[role] = champion_id
        
        return updated_context
    
    def _apply_champion_pool_filter(
        self,
        recommendations: List[ChampionRecommendation],
        champion_filter: ChampionPoolFilter,
        puuid: str,
        role: str
    ) -> List[ChampionRecommendation]:
        """Apply champion pool filtering to recommendations."""
        filtered_recommendations = []
        
        # Get player data for filtering (mock implementation)
        player_data = self._get_player_data_for_filtering(puuid)
        
        for recommendation in recommendations:
            if champion_filter.apply_filter(recommendation.champion_id, role, player_data):
                filtered_recommendations.append(recommendation)
        
        return filtered_recommendations
    
    def _get_player_data_for_filtering(self, puuid: str) -> Dict[str, Any]:
        """Get player data needed for champion pool filtering."""
        # Mock implementation - in real system, this would fetch from data manager
        return {
            'mastery': {},
            'performance': {},
            'meta': {}
        }
    
    def _apply_risk_tolerance(
        self,
        recommendations: List[ChampionRecommendation],
        risk_tolerance: float
    ) -> List[ChampionRecommendation]:
        """Apply risk tolerance filtering to recommendations."""
        # Calculate risk score for each recommendation
        risk_filtered = []
        
        for recommendation in recommendations:
            # Calculate risk score based on confidence and performance variance
            risk_score = 1.0 - recommendation.confidence
            
            # Apply risk tolerance threshold
            if risk_score <= (1.0 - risk_tolerance):
                risk_filtered.append(recommendation)
        
        return risk_filtered
    
    def _apply_feedback_learning(
        self,
        recommendations: List[ChampionRecommendation],
        user_id: str,
        role: str
    ) -> List[ChampionRecommendation]:
        """Apply feedback learning to adjust recommendation scores."""
        # Get user feedback for this role
        user_feedback = [
            f for f in self.feedback_history
            if f.user_id == user_id and f.role == role
        ]
        
        if not user_feedback:
            return recommendations
        
        # Create feedback weights for champions
        champion_feedback_weights = {}
        for feedback in user_feedback:
            if feedback.champion_id not in champion_feedback_weights:
                champion_feedback_weights[feedback.champion_id] = []
            
            # Convert feedback to weight
            if feedback.feedback_type == 'positive':
                weight = 1.1
            elif feedback.feedback_type == 'negative':
                weight = 0.9
            else:
                weight = 1.0
            
            champion_feedback_weights[feedback.champion_id].append(weight)
        
        # Apply feedback weights to recommendations
        adjusted_recommendations = []
        for recommendation in recommendations:
            if recommendation.champion_id in champion_feedback_weights:
                weights = champion_feedback_weights[recommendation.champion_id]
                avg_weight = statistics.mean(weights)
                
                # Adjust recommendation score
                adjusted_score = recommendation.recommendation_score * avg_weight
                
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
            else:
                adjusted_recommendations.append(recommendation)
        
        # Re-sort by adjusted scores
        adjusted_recommendations.sort(key=lambda r: r.recommendation_score, reverse=True)
        
        return adjusted_recommendations
    
    def _get_counter_pick_recommendations(
        self,
        puuid: str,
        role: str,
        enemy_champion_id: int,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get counter-pick recommendations against a specific enemy champion."""
        try:
            # Get base recommendations
            base_recommendations = self.get_customized_recommendations(
                puuid=puuid,
                role=role,
                user_id=user_id
            )
            
            # Filter and score based on counter-pick potential
            counter_recommendations = []
            
            for recommendation in base_recommendations:
                # Calculate counter-pick score (mock implementation)
                counter_score = self._calculate_counter_pick_score(
                    recommendation.champion_id, enemy_champion_id
                )
                
                if counter_score > 0.1:  # Only include meaningful counters
                    counter_recommendations.append({
                        'champion_id': recommendation.champion_id,
                        'champion_name': recommendation.champion_name,
                        'counter_score': counter_score,
                        'recommendation_score': recommendation.recommendation_score,
                        'combined_score': recommendation.recommendation_score * (1 + counter_score)
                    })
            
            # Sort by combined score
            counter_recommendations.sort(key=lambda r: r['combined_score'], reverse=True)
            
            return counter_recommendations[:5]  # Top 5 counter picks
            
        except Exception as e:
            self.logger.error(f"Error getting counter-pick recommendations: {e}")
            return []
    
    def _calculate_counter_pick_score(self, our_champion_id: int, enemy_champion_id: int) -> float:
        """Calculate counter-pick score between two champions."""
        # Mock implementation - in real system, this would use historical matchup data
        # For now, return a random score for demonstration
        import random
        return random.uniform(0.0, 0.5)
    
    def _get_strategic_ban_suggestions(
        self,
        team_context: Optional[TeamContext],
        ban_phase: BanPhaseSimulation
    ) -> List[Dict[str, Any]]:
        """Get strategic ban suggestions based on team context."""
        suggestions = []
        
        # Mock implementation - suggest high-priority champions to ban
        high_priority_champions = [
            {'champion_id': 1, 'champion_name': 'Annie', 'priority': 'high', 'reason': 'Strong meta pick'},
            {'champion_id': 2, 'champion_name': 'Olaf', 'priority': 'medium', 'reason': 'Counter to our composition'},
            {'champion_id': 3, 'champion_name': 'Twisted Fate', 'priority': 'high', 'reason': 'High impact potential'}
        ]
        
        # Filter out already banned champions
        banned_champions = ban_phase.get_banned_champions()
        suggestions = [
            champ for champ in high_priority_champions
            if champ['champion_id'] not in banned_champions
        ]
        
        return suggestions[:3]  # Top 3 suggestions
    
    def _evaluate_scenario_results(self, scenario: RecommendationScenario) -> Dict[str, Any]:
        """Evaluate scenario results against success criteria."""
        evaluation = {
            'overall_success': False,
            'criteria_met': {},
            'recommendations_match': False,
            'performance_score': 0.0
        }
        
        if not scenario.actual_recommendations:
            return evaluation
        
        # Check if expected recommendations were included
        if scenario.expected_recommendations:
            actual_champion_ids = {rec.champion_id for rec in scenario.actual_recommendations}
            expected_set = set(scenario.expected_recommendations)
            
            overlap = len(actual_champion_ids & expected_set)
            total_expected = len(expected_set)
            
            evaluation['recommendations_match'] = overlap >= (total_expected * 0.5)
            evaluation['recommendation_overlap_ratio'] = overlap / total_expected if total_expected > 0 else 0
        
        # Evaluate success criteria
        criteria_met = 0
        total_criteria = len(scenario.success_criteria)
        
        for criterion, expected_value in scenario.success_criteria.items():
            if criterion == 'min_confidence':
                min_confidence = min(rec.confidence for rec in scenario.actual_recommendations)
                met = min_confidence >= expected_value
            elif criterion == 'min_recommendations':
                met = len(scenario.actual_recommendations) >= expected_value
            elif criterion == 'max_recommendations':
                met = len(scenario.actual_recommendations) <= expected_value
            else:
                met = False  # Unknown criterion
            
            evaluation['criteria_met'][criterion] = met
            if met:
                criteria_met += 1
        
        # Calculate overall success
        if total_criteria > 0:
            evaluation['performance_score'] = criteria_met / total_criteria
            evaluation['overall_success'] = evaluation['performance_score'] >= 0.8
        
        return evaluation
    
    def _calculate_scenario_performance(self, scenario: RecommendationScenario) -> Dict[str, float]:
        """Calculate performance metrics for a scenario."""
        if not scenario.actual_recommendations:
            return {}
        
        metrics = {
            'avg_confidence': statistics.mean(rec.confidence for rec in scenario.actual_recommendations),
            'avg_recommendation_score': statistics.mean(rec.recommendation_score for rec in scenario.actual_recommendations),
            'recommendation_count': len(scenario.actual_recommendations),
            'confidence_variance': statistics.variance(rec.confidence for rec in scenario.actual_recommendations) if len(scenario.actual_recommendations) > 1 else 0.0
        }
        
        return metrics
    
    def _update_feedback_learning(self, feedback: UserFeedback) -> None:
        """Update the feedback learning system with new feedback."""
        # Update feedback weights for the champion/role combination
        key = f"{feedback.champion_id}_{feedback.role}"
        
        if key not in self.feedback_weights:
            self.feedback_weights[key] = 1.0
        
        # Adjust weight based on feedback
        if feedback.feedback_type == 'positive':
            adjustment = self.adaptation_rate
        elif feedback.feedback_type == 'negative':
            adjustment = -self.adaptation_rate
        else:
            adjustment = 0.0
        
        # Apply adjustment with bounds
        self.feedback_weights[key] = max(0.5, min(1.5, self.feedback_weights[key] + adjustment))
    
    def _update_performance_metrics(self, feedback: UserFeedback) -> None:
        """Update overall performance metrics with new feedback."""
        # Update sample size
        self.performance_metrics.sample_size += 1
        
        # Update user satisfaction metrics
        if feedback.feedback_type == 'positive':
            positive_count = 1
        else:
            positive_count = 0
        
        # Calculate running average for positive feedback rate
        current_rate = self.performance_metrics.positive_feedback_rate
        new_rate = ((current_rate * (self.performance_metrics.sample_size - 1)) + positive_count) / self.performance_metrics.sample_size
        self.performance_metrics.positive_feedback_rate = new_rate
        
        # Update role-specific performance
        if feedback.role not in self.performance_metrics.performance_by_role:
            self.performance_metrics.performance_by_role[feedback.role] = 0.0
        
        role_positive_rate = self.performance_metrics.performance_by_role[feedback.role]
        # Simple running average update (in real implementation, would track counts separately)
        self.performance_metrics.performance_by_role[feedback.role] = (role_positive_rate + positive_count) / 2
        
        # Update timestamp
        self.performance_metrics.last_updated = datetime.now()
    
    def _filter_feedback(
        self,
        user_id: Optional[str],
        role: Optional[str],
        time_range: Optional[Tuple[datetime, datetime]]
    ) -> List[UserFeedback]:
        """Filter feedback based on criteria."""
        filtered_feedback = self.feedback_history.copy()
        
        if user_id:
            filtered_feedback = [f for f in filtered_feedback if f.user_id == user_id]
        
        if role:
            filtered_feedback = [f for f in filtered_feedback if f.role == role]
        
        if time_range:
            start_time, end_time = time_range
            filtered_feedback = [
                f for f in filtered_feedback
                if start_time <= f.created_at <= end_time
            ]
        
        return filtered_feedback
    
    def _calculate_performance_metrics(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Calculate performance metrics from feedback list."""
        if not feedback_list:
            return {}
        
        total_feedback = len(feedback_list)
        positive_feedback = len([f for f in feedback_list if f.feedback_type == 'positive'])
        negative_feedback = len([f for f in feedback_list if f.feedback_type == 'negative'])
        
        metrics = {
            'total_feedback': total_feedback,
            'positive_feedback_rate': positive_feedback / total_feedback,
            'negative_feedback_rate': negative_feedback / total_feedback,
            'neutral_feedback_rate': (total_feedback - positive_feedback - negative_feedback) / total_feedback
        }
        
        # Calculate average ratings
        accuracy_ratings = [f.accuracy_rating for f in feedback_list if f.accuracy_rating is not None]
        if accuracy_ratings:
            metrics['avg_accuracy_rating'] = statistics.mean(accuracy_ratings)
            metrics['accuracy_rating_std'] = statistics.stdev(accuracy_ratings) if len(accuracy_ratings) > 1 else 0.0
        
        usefulness_ratings = [f.usefulness_rating for f in feedback_list if f.usefulness_rating is not None]
        if usefulness_ratings:
            metrics['avg_usefulness_rating'] = statistics.mean(usefulness_ratings)
            metrics['usefulness_rating_std'] = statistics.stdev(usefulness_ratings) if len(usefulness_ratings) > 1 else 0.0
        
        # Calculate role-specific metrics
        role_metrics = {}
        for role in ['top', 'jungle', 'middle', 'bottom', 'support']:
            role_feedback = [f for f in feedback_list if f.role == role]
            if role_feedback:
                role_positive = len([f for f in role_feedback if f.feedback_type == 'positive'])
                role_metrics[role] = {
                    'total': len(role_feedback),
                    'positive_rate': role_positive / len(role_feedback)
                }
        
        metrics['role_metrics'] = role_metrics
        
        return metrics
    
    def _generate_performance_insights(
        self,
        feedback_list: List[UserFeedback],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from performance metrics."""
        insights = []
        
        # Overall performance insights
        positive_rate = metrics.get('positive_feedback_rate', 0)
        if positive_rate > 0.8:
            insights.append("Excellent recommendation performance - users are highly satisfied")
        elif positive_rate > 0.6:
            insights.append("Good recommendation performance with room for improvement")
        elif positive_rate > 0.4:
            insights.append("Moderate recommendation performance - consider parameter adjustments")
        else:
            insights.append("Poor recommendation performance - significant improvements needed")
        
        # Role-specific insights
        role_metrics = metrics.get('role_metrics', {})
        for role, role_data in role_metrics.items():
            if role_data['positive_rate'] < 0.4:
                insights.append(f"Low satisfaction for {role} recommendations - review role-specific parameters")
        
        # Rating insights
        if 'avg_accuracy_rating' in metrics:
            avg_accuracy = metrics['avg_accuracy_rating']
            if avg_accuracy < 3.0:
                insights.append("Accuracy ratings are below average - consider improving prediction models")
        
        return insights
    
    def _generate_improvement_recommendations(
        self,
        feedback_list: List[UserFeedback],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement recommendations based on performance analysis."""
        recommendations = []
        
        # Parameter adjustment recommendations
        positive_rate = metrics.get('positive_feedback_rate', 0)
        if positive_rate < 0.5:
            recommendations.append("Consider running parameter optimization based on user feedback")
        
        # Data collection recommendations
        if len(feedback_list) < 50:
            recommendations.append("Collect more user feedback to improve recommendation accuracy")
        
        # Role-specific recommendations
        role_metrics = metrics.get('role_metrics', {})
        low_performing_roles = [
            role for role, data in role_metrics.items()
            if data['positive_rate'] < 0.5
        ]
        
        if low_performing_roles:
            recommendations.append(
                f"Focus on improving recommendations for: {', '.join(low_performing_roles)}"
            )
        
        # Meta and synergy recommendations
        common_negative_tags = []
        for feedback in feedback_list:
            if feedback.feedback_type == 'negative':
                common_negative_tags.extend(feedback.tags)
        
        if 'poor_synergy' in common_negative_tags:
            recommendations.append("Increase team synergy weight in recommendation parameters")
        
        if 'off_meta' in common_negative_tags:
            recommendations.append("Increase meta relevance weight in recommendation parameters")
        
        return recommendations
    
    def _create_detailed_breakdown(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Create detailed breakdown of feedback data."""
        breakdown = {
            'feedback_by_role': defaultdict(list),
            'feedback_by_champion': defaultdict(list),
            'feedback_by_date': defaultdict(list),
            'common_issues': defaultdict(int),
            'success_factors': defaultdict(int)
        }
        
        for feedback in feedback_list:
            # Group by role
            breakdown['feedback_by_role'][feedback.role].append({
                'feedback_type': feedback.feedback_type,
                'champion_id': feedback.champion_id,
                'accuracy_rating': feedback.accuracy_rating,
                'usefulness_rating': feedback.usefulness_rating
            })
            
            # Group by champion
            breakdown['feedback_by_champion'][feedback.champion_id].append({
                'feedback_type': feedback.feedback_type,
                'role': feedback.role,
                'accuracy_rating': feedback.accuracy_rating
            })
            
            # Group by date
            date_key = feedback.created_at.strftime('%Y-%m-%d')
            breakdown['feedback_by_date'][date_key].append(feedback.feedback_type)
            
            # Track issues and success factors
            if feedback.feedback_type == 'negative':
                for tag in feedback.tags:
                    breakdown['common_issues'][tag] += 1
            elif feedback.feedback_type == 'positive':
                for tag in feedback.tags:
                    breakdown['success_factors'][tag] += 1
        
        # Convert defaultdicts to regular dicts
        breakdown['feedback_by_role'] = dict(breakdown['feedback_by_role'])
        breakdown['feedback_by_champion'] = dict(breakdown['feedback_by_champion'])
        breakdown['feedback_by_date'] = dict(breakdown['feedback_by_date'])
        breakdown['common_issues'] = dict(breakdown['common_issues'])
        breakdown['success_factors'] = dict(breakdown['success_factors'])
        
        return breakdown
    
    def _filter_meta_recommendations(self, recommendations: List[ChampionRecommendation]) -> List[ChampionRecommendation]:
        """Filter out off-meta recommendations."""
        # Mock implementation - in real system, would check meta tier data
        return recommendations  # For now, return all recommendations
    
    def _prioritize_comfort_picks(
        self,
        recommendations: List[ChampionRecommendation],
        puuid: str
    ) -> List[ChampionRecommendation]:
        """Prioritize comfort picks based on player experience."""
        # Mock implementation - in real system, would check player's champion experience
        return recommendations  # For now, return recommendations as-is
    
    # Private helper methods
    
    def _update_team_context_with_ban_phase(
        self,
        team_context: TeamContext,
        ban_phase: BanPhaseSimulation
    ) -> TeamContext:
        """Update team context with ban phase information."""
        # Create a copy of team context
        updated_context = TeamContext(
            existing_picks=team_context.existing_picks.copy() if team_context.existing_picks else {},
            banned_champions=ban_phase.get_banned_champions(),
            enemy_composition=team_context.enemy_composition.copy() if team_context.enemy_composition else {},
            available_champions=team_context.available_champions
        )
        
        # Add picks from ban phase
        for role, champion_id in ban_phase.team1_picks:
            if role not in updated_context.existing_picks:
                # Create a mock PlayerRoleAssignment
                from dataclasses import dataclass
                
                @dataclass
                class PlayerRoleAssignment:
                    puuid: str
                    player_name: str
                    role: str
                    champion_id: int
                
                updated_context.existing_picks[role] = PlayerRoleAssignment(
                    puuid="unknown",
                    player_name="Player",
                    role=role,
                    champion_id=champion_id
                )
        
        return updated_context
    
    def _apply_champion_pool_filter(
        self,
        recommendations: List[ChampionRecommendation],
        champion_filter: ChampionPoolFilter,
        puuid: str,
        role: str
    ) -> List[ChampionRecommendation]:
        """Apply champion pool filtering to recommendations."""
        filtered_recommendations = []
        
        # Get player data for filtering
        player_data = self._get_player_data_for_filtering(puuid)
        
        for recommendation in recommendations:
            if champion_filter.apply_filter(
                recommendation.champion_id, 
                role, 
                player_data
            ):
                filtered_recommendations.append(recommendation)
        
        return filtered_recommendations
    
    def _apply_risk_tolerance(
        self,
        recommendations: List[ChampionRecommendation],
        risk_tolerance: float
    ) -> List[ChampionRecommendation]:
        """Apply risk tolerance filtering to recommendations."""
        if risk_tolerance >= 0.8:
            # High risk tolerance - include all recommendations
            return recommendations
        elif risk_tolerance >= 0.5:
            # Medium risk tolerance - filter out very risky picks
            return [rec for rec in recommendations if rec.confidence >= 0.4]
        else:
            # Low risk tolerance - only safe picks
            return [rec for rec in recommendations if rec.confidence >= 0.6]
    
    def _apply_feedback_learning(
        self,
        recommendations: List[ChampionRecommendation],
        user_id: str,
        role: str
    ) -> List[ChampionRecommendation]:
        """Apply learning from user feedback to adjust recommendations."""
        # Get user feedback for this role
        user_feedback = [
            f for f in self.feedback_history 
            if f.user_id == user_id and f.role == role
        ]
        
        if not user_feedback:
            return recommendations
        
        # Calculate feedback weights for each champion
        champion_feedback_weights = defaultdict(list)
        for feedback in user_feedback:
            weight = 1.0
            if feedback.feedback_type == 'positive':
                weight = 1.2
            elif feedback.feedback_type == 'negative':
                weight = 0.8
            
            if feedback.accuracy_rating:
                weight *= (feedback.accuracy_rating / 3.0)  # Scale 1-5 to ~0.33-1.67
            
            champion_feedback_weights[feedback.champion_id].append(weight)
        
        # Apply feedback weights to recommendations
        adjusted_recommendations = []
        for recommendation in recommendations:
            if recommendation.champion_id in champion_feedback_weights:
                weights = champion_feedback_weights[recommendation.champion_id]
                avg_weight = statistics.mean(weights)
                
                # Adjust recommendation score
                adjusted_score = recommendation.recommendation_score * avg_weight
                
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
            else:
                adjusted_recommendations.append(recommendation)
        
        # Re-sort by adjusted scores
        adjusted_recommendations.sort(key=lambda r: r.recommendation_score, reverse=True)
        
        return adjusted_recommendations
    
    def _get_counter_pick_recommendations(
        self,
        puuid: str,
        role: str,
        enemy_champion_id: int,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get recommendations specifically for counter-picking."""
        # This would integrate with the recommendation engine's counter-pick logic
        # For now, return a placeholder
        return [
            {
                'champion_id': 1,  # Placeholder
                'champion_name': 'Counter Champion',
                'counter_strength': 0.8,
                'reasoning': f'Strong against champion {enemy_champion_id}'
            }
        ]
    
    def _get_strategic_ban_suggestions(
        self,
        team_context: Optional[TeamContext],
        ban_phase: BanPhaseSimulation
    ) -> List[Dict[str, Any]]:
        """Get strategic ban suggestions."""
        # This would analyze the current draft state and suggest strategic bans
        # For now, return a placeholder
        return [
            {
                'champion_id': 1,
                'champion_name': 'High Priority Ban',
                'ban_priority': 'high',
                'reasoning': 'Meta dominant champion'
            }
        ]
    
    def _get_player_data_for_filtering(self, puuid: str) -> Dict[str, Any]:
        """Get player data needed for champion pool filtering."""
        # This would fetch actual player data from the analytics engine
        # For now, return a placeholder structure
        return {
            'mastery': {},
            'performance': {},
            'meta': {}
        }
    
    def _evaluate_scenario_results(self, scenario: RecommendationScenario) -> Dict[str, Any]:
        """Evaluate scenario results against success criteria."""
        evaluation = {
            'overall_success': True,
            'criteria_results': {},
            'recommendations_match': False
        }
        
        if scenario.expected_recommendations and scenario.actual_recommendations:
            actual_champion_ids = {rec.champion_id for rec in scenario.actual_recommendations}
            expected_champion_ids = set(scenario.expected_recommendations)
            
            overlap = len(actual_champion_ids & expected_champion_ids)
            total_expected = len(expected_champion_ids)
            
            evaluation['recommendations_match'] = overlap >= (total_expected * 0.5)
            evaluation['overlap_percentage'] = (overlap / total_expected) * 100 if total_expected > 0 else 0
        
        return evaluation
    
    def _calculate_scenario_performance(self, scenario: RecommendationScenario) -> Dict[str, float]:
        """Calculate performance metrics for a scenario."""
        if not scenario.actual_recommendations:
            return {}
        
        return {
            'avg_recommendation_score': statistics.mean([
                rec.recommendation_score for rec in scenario.actual_recommendations
            ]),
            'avg_confidence': statistics.mean([
                rec.confidence for rec in scenario.actual_recommendations
            ]),
            'recommendation_count': len(scenario.actual_recommendations)
        }
    
    def _update_feedback_learning(self, feedback: UserFeedback) -> None:
        """Update the learning system with new feedback."""
        key = f"{feedback.user_id}_{feedback.role}_{feedback.champion_id}"
        
        if key not in self.feedback_weights:
            self.feedback_weights[key] = 1.0
        
        # Adjust weight based on feedback
        adjustment = 0.0
        if feedback.feedback_type == 'positive':
            adjustment = self.adaptation_rate
        elif feedback.feedback_type == 'negative':
            adjustment = -self.adaptation_rate
        
        if feedback.accuracy_rating:
            adjustment *= (feedback.accuracy_rating - 3) / 2  # Scale around neutral (3)
        
        self.feedback_weights[key] = max(0.1, min(2.0, 
            self.feedback_weights[key] + adjustment
        ))
    
    def _update_performance_metrics(self, feedback: UserFeedback) -> None:
        """Update overall performance metrics with new feedback."""
        # Update user satisfaction metrics
        if feedback.accuracy_rating:
            # Update average rating (simplified)
            current_avg = self.performance_metrics.avg_user_rating
            current_count = self.performance_metrics.sample_size
            
            new_avg = ((current_avg * current_count) + feedback.accuracy_rating) / (current_count + 1)
            self.performance_metrics.avg_user_rating = new_avg
        
        # Update positive feedback rate
        if feedback.feedback_type == 'positive':
            current_rate = self.performance_metrics.positive_feedback_rate
            current_count = self.performance_metrics.sample_size
            
            new_rate = ((current_rate * current_count) + 1) / (current_count + 1)
            self.performance_metrics.positive_feedback_rate = new_rate
        
        # Update sample size
        self.performance_metrics.sample_size += 1
        self.performance_metrics.last_updated = datetime.now()
    
    def _filter_feedback(
        self,
        user_id: Optional[str],
        role: Optional[str],
        time_range: Optional[Tuple[datetime, datetime]]
    ) -> List[UserFeedback]:
        """Filter feedback based on criteria."""
        filtered = self.feedback_history
        
        if user_id:
            filtered = [f for f in filtered if f.user_id == user_id]
        
        if role:
            filtered = [f for f in filtered if f.role == role]
        
        if time_range:
            start_time, end_time = time_range
            filtered = [
                f for f in filtered 
                if start_time <= f.created_at <= end_time
            ]
        
        return filtered
    
    def _calculate_performance_metrics(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Calculate performance metrics from feedback list."""
        if not feedback_list:
            return {}
        
        metrics = {
            'total_feedback': len(feedback_list),
            'positive_feedback_count': len([f for f in feedback_list if f.feedback_type == 'positive']),
            'negative_feedback_count': len([f for f in feedback_list if f.feedback_type == 'negative']),
            'neutral_feedback_count': len([f for f in feedback_list if f.feedback_type == 'neutral']),
        }
        
        # Calculate rates
        total = metrics['total_feedback']
        metrics['positive_feedback_rate'] = metrics['positive_feedback_count'] / total
        metrics['negative_feedback_rate'] = metrics['negative_feedback_count'] / total
        
        # Calculate average ratings
        accuracy_ratings = [f.accuracy_rating for f in feedback_list if f.accuracy_rating]
        if accuracy_ratings:
            metrics['avg_accuracy_rating'] = statistics.mean(accuracy_ratings)
            metrics['accuracy_rating_std'] = statistics.stdev(accuracy_ratings) if len(accuracy_ratings) > 1 else 0
        
        usefulness_ratings = [f.usefulness_rating for f in feedback_list if f.usefulness_rating]
        if usefulness_ratings:
            metrics['avg_usefulness_rating'] = statistics.mean(usefulness_ratings)
            metrics['usefulness_rating_std'] = statistics.stdev(usefulness_ratings) if len(usefulness_ratings) > 1 else 0
        
        # Calculate win rate with recommendations
        match_outcomes = [f.match_outcome for f in feedback_list if f.match_outcome is not None]
        if match_outcomes:
            metrics['win_rate_with_recommendations'] = sum(match_outcomes) / len(match_outcomes)
        
        return metrics
    
    def _generate_performance_insights(
        self,
        feedback_list: List[UserFeedback],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from performance metrics."""
        insights = []
        
        if metrics.get('positive_feedback_rate', 0) > 0.7:
            insights.append("High user satisfaction with recommendations")
        elif metrics.get('positive_feedback_rate', 0) < 0.3:
            insights.append("Low user satisfaction - consider adjusting recommendation parameters")
        
        if metrics.get('avg_accuracy_rating', 0) > 4.0:
            insights.append("Recommendations are highly accurate according to users")
        elif metrics.get('avg_accuracy_rating', 0) < 2.5:
            insights.append("Users find recommendations inaccurate - review recommendation logic")
        
        if metrics.get('win_rate_with_recommendations', 0) > 0.6:
            insights.append("Recommendations correlate with positive match outcomes")
        elif metrics.get('win_rate_with_recommendations', 0) < 0.4:
            insights.append("Recommendations may not be leading to successful matches")
        
        return insights
    
    def _generate_improvement_recommendations(
        self,
        feedback_list: List[UserFeedback],
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement recommendations based on performance."""
        recommendations = []
        
        if metrics.get('negative_feedback_rate', 0) > 0.3:
            recommendations.append("Increase confidence thresholds to filter out uncertain recommendations")
        
        if metrics.get('avg_accuracy_rating', 0) < 3.0:
            recommendations.append("Adjust weight parameters to emphasize individual performance over other factors")
        
        if metrics.get('win_rate_with_recommendations', 0) < 0.5:
            recommendations.append("Consider increasing team synergy weight in recommendation calculations")
        
        # Analyze feedback by role
        role_feedback = defaultdict(list)
        for feedback in feedback_list:
            role_feedback[feedback.role].append(feedback)
        
        for role, role_feedback_list in role_feedback.items():
            role_positive_rate = len([f for f in role_feedback_list if f.feedback_type == 'positive']) / len(role_feedback_list)
            if role_positive_rate < 0.4:
                recommendations.append(f"Review recommendation logic for {role} role - low satisfaction rate")
        
        return recommendations
    
    def _create_detailed_breakdown(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Create detailed breakdown of feedback data."""
        breakdown = {
            'by_role': defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0}),
            'by_champion': defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0}),
            'by_time': defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0}),
            'common_tags': defaultdict(int),
            'recent_comments': []
        }
        
        for feedback in feedback_list:
            # By role
            breakdown['by_role'][feedback.role][feedback.feedback_type] += 1
            
            # By champion
            breakdown['by_champion'][feedback.champion_id][feedback.feedback_type] += 1
            
            # By time (monthly)
            month_key = feedback.created_at.strftime('%Y-%m')
            breakdown['by_time'][month_key][feedback.feedback_type] += 1
            
            # Tags
            for tag in feedback.tags:
                breakdown['common_tags'][tag] += 1
            
            # Recent comments
            if feedback.comments and len(breakdown['recent_comments']) < 10:
                breakdown['recent_comments'].append({
                    'comment': feedback.comments,
                    'feedback_type': feedback.feedback_type,
                    'champion_id': feedback.champion_id,
                    'role': feedback.role,
                    'created_at': feedback.created_at.isoformat()
                })
        
        # Convert defaultdicts to regular dicts for JSON serialization
        breakdown['by_role'] = dict(breakdown['by_role'])
        breakdown['by_champion'] = dict(breakdown['by_champion'])
        breakdown['by_time'] = dict(breakdown['by_time'])
        breakdown['common_tags'] = dict(breakdown['common_tags'])
        
        return breakdown