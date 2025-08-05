"""
Tests for the Interactive Analytics Dashboard.

This module tests the interactive dashboard functionality including:
- Dynamic filtering with real-time updates
- Drill-down capabilities
- Comparative analysis
- Export and reporting functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from lol_team_optimizer.interactive_analytics_dashboard import (
    InteractiveAnalyticsDashboard,
    DashboardState,
    ExportOptions
)
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters,
    DateRange,
    PlayerAnalytics,
    ChampionPerformanceMetrics
)


class TestDashboardState:
    """Test the DashboardState dataclass."""
    
    def test_dashboard_state_initialization(self):
        """Test dashboard state initialization with defaults."""
        state = DashboardState()
        
        assert isinstance(state.active_filters, AnalyticsFilters)
        assert state.selected_players == set()
        assert state.selected_champions == set()
        assert state.selected_roles == set()
        assert state.comparison_mode == "players"
        assert state.view_level == "summary"
        assert state.cached_results == {}
        assert state.last_update is None
    
    def test_dashboard_state_with_data(self):
        """Test dashboard state with custom data."""
        filters = AnalyticsFilters(min_games=5)
        state = DashboardState(
            active_filters=filters,
            selected_players={"Player1", "Player2"},
            comparison_mode="champions",
            view_level="detailed"
        )
        
        assert state.active_filters.min_games == 5
        assert len(state.selected_players) == 2
        assert state.comparison_mode == "champions"
        assert state.view_level == "detailed"


class TestExportOptions:
    """Test the ExportOptions dataclass."""
    
    def test_export_options_defaults(self):
        """Test export options with default values."""
        options = ExportOptions()
        
        assert options.format == "csv"
        assert options.include_charts is False
        assert options.include_raw_data is True
        assert options.custom_fields == []
        assert options.file_path is None
    
    def test_export_options_custom(self):
        """Test export options with custom values."""
        options = ExportOptions(
            format="json",
            include_charts=True,
            custom_fields=["win_rate", "kda"],
            file_path="/tmp/export.json"
        )
        
        assert options.format == "json"
        assert options.include_charts is True
        assert options.custom_fields == ["win_rate", "kda"]
        assert options.file_path == "/tmp/export.json"


class TestInteractiveAnalyticsDashboard:
    """Test the InteractiveAnalyticsDashboard class."""
    
    @pytest.fixture
    def mock_engines(self):
        """Create mock engines for testing."""
        analytics_engine = Mock()
        recommendation_engine = Mock()
        composition_analyzer = Mock()
        comparative_analyzer = Mock()
        data_manager = Mock()
        
        # Mock data manager responses
        mock_player = Mock()
        mock_player.name = "TestPlayer"
        mock_player.puuid = "test-puuid-123"
        data_manager.load_player_data.return_value = [mock_player]
        
        # Mock analytics engine responses
        analytics_engine.get_available_champions.return_value = [1, 2, 3, 4, 5]
        
        return {
            'analytics_engine': analytics_engine,
            'recommendation_engine': recommendation_engine,
            'composition_analyzer': composition_analyzer,
            'comparative_analyzer': comparative_analyzer,
            'data_manager': data_manager
        }
    
    @pytest.fixture
    def dashboard(self, mock_engines):
        """Create dashboard instance for testing."""
        return InteractiveAnalyticsDashboard(**mock_engines)
    
    def test_dashboard_initialization(self, dashboard, mock_engines):
        """Test dashboard initialization."""
        assert dashboard.analytics_engine == mock_engines['analytics_engine']
        assert dashboard.data_manager == mock_engines['data_manager']
        assert isinstance(dashboard.state, DashboardState)
        assert len(dashboard.available_players) == 1
        assert len(dashboard.available_champions) == 5
        assert len(dashboard.available_roles) == 5
    
    def test_refresh_available_options(self, dashboard, mock_engines):
        """Test refreshing available options."""
        # Add more mock players
        mock_player2 = Mock()
        mock_player2.name = "TestPlayer2"
        mock_player2.puuid = "test-puuid-456"
        
        mock_engines['data_manager'].load_player_data.return_value = [
            mock_engines['data_manager'].load_player_data.return_value[0],
            mock_player2
        ]
        
        dashboard._refresh_available_options()
        
        assert len(dashboard.available_players) == 2
        assert ("TestPlayer", "test-puuid-123") in dashboard.available_players
        assert ("TestPlayer2", "test-puuid-456") in dashboard.available_players
    
    def test_generate_cache_key(self, dashboard):
        """Test cache key generation."""
        # Test with empty selections
        key1 = dashboard._generate_cache_key()
        assert "players:all" in key1
        assert "champions:all" in key1
        assert "roles:all" in key1
        
        # Test with selections
        dashboard.state.selected_players = {"Player1", "Player2"}
        dashboard.state.selected_champions = {1, 2}
        dashboard.state.selected_roles = {"top", "jungle"}
        
        key2 = dashboard._generate_cache_key()
        assert "players:['Player1', 'Player2']" in key2
        assert "champions:[1, 2]" in key2
        assert "roles:['jungle', 'top']" in key2
        
        # Keys should be different
        assert key1 != key2
    
    def test_configure_date_range(self, dashboard):
        """Test date range configuration."""
        # Test last 7 days
        with patch('builtins.input', return_value='1'):
            dashboard._configure_date_range()
        
        assert dashboard.state.active_filters.date_range is not None
        date_range = dashboard.state.active_filters.date_range
        assert (datetime.now() - date_range.start_date).days == 7
        
        # Test all time
        with patch('builtins.input', return_value='6'):
            dashboard._configure_date_range()
        
        assert dashboard.state.active_filters.date_range is None
    
    def test_configure_custom_date_range(self, dashboard):
        """Test custom date range configuration."""
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        with patch('builtins.input', side_effect=[start_date, end_date]):
            dashboard._configure_custom_date_range()
        
        date_range = dashboard.state.active_filters.date_range
        assert date_range is not None
        assert date_range.start_date.strftime('%Y-%m-%d') == start_date
        assert date_range.end_date.strftime('%Y-%m-%d') == end_date
    
    def test_configure_custom_date_range_invalid(self, dashboard):
        """Test custom date range with invalid input."""
        with patch('builtins.input', side_effect=["invalid-date", "2024-01-31"]):
            with patch('builtins.print') as mock_print:
                dashboard._configure_custom_date_range()
                mock_print.assert_called_with("❌ Invalid date format. Please use YYYY-MM-DD")
    
    def test_configure_player_selection(self, dashboard):
        """Test player selection configuration."""
        # Test select all
        with patch('builtins.input', return_value='2'):
            dashboard._configure_player_selection()
        
        assert len(dashboard.state.selected_players) == len(dashboard.available_players)
        assert "TestPlayer" in dashboard.state.selected_players
        
        # Test clear selection
        with patch('builtins.input', return_value='3'):
            dashboard._configure_player_selection()
        
        assert len(dashboard.state.selected_players) == 0
    
    def test_configure_role_selection(self, dashboard):
        """Test role selection configuration."""
        # Test select all roles
        with patch('builtins.input', return_value='2'):
            dashboard._configure_role_selection()
        
        assert len(dashboard.state.selected_roles) == 5
        assert "top" in dashboard.state.selected_roles
        assert "jungle" in dashboard.state.selected_roles
        
        # Test clear selection
        with patch('builtins.input', return_value='3'):
            dashboard._configure_role_selection()
        
        assert len(dashboard.state.selected_roles) == 0
    
    def test_apply_filters(self, dashboard):
        """Test applying filters."""
        initial_time = dashboard.state.last_update
        
        with patch('builtins.print'):
            dashboard._apply_filters()
        
        assert dashboard.state.last_update != initial_time
        assert len(dashboard.state.cached_results) == 0  # Should be cleared
    
    def test_reset_filters(self, dashboard):
        """Test resetting all filters."""
        # Set some filters first
        dashboard.state.selected_players = {"Player1"}
        dashboard.state.selected_champions = {1, 2}
        dashboard.state.active_filters.min_games = 10
        dashboard.state.cached_results["test"] = "data"
        
        with patch('builtins.print'):
            dashboard._reset_filters()
        
        assert len(dashboard.state.selected_players) == 0
        assert len(dashboard.state.selected_champions) == 0
        # AnalyticsFilters has a default min_games of 1, not None
        assert dashboard.state.active_filters.min_games == 1
        assert len(dashboard.state.cached_results) == 0
    
    @patch('builtins.print')
    def test_get_filtered_analytics_no_data(self, mock_print, dashboard, mock_engines):
        """Test getting filtered analytics with no data."""
        # Mock empty player analytics
        mock_engines['analytics_engine'].analyze_player_performance.return_value = None
        
        result = dashboard._get_filtered_analytics()
        
        assert 'players' in result
        assert 'summary' in result
        assert len(result['players']) == 0
    
    def test_get_filtered_analytics_with_data(self, dashboard, mock_engines):
        """Test getting filtered analytics with mock data."""
        # Create mock player analytics
        mock_analytics = Mock()
        mock_analytics.games_played = 10
        mock_analytics.wins = 6
        mock_analytics.win_rate = 0.6
        mock_analytics.avg_kda = 2.5
        
        mock_engines['analytics_engine'].analyze_player_performance.return_value = mock_analytics
        
        result = dashboard._get_filtered_analytics()
        
        assert 'players' in result
        assert 'TestPlayer' in result['players']
        assert result['players']['TestPlayer'] == mock_analytics
        assert 'summary' in result
    
    def test_generate_summary_statistics(self, dashboard):
        """Test generating summary statistics."""
        # Create mock player data
        mock_analytics1 = Mock()
        mock_analytics1.games_played = 10
        mock_analytics1.wins = 7
        mock_analytics1.avg_kda = 2.5
        
        mock_analytics2 = Mock()
        mock_analytics2.games_played = 8
        mock_analytics2.wins = 3
        mock_analytics2.avg_kda = 1.8
        
        players_data = {
            'Player1': mock_analytics1,
            'Player2': mock_analytics2
        }
        
        summary = dashboard._generate_summary_statistics(players_data)
        
        assert summary['total_players'] == 2
        assert summary['total_games'] == 18
        assert summary['avg_win_rate'] == 10/18  # (7+3)/(10+8)
        assert summary['avg_kda'] == (2.5 + 1.8) / 2
        assert 'performance_distribution' in summary
    
    @patch('builtins.open', create=True)
    @patch('json.dump')
    @patch('builtins.print')
    def test_export_current_analytics(self, mock_print, mock_json_dump, mock_open, dashboard):
        """Test exporting current analytics."""
        # Mock analytics data
        dashboard.state.cached_results["test_key"] = {
            'summary': {'total_players': 1},
            'players': {'TestPlayer': Mock()},
            'timestamp': datetime.now()
        }
        
        with patch.object(dashboard, '_get_filtered_analytics') as mock_get_analytics:
            mock_get_analytics.return_value = dashboard.state.cached_results["test_key"]
            
            dashboard._export_current_analytics()
            
            mock_open.assert_called_once()
            mock_json_dump.assert_called_once()
            # Should print success message containing "exported"
            printed_calls = [str(call) for call in mock_print.call_args_list]
            assert any("exported" in call.lower() for call in printed_calls)
    
    def test_display_summary_metrics(self, dashboard):
        """Test displaying summary metrics."""
        summary_data = {
            'summary': {
                'total_players': 5,
                'total_games': 100,
                'avg_win_rate': 0.55,
                'avg_kda': 2.1,
                'performance_distribution': {
                    'high': 2,
                    'average': 2,
                    'low': 1
                }
            }
        }
        
        with patch('builtins.print') as mock_print:
            dashboard._display_summary_metrics(summary_data)
            
            # Check that summary information was printed
            printed_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Summary Metrics" in call for call in printed_calls)
            assert any("Total Players Analyzed: 5" in call for call in printed_calls)
    
    def test_display_player_comparison_table(self, dashboard):
        """Test displaying player comparison table."""
        # Create mock comparison data
        mock_analytics1 = Mock()
        mock_analytics1.games_played = 10
        mock_analytics1.win_rate = 0.6
        mock_analytics1.avg_kda = 2.5
        mock_analytics1.avg_damage = 15000
        mock_analytics1.avg_gold = 12000
        
        mock_analytics2 = Mock()
        mock_analytics2.games_played = 8
        mock_analytics2.win_rate = 0.5
        mock_analytics2.avg_kda = 2.0
        mock_analytics2.avg_damage = 14000
        mock_analytics2.avg_gold = 11000
        
        comparison_data = {
            'Player1': mock_analytics1,
            'Player2': mock_analytics2
        }
        
        with patch('builtins.print') as mock_print:
            dashboard._display_player_comparison_table(comparison_data)
            
            # Check that comparison table was printed
            printed_calls = [str(call) for call in mock_print.call_args_list]
            assert any("Player Comparison Table" in call for call in printed_calls)
    
    def test_configure_game_requirements(self, dashboard):
        """Test configuring game requirements."""
        with patch('builtins.input', return_value='5'):
            dashboard._configure_game_requirements()
        
        assert dashboard.state.active_filters.min_games == 5
        
        # Test invalid input
        with patch('builtins.input', return_value='invalid'):
            with patch('builtins.print') as mock_print:
                dashboard._configure_game_requirements()
                mock_print.assert_any_call("❌ Invalid number")
    
    def test_configure_queue_types(self, dashboard):
        """Test configuring queue types."""
        # Test select all queues
        with patch('builtins.input', return_value='2'):
            dashboard._configure_queue_types()
        
        assert len(dashboard.state.active_filters.queue_types) == 5
        assert "RANKED_SOLO_5x5" in dashboard.state.active_filters.queue_types
        
        # Test clear selection
        with patch('builtins.input', return_value='3'):
            dashboard._configure_queue_types()
        
        assert dashboard.state.active_filters.queue_types == []


class TestDashboardIntegration:
    """Test dashboard integration scenarios."""
    
    @pytest.fixture
    def full_dashboard_setup(self):
        """Set up a complete dashboard for integration testing."""
        # Create comprehensive mock setup
        analytics_engine = Mock()
        recommendation_engine = Mock()
        composition_analyzer = Mock()
        comparative_analyzer = Mock()
        data_manager = Mock()
        
        # Mock multiple players
        players = []
        for i in range(3):
            player = Mock()
            player.name = f"Player{i+1}"
            player.puuid = f"puuid-{i+1}"
            players.append(player)
        
        data_manager.load_player_data.return_value = players
        analytics_engine.get_available_champions.return_value = list(range(1, 11))
        
        dashboard = InteractiveAnalyticsDashboard(
            analytics_engine=analytics_engine,
            recommendation_engine=recommendation_engine,
            composition_analyzer=composition_analyzer,
            comparative_analyzer=comparative_analyzer,
            data_manager=data_manager
        )
        
        return dashboard, {
            'analytics_engine': analytics_engine,
            'data_manager': data_manager
        }
    
    def test_full_filtering_workflow(self, full_dashboard_setup):
        """Test complete filtering workflow."""
        dashboard, mocks = full_dashboard_setup
        
        # Configure filters
        dashboard.state.selected_players = {"Player1", "Player2"}
        dashboard.state.selected_roles = {"top", "jungle"}
        dashboard.state.active_filters.min_games = 5
        
        # Apply filters
        dashboard._apply_filters()
        
        # Verify state
        assert len(dashboard.state.selected_players) == 2
        assert len(dashboard.state.selected_roles) == 2
        assert dashboard.state.active_filters.min_games == 5
        assert dashboard.state.last_update is not None
    
    def test_analytics_data_flow(self, full_dashboard_setup):
        """Test analytics data flow through the dashboard."""
        dashboard, mocks = full_dashboard_setup
        
        # Mock analytics response
        mock_analytics = Mock()
        mock_analytics.games_played = 15
        mock_analytics.wins = 9
        mock_analytics.win_rate = 0.6
        mock_analytics.avg_kda = 2.8
        
        mocks['analytics_engine'].analyze_player_performance.return_value = mock_analytics
        
        # Get filtered analytics
        result = dashboard._get_filtered_analytics()
        
        # Verify data structure
        assert 'players' in result
        assert 'summary' in result
        assert len(result['players']) == 3  # All 3 players
        
        # Verify summary generation
        summary = result['summary']
        assert summary['total_players'] == 3
        assert summary['total_games'] == 45  # 15 * 3 players
    
    def test_export_workflow(self, full_dashboard_setup):
        """Test complete export workflow."""
        dashboard, mocks = full_dashboard_setup
        
        # Set up analytics data
        mock_analytics = Mock()
        mock_analytics.games_played = 10
        mock_analytics.wins = 6
        mock_analytics.win_rate = 0.6
        mock_analytics.avg_kda = 2.0
        mock_analytics.avg_damage = 15000
        mock_analytics.avg_gold = 12000
        
        mocks['analytics_engine'].analyze_player_performance.return_value = mock_analytics
        
        # Test CSV export
        with patch('builtins.open', create=True) as mock_open:
            with patch('csv.DictWriter') as mock_csv_writer:
                dashboard._export_performance_report()
                
                # Verify file operations
                mock_open.assert_called_once()
                mock_csv_writer.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__])