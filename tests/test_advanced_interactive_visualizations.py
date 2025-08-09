"""
Tests for advanced interactive visualizations with drill-down functionality.

This module tests the enhanced visualization capabilities including:
- Player performance radar charts with role-specific breakdowns
- Champion performance heatmaps with statistical significance indicators
- Team synergy matrices with interactive exploration
- Performance trend visualizations with predictive analytics
- Comparative analysis charts for multiple players or time periods
- Chart export functionality in multiple formats
- Drill-down interactions and navigation
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import plotly.graph_objects as go
from typing import Dict, List, Any

from lol_team_optimizer.visualization_manager import (
    VisualizationManager, InteractiveChartBuilder, ChartConfiguration, 
    ChartType, ColorSchemeManager, DrillDownData
)
from lol_team_optimizer.analytics_models import (
    PerformanceMetrics, ChampionPerformanceMetrics, AnalyticsFilters
)


class TestAdvancedVisualizationManager:
    """Test suite for advanced visualization manager functionality."""
    
    @pytest.fixture
    def viz_manager(self):
        """Create visualization manager instance."""
        return VisualizationManager()
    
    @pytest.fixture
    def sample_player_data(self):
        """Create sample player performance data."""
        return {
            'player_name': 'TestPlayer',
            'performance_by_role': {
                'top': {
                    'games_played': 50,
                    'win_rate': 0.65,
                    'avg_kda': 2.3,
                    'avg_cs_per_min': 7.2,
                    'avg_vision_score': 18.5,
                    'avg_damage_per_min': 450,
                    'avg_gold_per_min': 380,
                    'kill_participation': 0.72,
                    'first_blood_rate': 0.15,
                    'objective_control_score': 0.68,
                    'recent_form': 0.2,
                    'confidence_intervals': {
                        'win_rate': 0.05,
                        'avg_kda': 0.1,
                        'avg_cs_per_min': 0.3
                    }
                },
                'jungle': {
                    'games_played': 30,
                    'win_rate': 0.58,
                    'avg_kda': 2.8,
                    'avg_cs_per_min': 5.8,
                    'avg_vision_score': 22.1,
                    'avg_damage_per_min': 420,
                    'avg_gold_per_min': 360,
                    'kill_participation': 0.78,
                    'first_blood_rate': 0.22,
                    'objective_control_score': 0.75,
                    'recent_form': -0.1,
                    'confidence_intervals': {
                        'win_rate': 0.08,
                        'avg_kda': 0.15,
                        'avg_cs_per_min': 0.4
                    }
                }
            }
        }
    
    @pytest.fixture
    def sample_champion_data(self):
        """Create sample champion performance data."""
        champions = ['Garen', 'Darius', 'Fiora', 'Camille']
        metrics = ['win_rate', 'avg_kda', 'pick_rate']
        
        performance_matrix = {}
        significance_matrix = {}
        
        for champion in champions:
            for metric in metrics:
                key = f"{champion}_{metric}"
                performance_matrix[key] = np.random.uniform(0.3, 0.8)
                significance_matrix[key] = {
                    'p_value': np.random.uniform(0.001, 0.1),
                    'effect_size': np.random.uniform(0.1, 0.8),
                    'sample_size': np.random.randint(20, 100)
                }
        
        return {
            'champions': champions,
            'metrics': metrics,
            'performance_matrix': performance_matrix,
            'significance_matrix': significance_matrix,
            'time_series': {
                f"{champion}_{metric}": {
                    (datetime.now() - timedelta(days=i)).isoformat(): np.random.uniform(0.3, 0.8)
                    for i in range(30)
                } for champion in champions for metric in metrics
            }
        }
    
    @pytest.fixture
    def sample_synergy_data(self):
        """Create sample team synergy data."""
        players = ['Player1', 'Player2', 'Player3', 'Player4', 'Player5']
        
        synergy_scores = {}
        confidence_scores = {}
        sample_sizes = {}
        
        for i, player1 in enumerate(players):
            for j, player2 in enumerate(players):
                if i < j:  # Only create upper triangle
                    key = tuple(sorted([player1, player2]))
                    synergy_scores[key] = np.random.uniform(0.2, 0.9)
                    confidence_scores[key] = np.random.uniform(0.6, 0.95)
                    sample_sizes[key] = np.random.randint(10, 50)
        
        return {
            'players': players,
            'synergy_scores': synergy_scores,
            'confidence_scores': confidence_scores,
            'sample_sizes': sample_sizes,
            'individual_performance': {
                player: {
                    'win_rate': np.random.uniform(0.4, 0.7),
                    'avg_kda': np.random.uniform(1.5, 3.0),
                    'avg_cs_per_min': np.random.uniform(5.0, 8.0),
                    'avg_vision_score': np.random.uniform(15, 25),
                    'avg_damage_per_min': np.random.uniform(300, 500)
                } for player in players
            },
            'detailed_synergy': {
                tuple(sorted([players[0], players[1]])): {
                    'champion_combinations': {
                        'Garen+Graves': {'synergy_score': 0.75, 'win_rate': 0.68},
                        'Darius+Elise': {'synergy_score': 0.82, 'win_rate': 0.71},
                        'Fiora+Kindred': {'synergy_score': 0.65, 'win_rate': 0.59}
                    }
                }
            }
        }
    
    @pytest.fixture
    def sample_trend_data(self):
        """Create sample trend data with predictions."""
        base_date = datetime.now() - timedelta(days=90)
        dates = [(base_date + timedelta(days=i)).isoformat() for i in range(90)]
        
        # Generate realistic trend data
        win_rate_trend = [0.5 + 0.1 * np.sin(i * 0.1) + np.random.normal(0, 0.02) for i in range(90)]
        kda_trend = [2.0 + 0.3 * np.sin(i * 0.08) + np.random.normal(0, 0.05) for i in range(90)]
        
        # Generate predictions for next 30 days
        pred_dates = [(base_date + timedelta(days=90 + i)).isoformat() for i in range(30)]
        win_rate_pred = [win_rate_trend[-1] + 0.01 * i + np.random.normal(0, 0.01) for i in range(30)]
        kda_pred = [kda_trend[-1] + 0.02 * i + np.random.normal(0, 0.02) for i in range(30)]
        
        return {
            'time_series': {
                'win_rate': dict(zip(dates, win_rate_trend)),
                'avg_kda': dict(zip(dates, kda_trend))
            },
            'predictions': {
                'win_rate': dict(zip(pred_dates, win_rate_pred)),
                'avg_kda': dict(zip(pred_dates, kda_pred))
            },
            'confidence_bands': {
                'win_rate': {
                    date: {'upper': pred + 0.05, 'lower': pred - 0.05}
                    for date, pred in zip(pred_dates, win_rate_pred)
                },
                'avg_kda': {
                    date: {'upper': pred + 0.1, 'lower': pred - 0.1}
                    for date, pred in zip(pred_dates, kda_pred)
                }
            },
            'metrics': ['win_rate', 'avg_kda']
        }
    
    @pytest.fixture
    def sample_comparison_data(self):
        """Create sample comparative analysis data."""
        players = ['Player1', 'Player2', 'Player3']
        metrics = ['win_rate', 'avg_kda', 'avg_cs_per_min']
        
        performance_data = {}
        statistical_tests = {}
        
        for player in players:
            for metric in metrics:
                key = f"{player}_{metric}"
                performance_data[key] = {
                    'mean': np.random.uniform(0.4, 0.8),
                    'std_error': np.random.uniform(0.01, 0.05),
                    'sample_size': np.random.randint(30, 100)
                }
                statistical_tests[f"{metric}_{player}"] = {
                    'p_value': np.random.uniform(0.001, 0.1),
                    'effect_size': np.random.uniform(0.2, 0.8)
                }
        
        return {
            'comparison_type': 'players',
            'entities': players,
            'metrics': metrics,
            'performance_data': performance_data,
            'statistical_tests': statistical_tests,
            'detailed_stats': {
                player: {
                    'mean': np.random.uniform(0.5, 0.7),
                    'median': np.random.uniform(0.4, 0.6),
                    'std_dev': np.random.uniform(0.05, 0.15),
                    'min': np.random.uniform(0.2, 0.4),
                    'max': np.random.uniform(0.7, 0.9)
                } for player in players
            }
        }
    
    def test_create_player_performance_radar_with_drill_down(self, viz_manager, sample_player_data):
        """Test creation of advanced player performance radar chart."""
        config = ChartConfiguration(
            chart_type=ChartType.RADAR,
            title="Advanced Player Performance",
            data_source="player_performance_detailed"
        )
        
        fig = viz_manager.create_player_performance_radar_with_drill_down(
            sample_player_data, role_breakdown=True, config=config
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 2  # At least 2 roles
        
        # Verify radar chart structure
        for trace in fig.data:
            assert trace.type == 'scatterpolar'
            assert len(trace.r) == 10  # 10 performance categories
            assert len(trace.theta) == 10
        
        # Verify drill-down metadata
        assert 'drill_down_key' in fig.layout.meta
        drill_down_key = fig.layout.meta['drill_down_key']
        assert drill_down_key in viz_manager.drill_down_cache
        
        cached_data = viz_manager.drill_down_cache[drill_down_key]
        assert cached_data['type'] == 'player_performance_radar'
        assert 'available_breakdowns' in cached_data
        assert 'by_champion' in cached_data['available_breakdowns']
    
    def test_create_champion_performance_heatmap_with_significance(self, viz_manager, sample_champion_data):
        """Test creation of champion performance heatmap with statistical significance."""
        config = ChartConfiguration(
            chart_type=ChartType.HEATMAP,
            title="Champion Performance with Significance",
            data_source="champion_performance_stats"
        )
        
        fig = viz_manager.create_champion_performance_heatmap_with_significance(
            sample_champion_data, config=config
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'heatmap'
        
        # Verify heatmap dimensions
        champions = sample_champion_data['champions']
        metrics = sample_champion_data['metrics']
        assert len(fig.data[0].z) == len(champions)
        assert len(fig.data[0].z[0]) == len(metrics)
        
        # Verify significance annotations
        assert len(fig.layout.annotations) > 0
        
        # Verify drill-down capability
        assert 'drill_down_key' in fig.layout.meta
    
    def test_create_team_synergy_matrix_interactive(self, viz_manager, sample_synergy_data):
        """Test creation of interactive team synergy matrix."""
        config = ChartConfiguration(
            chart_type=ChartType.HEATMAP,
            title="Interactive Team Synergy Matrix",
            data_source="synergy_analysis"
        )
        
        fig = viz_manager.create_team_synergy_matrix_interactive(
            sample_synergy_data, config=config
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].type == 'heatmap'
        
        # Verify matrix dimensions
        players = sample_synergy_data['players']
        n_players = len(players)
        assert len(fig.data[0].z) == n_players
        assert len(fig.data[0].z[0]) == n_players
        
        # Verify diagonal values (self-synergy should be 1.0)
        for i in range(n_players):
            assert fig.data[0].z[i][i] == 1.0
        
        # Verify annotations for synergy scores
        assert len(fig.layout.annotations) > 0
        
        # Verify drill-down capability
        assert 'drill_down_key' in fig.layout.meta
    
    def test_create_performance_trend_with_predictions(self, viz_manager, sample_trend_data):
        """Test creation of performance trend visualization with predictions."""
        config = ChartConfiguration(
            chart_type=ChartType.LINE,
            title="Performance Trends with Predictions",
            data_source="trend_analysis_predictive"
        )
        
        fig = viz_manager.create_performance_trend_with_predictions(
            sample_trend_data, config=config
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 4  # Historical + predicted + confidence bands for each metric
        
        # Verify trend lines
        historical_traces = [trace for trace in fig.data if trace.name and 'Historical' in trace.name]
        predicted_traces = [trace for trace in fig.data if trace.name and 'Predicted' in trace.name]
        
        assert len(historical_traces) >= 1
        assert len(predicted_traces) >= 1
        
        # Verify confidence bands
        confidence_traces = [trace for trace in fig.data if trace.name and 'Confidence' in trace.name]
        assert len(confidence_traces) >= 1
        
        # Verify trend annotations
        assert len(fig.layout.annotations) > 0
        
        # Verify drill-down capability
        assert 'drill_down_key' in fig.layout.meta
    
    def test_create_comparative_analysis_chart(self, viz_manager, sample_comparison_data):
        """Test creation of comparative analysis chart."""
        config = ChartConfiguration(
            chart_type=ChartType.BAR,
            title="Comparative Performance Analysis",
            data_source="comparative_analysis"
        )
        
        fig = viz_manager.create_comparative_analysis_chart(
            sample_comparison_data, config=config
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        
        # Verify subplots for each metric
        metrics = sample_comparison_data['metrics']
        assert len(fig.data) == len(metrics)
        
        # Verify bar charts
        for trace in fig.data:
            assert trace.type == 'bar'
            assert len(trace.x) == len(sample_comparison_data['entities'])
        
        # Verify error bars
        for trace in fig.data:
            assert trace.error_y is not None
        
        # Verify drill-down capability
        assert 'drill_down_key' in fig.layout.meta
    
    def test_chart_export_functionality(self, viz_manager, sample_player_data):
        """Test chart export in multiple formats."""
        fig = viz_manager.create_player_performance_radar_with_drill_down(sample_player_data)
        
        # Test supported formats
        supported_formats = ['png', 'svg', 'pdf', 'html', 'json']
        
        for format_type in supported_formats:
            with patch('plotly.graph_objects.Figure.write_image') as mock_write_image, \
                 patch('plotly.graph_objects.Figure.write_html') as mock_write_html, \
                 patch('plotly.graph_objects.Figure.write_json') as mock_write_json:
                
                filename = f"test_chart_{format_type}"
                result = viz_manager.export_chart(fig, filename, format_type)
                
                expected_path = f"{filename}.{format_type}"
                assert result == expected_path
                
                # Verify appropriate method was called
                if format_type in ['png', 'svg', 'pdf']:
                    mock_write_image.assert_called_once()
                elif format_type == 'html':
                    mock_write_html.assert_called_once()
                elif format_type == 'json':
                    mock_write_json.assert_called_once()
    
    def test_unsupported_export_format(self, viz_manager, sample_player_data):
        """Test error handling for unsupported export formats."""
        fig = viz_manager.create_player_performance_radar_with_drill_down(sample_player_data)
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            viz_manager.export_chart(fig, "test", "unsupported_format")
    
    def test_drill_down_data_retrieval(self, viz_manager, sample_player_data):
        """Test drill-down data retrieval functionality."""
        fig = viz_manager.create_player_performance_radar_with_drill_down(sample_player_data)
        drill_down_key = fig.layout.meta['drill_down_key']
        
        # Test valid drill-down data retrieval
        breakdown_type = 'by_champion'
        drill_down_data = viz_manager.get_drill_down_data(drill_down_key, breakdown_type)
        
        assert 'breakdown_type' in drill_down_data
        assert drill_down_data['breakdown_type'] == breakdown_type
        assert 'data' in drill_down_data
        assert 'timestamp' in drill_down_data
    
    def test_invalid_drill_down_key(self, viz_manager):
        """Test error handling for invalid drill-down keys."""
        result = viz_manager.get_drill_down_data('invalid_key', 'by_champion')
        assert result == {}
    
    def test_invalid_breakdown_type(self, viz_manager, sample_player_data):
        """Test error handling for invalid breakdown types."""
        fig = viz_manager.create_player_performance_radar_with_drill_down(sample_player_data)
        drill_down_key = fig.layout.meta['drill_down_key']
        
        result = viz_manager.get_drill_down_data(drill_down_key, 'invalid_breakdown')
        assert result == {}
    
    def test_calculate_advanced_radar_values(self, viz_manager):
        """Test calculation of advanced radar values."""
        metrics = {
            'win_rate': 0.65,
            'avg_kda': 2.3,
            'avg_cs_per_min': 7.2,
            'avg_vision_score': 18.5,
            'avg_damage_per_min': 450,
            'avg_gold_per_min': 380,
            'kill_participation': 0.72,
            'first_blood_rate': 0.15,
            'objective_control_score': 0.68,
            'recent_form': 0.2
        }
        
        values = viz_manager._calculate_advanced_radar_values(metrics)
        
        assert len(values) == 10
        assert all(0 <= value <= 100 for value in values)
        assert values[0] == 65.0  # win_rate * 100
        assert values[1] == min(2.3 * 20, 100)  # kda scaled
    
    def test_calculate_trend_direction(self, viz_manager):
        """Test trend direction calculation."""
        # Test improving trend
        improving_values = [0.5, 0.52, 0.55, 0.58, 0.60]
        trend = viz_manager._calculate_trend_direction(improving_values)
        assert trend > 0
        
        # Test declining trend
        declining_values = [0.60, 0.58, 0.55, 0.52, 0.50]
        trend = viz_manager._calculate_trend_direction(declining_values)
        assert trend < 0
        
        # Test stable trend
        stable_values = [0.55, 0.55, 0.55, 0.55, 0.55]
        trend = viz_manager._calculate_trend_direction(stable_values)
        assert abs(trend) < 0.01  # Nearly zero
    
    def test_empty_data_handling(self, viz_manager):
        """Test handling of empty or invalid data."""
        # Test empty player data
        empty_player_data = {'player_name': 'Test', 'performance_by_role': {}}
        fig = viz_manager.create_player_performance_radar_with_drill_down(empty_player_data)
        assert "No performance data available" in fig.layout.annotations[0].text
        
        # Test empty champion data
        empty_champion_data = {'champions': [], 'metrics': []}
        fig = viz_manager.create_champion_performance_heatmap_with_significance(empty_champion_data)
        assert "No champion performance data available" in fig.layout.annotations[0].text
        
        # Test empty synergy data
        empty_synergy_data = {'players': []}
        fig = viz_manager.create_team_synergy_matrix_interactive(empty_synergy_data)
        assert "No synergy data available" in fig.layout.annotations[0].text


class TestInteractiveChartBuilder:
    """Test suite for interactive chart builder functionality."""
    
    @pytest.fixture
    def viz_manager(self):
        """Create visualization manager instance."""
        return VisualizationManager()
    
    @pytest.fixture
    def chart_builder(self, viz_manager):
        """Create interactive chart builder instance."""
        return InteractiveChartBuilder(viz_manager)
    
    @pytest.fixture
    def sample_chart_data(self):
        """Create sample data for chart building."""
        return {
            'title': 'Test Interactive Chart',
            'source': 'test_data',
            'available_players': ['Player1', 'Player2', 'Player3'],
            'available_champions': ['Garen', 'Darius', 'Fiora'],
            'available_metrics': ['win_rate', 'avg_kda', 'avg_cs_per_min'],
            'performance_by_role': {
                'top': {
                    'win_rate': 0.65,
                    'avg_kda': 2.3,
                    'avg_cs_per_min': 7.2,
                    'games_played': 50
                }
            }
        }
    
    def test_build_filterable_chart(self, chart_builder, sample_chart_data):
        """Test building filterable chart with components."""
        filters = ['player', 'champion', 'role', 'metric']
        
        fig, filter_components = chart_builder.build_filterable_chart(
            sample_chart_data, 'radar', filters
        )
        
        # Verify figure creation
        assert isinstance(fig, go.Figure)
        
        # Verify filter components creation
        assert len(filter_components) >= len(filters)
        
        # Verify filter types
        component_types = [type(comp).__name__ for comp in filter_components]
        assert 'Dropdown' in component_types  # For player and champion filters
        assert 'CheckboxGroup' in component_types  # For role and metric filters
    
    def test_add_drill_down_capability(self, chart_builder, sample_chart_data):
        """Test adding drill-down capability to charts."""
        fig = go.Figure()
        drill_down_data = {
            'available_breakdowns': ['by_role', 'by_champion'],
            'data_key': 'test_key'
        }
        
        enhanced_fig = chart_builder.add_drill_down_capability(fig, drill_down_data)
        
        # Verify drill-down configuration
        assert 'drill_down_config' in enhanced_fig.layout.meta
        config = enhanced_fig.layout.meta['drill_down_config']
        assert config['enabled'] is True
        assert 'by_role' in config['levels']
        assert 'by_champion' in config['levels']
        
        # Verify interaction modes
        assert enhanced_fig.layout.clickmode == 'event+select'
        assert enhanced_fig.layout.dragmode == 'select'
    
    def test_handle_drill_down_event_radar(self, chart_builder, sample_chart_data):
        """Test handling drill-down events for radar charts."""
        # Create a radar chart with drill-down capability
        fig = chart_builder.viz_manager.create_player_performance_radar_with_drill_down(
            sample_chart_data
        )
        drill_down_key = fig.layout.meta['drill_down_key']
        
        # Simulate click event
        click_data = {
            'points': [{'x': 'Win Rate', 'y': 65, 'fullData': {'name': 'Top (n=50)'}}],
            'drill_down_key': drill_down_key
        }
        
        result_fig, result_data = chart_builder.handle_drill_down_event('test_chart', click_data)
        
        # Verify drill-down result
        assert result_fig is not None
        assert isinstance(result_fig, go.Figure)
        assert result_data['success'] is True
        assert result_data['level'] == 'role_detail'
        
        # Verify drill-down history
        assert len(chart_builder.drill_down_history) > 0
        assert 'Top Role Details' in chart_builder.drill_down_history[-1]['title']
    
    def test_handle_drill_down_event_heatmap(self, chart_builder):
        """Test handling drill-down events for heatmap charts."""
        # Create sample champion data
        champion_data = {
            'champions': ['Garen', 'Darius'],
            'metrics': ['win_rate', 'avg_kda'],
            'performance_matrix': {
                'Garen_win_rate': 0.65,
                'Garen_avg_kda': 2.3,
                'Darius_win_rate': 0.58,
                'Darius_avg_kda': 2.8
            },
            'significance_matrix': {
                'Garen_win_rate': {'p_value': 0.02, 'effect_size': 0.5, 'sample_size': 50}
            },
            'time_series': {
                'Garen_win_rate': {
                    (datetime.now() - timedelta(days=i)).isoformat(): 0.6 + 0.05 * i
                    for i in range(10)
                }
            }
        }
        
        fig = chart_builder.viz_manager.create_champion_performance_heatmap_with_significance(
            champion_data
        )
        drill_down_key = fig.layout.meta['drill_down_key']
        
        # Simulate click event on heatmap
        click_data = {
            'points': [{'x': 0, 'y': 0}],  # First champion, first metric
            'drill_down_key': drill_down_key
        }
        
        result_fig, result_data = chart_builder.handle_drill_down_event('test_heatmap', click_data)
        
        # Verify drill-down result
        assert result_fig is not None
        assert isinstance(result_fig, go.Figure)
        assert result_data['success'] is True
        assert result_data['level'] == 'champion_detail'
    
    def test_handle_drill_down_event_synergy(self, chart_builder):
        """Test handling drill-down events for synergy matrix."""
        synergy_data = {
            'players': ['Player1', 'Player2'],
            'synergy_scores': {('Player1', 'Player2'): 0.75},
            'confidence_scores': {('Player1', 'Player2'): 0.85},
            'sample_sizes': {('Player1', 'Player2'): 25},
            'individual_performance': {
                'Player1': {'win_rate': 0.65, 'avg_kda': 2.3},
                'Player2': {'win_rate': 0.58, 'avg_kda': 2.8}
            },
            'detailed_synergy': {
                ('Player1', 'Player2'): {
                    'champion_combinations': {
                        'Garen+Graves': {'synergy_score': 0.75, 'win_rate': 0.68}
                    }
                }
            }
        }
        
        fig = chart_builder.viz_manager.create_team_synergy_matrix_interactive(synergy_data)
        drill_down_key = fig.layout.meta['drill_down_key']
        
        # Test drill-down on player pair
        click_data = {
            'points': [{'x': 1, 'y': 0}],  # Player1 + Player2
            'drill_down_key': drill_down_key
        }
        
        result_fig, result_data = chart_builder.handle_drill_down_event('test_synergy', click_data)
        
        assert result_fig is not None
        assert result_data['success'] is True
        assert result_data['level'] == 'synergy_detail'
    
    def test_create_drill_down_breadcrumb(self, chart_builder):
        """Test creation of drill-down breadcrumb navigation."""
        # Add some drill-down history
        chart_builder.drill_down_history = [
            {'title': 'Overview', 'description': 'Main chart view', 'level': 'overview'},
            {'title': 'Role Details', 'description': 'Role-specific breakdown', 'level': 'role_detail'},
            {'title': 'Champion Analysis', 'description': 'Champion-specific data', 'level': 'champion_detail'}
        ]
        
        breadcrumbs = chart_builder.create_drill_down_breadcrumb()
        
        assert len(breadcrumbs) == 3
        
        # Verify breadcrumb structure
        for i, breadcrumb in enumerate(breadcrumbs):
            assert 'level' in breadcrumb
            assert 'title' in breadcrumb
            assert 'description' in breadcrumb
            assert 'active' in breadcrumb
            assert breadcrumb['level'] == i
        
        # Verify last item is active
        assert breadcrumbs[-1]['active'] is True
        assert not any(bc['active'] for bc in breadcrumbs[:-1])
    
    def test_invalid_drill_down_event(self, chart_builder):
        """Test handling of invalid drill-down events."""
        # Test with invalid drill-down key
        click_data = {
            'points': [{'x': 0, 'y': 0}],
            'drill_down_key': 'invalid_key'
        }
        
        result_fig, result_data = chart_builder.handle_drill_down_event('test_chart', click_data)
        
        assert result_fig is None
        assert 'error' in result_data
        assert 'No drill-down data available' in result_data['error']
    
    def test_unsupported_chart_type_drill_down(self, chart_builder):
        """Test handling of unsupported chart types for drill-down."""
        # Create mock cached data with unsupported type
        drill_down_key = 'test_key'
        chart_builder.viz_manager.drill_down_cache[drill_down_key] = {
            'type': 'unsupported_chart_type',
            'data': {}
        }
        
        click_data = {
            'points': [{'x': 0, 'y': 0}],
            'drill_down_key': drill_down_key
        }
        
        result_fig, result_data = chart_builder.handle_drill_down_event('test_chart', click_data)
        
        assert result_fig is None
        assert 'error' in result_data
        assert 'Unsupported chart type' in result_data['error']
    
    def test_filter_components_creation(self, chart_builder, sample_chart_data):
        """Test creation of various filter components."""
        # Test all filter types
        filters = ['player', 'champion', 'role', 'date_range', 'metric']
        components = chart_builder._create_filter_components(filters, sample_chart_data)
        
        # Should have components for each filter type
        # player: 1, champion: 1, role: 1, date_range: 2, metric: 1
        assert len(components) == 6
        
        # Verify component types and configurations
        component_types = [type(comp).__name__ for comp in components]
        assert component_types.count('Dropdown') == 2  # player and champion
        assert component_types.count('CheckboxGroup') == 2  # role and metric
        assert component_types.count('Textbox') == 2  # date range (start and end)


class TestColorSchemeManager:
    """Test suite for color scheme manager."""
    
    @pytest.fixture
    def color_manager(self):
        """Create color scheme manager instance."""
        return ColorSchemeManager()
    
    def test_color_scheme_initialization(self, color_manager):
        """Test color scheme initialization."""
        assert 'lol_classic' in color_manager.schemes
        assert 'performance' in color_manager.schemes
        assert 'synergy' in color_manager.schemes
        
        # Verify LoL classic scheme
        lol_scheme = color_manager.schemes['lol_classic']
        assert 'primary' in lol_scheme
        assert 'roles' in lol_scheme
        assert len(lol_scheme['roles']) == 5  # 5 roles
    
    def test_get_color_palette_roles(self, color_manager):
        """Test getting color palette for roles."""
        colors = color_manager.get_color_palette('lol_classic', 5)
        
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith('#') or color.startswith('rgb') for color in colors)
    
    def test_get_color_palette_gradient(self, color_manager):
        """Test getting color palette with gradient."""
        colors = color_manager.get_color_palette('performance', 10)
        
        assert len(colors) == 10
        assert all(isinstance(color, str) for color in colors)
    
    def test_get_color_palette_fallback(self, color_manager):
        """Test fallback to default colors for unknown scheme."""
        colors = color_manager.get_color_palette('unknown_scheme', 3)
        
        assert len(colors) == 3
        assert all(isinstance(color, str) for color in colors)
    
    def test_interpolate_colors(self, color_manager):
        """Test color interpolation."""
        base_colors = ['#FF0000', '#00FF00', '#0000FF']  # Red, Green, Blue
        interpolated = color_manager._interpolate_colors(base_colors, 6)
        
        assert len(interpolated) == 6
        assert all(color.startswith('rgb(') for color in interpolated)
        
        # First color should be close to red
        assert 'rgb(255,0,0)' in interpolated[0] or interpolated[0].startswith('rgb(255')
    
    def test_interpolate_colors_fewer_than_base(self, color_manager):
        """Test color interpolation when requesting fewer colors than base."""
        base_colors = ['#FF0000', '#00FF00', '#0000FF']
        interpolated = color_manager._interpolate_colors(base_colors, 2)
        
        assert len(interpolated) == 2


if __name__ == '__main__':
    pytest.main([__file__])