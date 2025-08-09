#!/usr/bin/env python3
"""
Demo script for advanced interactive visualizations with drill-down functionality.

This script demonstrates the enhanced visualization capabilities including:
- Player performance radar charts with role-specific breakdowns
- Champion performance heatmaps with statistical significance indicators
- Team synergy matrices with interactive exploration
- Performance trend visualizations with predictive analytics
- Comparative analysis charts for multiple players or time periods
- Chart export functionality in multiple formats
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any

from lol_team_optimizer.visualization_manager import (
    VisualizationManager, InteractiveChartBuilder, ChartConfiguration, ChartType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_player_data() -> Dict[str, Any]:
    """Create comprehensive sample player performance data."""
    return {
        'player_name': 'ProPlayer123',
        'performance_by_role': {
            'top': {
                'games_played': 75,
                'win_rate': 0.68,
                'avg_kda': 2.4,
                'avg_cs_per_min': 7.8,
                'avg_vision_score': 19.2,
                'avg_damage_per_min': 520,
                'avg_gold_per_min': 420,
                'kill_participation': 0.74,
                'first_blood_rate': 0.18,
                'objective_control_score': 0.71,
                'recent_form': 0.3,
                'confidence_intervals': {
                    'win_rate': 0.04,
                    'avg_kda': 0.08,
                    'avg_cs_per_min': 0.2
                }
            },
            'jungle': {
                'games_played': 45,
                'win_rate': 0.62,
                'avg_kda': 3.1,
                'avg_cs_per_min': 6.2,
                'avg_vision_score': 24.5,
                'avg_damage_per_min': 480,
                'avg_gold_per_min': 390,
                'kill_participation': 0.82,
                'first_blood_rate': 0.26,
                'objective_control_score': 0.78,
                'recent_form': -0.05,
                'confidence_intervals': {
                    'win_rate': 0.06,
                    'avg_kda': 0.12,
                    'avg_cs_per_min': 0.3
                }
            },
            'middle': {
                'games_played': 30,
                'win_rate': 0.73,
                'avg_kda': 2.8,
                'avg_cs_per_min': 8.1,
                'avg_vision_score': 16.8,
                'avg_damage_per_min': 580,
                'avg_gold_per_min': 450,
                'kill_participation': 0.69,
                'first_blood_rate': 0.21,
                'objective_control_score': 0.65,
                'recent_form': 0.4,
                'confidence_intervals': {
                    'win_rate': 0.07,
                    'avg_kda': 0.15,
                    'avg_cs_per_min': 0.4
                }
            }
        }
    }


def create_sample_champion_data() -> Dict[str, Any]:
    """Create sample champion performance data with statistical significance."""
    champions = ['Garen', 'Darius', 'Fiora', 'Camille', 'Aatrox', 'Sett']
    metrics = ['win_rate', 'avg_kda', 'pick_rate', 'ban_rate']
    
    performance_matrix = {}
    significance_matrix = {}
    time_series = {}
    
    for champion in champions:
        for metric in metrics:
            key = f"{champion}_{metric}"
            # Create realistic performance values
            if metric == 'win_rate':
                value = np.random.uniform(0.45, 0.65)
            elif metric == 'avg_kda':
                value = np.random.uniform(1.8, 3.2)
            elif metric == 'pick_rate':
                value = np.random.uniform(0.05, 0.25)
            else:  # ban_rate
                value = np.random.uniform(0.02, 0.15)
            
            performance_matrix[key] = value
            
            # Statistical significance data
            significance_matrix[key] = {
                'p_value': np.random.uniform(0.001, 0.08),
                'effect_size': np.random.uniform(0.2, 0.9),
                'sample_size': np.random.randint(30, 150)
            }
            
            # Time series data for drill-down
            base_date = datetime.now() - timedelta(days=30)
            time_series[key] = {
                (base_date + timedelta(days=i)).isoformat(): 
                value + np.random.normal(0, value * 0.1) 
                for i in range(30)
            }
    
    return {
        'champions': champions,
        'metrics': metrics,
        'performance_matrix': performance_matrix,
        'significance_matrix': significance_matrix,
        'time_series': time_series
    }


def create_sample_synergy_data() -> Dict[str, Any]:
    """Create sample team synergy data."""
    players = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon']
    
    synergy_scores = {}
    confidence_scores = {}
    sample_sizes = {}
    individual_performance = {}
    detailed_synergy = {}
    
    # Generate synergy matrix
    for i, player1 in enumerate(players):
        for j, player2 in enumerate(players):
            if i < j:  # Only upper triangle
                key = tuple(sorted([player1, player2]))
                synergy_scores[key] = np.random.uniform(0.3, 0.85)
                confidence_scores[key] = np.random.uniform(0.7, 0.95)
                sample_sizes[key] = np.random.randint(15, 60)
    
    # Individual performance data
    for player in players:
        individual_performance[player] = {
            'win_rate': np.random.uniform(0.45, 0.75),
            'avg_kda': np.random.uniform(1.8, 3.5),
            'avg_cs_per_min': np.random.uniform(6.0, 8.5),
            'avg_vision_score': np.random.uniform(18, 28),
            'avg_damage_per_min': np.random.uniform(400, 600)
        }
    
    # Detailed synergy for specific pairs
    detailed_synergy[tuple(sorted([players[0], players[1]]))] = {
        'champion_combinations': {
            'Garen+Graves': {'synergy_score': 0.78, 'win_rate': 0.72},
            'Darius+Elise': {'synergy_score': 0.85, 'win_rate': 0.76},
            'Fiora+Kindred': {'synergy_score': 0.68, 'win_rate': 0.63},
            'Camille+Nidalee': {'synergy_score': 0.71, 'win_rate': 0.65}
        }
    }
    
    return {
        'players': players,
        'synergy_scores': synergy_scores,
        'confidence_scores': confidence_scores,
        'sample_sizes': sample_sizes,
        'individual_performance': individual_performance,
        'detailed_synergy': detailed_synergy
    }


def create_sample_trend_data() -> Dict[str, Any]:
    """Create sample trend data with predictions."""
    base_date = datetime.now() - timedelta(days=90)
    
    # Historical data
    dates = [(base_date + timedelta(days=i)).isoformat() for i in range(90)]
    
    # Generate realistic trends
    win_rate_trend = []
    kda_trend = []
    cs_trend = []
    
    for i in range(90):
        # Win rate with seasonal variation
        win_rate = 0.55 + 0.08 * np.sin(i * 0.07) + np.random.normal(0, 0.02)
        win_rate_trend.append(max(0.3, min(0.8, win_rate)))
        
        # KDA with improvement over time
        kda = 2.2 + 0.01 * i + 0.2 * np.sin(i * 0.05) + np.random.normal(0, 0.05)
        kda_trend.append(max(1.0, min(4.0, kda)))
        
        # CS per minute with learning curve
        cs = 6.5 + 0.005 * i + 0.3 * np.sin(i * 0.06) + np.random.normal(0, 0.1)
        cs_trend.append(max(5.0, min(9.0, cs)))
    
    # Prediction data
    pred_dates = [(base_date + timedelta(days=90 + i)).isoformat() for i in range(30)]
    
    # Generate predictions based on recent trends
    recent_win_rate = np.mean(win_rate_trend[-10:])
    recent_kda = np.mean(kda_trend[-10:])
    recent_cs = np.mean(cs_trend[-10:])
    
    win_rate_pred = [recent_win_rate + 0.002 * i + np.random.normal(0, 0.01) for i in range(30)]
    kda_pred = [recent_kda + 0.01 * i + np.random.normal(0, 0.03) for i in range(30)]
    cs_pred = [recent_cs + 0.005 * i + np.random.normal(0, 0.05) for i in range(30)]
    
    return {
        'time_series': {
            'win_rate': dict(zip(dates, win_rate_trend)),
            'avg_kda': dict(zip(dates, kda_trend)),
            'avg_cs_per_min': dict(zip(dates, cs_trend))
        },
        'predictions': {
            'win_rate': dict(zip(pred_dates, win_rate_pred)),
            'avg_kda': dict(zip(pred_dates, kda_pred)),
            'avg_cs_per_min': dict(zip(pred_dates, cs_pred))
        },
        'confidence_bands': {
            'win_rate': {
                date: {'upper': pred + 0.04, 'lower': pred - 0.04}
                for date, pred in zip(pred_dates, win_rate_pred)
            },
            'avg_kda': {
                date: {'upper': pred + 0.15, 'lower': pred - 0.15}
                for date, pred in zip(pred_dates, kda_pred)
            },
            'avg_cs_per_min': {
                date: {'upper': pred + 0.3, 'lower': pred - 0.3}
                for date, pred in zip(pred_dates, cs_pred)
            }
        },
        'metrics': ['win_rate', 'avg_kda', 'avg_cs_per_min']
    }


def create_sample_comparison_data() -> Dict[str, Any]:
    """Create sample comparative analysis data."""
    players = ['PlayerA', 'PlayerB', 'PlayerC', 'PlayerD']
    metrics = ['win_rate', 'avg_kda', 'avg_cs_per_min', 'avg_vision_score']
    
    performance_data = {}
    statistical_tests = {}
    detailed_stats = {}
    
    for player in players:
        for metric in metrics:
            key = f"{player}_{metric}"
            
            # Generate realistic performance data
            if metric == 'win_rate':
                mean_val = np.random.uniform(0.45, 0.75)
            elif metric == 'avg_kda':
                mean_val = np.random.uniform(1.8, 3.2)
            elif metric == 'avg_cs_per_min':
                mean_val = np.random.uniform(6.0, 8.5)
            else:  # avg_vision_score
                mean_val = np.random.uniform(18, 28)
            
            performance_data[key] = {
                'mean': mean_val,
                'std_error': mean_val * np.random.uniform(0.05, 0.15),
                'sample_size': np.random.randint(40, 120)
            }
            
            # Statistical test results
            statistical_tests[f"{metric}_{player}"] = {
                'p_value': np.random.uniform(0.001, 0.08),
                'effect_size': np.random.uniform(0.2, 0.8)
            }
        
        # Detailed statistics for drill-down
        detailed_stats[player] = {
            'mean': np.random.uniform(0.5, 0.7),
            'median': np.random.uniform(0.45, 0.65),
            'std_dev': np.random.uniform(0.08, 0.18),
            'min': np.random.uniform(0.2, 0.4),
            'max': np.random.uniform(0.75, 0.95),
            'percentile_25': np.random.uniform(0.4, 0.5),
            'percentile_75': np.random.uniform(0.6, 0.8)
        }
    
    return {
        'comparison_type': 'players',
        'entities': players,
        'metrics': metrics,
        'performance_data': performance_data,
        'statistical_tests': statistical_tests,
        'detailed_stats': detailed_stats
    }


def demonstrate_advanced_visualizations():
    """Demonstrate all advanced visualization features."""
    logger.info("Starting Advanced Interactive Visualizations Demo")
    
    # Initialize visualization manager
    viz_manager = VisualizationManager()
    chart_builder = InteractiveChartBuilder(viz_manager)
    
    logger.info("Creating sample data...")
    
    # Create sample data
    player_data = create_sample_player_data()
    champion_data = create_sample_champion_data()
    synergy_data = create_sample_synergy_data()
    trend_data = create_sample_trend_data()
    comparison_data = create_sample_comparison_data()
    
    logger.info("Generating advanced visualizations...")
    
    # 1. Player Performance Radar with Drill-down
    logger.info("1. Creating player performance radar chart with drill-down...")
    radar_config = ChartConfiguration(
        chart_type=ChartType.RADAR,
        title="Advanced Player Performance Analysis",
        data_source="player_performance_detailed"
    )
    
    radar_fig = viz_manager.create_player_performance_radar_with_drill_down(
        player_data, role_breakdown=True, config=radar_config
    )
    
    # Export radar chart
    try:
        radar_export_path = viz_manager.export_chart(radar_fig, "player_radar_advanced", "html")
        logger.info(f"Player radar chart exported to: {radar_export_path}")
    except Exception as e:
        logger.warning(f"Could not export radar chart: {e}")
    
    # 2. Champion Performance Heatmap with Statistical Significance
    logger.info("2. Creating champion performance heatmap with significance indicators...")
    heatmap_config = ChartConfiguration(
        chart_type=ChartType.HEATMAP,
        title="Champion Performance Matrix with Statistical Significance",
        data_source="champion_performance_stats"
    )
    
    heatmap_fig = viz_manager.create_champion_performance_heatmap_with_significance(
        champion_data, config=heatmap_config
    )
    
    # Export heatmap
    try:
        heatmap_export_path = viz_manager.export_chart(heatmap_fig, "champion_heatmap_advanced", "html")
        logger.info(f"Champion heatmap exported to: {heatmap_export_path}")
    except Exception as e:
        logger.warning(f"Could not export heatmap: {e}")
    
    # 3. Team Synergy Matrix Interactive
    logger.info("3. Creating interactive team synergy matrix...")
    synergy_config = ChartConfiguration(
        chart_type=ChartType.HEATMAP,
        title="Interactive Team Synergy Analysis Matrix",
        data_source="synergy_analysis"
    )
    
    synergy_fig = viz_manager.create_team_synergy_matrix_interactive(
        synergy_data, config=synergy_config
    )
    
    # Export synergy matrix
    try:
        synergy_export_path = viz_manager.export_chart(synergy_fig, "synergy_matrix_advanced", "html")
        logger.info(f"Synergy matrix exported to: {synergy_export_path}")
    except Exception as e:
        logger.warning(f"Could not export synergy matrix: {e}")
    
    # 4. Performance Trend with Predictions
    logger.info("4. Creating performance trend visualization with predictive analytics...")
    trend_config = ChartConfiguration(
        chart_type=ChartType.LINE,
        title="Performance Trends with Predictive Analytics",
        data_source="trend_analysis_predictive"
    )
    
    trend_fig = viz_manager.create_performance_trend_with_predictions(
        trend_data, config=trend_config
    )
    
    # Export trend chart
    try:
        trend_export_path = viz_manager.export_chart(trend_fig, "trend_analysis_advanced", "html")
        logger.info(f"Trend analysis exported to: {trend_export_path}")
    except Exception as e:
        logger.warning(f"Could not export trend chart: {e}")
    
    # 5. Comparative Analysis Chart
    logger.info("5. Creating comparative analysis chart...")
    comparison_config = ChartConfiguration(
        chart_type=ChartType.BAR,
        title="Multi-Player Comparative Performance Analysis",
        data_source="comparative_analysis"
    )
    
    comparison_fig = viz_manager.create_comparative_analysis_chart(
        comparison_data, config=comparison_config
    )
    
    # Export comparison chart
    try:
        comparison_export_path = viz_manager.export_chart(comparison_fig, "comparison_analysis_advanced", "html")
        logger.info(f"Comparison analysis exported to: {comparison_export_path}")
    except Exception as e:
        logger.warning(f"Could not export comparison chart: {e}")
    
    # 6. Demonstrate Drill-down Functionality
    logger.info("6. Demonstrating drill-down functionality...")
    
    # Simulate drill-down on radar chart
    radar_drill_key = radar_fig.layout.meta['drill_down_key']
    drill_down_data = viz_manager.get_drill_down_data(radar_drill_key, 'by_champion')
    logger.info(f"Drill-down data retrieved for radar chart: {len(drill_down_data)} items")
    
    # Simulate click event for drill-down
    click_data = {
        'points': [{'x': 'Win Rate', 'y': 68, 'fullData': {'name': 'Top (n=75)'}}],
        'drill_down_key': radar_drill_key
    }
    
    drill_fig, drill_result = chart_builder.handle_drill_down_event('radar_chart', click_data)
    if drill_fig:
        logger.info(f"Drill-down successful: {drill_result}")
        try:
            drill_export_path = viz_manager.export_chart(drill_fig, "drill_down_example", "html")
            logger.info(f"Drill-down chart exported to: {drill_export_path}")
        except Exception as e:
            logger.warning(f"Could not export drill-down chart: {e}")
    
    # 7. Demonstrate Chart Export in Multiple Formats
    logger.info("7. Demonstrating multi-format export...")
    
    export_formats = ['html', 'json']  # PNG/SVG/PDF require additional dependencies
    for fmt in export_formats:
        try:
            export_path = viz_manager.export_chart(radar_fig, f"multi_format_export", fmt)
            logger.info(f"Chart exported in {fmt.upper()} format to: {export_path}")
        except Exception as e:
            logger.warning(f"Could not export in {fmt} format: {e}")
    
    # 8. Display Summary Statistics
    logger.info("8. Summary of generated visualizations:")
    logger.info(f"   - Player Performance Radar: {len(radar_fig.data)} traces")
    logger.info(f"   - Champion Performance Heatmap: {len(heatmap_fig.data)} traces")
    logger.info(f"   - Team Synergy Matrix: {len(synergy_fig.data)} traces")
    logger.info(f"   - Performance Trends: {len(trend_fig.data)} traces")
    logger.info(f"   - Comparative Analysis: {len(comparison_fig.data)} traces")
    
    # 9. Cache Statistics
    logger.info(f"   - Drill-down cache entries: {len(viz_manager.drill_down_cache)}")
    logger.info(f"   - Chart cache entries: {len(viz_manager.chart_cache)}")
    
    logger.info("Advanced Interactive Visualizations Demo completed successfully!")
    
    return {
        'radar_chart': radar_fig,
        'heatmap_chart': heatmap_fig,
        'synergy_chart': synergy_fig,
        'trend_chart': trend_fig,
        'comparison_chart': comparison_fig,
        'drill_down_chart': drill_fig if drill_fig else None
    }


if __name__ == "__main__":
    try:
        charts = demonstrate_advanced_visualizations()
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"Generated {len([c for c in charts.values() if c is not None])} interactive charts")
        print("Check the exported HTML files to view the interactive visualizations")
        print("="*60)
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise