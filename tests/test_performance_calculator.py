"""
Unit tests for the performance calculator.

Tests individual performance calculations, synergy scoring, and score normalization.
"""

import pytest
from datetime import datetime

from lol_team_optimizer.performance_calculator import PerformanceCalculator
from lol_team_optimizer.models import Player, PerformanceData


class TestPerformanceCalculator:
    """Test cases for the PerformanceCalculator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PerformanceCalculator()
        
        # Create test player with performance data
        self.player_with_data = Player(
            name="TestPlayer",
            summoner_name="test_player",
            puuid="test_puuid",
            role_preferences={"top": 5, "jungle": 2, "middle": 3, "support": 1, "bottom": 4},
            performance_cache={
                "top": {
                    "matches_played": 20,
                    "win_rate": 0.65,
                    "avg_kda": 2.1,
                    "avg_cs_per_min": 7.2,
                    "avg_vision_score": 25.0,
                    "recent_form": 0.3
                },
                "jungle": {
                    "matches_played": 15,
                    "win_rate": 0.58,
                    "avg_kda": 2.8,
                    "avg_cs_per_min": 5.5,
                    "avg_vision_score": 35.0,
                    "recent_form": 0.1
                }
            }
        )
        
        # Create test player without performance data
        self.player_no_data = Player(
            name="NoDataPlayer",
            summoner_name="no_data",
            puuid="no_data_puuid",
            role_preferences={"top": 4, "jungle": 3, "middle": 5, "support": 2, "bottom": 1}
        )
    
    def test_init(self):
        """Test PerformanceCalculator initialization."""
        calc = PerformanceCalculator()
        
        assert "win_rate" in calc.performance_weights
        assert "kda" in calc.performance_weights
        assert "cs_per_min" in calc.performance_weights
        assert "vision_score" in calc.performance_weights
        assert "recent_form" in calc.performance_weights
        
        # Check role-specific weights
        assert "top" in calc.role_weights
        assert "jungle" in calc.role_weights
        assert "middle" in calc.role_weights
        assert "support" in calc.role_weights
        assert "bottom" in calc.role_weights
    
    def test_calculate_individual_score_with_data(self):
        """Test individual score calculation with performance data."""
        score = self.calculator.calculate_individual_score(self.player_with_data, "top")
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        
        # Player has good performance in top, should have decent score
        assert score > 0.5
        
        # Test with jungle data
        jungle_score = self.calculator.calculate_individual_score(self.player_with_data, "jungle")
        assert 0.0 <= jungle_score <= 1.0
    
    def test_calculate_individual_score_no_data(self):
        """Test individual score calculation without performance data."""
        score = self.calculator.calculate_individual_score(self.player_no_data, "middle")
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        
        # Without data, score should be based on preference and reduced
        # Player prefers middle (5/5), so should get some score but reduced due to no data
        assert score > 0.0
        assert score < 0.6  # Should be reduced due to lack of data
    
    def test_calculate_individual_score_role_preference_impact(self):
        """Test that role preferences impact scores when no performance data exists."""
        # High preference role
        high_pref_score = self.calculator.calculate_individual_score(self.player_no_data, "middle")  # pref: 5
        
        # Low preference role  
        low_pref_score = self.calculator.calculate_individual_score(self.player_no_data, "bottom")  # pref: 1
        
        assert high_pref_score > low_pref_score
    
    def test_calculate_individual_score_low_match_count_penalty(self):
        """Test penalty for low match count."""
        # Create player with very few matches
        low_matches_player = Player(
            name="LowMatches",
            summoner_name="low_matches",
            puuid="low_puuid",
            performance_cache={
                "top": {
                    "matches_played": 3,  # Very low
                    "win_rate": 0.8,  # High win rate
                    "avg_kda": 3.0,
                    "avg_cs_per_min": 8.0,
                    "avg_vision_score": 30.0,
                    "recent_form": 0.5
                }
            }
        )
        
        score = self.calculator.calculate_individual_score(low_matches_player, "top")
        
        # Should be penalized despite good stats
        assert score < 0.8  # Should be reduced due to low match count
    
    def test_calculate_synergy_score_basic(self):
        """Test basic synergy score calculation."""
        player1 = self.player_with_data
        player2 = self.player_no_data
        
        synergy = self.calculator.calculate_synergy_score(player1, "top", player2, "jungle")
        
        assert isinstance(synergy, float)
        assert -0.2 <= synergy <= 0.2  # Should be in expected range
    
    def test_calculate_synergy_score_role_compatibility(self):
        """Test synergy based on role compatibility."""
        player1 = self.player_with_data
        player2 = self.player_no_data
        
        # Support-ADC should have high synergy
        support_adc_synergy = self.calculator.calculate_synergy_score(
            player1, "support", player2, "bottom"
        )
        
        # Top-Middle should have lower synergy
        top_mid_synergy = self.calculator.calculate_synergy_score(
            player1, "top", player2, "middle"
        )
        
        # Support-ADC synergy should be higher due to lane partnership
        assert support_adc_synergy >= top_mid_synergy
    
    def test_calculate_synergy_score_preference_bonus(self):
        """Test synergy bonus for preferred roles."""
        # Create players with strong preferences for their roles
        support_player = Player(
            name="SupportMain",
            summoner_name="support_main",
            puuid="support_puuid",
            role_preferences={"support": 5, "top": 1, "jungle": 1, "middle": 1, "bottom": 1}
        )
        
        adc_player = Player(
            name="ADCMain", 
            summoner_name="adc_main",
            puuid="adc_puuid",
            role_preferences={"bottom": 5, "top": 1, "jungle": 1, "middle": 1, "support": 1}
        )
        
        synergy_preferred = self.calculator.calculate_synergy_score(
            support_player, "support", adc_player, "bottom"
        )
        
        synergy_not_preferred = self.calculator.calculate_synergy_score(
            support_player, "top", adc_player, "jungle"
        )
        
        # Should get bonus for preferred roles
        assert synergy_preferred > synergy_not_preferred
    
    def test_normalize_scores_basic(self):
        """Test basic score normalization."""
        scores = {"player1": 10.0, "player2": 20.0, "player3": 30.0}
        normalized = self.calculator.normalize_scores(scores)
        
        assert len(normalized) == len(scores)
        assert all(0.0 <= score <= 1.0 for score in normalized.values())
        
        # Min should be 0, max should be 1
        assert min(normalized.values()) == 0.0
        assert max(normalized.values()) == 1.0
    
    def test_normalize_scores_equal_values(self):
        """Test normalization when all scores are equal."""
        scores = {"player1": 5.0, "player2": 5.0, "player3": 5.0}
        normalized = self.calculator.normalize_scores(scores)
        
        # All should be 0.5 when equal
        assert all(score == 0.5 for score in normalized.values())
    
    def test_normalize_scores_empty(self):
        """Test normalization with empty input."""
        normalized = self.calculator.normalize_scores({})
        assert normalized == {}
    
    def test_get_role_performance_summary(self):
        """Test getting performance summary for all roles."""
        summary = self.calculator.get_role_performance_summary(self.player_with_data)
        
        assert isinstance(summary, dict)
        assert len(summary) == 5  # All 5 roles
        
        expected_roles = {"top", "jungle", "middle", "support", "bottom"}
        assert set(summary.keys()) == expected_roles
        
        # All scores should be valid
        for role, score in summary.items():
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
        
        # Top should have higher score than jungle (better performance data)
        assert summary["top"] >= summary["jungle"]
    
    def test_performance_data_validation(self):
        """Test that PerformanceData validation works correctly."""
        # Valid data
        valid_data = PerformanceData(
            role="top",
            matches_played=10,
            win_rate=0.6,
            avg_kda=2.0,
            avg_cs_per_min=7.0,
            avg_vision_score=25.0,
            recent_form=0.1
        )
        assert valid_data.role == "top"
        
        # Invalid win rate
        with pytest.raises(ValueError, match="Win rate must be between 0 and 1"):
            PerformanceData(role="top", win_rate=1.5)
        
        # Invalid KDA
        with pytest.raises(ValueError, match="Average KDA cannot be negative"):
            PerformanceData(role="top", avg_kda=-1.0)
        
        # Invalid CS per minute
        with pytest.raises(ValueError, match="Average CS per minute cannot be negative"):
            PerformanceData(role="top", avg_cs_per_min=-5.0)
        
        # Invalid vision score
        with pytest.raises(ValueError, match="Average vision score cannot be negative"):
            PerformanceData(role="top", avg_vision_score=-10.0)
        
        # Invalid recent form
        with pytest.raises(ValueError, match="Recent form must be between -1 and 1"):
            PerformanceData(role="top", recent_form=2.0)
    
    def test_role_specific_weights(self):
        """Test that different roles use appropriate metric weights."""
        # Create player with extreme stats to test weighting
        extreme_player = Player(
            name="ExtremePlayer",
            summoner_name="extreme",
            puuid="extreme_puuid",
            performance_cache={
                "support": {
                    "matches_played": 20,
                    "win_rate": 0.6,
                    "avg_kda": 1.0,  # Low KDA
                    "avg_cs_per_min": 1.0,  # Low CS (normal for support)
                    "avg_vision_score": 50.0,  # High vision (important for support)
                    "recent_form": 0.0
                },
                "middle": {
                    "matches_played": 20,
                    "win_rate": 0.6,
                    "avg_kda": 1.0,  # Low KDA
                    "avg_cs_per_min": 1.0,  # Low CS (bad for mid)
                    "avg_vision_score": 50.0,  # High vision
                    "recent_form": 0.0
                }
            }
        )
        
        support_score = self.calculator.calculate_individual_score(extreme_player, "support")
        middle_score = self.calculator.calculate_individual_score(extreme_player, "middle")
        
        # Support should score better due to vision being weighted more heavily
        assert support_score > middle_score
    
    def test_score_clamping(self):
        """Test that scores are properly clamped to 0-1 range."""
        # Create player with extreme performance data
        extreme_player = Player(
            name="ExtremePlayer",
            summoner_name="extreme",
            puuid="extreme_puuid",
            performance_cache={
                "top": {
                    "matches_played": 50,
                    "win_rate": 1.0,  # Perfect win rate
                    "avg_kda": 10.0,  # Extremely high KDA
                    "avg_cs_per_min": 15.0,  # Extremely high CS
                    "avg_vision_score": 100.0,  # Extremely high vision
                    "recent_form": 1.0  # Perfect recent form
                }
            }
        )
        
        score = self.calculator.calculate_individual_score(extreme_player, "top")
        
        # Should be clamped to 1.0 maximum
        assert score <= 1.0
        assert score > 0.8  # Should be very high though
    
    def test_champion_mastery_score_calculation(self):
        """Test champion mastery score calculation."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Create player with champion mastery
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
        
        # Test mastery score calculation
        middle_score = self.calculator.calculate_champion_mastery_score(player, "middle")
        assert 0.8 <= middle_score <= 1.0  # High mastery should give high score
        
        top_score = self.calculator.calculate_champion_mastery_score(player, "top")
        assert 0.6 <= top_score <= 0.8  # Medium mastery should give medium score
        
        jungle_score = self.calculator.calculate_champion_mastery_score(player, "jungle")
        assert 0.0 <= jungle_score <= 0.4  # No champions should give low score
    
    def test_champion_pool_analysis(self):
        """Test champion pool depth analysis."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Create player with multiple champions for middle
        masteries = []
        for i in range(3):
            mastery = ChampionMastery(
                champion_id=100 + i,
                champion_name=f"Champion{i}",
                mastery_level=7 - i,  # Decreasing mastery levels
                mastery_points=100000 - (i * 20000),
                primary_roles=["middle"]
            )
            masteries.append(mastery)
        
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid",
            champion_masteries={mastery.champion_id: mastery for mastery in masteries},
            role_champion_pools={
                "middle": [mastery.champion_id for mastery in masteries],
                "top": [],
                "jungle": [],
                "support": [],
                "bottom": []
            }
        )
        
        # Test pool analysis
        analysis = self.calculator.analyze_champion_pool_depth(player, "middle")
        
        assert analysis["pool_size"] == 3
        assert analysis["depth_score"] > 0.5  # Should be decent with 3 champions
        assert len(analysis["top_champions"]) == 3
        assert "recommendation" in analysis
        
        # Test empty pool
        empty_analysis = self.calculator.analyze_champion_pool_depth(player, "jungle")
        assert empty_analysis["pool_size"] == 0
        assert empty_analysis["depth_score"] == 0.0
    
    def test_individual_champion_score(self):
        """Test individual champion mastery scoring."""
        from lol_team_optimizer.models import ChampionMastery
        
        # High mastery champion
        high_mastery = ChampionMastery(
            champion_id=103,
            champion_name="Ahri",
            mastery_level=7,
            mastery_points=200000
        )
        
        high_score = self.calculator._calculate_individual_champion_score(high_mastery)
        assert 0.9 <= high_score <= 1.0
        
        # Medium mastery champion
        medium_mastery = ChampionMastery(
            champion_id=266,
            champion_name="Aatrox",
            mastery_level=4,
            mastery_points=30000
        )
        
        medium_score = self.calculator._calculate_individual_champion_score(medium_mastery)
        assert 0.4 <= medium_score <= 0.7
        
        # Low mastery champion
        low_mastery = ChampionMastery(
            champion_id=1,
            champion_name="Annie",
            mastery_level=1,
            mastery_points=5000
        )
        
        low_score = self.calculator._calculate_individual_champion_score(low_mastery)
        assert 0.0 <= low_score <= 0.3
    
    def test_overall_mastery_score(self):
        """Test overall mastery score calculation."""
        from lol_team_optimizer.models import ChampionMastery
        
        # Create player with multiple champions
        masteries = {}
        for i in range(5):
            mastery = ChampionMastery(
                champion_id=100 + i,
                champion_name=f"Champion{i}",
                mastery_level=6 - i,  # Decreasing levels
                mastery_points=80000 - (i * 15000)
            )
            masteries[mastery.champion_id] = mastery
        
        player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid",
            champion_masteries=masteries
        )
        
        overall_score = self.calculator._calculate_overall_mastery_score(player)
        assert 0.3 <= overall_score <= 0.8  # Should be decent with multiple champions
        
        # Test empty masteries
        empty_player = Player(
            name="EmptyPlayer",
            summoner_name="EmptyPlayer#NA1",
            puuid="empty_puuid"
        )
        
        empty_score = self.calculator._calculate_overall_mastery_score(empty_player)
        assert empty_score == 0.0