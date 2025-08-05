"""
Tests for Champion Performance Analytics Interface.

This module tests the champion performance analytics interface functionality
including performance analysis, recommendations, synergy analysis, and trend visualization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lol_team_optimizer.streamlined_cli import StreamlinedCLI
from lol_team_optimizer.models import Player, ChampionMastery
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics, ChampionPerformanceMetrics, PerformanceMetrics,
    PerformanceDelta, ChampionRecommendation, TeamContext, DateRange
)


def extract_print_calls(mock_print):
    """Helper function to safely extract print calls."""
    print_calls = []
    for call in mock_print.call_args_list:
        if call[0]:  # Check if there are positional arguments
            print_calls.append(str(call[0][0]))
    return ' '.join(print_calls)


class TestChampionPerformanceAnalyticsInterface:
    """Test suite for champion performance analytics interface."""
    
    @pytest.fixture
    def mock_cli(self):
        """Create a mock CLI instance with analytics engines."""
        cli = Mock(spec=StreamlinedCLI)
        cli.engine = Mock()
        cli.engine.data_manager = Mock()
        cli.engine.historical_analytics_engine = Mock()
        cli.engine.champion_recommendation_engine = Mock()
        cli.engine.analytics_cache_manager = Mock()
        cli.engine.baseline_manager = Mock()
        cli.logger = Mock()
        return cli
    
    @pytest.fixture
    def sample_players(self):
        """Create sample players for testing."""
        players = []
        for i in range(3):
            player = Player(
                name=f"TestPlayer{i+1}",
                summoner_name=f"TestSummoner{i+1}",
                puuid=f"test_puuid_{i+1}"
            )
            player.riot_id = f"TestPlayer{i+1}#TEST"
            
            # Add champion masteries
            player.champion_masteries = {
                1: ChampionMastery(
                    champion_id=1,
                    champion_name="Annie",
                    mastery_level=7,
                    mastery_points=150000,
                    primary_roles=["middle"]
                ),
                2: ChampionMastery(
                    champion_id=2,
                    champion_name="Olaf",
                    mastery_level=5,
                    mastery_points=75000,
                    primary_roles=["jungle", "top"]
                )
            }
            players.append(player)
        
        return players
    
    @pytest.fixture
    def sample_analytics(self):
        """Create sample analytics data for testing."""
        # Create performance metrics
        perf_metrics = PerformanceMetrics(
            win_rate=0.65,
            avg_kda=2.5,
            avg_cs_per_min=7.2,
            avg_vision_score=25.0,
            avg_damage_per_min=450.0,
            games_played=25
        )
        
        # Create performance delta
        perf_delta = PerformanceDelta(
            metric_name="overall_performance",
            baseline_value=0.55,
            actual_value=0.65,
            delta_absolute=0.10,
            delta_percentage=18.2,
            percentile_rank=75.0,
            statistical_significance=0.05
        )
        
        # Create champion performance metrics
        champion_perf = ChampionPerformanceMetrics(
            champion_id=1,
            champion_name="Annie",
            role="middle",
            performance=perf_metrics,
            performance_vs_baseline={"overall": perf_delta},
            recent_form=None,
            synergy_scores={}
        )
        
        # Create player analytics
        analytics = PlayerAnalytics(
            puuid="test_puuid_1",
            player_name="TestPlayer1",
            analysis_period=DateRange(
                start_date=datetime.now() - timedelta(days=90),
                end_date=datetime.now()
            ),
            overall_performance=perf_metrics,
            role_performance={"middle": perf_metrics},
            champion_performance={1: champion_perf},
            trend_analysis=None,
            comparative_rankings=None,
            confidence_scores={}
        )
        
        return analytics
    
    @pytest.fixture
    def sample_recommendations(self):
        """Create sample champion recommendations for testing."""
        recommendations = []
        
        for i, (champ_name, score, confidence) in enumerate([
            ("Annie", 0.85, 0.85),
            ("Orianna", 0.78, 0.78),
            ("Syndra", 0.72, 0.72)
        ]):
            rec = ChampionRecommendation(
                champion_id=i+1,
                champion_name=champ_name,
                role="middle",
                recommendation_score=score,
                confidence=confidence,
                historical_performance=None,
                expected_performance=None,
                synergy_analysis=None,
                reasoning=Mock(primary_reason=f"{champ_name} shows strong historical performance")
            )
            recommendations.append(rec)
        
        return recommendations
    
    def test_champion_performance_analytics_menu_display(self, mock_cli, sample_players):
        """Test that the champion performance analytics menu displays correctly."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        # Create real CLI instance for testing menu display
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.historical_analytics_engine = Mock()
            
            # Mock input to exit menu
            with patch('builtins.input', return_value='6'):
                with patch('builtins.print') as mock_print:
                    cli._champion_performance_analytics()
                    
                    # Verify menu options are displayed
                    menu_text = extract_print_calls(mock_print)
                    
                    assert "CHAMPION PERFORMANCE ANALYTICS" in menu_text
                    assert "Champion Performance Analysis" in menu_text
                    assert "Champion Recommendations" in menu_text
                    assert "Champion Synergy Analysis" in menu_text
                    assert "Performance Trend Visualization" in menu_text
    
    def test_champion_performance_analysis_with_data(self, mock_cli, sample_players, sample_analytics):
        """Test champion performance analysis with valid data."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.historical_analytics_engine.analyze_player_performance.return_value = sample_analytics
            cli.logger = Mock()
            
            # Mock user input: select first player
            with patch('builtins.input', return_value='1'):
                with patch('builtins.print') as mock_print:
                    cli._champion_performance_analysis()
                    
                    # Verify analysis was called
                    cli.engine.historical_analytics_engine.analyze_player_performance.assert_called_once()
                    
                    # Verify results are displayed
                    output_text = extract_print_calls(mock_print)
                    
                    assert "CHAMPION PERFORMANCE REPORT" in output_text
                    assert "TestPlayer1" in output_text
                    assert "Annie" in output_text
    
    def test_champion_recommendations_interface(self, mock_cli, sample_players, sample_recommendations):
        """Test champion recommendations interface."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.champion_recommendation_engine.get_champion_recommendations.return_value = sample_recommendations
            cli.logger = Mock()
            
            # Mock user input: select first player and middle role
            with patch('builtins.input', side_effect=['1', '3']):  # Player 1, Middle role
                with patch('builtins.print') as mock_print:
                    cli._champion_recommendations_interface()
                    
                    # Verify recommendations were requested
                    cli.engine.champion_recommendation_engine.get_champion_recommendations.assert_called_once()
                    
                    # Verify results are displayed
                    print_calls = []
                    for call in mock_print.call_args_list:
                        if call[0]:  # Check if there are positional arguments
                            print_calls.append(str(call[0][0]))
                    output_text = ' '.join(print_calls)
                    
                    assert "CHAMPION RECOMMENDATIONS" in output_text
                    assert "Annie" in output_text
                    assert "Orianna" in output_text
                    assert "Syndra" in output_text
    
    def test_fallback_to_mastery_data(self, mock_cli, sample_players):
        """Test fallback to mastery data when analytics fail."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.historical_analytics_engine.analyze_player_performance.side_effect = Exception("Analytics failed")
            cli.logger = Mock()
            
            # Mock user input: select first player
            with patch('builtins.input', return_value='1'):
                with patch('builtins.print') as mock_print:
                    cli._champion_performance_analysis()
                    
                    # Verify fallback is used
                    output_text = extract_print_calls(mock_print)
                    
                    assert "Fallback: Champion Mastery Data" in output_text
                    assert "Annie" in output_text
                    assert "Olaf" in output_text
    
    def test_mastery_based_recommendations_fallback(self, mock_cli, sample_players):
        """Test mastery-based recommendations fallback."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.champion_recommendation_engine.get_champion_recommendations.side_effect = Exception("Recommendations failed")
            cli.logger = Mock()
            
            # Mock user input: select first player and middle role
            with patch('builtins.input', side_effect=['1', '3']):  # Player 1, Middle role
                with patch('builtins.print') as mock_print:
                    cli._champion_recommendations_interface()
                    
                    # Verify fallback is used
                    output_text = extract_print_calls(mock_print)
                    
                    assert "Fallback: Mastery-Based Recommendations" in output_text
                    assert "Annie" in output_text  # Should show Annie for middle role
    
    def test_analytics_engines_not_available(self, mock_cli):
        """Test behavior when analytics engines are not available."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.historical_analytics_engine = None  # Analytics not available
            
            with patch('builtins.print') as mock_print:
                cli._champion_performance_analytics()
                
                # Verify error message is displayed
                output_text = extract_print_calls(mock_print)
                
                assert "Analytics engines not available" in output_text
    
    def test_no_players_available(self, mock_cli):
        """Test behavior when no players are available."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.historical_analytics_engine = Mock()
            cli.engine.data_manager.load_player_data.return_value = []
            
            with patch('builtins.print') as mock_print:
                cli._champion_performance_analytics()
                
                # Verify appropriate message is displayed
                output_text = extract_print_calls(mock_print)
                
                assert "No players found" in output_text
    
    def test_refresh_analytics_data(self, mock_cli, sample_players):
        """Test analytics data refresh functionality."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            cli.engine.analytics_cache_manager = Mock()
            cli.engine.baseline_manager = Mock()
            cli.logger = Mock()
            
            with patch('builtins.print') as mock_print:
                cli._refresh_analytics_data()
                
                # Verify cache clearing was called
                cli.engine.analytics_cache_manager.clear_all_caches.assert_called_once()
                
                # Verify baseline invalidation was called for each player
                assert cli.engine.baseline_manager.invalidate_player_baselines.call_count == len(sample_players)
                
                # Verify success message
                output_text = extract_print_calls(mock_print)
                
                assert "Analytics data refresh complete" in output_text
    
    def test_invalid_player_selection(self, mock_cli, sample_players):
        """Test handling of invalid player selection."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            
            # Mock invalid input
            with patch('builtins.input', return_value='999'):
                with patch('builtins.print') as mock_print:
                    cli._champion_performance_analysis()
                    
                    # Verify error message
                    output_text = extract_print_calls(mock_print)
                    
                    assert "Invalid player selection" in output_text
    
    def test_invalid_role_selection(self, mock_cli, sample_players):
        """Test handling of invalid role selection in recommendations."""
        from lol_team_optimizer.streamlined_cli import StreamlinedCLI
        
        with patch('lol_team_optimizer.streamlined_cli.CoreEngine'):
            cli = StreamlinedCLI()
            cli.engine = mock_cli.engine
            cli.engine.data_manager.load_player_data.return_value = sample_players
            
            # Mock valid player selection, invalid role selection
            with patch('builtins.input', side_effect=['1', '999']):
                with patch('builtins.print') as mock_print:
                    cli._champion_recommendations_interface()
                    
                    # Verify error message
                    output_text = extract_print_calls(mock_print)
                    
                    assert "Invalid role selection" in output_text


if __name__ == "__main__":
    pytest.main([__file__])