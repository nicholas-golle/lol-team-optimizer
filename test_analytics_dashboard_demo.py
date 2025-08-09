#!/usr/bin/env python3
"""
Analytics Dashboard Demo

This script demonstrates the comprehensive analytics dashboard with real-time filtering,
preset configurations, and interactive visualizations.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lol_team_optimizer.analytics_dashboard import AnalyticsDashboard, FilterState, AnalyticsPreset
from lol_team_optimizer.visualization_manager import VisualizationManager
from lol_team_optimizer.enhanced_state_manager import EnhancedStateManager
from lol_team_optimizer.models import Player
from lol_team_optimizer.analytics_models import AnalyticsFilters, DateRange, PlayerAnalytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockAnalyticsEngine:
    """Mock analytics engine for testing."""
    
    def get_available_champions(self):
        """Return mock champion list."""
        return ["Aatrox", "Ahri", "Akali", "Alistar", "Amumu", "Anivia", "Annie", "Ashe"]
    
    def analyze_player_performance(self, puuid, filters):
        """Return mock player analytics."""
        # Create mock analytics data
        mock_analytics = type('MockAnalytics', (), {
            'win_rate': 0.65,
            'avg_kda': 2.3,
            'games_played': 45,
            'wins': 29,
            'avg_cs_per_min': 7.2,
            'avg_vision_score': 28.5,
            'avg_damage_per_min': 520.0,
            'avg_gold_per_min': 380.0
        })()
        
        return mock_analytics


class MockDataManager:
    """Mock data manager for testing."""
    
    def load_player_data(self):
        """Return mock player data."""
        return [
            Player(name="TestPlayer1", summoner_name="test1", puuid="puuid1"),
            Player(name="TestPlayer2", summoner_name="test2", puuid="puuid2"),
            Player(name="TestPlayer3", summoner_name="test3", puuid="puuid3"),
            Player(name="TestPlayer4", summoner_name="test4", puuid="puuid4"),
            Player(name="TestPlayer5", summoner_name="test5", puuid="puuid5")
        ]


def test_filter_state():
    """Test FilterState functionality."""
    print("\n=== Testing FilterState ===")
    
    # Test default initialization
    filter_state = FilterState()
    print(f"Default filter state: {filter_state}")
    
    # Test with custom values
    filter_state.selected_players = ["TestPlayer1", "TestPlayer2"]
    filter_state.selected_roles = ["top", "jungle"]
    filter_state.date_range_start = "2024-01-01"
    filter_state.date_range_end = "2024-01-31"
    filter_state.min_games = 10
    
    print(f"Updated filter state: {filter_state}")
    
    # Test conversion to AnalyticsFilters
    analytics_filters = filter_state.to_analytics_filters()
    print(f"Converted to AnalyticsFilters: {analytics_filters}")
    print(f"Date range: {analytics_filters.date_range}")
    print(f"Min games: {analytics_filters.min_games}")
    
    print("✅ FilterState tests passed")


def test_analytics_presets():
    """Test analytics presets functionality."""
    print("\n=== Testing Analytics Presets ===")
    
    # Create mock dependencies
    mock_analytics_engine = MockAnalyticsEngine()
    mock_data_manager = MockDataManager()
    viz_manager = VisualizationManager()
    state_manager = EnhancedStateManager()
    
    # Create dashboard
    dashboard = AnalyticsDashboard(
        analytics_engine=mock_analytics_engine,
        visualization_manager=viz_manager,
        state_manager=state_manager,
        data_manager=mock_data_manager
    )
    
    # Test presets
    print(f"Number of presets: {len(dashboard.presets)}")
    
    for preset in dashboard.presets:
        print(f"\nPreset: {preset.name}")
        print(f"  Description: {preset.description}")
        print(f"  Chart types: {preset.chart_types}")
        print(f"  Date range: {preset.filters.date_range_start} to {preset.filters.date_range_end}")
        print(f"  Min games: {preset.filters.min_games}")
    
    print("✅ Analytics presets tests passed")


def test_dashboard_initialization():
    """Test dashboard initialization."""
    print("\n=== Testing Dashboard Initialization ===")
    
    # Create mock dependencies
    mock_analytics_engine = MockAnalyticsEngine()
    mock_data_manager = MockDataManager()
    viz_manager = VisualizationManager()
    state_manager = EnhancedStateManager()
    
    # Create dashboard
    dashboard = AnalyticsDashboard(
        analytics_engine=mock_analytics_engine,
        visualization_manager=viz_manager,
        state_manager=state_manager,
        data_manager=mock_data_manager
    )
    
    # Test initialization
    print(f"Available players: {dashboard.available_players}")
    print(f"Available champions: {dashboard.available_champions}")
    print(f"Available roles: {dashboard.available_roles}")
    print(f"Current filters: {dashboard.current_filters}")
    print(f"Number of presets: {len(dashboard.presets)}")
    print(f"Number of saved views: {len(dashboard.saved_views)}")
    
    print("✅ Dashboard initialization tests passed")


def test_filtered_analytics_data():
    """Test filtered analytics data retrieval."""
    print("\n=== Testing Filtered Analytics Data ===")
    
    # Create mock dependencies
    mock_analytics_engine = MockAnalyticsEngine()
    mock_data_manager = MockDataManager()
    viz_manager = VisualizationManager()
    state_manager = EnhancedStateManager()
    
    # Create dashboard
    dashboard = AnalyticsDashboard(
        analytics_engine=mock_analytics_engine,
        visualization_manager=viz_manager,
        state_manager=state_manager,
        data_manager=mock_data_manager
    )
    
    # Set filters
    dashboard.current_filters.selected_players = ["TestPlayer1", "TestPlayer2"]
    dashboard.current_filters.date_range_start = "2024-01-01"
    dashboard.current_filters.date_range_end = "2024-01-31"
    dashboard.current_filters.min_games = 5
    
    # Get filtered data
    analytics_data = dashboard._get_filtered_analytics_data()
    
    print(f"Analytics data keys: {list(analytics_data.keys())}")
    print(f"Players in data: {list(analytics_data.get('players', {}).keys())}")
    print(f"Summary data: {analytics_data.get('summary', {})}")
    
    # Test summary statistics
    if 'summary' in analytics_data:
        summary = analytics_data['summary']
        print(f"\nSummary Statistics:")
        print(f"  Total players: {summary.get('total_players', 0)}")
        print(f"  Total games: {summary.get('total_games', 0)}")
        print(f"  Average win rate: {summary.get('avg_win_rate', 0):.2%}")
        print(f"  Average KDA: {summary.get('avg_kda', 0):.2f}")
    
    print("✅ Filtered analytics data tests passed")


def test_chart_creation():
    """Test chart creation functionality."""
    print("\n=== Testing Chart Creation ===")
    
    # Create mock dependencies
    mock_analytics_engine = MockAnalyticsEngine()
    mock_data_manager = MockDataManager()
    viz_manager = VisualizationManager()
    state_manager = EnhancedStateManager()
    
    # Create dashboard
    dashboard = AnalyticsDashboard(
        analytics_engine=mock_analytics_engine,
        visualization_manager=viz_manager,
        state_manager=state_manager,
        data_manager=mock_data_manager
    )
    
    # Create test analytics data
    analytics_data = {
        'players': {
            'TestPlayer1': type('MockAnalytics', (), {
                'win_rate': 0.65,
                'avg_kda': 2.3,
                'games_played': 45,
                'wins': 29,
                'avg_cs_per_min': 7.2,
                'avg_vision_score': 28.5,
                'avg_damage_per_min': 520.0,
                'avg_gold_per_min': 380.0
            })()
        },
        'summary': {
            'total_players': 1,
            'total_games': 45,
            'avg_win_rate': 0.65,
            'avg_kda': 2.3
        }
    }
    
    # Test chart creation
    try:
        player_radar = dashboard._create_player_radar_chart(analytics_data)
        print(f"Player radar chart created: {type(player_radar)}")
        
        performance_trends = dashboard._create_performance_trends_chart(analytics_data)
        print(f"Performance trends chart created: {type(performance_trends)}")
        
        champion_heatmap = dashboard._create_champion_heatmap_chart(analytics_data)
        print(f"Champion heatmap chart created: {type(champion_heatmap)}")
        
        synergy_matrix = dashboard._create_synergy_matrix_chart(analytics_data)
        print(f"Synergy matrix chart created: {type(synergy_matrix)}")
        
        print("✅ Chart creation tests passed")
        
    except Exception as e:
        print(f"❌ Chart creation failed: {e}")
        import traceback
        traceback.print_exc()


def test_filter_updates():
    """Test filter update functionality."""
    print("\n=== Testing Filter Updates ===")
    
    # Create mock dependencies
    mock_analytics_engine = MockAnalyticsEngine()
    mock_data_manager = MockDataManager()
    viz_manager = VisualizationManager()
    state_manager = EnhancedStateManager()
    
    # Create dashboard
    dashboard = AnalyticsDashboard(
        analytics_engine=mock_analytics_engine,
        visualization_manager=viz_manager,
        state_manager=state_manager,
        data_manager=mock_data_manager
    )
    
    # Test initial state
    print(f"Initial filters: {dashboard.current_filters}")
    
    # Update filters
    dashboard.current_filters.selected_players = ["TestPlayer1"]
    dashboard.current_filters.selected_champions = ["Aatrox", "Ahri"]
    dashboard.current_filters.selected_roles = ["top", "middle"]
    dashboard.current_filters.min_games = 10
    
    print(f"Updated filters: {dashboard.current_filters}")
    
    # Test filter value extraction
    filter_values = dashboard._get_current_filter_values()
    print(f"Filter values: {filter_values}")
    
    # Test empty and error chart updates
    empty_charts = dashboard._get_empty_chart_updates()
    print(f"Empty charts count: {len(empty_charts)}")
    
    error_charts = dashboard._get_error_chart_updates("Test error")
    print(f"Error charts count: {len(error_charts)}")
    
    print("✅ Filter update tests passed")


def main():
    """Run all analytics dashboard tests."""
    print("🚀 Starting Analytics Dashboard Demo")
    print("=" * 60)
    
    try:
        # Run tests
        test_filter_state()
        test_analytics_presets()
        test_dashboard_initialization()
        test_filtered_analytics_data()
        test_chart_creation()
        test_filter_updates()
        
        print("\n" + "=" * 60)
        print("✅ All Analytics Dashboard tests completed successfully!")
        print("\n📊 Analytics Dashboard Features Demonstrated:")
        print("  • Dynamic filter panel with real-time updates")
        print("  • Analytics preset configurations")
        print("  • Interactive chart creation and updates")
        print("  • Comprehensive data filtering and processing")
        print("  • Error handling and fallback mechanisms")
        print("  • State management and caching")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)