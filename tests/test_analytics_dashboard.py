"""
Test suite for Analytics Dashboard with Real-time Filtering

Tests the comprehensive analytics dashboard functionality including:
- Dynamic filter panel creation
- Real-time chart updates
- Preset configurations
- Saved views functionality
- Comparison tools
- Filter interactions
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import gradio as gr
import plotly.graph_objects as go

from lol_team_optimizer.analytics_dashboard import (
    AnalyticsDashboard, FilterState, AnalyticsPreset, SavedView
)
from lol_team_optimizer.analytics_models import AnalyticsFilters, DateRange
from lol_team_optimizer.models import Player


class TestAnalyticsDashboard(unittest.TestCase):
    """Test suite for AnalyticsDashboard class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_analytics_engine = Mock()
        self.mock_viz_manager = Mock()
        self.mock_state_manager = Mock()
        self.mock_data_manager = Mock()
        
        # Create test players
        self.test_players = [
            Player(name="TestPlayer1", summoner_name="test1", puuid="puuid1"),
            Player(name="TestPlayer2", summoner_name="test2", puuid="puuid2"),
            Player(name="TestPlayer3", summoner_name="test3", puuid="puuid3")
        ]
        
        # Mock data manager responses
        self.mock_data_manager.load_player_data.return_value = self.test_players
        self.mock_analytics_engine.get_available_champions.return_value = [
            "Aatrox", "Ahri", "Akali", "Alistar", "Amumu"
        ]
        
        # Create dashboard instance
        self.dashboard = AnalyticsDashboard(
            analytics_engine=self.mock_analytics_engine,
            visualization_manager=self.mock_viz_manager,
            state_manager=self.mock_state_manager,
            data_manager=self.mock_data_manager
        )
    
    def test_filter_state_initialization(self):
        """Test FilterState initialization and conversion."""
        # Test default initialization
        filter_state = FilterState()
        self.assertEqual(filter_state.selected_players, [])
        self.assertEqual(filter_state.selected_champions, [])
        self.assertEqual(filter_state.min_games, 1)
        
        # Test conversion to AnalyticsFilters
        analytics_filters = filter_state.to_analytics_filters()
        self.assertIsInstance(analytics_filters, AnalyticsFilters)
        self.assertEqual(analytics_filters.min_games, 1)
        self.assertIsNone(analytics_filters.date_range)
        
        # Test with date range
        filter_state.date_range_start = "2024-01-01"
        filter_state.date_range_end = "2024-01-31"
        analytics_filters = filter_state.to_analytics_filters()
        self.assertIsNotNone(analytics_filters.date_range)
    
    def test_dashboard_initialization(self):
        """Test dashboard initialization."""
        self.assertIsNotNone(self.dashboard.current_filters)
        self.assertIsInstance(self.dashboard.current_filters, FilterState)
        self.assertEqual(len(self.dashboard.presets), 4)  # Should have 4 default presets
        self.assertEqual(len(self.dashboard.available_players), 3)
        self.assertEqual(len(self.dashboard.available_champions), 5)
    
    def test_preset_initialization(self):
        """Test analytics preset initialization."""
        presets = self.dashboard.presets
        
        # Check preset names
        preset_names = [preset.name for preset in presets]
        expected_names = ["Player Overview", "Team Synergy Analysis", "Recent Performance", "Champion Meta Analysis"]
        for name in expected_names:
            self.assertIn(name, preset_names)
        
        # Check preset structure
        for preset in presets:
            self.assertIsInstance(preset, AnalyticsPreset)
            self.assertIsInstance(preset.filters, FilterState)
            self.assertIsInstance(preset.chart_types, list)
            self.assertTrue(len(preset.chart_types) > 0)
    
    @patch('gradio.Dropdown')
    @patch('gradio.CheckboxGroup')
    @patch('gradio.Textbox')
    @patch('gradio.Slider')
    @patch('gradio.Button')
    @patch('gradio.Checkbox')
    def test_create_filter_panel(self, mock_checkbox, mock_button, mock_slider, 
                                mock_textbox, mock_checkboxgroup, mock_dropdown):
        """Test filter panel creation."""
        # Mock Gradio components
        mock_dropdown.return_value = Mock()
        mock_checkboxgroup.return_value = Mock()
        mock_textbox.return_value = Mock()
        mock_slider.return_value = Mock()
        mock_button.return_value = Mock()
        mock_checkbox.return_value = Mock()
        
        with patch('gradio.Accordion'), patch('gradio.Row'):
            components = self.dashboard._create_filter_panel()
        
        # Verify components were created
        self.assertTrue(len(components) > 0)
        
        # Verify filter components are stored
        self.assertIn('player_filter', self.dashboard.filter_components)
        self.assertIn('champion_filter', self.dashboard.filter_components)
        self.assertIn('role_filter', self.dashboard.filter_components)
        self.assertIn('apply_filters_btn', self.dashboard.filter_components)
    
    @patch('gradio.Dropdown')
    @patch('gradio.Button')
    @patch('gradio.Textbox')
    def test_create_preset_section(self, mock_textbox, mock_button, mock_dropdown):
        """Test preset section creation."""
        # Mock Gradio components
        mock_dropdown.return_value = Mock()
        mock_button.return_value = Mock()
        mock_textbox.return_value = Mock()
        
        with patch('gradio.Accordion'), patch('gradio.Row'), patch('gradio.Group'):
            components = self.dashboard._create_preset_section()
        
        # Verify components were created
        self.assertTrue(len(components) > 0)
        
        # Verify preset components are stored
        self.assertIn('preset_dropdown', self.dashboard.preset_components)
        self.assertIn('load_preset_btn', self.dashboard.preset_components)
        self.assertIn('saved_views_dropdown', self.dashboard.preset_components)
    
    @patch('gradio.Plot')
    @patch('gradio.Radio')
    @patch('gradio.Button')
    @patch('gradio.Dropdown')
    def test_create_analytics_display(self, mock_dropdown, mock_button, mock_radio, mock_plot):
        """Test analytics display creation."""
        # Mock Gradio components
        mock_plot.return_value = Mock()
        mock_radio.return_value = Mock()
        mock_button.return_value = Mock()
        mock_dropdown.return_value = Mock()
        
        with patch('gradio.Markdown'), patch('gradio.Row'), patch('gradio.Group'), patch('gradio.Tabs'), patch('gradio.Tab'):
            components = self.dashboard._create_analytics_display()
        
        # Verify components were created
        self.assertTrue(len(components) > 0)
        
        # Verify chart components are stored
        self.assertIn('player_radar_plot', self.dashboard.chart_components)
        self.assertIn('performance_trends_plot', self.dashboard.chart_components)
        self.assertIn('champion_heatmap_plot', self.dashboard.chart_components)
        self.assertIn('synergy_matrix_plot', self.dashboard.chart_components)
    
    def test_get_filtered_analytics_data(self):
        """Test filtered analytics data retrieval."""
        # Mock analytics engine response
        mock_player_analytics = Mock()
        mock_player_analytics.win_rate = 0.65
        mock_player_analytics.avg_kda = 2.5
        mock_player_analytics.games_played = 50
        mock_player_analytics.wins = 32
        
        self.mock_analytics_engine.analyze_player_performance.return_value = mock_player_analytics
        
        # Set up filters
        self.dashboard.current_filters.selected_players = ["TestPlayer1"]
        
        # Get filtered data
        analytics_data = self.dashboard._get_filtered_analytics_data()
        
        # Verify data structure
        self.assertIn('players', analytics_data)
        self.assertIn('summary', analytics_data)
        self.assertIn('filters_applied', analytics_data)
        self.assertIn('timestamp', analytics_data)
        
        # Verify player data
        self.assertIn('TestPlayer1', analytics_data['players'])
        
        # Verify analytics engine was called
        self.mock_analytics_engine.analyze_player_performance.assert_called()
    
    def test_create_player_radar_chart(self):
        """Test player radar chart creation."""
        # Mock visualization manager
        mock_figure = Mock(spec=go.Figure)
        self.mock_viz_manager.create_player_performance_radar.return_value = mock_figure
        
        # Create test analytics data
        analytics_data = {
            'players': {
                'TestPlayer1': Mock(
                    win_rate=0.65,
                    avg_kda=2.5,
                    avg_cs_per_min=7.2,
                    avg_vision_score=25.0,
                    avg_damage_per_min=500.0,
                    avg_gold_per_min=400.0
                )
            }
        }
        
        # Create chart
        chart = self.dashboard._create_player_radar_chart(analytics_data)
        
        # Verify chart was created
        self.assertIsNotNone(chart)
        self.mock_viz_manager.create_player_performance_radar.assert_called_once()
    
    def test_create_performance_trends_chart(self):
        """Test performance trends chart creation."""
        # Mock visualization manager
        mock_figure = Mock(spec=go.Figure)
        self.mock_viz_manager.create_performance_trend_line.return_value = mock_figure
        
        # Create test analytics data
        analytics_data = {'players': {'TestPlayer1': Mock()}}
        
        # Create chart
        chart = self.dashboard._create_performance_trends_chart(analytics_data)
        
        # Verify chart was created
        self.assertIsNotNone(chart)
        self.mock_viz_manager.create_performance_trend_line.assert_called_once()
    
    def test_generate_summary_statistics(self):
        """Test summary statistics generation."""
        # Create test player data
        players_data = {
            'TestPlayer1': Mock(games_played=50, wins=32, avg_kda=2.5, win_rate=0.64),
            'TestPlayer2': Mock(games_played=30, wins=15, avg_kda=1.8, win_rate=0.50),
            'TestPlayer3': Mock(games_played=40, wins=28, avg_kda=3.2, win_rate=0.70)
        }
        
        # Generate summary
        summary = self.dashboard._generate_summary_statistics(players_data)
        
        # Verify summary structure
        self.assertIn('total_players', summary)
        self.assertIn('total_games', summary)
        self.assertIn('avg_win_rate', summary)
        self.assertIn('avg_kda', summary)
        self.assertIn('performance_distribution', summary)
        
        # Verify calculations
        self.assertEqual(summary['total_players'], 3)
        self.assertEqual(summary['total_games'], 120)  # 50 + 30 + 40
        self.assertAlmostEqual(summary['avg_win_rate'], 75/120, places=2)  # 32 + 15 + 28 = 75
        self.assertAlmostEqual(summary['avg_kda'], (2.5 + 1.8 + 3.2) / 3, places=2)
    
    def test_saved_view_functionality(self):
        """Test saved view creation and management."""
        # Create a saved view
        view_id = "test_view_1"
        saved_view = SavedView(
            id=view_id,
            name="Test View",
            description="Test description",
            filters=FilterState(selected_players=["TestPlayer1"]),
            chart_configs=[],
            created_at=datetime.now()
        )
        
        # Add to dashboard
        self.dashboard.saved_views["Test View"] = saved_view
        
        # Verify saved view
        self.assertIn("Test View", self.dashboard.saved_views)
        retrieved_view = self.dashboard.saved_views["Test View"]
        self.assertEqual(retrieved_view.name, "Test View")
        self.assertEqual(retrieved_view.description, "Test description")
        self.assertEqual(retrieved_view.filters.selected_players, ["TestPlayer1"])
    
    def test_filter_state_updates(self):
        """Test filter state updates and conversions."""
        # Update filters
        self.dashboard.current_filters.selected_players = ["TestPlayer1", "TestPlayer2"]
        self.dashboard.current_filters.selected_roles = ["top", "jungle"]
        self.dashboard.current_filters.min_games = 10
        self.dashboard.current_filters.date_range_start = "2024-01-01"
        self.dashboard.current_filters.date_range_end = "2024-01-31"
        
        # Convert to analytics filters
        analytics_filters = self.dashboard.current_filters.to_analytics_filters()
        
        # Verify conversion
        self.assertEqual(analytics_filters.min_games, 10)
        self.assertIsNotNone(analytics_filters.date_range)
        self.assertEqual(analytics_filters.date_range.start_date.year, 2024)
        self.assertEqual(analytics_filters.date_range.start_date.month, 1)
        self.assertEqual(analytics_filters.date_range.start_date.day, 1)
    
    def test_empty_chart_creation(self):
        """Test empty chart creation."""
        message = "No data available"
        chart = self.dashboard._create_empty_chart(message)
        
        # Verify chart is created
        self.assertIsInstance(chart, go.Figure)
        
        # Verify chart has annotation with message
        self.assertTrue(len(chart.layout.annotations) > 0)
        self.assertIn(message, chart.layout.annotations[0].text)
    
    def test_error_chart_creation(self):
        """Test error chart creation."""
        error_message = "Test error"
        chart = self.dashboard._create_error_chart(error_message)
        
        # Verify chart is created
        self.assertIsInstance(chart, go.Figure)
        
        # Verify chart has error annotation
        self.assertTrue(len(chart.layout.annotations) > 0)
        self.assertIn(error_message, chart.layout.annotations[0].text)
    
    def test_chart_update_error_handling(self):
        """Test error handling in chart updates."""
        # Mock analytics engine to raise exception
        self.mock_analytics_engine.analyze_player_performance.side_effect = Exception("Test error")
        
        # Try to update charts
        chart_updates = self.dashboard._update_all_charts()
        
        # Verify error charts are returned
        self.assertEqual(len(chart_updates), 4)
        for chart in chart_updates:
            self.assertIsInstance(chart, go.Figure)


class TestFilterInteractions(unittest.TestCase):
    """Test suite for filter interactions and real-time updates."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_analytics_engine = Mock()
        self.mock_viz_manager = Mock()
        self.mock_state_manager = Mock()
        self.mock_data_manager = Mock()
        
        # Mock data manager responses
        self.mock_data_manager.load_player_data.return_value = [
            Player(name="Player1", summoner_name="p1", puuid="puuid1"),
            Player(name="Player2", summoner_name="p2", puuid="puuid2")
        ]
        self.mock_analytics_engine.get_available_champions.return_value = ["Aatrox", "Ahri"]
        
        # Create dashboard
        self.dashboard = AnalyticsDashboard(
            analytics_engine=self.mock_analytics_engine,
            visualization_manager=self.mock_viz_manager,
            state_manager=self.mock_state_manager,
            data_manager=self.mock_data_manager
        )
    
    def test_filter_value_extraction(self):
        """Test extraction of current filter values."""
        # Set filter values
        self.dashboard.current_filters.selected_players = ["Player1"]
        self.dashboard.current_filters.selected_champions = ["Aatrox"]
        self.dashboard.current_filters.selected_roles = ["top", "jungle"]
        self.dashboard.current_filters.date_range_start = "2024-01-01"
        self.dashboard.current_filters.date_range_end = "2024-01-31"
        self.dashboard.current_filters.min_games = 5
        self.dashboard.current_filters.queue_types = ["RANKED_SOLO_5x5"]
        
        # Get current values
        values = self.dashboard._get_current_filter_values()
        
        # Verify values
        self.assertEqual(values[0], ["Player1"])  # players
        self.assertEqual(values[1], ["Aatrox"])   # champions
        self.assertEqual(values[2], ["Top", "Jungle"])  # roles (capitalized)
        self.assertEqual(values[3], "2024-01-01")  # start date
        self.assertEqual(values[4], "2024-01-31")  # end date
        self.assertEqual(values[5], 5)  # min games
        self.assertEqual(values[6], ["RANKED_SOLO_5x5"])  # queue types
    
    def test_empty_chart_updates(self):
        """Test empty chart updates generation."""
        chart_updates = self.dashboard._get_empty_chart_updates()
        
        # Verify 4 charts are returned
        self.assertEqual(len(chart_updates), 4)
        
        # Verify all are Figure objects
        for chart in chart_updates:
            self.assertIsInstance(chart, go.Figure)
    
    def test_error_chart_updates(self):
        """Test error chart updates generation."""
        error_message = "Test error message"
        chart_updates = self.dashboard._get_error_chart_updates(error_message)
        
        # Verify 4 charts are returned
        self.assertEqual(len(chart_updates), 4)
        
        # Verify all are Figure objects with error message
        for chart in chart_updates:
            self.assertIsInstance(chart, go.Figure)
            self.assertTrue(len(chart.layout.annotations) > 0)
            self.assertIn(error_message, chart.layout.annotations[0].text)


if __name__ == '__main__':
    unittest.main()