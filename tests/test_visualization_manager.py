"""
Tests for the VisualizationManager and InteractiveChartBuilder classes.

This module tests all visualization components including chart creation,
interactive features, drill-down capabilities, and filter functionality.
"""

import pytest
import plotly.graph_objects as go
import gradio as gr
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from lol_team_optimizer.visualization_manager import (
    VisualizationManager, InteractiveChartBuilder, ColorSchemeManager,
    ChartConfiguration, ChartType, DrillDownData
)


class TestColorSchemeManager:
    """Test color scheme management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.color_manager = ColorSchemeManager()
    
    def test_initialization(self):
        """Test color scheme manager initialization."""
        assert hasattr(self.color_manager, 'schemes')
        assert 'lol_classic' in self.color_manager.schemes
        assert 'performance' in self.color_manager.schemes
        assert 'synergy' in self.color_manager.schemes
    
    def test_get_color_palette_lol_classic(self):
        """Test getting LoL classic color palette."""
        colors = self.color_manager.get_color_palette('lol_classic', 5)
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
    
    def test_get_color_palette_performance(self):
        """Test getting performance color palette."""
        colors = self.color_manager.get_color_palette('performance', 4)
        assert len(colors) == 4
        # Should use gradient interpolation
        assert all(color.startswith('rgb(') or color.startswith('#') for color in colors)
    
    def test_get_color_palette_fallback(self):
        """Test fallback to default colors for unknown scheme."""
        colors = self.color_manager.get_color_palette('unknown_scheme', 3)
        assert len(colors) == 3
        # Should fallback to Plotly default colors
    
    def test_interpolate_colors(self):
        """Test color interpolation functionality."""
        base_colors = ['#FF0000', '#00FF00', '#0000FF']
        interpolated = self.color_manager._interpolate_colors(base_colors, 6)
        assert len(interpolated) == 6
        assert all(color.startswith('rgb(') for color in interpolated)


class TestVisualizationManager:
    """Test main visualization manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.viz_manager = VisualizationManager()
        
        # Sample player data
        self.sample_player_data = {
            'performance_metrics': {
                'overall': {
                    'win_rate': 0.65,
                    'avg_kda': 2.5,
                    'avg_cs_per_min': 7.2,
                    'avg_vision_score': 25.0,
                    'avg_damage_per_min': 500.0,
                    'avg_gold_per_min': 400.0,
                    'recent_form': 0.2
                },
                'top': {
                    'win_rate': 0.70,
                    'avg_kda': 2.8,
                    'avg_cs_per_min': 8.0,
                    'avg_vision_score': 20.0,
                    'avg_damage_per_min': 600.0,
                    'avg_gold_per_min': 450.0,
                    'recent_form': 0.3
                }
            },
            'roles': ['overall', 'top']
        }
        
        # Sample synergy data
        self.sample_synergy_data = {
            'players': ['Player1', 'Player2', 'Player3'],
            'synergy_scores': {
                ('Player1', 'Player2'): 0.8,
                ('Player1', 'Player3'): 0.6,
                ('Player2', 'Player3'): 0.4
            }
        }
        
        # Sample recommendations
        self.sample_recommendations = [
            {
                'champion_name': 'Garen',
                'score': 0.85,
                'confidence': 0.90,
                'role': 'top'
            },
            {
                'champion_name': 'Darius',
                'score': 0.78,
                'confidence': 0.85,
                'role': 'top'
            },
            {
                'champion_name': 'Malphite',
                'score': 0.72,
                'confidence': 0.80,
                'role': 'top'
            }
        ]
        
        # Sample trend data
        self.sample_trend_data = {
            'time_series': {
                'win_rate': {
                    '2024-01-01': 0.60,
                    '2024-01-02': 0.62,
                    '2024-01-03': 0.65,
                    '2024-01-04': 0.68,
                    '2024-01-05': 0.70
                },
                'avg_kda': {
                    '2024-01-01': 2.0,
                    '2024-01-02': 2.2,
                    '2024-01-03': 2.4,
                    '2024-01-04': 2.6,
                    '2024-01-05': 2.8
                }
            },
            'metrics': ['win_rate', 'avg_kda']
        }
    
    def test_initialization(self):
        """Test visualization manager initialization."""
        assert hasattr(self.viz_manager, 'color_manager')
        assert hasattr(self.viz_manager, 'chart_cache')
        assert hasattr(self.viz_manager, 'default_layout')
        assert isinstance(self.viz_manager.color_manager, ColorSchemeManager)
    
    def test_create_player_performance_radar(self):
        """Test player performance radar chart creation."""
        fig = self.viz_manager.create_player_performance_radar(self.sample_player_data)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Two roles: overall and top
        assert all(isinstance(trace, go.Scatterpolar) for trace in fig.data)
        
        # Check radar chart properties
        for trace in fig.data:
            assert trace.fill == 'toself'
            assert len(trace.r) == 7  # 7 performance categories
            assert len(trace.theta) == 7
    
    def test_create_player_performance_radar_empty_data(self):
        """Test radar chart with empty data."""
        empty_data = {'performance_metrics': {}, 'roles': []}
        fig = self.viz_manager.create_player_performance_radar(empty_data)
        
        assert isinstance(fig, go.Figure)
        # Should handle empty data gracefully
    
    def test_create_team_synergy_heatmap(self):
        """Test team synergy heatmap creation."""
        fig = self.viz_manager.create_team_synergy_heatmap(self.sample_synergy_data)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert isinstance(fig.data[0], go.Heatmap)
        
        # Check heatmap properties
        heatmap = fig.data[0]
        assert heatmap.zmin == -1
        assert heatmap.zmax == 1
        assert len(heatmap.x) == 3  # 3 players
        assert len(heatmap.y) == 3
        # Check that colorscale is set (Plotly expands it to actual values)
        assert heatmap.colorscale is not None
    
    def test_create_team_synergy_heatmap_empty_data(self):
        """Test heatmap with empty data."""
        empty_data = {'players': [], 'synergy_scores': {}}
        fig = self.viz_manager.create_team_synergy_heatmap(empty_data)
        
        assert isinstance(fig, go.Figure)
        # Should return empty chart message
    
    def test_create_champion_recommendation_chart(self):
        """Test champion recommendation chart creation."""
        fig = self.viz_manager.create_champion_recommendation_chart(self.sample_recommendations)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 2  # Bar chart + confidence indicators
        
        # Check bar chart properties
        bar_trace = fig.data[0]
        assert isinstance(bar_trace, go.Bar)
        assert len(bar_trace.x) == 3  # 3 recommendations
        assert len(bar_trace.y) == 3
        assert all(y <= 100 for y in bar_trace.y)  # Scores should be percentages
    
    def test_create_champion_recommendation_chart_empty_data(self):
        """Test recommendation chart with empty data."""
        fig = self.viz_manager.create_champion_recommendation_chart([])
        
        assert isinstance(fig, go.Figure)
        # Should return empty chart message
    
    def test_create_performance_trend_line(self):
        """Test performance trend line chart creation."""
        fig = self.viz_manager.create_performance_trend_line(self.sample_trend_data)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 4  # 2 metrics + 2 trend lines
        
        # Check line chart properties
        line_traces = [trace for trace in fig.data if isinstance(trace, go.Scatter)]
        assert len(line_traces) == 4
        
        # Check that main traces have markers
        main_traces = [trace for trace in line_traces if 'Trend' not in trace.name]
        assert len(main_traces) == 2
        for trace in main_traces:
            assert 'markers' in trace.mode
    
    def test_create_performance_trend_line_empty_data(self):
        """Test trend line with empty data."""
        empty_data = {'time_series': {}, 'metrics': []}
        fig = self.viz_manager.create_performance_trend_line(empty_data)
        
        assert isinstance(fig, go.Figure)
        # Should return empty chart message
    
    def test_create_composition_comparison(self):
        """Test composition comparison chart creation."""
        compositions = [
            {
                'name': 'Comp A',
                'win_rate': 0.75,
                'synergy_score': 0.80,
                'confidence': 0.85
            },
            {
                'name': 'Comp B',
                'win_rate': 0.70,
                'synergy_score': 0.75,
                'confidence': 0.80
            }
        ]
        
        fig = self.viz_manager.create_composition_comparison(compositions)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # Win rate, synergy, confidence bars
        
        # Check grouped bar chart properties
        for trace in fig.data:
            assert isinstance(trace, go.Bar)
            assert len(trace.x) == 2  # 2 compositions
            assert len(trace.y) == 2
    
    def test_create_composition_comparison_empty_data(self):
        """Test composition comparison with empty data."""
        fig = self.viz_manager.create_composition_comparison([])
        
        assert isinstance(fig, go.Figure)
        # Should return empty chart message
    
    def test_add_drill_down_capability(self):
        """Test adding drill-down capability to charts."""
        fig = go.Figure()
        drill_down_data = {'level': 1, 'data': {'test': 'data'}}
        
        enhanced_fig = self.viz_manager._add_drill_down_capability(fig, drill_down_data)
        
        assert isinstance(enhanced_fig, go.Figure)
        assert enhanced_fig.layout.clickmode == 'event+select'
        assert hasattr(enhanced_fig.layout, 'meta')
        assert 'drill_down_data' in enhanced_fig.layout.meta
    
    def test_create_error_chart(self):
        """Test error chart creation."""
        error_message = "Test error message"
        fig = self.viz_manager._create_error_chart(error_message)
        
        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "Visualization Error"
        assert len(fig.layout.annotations) == 1
        assert error_message in fig.layout.annotations[0].text
    
    def test_create_empty_chart(self):
        """Test empty chart creation."""
        message = "No data available"
        fig = self.viz_manager._create_empty_chart(message)
        
        assert isinstance(fig, go.Figure)
        assert fig.layout.title.text == "No Data Available"
        assert len(fig.layout.annotations) == 1
        assert message in fig.layout.annotations[0].text
    
    def test_chart_configuration(self):
        """Test chart configuration usage."""
        config = ChartConfiguration(
            chart_type=ChartType.RADAR,
            title="Custom Title",
            data_source="test_source",
            height=600
        )
        
        fig = self.viz_manager.create_player_performance_radar(
            self.sample_player_data, config
        )
        
        assert fig.layout.title.text == "Custom Title"
        assert fig.layout.height == 600


class TestInteractiveChartBuilder:
    """Test interactive chart builder functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.viz_manager = VisualizationManager()
        self.chart_builder = InteractiveChartBuilder(self.viz_manager)
        
        self.sample_data = {
            'title': 'Test Chart',
            'source': 'test_data',
            'available_players': ['Player1', 'Player2', 'Player3'],
            'available_champions': ['Garen', 'Darius', 'Malphite'],
            'available_metrics': ['win_rate', 'kda', 'cs_per_min'],
            'performance_metrics': {
                'Player1': {'win_rate': 0.65, 'avg_kda': 2.5},
                'Player2': {'win_rate': 0.70, 'avg_kda': 2.8}
            },
            'recommendations': [
                {'champion_name': 'Garen', 'score': 0.85, 'confidence': 0.90}
            ]
        }
    
    def test_initialization(self):
        """Test interactive chart builder initialization."""
        assert hasattr(self.chart_builder, 'viz_manager')
        assert isinstance(self.chart_builder.viz_manager, VisualizationManager)
    
    @patch('gradio.Dropdown')
    @patch('gradio.CheckboxGroup')
    @patch('gradio.Textbox')
    def test_create_filter_components(self, mock_textbox, mock_checkbox, mock_dropdown):
        """Test filter component creation."""
        filters = ['player', 'champion', 'role', 'date_range', 'metric']
        
        # Mock Gradio components
        mock_dropdown.return_value = Mock()
        mock_checkbox.return_value = Mock()
        mock_textbox.return_value = Mock()
        
        components = self.chart_builder._create_filter_components(filters, self.sample_data)
        
        # Should create components for each filter type
        assert len(components) > 0
        
        # Verify that Gradio components were called
        assert mock_dropdown.called
        assert mock_checkbox.called
        assert mock_textbox.called
    
    def test_build_filterable_chart_radar(self):
        """Test building filterable radar chart."""
        with patch.object(self.viz_manager, 'create_player_performance_radar') as mock_create:
            mock_create.return_value = go.Figure()
            
            fig, components = self.chart_builder.build_filterable_chart(
                self.sample_data, ChartType.RADAR.value, ['player', 'role']
            )
            
            assert isinstance(fig, go.Figure)
            mock_create.assert_called_once()
    
    def test_build_filterable_chart_heatmap(self):
        """Test building filterable heatmap chart."""
        with patch.object(self.viz_manager, 'create_team_synergy_heatmap') as mock_create:
            mock_create.return_value = go.Figure()
            
            fig, components = self.chart_builder.build_filterable_chart(
                self.sample_data, ChartType.HEATMAP.value, ['player']
            )
            
            assert isinstance(fig, go.Figure)
            mock_create.assert_called_once()
    
    def test_build_filterable_chart_bar(self):
        """Test building filterable bar chart."""
        with patch.object(self.viz_manager, 'create_champion_recommendation_chart') as mock_create:
            mock_create.return_value = go.Figure()
            
            fig, components = self.chart_builder.build_filterable_chart(
                self.sample_data, ChartType.BAR.value, ['champion']
            )
            
            assert isinstance(fig, go.Figure)
            mock_create.assert_called_once()
    
    def test_build_filterable_chart_line(self):
        """Test building filterable line chart."""
        with patch.object(self.viz_manager, 'create_performance_trend_line') as mock_create:
            mock_create.return_value = go.Figure()
            
            fig, components = self.chart_builder.build_filterable_chart(
                self.sample_data, ChartType.LINE.value, ['date_range', 'metric']
            )
            
            assert isinstance(fig, go.Figure)
            mock_create.assert_called_once()
    
    def test_build_filterable_chart_unsupported(self):
        """Test building chart with unsupported type."""
        fig, components = self.chart_builder.build_filterable_chart(
            self.sample_data, 'unsupported_type', []
        )
        
        assert isinstance(fig, go.Figure)
        # Should return error chart
        assert "Error:" in fig.layout.annotations[0].text
    
    def test_apply_filters_player(self):
        """Test applying player filter."""
        filters = {'player': ['Player1']}
        filtered_data = self.chart_builder._apply_filters(self.sample_data, filters)
        
        assert 'performance_metrics' in filtered_data
        assert 'Player1' in filtered_data['performance_metrics']
        assert 'Player2' not in filtered_data['performance_metrics']
    
    def test_apply_filters_champion(self):
        """Test applying champion filter."""
        filters = {'champion': ['Garen']}
        filtered_data = self.chart_builder._apply_filters(self.sample_data, filters)
        
        assert 'recommendations' in filtered_data
        assert len(filtered_data['recommendations']) == 1
        assert filtered_data['recommendations'][0]['champion_name'] == 'Garen'
    
    def test_apply_filters_role(self):
        """Test applying role filter."""
        data_with_roles = self.sample_data.copy()
        data_with_roles['roles'] = ['top', 'jungle', 'middle']
        
        filters = {'role': ['Top', 'Jungle']}
        filtered_data = self.chart_builder._apply_filters(data_with_roles, filters)
        
        assert 'roles' in filtered_data
        assert 'top' in filtered_data['roles']
        assert 'jungle' in filtered_data['roles']
        assert 'middle' not in filtered_data['roles']
    
    def test_apply_filters_date_range(self):
        """Test applying date range filter."""
        data_with_time_series = self.sample_data.copy()
        data_with_time_series['time_series'] = {
            'win_rate': {
                '2024-01-01': 0.60,
                '2024-01-02': 0.65,
                '2024-01-03': 0.70
            }
        }
        
        filters = {
            'start_date': '2024-01-01',
            'end_date': '2024-01-02'
        }
        filtered_data = self.chart_builder._apply_filters(data_with_time_series, filters)
        
        assert 'time_series' in filtered_data
        assert len(filtered_data['time_series']['win_rate']) == 2
        assert '2024-01-03' not in filtered_data['time_series']['win_rate']
    
    def test_apply_filters_invalid_date(self):
        """Test applying invalid date range filter."""
        data_with_time_series = self.sample_data.copy()
        data_with_time_series['time_series'] = {'win_rate': {'2024-01-01': 0.60}}
        
        filters = {
            'start_date': 'invalid-date',
            'end_date': '2024-01-02'
        }
        
        # Should handle invalid dates gracefully
        filtered_data = self.chart_builder._apply_filters(data_with_time_series, filters)
        assert 'time_series' in filtered_data
    
    def test_update_chart_with_filters(self):
        """Test updating chart with filter values."""
        filter_values = {'player': ['Player1']}
        
        with patch.object(self.viz_manager, 'create_champion_recommendation_chart') as mock_create:
            mock_create.return_value = go.Figure()
            
            data_with_chart_type = self.sample_data.copy()
            data_with_chart_type['chart_type'] = ChartType.BAR.value
            
            fig = self.chart_builder.update_chart_with_filters(data_with_chart_type, filter_values)
            
            assert isinstance(fig, go.Figure)
            mock_create.assert_called_once()
    
    @patch('gradio.Blocks')
    @patch('gradio.Tabs')
    @patch('gradio.Tab')
    @patch('gradio.Plot')
    @patch('gradio.Markdown')
    def test_create_dashboard_layout(self, mock_markdown, mock_plot, mock_tab, mock_tabs, mock_blocks):
        """Test dashboard layout creation."""
        # Mock Gradio components
        mock_blocks.return_value.__enter__ = Mock(return_value=Mock())
        mock_blocks.return_value.__exit__ = Mock(return_value=None)
        mock_tabs.return_value.__enter__ = Mock(return_value=Mock())
        mock_tabs.return_value.__exit__ = Mock(return_value=None)
        mock_tab.return_value.__enter__ = Mock(return_value=Mock())
        mock_tab.return_value.__exit__ = Mock(return_value=None)
        
        charts = [
            (go.Figure(), 'performance'),
            (go.Figure(), 'synergy'),
            (go.Figure(), 'performance')
        ]
        
        dashboard = self.chart_builder.create_dashboard_layout(charts)
        
        # Verify that Gradio components were called
        mock_blocks.assert_called()
        mock_tabs.assert_called()
    
    def test_create_dashboard_layout_error_handling(self):
        """Test dashboard layout creation with error."""
        # Test with invalid chart data
        invalid_charts = [("not_a_figure", "category")]
        
        dashboard = self.chart_builder.create_dashboard_layout(invalid_charts)
        
        # Should return error dashboard
        assert dashboard is not None


class TestChartConfiguration:
    """Test chart configuration functionality."""
    
    def test_chart_configuration_creation(self):
        """Test creating chart configuration."""
        config = ChartConfiguration(
            chart_type=ChartType.RADAR,
            title="Test Chart",
            data_source="test_data",
            filters=['player', 'role'],
            color_scheme="lol_classic",
            height=600
        )
        
        assert config.chart_type == ChartType.RADAR
        assert config.title == "Test Chart"
        assert config.data_source == "test_data"
        assert config.filters == ['player', 'role']
        assert config.color_scheme == "lol_classic"
        assert config.height == 600
        assert config.show_legend is True  # Default value
    
    def test_chart_configuration_defaults(self):
        """Test chart configuration with default values."""
        config = ChartConfiguration(
            chart_type=ChartType.BAR,
            title="Test",
            data_source="test"
        )
        
        assert config.filters == []
        assert config.color_scheme == "viridis"
        assert config.interactive_features == []
        assert config.export_options == []
        assert config.height == 500
        assert config.width is None
        assert config.show_legend is True
        assert config.animation_enabled is True


class TestDrillDownData:
    """Test drill-down data functionality."""
    
    def test_drill_down_data_creation(self):
        """Test creating drill-down data."""
        drill_down = DrillDownData(
            level=1,
            parent_key="player1",
            data={'performance': 0.85},
            available_drill_downs=['champion', 'role']
        )
        
        assert drill_down.level == 1
        assert drill_down.parent_key == "player1"
        assert drill_down.data == {'performance': 0.85}
        assert drill_down.available_drill_downs == ['champion', 'role']
    
    def test_drill_down_data_defaults(self):
        """Test drill-down data with default values."""
        drill_down = DrillDownData(
            level=0,
            parent_key="root",
            data={}
        )
        
        assert drill_down.available_drill_downs == []


class TestIntegration:
    """Integration tests for visualization components."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.viz_manager = VisualizationManager()
        self.chart_builder = InteractiveChartBuilder(self.viz_manager)
    
    def test_end_to_end_radar_chart_with_filters(self):
        """Test complete workflow for radar chart with filters."""
        # Prepare comprehensive data
        data = {
            'title': 'Player Performance Analysis',
            'source': 'match_data',
            'available_players': ['Player1', 'Player2'],
            'performance_metrics': {
                'Player1': {
                    'win_rate': 0.65,
                    'avg_kda': 2.5,
                    'avg_cs_per_min': 7.2,
                    'avg_vision_score': 25.0,
                    'avg_damage_per_min': 500.0,
                    'avg_gold_per_min': 400.0,
                    'recent_form': 0.2
                }
            },
            'roles': ['overall']
        }
        
        # Build filterable chart
        fig, components = self.chart_builder.build_filterable_chart(
            data, ChartType.RADAR.value, ['player', 'role']
        )
        
        # Verify chart creation
        assert isinstance(fig, go.Figure)
        assert len(components) > 0
        
        # Apply filters and update
        filter_values = {'player': ['Player1']}
        updated_fig = self.chart_builder.update_chart_with_filters(
            {**data, 'chart_type': ChartType.RADAR.value}, filter_values
        )
        
        assert isinstance(updated_fig, go.Figure)
    
    def test_end_to_end_multiple_chart_dashboard(self):
        """Test creating dashboard with multiple chart types."""
        # Create different chart types
        player_data = {
            'performance_metrics': {'overall': {'win_rate': 0.65, 'avg_kda': 2.5}},
            'roles': ['overall']
        }
        synergy_data = {
            'players': ['Player1', 'Player2'],
            'synergy_scores': {('Player1', 'Player2'): 0.8}
        }
        recommendations = [
            {'champion_name': 'Garen', 'score': 0.85, 'confidence': 0.90, 'role': 'top'}
        ]
        
        # Create charts
        radar_fig = self.viz_manager.create_player_performance_radar(player_data)
        heatmap_fig = self.viz_manager.create_team_synergy_heatmap(synergy_data)
        bar_fig = self.viz_manager.create_champion_recommendation_chart(recommendations)
        
        # Create dashboard
        charts = [
            (radar_fig, 'performance'),
            (heatmap_fig, 'synergy'),
            (bar_fig, 'recommendations')
        ]
        
        dashboard = self.chart_builder.create_dashboard_layout(charts)
        
        # Verify dashboard creation
        assert dashboard is not None
    
    def test_error_handling_throughout_pipeline(self):
        """Test error handling in complete visualization pipeline."""
        # Test with malformed data
        malformed_data = {
            'invalid_structure': True,
            'missing_required_fields': None
        }
        
        # Should handle errors gracefully
        fig = self.viz_manager.create_player_performance_radar(malformed_data)
        assert isinstance(fig, go.Figure)
        
        # Test filter application with invalid data
        filter_values = {'invalid_filter': 'invalid_value'}
        filtered_data = self.chart_builder._apply_filters(malformed_data, filter_values)
        assert isinstance(filtered_data, dict)
        
        # Test chart building with invalid type
        fig, components = self.chart_builder.build_filterable_chart(
            malformed_data, 'invalid_chart_type', []
        )
        assert isinstance(fig, go.Figure)


if __name__ == '__main__':
    pytest.main([__file__])