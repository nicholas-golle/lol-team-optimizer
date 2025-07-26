"""
Performance calculation engine for League of Legends players.

This module calculates individual player performance metrics and team synergy scores
based on historical match data and role-specific statistics.
"""

from typing import Dict, List, Optional
from .models import Player, PerformanceData, ChampionMastery
from .champion_data import ChampionDataManager


class PerformanceCalculator:
    """
    Calculator for individual player performance and team synergy metrics.
    
    Analyzes player performance in different roles and calculates synergy scores
    between player pairs based on historical data.
    """
    
    def __init__(self, champion_data_manager: Optional[ChampionDataManager] = None):
        """Initialize the performance calculator."""
        self.champion_data_manager = champion_data_manager
        
        # Default performance weights for different metrics
        self.performance_weights = {
            "win_rate": 0.3,
            "kda": 0.2,
            "cs_per_min": 0.15,
            "vision_score": 0.1,
            "recent_form": 0.1,
            "champion_mastery": 0.15  # New weight for champion mastery
        }
        
        # Role-specific metric weights (including champion mastery)
        self.role_weights = {
            "top": {"cs_per_min": 0.25, "kda": 0.25, "win_rate": 0.3, "champion_mastery": 0.2},
            "jungle": {"vision_score": 0.15, "kda": 0.25, "win_rate": 0.35, "champion_mastery": 0.25},
            "middle": {"cs_per_min": 0.2, "kda": 0.3, "win_rate": 0.3, "champion_mastery": 0.2},
            "support": {"vision_score": 0.3, "kda": 0.15, "win_rate": 0.35, "champion_mastery": 0.2},
            "bottom": {"cs_per_min": 0.25, "kda": 0.25, "win_rate": 0.3, "champion_mastery": 0.2}
        }
    
    def calculate_individual_score(self, player: Player, role: str) -> float:
        """
        Calculate individual performance score for a player in a specific role.
        
        Args:
            player: Player to calculate score for
            role: Role to calculate performance in
            
        Returns:
            Normalized performance score (0.0 to 1.0)
        """
        # Get cached performance data for the role
        performance_data = player.performance_cache.get(role)
        
        if not performance_data:
            # No performance data available, use neutral score based on preference
            preference_score = player.role_preferences.get(role, 3) / 5.0
            return preference_score * 0.5  # Reduced score due to lack of data
        
        # Create PerformanceData object if we have raw data
        if isinstance(performance_data, dict):
            perf = PerformanceData(
                role=role,
                matches_played=performance_data.get("matches_played", 0),
                win_rate=performance_data.get("win_rate", 0.0),
                avg_kda=performance_data.get("avg_kda", 0.0),
                avg_cs_per_min=performance_data.get("avg_cs_per_min", 0.0),
                avg_vision_score=performance_data.get("avg_vision_score", 0.0),
                recent_form=performance_data.get("recent_form", 0.0)
            )
        else:
            perf = performance_data
        
        # Calculate weighted score based on role-specific importance
        role_weights = self.role_weights.get(role, self.performance_weights)
        
        # Normalize individual metrics
        normalized_scores = {
            "win_rate": perf.win_rate,  # Already 0-1
            "kda": min(perf.avg_kda / 3.0, 1.0),  # Cap at 3.0 KDA = 1.0 score
            "cs_per_min": min(perf.avg_cs_per_min / 8.0, 1.0),  # Cap at 8 CS/min = 1.0 score
            "vision_score": min(perf.avg_vision_score / 50.0, 1.0),  # Cap at 50 vision = 1.0 score
            "recent_form": (perf.recent_form + 1) / 2.0  # Convert -1,1 to 0,1
        }
        
        # Add champion mastery score
        champion_mastery_score = self.calculate_champion_mastery_score(player, role)
        normalized_scores["champion_mastery"] = champion_mastery_score
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in role_weights.items():
            if metric in normalized_scores:
                total_score += normalized_scores[metric] * weight
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.5  # Default neutral score
        
        # Apply penalty for low match count
        if perf.matches_played < 10:
            confidence_penalty = perf.matches_played / 10.0
            final_score *= confidence_penalty
        
        return max(0.0, min(1.0, final_score))
    
    def calculate_champion_mastery_score(self, player: Player, role: str) -> float:
        """
        Calculate champion mastery score for a player in a specific role.
        
        Args:
            player: Player to calculate mastery score for
            role: Role to calculate mastery for
            
        Returns:
            Normalized mastery score (0.0 to 1.0)
        """
        if not player.champion_masteries:
            # No mastery data, use preference as fallback
            preference = player.role_preferences.get(role, 3)
            return (preference / 5.0) * 0.5  # Reduced score due to no mastery data
        
        # Get champions for this role
        role_champions = player.get_top_champions_for_role(role, count=5)
        
        if not role_champions:
            # No champions for this role, use overall mastery as indicator
            total_mastery_score = self._calculate_overall_mastery_score(player)
            return min(total_mastery_score * 0.3, 0.4)  # Cap at 0.4 for non-role champions
        
        # Calculate weighted mastery score for role
        total_score = 0.0
        total_weight = 0.0
        
        for i, mastery in enumerate(role_champions):
            # Weight decreases for lower-ranked champions
            weight = 1.0 / (i + 1)  # 1.0, 0.5, 0.33, 0.25, 0.2
            
            # Calculate individual champion mastery score
            champion_score = self._calculate_individual_champion_score(mastery)
            
            total_score += champion_score * weight
            total_weight += weight
        
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.3  # Default low score
        
        return max(0.0, min(1.0, final_score))
    
    def _calculate_individual_champion_score(self, mastery: ChampionMastery) -> float:
        """
        Calculate score for individual champion mastery.
        
        Args:
            mastery: ChampionMastery object
            
        Returns:
            Normalized score (0.0 to 1.0)
        """
        # Base score from mastery level (0-7 -> 0-1)
        level_score = mastery.mastery_level / 7.0
        
        # Points score (logarithmic scale, 100k points = 1.0)
        points_score = min(mastery.mastery_points / 100000.0, 1.0)
        
        # Combine level and points (level is more important)
        combined_score = (level_score * 0.7) + (points_score * 0.3)
        
        # Bonus for high mastery levels
        if mastery.mastery_level >= 6:
            combined_score += 0.1
        if mastery.mastery_level == 7:
            combined_score += 0.1
        
        return max(0.0, min(1.0, combined_score))
    
    def _calculate_overall_mastery_score(self, player: Player) -> float:
        """
        Calculate overall mastery score across all champions.
        
        Args:
            player: Player to calculate for
            
        Returns:
            Normalized overall mastery score
        """
        if not player.champion_masteries:
            return 0.0
        
        # Get top 10 champions by mastery points
        top_masteries = sorted(
            player.champion_masteries.values(),
            key=lambda x: x.mastery_points,
            reverse=True
        )[:10]
        
        total_score = 0.0
        for i, mastery in enumerate(top_masteries):
            weight = 1.0 / (i + 1)  # Decreasing weight
            champion_score = self._calculate_individual_champion_score(mastery)
            total_score += champion_score * weight
        
        # Normalize by maximum possible score
        max_possible = sum(1.0 / (i + 1) for i in range(len(top_masteries)))
        if max_possible > 0:
            return total_score / max_possible
        else:
            return 0.0
    
    def get_role_champion_pool(self, player: Player, role: str) -> List[ChampionMastery]:
        """
        Get champion pool for a specific role with mastery information.
        
        Args:
            player: Player to get champion pool for
            role: Role to get champions for
            
        Returns:
            List of ChampionMastery objects for the role
        """
        return player.get_top_champions_for_role(role, count=10)
    
    def analyze_champion_pool_depth(self, player: Player, role: str) -> Dict[str, any]:
        """
        Analyze the depth and quality of a player's champion pool for a role.
        
        Args:
            player: Player to analyze
            role: Role to analyze
            
        Returns:
            Dictionary containing pool analysis
        """
        champions = self.get_role_champion_pool(player, role)
        
        if not champions:
            return {
                "pool_size": 0,
                "average_mastery": 0.0,
                "depth_score": 0.0,
                "recommendation": f"No champions available for {role} - learn role-appropriate champions"
            }
        
        # Calculate metrics
        pool_size = len(champions)
        total_mastery_score = sum(self._calculate_individual_champion_score(champ) for champ in champions)
        average_mastery = total_mastery_score / pool_size if pool_size > 0 else 0.0
        
        # Depth score considers both size and quality
        size_score = min(pool_size / 5.0, 1.0)  # 5+ champions = full size score
        quality_score = average_mastery
        depth_score = (size_score * 0.4) + (quality_score * 0.6)
        
        # Generate recommendation
        if depth_score >= 0.8:
            recommendation = f"Excellent {role} champion pool - very versatile"
        elif depth_score >= 0.6:
            recommendation = f"Good {role} champion pool - solid role coverage"
        elif depth_score >= 0.4:
            recommendation = f"Adequate {role} champion pool - consider expanding"
        else:
            recommendation = f"Limited {role} champion pool - focus on learning more champions"
        
        return {
            "pool_size": pool_size,
            "average_mastery": average_mastery,
            "depth_score": depth_score,
            "top_champions": [
                {
                    "name": champ.champion_name,
                    "mastery_level": champ.mastery_level,
                    "mastery_points": champ.mastery_points,
                    "score": self._calculate_individual_champion_score(champ)
                }
                for champ in champions[:3]  # Top 3
            ],
            "recommendation": recommendation
        }
    
    def calculate_synergy_score(self, player1: Player, role1: str, 
                              player2: Player, role2: str, 
                              synergy_db: Optional['SynergyDatabase'] = None) -> float:
        """
        Calculate synergy score between two players in specific roles.
        
        Args:
            player1: First player
            role1: Role of first player
            player2: Second player
            role2: Role of second player
            synergy_db: Optional synergy database for historical data
            
        Returns:
            Synergy score (-0.3 to 0.3, where positive is good synergy)
        """
        # If we have synergy database, use historical data
        if synergy_db:
            synergy_data = synergy_db.get_synergy(player1.name, player2.name)
            
            if synergy_data.games_together >= 3:
                # Use historical synergy data
                historical_synergy = synergy_data.calculate_overall_synergy_score()
                
                # Get role-specific synergy if available
                role_synergy = synergy_data.get_role_synergy_score(role1, role2)
                role_adjustment = (role_synergy - 0.5) * 0.1  # Convert to -0.05 to 0.05 range
                
                # Combine historical and role-specific synergy
                total_synergy = historical_synergy + role_adjustment
                
                return max(-0.3, min(0.3, total_synergy))
        
        # Fallback to role compatibility matrix if no historical data
        synergy_matrix = {
            ("top", "jungle"): 0.1,
            ("jungle", "middle"): 0.15,
            ("middle", "support"): 0.05,
            ("support", "bottom"): 0.2,
            ("bottom", "support"): 0.2,
            ("top", "support"): 0.05,
            ("jungle", "support"): 0.1,
            ("jungle", "bottom"): 0.05,
            ("top", "middle"): 0.05,
            ("middle", "bottom"): 0.05
        }
        
        # Get base synergy from role compatibility
        base_synergy = synergy_matrix.get((role1, role2), 0.0)
        base_synergy += synergy_matrix.get((role2, role1), 0.0)
        
        # Modify based on individual performance levels
        perf1 = self.calculate_individual_score(player1, role1)
        perf2 = self.calculate_individual_score(player2, role2)
        
        # Higher performing players have better synergy potential
        performance_bonus = (perf1 + perf2 - 1.0) * 0.05
        
        # Check for complementary preferences (players who prefer different roles)
        pref1 = player1.role_preferences.get(role1, 3)
        pref2 = player2.role_preferences.get(role2, 3)
        
        # Bonus if both players prefer their assigned roles
        if pref1 >= 4 and pref2 >= 4:
            preference_bonus = 0.05
        elif pref1 <= 2 or pref2 <= 2:
            preference_bonus = -0.05
        else:
            preference_bonus = 0.0
        
        total_synergy = base_synergy + performance_bonus + preference_bonus
        
        # Clamp to reasonable range (reduced from historical data range)
        return max(-0.2, min(0.2, total_synergy))
    
    def normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize a dictionary of scores to 0-1 range.
        
        Args:
            scores: Dictionary of raw scores
            
        Returns:
            Dictionary of normalized scores
        """
        if not scores:
            return {}
        
        values = list(scores.values())
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            # All scores are the same
            return {key: 0.5 for key in scores.keys()}
        
        normalized = {}
        for key, value in scores.items():
            normalized[key] = (value - min_val) / (max_val - min_val)
        
        return normalized
    
    def get_role_performance_summary(self, player: Player) -> Dict[str, float]:
        """
        Get performance summary for all roles for a player.
        
        Args:
            player: Player to get summary for
            
        Returns:
            Dictionary of role -> performance score
        """
        summary = {}
        roles = ["top", "jungle", "middle", "support", "bottom"]
        
        for role in roles:
            summary[role] = self.calculate_individual_score(player, role)
        
        return summary
    
    def analyze_performance_trends(self, player: Player, role: str) -> Dict[str, any]:
        """
        Analyze performance trends for a player in a specific role.
        
        Args:
            player: Player to analyze
            role: Role to analyze trends for
            
        Returns:
            Dictionary containing trend analysis data
        """
        performance_data = player.performance_cache.get(role, {})
        
        if not performance_data:
            return {
                "trend": "no_data",
                "direction": "unknown",
                "confidence": 0.0,
                "recent_form": 0.0,
                "recommendation": "Need more match data to analyze trends"
            }
        
        recent_form = performance_data.get('recent_form', 0.0)
        matches_played = performance_data.get('matches_played', 0)
        win_rate = performance_data.get('win_rate', 0.0)
        
        # Determine trend direction
        if recent_form > 0.2:
            direction = "improving"
            trend = "positive"
        elif recent_form < -0.2:
            direction = "declining"
            trend = "negative"
        else:
            direction = "stable"
            trend = "neutral"
        
        # Calculate confidence based on sample size
        confidence = min(matches_played / 20.0, 1.0)  # Full confidence at 20+ games
        
        # Generate recommendation
        recommendation = self._generate_trend_recommendation(
            trend, direction, win_rate, matches_played, recent_form
        )
        
        return {
            "trend": trend,
            "direction": direction,
            "confidence": confidence,
            "recent_form": recent_form,
            "matches_analyzed": matches_played,
            "win_rate": win_rate,
            "recommendation": recommendation
        }
    
    def _generate_trend_recommendation(self, trend: str, direction: str, win_rate: float, 
                                     matches: int, recent_form: float) -> str:
        """Generate recommendation based on trend analysis."""
        if matches < 5:
            return "Play more games in this role to establish performance baseline"
        
        if trend == "positive":
            if win_rate > 0.6:
                return f"Excellent {direction} performance - prioritize this role"
            else:
                return f"Performance is {direction} - good role option with practice"
        
        elif trend == "negative":
            if win_rate < 0.4:
                return f"Performance {direction} - consider alternative roles or focused practice"
            else:
                return f"Recent dip in performance - may recover with continued play"
        
        else:  # neutral/stable
            if win_rate > 0.55:
                return "Consistent solid performance - reliable role choice"
            elif win_rate < 0.45:
                return "Consistently struggling - consider role change or intensive practice"
            else:
                return "Average performance - room for improvement with focused practice"
    
    def get_comprehensive_player_analysis(self, player: Player) -> Dict[str, any]:
        """
        Get comprehensive analysis of player performance across all roles.
        
        Args:
            player: Player to analyze
            
        Returns:
            Dictionary containing comprehensive analysis
        """
        analysis = {
            "player_name": player.name,
            "role_scores": {},
            "role_trends": {},
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        roles = ["top", "jungle", "middle", "support", "bottom"]
        role_scores = {}
        
        # Analyze each role
        for role in roles:
            score = self.calculate_individual_score(player, role)
            trend = self.analyze_performance_trends(player, role)
            
            role_scores[role] = score
            analysis["role_scores"][role] = score
            analysis["role_trends"][role] = trend
        
        # Identify strengths and weaknesses
        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Top 2 roles are strengths
        for role, score in sorted_roles[:2]:
            if score > 0.6:
                preference = player.role_preferences.get(role, 3)
                pref_text = "and enjoys" if preference >= 4 else "but doesn't prefer"
                analysis["strengths"].append(f"{role.capitalize()}: Strong performance ({score:.2f}) {pref_text} this role")
        
        # Bottom 2 roles are potential weaknesses
        for role, score in sorted_roles[-2:]:
            if score < 0.4:
                analysis["weaknesses"].append(f"{role.capitalize()}: Weak performance ({score:.2f}) - needs improvement")
        
        # Generate overall recommendations
        best_role, best_score = sorted_roles[0]
        worst_role, worst_score = sorted_roles[-1]
        
        analysis["recommendations"].append(f"Primary role recommendation: {best_role.capitalize()} (score: {best_score:.2f})")
        
        if best_score - worst_score > 0.3:
            analysis["recommendations"].append("Consider specializing in top roles rather than playing all positions")
        
        # Check preference alignment
        preference_aligned = sum(1 for role in roles 
                               if player.role_preferences.get(role, 3) >= 4 and role_scores[role] > 0.5)
        
        if preference_aligned == 0:
            analysis["recommendations"].append("Work on improving performance in preferred roles")
        elif preference_aligned >= 2:
            analysis["recommendations"].append("Good alignment between preferences and performance")
        
        return analysis    

    def calculate_champion_synergy_score(self, player1: Player, champion1_id: int,
                                       player2: Player, champion2_id: int,
                                       synergy_db: Optional['SynergyDatabase'] = None) -> float:
        """
        Calculate synergy score between two players playing specific champions.
        
        Args:
            player1: First player
            champion1_id: Champion ID for first player
            player2: Second player
            champion2_id: Champion ID for second player
            synergy_db: Optional synergy database for historical data
            
        Returns:
            Champion synergy score (0.0 to 1.0)
        """
        if not synergy_db:
            return 0.5  # Neutral score without data
        
        synergy_data = synergy_db.get_synergy(player1.name, player2.name)
        
        if synergy_data.games_together < 2:
            return 0.5  # Not enough data
        
        # Get champion-specific synergy
        champion_synergy = synergy_data.get_champion_synergy_score(champion1_id, champion2_id)
        
        return champion_synergy
    
    def analyze_team_synergy_composition(self, players: List[Player], assignments: Dict[str, str],
                                       synergy_db: Optional['SynergyDatabase'] = None) -> Dict[str, any]:
        """
        Analyze the overall synergy composition of a team.
        
        Args:
            players: List of players in the team
            assignments: Role assignments (role -> player_name)
            synergy_db: Optional synergy database
            
        Returns:
            Dictionary containing team synergy analysis
        """
        player_dict = {p.name: p for p in players}
        assigned_players = list(assignments.values())
        
        if len(assigned_players) < 2:
            return {
                'overall_synergy': 0.0,
                'synergy_pairs': [],
                'strengths': [],
                'weaknesses': [],
                'recommendations': []
            }
        
        # Calculate all pairwise synergies
        synergy_pairs = []
        total_synergy = 0.0
        pair_count = 0
        
        for i, player1_name in enumerate(assigned_players):
            for player2_name in assigned_players[i+1:]:
                player1 = player_dict[player1_name]
                player2 = player_dict[player2_name]
                
                role1 = next(role for role, name in assignments.items() if name == player1_name)
                role2 = next(role for role, name in assignments.items() if name == player2_name)
                
                synergy_score = self.calculate_synergy_score(player1, role1, player2, role2, synergy_db)
                
                synergy_pairs.append({
                    'player1': player1_name,
                    'role1': role1,
                    'player2': player2_name,
                    'role2': role2,
                    'synergy_score': synergy_score,
                    'games_together': 0,
                    'win_rate_together': 0.0
                })
                
                # Add historical data if available
                if synergy_db:
                    synergy_data = synergy_db.get_synergy(player1_name, player2_name)
                    synergy_pairs[-1]['games_together'] = synergy_data.games_together
                    synergy_pairs[-1]['win_rate_together'] = synergy_data.win_rate_together
                
                total_synergy += synergy_score
                pair_count += 1
        
        overall_synergy = total_synergy / pair_count if pair_count > 0 else 0.0
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for pair in synergy_pairs:
            if pair['synergy_score'] > 0.1:
                strengths.append(f"{pair['player1']} ({pair['role1']}) + {pair['player2']} ({pair['role2']}): Strong synergy")
            elif pair['synergy_score'] < -0.1:
                weaknesses.append(f"{pair['player1']} ({pair['role1']}) + {pair['player2']} ({pair['role2']}): Poor synergy")
        
        # Generate recommendations
        recommendations = []
        if overall_synergy > 0.05:
            recommendations.append("Team has good overall synergy - focus on coordination")
        elif overall_synergy < -0.05:
            recommendations.append("Team synergy needs work - consider role swaps or practice together")
        else:
            recommendations.append("Team synergy is neutral - room for improvement through practice")
        
        if len(strengths) > 0:
            recommendations.append(f"Leverage strong synergy pairs: {len(strengths)} identified")
        
        if len(weaknesses) > 0:
            recommendations.append(f"Address weak synergy pairs: {len(weaknesses)} need attention")
        
        return {
            'overall_synergy': overall_synergy,
            'synergy_pairs': sorted(synergy_pairs, key=lambda x: x['synergy_score'], reverse=True),
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': recommendations,
            'pair_count': pair_count,
            'historical_data_coverage': sum(1 for p in synergy_pairs if p['games_together'] > 0) / pair_count if pair_count > 0 else 0.0
        }
    
    def get_synergy_recommendations_for_player(self, player: Player, potential_teammates: List[Player],
                                             target_role: str, synergy_db: Optional['SynergyDatabase'] = None) -> List[Dict[str, any]]:
        """
        Get synergy-based teammate recommendations for a player.
        
        Args:
            player: Player to get recommendations for
            potential_teammates: List of potential teammates
            target_role: Role the player will play
            synergy_db: Optional synergy database
            
        Returns:
            List of teammate recommendations with synergy scores
        """
        recommendations = []
        
        for teammate in potential_teammates:
            if teammate.name == player.name:
                continue
            
            # Calculate synergy for each role the teammate could play
            best_synergy = -1.0
            best_role = None
            
            for role in ["top", "jungle", "middle", "support", "bottom"]:
                if role == target_role:
                    continue  # Can't play same role
                
                synergy_score = self.calculate_synergy_score(player, target_role, teammate, role, synergy_db)
                
                if synergy_score > best_synergy:
                    best_synergy = synergy_score
                    best_role = role
            
            if best_role:
                # Get historical data if available
                games_together = 0
                win_rate_together = 0.0
                
                if synergy_db:
                    synergy_data = synergy_db.get_synergy(player.name, teammate.name)
                    games_together = synergy_data.games_together
                    win_rate_together = synergy_data.win_rate_together
                
                recommendations.append({
                    'teammate': teammate.name,
                    'best_role': best_role,
                    'synergy_score': best_synergy,
                    'games_together': games_together,
                    'win_rate_together': win_rate_together,
                    'confidence': min(games_together / 10.0, 1.0)  # Confidence based on sample size
                })
        
        # Sort by synergy score (descending)
        recommendations.sort(key=lambda x: x['synergy_score'], reverse=True)
        
        return recommendations