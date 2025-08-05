"""
Interactive Analytics Dashboard for League of Legends Team Optimizer.

This module provides an interactive dashboard with dynamic filtering,
real-time analytics updates, drill-down capabilities, and comparative analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import json
import csv
from pathlib import Path

from .analytics_models import (
    AnalyticsFilters, DateRange, PlayerAnalytics, ChampionPerformanceMetrics,
    TeamComposition, CompositionPerformance, PerformanceDelta
)
from .historical_analytics_engine import HistoricalAnalyticsEngine
from .champion_recommendation_engine import ChampionRecommendationEngine
from .team_composition_analyzer import TeamCompositionAnalyzer
from .comparative_analyzer import ComparativeAnalyzer
from .data_manager import DataManager


@dataclass
class DashboardState:
    """Maintains the current state of the interactive dashboard."""
    active_filters: AnalyticsFilters = field(default_factory=lambda: AnalyticsFilters())
    selected_players: Set[str] = field(default_factory=set)
    selected_champions: Set[int] = field(default_factory=set)
    selected_roles: Set[str] = field(default_factory=set)
    comparison_mode: str = "players"  # "players", "champions", "roles", "time_periods"
    view_level: str = "summary"  # "summary", "detailed", "individual"
    cached_results: Dict[str, Any] = field(default_factory=dict)
    last_update: Optional[datetime] = None


@dataclass
class ExportOptions:
    """Options for exporting analytics data."""
    format: str = "csv"  # "csv", "json", "excel", "pdf"
    include_charts: bool = False
    include_raw_data: bool = True
    custom_fields: List[str] = field(default_factory=list)
    file_path: Optional[str] = None


class InteractiveAnalyticsDashboard:
    """
    Interactive analytics dashboard with dynamic filtering and real-time updates.
    
    Provides comprehensive analytics interface with:
    - Dynamic filtering with real-time updates
    - Drill-down capabilities from summary to detailed views
    - Comparative analysis for multiple players/champions
    - Export and reporting functionality
    """
    
    def __init__(self, 
                 analytics_engine: HistoricalAnalyticsEngine,
                 recommendation_engine: ChampionRecommendationEngine,
                 composition_analyzer: TeamCompositionAnalyzer,
                 comparative_analyzer: ComparativeAnalyzer,
                 data_manager: DataManager):
        """Initialize the interactive analytics dashboard."""
        self.logger = logging.getLogger(__name__)
        self.analytics_engine = analytics_engine
        self.recommendation_engine = recommendation_engine
        self.composition_analyzer = composition_analyzer
        self.comparative_analyzer = comparative_analyzer
        self.data_manager = data_manager
        
        # Dashboard state
        self.state = DashboardState()
        
        # Available options for filtering
        self.available_players = []
        self.available_champions = []
        self.available_roles = ["top", "jungle", "middle", "support", "bottom"]
        
        # Initialize available options
        self._refresh_available_options()  
  
    def _refresh_available_options(self) -> None:
        """Refresh available players and champions for filtering."""
        try:
            # Get available players
            players = self.data_manager.load_player_data()
            self.available_players = [(p.name, p.puuid) for p in players if p.puuid]
            
            # Get available champions from analytics engine
            self.available_champions = list(self.analytics_engine.get_available_champions())
            
            self.logger.info(f"Refreshed options: {len(self.available_players)} players, {len(self.available_champions)} champions")
        except Exception as e:
            self.logger.error(f"Failed to refresh available options: {e}")
    
    def show_dashboard(self) -> None:
        """Main dashboard interface with interactive menu."""
        while True:
            self._display_dashboard_header()
            self._display_current_filters()
            self._display_dashboard_menu()
            
            choice = input("\nEnter your choice: ").strip().lower()
            
            if choice == "1":
                self._configure_filters()
            elif choice == "2":
                self._show_summary_analytics()
            elif choice == "3":
                self._show_detailed_analytics()
            elif choice == "4":
                self._show_comparative_analysis()
            elif choice == "5":
                self._drill_down_analysis()
            elif choice == "6":
                self._export_analytics()
            elif choice == "7":
                self._refresh_data()
            elif choice == "8":
                break
            elif choice == "r":
                self._refresh_data()
            elif choice == "f":
                self._configure_filters()
            elif choice == "c":
                self._clear_filters()
            else:
                print("Invalid choice. Please try again.")
            
            if choice != "8":
                input("\nPress Enter to continue...")
    
    def _display_dashboard_header(self) -> None:
        """Display dashboard header with current status."""
        print("\n" + "=" * 80)
        print("📊 INTERACTIVE ANALYTICS DASHBOARD")
        print("=" * 80)
        
        # Show current state
        player_count = len(self.state.selected_players) if self.state.selected_players else len(self.available_players)
        champion_count = len(self.state.selected_champions) if self.state.selected_champions else len(self.available_champions)
        
        print(f"📈 Active Analysis: {player_count} players, {champion_count} champions")
        print(f"🎯 View Level: {self.state.view_level.title()}")
        print(f"🔄 Last Update: {self.state.last_update.strftime('%H:%M:%S') if self.state.last_update else 'Never'}")
    
    def _display_current_filters(self) -> None:
        """Display currently active filters."""
        filters = self.state.active_filters
        
        print(f"\n🔍 Active Filters:")
        
        # Date range
        if filters.date_range:
            start = filters.date_range.start_date.strftime('%Y-%m-%d')
            end = filters.date_range.end_date.strftime('%Y-%m-%d')
            print(f"   📅 Date Range: {start} to {end}")
        else:
            print(f"   📅 Date Range: All time")
        
        # Player selection
        if self.state.selected_players:
            players_str = ", ".join(list(self.state.selected_players)[:3])
            if len(self.state.selected_players) > 3:
                players_str += f" (+{len(self.state.selected_players) - 3} more)"
            print(f"   👥 Players: {players_str}")
        else:
            print(f"   👥 Players: All ({len(self.available_players)})")
        
        # Champion selection
        if self.state.selected_champions:
            print(f"   🏆 Champions: {len(self.state.selected_champions)} selected")
        else:
            print(f"   🏆 Champions: All ({len(self.available_champions)})")
        
        # Role selection
        if self.state.selected_roles:
            roles_str = ", ".join(self.state.selected_roles)
            print(f"   🎭 Roles: {roles_str}")
        else:
            print(f"   🎭 Roles: All")
        
        # Other filters
        if filters.min_games and filters.min_games > 1:
            print(f"   🎮 Min Games: {filters.min_games}")
        
        if filters.queue_types:
            print(f"   🏟️ Queue Types: {', '.join(filters.queue_types)}")
    
    def _display_dashboard_menu(self) -> None:
        """Display the main dashboard menu options."""
        print(f"\n📋 Dashboard Options:")
        print("1. 🔧 Configure Filters")
        print("2. 📊 Summary Analytics")
        print("3. 🔍 Detailed Analytics")
        print("4. ⚖️ Comparative Analysis")
        print("5. 🎯 Drill-Down Analysis")
        print("6. 📤 Export & Reporting")
        print("7. 🔄 Refresh Data")
        print("8. 🏠 Back to Main Menu")
        
        print(f"\n⚡ Quick Actions: 'r'=Refresh, 'f'=Filters, 'c'=Clear Filters")
    
    def _configure_filters(self) -> None:
        """Interactive filter configuration with real-time preview."""
        print("\n🔧 Configure Analytics Filters")
        print("-" * 40)
        
        while True:
            print(f"\nFilter Configuration:")
            print("1. 📅 Date Range")
            print("2. 👥 Player Selection")
            print("3. 🏆 Champion Selection")
            print("4. 🎭 Role Selection")
            print("5. 🎮 Game Requirements")
            print("6. 🏟️ Queue Types")
            print("7. ✅ Apply Filters")
            print("8. 🔄 Reset All Filters")
            print("9. ❌ Cancel")
            
            choice = input("\nSelect filter to configure: ").strip()
            
            if choice == "1":
                self._configure_date_range()
            elif choice == "2":
                self._configure_player_selection()
            elif choice == "3":
                self._configure_champion_selection()
            elif choice == "4":
                self._configure_role_selection()
            elif choice == "5":
                self._configure_game_requirements()
            elif choice == "6":
                self._configure_queue_types()
            elif choice == "7":
                self._apply_filters()
                break
            elif choice == "8":
                self._reset_filters()
            elif choice == "9":
                break
            else:
                print("Invalid choice. Please try again.")
    
    def _configure_date_range(self) -> None:
        """Configure date range filter."""
        print("\n📅 Date Range Configuration")
        print("1. Last 7 days")
        print("2. Last 30 days")
        print("3. Last 3 months")
        print("4. Last 6 months")
        print("5. Custom range")
        print("6. All time")
        
        choice = input("Select date range: ").strip()
        
        now = datetime.now()
        
        if choice == "1":
            start_date = now - timedelta(days=7)
            self.state.active_filters.date_range = DateRange(start_date=start_date, end_date=now)
        elif choice == "2":
            start_date = now - timedelta(days=30)
            self.state.active_filters.date_range = DateRange(start_date=start_date, end_date=now)
        elif choice == "3":
            start_date = now - timedelta(days=90)
            self.state.active_filters.date_range = DateRange(start_date=start_date, end_date=now)
        elif choice == "4":
            start_date = now - timedelta(days=180)
            self.state.active_filters.date_range = DateRange(start_date=start_date, end_date=now)
        elif choice == "5":
            self._configure_custom_date_range()
        elif choice == "6":
            self.state.active_filters.date_range = None
        
        print("✅ Date range updated")
    
    def _configure_custom_date_range(self) -> None:
        """Configure custom date range."""
        try:
            start_str = input("Enter start date (YYYY-MM-DD): ").strip()
            end_str = input("Enter end date (YYYY-MM-DD): ").strip()
            
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            
            if start_date >= end_date:
                print("❌ Start date must be before end date")
                return
            
            self.state.active_filters.date_range = DateRange(start_date=start_date, end_date=end_date)
            print("✅ Custom date range set")
            
        except ValueError:
            print("❌ Invalid date format. Please use YYYY-MM-DD")
    
    def _configure_player_selection(self) -> None:
        """Configure player selection filter."""
        print("\n👥 Player Selection")
        
        if not self.available_players:
            print("No players available")
            return
        
        print("Available players:")
        for i, (name, puuid) in enumerate(self.available_players, 1):
            selected = "✅" if name in self.state.selected_players else "⬜"
            print(f"{i:2}. {selected} {name}")
        
        print(f"\nCurrent selection: {len(self.state.selected_players)} players")
        print("Options:")
        print("1. Select specific players (comma-separated numbers)")
        print("2. Select all players")
        print("3. Clear selection")
        print("4. Toggle individual players")
        
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            try:
                indices = [int(x.strip()) - 1 for x in input("Enter player numbers: ").split(",")]
                self.state.selected_players = {
                    self.available_players[i][0] for i in indices 
                    if 0 <= i < len(self.available_players)
                }
                print(f"✅ Selected {len(self.state.selected_players)} players")
            except ValueError:
                print("❌ Invalid input format")
        elif choice == "2":
            self.state.selected_players = {name for name, _ in self.available_players}
            print("✅ All players selected")
        elif choice == "3":
            self.state.selected_players.clear()
            print("✅ Player selection cleared")
        elif choice == "4":
            self._toggle_player_selection()
    
    def _toggle_player_selection(self) -> None:
        """Toggle individual player selection."""
        while True:
            print("\nToggle players (enter number to toggle, 'done' to finish):")
            for i, (name, puuid) in enumerate(self.available_players, 1):
                selected = "✅" if name in self.state.selected_players else "⬜"
                print(f"{i:2}. {selected} {name}")
            
            choice = input("Toggle player (number or 'done'): ").strip().lower()
            
            if choice == "done":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.available_players):
                    name = self.available_players[idx][0]
                    if name in self.state.selected_players:
                        self.state.selected_players.remove(name)
                        print(f"❌ Deselected {name}")
                    else:
                        self.state.selected_players.add(name)
                        print(f"✅ Selected {name}")
                else:
                    print("❌ Invalid player number")
            except ValueError:
                print("❌ Invalid input")
    
    def _configure_role_selection(self) -> None:
        """Configure role selection filter."""
        print("\n🎭 Role Selection")
        
        print("Available roles:")
        for i, role in enumerate(self.available_roles, 1):
            selected = "✅" if role in self.state.selected_roles else "⬜"
            print(f"{i}. {selected} {role.title()}")
        
        print("\nOptions:")
        print("1. Select specific roles")
        print("2. Select all roles")
        print("3. Clear selection")
        
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            try:
                indices = [int(x.strip()) - 1 for x in input("Enter role numbers: ").split(",")]
                self.state.selected_roles = {
                    self.available_roles[i] for i in indices 
                    if 0 <= i < len(self.available_roles)
                }
                print(f"✅ Selected {len(self.state.selected_roles)} roles")
            except ValueError:
                print("❌ Invalid input format")
        elif choice == "2":
            self.state.selected_roles = set(self.available_roles)
            print("✅ All roles selected")
        elif choice == "3":
            self.state.selected_roles.clear()
            print("✅ Role selection cleared")
    
    def _apply_filters(self) -> None:
        """Apply current filters and update cached results."""
        print("\n🔄 Applying filters and updating analytics...")
        
        try:
            # Clear cached results to force refresh
            self.state.cached_results.clear()
            
            # Update timestamp
            self.state.last_update = datetime.now()
            
            print("✅ Filters applied successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to apply filters: {e}")
            print(f"❌ Failed to apply filters: {e}")
    
    def _reset_filters(self) -> None:
        """Reset all filters to default state."""
        self.state.active_filters = AnalyticsFilters()
        self.state.selected_players.clear()
        self.state.selected_champions.clear()
        self.state.selected_roles.clear()
        self.state.cached_results.clear()
        
        print("✅ All filters reset to default")
    
    def _clear_filters(self) -> None:
        """Quick clear all filters."""
        self._reset_filters()  
  
    def _show_summary_analytics(self) -> None:
        """Display summary-level analytics with current filters."""
        print("\n📊 Summary Analytics")
        print("-" * 40)
        
        try:
            # Get filtered analytics data
            analytics_data = self._get_filtered_analytics()
            
            if not analytics_data:
                print("No data available with current filters")
                return
            
            # Display summary metrics
            self._display_summary_metrics(analytics_data)
            
            # Show top performers
            self._display_top_performers(analytics_data)
            
            # Show trends
            self._display_summary_trends(analytics_data)
            
        except Exception as e:
            self.logger.error(f"Failed to show summary analytics: {e}")
            print(f"❌ Failed to load summary analytics: {e}")
    
    def _show_detailed_analytics(self) -> None:
        """Display detailed analytics with drill-down options."""
        print("\n🔍 Detailed Analytics")
        print("-" * 40)
        
        while True:
            print("\nDetailed Analysis Options:")
            print("1. 👤 Player Performance Details")
            print("2. 🏆 Champion Performance Details")
            print("3. 🎭 Role Performance Analysis")
            print("4. 📈 Performance Trends")
            print("5. 🤝 Synergy Analysis")
            print("6. 🏠 Back to Dashboard")
            
            choice = input("Select analysis type: ").strip()
            
            if choice == "1":
                self._show_player_performance_details()
            elif choice == "2":
                self._show_champion_performance_details()
            elif choice == "3":
                self._show_role_performance_analysis()
            elif choice == "4":
                self._show_performance_trends()
            elif choice == "5":
                self._show_synergy_analysis()
            elif choice == "6":
                break
            else:
                print("Invalid choice. Please try again.")
            
            if choice != "6":
                input("\nPress Enter to continue...")
    
    def _show_comparative_analysis(self) -> None:
        """Display comparative analysis interface."""
        print("\n⚖️ Comparative Analysis")
        print("-" * 40)
        
        while True:
            print(f"\nComparison Mode: {self.state.comparison_mode.title()}")
            print("\nComparison Options:")
            print("1. 👥 Compare Players")
            print("2. 🏆 Compare Champions")
            print("3. 🎭 Compare Roles")
            print("4. 📅 Compare Time Periods")
            print("5. 🔧 Change Comparison Mode")
            print("6. 🏠 Back to Dashboard")
            
            choice = input("Select comparison type: ").strip()
            
            if choice == "1":
                self.state.comparison_mode = "players"
                self._compare_players()
            elif choice == "2":
                self.state.comparison_mode = "champions"
                self._compare_champions()
            elif choice == "3":
                self.state.comparison_mode = "roles"
                self._compare_roles()
            elif choice == "4":
                self.state.comparison_mode = "time_periods"
                self._compare_time_periods()
            elif choice == "5":
                self._change_comparison_mode()
            elif choice == "6":
                break
            else:
                print("Invalid choice. Please try again.")
            
            if choice != "6":
                input("\nPress Enter to continue...")
    
    def _drill_down_analysis(self) -> None:
        """Provide drill-down capabilities from summary to detailed views."""
        print("\n🎯 Drill-Down Analysis")
        print("-" * 40)
        
        # Start with summary view
        analytics_data = self._get_filtered_analytics()
        
        if not analytics_data:
            print("No data available for drill-down analysis")
            return
        
        # Show summary first
        print("📊 Summary View:")
        self._display_summary_metrics(analytics_data)
        
        while True:
            print("\nDrill-Down Options:")
            print("1. 🔍 Drill into specific player")
            print("2. 🏆 Drill into specific champion")
            print("3. 🎭 Drill into specific role")
            print("4. 📅 Drill into time period")
            print("5. 🔄 Refresh summary")
            print("6. 🏠 Back to Dashboard")
            
            choice = input("Select drill-down option: ").strip()
            
            if choice == "1":
                self._drill_down_player(analytics_data)
            elif choice == "2":
                self._drill_down_champion(analytics_data)
            elif choice == "3":
                self._drill_down_role(analytics_data)
            elif choice == "4":
                self._drill_down_time_period(analytics_data)
            elif choice == "5":
                analytics_data = self._get_filtered_analytics()
                self._display_summary_metrics(analytics_data)
            elif choice == "6":
                break
            else:
                print("Invalid choice. Please try again.")
    
    def _export_analytics(self) -> None:
        """Export analytics data and reports."""
        print("\n📤 Export & Reporting")
        print("-" * 40)
        
        while True:
            print("\nExport Options:")
            print("1. 📊 Export Current Analytics")
            print("2. 📈 Export Performance Report")
            print("3. 🏆 Export Champion Analysis")
            print("4. 👥 Export Player Comparison")
            print("5. 🔧 Configure Export Settings")
            print("6. 🏠 Back to Dashboard")
            
            choice = input("Select export option: ").strip()
            
            if choice == "1":
                self._export_current_analytics()
            elif choice == "2":
                self._export_performance_report()
            elif choice == "3":
                self._export_champion_analysis()
            elif choice == "4":
                self._export_player_comparison()
            elif choice == "5":
                self._configure_export_settings()
            elif choice == "6":
                break
            else:
                print("Invalid choice. Please try again.")
            
            if choice != "6":
                input("\nPress Enter to continue...")
    
    def _get_filtered_analytics(self) -> Dict[str, Any]:
        """Get analytics data with current filters applied."""
        cache_key = self._generate_cache_key()
        
        # Check cache first
        if cache_key in self.state.cached_results:
            return self.state.cached_results[cache_key]
        
        try:
            # Get player data based on selection
            if self.state.selected_players:
                player_puuids = [
                    puuid for name, puuid in self.available_players 
                    if name in self.state.selected_players
                ]
            else:
                player_puuids = [puuid for _, puuid in self.available_players]
            
            # Collect analytics for each player
            analytics_data = {
                'players': {},
                'champions': {},
                'roles': {},
                'summary': {},
                'filters_applied': self.state.active_filters,
                'timestamp': datetime.now()
            }
            
            for puuid in player_puuids:
                try:
                    player_analytics = self.analytics_engine.analyze_player_performance(
                        puuid, self.state.active_filters
                    )
                    
                    if player_analytics:
                        # Find player name
                        player_name = next(
                            (name for name, p_uuid in self.available_players if p_uuid == puuid),
                            f"Player_{puuid[:8]}"
                        )
                        analytics_data['players'][player_name] = player_analytics
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get analytics for player {puuid}: {e}")
                    continue
            
            # Generate summary statistics
            analytics_data['summary'] = self._generate_summary_statistics(analytics_data['players'])
            
            # Cache the results
            self.state.cached_results[cache_key] = analytics_data
            
            return analytics_data
            
        except Exception as e:
            self.logger.error(f"Failed to get filtered analytics: {e}")
            return {}
    
    def _generate_cache_key(self) -> str:
        """Generate cache key based on current filters and selections."""
        key_parts = [
            f"players:{sorted(self.state.selected_players) if self.state.selected_players else 'all'}",
            f"champions:{sorted(self.state.selected_champions) if self.state.selected_champions else 'all'}",
            f"roles:{sorted(self.state.selected_roles) if self.state.selected_roles else 'all'}",
            f"date_range:{self.state.active_filters.date_range}",
            f"min_games:{self.state.active_filters.min_games}",
            f"queue_types:{sorted(self.state.active_filters.queue_types) if self.state.active_filters.queue_types else 'all'}"
        ]
        return "|".join(key_parts)
    
    def _display_summary_metrics(self, analytics_data: Dict[str, Any]) -> None:
        """Display summary metrics from analytics data."""
        summary = analytics_data.get('summary', {})
        
        if not summary:
            print("No summary data available")
            return
        
        print(f"\n📊 Summary Metrics:")
        print(f"   Total Players Analyzed: {summary.get('total_players', 0)}")
        print(f"   Total Games: {summary.get('total_games', 0)}")
        print(f"   Average Win Rate: {summary.get('avg_win_rate', 0):.1%}")
        print(f"   Average KDA: {summary.get('avg_kda', 0):.2f}")
        
        # Performance distribution
        if 'performance_distribution' in summary:
            dist = summary['performance_distribution']
            print(f"\n📈 Performance Distribution:")
            print(f"   High Performers (>60% WR): {dist.get('high', 0)} players")
            print(f"   Average Performers (40-60% WR): {dist.get('average', 0)} players")
            print(f"   Struggling Players (<40% WR): {dist.get('low', 0)} players")
    
    def _display_top_performers(self, analytics_data: Dict[str, Any]) -> None:
        """Display top performing players/champions."""
        players_data = analytics_data.get('players', {})
        
        if not players_data:
            return
        
        # Sort players by win rate
        sorted_players = sorted(
            players_data.items(),
            key=lambda x: getattr(x[1], 'win_rate', 0),
            reverse=True
        )
        
        print(f"\n🏆 Top Performers:")
        for i, (player_name, analytics) in enumerate(sorted_players[:5], 1):
            win_rate = getattr(analytics, 'win_rate', 0)
            games_played = getattr(analytics, 'games_played', 0)
            kda = getattr(analytics, 'avg_kda', 0)
            
            print(f"   {i}. {player_name}: {win_rate:.1%} WR, {kda:.2f} KDA ({games_played} games)")
    
    def _generate_summary_statistics(self, players_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from player analytics data."""
        if not players_data:
            return {}
        
        total_players = len(players_data)
        total_games = 0
        total_wins = 0
        total_kda = 0
        valid_kda_count = 0
        
        performance_distribution = {'high': 0, 'average': 0, 'low': 0}
        
        for player_analytics in players_data.values():
            games = getattr(player_analytics, 'games_played', 0)
            wins = getattr(player_analytics, 'wins', 0)
            kda = getattr(player_analytics, 'avg_kda', 0)
            
            total_games += games
            total_wins += wins
            
            if kda > 0:
                total_kda += kda
                valid_kda_count += 1
            
            # Categorize performance
            if games > 0:
                win_rate = wins / games
                if win_rate > 0.6:
                    performance_distribution['high'] += 1
                elif win_rate >= 0.4:
                    performance_distribution['average'] += 1
                else:
                    performance_distribution['low'] += 1
        
        return {
            'total_players': total_players,
            'total_games': total_games,
            'avg_win_rate': total_wins / total_games if total_games > 0 else 0,
            'avg_kda': total_kda / valid_kda_count if valid_kda_count > 0 else 0,
            'performance_distribution': performance_distribution
        }
    
    def _refresh_data(self) -> None:
        """Refresh all analytics data."""
        print("\n🔄 Refreshing analytics data...")
        
        try:
            # Clear cache
            self.state.cached_results.clear()
            
            # Refresh available options
            self._refresh_available_options()
            
            # Update timestamp
            self.state.last_update = datetime.now()
            
            print("✅ Data refreshed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh data: {e}")
            print(f"❌ Failed to refresh data: {e}")
    
    def _export_current_analytics(self) -> None:
        """Export current analytics data."""
        print("\n📊 Exporting Current Analytics...")
        
        try:
            analytics_data = self._get_filtered_analytics()
            
            if not analytics_data:
                print("No data to export")
                return
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analytics_export_{timestamp}.json"
            
            # Export data
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'filters_applied': {
                    'date_range': str(self.state.active_filters.date_range) if self.state.active_filters.date_range else None,
                    'selected_players': list(self.state.selected_players),
                    'selected_champions': list(self.state.selected_champions),
                    'selected_roles': list(self.state.selected_roles),
                    'min_games': self.state.active_filters.min_games
                },
                'summary': analytics_data.get('summary', {}),
                'player_count': len(analytics_data.get('players', {})),
                'data_timestamp': analytics_data.get('timestamp', datetime.now()).isoformat()
            }
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✅ Analytics exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to export analytics: {e}")
            print(f"❌ Export failed: {e}")
    
    def _compare_players(self) -> None:
        """Compare multiple players side by side."""
        print("\n👥 Player Comparison")
        
        if len(self.state.selected_players) < 2:
            print("Please select at least 2 players for comparison")
            return
        
        try:
            analytics_data = self._get_filtered_analytics()
            players_data = analytics_data.get('players', {})
            
            # Filter to selected players
            comparison_data = {
                name: data for name, data in players_data.items()
                if name in self.state.selected_players
            }
            
            if len(comparison_data) < 2:
                print("Insufficient data for selected players")
                return
            
            # Display comparison table
            self._display_player_comparison_table(comparison_data)
            
        except Exception as e:
            self.logger.error(f"Failed to compare players: {e}")
            print(f"❌ Comparison failed: {e}")
    
    def _display_player_comparison_table(self, comparison_data: Dict[str, Any]) -> None:
        """Display player comparison in table format."""
        print(f"\n⚖️ Player Comparison Table:")
        print("-" * 80)
        
        # Header
        players = list(comparison_data.keys())
        print(f"{'Metric':<20}", end="")
        for player in players:
            print(f"{player:<15}", end="")
        print()
        print("-" * 80)
        
        # Metrics to compare
        metrics = [
            ('Games Played', 'games_played', '{}'),
            ('Win Rate', 'win_rate', '{:.1%}'),
            ('Average KDA', 'avg_kda', '{:.2f}'),
            ('Avg Damage', 'avg_damage', '{:.0f}'),
            ('Avg Gold', 'avg_gold', '{:.0f}')
        ]
        
        for metric_name, attr_name, format_str in metrics:
            print(f"{metric_name:<20}", end="")
            for player in players:
                analytics = comparison_data[player]
                value = getattr(analytics, attr_name, 0)
                formatted_value = format_str.format(value)
                print(f"{formatted_value:<15}", end="")
            print()
        
        print("-" * 80)
    
    def _show_player_performance_details(self) -> None:
        """Show detailed player performance analysis."""
        if not self.available_players:
            print("No players available")
            return
        
        # Select player
        print("\nSelect player for detailed analysis:")
        for i, (name, puuid) in enumerate(self.available_players, 1):
            print(f"{i}. {name}")
        
        try:
            choice = int(input("Enter player number: ").strip()) - 1
            if not 0 <= choice < len(self.available_players):
                print("Invalid selection")
                return
            
            player_name, player_puuid = self.available_players[choice]
            
            # Get detailed analytics
            analytics_data = self._get_filtered_analytics()
            player_data = analytics_data.get('players', {}).get(player_name)
            
            if not player_data:
                print(f"No data available for {player_name}")
                return
            
            self._display_detailed_player_analysis(player_name, player_data)
            
        except ValueError:
            print("Invalid input")
    
    def _display_detailed_player_analysis(self, player_name: str, player_data: Any) -> None:
        """Display detailed analysis for a specific player."""
        print(f"\n🔍 Detailed Analysis: {player_name}")
        print("=" * 60)
        
        # Basic stats
        games = getattr(player_data, 'games_played', 0)
        wins = getattr(player_data, 'wins', 0)
        win_rate = wins / games if games > 0 else 0
        
        print(f"📊 Performance Overview:")
        print(f"   Games Played: {games}")
        print(f"   Win Rate: {win_rate:.1%}")
        print(f"   Average KDA: {getattr(player_data, 'avg_kda', 0):.2f}")
        
        # Champion performance
        if hasattr(player_data, 'champion_performance') and player_data.champion_performance:
            print(f"\n🏆 Top Champions:")
            champion_perf = player_data.champion_performance
            sorted_champions = sorted(
                champion_perf.items(),
                key=lambda x: getattr(x[1], 'win_rate', 0),
                reverse=True
            )[:5]
            
            for champion_id, perf in sorted_champions:
                champion_name = self._get_champion_name(champion_id)
                champ_games = getattr(perf, 'games_played', 0)
                champ_wr = getattr(perf, 'win_rate', 0)
                print(f"   {champion_name}: {champ_wr:.1%} WR ({champ_games} games)")
        
        # Role performance
        if hasattr(player_data, 'role_performance') and player_data.role_performance:
            print(f"\n🎭 Role Performance:")
            for role, perf in player_data.role_performance.items():
                role_games = getattr(perf, 'games_played', 0)
                role_wr = getattr(perf, 'win_rate', 0)
                if role_games > 0:
                    print(f"   {role.title()}: {role_wr:.1%} WR ({role_games} games)")
    
    def _get_champion_name(self, champion_id: int) -> str:
        """Get champion name from ID."""
        # This would typically use the champion data manager
        return f"Champion_{champion_id}"
    
    def _drill_down_player(self, analytics_data: Dict[str, Any]) -> None:
        """Drill down into specific player analysis."""
        players_data = analytics_data.get('players', {})
        
        if not players_data:
            print("No player data available")
            return
        
        print("\nSelect player to drill down:")
        player_names = list(players_data.keys())
        for i, name in enumerate(player_names, 1):
            print(f"{i}. {name}")
        
        try:
            choice = int(input("Enter player number: ").strip()) - 1
            if not 0 <= choice < len(player_names):
                print("Invalid selection")
                return
            
            selected_player = player_names[choice]
            player_data = players_data[selected_player]
            
            self._display_detailed_player_analysis(selected_player, player_data)
            
        except ValueError:
            print("Invalid input")
    
    def _configure_game_requirements(self) -> None:
        """Configure minimum game requirements."""
        print("\n🎮 Game Requirements Configuration")
        
        current_min = self.state.active_filters.min_games or 1
        print(f"Current minimum games: {current_min}")
        
        try:
            new_min = input("Enter minimum games (or press Enter to keep current): ").strip()
            if new_min:
                min_games = int(new_min)
                if min_games >= 1:
                    self.state.active_filters.min_games = min_games
                    print(f"✅ Minimum games set to {min_games}")
                else:
                    print("❌ Minimum games must be at least 1")
        except ValueError:
            print("❌ Invalid number")
    
    def _configure_queue_types(self) -> None:
        """Configure queue type filters."""
        print("\n🏟️ Queue Type Configuration")
        
        available_queues = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR", "NORMAL_DRAFT", "NORMAL_BLIND", "ARAM"]
        
        print("Available queue types:")
        for i, queue in enumerate(available_queues, 1):
            selected = "✅" if queue in (self.state.active_filters.queue_types or []) else "⬜"
            print(f"{i}. {selected} {queue}")
        
        print("\nOptions:")
        print("1. Select specific queues")
        print("2. Select all queues")
        print("3. Clear selection")
        
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            try:
                indices = [int(x.strip()) - 1 for x in input("Enter queue numbers: ").split(",")]
                selected_queues = [
                    available_queues[i] for i in indices 
                    if 0 <= i < len(available_queues)
                ]
                self.state.active_filters.queue_types = selected_queues
                print(f"✅ Selected {len(selected_queues)} queue types")
            except ValueError:
                print("❌ Invalid input format")
        elif choice == "2":
            self.state.active_filters.queue_types = available_queues
            print("✅ All queue types selected")
        elif choice == "3":
            self.state.active_filters.queue_types = []
            print("✅ Queue type selection cleared")
    
    def _show_champion_performance_details(self) -> None:
        """Show detailed champion performance analysis."""
        print("\n🏆 Champion Performance Details")
        print("This feature analyzes champion performance across all selected players")
        
        analytics_data = self._get_filtered_analytics()
        
        # Aggregate champion performance across all players
        champion_stats = {}
        
        for player_name, player_data in analytics_data.get('players', {}).items():
            if hasattr(player_data, 'champion_performance') and player_data.champion_performance:
                for champion_id, perf in player_data.champion_performance.items():
                    if champion_id not in champion_stats:
                        champion_stats[champion_id] = {
                            'total_games': 0,
                            'total_wins': 0,
                            'players': []
                        }
                    
                    games = getattr(perf, 'games_played', 0)
                    wins = getattr(perf, 'wins', 0)
                    
                    champion_stats[champion_id]['total_games'] += games
                    champion_stats[champion_id]['total_wins'] += wins
                    champion_stats[champion_id]['players'].append(player_name)
        
        if not champion_stats:
            print("No champion performance data available")
            return
        
        # Display top champions
        print(f"\n🏆 Top Champions (by win rate):")
        sorted_champions = sorted(
            champion_stats.items(),
            key=lambda x: x[1]['total_wins'] / x[1]['total_games'] if x[1]['total_games'] > 0 else 0,
            reverse=True
        )[:10]
        
        for champion_id, stats in sorted_champions:
            champion_name = self._get_champion_name(champion_id)
            win_rate = stats['total_wins'] / stats['total_games'] if stats['total_games'] > 0 else 0
            player_count = len(stats['players'])
            
            print(f"   {champion_name}: {win_rate:.1%} WR ({stats['total_games']} games, {player_count} players)")
    
    def _show_role_performance_analysis(self) -> None:
        """Show role-based performance analysis."""
        print("\n🎭 Role Performance Analysis")
        
        analytics_data = self._get_filtered_analytics()
        
        # Aggregate role performance
        role_stats = {}
        
        for player_name, player_data in analytics_data.get('players', {}).items():
            if hasattr(player_data, 'role_performance') and player_data.role_performance:
                for role, perf in player_data.role_performance.items():
                    if role not in role_stats:
                        role_stats[role] = {
                            'total_games': 0,
                            'total_wins': 0,
                            'players': []
                        }
                    
                    games = getattr(perf, 'games_played', 0)
                    wins = getattr(perf, 'wins', 0)
                    
                    role_stats[role]['total_games'] += games
                    role_stats[role]['total_wins'] += wins
                    role_stats[role]['players'].append(player_name)
        
        if not role_stats:
            print("No role performance data available")
            return
        
        print(f"\n🎭 Role Performance Summary:")
        for role in self.available_roles:
            if role in role_stats:
                stats = role_stats[role]
                win_rate = stats['total_wins'] / stats['total_games'] if stats['total_games'] > 0 else 0
                player_count = len(set(stats['players']))  # Unique players
                
                print(f"   {role.title()}: {win_rate:.1%} WR ({stats['total_games']} games, {player_count} players)")
            else:
                print(f"   {role.title()}: No data")
    
    def _show_performance_trends(self) -> None:
        """Show performance trends over time."""
        print("\n📈 Performance Trends")
        print("This feature would show performance trends over the selected time period")
        print("Implementation would require time-series analysis of match data")
    
    def _show_synergy_analysis(self) -> None:
        """Show team synergy analysis."""
        print("\n🤝 Synergy Analysis")
        print("This feature would analyze champion and player synergies")
        print("Implementation would use the synergy analyzer components")
    
    def _compare_champions(self) -> None:
        """Compare champion performance."""
        print("\n🏆 Champion Comparison")
        print("Select champions to compare (feature would be implemented with champion selection)")
    
    def _compare_roles(self) -> None:
        """Compare role performance."""
        print("\n🎭 Role Comparison")
        self._show_role_performance_analysis()
    
    def _compare_time_periods(self) -> None:
        """Compare performance across different time periods."""
        print("\n📅 Time Period Comparison")
        print("This feature would compare performance across different date ranges")
    
    def _change_comparison_mode(self) -> None:
        """Change the comparison mode."""
        print("\n🔧 Change Comparison Mode")
        print("1. Players")
        print("2. Champions") 
        print("3. Roles")
        print("4. Time Periods")
        
        choice = input("Select comparison mode: ").strip()
        
        modes = {"1": "players", "2": "champions", "3": "roles", "4": "time_periods"}
        if choice in modes:
            self.state.comparison_mode = modes[choice]
            print(f"✅ Comparison mode set to {modes[choice]}")
        else:
            print("❌ Invalid choice")
    
    def _drill_down_champion(self, analytics_data: Dict[str, Any]) -> None:
        """Drill down into champion analysis."""
        print("\n🏆 Champion Drill-Down")
        print("This would provide detailed champion analysis")
    
    def _drill_down_role(self, analytics_data: Dict[str, Any]) -> None:
        """Drill down into role analysis."""
        print("\n🎭 Role Drill-Down")
        self._show_role_performance_analysis()
    
    def _drill_down_time_period(self, analytics_data: Dict[str, Any]) -> None:
        """Drill down into time period analysis."""
        print("\n📅 Time Period Drill-Down")
        print("This would provide time-based performance analysis")
    
    def _export_performance_report(self) -> None:
        """Export comprehensive performance report."""
        print("\n📈 Exporting Performance Report...")
        
        try:
            analytics_data = self._get_filtered_analytics()
            
            if not analytics_data:
                print("No data to export")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.csv"
            
            # Prepare CSV data
            csv_data = []
            
            for player_name, player_data in analytics_data.get('players', {}).items():
                row = {
                    'Player': player_name,
                    'Games': getattr(player_data, 'games_played', 0),
                    'Wins': getattr(player_data, 'wins', 0),
                    'Win_Rate': getattr(player_data, 'win_rate', 0),
                    'Avg_KDA': getattr(player_data, 'avg_kda', 0),
                    'Avg_Damage': getattr(player_data, 'avg_damage', 0),
                    'Avg_Gold': getattr(player_data, 'avg_gold', 0)
                }
                csv_data.append(row)
            
            # Write CSV file
            if csv_data:
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = csv_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)
                
                print(f"✅ Performance report exported to {filename}")
            else:
                print("No data to export")
                
        except Exception as e:
            self.logger.error(f"Failed to export performance report: {e}")
            print(f"❌ Export failed: {e}")
    
    def _export_champion_analysis(self) -> None:
        """Export champion analysis data."""
        print("\n🏆 Exporting Champion Analysis...")
        print("Champion analysis export would be implemented here")
    
    def _export_player_comparison(self) -> None:
        """Export player comparison data."""
        print("\n👥 Exporting Player Comparison...")
        
        if len(self.state.selected_players) < 2:
            print("Please select at least 2 players for comparison export")
            return
        
        try:
            analytics_data = self._get_filtered_analytics()
            comparison_data = {
                name: data for name, data in analytics_data.get('players', {}).items()
                if name in self.state.selected_players
            }
            
            if len(comparison_data) < 2:
                print("Insufficient data for selected players")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"player_comparison_{timestamp}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'compared_players': list(self.state.selected_players),
                'comparison_data': {
                    name: {
                        'games_played': getattr(data, 'games_played', 0),
                        'win_rate': getattr(data, 'win_rate', 0),
                        'avg_kda': getattr(data, 'avg_kda', 0),
                        'avg_damage': getattr(data, 'avg_damage', 0),
                        'avg_gold': getattr(data, 'avg_gold', 0)
                    }
                    for name, data in comparison_data.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            print(f"✅ Player comparison exported to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to export player comparison: {e}")
            print(f"❌ Export failed: {e}")
    
    def _configure_export_settings(self) -> None:
        """Configure export settings."""
        print("\n🔧 Export Settings Configuration")
        print("1. Export Format (CSV, JSON, Excel)")
        print("2. Include Charts (Yes/No)")
        print("3. Include Raw Data (Yes/No)")
        print("4. Custom Output Path")
        
        print("\nCurrent settings would be displayed and configurable here")
    
    def _display_summary_trends(self, analytics_data: Dict[str, Any]) -> None:
        """Display summary trends from analytics data."""
        print(f"\n📈 Recent Trends:")
        print("   Trend analysis would show performance changes over time")
        print("   This requires time-series data processing")
    
    def _configure_champion_selection(self) -> None:
        """Configure champion selection filter."""
        print("\n🏆 Champion Selection")
        
        if not self.available_champions:
            print("No champions available")
            return
        
        print(f"Available champions: {len(self.available_champions)}")
        print("Champion selection interface would be implemented here")
        print("Due to the large number of champions, this would use search/filter functionality")
        
        # For now, just show current selection count
        if self.state.selected_champions:
            print(f"Currently selected: {len(self.state.selected_champions)} champions")
        else:
            print("Currently selected: All champions")
        
        print("\nOptions:")
        print("1. Clear champion selection (use all)")
        print("2. Select by role")
        print("3. Select by name pattern")
        
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            self.state.selected_champions.clear()
            print("✅ Champion selection cleared (using all champions)")
        elif choice == "2":
            print("Role-based champion selection would be implemented")
        elif choice == "3":
            print("Name pattern champion selection would be implemented")