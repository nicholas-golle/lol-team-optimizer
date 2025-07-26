"""
Optimization engine for League of Legends team composition.

This module implements the core optimization algorithm using the Hungarian algorithm
to solve the role assignment problem while maximizing team performance.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.optimize import linear_sum_assignment
from dataclasses import dataclass

from .models import Player, TeamAssignment, PerformanceData, ChampionRecommendation
from .performance_calculator import PerformanceCalculator
from .champion_data import ChampionDataManager


@dataclass
class OptimizationResult:
    """Result of team optimization with multiple ranked solutions."""
    
    assignments: List[TeamAssignment]
    best_assignment: TeamAssignment
    optimization_time: float
    
    def __post_init__(self):
        """Validate optimization result."""
        if not self.assignments:
            raise ValueError("Optimization result must contain at least one assignment")
        if self.best_assignment not in self.assignments:
            raise ValueError("Best assignment must be in the assignments list")


class OptimizationEngine:
    """
    Core optimization engine that solves the role assignment problem.
    
    Uses the Hungarian algorithm to find optimal role assignments that maximize
    team performance while considering individual performance, preferences, and synergy.
    """
    
    def __init__(self, performance_calculator: Optional[PerformanceCalculator] = None, 
                 champion_data_manager: Optional[ChampionDataManager] = None,
                 synergy_database: Optional['SynergyDatabase'] = None):
        """
        Initialize the optimization engine.
        
        Args:
            performance_calculator: Calculator for performance metrics
            champion_data_manager: Manager for champion data
            synergy_database: Database for player synergy data
        """
        self.logger = logging.getLogger(__name__)
        self.performance_calculator = performance_calculator or PerformanceCalculator()
        self.champion_data_manager = champion_data_manager
        self.synergy_database = synergy_database
        self.roles = ["top", "jungle", "middle", "support", "bottom"]
        
        # Optimization weights (can be made configurable)
        self.weights = {
            "individual_performance": 0.6,
            "role_preference": 0.25,
            "team_synergy": 0.15
        }
        
        self.logger.info("Optimization engine initialized")
    
    def optimize_team(self, available_players: List[Player]) -> OptimizationResult:
        """
        Find optimal role assignments for available players.
        
        Args:
            available_players: List of players to assign roles to
            
        Returns:
            OptimizationResult with ranked team assignments
            
        Raises:
            ValueError: If fewer than 5 players provided or optimization fails
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"Starting team optimization for {len(available_players)} players")
        
        # Input validation
        if not available_players:
            raise ValueError("No players provided for optimization")
        
        if len(available_players) < 2:
            raise ValueError(f"At least 2 players required for team optimization, got {len(available_players)}")
        
        # Validate player data
        for i, player in enumerate(available_players):
            if not player.name:
                raise ValueError(f"Player at index {i} has no name")
            if not isinstance(player.role_preferences, dict):
                raise ValueError(f"Player '{player.name}' has invalid role preferences")
        
        try:
            # Generate team combinations based on available players
            if len(available_players) <= 5:
                # Use all available players (even if less than 5)
                team_combinations = [available_players]
                self.logger.info(f"Optimizing team with {len(available_players)} players")
            else:
                # Generate combinations of 5 players from available pool
                from itertools import combinations
                team_combinations = list(combinations(available_players, 5))
                self.logger.info(f"Evaluating {len(team_combinations)} possible team combinations")
                
                # Limit combinations to prevent excessive computation
                if len(team_combinations) > 100:
                    self.logger.warning(f"Too many combinations ({len(team_combinations)}), limiting to first 100")
                    team_combinations = team_combinations[:100]
            
            all_assignments = []
            failed_combinations = 0
            
            for i, team_players in enumerate(team_combinations):
                try:
                    assignment = self._optimize_single_team(list(team_players))
                    if assignment and assignment.is_complete():
                        all_assignments.append(assignment)
                        self.logger.debug(f"Successfully optimized combination {i+1}")
                    else:
                        failed_combinations += 1
                        self.logger.warning(f"Combination {i+1} produced incomplete assignment")
                except Exception as e:
                    failed_combinations += 1
                    self.logger.warning(f"Failed to optimize combination {i+1}: {e}")
                    continue
            
            if failed_combinations > 0:
                self.logger.warning(f"{failed_combinations} team combinations failed optimization")
            
            if not all_assignments:
                raise ValueError("No valid team assignments could be generated - check player data and preferences")
            
            # Sort assignments by total score (descending)
            all_assignments.sort(key=lambda x: x.total_score, reverse=True)
            
            optimization_time = time.time() - start_time
            self.logger.info(f"Optimization completed in {optimization_time:.2f} seconds, found {len(all_assignments)} valid assignments")
            
            return OptimizationResult(
                assignments=all_assignments[:10],  # Return top 10 solutions
                best_assignment=all_assignments[0],
                optimization_time=optimization_time
            )
            
        except Exception as e:
            self.logger.error(f"Optimization failed: {e}", exc_info=True)
            raise ValueError(f"Team optimization failed: {e}") from e
    
    def _optimize_single_team(self, players: List[Player]) -> TeamAssignment:
        """
        Optimize role assignments for available players (2-5 players).
        
        Args:
            players: List of 2-5 players
            
        Returns:
            TeamAssignment with optimal role assignments
        """
        if len(players) < 2:
            raise ValueError("At least 2 players required for single team optimization")
        if len(players) > 5:
            raise ValueError("Maximum 5 players allowed for single team optimization")
        
        # Build cost matrix (we minimize cost, so use negative scores)
        cost_matrix = self._build_cost_matrix(players)
        
        # Solve assignment problem using Hungarian algorithm
        player_indices, role_indices = linear_sum_assignment(cost_matrix)
        
        # Build assignment result
        assignments = {}
        individual_scores = {}
        total_score = 0
        
        for player_idx, role_idx in zip(player_indices, role_indices):
            # Skip dummy assignments (high cost assignments)
            if player_idx >= len(players) or role_idx >= len(self.roles):
                continue
            
            # Skip assignments with very high cost (dummy assignments)
            if cost_matrix[player_idx, role_idx] >= 999.0:
                continue
                
            player = players[player_idx]
            role = self.roles[role_idx]
            assignments[role] = player.name
            
            # Calculate individual score (negative of cost)
            individual_score = -cost_matrix[player_idx, role_idx]
            individual_scores[player.name] = individual_score
            total_score += individual_score
        
        # Calculate synergy scores
        synergy_scores = self._calculate_team_synergy(players, assignments)
        total_score += sum(synergy_scores.values())
        
        # Generate champion recommendations
        champion_recommendations = self._generate_champion_recommendations(players, assignments)
        
        # Generate explanation
        explanation = self._generate_explanation(players, assignments, individual_scores, synergy_scores)
        
        return TeamAssignment(
            assignments=assignments,
            total_score=total_score,
            individual_scores=individual_scores,
            synergy_scores=synergy_scores,
            champion_recommendations=champion_recommendations,
            explanation=explanation
        )
    
    def _build_cost_matrix(self, players: List[Player]) -> np.ndarray:
        """
        Build cost matrix for the assignment problem.
        
        Args:
            players: List of players
            
        Returns:
            Cost matrix where cost[i][j] is the cost of assigning player i to role j
        """
        n_players = len(players)
        n_roles = len(self.roles)
        
        # For fewer than 5 players, we need to create a square matrix
        # by adding dummy players with high cost (so they won't be assigned)
        matrix_size = max(n_players, n_roles)
        cost_matrix = np.full((matrix_size, matrix_size), 1000.0)  # High cost for dummy assignments
        
        # Fill in actual player costs
        for i, player in enumerate(players):
            for j, role in enumerate(self.roles):
                # Calculate individual performance score
                performance_score = self.performance_calculator.calculate_individual_score(
                    player, role
                )
                
                # Get role preference score (1-5, normalize to 0-1)
                preference_score = player.role_preferences.get(role, 3) / 5.0
                
                # Combine scores with weights
                total_score = (
                    self.weights["individual_performance"] * performance_score +
                    self.weights["role_preference"] * preference_score
                )
                
                # Use negative score as cost (since we minimize cost)
                cost_matrix[i, j] = -total_score
        
        return cost_matrix
    
    def _calculate_team_synergy(self, players: List[Player], assignments: Dict[str, str]) -> Dict[Tuple[str, str], float]:
        """
        Calculate synergy scores for all player pairs in the team.
        
        Args:
            players: List of players
            assignments: Role assignments (role -> player_name)
            
        Returns:
            Dictionary of synergy scores for player pairs
        """
        synergy_scores = {}
        player_dict = {p.name: p for p in players}
        
        # Calculate synergy for all player pairs
        assigned_players = list(assignments.values())
        for i, player1_name in enumerate(assigned_players):
            for j, player2_name in enumerate(assigned_players[i+1:], i+1):
                player1 = player_dict[player1_name]
                player2 = player_dict[player2_name]
                
                role1 = next(role for role, name in assignments.items() if name == player1_name)
                role2 = next(role for role, name in assignments.items() if name == player2_name)
                
                synergy_score = self.performance_calculator.calculate_synergy_score(
                    player1, role1, player2, role2, self.synergy_database
                )
                
                synergy_scores[(player1_name, player2_name)] = synergy_score
        
        return synergy_scores
    
    def _generate_champion_recommendations(self, players: List[Player], 
                                         assignments: Dict[str, str]) -> Dict[str, List[ChampionRecommendation]]:
        """
        Generate champion recommendations for each role assignment.
        
        Args:
            players: List of players
            assignments: Role assignments (role -> player_name)
            
        Returns:
            Dictionary mapping roles to champion recommendations
        """
        recommendations = {}
        player_dict = {p.name: p for p in players}
        
        for role, player_name in assignments.items():
            player = player_dict[player_name]
            role_recommendations = []
            
            # Get top champions for this role based on mastery
            top_champions = player.get_top_champions_for_role(role, count=5)
            
            if not top_champions:
                # No mastery data for this role, use overall top champions
                all_masteries = sorted(
                    player.champion_masteries.values(),
                    key=lambda x: x.mastery_points,
                    reverse=True
                )[:3]  # Top 3 overall champions
                
                for mastery in all_masteries:
                    # Check if this champion can play the assigned role
                    role_suitability = self._calculate_role_suitability(mastery, role)
                    
                    confidence = self._calculate_recommendation_confidence(mastery, role_suitability)
                    
                    recommendation = ChampionRecommendation(
                        champion_id=mastery.champion_id,
                        champion_name=mastery.champion_name,
                        mastery_level=mastery.mastery_level,
                        mastery_points=mastery.mastery_points,
                        role_suitability=role_suitability,
                        confidence=confidence
                    )
                    role_recommendations.append(recommendation)
            else:
                # Use role-specific champions
                for mastery in top_champions:
                    # Calculate role suitability based on champion data
                    role_suitability = self._calculate_role_suitability(mastery, role)
                    
                    confidence = self._calculate_recommendation_confidence(mastery, role_suitability)
                    
                    recommendation = ChampionRecommendation(
                        champion_id=mastery.champion_id,
                        champion_name=mastery.champion_name,
                        mastery_level=mastery.mastery_level,
                        mastery_points=mastery.mastery_points,
                        role_suitability=role_suitability,
                        confidence=confidence
                    )
                    role_recommendations.append(recommendation)
            
            # Sort by confidence and role suitability
            role_recommendations.sort(
                key=lambda x: (x.confidence * x.role_suitability), 
                reverse=True
            )
            
            # Keep top 3 recommendations per role
            recommendations[role] = role_recommendations[:3]
        
        return recommendations
    
    def _calculate_recommendation_confidence(self, mastery, role_suitability: float) -> float:
        """
        Calculate confidence in a champion recommendation.
        
        Args:
            mastery: ChampionMastery object
            role_suitability: How well the champion fits the role (0-1)
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence from mastery level
        level_confidence = mastery.mastery_level / 7.0
        
        # Points confidence (logarithmic scale)
        points_confidence = min(mastery.mastery_points / 50000.0, 1.0)
        
        # Combine factors
        mastery_confidence = (level_confidence * 0.6) + (points_confidence * 0.4)
        
        # Factor in role suitability
        final_confidence = (mastery_confidence * 0.7) + (role_suitability * 0.3)
        
        return max(0.0, min(1.0, final_confidence))
    
    def _calculate_role_suitability(self, mastery, role: str) -> float:
        """
        Calculate how suitable a champion is for a specific role.
        
        Args:
            mastery: ChampionMastery object
            role: Role to evaluate suitability for
            
        Returns:
            Role suitability score (0-1)
        """
        if not self.champion_data_manager:
            # If no champion data manager, assume moderate suitability
            return 0.6
        
        # Get champion's primary roles
        champion_roles = self.champion_data_manager.get_champion_roles(mastery.champion_id)
        
        if not champion_roles:
            # No role data available
            return 0.5
        
        if role in champion_roles:
            # Champion can play this role
            if len(champion_roles) == 1:
                # Champion is specialized for this role
                return 0.95
            elif len(champion_roles) == 2:
                # Champion can play 2 roles well
                return 0.85
            else:
                # Champion is flexible but less specialized
                return 0.75
        else:
            # Champion is not typically played in this role
            # But some champions can be flexed (e.g., mages to support)
            
            # Check for common flex picks
            flex_compatibility = self._check_flex_compatibility(mastery.champion_id, champion_roles, role)
            if flex_compatibility > 0:
                return flex_compatibility
            
            # Very poor fit for this role
            return 0.2
    
    def _check_flex_compatibility(self, champion_id: int, champion_roles: List[str], target_role: str) -> float:
        """
        Check if a champion can be flexed to a different role.
        
        Args:
            champion_id: Champion ID
            champion_roles: Champion's primary roles
            target_role: Role we want to flex to
            
        Returns:
            Flex compatibility score (0-1)
        """
        # Common flex patterns
        flex_patterns = {
            # Mages can often support
            ('middle', 'support'): 0.6,
            # Some supports can mid
            ('support', 'middle'): 0.4,
            # ADCs can sometimes mid
            ('bottom', 'middle'): 0.3,
            # Some mids can ADC
            ('middle', 'bottom'): 0.3,
            # Tanks can often flex between top and jungle
            ('top', 'jungle'): 0.7,
            ('jungle', 'top'): 0.7,
            # Some junglers can support
            ('jungle', 'support'): 0.4,
            # Some tops can support (tank supports)
            ('top', 'support'): 0.5,
        }
        
        # Check if any of the champion's roles can flex to target role
        max_flex = 0.0
        for champ_role in champion_roles:
            flex_key = (champ_role, target_role)
            if flex_key in flex_patterns:
                max_flex = max(max_flex, flex_patterns[flex_key])
        
        return max_flex
    
    def _generate_explanation(self, players: List[Player], assignments: Dict[str, str], 
                            individual_scores: Dict[str, float], 
                            synergy_scores: Dict[Tuple[str, str], float]) -> str:
        """
        Generate detailed explanation for the team assignment.
        
        Args:
            players: List of players
            assignments: Role assignments
            individual_scores: Individual performance scores
            synergy_scores: Team synergy scores
            
        Returns:
            Detailed explanation string
        """
        explanation_parts = ["Team Assignment Explanation:", ""]
        
        # Individual assignments with detailed analysis
        explanation_parts.append("Role Assignments:")
        player_dict = {p.name: p for p in players}
        
        for role, player_name in assignments.items():
            player = player_dict[player_name]
            preference = player.role_preferences.get(role, 3)
            individual_score = individual_scores[player_name]
            
            # Get performance data for more detailed explanation
            performance_data = player.performance_cache.get(role, {})
            
            explanation_parts.append(f"  {role.upper()}: {player_name}")
            explanation_parts.append(f"    Performance Score: {individual_score:.2f}")
            explanation_parts.append(f"    Role Preference: {preference}/5 ({self._preference_description(preference)})")
            
            if performance_data:
                win_rate = performance_data.get('win_rate', 0) * 100
                matches = performance_data.get('matches_played', 0)
                explanation_parts.append(f"    Recent Stats: {win_rate:.1f}% WR over {matches} games")
                
                if performance_data.get('avg_kda', 0) > 0:
                    explanation_parts.append(f"    Average KDA: {performance_data.get('avg_kda', 0):.1f}")
            else:
                explanation_parts.append("    Stats: Limited data available")
            
            explanation_parts.append("")
        
        # Synergy analysis with role context
        if synergy_scores:
            explanation_parts.append("Team Synergy Analysis:")
            sorted_synergy = sorted(synergy_scores.items(), key=lambda x: x[1], reverse=True)
            
            for (player1, player2), score in sorted_synergy:
                role1 = next(role for role, name in assignments.items() if name == player1)
                role2 = next(role for role, name in assignments.items() if name == player2)
                
                synergy_desc = self._synergy_description(score)
                explanation_parts.append(f"  {player1} ({role1}) + {player2} ({role2}): {score:+.2f} ({synergy_desc})")
            
            explanation_parts.append("")
        
        # Strategic analysis
        explanation_parts.extend(self._generate_strategic_analysis(players, assignments, individual_scores))
        
        # Overall score breakdown with weights
        total_individual = sum(individual_scores.values())
        total_synergy = sum(synergy_scores.values())
        total_score = total_individual + total_synergy
        
        explanation_parts.extend([
            "Score Breakdown:",
            f"  Individual Performance: {total_individual:.2f} (weight: {self.weights['individual_performance']:.0%})",
            f"  Team Synergy: {total_synergy:.2f} (weight: {self.weights['team_synergy']:.0%})",
            f"  Total Score: {total_score:.2f}"
        ])
        
        return "\n".join(explanation_parts)
    
    def _preference_description(self, preference: int) -> str:
        """Convert preference number to descriptive text."""
        descriptions = {
            1: "Strongly Dislikes",
            2: "Dislikes", 
            3: "Neutral",
            4: "Prefers",
            5: "Strongly Prefers"
        }
        return descriptions.get(preference, "Unknown")
    
    def _synergy_description(self, score: float) -> str:
        """Convert synergy score to descriptive text."""
        if score >= 0.1:
            return "Excellent synergy"
        elif score >= 0.05:
            return "Good synergy"
        elif score >= 0:
            return "Neutral synergy"
        elif score >= -0.05:
            return "Minor conflict"
        else:
            return "Poor synergy"
    
    def _generate_strategic_analysis(self, players: List[Player], assignments: Dict[str, str], 
                                   individual_scores: Dict[str, float]) -> List[str]:
        """Generate strategic insights about the team composition."""
        analysis = ["Strategic Analysis:"]
        player_dict = {p.name: p for p in players}
        
        # Analyze role satisfaction
        satisfied_players = 0
        dissatisfied_players = []
        
        for role, player_name in assignments.items():
            player = player_dict[player_name]
            preference = player.role_preferences.get(role, 3)
            
            if preference >= 4:
                satisfied_players += 1
            elif preference <= 2:
                dissatisfied_players.append((player_name, role, preference))
        
        analysis.append(f"  Role Satisfaction: {satisfied_players}/5 players in preferred roles")
        
        if dissatisfied_players:
            analysis.append("  Potential Issues:")
            for player_name, role, pref in dissatisfied_players:
                analysis.append(f"    {player_name} may struggle in {role} (preference: {pref}/5)")
        
        # Analyze team balance
        avg_score = sum(individual_scores.values()) / len(individual_scores)
        weak_roles = [(role, player) for role, player in assignments.items() 
                     if individual_scores.get(player, 0) < avg_score * 0.8]
        
        if weak_roles:
            analysis.append("  Team Balance:")
            for role, player in weak_roles:
                analysis.append(f"    {role.capitalize()} may need support ({player})")
        
        # Suggest focus areas
        analysis.append("  Recommended Focus:")
        if len(dissatisfied_players) > 1:
            analysis.append("    Practice role flexibility with assigned players")
        if weak_roles:
            analysis.append("    Provide extra support for weaker roles during games")
        if satisfied_players >= 4:
            analysis.append("    Strong role alignment - focus on team coordination")
        
        analysis.append("")
        return analysis
    
    def get_alternative_assignments(self, result: OptimizationResult, count: int = 3) -> List[TeamAssignment]:
        """
        Get alternative team assignments from optimization result.
        
        Args:
            result: Optimization result
            count: Number of alternatives to return
            
        Returns:
            List of alternative assignments
        """
        return result.assignments[1:count+1] if len(result.assignments) > 1 else []
    
    def generate_alternative_compositions(self, available_players: List[Player], 
                                        primary_result: OptimizationResult) -> List[TeamAssignment]:
        """
        Generate alternative team compositions using different optimization strategies.
        
        Args:
            available_players: List of players to consider
            primary_result: Primary optimization result to compare against
            
        Returns:
            List of alternative team assignments
        """
        alternatives = []
        
        if len(available_players) < 5:
            return alternatives
        
        # Strategy 1: Preference-weighted optimization
        alternatives.extend(self._optimize_with_preference_weight(available_players, 0.8))
        
        # Strategy 2: Performance-weighted optimization  
        alternatives.extend(self._optimize_with_performance_weight(available_players, 0.9))
        
        # Strategy 3: Synergy-focused optimization
        alternatives.extend(self._optimize_with_synergy_focus(available_players))
        
        # Strategy 4: Role-balanced optimization (ensure no player is too far from preferred role)
        alternatives.extend(self._optimize_role_balanced(available_players))
        
        # Filter out duplicates and assignments too similar to primary
        unique_alternatives = self._filter_unique_assignments(alternatives, primary_result)
        
        # Sort by score and return top alternatives
        unique_alternatives.sort(key=lambda x: x.total_score, reverse=True)
        return unique_alternatives[:5]
    
    def _optimize_with_preference_weight(self, players: List[Player], weight: float) -> List[TeamAssignment]:
        """Optimize with higher preference weighting."""
        original_weights = self.weights.copy()
        self.weights["role_preference"] = weight
        self.weights["individual_performance"] = (1 - weight) * 0.7
        self.weights["team_synergy"] = (1 - weight) * 0.3
        
        try:
            if len(players) == 5:
                result = self._optimize_single_team(players)
                return [result] if result and result.is_complete() else []
            else:
                from itertools import combinations
                best_assignments = []
                for team in list(combinations(players, 5))[:10]:  # Limit combinations
                    assignment = self._optimize_single_team(list(team))
                    if assignment and assignment.is_complete():
                        best_assignments.append(assignment)
                return sorted(best_assignments, key=lambda x: x.total_score, reverse=True)[:3]
        finally:
            self.weights = original_weights
    
    def _optimize_with_performance_weight(self, players: List[Player], weight: float) -> List[TeamAssignment]:
        """Optimize with higher performance weighting."""
        original_weights = self.weights.copy()
        self.weights["individual_performance"] = weight
        self.weights["role_preference"] = (1 - weight) * 0.6
        self.weights["team_synergy"] = (1 - weight) * 0.4
        
        try:
            if len(players) == 5:
                result = self._optimize_single_team(players)
                return [result] if result and result.is_complete() else []
            else:
                from itertools import combinations
                best_assignments = []
                for team in list(combinations(players, 5))[:10]:
                    assignment = self._optimize_single_team(list(team))
                    if assignment and assignment.is_complete():
                        best_assignments.append(assignment)
                return sorted(best_assignments, key=lambda x: x.total_score, reverse=True)[:3]
        finally:
            self.weights = original_weights
    
    def _optimize_with_synergy_focus(self, players: List[Player]) -> List[TeamAssignment]:
        """Optimize with focus on team synergy."""
        original_weights = self.weights.copy()
        self.weights["team_synergy"] = 0.5
        self.weights["individual_performance"] = 0.3
        self.weights["role_preference"] = 0.2
        
        try:
            if len(players) == 5:
                result = self._optimize_single_team(players)
                return [result] if result and result.is_complete() else []
            else:
                from itertools import combinations
                best_assignments = []
                for team in list(combinations(players, 5))[:10]:
                    assignment = self._optimize_single_team(list(team))
                    if assignment and assignment.is_complete():
                        best_assignments.append(assignment)
                return sorted(best_assignments, key=lambda x: x.total_score, reverse=True)[:3]
        finally:
            self.weights = original_weights
    
    def _optimize_role_balanced(self, players: List[Player]) -> List[TeamAssignment]:
        """Optimize ensuring players are close to their preferred roles."""
        # Find assignments where each player gets at least their 2nd preferred role
        if len(players) < 5:
            return []
        
        from itertools import combinations, permutations
        
        best_assignments = []
        player_combinations = list(combinations(players, 5)) if len(players) > 5 else [players]
        
        for team_players in player_combinations[:5]:  # Limit combinations
            # Try different role permutations focusing on preference satisfaction
            for role_perm in permutations(self.roles):
                assignment = {}
                individual_scores = {}
                valid = True
                
                for i, player in enumerate(team_players):
                    role = role_perm[i]
                    preference = player.role_preferences.get(role, 3)
                    
                    # Skip if player really dislikes this role
                    if preference < 2:
                        valid = False
                        break
                    
                    assignment[role] = player.name
                    individual_scores[player.name] = self.performance_calculator.calculate_individual_score(player, role)
                
                if valid and len(assignment) == 5:
                    # Calculate synergy and create team assignment
                    synergy_scores = self._calculate_team_synergy(list(team_players), assignment)
                    total_score = sum(individual_scores.values()) + sum(synergy_scores.values())
                    
                    explanation = self._generate_explanation(list(team_players), assignment, individual_scores, synergy_scores)
                    
                    team_assignment = TeamAssignment(
                        assignments=assignment,
                        total_score=total_score,
                        individual_scores=individual_scores,
                        synergy_scores=synergy_scores,
                        explanation=explanation
                    )
                    
                    best_assignments.append(team_assignment)
                    break  # Found valid assignment for this team
        
        return sorted(best_assignments, key=lambda x: x.total_score, reverse=True)[:3]
    
    def _filter_unique_assignments(self, assignments: List[TeamAssignment], 
                                 primary: OptimizationResult) -> List[TeamAssignment]:
        """Filter out duplicate or too-similar assignments."""
        unique = []
        primary_assignment = primary.best_assignment.assignments
        
        for assignment in assignments:
            # Skip if too similar to primary (more than 3 same role assignments)
            same_assignments = sum(1 for role in self.roles 
                                 if assignment.assignments.get(role) == primary_assignment.get(role))
            if same_assignments >= 4:
                continue
            
            # Skip if duplicate of existing alternative
            is_duplicate = False
            for existing in unique:
                same_count = sum(1 for role in self.roles 
                               if assignment.assignments.get(role) == existing.assignments.get(role))
                if same_count >= 4:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(assignment)
        
        return unique
    
    def compare_assignments(self, assignment1: TeamAssignment, assignment2: TeamAssignment) -> str:
        """
        Compare two team assignments and explain the differences.
        
        Args:
            assignment1: First assignment
            assignment2: Second assignment
            
        Returns:
            Comparison explanation
        """
        comparison_parts = ["Assignment Comparison:", ""]
        
        # Score comparison
        score_diff = assignment1.total_score - assignment2.total_score
        comparison_parts.append(f"Score Difference: {score_diff:+.2f}")
        comparison_parts.append("")
        
        # Role differences
        differences = []
        for role in self.roles:
            player1 = assignment1.assignments.get(role)
            player2 = assignment2.assignments.get(role)
            if player1 != player2:
                differences.append(f"  {role.upper()}: {player1} → {player2}")
        
        if differences:
            comparison_parts.append("Role Changes:")
            comparison_parts.extend(differences)
        else:
            comparison_parts.append("No role changes between assignments.")
        
        return "\n".join(comparison_parts)