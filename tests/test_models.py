"""
Unit tests for the data models module.
"""

import pytest
from datetime import datetime
from lol_team_optimizer.models import Player, PerformanceData, TeamAssignment, ChampionMastery, ChampionRecommendation


class TestPlayer:
    """Test cases for the Player data model."""
    
    def test_player_creation_with_defaults(self):
        """Test creating a player with minimal required fields."""
        player = Player(name="TestPlayer", summoner_name="TestSummoner")
        
        assert player.name == "TestPlayer"
        assert player.summoner_name == "TestSummoner"
        assert player.puuid == ""
        assert isinstance(player.last_updated, datetime)
        assert len(player.role_preferences) == 5
        assert all(pref == 3 for pref in player.role_preferences.values())
        assert player.performance_cache == {}
    
    def test_player_creation_with_all_fields(self):
        """Test creating a player with all fields specified."""
        test_time = datetime.now()
        preferences = {"top": 5, "jungle": 1, "middle": 4, "support": 2, "bottom": 3}
        cache = {"top": {"win_rate": 0.6}}
        
        player = Player(
            name="FullPlayer",
            summoner_name="FullSummoner",
            puuid="test-puuid-123",
            role_preferences=preferences,
            performance_cache=cache,
            last_updated=test_time
        )
        
        assert player.name == "FullPlayer"
        assert player.summoner_name == "FullSummoner"
        assert player.puuid == "test-puuid-123"
        assert player.role_preferences == preferences
        assert player.performance_cache == cache
        assert player.last_updated == test_time
    
    def test_player_role_preferences_validation(self):
        """Test that role preferences are properly handled."""
        player = Player(name="Test", summoner_name="Test")
        
        # Check default roles are present
        expected_roles = {"top", "jungle", "middle", "support", "bottom"}
        assert set(player.role_preferences.keys()) == expected_roles


class TestPerformanceData:
    """Test cases for the PerformanceData data model."""
    
    def test_performance_data_creation_with_defaults(self):
        """Test creating performance data with minimal fields."""
        perf = PerformanceData(role="top")
        
        assert perf.role == "top"
        assert perf.matches_played == 0
        assert perf.win_rate == 0.0
        assert perf.avg_kda == 0.0
        assert perf.avg_cs_per_min == 0.0
        assert perf.avg_vision_score == 0.0
        assert perf.recent_form == 0.0
    
    def test_performance_data_creation_with_all_fields(self):
        """Test creating performance data with all fields."""
        perf = PerformanceData(
            role="jungle",
            matches_played=25,
            win_rate=0.68,
            avg_kda=2.4,
            avg_cs_per_min=4.2,
            avg_vision_score=18.5,
            recent_form=0.3
        )
        
        assert perf.role == "jungle"
        assert perf.matches_played == 25
        assert perf.win_rate == 0.68
        assert perf.avg_kda == 2.4
        assert perf.avg_cs_per_min == 4.2
        assert perf.avg_vision_score == 18.5
        assert perf.recent_form == 0.3
    
    def test_performance_data_validation_win_rate(self):
        """Test win rate validation."""
        # Valid win rates
        PerformanceData(role="top", win_rate=0.0)
        PerformanceData(role="top", win_rate=0.5)
        PerformanceData(role="top", win_rate=1.0)
        
        # Invalid win rates
        with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
            PerformanceData(role="top", win_rate=-0.1)
        
        with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
            PerformanceData(role="top", win_rate=1.1)
    
    def test_performance_data_validation_negative_values(self):
        """Test validation of metrics that cannot be negative."""
        with pytest.raises(ValueError, match="Average KDA cannot be negative"):
            PerformanceData(role="top", avg_kda=-1.0)
        
        with pytest.raises(ValueError, match="Average CS per minute cannot be negative"):
            PerformanceData(role="top", avg_cs_per_min=-1.0)
        
        with pytest.raises(ValueError, match="Average vision score cannot be negative"):
            PerformanceData(role="top", avg_vision_score=-1.0)
    
    def test_performance_data_validation_recent_form(self):
        """Test recent form validation."""
        # Valid recent form values
        PerformanceData(role="top", recent_form=-1.0)
        PerformanceData(role="top", recent_form=0.0)
        PerformanceData(role="top", recent_form=1.0)
        
        # Invalid recent form values
        with pytest.raises(ValueError, match="Recent form must be between -1 and 1"):
            PerformanceData(role="top", recent_form=-1.1)
        
        with pytest.raises(ValueError, match="Recent form must be between -1 and 1"):
            PerformanceData(role="top", recent_form=1.1)


class TestTeamAssignment:
    """Test cases for the TeamAssignment data model."""
    
    def test_team_assignment_creation_with_defaults(self):
        """Test creating a team assignment with defaults."""
        assignment = TeamAssignment()
        
        assert assignment.assignments == {}
        assert assignment.total_score == 0.0
        assert assignment.individual_scores == {}
        assert assignment.synergy_scores == {}
        assert assignment.explanation == ""
    
    def test_team_assignment_creation_with_data(self):
        """Test creating a team assignment with data."""
        assignments = {
            "top": "Player1",
            "jungle": "Player2",
            "middle": "Player3",
            "support": "Player4",
            "bottom": "Player5"
        }
        individual_scores = {"Player1": 85.0, "Player2": 90.0}
        synergy_scores = {("Player1", "Player2"): 0.8}
        
        assignment = TeamAssignment(
            assignments=assignments,
            total_score=87.5,
            individual_scores=individual_scores,
            synergy_scores=synergy_scores,
            explanation="Optimal assignment based on performance data"
        )
        
        assert assignment.assignments == assignments
        assert assignment.total_score == 87.5
        assert assignment.individual_scores == individual_scores
        assert assignment.synergy_scores == synergy_scores
        assert assignment.explanation == "Optimal assignment based on performance data"
    
    def test_team_assignment_validation_invalid_roles(self):
        """Test validation of invalid role names."""
        with pytest.raises(ValueError, match="Invalid roles in assignment"):
            TeamAssignment(assignments={"invalid_role": "Player1"})
    
    def test_team_assignment_validation_duplicate_players(self):
        """Test validation of duplicate player assignments."""
        with pytest.raises(ValueError, match="Each player can only be assigned to one role"):
            TeamAssignment(assignments={
                "top": "Player1",
                "jungle": "Player1"  # Same player assigned twice
            })
    
    def test_team_assignment_is_complete(self):
        """Test the is_complete method."""
        # Incomplete assignment
        incomplete = TeamAssignment(assignments={"top": "Player1"})
        assert not incomplete.is_complete()
        
        # Complete assignment
        complete_assignments = {
            "top": "Player1",
            "jungle": "Player2",
            "middle": "Player3",
            "support": "Player4",
            "bottom": "Player5"
        }
        complete = TeamAssignment(assignments=complete_assignments)
        assert complete.is_complete()
    
    def test_team_assignment_get_player_role(self):
        """Test the get_player_role method."""
        assignments = {
            "top": "Player1",
            "jungle": "Player2",
            "middle": "Player3"
        }
        assignment = TeamAssignment(assignments=assignments)
        
        assert assignment.get_player_role("Player1") == "top"
        assert assignment.get_player_role("Player2") == "jungle"
        assert assignment.get_player_role("Player3") == "middle"
        assert assignment.get_player_role("Player4") is None


class TestChampionMastery:
    """Test cases for ChampionMastery model."""
    
    def test_champion_mastery_creation(self):
        """Test creating a ChampionMastery object."""
        mastery = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            chest_granted=True,
            tokens_earned=2,
            primary_roles=["middle", "jungle"]
        )
        
        assert mastery.champion_id == 103
        assert mastery.champion_name == "Ahri"
        assert mastery.mastery_level == 7
        assert mastery.mastery_points == 150000
        assert mastery.chest_granted is True
        assert mastery.tokens_earned == 2
        assert mastery.primary_roles == ["middle", "jungle"]
    
    def test_champion_mastery_validation(self):
        """Test ChampionMastery validation."""
        # Invalid mastery level
        with pytest.raises(ValueError, match="Mastery level must be between 1 and 7"):
            ChampionMastery(champion_id=103, mastery_level=8)
        
        # Negative mastery points
        with pytest.raises(ValueError, match="Mastery points cannot be negative"):
            ChampionMastery(champion_id=103, mastery_points=-1000)
        
        # Negative tokens
        with pytest.raises(ValueError, match="Tokens earned cannot be negative"):
            ChampionMastery(champion_id=103, tokens_earned=-1)
    
    def test_champion_mastery_defaults(self):
        """Test ChampionMastery default values."""
        mastery = ChampionMastery(champion_id=103)
        
        assert mastery.champion_name == ""
        assert mastery.mastery_level == 0
        assert mastery.mastery_points == 0
        assert mastery.chest_granted is False
        assert mastery.tokens_earned == 0
        assert mastery.primary_roles == []
        assert mastery.last_play_time is None


class TestChampionRecommendation:
    """Test cases for ChampionRecommendation model."""
    
    def test_champion_recommendation_creation(self):
        """Test creating a ChampionRecommendation object."""
        recommendation = ChampionRecommendation(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            role_suitability=0.9,
            confidence=0.85
        )
        
        assert recommendation.champion_id == 103
        assert recommendation.champion_name == "Ahri"
        assert recommendation.mastery_level == 7
        assert recommendation.mastery_points == 150000
        assert recommendation.role_suitability == 0.9
        assert recommendation.confidence == 0.85
    
    def test_champion_recommendation_validation(self):
        """Test ChampionRecommendation validation."""
        # Invalid role suitability
        with pytest.raises(ValueError, match="Role suitability must be between 0 and 1"):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=1.5,
                confidence=0.8
            )
        
        # Invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            ChampionRecommendation(
                champion_id=103,
                champion_name="Ahri",
                mastery_level=7,
                mastery_points=150000,
                role_suitability=0.9,
                confidence=-0.1
            )


class TestPlayerChampionMethods:
    """Test cases for Player champion-related methods."""
    
    def test_player_with_champion_data(self):
        """Test Player with champion mastery data."""
        mastery1 = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            primary_roles=["middle"]
        )
        
        mastery2 = ChampionMastery(
            champion_id=266,
            champion_name="Aatrox",
            mastery_level=5,
            mastery_points=75000,
            primary_roles=["top"]
        )
        
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid",
            champion_masteries={103: mastery1, 266: mastery2},
            role_champion_pools={
                "middle": [103],
                "top": [266],
                "jungle": [],
                "support": [],
                "bottom": []
            }
        )
        
        assert len(player.champion_masteries) == 2
        assert 103 in player.champion_masteries
        assert 266 in player.champion_masteries
    
    def test_get_top_champions_for_role(self):
        """Test getting top champions for a specific role."""
        mastery1 = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            primary_roles=["middle"]
        )
        
        mastery2 = ChampionMastery(
            champion_id=1,
            champion_name="Annie",
            mastery_level=6,
            mastery_points=100000,
            primary_roles=["middle"]
        )
        
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid",
            champion_masteries={103: mastery1, 1: mastery2},
            role_champion_pools={
                "middle": [103, 1],
                "top": [],
                "jungle": [],
                "support": [],
                "bottom": []
            }
        )
        
        middle_champions = player.get_top_champions_for_role("middle", count=5)
        
        assert len(middle_champions) == 2
        # Should be sorted by mastery points (descending)
        assert middle_champions[0].champion_id == 103  # Ahri (150000 points)
        assert middle_champions[1].champion_id == 1    # Annie (100000 points)
    
    def test_get_mastery_score_for_role(self):
        """Test calculating mastery score for a role."""
        mastery1 = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=150000,
            primary_roles=["middle"]
        )
        
        mastery2 = ChampionMastery(
            champion_id=1,
            champion_name="Annie",
            mastery_level=5,
            mastery_points=50000,
            primary_roles=["middle"]
        )
        
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid",
            champion_masteries={103: mastery1, 1: mastery2},
            role_champion_pools={
                "middle": [103, 1],
                "top": [],
                "jungle": [],
                "support": [],
                "bottom": []
            }
        )
        
        middle_score = player.get_mastery_score_for_role("middle")
        
        # Should be weighted by mastery level
        # Ahri: 150000 * (7/7) = 150000
        # Annie: 50000 * (5/7) ≈ 35714
        expected_score = 150000 + (50000 * 5/7)
        assert abs(middle_score - expected_score) < 1  # Allow for floating point precision
    
    def test_player_role_champion_pools_initialization(self):
        """Test that role champion pools are initialized properly."""
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid"
        )
        
        # Should have all roles initialized
        expected_roles = ["top", "jungle", "middle", "support", "bottom"]
        for role in expected_roles:
            assert role in player.role_champion_pools
            assert isinstance(player.role_champion_pools[role], list)