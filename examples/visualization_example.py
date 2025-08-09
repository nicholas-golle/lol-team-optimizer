"""
Example demonstrating the VisualizationManager and InteractiveChartBuilder.

This example shows how to create various types of interactive charts
for League of Legends team optimization data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lol_team_optimizer.visualization_manager import (
    VisualizationManager, InteractiveChartBuilder, ChartConfiguration, ChartType
)
from datetime import datetime, timedelta
import random


def generate_sample_data():
    """Generate sample data for visualization examples."""
    
    # Sample player performance data
    player_data = {
        'performance_metrics': {
            'overall': {
                'win_rate': 0.68,
                'avg_kda': 2.8,
                'avg_cs_per_min': 7.5,
                'avg_vision_score': 28.0,
                'avg_damage_per_min': 520.0,
                'avg_gold_per_min': 420.0,
                'recent_form': 0.3
            },
            'top': {
                'win_rate': 0.72,
                'avg_kda': 3.1,
                'avg_cs_per_min': 8.2,
                'avg_vision_score': 22.0,
                'avg_damage_per_min': 580.0,
                'avg_gold_per_min': 460.0,
                'recent_form': 0.4
            },
            'jungle': {
                'win_rate': 0.65,
                'avg_kda': 2.6,
                'avg_cs_per_min': 6.8,
                'avg_vision_score': 35.0,
                'avg_damage_per_min': 480.0,
                'avg_gold_per_min': 380.0,
                'recent_form': 0.2
            }
        },
        'roles': ['overall', 'top', 'jungle']
    }
    
    # Sample synergy data
    synergy_data = {
        'players': ['Player1', 'Player2', 'Player3', 'Player4', 'Player5'],
        'synergy_scores': {
            ('Player1', 'Player2'): 0.85,
            ('Player1', 'Player3'): 0.72,
            ('Player1', 'Player4'): 0.68,
            ('Player1', 'Player5'): 0.75,
            ('Player2', 'Player3'): 0.80,
            ('Player2', 'Player4'): 0.65,
            ('Player2', 'Player5'): 0.78,
            ('Player3', 'Player4'): 0.70,
            ('Player3', 'Player5'): 0.73,
            ('Player4', 'Player5'): 0.82
        }
    }
    
    # Sample champion recommendations
    recommendations = [
        {
            'champion_name': 'Garen',
            'score': 0.92,
            'confidence': 0.88,
            'role': 'top'
        },
        {
            'champion_name': 'Darius',
            'score': 0.87,
            'confidence': 0.85,
            'role': 'top'
        },
        {
            'champion_name': 'Malphite',
            'score': 0.83,
            'confidence': 0.82,
            'role': 'top'
        },
        {
            'champion_name': 'Fiora',
            'score': 0.79,
            'confidence': 0.75,
            'role': 'top'
        },
        {
            'champion_name': 'Camille',
            'score': 0.76,
            'confidence': 0.78,
            'role': 'top'
        }
    ]
    
    # Sample trend data
    base_date = datetime.now() - timedelta(days=30)
    trend_data = {
        'time_series': {
            'win_rate': {},
            'avg_kda': {},
            'avg_cs_per_min': {}
        },
        'metrics': ['win_rate', 'avg_kda', 'avg_cs_per_min']
    }
    
    # Generate time series data
    for i in range(30):
        date = base_date + timedelta(days=i)
        date_str = date.isoformat()
        
        # Simulate improving performance over time with some noise
        progress = i / 30.0
        noise = random.uniform(-0.05, 0.05)
        
        trend_data['time_series']['win_rate'][date_str] = 0.55 + (0.15 * progress) + noise
        trend_data['time_series']['avg_kda'][date_str] = 2.0 + (0.8 * progress) + (noise * 2)
        trend_data['time_series']['avg_cs_per_min'][date_str] = 6.5 + (1.5 * progress) + (noise * 3)
    
    # Sample composition data
    compositions = [
        {
            'name': 'Aggressive Comp',
            'win_rate': 0.78,
            'synergy_score': 0.85,
            'confidence': 0.82
        },
        {
            'name': 'Balanced Comp',
            'win_rate': 0.72,
            'synergy_score': 0.80,
            'confidence': 0.88
        },
        {
            'name': 'Defensive Comp',
            'win_rate': 0.69,
            'synergy_score': 0.75,
            'confidence': 0.85
        },
        {
            'name': 'Early Game Comp',
            'win_rate': 0.74,
            'synergy_score': 0.78,
            'confidence': 0.80
        }
    ]
    
    return player_data, synergy_data, recommendations, trend_data, compositions


def demonstrate_visualization_manager():
    """Demonstrate the VisualizationManager capabilities."""
    print("=== VisualizationManager Demo ===")
    
    # Initialize visualization manager
    viz_manager = VisualizationManager()
    
    # Generate sample data
    player_data, synergy_data, recommendations, trend_data, compositions = generate_sample_data()
    
    print("\n1. Creating Player Performance Radar Chart...")
    radar_config = ChartConfiguration(
        chart_type=ChartType.RADAR,
        title="Player Performance Analysis",
        data_source="player_metrics",
        height=600
    )
    radar_fig = viz_manager.create_player_performance_radar(player_data, radar_config)
    print(f"   ✓ Created radar chart with {len(radar_fig.data)} traces")
    
    print("\n2. Creating Team Synergy Heatmap...")
    heatmap_config = ChartConfiguration(
        chart_type=ChartType.HEATMAP,
        title="Team Synergy Matrix",
        data_source="synergy_data",
        height=500
    )
    heatmap_fig = viz_manager.create_team_synergy_heatmap(synergy_data, heatmap_config)
    print(f"   ✓ Created heatmap for {len(synergy_data['players'])} players")
    
    print("\n3. Creating Champion Recommendation Chart...")
    bar_config = ChartConfiguration(
        chart_type=ChartType.BAR,
        title="Top Champion Recommendations",
        data_source="recommendations",
        height=400
    )
    bar_fig = viz_manager.create_champion_recommendation_chart(recommendations, bar_config)
    print(f"   ✓ Created recommendation chart for {len(recommendations)} champions")
    
    print("\n4. Creating Performance Trend Line...")
    line_config = ChartConfiguration(
        chart_type=ChartType.LINE,
        title="Performance Trends Over Time",
        data_source="trend_data",
        height=500
    )
    line_fig = viz_manager.create_performance_trend_line(trend_data, line_config)
    print(f"   ✓ Created trend chart with {len(trend_data['metrics'])} metrics")
    
    print("\n5. Creating Composition Comparison...")
    comp_config = ChartConfiguration(
        chart_type=ChartType.BAR,
        title="Team Composition Comparison",
        data_source="compositions",
        height=450
    )
    comp_fig = viz_manager.create_composition_comparison(compositions, comp_config)
    print(f"   ✓ Created comparison chart for {len(compositions)} compositions")
    
    return {
        'radar': radar_fig,
        'heatmap': heatmap_fig,
        'recommendations': bar_fig,
        'trends': line_fig,
        'compositions': comp_fig
    }


def demonstrate_interactive_chart_builder():
    """Demonstrate the InteractiveChartBuilder capabilities."""
    print("\n=== InteractiveChartBuilder Demo ===")
    
    # Initialize components
    viz_manager = VisualizationManager()
    chart_builder = InteractiveChartBuilder(viz_manager)
    
    # Generate sample data
    player_data, synergy_data, recommendations, trend_data, compositions = generate_sample_data()
    
    # Prepare interactive data
    interactive_data = {
        'title': 'Interactive Player Analysis',
        'source': 'demo_data',
        'available_players': ['Player1', 'Player2', 'Player3'],
        'available_champions': ['Garen', 'Darius', 'Malphite', 'Fiora', 'Camille'],
        'available_metrics': ['win_rate', 'avg_kda', 'avg_cs_per_min'],
        'performance_metrics': player_data['performance_metrics'],
        'roles': player_data['roles'],
        'recommendations': recommendations,
        'time_series': trend_data['time_series']
    }
    
    print("\n1. Building Filterable Radar Chart...")
    try:
        radar_fig, radar_filters = chart_builder.build_filterable_chart(
            interactive_data, ChartType.RADAR.value, ['player', 'role']
        )
        print(f"   ✓ Created filterable radar chart with {len(radar_filters)} filter components")
    except Exception as e:
        print(f"   ✗ Error creating radar chart: {e}")
    
    print("\n2. Building Filterable Recommendation Chart...")
    try:
        rec_fig, rec_filters = chart_builder.build_filterable_chart(
            interactive_data, ChartType.BAR.value, ['champion', 'role']
        )
        print(f"   ✓ Created filterable recommendation chart with {len(rec_filters)} filter components")
    except Exception as e:
        print(f"   ✗ Error creating recommendation chart: {e}")
    
    print("\n3. Testing Filter Application...")
    try:
        # Test player filter
        filter_values = {'player': ['Player1']}
        filtered_data = chart_builder._apply_filters(interactive_data, filter_values)
        print(f"   ✓ Applied player filter, filtered to {len(filtered_data.get('performance_metrics', {}))} players")
        
        # Test champion filter
        filter_values = {'champion': ['Garen', 'Darius']}
        filtered_data = chart_builder._apply_filters(interactive_data, filter_values)
        print(f"   ✓ Applied champion filter, filtered to {len(filtered_data.get('recommendations', []))} recommendations")
        
    except Exception as e:
        print(f"   ✗ Error applying filters: {e}")
    
    print("\n4. Testing Chart Updates with Filters...")
    try:
        # Update chart with filters
        data_with_type = interactive_data.copy()
        data_with_type['chart_type'] = ChartType.BAR.value
        
        filter_values = {'champion': ['Garen', 'Darius', 'Malphite']}
        updated_fig = chart_builder.update_chart_with_filters(data_with_type, filter_values)
        print(f"   ✓ Updated chart with filters successfully")
        
    except Exception as e:
        print(f"   ✗ Error updating chart: {e}")


def demonstrate_color_schemes():
    """Demonstrate color scheme functionality."""
    print("\n=== Color Scheme Demo ===")
    
    viz_manager = VisualizationManager()
    color_manager = viz_manager.color_manager
    
    print("\n1. Available Color Schemes:")
    for scheme_name in color_manager.schemes.keys():
        print(f"   - {scheme_name}")
    
    print("\n2. Color Palette Examples:")
    
    # LoL Classic colors
    lol_colors = color_manager.get_color_palette('lol_classic', 5)
    print(f"   LoL Classic (5 colors): {lol_colors[:2]}... ({len(lol_colors)} total)")
    
    # Performance colors
    perf_colors = color_manager.get_color_palette('performance', 4)
    print(f"   Performance (4 colors): {perf_colors[:2]}... ({len(perf_colors)} total)")
    
    # Synergy colors
    synergy_colors = color_manager.get_color_palette('synergy', 3)
    print(f"   Synergy (3 colors): {synergy_colors}")
    
    print("\n3. Color Interpolation Test:")
    base_colors = ['#FF0000', '#00FF00', '#0000FF']
    interpolated = color_manager._interpolate_colors(base_colors, 8)
    print(f"   Interpolated 8 colors from {base_colors}")
    print(f"   Result: {interpolated[:3]}... ({len(interpolated)} total)")


def main():
    """Run all visualization demonstrations."""
    print("League of Legends Team Optimizer - Visualization Demo")
    print("=" * 60)
    
    try:
        # Demonstrate core visualization manager
        charts = demonstrate_visualization_manager()
        
        # Demonstrate interactive chart builder
        demonstrate_interactive_chart_builder()
        
        # Demonstrate color schemes
        demonstrate_color_schemes()
        
        print("\n" + "=" * 60)
        print("✓ All visualization demonstrations completed successfully!")
        print("\nGenerated Charts:")
        for chart_name, fig in charts.items():
            print(f"  - {chart_name.title()}: {len(fig.data)} traces, {fig.layout.title.text}")
        
        print(f"\nTo view the charts interactively, you can:")
        print("1. Save them using fig.write_html('chart_name.html')")
        print("2. Display them using fig.show() (requires browser)")
        print("3. Integrate them into a Gradio interface")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()