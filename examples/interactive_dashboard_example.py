"""
Example usage of the Interactive Analytics Dashboard.

This example demonstrates how to use the interactive analytics dashboard
with dynamic filtering, comparative analysis, and export capabilities.
"""

import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add the parent directory to the path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lol_team_optimizer.interactive_analytics_dashboard import (
    InteractiveAnalyticsDashboard,
    DashboardState,
    ExportOptions
)
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters,
    DateRange,
    PlayerAnalytics
)


def create_mock_engines():
    """Create mock engines for demonstration purposes."""
    print("🔧 Setting up mock analytics engines...")
    
    # Create mock analytics engine
    analytics_engine = Mock()
    
    # Mock player analytics data
    mock_analytics = Mock()
    mock_analytics.games_played = 25
    mock_analytics.wins = 15
    mock_analytics.win_rate = 0.6
    mock_analytics.avg_kda = 2.8
    mock_analytics.avg_damage = 18500
    mock_analytics.avg_gold = 13200
    mock_analytics.champion_performance = {
        1: Mock(games_played=8, wins=6, win_rate=0.75),
        2: Mock(games_played=7, wins=4, win_rate=0.57),
        3: Mock(games_played=10, wins=5, win_rate=0.5)
    }
    mock_analytics.role_performance = {
        'top': Mock(games_played=12, wins=8, win_rate=0.67),
        'jungle': Mock(games_played=8, wins=4, win_rate=0.5),
        'middle': Mock(games_played=5, wins=3, win_rate=0.6)
    }
    
    analytics_engine.analyze_player_performance.return_value = mock_analytics
    analytics_engine.get_available_champions.return_value = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # Create other mock engines
    recommendation_engine = Mock()
    composition_analyzer = Mock()
    comparative_analyzer = Mock()
    
    # Create mock data manager
    data_manager = Mock()
    
    # Mock player data
    mock_players = []
    for i in range(5):
        player = Mock()
        player.name = f"Player{i+1}"
        player.puuid = f"mock-puuid-{i+1}"
        mock_players.append(player)
    
    data_manager.load_player_data.return_value = mock_players
    
    return {
        'analytics_engine': analytics_engine,
        'recommendation_engine': recommendation_engine,
        'composition_analyzer': composition_analyzer,
        'comparative_analyzer': comparative_analyzer,
        'data_manager': data_manager
    }


def demonstrate_basic_dashboard_usage():
    """Demonstrate basic dashboard initialization and usage."""
    print("\n" + "=" * 60)
    print("📊 INTERACTIVE ANALYTICS DASHBOARD DEMO")
    print("=" * 60)
    
    # Create mock engines
    engines = create_mock_engines()
    
    # Initialize dashboard
    print("\n🚀 Initializing Interactive Analytics Dashboard...")
    dashboard = InteractiveAnalyticsDashboard(**engines)
    
    print(f"✅ Dashboard initialized successfully!")
    print(f"   Available Players: {len(dashboard.available_players)}")
    print(f"   Available Champions: {len(dashboard.available_champions)}")
    print(f"   Available Roles: {len(dashboard.available_roles)}")
    
    return dashboard


def demonstrate_filtering_capabilities(dashboard):
    """Demonstrate filtering capabilities."""
    print("\n🔍 FILTERING CAPABILITIES DEMO")
    print("-" * 40)
    
    # Configure date range filter
    print("\n📅 Setting date range filter (last 30 days)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dashboard.state.active_filters.date_range = DateRange(
        start_date=start_date,
        end_date=end_date
    )
    print(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Configure player selection
    print("\n👥 Setting player selection...")
    dashboard.state.selected_players = {"Player1", "Player2", "Player3"}
    print(f"   Selected players: {', '.join(dashboard.state.selected_players)}")
    
    # Configure role selection
    print("\n🎭 Setting role selection...")
    dashboard.state.selected_roles = {"top", "jungle", "middle"}
    print(f"   Selected roles: {', '.join(dashboard.state.selected_roles)}")
    
    # Configure game requirements
    print("\n🎮 Setting minimum games requirement...")
    dashboard.state.active_filters.min_games = 5
    print(f"   Minimum games: {dashboard.state.active_filters.min_games}")
    
    # Apply filters
    print("\n🔄 Applying filters...")
    dashboard._apply_filters()
    print(f"✅ Filters applied at {dashboard.state.last_update.strftime('%H:%M:%S')}")


def demonstrate_analytics_retrieval(dashboard):
    """Demonstrate analytics data retrieval."""
    print("\n📊 ANALYTICS DATA RETRIEVAL DEMO")
    print("-" * 40)
    
    print("\n🔄 Retrieving filtered analytics data...")
    analytics_data = dashboard._get_filtered_analytics()
    
    if analytics_data:
        print("✅ Analytics data retrieved successfully!")
        
        # Display summary
        summary = analytics_data.get('summary', {})
        print(f"\n📈 Summary Statistics:")
        print(f"   Total Players: {summary.get('total_players', 0)}")
        print(f"   Total Games: {summary.get('total_games', 0)}")
        print(f"   Average Win Rate: {summary.get('avg_win_rate', 0):.1%}")
        print(f"   Average KDA: {summary.get('avg_kda', 0):.2f}")
        
        # Display player data
        players_data = analytics_data.get('players', {})
        print(f"\n👥 Player Analytics:")
        for player_name, player_analytics in players_data.items():
            games = getattr(player_analytics, 'games_played', 0)
            win_rate = getattr(player_analytics, 'win_rate', 0)
            kda = getattr(player_analytics, 'avg_kda', 0)
            print(f"   {player_name}: {games} games, {win_rate:.1%} WR, {kda:.2f} KDA")
    else:
        print("❌ No analytics data available")


def demonstrate_comparative_analysis(dashboard):
    """Demonstrate comparative analysis capabilities."""
    print("\n⚖️ COMPARATIVE ANALYSIS DEMO")
    print("-" * 40)
    
    # Set comparison mode
    dashboard.state.comparison_mode = "players"
    print(f"🔧 Comparison mode: {dashboard.state.comparison_mode}")
    
    # Get analytics data for comparison
    analytics_data = dashboard._get_filtered_analytics()
    players_data = analytics_data.get('players', {})
    
    if len(players_data) >= 2:
        print("\n📊 Player Comparison:")
        dashboard._display_player_comparison_table(players_data)
    else:
        print("⚠️ Need at least 2 players for comparison")


def demonstrate_export_functionality(dashboard):
    """Demonstrate export and reporting functionality."""
    print("\n📤 EXPORT & REPORTING DEMO")
    print("-" * 40)
    
    print("\n📊 Exporting current analytics...")
    try:
        dashboard._export_current_analytics()
        print("✅ Analytics export completed")
    except Exception as e:
        print(f"⚠️ Export simulation: {e}")
    
    print("\n📈 Exporting performance report...")
    try:
        dashboard._export_performance_report()
        print("✅ Performance report export completed")
    except Exception as e:
        print(f"⚠️ Export simulation: {e}")
    
    # Demonstrate export options
    print("\n🔧 Export Options Configuration:")
    export_options = ExportOptions(
        format="json",
        include_charts=True,
        include_raw_data=True,
        custom_fields=["win_rate", "kda", "damage"],
        file_path="./exports/custom_analytics.json"
    )
    
    print(f"   Format: {export_options.format}")
    print(f"   Include Charts: {export_options.include_charts}")
    print(f"   Include Raw Data: {export_options.include_raw_data}")
    print(f"   Custom Fields: {', '.join(export_options.custom_fields)}")
    print(f"   File Path: {export_options.file_path}")


def demonstrate_drill_down_capabilities(dashboard):
    """Demonstrate drill-down analysis capabilities."""
    print("\n🎯 DRILL-DOWN ANALYSIS DEMO")
    print("-" * 40)
    
    # Get analytics data
    analytics_data = dashboard._get_filtered_analytics()
    
    if analytics_data:
        print("\n📊 Summary Level:")
        dashboard._display_summary_metrics(analytics_data)
        
        print("\n🔍 Drilling down to player details...")
        players_data = analytics_data.get('players', {})
        
        if players_data:
            # Show detailed analysis for first player
            first_player = list(players_data.keys())[0]
            player_data = players_data[first_player]
            
            print(f"\n👤 Detailed Analysis for {first_player}:")
            dashboard._display_detailed_player_analysis(first_player, player_data)
        else:
            print("⚠️ No player data available for drill-down")
    else:
        print("⚠️ No analytics data available for drill-down")


def demonstrate_real_time_updates(dashboard):
    """Demonstrate real-time analytics updates."""
    print("\n🔄 REAL-TIME UPDATES DEMO")
    print("-" * 40)
    
    print("\n⏰ Initial state:")
    print(f"   Last Update: {dashboard.state.last_update}")
    print(f"   Cache Size: {len(dashboard.state.cached_results)}")
    
    # Simulate filter changes
    print("\n🔧 Changing filters...")
    dashboard.state.selected_players.add("Player4")
    dashboard.state.active_filters.min_games = 10
    
    # Apply changes
    dashboard._apply_filters()
    
    print(f"\n✅ Updated state:")
    print(f"   Last Update: {dashboard.state.last_update.strftime('%H:%M:%S')}")
    print(f"   Cache Size: {len(dashboard.state.cached_results)} (cleared for refresh)")
    print(f"   Selected Players: {len(dashboard.state.selected_players)}")
    print(f"   Min Games: {dashboard.state.active_filters.min_games}")


def main():
    """Main demonstration function."""
    try:
        # Initialize dashboard
        dashboard = demonstrate_basic_dashboard_usage()
        
        # Demonstrate various capabilities
        demonstrate_filtering_capabilities(dashboard)
        demonstrate_analytics_retrieval(dashboard)
        demonstrate_comparative_analysis(dashboard)
        demonstrate_export_functionality(dashboard)
        demonstrate_drill_down_capabilities(dashboard)
        demonstrate_real_time_updates(dashboard)
        
        print("\n" + "=" * 60)
        print("🎉 INTERACTIVE ANALYTICS DASHBOARD DEMO COMPLETE")
        print("=" * 60)
        print("\n💡 Key Features Demonstrated:")
        print("   ✅ Dynamic filtering with real-time updates")
        print("   ✅ Drill-down capabilities from summary to detailed views")
        print("   ✅ Comparative analysis for multiple players")
        print("   ✅ Export and reporting functionality")
        print("   ✅ Interactive menu system with user-friendly interface")
        
        print("\n🚀 To use the dashboard in the main application:")
        print("   1. Launch the LoL Team Optimizer")
        print("   2. Go to 'View Analysis' menu")
        print("   3. Select 'Interactive Analytics Dashboard'")
        print("   4. Use the interactive menu to explore your data")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()