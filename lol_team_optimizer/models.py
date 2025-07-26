"""
Data models for the League of Legends Team Optimizer.

This module contains the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Tuple


@dataclass
class ChampionPerformance:
    """Represents performance data for a specific champion."""
    
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    total_kills: int = 0
    total_deaths: int = 0
    total_assists: int = 0
    recent_games: int = 0  # Games in last 30 days
    last_played: Optional[datetime] = None
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        return self.wins / max(self.games_played, 1)
    
    @property
    def kda(self) -> float:
        """Calculate KDA ratio."""
        return (self.total_kills + self.total_assists) / max(self.total_deaths, 1)
    
    @property
    def is_recent(self) -> bool:
        """Check if champion was played recently (within 30 days)."""
        if not self.last_played:
            return False
        return (datetime.now() - self.last_played).days <= 30


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
    performance: Optional[ChampionPerformance] = None  # Performance data from match history
    
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
    
    def get_competent_champions_for_role(self, role: str, min_games: int = 3, 
                                       min_win_rate: float = 0.4, count: int = 5) -> List[ChampionMastery]:
        """
        Get champions the player is competent with for a specific role.
        
        Args:
            role: Role to get champions for
            min_games: Minimum games played to be considered competent
            min_win_rate: Minimum win rate to be considered competent
            count: Number of champions to return
            
        Returns:
            List of ChampionMastery objects for competent champions
        """
        if role not in self.role_champion_pools:
            return []
        
        competent_champions = []
        for champion_id in self.role_champion_pools[role]:
            if champion_id in self.champion_masteries:
                mastery = self.champion_masteries[champion_id]
                if role in mastery.primary_roles and mastery.performance:
                    perf = mastery.performance
                    
                    # Check competency criteria
                    if (perf.games_played >= min_games and 
                        perf.win_rate >= min_win_rate):
                        competent_champions.append(mastery)
        
        # Sort by competency score (combination of performance and mastery)
        competent_champions.sort(key=lambda x: self._calculate_competency_score(x), reverse=True)
        return competent_champions[:count]
    
    def get_recent_champions_for_role(self, role: str, days: int = 30, count: int = 5) -> List[ChampionMastery]:
        """
        Get recently played champions for a specific role.
        
        Args:
            role: Role to get champions for
            days: Number of days to consider as "recent"
            count: Number of champions to return
            
        Returns:
            List of recently played ChampionMastery objects
        """
        if role not in self.role_champion_pools:
            return []
        
        recent_champions = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for champion_id in self.role_champion_pools[role]:
            if champion_id in self.champion_masteries:
                mastery = self.champion_masteries[champion_id]
                if (role in mastery.primary_roles and 
                    mastery.performance and 
                    mastery.performance.last_played and
                    mastery.performance.last_played >= cutoff_date):
                    recent_champions.append(mastery)
        
        # Sort by recency and performance
        recent_champions.sort(key=lambda x: (
            x.performance.last_played or datetime.min,
            self._calculate_competency_score(x)
        ), reverse=True)
        
        return recent_champions[:count]
    
    def _calculate_competency_score(self, mastery: ChampionMastery) -> float:
        """
        Calculate a competency score for a champion.
        
        Args:
            mastery: ChampionMastery object
            
        Returns:
            Competency score (higher is better)
        """
        if not mastery.performance:
            # Fallback to mastery points if no performance data
            return mastery.mastery_points / 100000.0
        
        perf = mastery.performance
        
        # Base score from games played (logarithmic)
        games_score = min(perf.games_played / 20.0, 1.0)  # Cap at 20 games
        
        # Win rate score
        win_rate_score = perf.win_rate
        
        # KDA score (normalized)
        kda_score = min(perf.kda / 3.0, 1.0)  # Cap at 3.0 KDA
        
        # Recency bonus
        recency_bonus = 0.2 if perf.is_recent else 0.0
        
        # Mastery level bonus
        mastery_bonus = mastery.mastery_level / 100.0  # Small bonus for high mastery
        
        # Combine scores
        competency_score = (
            games_score * 0.3 +
            win_rate_score * 0.4 +
            kda_score * 0.2 +
            recency_bonus +
            mastery_bonus
        )
        
        return competency_score
    
    def get_champion_competency_tier(self, mastery: ChampionMastery) -> str:
        """
        Get a tier description for champion competency.
        
        Args:
            mastery: ChampionMastery object
            
        Returns:
            Tier description string
        """
        if not mastery.performance:
            if mastery.mastery_level >= 6:
                return "Experienced"
            elif mastery.mastery_level >= 4:
                return "Familiar"
            else:
                return "Novice"
        
        perf = mastery.performance
        competency = self._calculate_competency_score(mastery)
        
        if competency >= 0.8 and perf.games_played >= 10:
            return "Expert"
        elif competency >= 0.6 and perf.games_played >= 5:
            return "Competent"
        elif competency >= 0.4 and perf.games_played >= 3:
            return "Developing"
        elif perf.games_played >= 1:
            return "Learning"
        else:
            return "Untested"


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

@dataclass
class RoleSpecificSynergyData:
    """Represents synergy data between two players in specific roles."""
    
    player1_name: str
    player1_role: str
    player2_name: str
    player2_role: str
    
    # Match statistics
    games_together: int = 0
    wins_together: int = 0
    losses_together: int = 0
    
    # Performance metrics when playing in these roles together
    avg_combined_kda: float = 0.0
    avg_game_duration: float = 0.0
    avg_vision_score_combined: float = 0.0
    avg_damage_share: float = 0.0  # Combined damage percentage
    avg_gold_share: float = 0.0    # Combined gold percentage
    
    # Champion combinations in these roles
    champion_combinations: Dict[Tuple[int, int], Dict[str, any]] = field(default_factory=dict)
    
    # Temporal data
    last_played_together: Optional[datetime] = None
    recent_games_together: int = 0  # Games in last 30 days
    
    @property
    def win_rate_together(self) -> float:
        """Calculate win rate when playing in these roles together."""
        if self.games_together == 0:
            return 0.0
        return self.wins_together / self.games_together
    
    @property
    def synergy_key(self) -> Tuple[str, str, str, str]:
        """Get synergy key for this role combination."""
        return (self.player1_name, self.player1_role, self.player2_name, self.player2_role)
    
    def add_game_result(self, won: bool, player1_champion: int, player2_champion: int, game_data: Dict[str, any]):
        """
        Add a game result for this specific role combination.
        
        Args:
            won: Whether the team won the game
            player1_champion: Champion ID played by player1
            player2_champion: Champion ID played by player2
            game_data: Additional game performance data
        """
        self.games_together += 1
        if won:
            self.wins_together += 1
        else:
            self.losses_together += 1
        
        # Update champion combination data
        champ_key = tuple(sorted([player1_champion, player2_champion]))
        if champ_key not in self.champion_combinations:
            self.champion_combinations[champ_key] = {
                'games': 0,
                'wins': 0,
                'avg_performance': 0.0
            }
        
        champ_data = self.champion_combinations[champ_key]
        champ_data['games'] += 1
        if won:
            champ_data['wins'] += 1
        
        # Update performance metrics (running averages)
        n = self.games_together
        self.avg_combined_kda = ((self.avg_combined_kda * (n-1)) + game_data.get('combined_kda', 0.0)) / n
        self.avg_vision_score_combined = ((self.avg_vision_score_combined * (n-1)) + game_data.get('combined_vision', 0.0)) / n
        self.avg_game_duration = ((self.avg_game_duration * (n-1)) + game_data.get('game_duration', 0.0)) / n
        self.avg_damage_share = ((self.avg_damage_share * (n-1)) + game_data.get('damage_share', 0.0)) / n
        self.avg_gold_share = ((self.avg_gold_share * (n-1)) + game_data.get('gold_share', 0.0)) / n
        
        # Update temporal data
        self.last_played_together = datetime.now()
        if game_data.get('is_recent', False):
            self.recent_games_together += 1
    
    def calculate_role_synergy_score(self) -> float:
        """
        Calculate synergy score for this specific role combination.
        
        Returns:
            Synergy score (-0.3 to 0.3)
        """
        if self.games_together == 0:
            return 0.0
        
        # Base synergy from win rate
        base_synergy = (self.win_rate_together - 0.5) * 0.4
        
        # Performance bonuses
        performance_bonus = 0.0
        if self.avg_combined_kda > 3.0:
            performance_bonus += 0.05
        elif self.avg_combined_kda < 1.5:
            performance_bonus -= 0.05
        
        # Damage/gold share bonus (good coordination)
        if self.avg_damage_share > 0.6:  # High combined impact
            performance_bonus += 0.03
        
        # Recency bonus
        recency_bonus = 0.0
        if self.recent_games_together >= 5:
            recency_bonus = 0.05
        elif self.recent_games_together >= 2:
            recency_bonus = 0.02
        
        # Confidence adjustment based on sample size
        confidence = min(self.games_together / 10.0, 1.0)
        final_synergy = (base_synergy + performance_bonus + recency_bonus) * confidence
        
        return max(-0.3, min(0.3, final_synergy))


@dataclass
class PlayerSynergyData:
    """Represents synergy data between two players based on match history."""
    
    player1_name: str
    player2_name: str
    games_together: int = 0
    wins_together: int = 0
    losses_together: int = 0
    
    # Role-specific synergy data - now more granular
    role_combinations: Dict[Tuple[str, str], Dict[str, any]] = field(default_factory=dict)
    
    # Champion-specific synergy data
    champion_combinations: Dict[Tuple[int, int], Dict[str, any]] = field(default_factory=dict)
    
    # Performance metrics when playing together
    avg_combined_kda: float = 0.0
    avg_game_duration: float = 0.0
    avg_vision_score_combined: float = 0.0
    
    # Temporal data
    last_played_together: Optional[datetime] = None
    recent_games_together: int = 0  # Games in last 30 days
    
    def __post_init__(self):
        """Validate synergy data after initialization."""
        if self.games_together < 0:
            raise ValueError("Games together cannot be negative")
        if self.wins_together + self.losses_together > self.games_together:
            raise ValueError("Wins + losses cannot exceed total games")
        if self.wins_together < 0 or self.losses_together < 0:
            raise ValueError("Wins and losses cannot be negative")
    
    @property
    def win_rate_together(self) -> float:
        """Calculate win rate when playing together."""
        if self.games_together == 0:
            return 0.0
        return self.wins_together / self.games_together
    
    @property
    def synergy_key(self) -> Tuple[str, str]:
        """Get normalized synergy key (alphabetically sorted)."""
        return tuple(sorted([self.player1_name, self.player2_name]))
    
    def add_game_result(self, won: bool, player1_role: str, player2_role: str,
                       player1_champion: int, player2_champion: int,
                       game_data: Dict[str, any]):
        """
        Add a game result to the synergy data.
        
        Args:
            won: Whether the team won the game
            player1_role: Role played by player1
            player2_role: Role played by player2
            player1_champion: Champion ID played by player1
            player2_champion: Champion ID played by player2
            game_data: Additional game performance data
        """
        self.games_together += 1
        if won:
            self.wins_together += 1
        else:
            self.losses_together += 1
        
        # Update role combination data
        role_key = tuple(sorted([player1_role, player2_role]))
        if role_key not in self.role_combinations:
            self.role_combinations[role_key] = {
                'games': 0,
                'wins': 0,
                'avg_kda_combined': 0.0,
                'avg_vision_combined': 0.0
            }
        
        role_data = self.role_combinations[role_key]
        role_data['games'] += 1
        if won:
            role_data['wins'] += 1
        
        # Update champion combination data
        champ_key = tuple(sorted([player1_champion, player2_champion]))
        if champ_key not in self.champion_combinations:
            self.champion_combinations[champ_key] = {
                'games': 0,
                'wins': 0,
                'avg_performance': 0.0
            }
        
        champ_data = self.champion_combinations[champ_key]
        champ_data['games'] += 1
        if won:
            champ_data['wins'] += 1
        
        # Update performance metrics
        combined_kda = game_data.get('combined_kda', 0.0)
        combined_vision = game_data.get('combined_vision', 0.0)
        game_duration = game_data.get('game_duration', 0.0)
        
        # Running average calculation
        n = self.games_together
        self.avg_combined_kda = ((self.avg_combined_kda * (n-1)) + combined_kda) / n
        self.avg_vision_score_combined = ((self.avg_vision_score_combined * (n-1)) + combined_vision) / n
        self.avg_game_duration = ((self.avg_game_duration * (n-1)) + game_duration) / n
        
        # Update temporal data
        self.last_played_together = datetime.now()
        if game_data.get('is_recent', False):
            self.recent_games_together += 1
    
    def get_role_synergy_score(self, role1: str, role2: str) -> float:
        """
        Get synergy score for specific role combination.
        
        Args:
            role1: First player's role
            role2: Second player's role
            
        Returns:
            Synergy score (0.0 to 1.0)
        """
        role_key = tuple(sorted([role1, role2]))
        role_data = self.role_combinations.get(role_key)
        
        if not role_data or role_data['games'] == 0:
            return 0.5  # Neutral score for no data
        
        # Base score from win rate
        win_rate = role_data['wins'] / role_data['games']
        base_score = win_rate
        
        # Adjust for sample size (more games = more reliable)
        confidence = min(role_data['games'] / 10.0, 1.0)
        adjusted_score = (base_score * confidence) + (0.5 * (1 - confidence))
        
        return max(0.0, min(1.0, adjusted_score))
    
    def get_champion_synergy_score(self, champ1: int, champ2: int) -> float:
        """
        Get synergy score for specific champion combination.
        
        Args:
            champ1: First champion ID
            champ2: Second champion ID
            
        Returns:
            Synergy score (0.0 to 1.0)
        """
        champ_key = tuple(sorted([champ1, champ2]))
        champ_data = self.champion_combinations.get(champ_key)
        
        if not champ_data or champ_data['games'] == 0:
            return 0.5  # Neutral score for no data
        
        # Base score from win rate
        win_rate = champ_data['wins'] / champ_data['games']
        base_score = win_rate
        
        # Adjust for sample size
        confidence = min(champ_data['games'] / 5.0, 1.0)  # Lower threshold for champion combos
        adjusted_score = (base_score * confidence) + (0.5 * (1 - confidence))
        
        return max(0.0, min(1.0, adjusted_score))
    
    def calculate_overall_synergy_score(self) -> float:
        """
        Calculate overall synergy score between the two players.
        
        Returns:
            Overall synergy score (-0.3 to 0.3)
        """
        if self.games_together == 0:
            return 0.0  # No data = neutral synergy
        
        # Base synergy from overall win rate
        base_synergy = (self.win_rate_together - 0.5) * 0.4  # Scale to -0.2 to 0.2
        
        # Performance bonus/penalty
        performance_factor = 0.0
        if self.avg_combined_kda > 3.0:
            performance_factor += 0.05
        elif self.avg_combined_kda < 1.5:
            performance_factor -= 0.05
        
        # Recency bonus (recent games together indicate active synergy)
        recency_factor = 0.0
        if self.recent_games_together >= 5:
            recency_factor = 0.05
        elif self.recent_games_together >= 2:
            recency_factor = 0.02
        
        # Sample size confidence adjustment
        confidence = min(self.games_together / 15.0, 1.0)
        final_synergy = (base_synergy + performance_factor + recency_factor) * confidence
        
        return max(-0.3, min(0.3, final_synergy))


@dataclass
class SynergyDatabase:
    """Database for storing and managing player synergy data."""
    
    synergies: Dict[Tuple[str, str], PlayerSynergyData] = field(default_factory=dict)
    role_specific_synergies: Dict[Tuple[str, str, str, str], RoleSpecificSynergyData] = field(default_factory=dict)
    last_updated: Optional[datetime] = None
    
    def get_synergy(self, player1: str, player2: str) -> PlayerSynergyData:
        """
        Get synergy data between two players.
        
        Args:
            player1: First player name
            player2: Second player name
            
        Returns:
            PlayerSynergyData object
        """
        key = tuple(sorted([player1, player2]))
        
        if key not in self.synergies:
            self.synergies[key] = PlayerSynergyData(
                player1_name=key[0],
                player2_name=key[1]
            )
        
        return self.synergies[key]
    
    def get_role_specific_synergy(self, player1: str, role1: str, player2: str, role2: str) -> RoleSpecificSynergyData:
        """
        Get role-specific synergy data between two players in specific roles.
        
        Args:
            player1: First player name
            role1: First player's role
            player2: Second player name
            role2: Second player's role
            
        Returns:
            RoleSpecificSynergyData object
        """
        key = (player1, role1, player2, role2)
        
        if key not in self.role_specific_synergies:
            self.role_specific_synergies[key] = RoleSpecificSynergyData(
                player1_name=player1,
                player1_role=role1,
                player2_name=player2,
                player2_role=role2
            )
        
        return self.role_specific_synergies[key]
    
    def get_all_role_synergies_for_players(self, player1: str, player2: str) -> List[RoleSpecificSynergyData]:
        """
        Get all role-specific synergies between two players.
        
        Args:
            player1: First player name
            player2: Second player name
            
        Returns:
            List of RoleSpecificSynergyData objects
        """
        synergies = []
        
        for key, synergy in self.role_specific_synergies.items():
            if (key[0] == player1 and key[2] == player2) or (key[0] == player2 and key[2] == player1):
                synergies.append(synergy)
        
        return synergies
    
    def add_match_data(self, match_data: Dict[str, any]):
        """
        Add match data to update synergy information.
        
        Args:
            match_data: Dictionary containing match information
        """
        participants = match_data.get('participants', [])
        if len(participants) < 2:
            return
        
        # Find all pairs of players in the match
        for i, player1 in enumerate(participants):
            for player2 in participants[i+1:]:
                # Only process if both players are in our database
                player1_name = player1.get('player_name')
                player2_name = player2.get('player_name')
                
                if not player1_name or not player2_name:
                    continue
                
                # Extract game data
                won = player1.get('win', False)  # Assuming same team
                player1_role = player1.get('role', 'unknown')
                player2_role = player2.get('role', 'unknown')
                player1_champion = player1.get('champion_id', 0)
                player2_champion = player2.get('champion_id', 0)
                
                # Calculate combined performance metrics
                player1_kda = (player1.get('kills', 0) + player1.get('assists', 0)) / max(player1.get('deaths', 1), 1)
                player2_kda = (player2.get('kills', 0) + player2.get('assists', 0)) / max(player2.get('deaths', 1), 1)
                combined_kda = (player1_kda + player2_kda) / 2
                
                combined_vision = player1.get('vision_score', 0) + player2.get('vision_score', 0)
                game_duration = match_data.get('game_duration', 0)
                
                # Calculate damage and gold shares
                total_team_damage = match_data.get('total_team_damage', 1)
                total_team_gold = match_data.get('total_team_gold', 1)
                
                player1_damage = player1.get('total_damage_dealt', 0)
                player2_damage = player2.get('total_damage_dealt', 0)
                damage_share = (player1_damage + player2_damage) / max(total_team_damage, 1)
                
                player1_gold = player1.get('gold_earned', 0)
                player2_gold = player2.get('gold_earned', 0)
                gold_share = (player1_gold + player2_gold) / max(total_team_gold, 1)
                
                # Check if game is recent (last 30 days)
                game_creation = match_data.get('game_creation', 0)
                is_recent = False
                if game_creation:
                    game_date = datetime.fromtimestamp(game_creation / 1000)
                    is_recent = (datetime.now() - game_date).days <= 30
                
                game_data = {
                    'combined_kda': combined_kda,
                    'combined_vision': combined_vision,
                    'game_duration': game_duration,
                    'damage_share': damage_share,
                    'gold_share': gold_share,
                    'is_recent': is_recent
                }
                
                # Update general synergy data
                synergy = self.get_synergy(player1_name, player2_name)
                synergy.add_game_result(
                    won=won,
                    player1_role=player1_role,
                    player2_role=player2_role,
                    player1_champion=player1_champion,
                    player2_champion=player2_champion,
                    game_data=game_data
                )
                
                # Update role-specific synergy data
                if player1_role != 'unknown' and player2_role != 'unknown':
                    role_synergy = self.get_role_specific_synergy(
                        player1_name, player1_role, player2_name, player2_role
                    )
                    role_synergy.add_game_result(
                        won=won,
                        player1_champion=player1_champion,
                        player2_champion=player2_champion,
                        game_data=game_data
                    )
        
        self.last_updated = datetime.now()
    
    def get_all_synergies_for_player(self, player_name: str) -> List[PlayerSynergyData]:
        """
        Get all synergy data involving a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            List of PlayerSynergyData objects
        """
        synergies = []
        for synergy in self.synergies.values():
            if player_name in [synergy.player1_name, synergy.player2_name]:
                synergies.append(synergy)
        
        return synergies
    
    def calculate_team_synergy_matrix(self, player_names: List[str]) -> Dict[Tuple[str, str], float]:
        """
        Calculate synergy matrix for a team of players.
        
        Args:
            player_names: List of player names
            
        Returns:
            Dictionary mapping player pairs to synergy scores
        """
        synergy_matrix = {}
        
        for i, player1 in enumerate(player_names):
            for player2 in player_names[i+1:]:
                synergy = self.get_synergy(player1, player2)
                synergy_score = synergy.calculate_overall_synergy_score()
                synergy_matrix[(player1, player2)] = synergy_score
        
        return synergy_matrix
    
    def calculate_team_synergy_with_roles(self, assignments: Dict[str, str]) -> Dict[Tuple[str, str], float]:
        """
        Calculate team synergy matrix considering specific role assignments.
        
        Args:
            assignments: Dictionary mapping roles to player names (role -> player_name)
            
        Returns:
            Dictionary mapping player pairs to role-specific synergy scores
        """
        synergy_matrix = {}
        
        # Get all player-role pairs
        player_roles = [(player, role) for role, player in assignments.items()]
        
        # Calculate synergy for all pairs considering their specific roles
        for i, (player1, role1) in enumerate(player_roles):
            for (player2, role2) in player_roles[i+1:]:
                # Get role-specific synergy
                role_synergy = self.get_role_specific_synergy(player1, role1, player2, role2)
                synergy_score = role_synergy.calculate_role_synergy_score()
                
                synergy_matrix[(player1, player2)] = synergy_score
        
        return synergy_matrix
    
    def get_best_role_combinations_for_players(self, player1: str, player2: str, 
                                             roles: List[str]) -> List[Tuple[str, str, float]]:
        """
        Get the best role combinations for two players based on synergy data.
        
        Args:
            player1: First player name
            player2: Second player name
            roles: List of available roles
            
        Returns:
            List of (role1, role2, synergy_score) tuples sorted by synergy score
        """
        combinations = []
        
        for role1 in roles:
            for role2 in roles:
                if role1 != role2:  # Players can't play the same role
                    role_synergy = self.get_role_specific_synergy(player1, role1, player2, role2)
                    if role_synergy.games_together > 0:  # Only include combinations with data
                        synergy_score = role_synergy.calculate_role_synergy_score()
                        combinations.append((role1, role2, synergy_score))
        
        # Sort by synergy score (descending)
        combinations.sort(key=lambda x: x[2], reverse=True)
        return combinations
    
    def analyze_role_synergy_patterns(self, players: List[str], roles: List[str]) -> Dict[str, any]:
        """
        Analyze synergy patterns across all role combinations.
        
        Args:
            players: List of player names
            roles: List of role names
            
        Returns:
            Dictionary with synergy pattern analysis
        """
        role_pair_synergies = {}  # (role1, role2) -> [synergy_scores]
        player_role_synergies = {}  # player -> {role -> avg_synergy}
        
        # Collect all role-specific synergy data
        for synergy in self.role_specific_synergies.values():
            if synergy.games_together >= 3:  # Minimum games for reliability
                role_pair = tuple(sorted([synergy.player1_role, synergy.player2_role]))
                synergy_score = synergy.calculate_role_synergy_score()
                
                if role_pair not in role_pair_synergies:
                    role_pair_synergies[role_pair] = []
                role_pair_synergies[role_pair].append(synergy_score)
                
                # Track player-role synergies
                for player, role in [(synergy.player1_name, synergy.player1_role), 
                                   (synergy.player2_name, synergy.player2_role)]:
                    if player not in player_role_synergies:
                        player_role_synergies[player] = {}
                    if role not in player_role_synergies[player]:
                        player_role_synergies[player][role] = []
                    player_role_synergies[player][role].append(synergy_score)
        
        # Calculate average synergies
        avg_role_pair_synergies = {}
        for role_pair, scores in role_pair_synergies.items():
            avg_role_pair_synergies[role_pair] = sum(scores) / len(scores)
        
        avg_player_role_synergies = {}
        for player, role_scores in player_role_synergies.items():
            avg_player_role_synergies[player] = {}
            for role, scores in role_scores.items():
                avg_player_role_synergies[player][role] = sum(scores) / len(scores)
        
        return {
            'role_pair_synergies': avg_role_pair_synergies,
            'player_role_synergies': avg_player_role_synergies,
            'total_role_combinations': len(self.role_specific_synergies),
            'reliable_combinations': len([s for s in self.role_specific_synergies.values() if s.games_together >= 3])
        }
    
    def get_best_teammates_for_player(self, player_name: str, count: int = 5) -> List[Tuple[str, float]]:
        """
        Get the best teammates for a specific player based on synergy.
        
        Args:
            player_name: Name of the player
            count: Number of teammates to return
            
        Returns:
            List of (teammate_name, synergy_score) tuples
        """
        synergies = self.get_all_synergies_for_player(player_name)
        
        teammate_scores = []
        for synergy in synergies:
            teammate = synergy.player2_name if synergy.player1_name == player_name else synergy.player1_name
            score = synergy.calculate_overall_synergy_score()
            
            # Only include if they've played together enough
            if synergy.games_together >= 3:
                teammate_scores.append((teammate, score))
        
        # Sort by synergy score (descending)
        teammate_scores.sort(key=lambda x: x[1], reverse=True)
        
        return teammate_scores[:count]
    
    def export_synergy_summary(self) -> Dict[str, any]:
        """
        Export summary of synergy database for analysis.
        
        Returns:
            Dictionary containing synergy summary
        """
        total_pairs = len(self.synergies)
        pairs_with_data = sum(1 for s in self.synergies.values() if s.games_together > 0)
        
        avg_games_together = 0.0
        avg_win_rate = 0.0
        if pairs_with_data > 0:
            total_games = sum(s.games_together for s in self.synergies.values())
            total_wins = sum(s.wins_together for s in self.synergies.values())
            avg_games_together = total_games / pairs_with_data
            avg_win_rate = total_wins / total_games if total_games > 0 else 0.0
        
        return {
            'total_player_pairs': total_pairs,
            'pairs_with_match_data': pairs_with_data,
            'average_games_together': avg_games_together,
            'average_win_rate_together': avg_win_rate,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'top_synergy_pairs': [
                {
                    'players': [s.player1_name, s.player2_name],
                    'games': s.games_together,
                    'win_rate': s.win_rate_together,
                    'synergy_score': s.calculate_overall_synergy_score()
                }
                for s in sorted(self.synergies.values(), 
                              key=lambda x: x.calculate_overall_synergy_score(), 
                              reverse=True)[:10]
                if s.games_together >= 5
            ]
        }