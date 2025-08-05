#!/usr/bin/env python3
"""
Demo script for LoL Team Optimizer Gradio UI

This script creates a demo version of the interface with sample data
for testing and demonstration purposes.
"""

import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


class GradioDemo:
    """Demo version of the Gradio UI with sample data."""
    
    def __init__(self):
        """Initialize the demo with sample data."""
        self.sample_players = [
            "Alice (Summoner1)",
            "Bob (Summoner2)", 
            "Charlie (Summoner3)",
            "Diana (Summoner4)",
            "Eve (Summoner5)"
        ]
        
        self.sample_champions = [
            "Jinx", "Caitlyn", "Ezreal", "Vayne", "Kai'Sa",
            "Thresh", "Leona", "Lulu", "Morgana", "Blitzcrank",
            "Azir", "Yasuo", "Zed", "Orianna", "Syndra",
            "Gnar", "Camille", "Fiora", "Darius", "Renekton",
            "Graves", "Lee Sin", "Elise", "Nidalee", "Kha'Zix"
        ]
    
    def add_player_demo(self, name: str, summoner_name: str, riot_id: str, region: str) -> str:
        """Demo version of add player."""
        if not all([name, summoner_name, riot_id, region]):
            return "❌ All fields are required"
        
        return f"✅ Demo: Added player {name} ({summoner_name}) from {region}"
    
    def extract_matches_demo(self, player_selection: str, days: int, progress=gr.Progress()) -> str:
        """Demo version of match extraction."""
        if not player_selection:
            return "❌ No player selected"
        
        progress(0.1, desc="Starting demo extraction...")
        
        # Simulate extraction process
        import time
        for i in range(5):
            time.sleep(0.2)
            progress((i + 1) * 0.2, desc=f"Extracting matches... {i+1}/5")
        
        matches_found = random.randint(15, 45)
        return f"✅ Demo: Extracted {matches_found} matches for {player_selection}"
    
    def get_player_analytics_demo(self, player_selection: str, days: int) -> Tuple[str, Any, Any]:
        """Demo version of player analytics."""
        if not player_selection:
            return "❌ No player selected", None, None
        
        # Generate sample analytics summary
        win_rate = random.uniform(0.45, 0.75)
        games_played = random.randint(20, 60)
        avg_kda = random.uniform(1.5, 4.0)
        cs_per_min = random.uniform(5.5, 8.5)
        vision_score = random.uniform(15, 35)
        
        summary = f"""# 📊 Demo Analytics Report - {player_selection}
        
**Analysis Period:** {(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}

## 🎮 Overall Performance
- **Games Played:** {games_played}
- **Win Rate:** {win_rate:.1%}
- **Average KDA:** {avg_kda:.2f}
- **CS/Min:** {cs_per_min:.1f}
- **Vision Score:** {vision_score:.1f}

## 🏆 Top Champions
1. **{random.choice(self.sample_champions)}** (middle)
   - Win Rate: {random.uniform(0.6, 0.8):.1%} ({random.randint(8, 15)} games)
   - KDA: {random.uniform(2.0, 5.0):.2f}

2. **{random.choice(self.sample_champions)}** (bottom)
   - Win Rate: {random.uniform(0.5, 0.75):.1%} ({random.randint(6, 12)} games)
   - KDA: {random.uniform(1.8, 4.5):.2f}

3. **{random.choice(self.sample_champions)}** (support)
   - Win Rate: {random.uniform(0.55, 0.8):.1%} ({random.randint(5, 10)} games)
   - KDA: {random.uniform(1.5, 3.5):.2f}
"""
        
        # Create performance chart
        perf_chart = self.create_demo_performance_chart(win_rate, avg_kda, cs_per_min, vision_score)
        
        # Create champion chart
        champ_chart = self.create_demo_champion_chart()
        
        return summary, perf_chart, champ_chart
    
    def create_demo_performance_chart(self, win_rate: float, avg_kda: float, cs_per_min: float, vision_score: float) -> Any:
        """Create a demo performance radar chart."""
        categories = ['Win Rate', 'KDA', 'CS/Min', 'Vision Score', 'Damage/Min']
        values = [
            win_rate * 100,
            min(avg_kda * 20, 100),  # Scale KDA to 0-100
            min(cs_per_min * 12, 100),  # Scale CS to 0-100
            min(vision_score * 3, 100),  # Scale vision to 0-100
            random.uniform(60, 95)  # Random damage value
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
            title="Demo Performance Metrics Overview"
        )
        
        return fig
    
    def create_demo_champion_chart(self) -> Any:
        """Create a demo champion performance chart."""
        # Generate sample champion data
        champions = random.sample(self.sample_champions, 6)
        win_rates = [random.uniform(40, 85) for _ in champions]
        games_played = [random.randint(5, 20) for _ in champions]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=champions,
            y=win_rates,
            text=[f"{wr:.1f}% ({gp} games)" for wr, gp in zip(win_rates, games_played)],
            textposition='auto',
            marker_color='rgb(0, 123, 255)'
        ))
        
        fig.update_layout(
            title="Demo Champion Win Rates",
            xaxis_title="Champion",
            yaxis_title="Win Rate (%)",
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    def get_champion_recommendations_demo(self, player_selection: str, role: str) -> str:
        """Demo version of champion recommendations."""
        if not player_selection:
            return "❌ No player selected"
        
        # Generate sample recommendations
        recommended_champions = random.sample(self.sample_champions, 5)
        
        result = f"# 🎯 Demo Champion Recommendations - {role.title()}\n\n"
        
        for i, champion in enumerate(recommended_champions, 1):
            score = random.uniform(0.6, 0.95)
            confidence = random.uniform(0.7, 0.9)
            reasons = [
                "Strong historical performance with this champion",
                "Good synergy with your playstyle",
                "Currently strong in the meta",
                "High win rate in recent matches",
                "Excellent team composition fit"
            ]
            
            result += f"## {i}. {champion}\n"
            result += f"- **Recommendation Score:** {score:.1%}\n"
            result += f"- **Confidence:** {confidence:.1%}\n"
            result += f"- **Reason:** {random.choice(reasons)}\n\n"
        
        return result
    
    def analyze_team_composition_demo(self, *player_selections) -> str:
        """Demo version of team composition analysis."""
        # Filter out empty selections
        selected_players = [p for p in player_selections if p and p != "None"]
        
        if len(selected_players) < 2:
            return "❌ Please select at least 2 players"
        
        result = f"# 👥 Demo Team Composition Analysis\n\n"
        result += f"**Players:** {', '.join(selected_players)}\n\n"
        
        result += "## Individual Performance\n"
        total_wr = 0
        for player in selected_players:
            wr = random.uniform(0.45, 0.75)
            games = random.randint(15, 40)
            result += f"- **{player}:** {wr:.1%} WR ({games} games)\n"
            total_wr += wr
        
        avg_wr = total_wr / len(selected_players)
        result += f"\n**Team Average Win Rate:** {avg_wr:.1%}\n"
        
        # Add synergy analysis
        synergy_score = random.uniform(0.6, 0.9)
        result += f"**Team Synergy Score:** {synergy_score:.1%}\n\n"
        
        result += "## Recommendations\n"
        recommendations = [
            "Focus on early game objectives",
            "Prioritize vision control",
            "Practice team fight positioning",
            "Develop late game strategies",
            "Work on communication timing"
        ]
        
        for rec in random.sample(recommendations, 3):
            result += f"- {rec}\n"
        
        return result
    
    def create_interface(self):
        """Create the demo Gradio interface."""
        
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
        
        with gr.Blocks(css=css, title="LoL Team Optimizer Demo", theme=gr.themes.Soft()) as interface:
            
            # Header
            gr.Markdown("""
            # 🎮 League of Legends Team Optimizer - DEMO
            
            **Advanced Analytics & Team Optimization Platform - Demo Version**
            
            This is a demonstration version of the LoL Team Optimizer Gradio interface.
            All data shown is simulated for demonstration purposes.
            
            ⚠️ **Note**: This is a demo with sample data. For the full version with real data,
            set up your Riot API key and use the complete interface.
            """)
            
            with gr.Tabs():
                
                # Player Management Tab
                with gr.Tab("👥 Player Management"):
                    gr.Markdown("## Add New Player (Demo)")
                    
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
                    
                    add_player_btn = gr.Button("Add Player (Demo)", variant="primary")
                    add_player_result = gr.Markdown()
                    
                    add_player_btn.click(
                        fn=self.add_player_demo,
                        inputs=[player_name, summoner_name, riot_id, region],
                        outputs=add_player_result
                    )
                    
                    gr.Markdown("## Demo Players")
                    gr.Markdown("**Available Demo Players:**\n" + "\n".join([f"- {player}" for player in self.sample_players]))
                
                # Match Extraction Tab
                with gr.Tab("📥 Match Extraction"):
                    gr.Markdown("## Extract Match Data (Demo)")
                    
                    with gr.Row():
                        extract_player = gr.Dropdown(
                            choices=self.sample_players,
                            label="Select Player",
                            value=self.sample_players[0]
                        )
                        extract_days = gr.Slider(
                            minimum=1,
                            maximum=90,
                            value=30,
                            step=1,
                            label="Days to Extract"
                        )
                    
                    extract_btn = gr.Button("Extract Matches (Demo)", variant="primary")
                    extract_result = gr.Markdown()
                    
                    extract_btn.click(
                        fn=self.extract_matches_demo,
                        inputs=[extract_player, extract_days],
                        outputs=extract_result
                    )
                
                # Analytics Tab
                with gr.Tab("📊 Analytics"):
                    gr.Markdown("## Player Performance Analytics (Demo)")
                    
                    with gr.Row():
                        analytics_player = gr.Dropdown(
                            choices=self.sample_players,
                            label="Select Player",
                            value=self.sample_players[0]
                        )
                        analytics_days = gr.Slider(
                            minimum=7,
                            maximum=180,
                            value=60,
                            step=7,
                            label="Analysis Period (Days)"
                        )
                    
                    analyze_btn = gr.Button("Analyze Performance (Demo)", variant="primary")
                    
                    with gr.Row():
                        with gr.Column():
                            analytics_summary = gr.Markdown()
                        with gr.Column():
                            performance_chart = gr.Plot()
                    
                    champion_chart = gr.Plot()
                    
                    analyze_btn.click(
                        fn=self.get_player_analytics_demo,
                        inputs=[analytics_player, analytics_days],
                        outputs=[analytics_summary, performance_chart, champion_chart]
                    )
                
                # Champion Recommendations Tab
                with gr.Tab("🎯 Champion Recommendations"):
                    gr.Markdown("## Get Champion Recommendations (Demo)")
                    
                    with gr.Row():
                        rec_player = gr.Dropdown(
                            choices=self.sample_players,
                            label="Select Player",
                            value=self.sample_players[0]
                        )
                        rec_role = gr.Dropdown(
                            choices=["top", "jungle", "middle", "bottom", "support"],
                            label="Select Role",
                            value="middle"
                        )
                    
                    recommend_btn = gr.Button("Get Recommendations (Demo)", variant="primary")
                    recommendations_result = gr.Markdown()
                    
                    recommend_btn.click(
                        fn=self.get_champion_recommendations_demo,
                        inputs=[rec_player, rec_role],
                        outputs=recommendations_result
                    )
                
                # Team Composition Tab
                with gr.Tab("👥 Team Composition"):
                    gr.Markdown("## Analyze Team Composition (Demo)")
                    
                    with gr.Row():
                        with gr.Column():
                            team_player1 = gr.Dropdown(choices=self.sample_players, label="Player 1", value=self.sample_players[0])
                            team_player2 = gr.Dropdown(choices=self.sample_players, label="Player 2", value=self.sample_players[1])
                            team_player3 = gr.Dropdown(choices=self.sample_players, label="Player 3")
                        with gr.Column():
                            team_player4 = gr.Dropdown(choices=self.sample_players, label="Player 4")
                            team_player5 = gr.Dropdown(choices=self.sample_players, label="Player 5")
                    
                    analyze_team_btn = gr.Button("Analyze Team (Demo)", variant="primary")
                    team_analysis_result = gr.Markdown()
                    
                    analyze_team_btn.click(
                        fn=self.analyze_team_composition_demo,
                        inputs=[team_player1, team_player2, team_player3, team_player4, team_player5],
                        outputs=team_analysis_result
                    )
            
            # Footer
            gr.Markdown("""
            ---
            
            **LoL Team Optimizer Demo** - Advanced Analytics Platform
            
            This demo showcases the interface and features with simulated data.
            For the full version with real Riot API integration, use the complete application.
            
            🚀 **Ready to use the real version?** Set up your Riot API key and launch the full interface!
            """)
        
        return interface


def launch_demo(share: bool = False, server_port: int = 7861):
    """Launch the demo interface."""
    try:
        demo = GradioDemo()
        interface = demo.create_interface()
        
        print("🎮 Launching LoL Team Optimizer Demo...")
        print(f"📱 Demo interface will be available at: http://localhost:{server_port}")
        print("⚠️  Note: This is a demo with simulated data")
        
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
        print(f"❌ Failed to launch demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Launch demo with sharing enabled
    launch_demo(share=True)