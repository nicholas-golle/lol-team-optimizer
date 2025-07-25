"""
Data models for the League of Legends Team Optimizer.

This module contains the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List


@dataclass
class ChampionMastery:
    """Represents champion mastery data for a player."""
    
    champion_id: int
    champion_name: str = ""
    mastery_level: int = 0
    mastery_points: int = 0
    chest_granted: bool = False
    tokens_earned: int = 0
    primary_roles: List[str] = field(default_factory=list)  # roles this champion is typically played in
    last_play_time: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate mastery data after initialization."""
        if self.mastery_level < 0:  # Allow any positive level (Riot changed mastery system)
            raise ValueError("Mastery level cannot be negative")
        if self.mastery_points < 0:
            raise ValueError("Mastery points cannot be negative")
        if self.tokens_earned < 0:
            raise ValueError("Tokens earned cannot be negative")


@dataclass
class ChampionRecommendation:
    """Represents a champion recommendation for a specific role."""
    
    champion_id: int
    champion_name: str
    mastery_level: int
    mastery_points: int
    role_suitability: float  # how well this champion fits the assigned role (0-1)
    confidence: float  # confidence in this recommendation (0-1)
    
    def __post_init__(self):
        """Validate recommendation data."""
        if not 0 <= self.role_suitability <= 1:
            raise ValueError("Role suitability must be between 0 and 1")
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class Player:
    """Represents a League of Legends player with their preferences and cached data."""
    
    name: str
    summoner_name: str
    puuid: str = ""
    role_preferences: Dict[str, int] = field(default_factory=dict)  # role -> preference score (1-5)
    performance_cache: Dict[str, Dict] = field(default_factory=dict)  # role -> cached performance data
    champion_masteries: Dict[int, ChampionMastery] = field(default_factory=dict)  # champion_id -> mastery data
    role_champion_pools: Dict[str, List[int]] = field(default_factory=dict)  # role -> list of champion_ids
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values after object creation."""
        if self.last_updated is None:
            self.last_updated = datetime.now()
        
        # Initialize default role preferences if not provided
        if not self.role_preferences:
            roles = ["top", "jungle", "middle", "support", "bottom"]
            self.role_preferences = {role: 3 for role in roles}  # Default neutral preference
        
        # Initialize role champion pools if not provided
        if not self.role_champion_pools:
            roles = ["top", "jungle", "middle", "support", "bottom"]
            self.role_champion_pools = {role: [] for role in roles}
    
    def get_top_champions_for_role(self, role: str, count: int = 5) -> List[ChampionMastery]:
        """
        Get top champions for a specific role based on mastery.
        
        Args:
            role: Role to get champions for
            count: Number of champions to return
            
        Returns:
            List of ChampionMastery objects sorted by mastery points
        """
        if role not in self.role_champion_pools:
            return []
        
        role_champions = []
        for champion_id in self.role_champion_pools[role]:
            if champion_id in self.champion_masteries:
                mastery = self.champion_masteries[champion_id]
                if role in mastery.primary_roles:
                    role_champions.append(mastery)
        
        # Sort by mastery points (descending) and return top N
        role_champions.sort(key=lambda x: x.mastery_points, reverse=True)
        return role_champions[:count]
    
    def get_mastery_score_for_role(self, role: str) -> float:
        """
        Calculate total mastery score for a specific role.
        
        Args:
            role: Role to calculate score for
            
        Returns:
            Total mastery points for champions in that role
        """
        total_points = 0
        role_champions = self.get_top_champions_for_role(role, count=10)  # Top 10 for role
        
        for mastery in role_champions:
            # Weight mastery points by level (higher levels are more significant)
            level_multiplier = mastery.mastery_level / 7.0  # Normalize to 0-1
            total_points += mastery.mastery_points * level_multiplier
        
        return total_points


@dataclass
class PerformanceData:
    """Represents performance metrics for a player in a specific role."""
    
    role: str
    matches_played: int = 0
    win_rate: float = 0.0
    avg_kda: float = 0.0
    avg_cs_per_min: float = 0.0
    avg_vision_score: float = 0.0
    recent_form: float = 0.0  # performance trend (-1 to 1, where 1 is improving)
    
    def __post_init__(self):
        """Validate performance data after initialization."""
        if not 0 <= self.win_rate <= 1:
            raise ValueError("Win rate must be between 0 and 1")
        if self.avg_kda < 0:
            raise ValueError("Average KDA cannot be negative")
        if self.avg_cs_per_min < 0:
            raise ValueError("Average CS per minute cannot be negative")
        if self.avg_vision_score < 0:
            raise ValueError("Average vision score cannot be negative")
        if not -1 <= self.recent_form <= 1:
            raise ValueError("Recent form must be between -1 and 1")


@dataclass
class TeamAssignment:
    """Represents an optimized team composition with role assignments."""
    
    assignments: Dict[str, str] = field(default_factory=dict)  # role -> player_name
    total_score: float = 0.0
    individual_scores: Dict[str, float] = field(default_factory=dict)  # player -> individual score
    synergy_scores: Dict[tuple, float] = field(default_factory=dict)  # (player1, player2) -> synergy score
    champion_recommendations: Dict[str, List[ChampionRecommendation]] = field(default_factory=dict)  # role -> recommended champions
    explanation: str = ""
    
    def __post_init__(self):
        """Validate team assignment after initialization."""
        roles = {"top", "jungle", "middle", "support", "bottom"}
        
        if self.assignments:
            assigned_roles = set(self.assignments.keys())
            if not assigned_roles.issubset(roles):
                invalid_roles = assigned_roles - roles
                raise ValueError(f"Invalid roles in assignment: {invalid_roles}")
            
            # Check for duplicate player assignments
            assigned_players = list(self.assignments.values())
            if len(assigned_players) != len(set(assigned_players)):
                raise ValueError("Each player can only be assigned to one role")
    
    def is_complete(self) -> bool:
        """Check if the team assignment is valid (has at least some role assignments)."""
        # For teams with fewer than 5 players, we don't require all roles to be filled
        return len(self.assignments) >= 2  # At least 2 players must be assigned
    
    def get_player_role(self, player_name: str) -> Optional[str]:
        """Get the role assigned to a specific player."""
        for role, assigned_player in self.assignments.items():
            if assigned_player == player_name:
                return role
        return None