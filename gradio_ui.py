#!/usr/bin/env python3
"""
Gradio Web UI for LoL Team Optimizer

This module provides a modern web interface for the League of Legends Team Optimizer
using Gradio. It includes all major features: player management, match extraction,
analytics, and team optimization.
"""

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import sys
import os

# Add the lol_team_optimizer to the path
sys.path.append('lol_team_optimizer')

try:
    from lol_team_optimizer.core_engine import CoreEngine
    from lol_team_optimizer.models import Player
    from lol_team_optimizer.analytics_models import AnalyticsFilters, DateRange
    from lol_team_optimizer.config import get_config
except ImportError as e:
    print(f"Warning: Could not import LoL Team Optimizer modules: {e}")
    print("Make sure you're running this from the correct directory")


class GradioUI:
    """Main Gradio UI class for LoL Team Optimizer."""
    
    def __init__(self):
        """Initialize the Gradio UI."""
        self.engine = None
        self.players = []
        self.current_player = None
        self.initialize_engine()
    
    def initialize_engine(self):
        """Initialize the core engine."""
        try:
            self.engine = CoreEngine()
            self.refresh_players()
            return "✅ Engine initialized successfully"
        except Exception as e:
            return f"❌ Failed to initialize engine: {str(e)}"
    
    def refresh_players(self):
        """Refresh the player list."""
        try:
            if self.engine:
                self.players = self.engine.data_manager.load_player_data()
            return [f"{p.name} ({p.summoner_name})" for p in self.players]
        except Exception as e:
            print(f"Error refreshing players: {e}")
            return []
    
    def get_player_choices(self):
        """Get player choices for dropdowns."""
        return [f"{p.name} ({p.summoner_name})" for p in self.players]
    
    def add_player(self, name: str, summoner_name: str, riot_id: str, region: str) -> str:
        """Add a new player."""
        try:
            if not all([name, summoner_name, riot_id, region]):
                return "❌ All fields are required"
            
            # Create new player
            player = Player(
                name=name,
                summoner_name=summoner_name,
                puuid="",  # Will be filled during extraction
                riot_id=riot_id,
                region=region
            )
            
            # Add to engine
            self.engine.data_manager.add_player(player)
            self.refresh_players()
            
            return f"✅ Added player: {name} ({summoner_name})"
            
        except Exception as e:
            return f"❌ Error adding player: {str(e)}"
    
    def extract_matches(self, player_selection: str, days: int, progress=gr.Progress()) -> str:
        """Extract matches for a player."""
        try:
            if not player_selection or not self.players:
                return "❌ No player selected or no players available"
            
            # Find selected player
            player_idx = self.get_player_choices().index(player_selection)
            player = self.players[player_idx]
            
            progress(0.1, desc="Starting match extraction...")
            
            # Extract matches
            result = self.engine.extract_player_matches(
                player.summoner_name,
                player.riot_id,
                days_back=days
            )
            
            progress(1.0, desc="Extraction complete!")
            
            if result.get('success'):
                matches_found = result.get('matches_extracted', 0)
                return f"✅ Extracted {matches_found} matches for {player.name}"
            else:
                return f"❌ Extraction failed: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            return f"❌ Error during extraction: {str(e)}"
    
    def get_player_analytics(self, player_selection: str, days: int) -> Tuple[str, Any, Any]:
        """Get analytics for a player."""
        try:
            if not player_selection or not self.players:
                return "❌ No player selected", None, None
            
            # Find selected player
            player_idx = self.get_player_choices().index(player_selection)
            player = self.players[player_idx]
            
            if not self.engine.analytics_available:
                return "❌ Analytics not available", None, None
            
            # Create filters
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date),
                min_games=1
            )
            
            # Get analytics
            analytics = self.engine.historical_analytics_engine.analyze_player_performance(
                player.puuid, filters
            )
            
            # Create summary text
            summary = self.format_analytics_summary(analytics, player.name)
            
            # Create performance chart
            perf_chart = self.create_performance_chart(analytics)
            
            # Create champion performance chart
            champ_chart = self.create_champion_chart(analytics)
            
            return summary, perf_chart, champ_chart
            
        except Exception as e:
            error_msg = f"❌ Error getting analytics: {str(e)}"
            return error_msg, None, None
    
    def format_analytics_summary(self, analytics, player_name: str) -> str:
        """Format analytics into a readable summary."""
        try:
            summary = f"# 📊 Analytics Report - {player_name}\n\n"
            
            if hasattr(analytics, 'analysis_period') and analytics.analysis_period:
                start = analytics.analysis_period.start_date.strftime('%Y-%m-%d')
                end = analytics.analysis_period.end_date.strftime('%Y-%m-%d')
                summary += f"**Analysis Period:** {start} to {end}\n\n"
            
            # Overall performance
            if hasattr(analytics, 'overall_performance') and analytics.overall_performance:
                perf = analytics.overall_performance
                summary += f"## 🎮 Overall Performance\n"
                summary += f"- **Games Played:** {perf.games_played}\n"
                summary += f"- **Win Rate:** {perf.win_rate:.1%}\n"
                summary += f"- **Average KDA:** {perf.avg_kda:.2f}\n"
                summary += f"- **CS/Min:** {perf.avg_cs_per_min:.1f}\n"
                summary += f"- **Vision Score:** {perf.avg_vision_score:.1f}\n\n"
            
            # Champion performance
            if hasattr(analytics, 'champion_performance') and analytics.champion_performance:
                summary += f"## 🏆 Top Champions\n"
                sorted_champs = sorted(
                    analytics.champion_performance.items(),
                    key=lambda x: x[1].performance.win_rate,
                    reverse=True
                )[:5]
                
                for i, (champ_id, champ_perf) in enumerate(sorted_champs, 1):
                    perf = champ_perf.performance
                    summary += f"{i}. **{champ_perf.champion_name}** ({champ_perf.role})\n"
                    summary += f"   - Win Rate: {perf.win_rate:.1%} ({perf.games_played} games)\n"
                    summary += f"   - KDA: {perf.avg_kda:.2f}\n\n"
            
            return summary
            
        except Exception as e:
            return f"❌ Error formatting summary: {str(e)}"
    
    def create_performance_chart(self, analytics) -> Any:
        """Create a performance metrics chart."""
        try:
            if not hasattr(analytics, 'overall_performance') or not analytics.overall_performance:
                return None
            
            perf = analytics.overall_performance
            
            # Create radar chart for performance metrics
            categories = ['Win Rate', 'KDA', 'CS/Min', 'Vision Score', 'Damage/Min']
            values = [
                perf.win_rate * 100,
                min(perf.avg_kda * 10, 100),  # Scale KDA to 0-100
                min(perf.avg_cs_per_min * 10, 100),  # Scale CS to 0-100
                min(perf.avg_vision_score * 2, 100),  # Scale vision to 0-100
                min(perf.avg_damage_per_min / 10, 100)  # Scale damage to 0-100
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='Performance',
                line_color='rgb(0, 123, 255)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=False,
                title="Performance Metrics Overview"
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating performance chart: {e}")
            return None
    
    def create_champion_chart(self, analytics) -> Any:
        """Create a champion performance chart."""
        try:
            if not hasattr(analytics, 'champion_performance') or not analytics.champion_performance:
                return None
            
            # Prepare data for chart
            champions = []
            win_rates = []
            games_played = []
            
            for champ_id, champ_perf in analytics.champion_performance.items():
                if champ_perf.performance.games_played >= 3:  # Only show champions with 3+ games
                    champions.append(champ_perf.champion_name)
                    win_rates.append(champ_perf.performance.win_rate * 100)
                    games_played.append(champ_perf.performance.games_played)
            
            if not champions:
                return None
            
            # Create bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=champions,
                y=win_rates,
                text=[f"{wr:.1f}% ({gp} games)" for wr, gp in zip(win_rates, games_played)],
                textposition='auto',
                marker_color='rgb(0, 123, 255)'
            ))
            
            fig.update_layout(
                title="Champion Win Rates",
                xaxis_title="Champion",
                yaxis_title="Win Rate (%)",
                yaxis=dict(range=[0, 100])
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating champion chart: {e}")
            return None
    
    def get_champion_recommendations(self, player_selection: str, role: str) -> str:
        """Get champion recommendations for a player and role."""
        try:
            if not player_selection or not self.players:
                return "❌ No player selected"
            
            if not self.engine.analytics_available:
                return "❌ Analytics not available"
            
            # Find selected player
            player_idx = self.get_player_choices().index(player_selection)
            player = self.players[player_idx]
            
            # Get recommendations
            recommendations = self.engine.champion_recommendation_engine.get_champion_recommendations(
                player.puuid, role, limit=5
            )
            
            if not recommendations:
                return f"❌ No recommendations available for {role}"
            
            # Format recommendations
            result = f"# 🎯 Champion Recommendations - {role.title()}\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                result += f"## {i}. {rec.champion_name}\n"
                result += f"- **Recommendation Score:** {rec.recommendation_score:.1%}\n"
                result += f"- **Confidence:** {rec.confidence:.1%}\n"
                if hasattr(rec, 'reasoning') and rec.reasoning:
                    result += f"- **Reason:** {rec.reasoning.primary_reason}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error getting recommendations: {str(e)}"
    
    def analyze_team_composition(self, *player_selections) -> str:
        """Analyze team composition."""
        try:
            if not self.engine.analytics_available:
                return "❌ Analytics not available"
            
            # Filter out empty selections
            selected_players = [p for p in player_selections if p and p != "None"]
            
            if len(selected_players) < 2:
                return "❌ Please select at least 2 players"
            
            # Get player PUUIDs
            puuids = []
            player_names = []
            
            for selection in selected_players:
                if selection in self.get_player_choices():
                    player_idx = self.get_player_choices().index(selection)
                    player = self.players[player_idx]
                    puuids.append(player.puuid)
                    player_names.append(player.name)
            
            if len(puuids) < 2:
                return "❌ Could not find selected players"
            
            # Analyze team composition (simplified)
            result = f"# 👥 Team Composition Analysis\n\n"
            result += f"**Players:** {', '.join(player_names)}\n\n"
            
            # Get individual analytics for each player
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date),
                min_games=1
            )
            
            total_games = 0
            total_wins = 0
            
            result += "## Individual Performance\n"
            for puuid, name in zip(puuids, player_names):
                try:
                    analytics = self.engine.historical_analytics_engine.analyze_player_performance(
                        puuid, filters
                    )
                    
                    if analytics and analytics.overall_performance:
                        perf = analytics.overall_performance
                        result += f"- **{name}:** {perf.win_rate:.1%} WR ({perf.games_played} games)\n"
                        total_games += perf.games_played
                        total_wins += perf.wins
                except:
                    result += f"- **{name}:** No data available\n"
            
            if total_games > 0:
                team_wr = total_wins / total_games
                result += f"\n**Combined Win Rate:** {team_wr:.1%} ({total_games} total games)\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error analyzing team composition: {str(e)}"
    
    def create_interface(self):
        """Create the main Gradio interface."""
        
        # Custom CSS for better styling
        css = """
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .tab-nav {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        }
        .tab-nav button {
            color: white !important;
        }
        .tab-nav button.selected {
            background: rgba(255, 255, 255, 0.2) !important;
        }
        """
        
        with gr.Blocks(css=css, title="LoL Team Optimizer", theme=gr.themes.Soft()) as interface:
            
            # Header
            gr.Markdown("""
            # 🎮 League of Legends Team Optimizer
            
            **Advanced Analytics & Team Optimization Platform**
            
            Welcome to the comprehensive LoL Team Optimizer! This tool provides advanced analytics,
            champion recommendations, and team composition analysis to help you improve your gameplay.
            """)
            
            # Status display
            status_display = gr.Markdown("🔄 Initializing...")
            
            # Initialize engine on load
            interface.load(
                fn=self.initialize_engine,
                outputs=status_display
            )
            
            with gr.Tabs():
                
                # Player Management Tab
                with gr.Tab("👥 Player Management"):
                    gr.Markdown("## Add New Player")
                    
                    with gr.Row():
                        with gr.Column():
                            player_name = gr.Textbox(label="Player Name", placeholder="Enter player name")
                            summoner_name = gr.Textbox(label="Summoner Name", placeholder="Enter summoner name")
                        with gr.Column():
                            riot_id = gr.Textbox(label="Riot ID", placeholder="PlayerName#TAG")
                            region = gr.Dropdown(
                                choices=["na1", "euw1", "eun1", "kr", "br1", "la1", "la2", "oc1", "tr1", "ru", "jp1"],
                                label="Region",
                                value="na1"
                            )
                    
                    add_player_btn = gr.Button("Add Player", variant="primary")
                    add_player_result = gr.Markdown()
                    
                    add_player_btn.click(
                        fn=self.add_player,
                        inputs=[player_name, summoner_name, riot_id, region],
                        outputs=add_player_result
                    )
                    
                    gr.Markdown("## Current Players")
                    player_list = gr.Markdown("Loading players...")
                    
                    refresh_players_btn = gr.Button("Refresh Player List")
                    refresh_players_btn.click(
                        fn=lambda: f"**Current Players:**\n" + "\n".join([f"- {choice}" for choice in self.get_player_choices()]),
                        outputs=player_list
                    )
                
                # Match Extraction Tab
                with gr.Tab("📥 Match Extraction"):
                    gr.Markdown("## Extract Match Data")
                    
                    with gr.Row():
                        extract_player = gr.Dropdown(
                            choices=self.get_player_choices(),
                            label="Select Player",
                            interactive=True
                        )
                        extract_days = gr.Slider(
                            minimum=1,
                            maximum=90,
                            value=30,
                            step=1,
                            label="Days to Extract"
                        )
                    
                    extract_btn = gr.Button("Extract Matches", variant="primary")
                    extract_result = gr.Markdown()
                    
                    extract_btn.click(
                        fn=self.extract_matches,
                        inputs=[extract_player, extract_days],
                        outputs=extract_result
                    )
                    
                    # Refresh player choices when tab is selected
                    interface.load(
                        fn=self.get_player_choices,
                        outputs=extract_player
                    )
                
                # Analytics Tab
                with gr.Tab("📊 Analytics"):
                    gr.Markdown("## Player Performance Analytics")
                    
                    with gr.Row():
                        analytics_player = gr.Dropdown(
                            choices=self.get_player_choices(),
                            label="Select Player",
                            interactive=True
                        )
                        analytics_days = gr.Slider(
                            minimum=7,
                            maximum=180,
                            value=60,
                            step=7,
                            label="Analysis Period (Days)"
                        )
                    
                    analyze_btn = gr.Button("Analyze Performance", variant="primary")
                    
                    with gr.Row():
                        with gr.Column():
                            analytics_summary = gr.Markdown()
                        with gr.Column():
                            performance_chart = gr.Plot()
                    
                    champion_chart = gr.Plot()
                    
                    analyze_btn.click(
                        fn=self.get_player_analytics,
                        inputs=[analytics_player, analytics_days],
                        outputs=[analytics_summary, performance_chart, champion_chart]
                    )
                    
                    # Refresh player choices
                    interface.load(
                        fn=self.get_player_choices,
                        outputs=analytics_player
                    )
                
                # Champion Recommendations Tab
                with gr.Tab("🎯 Champion Recommendations"):
                    gr.Markdown("## Get Champion Recommendations")
                    
                    with gr.Row():
                        rec_player = gr.Dropdown(
                            choices=self.get_player_choices(),
                            label="Select Player",
                            interactive=True
                        )
                        rec_role = gr.Dropdown(
                            choices=["top", "jungle", "middle", "bottom", "support"],
                            label="Select Role",
                            value="middle"
                        )
                    
                    recommend_btn = gr.Button("Get Recommendations", variant="primary")
                    recommendations_result = gr.Markdown()
                    
                    recommend_btn.click(
                        fn=self.get_champion_recommendations,
                        inputs=[rec_player, rec_role],
                        outputs=recommendations_result
                    )
                    
                    # Refresh player choices
                    interface.load(
                        fn=self.get_player_choices,
                        outputs=rec_player
                    )
                
                # Team Composition Tab
                with gr.Tab("👥 Team Composition"):
                    gr.Markdown("## Analyze Team Composition")
                    
                    with gr.Row():
                        with gr.Column():
                            team_player1 = gr.Dropdown(choices=self.get_player_choices(), label="Player 1")
                            team_player2 = gr.Dropdown(choices=self.get_player_choices(), label="Player 2")
                            team_player3 = gr.Dropdown(choices=self.get_player_choices(), label="Player 3")
                        with gr.Column():
                            team_player4 = gr.Dropdown(choices=self.get_player_choices(), label="Player 4")
                            team_player5 = gr.Dropdown(choices=self.get_player_choices(), label="Player 5")
                    
                    analyze_team_btn = gr.Button("Analyze Team", variant="primary")
                    team_analysis_result = gr.Markdown()
                    
                    analyze_team_btn.click(
                        fn=self.analyze_team_composition,
                        inputs=[team_player1, team_player2, team_player3, team_player4, team_player5],
                        outputs=team_analysis_result
                    )
                    
                    # Refresh all player dropdowns
                    def refresh_team_dropdowns():
                        choices = self.get_player_choices()
                        return [gr.Dropdown.update(choices=choices) for _ in range(5)]
                    
                    interface.load(
                        fn=refresh_team_dropdowns,
                        outputs=[team_player1, team_player2, team_player3, team_player4, team_player5]
                    )
            
            # Footer
            gr.Markdown("""
            ---
            
            **LoL Team Optimizer** - Advanced Analytics Platform
            
            For support or questions, check the documentation or contact the development team.
            """)
        
        return interface


def launch_ui(share: bool = False, server_port: int = 7860):
    """Launch the Gradio UI."""
    try:
        ui = GradioUI()
        interface = ui.create_interface()
        
        print("🚀 Launching LoL Team Optimizer UI...")
        print(f"📱 Interface will be available at: http://localhost:{server_port}")
        
        if share:
            print("🌐 Public sharing enabled - you'll get a public URL")
        
        interface.launch(
            share=share,
            server_port=server_port,
            server_name="0.0.0.0" if share else "127.0.0.1",
            show_error=True,
            quiet=False
        )
        
    except Exception as e:
        print(f"❌ Failed to launch UI: {e}")
        traceback.print_exc()


# Export the main classes and functions for import
__all__ = ['GradioUI', 'launch_ui']


if __name__ == "__main__":
    # Launch with sharing enabled for Colab compatibility
    launch_ui(share=True)