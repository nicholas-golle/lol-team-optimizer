#!/usr/bin/env python3
"""
Gradio Web Interface Demo for Advanced Player Validation

This demo shows how the advanced player validator integrates with the Gradio web interface
to provide real-time validation, data quality assessment, and automatic data refresh.
"""

import asyncio
import gradio as gr
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

from lol_team_optimizer.advanced_player_validator import (
    AdvancedPlayerValidator,
    ValidationStatus,
    DataQualityLevel
)
from lol_team_optimizer.models import Player, ChampionMastery
from lol_team_optimizer.config import Config
from lol_team_optimizer.riot_client import RiotAPIClient


class GradioValidationInterface:
    """Gradio interface for player validation and data quality management."""
    
    def __init__(self):
        """Initialize the validation interface."""
        self.config = Config()
        self.config.riot_api_key = "DEMO_KEY"  # In real use, load from environment
        self.config.cache_directory = "cache"
        
        # For demo purposes, we'll use a mock client
        # In production, use: self.riot_client = RiotAPIClient(self.config)
        self.riot_client = self._create_demo_client()
        self.validator = AdvancedPlayerValidator(self.config, self.riot_client)
        
        # Demo players
        self.demo_players = self._create_demo_players()
    
    def _create_demo_client(self):
        """Create a demo Riot API client with mock responses."""
        from unittest.mock import Mock
        
        client = Mock()
        client.logger = Mock()
        
        # Mock responses for demo
        client.get_summoner_data.return_value = {
            'puuid': 'demo_puuid_12345',
            'id': 'demo_summoner_id',
            'summonerLevel': 150,
            'name': 'DemoPlayer',
            'tagLine': 'NA1'
        }
        
        client.get_ranked_stats.return_value = [
            {
                'queueType': 'RANKED_SOLO_5x5',
                'tier': 'DIAMOND',
                'rank': 'III',
                'leaguePoints': 45,
                'wins': 67,
                'losses': 43
            }
        ]
        
        client.get_champion_mastery_score.return_value = 125000
        
        client.get_all_champion_masteries.return_value = [
            {
                'championId': 1,
                'championLevel': 7,
                'championPoints': 45000,
                'chestGranted': True,
                'tokensEarned': 0,
                'lastPlayTime': int(datetime.now().timestamp() * 1000)
            },
            {
                'championId': 2,
                'championLevel': 6,
                'championPoints': 32000,
                'chestGranted': False,
                'tokensEarned': 2,
                'lastPlayTime': int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
            }
        ]
        
        return client
    
    def _create_demo_players(self) -> List[Player]:
        """Create demo players with different data quality levels."""
        return [
            # Excellent quality player
            Player(
                name="ExcellentPlayer",
                summoner_name="ExcellentPlayer#NA1",
                puuid="excellent_puuid_123",
                role_preferences={
                    "top": 4, "jungle": 2, "middle": 5, "bottom": 3, "support": 1
                },
                champion_masteries={
                    1: ChampionMastery(champion_id=1, mastery_level=7, mastery_points=50000),
                    2: ChampionMastery(champion_id=2, mastery_level=6, mastery_points=30000)
                },
                performance_cache={
                    'middle': {'matches_played': 20, 'win_rate': 0.65, 'avg_kda': 2.5}
                },
                last_updated=datetime.now()
            ),
            
            # Good quality player
            Player(
                name="GoodPlayer",
                summoner_name="GoodPlayer#NA1",
                puuid="good_puuid_456",
                role_preferences={
                    "top": 3, "jungle": 4, "middle": 2, "bottom": 1, "support": 5
                },
                last_updated=datetime.now() - timedelta(days=2)
            ),
            
            # Poor quality player
            Player(
                name="PoorPlayer",
                summoner_name="",  # Missing summoner name
                puuid="",  # Missing PUUID
                role_preferences={},  # Missing role preferences
                last_updated=datetime.now() - timedelta(days=30)
            ),
            
            # Outdated player
            Player(
                name="OutdatedPlayer",
                summoner_name="OutdatedPlayer#NA1",
                puuid="outdated_puuid_789",
                role_preferences={
                    "top": 2, "jungle": 3, "middle": 4, "bottom": 5, "support": 1
                },
                last_updated=datetime.now() - timedelta(days=15)
            )
        ]
    
    async def validate_summoner_async(self, summoner_name: str, tag_line: str) -> Dict[str, Any]:
        """Validate a summoner name asynchronously."""
        if not summoner_name or not tag_line:
            return {
                'status': 'error',
                'message': 'Please provide both summoner name and tag line',
                'details': {}
            }
        
        try:
            result = await self.validator.validate_summoner_real_time(summoner_name, tag_line)
            
            return {
                'status': result.status.value,
                'is_valid': result.is_valid,
                'message': result.message,
                'details': result.details,
                'suggestions': result.suggestions,
                'error_code': result.error_code
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Validation failed: {str(e)}',
                'details': {}
            }
    
    def validate_summoner(self, summoner_name: str, tag_line: str) -> str:
        """Gradio wrapper for summoner validation."""
        result = asyncio.run(self.validate_summoner_async(summoner_name, tag_line))
        
        # Format result for display
        if result['is_valid']:
            details = result.get('details', {})
            return f"""
✅ **Validation Successful**

**Summoner:** {summoner_name}#{tag_line}
**Status:** {result['status'].upper()}
**Message:** {result['message']}

**Details:**
- PUUID: {details.get('puuid', 'N/A')}
- Summoner Level: {details.get('summoner_level', 'N/A')}
- Mastery Score: {details.get('mastery_score', 'N/A')}
- Rank Data: {'Available' if details.get('rank_data') else 'Not Available'}
"""
        else:
            suggestions_text = ""
            if result.get('suggestions'):
                suggestions_text = "\\n**Suggestions:**\\n" + "\\n".join(f"- {s}" for s in result['suggestions'])
            
            return f"""
❌ **Validation Failed**

**Summoner:** {summoner_name}#{tag_line}
**Status:** {result['status'].upper()}
**Message:** {result['message']}
**Error Code:** {result.get('error_code', 'N/A')}

{suggestions_text}
"""
    
    def get_data_quality_report(self) -> str:
        """Generate a data quality report for all demo players."""
        report = self.validator.create_validation_report(self.demo_players)
        
        # Format report for display
        output = f"""
# 📊 Data Quality Report

**Generated:** {report['report_timestamp']}
**Total Players:** {report['total_players']}

## Summary
- **Players with PUUID:** {report['summary']['players_with_puuid']}
- **Players with Mastery Data:** {report['summary']['players_with_mastery_data']}

## Quality Distribution
"""
        
        for level, count in report['summary']['quality_distribution'].items():
            if count > 0:
                emoji = {
                    'excellent': '🟢',
                    'good': '🔵', 
                    'fair': '🟡',
                    'poor': '🟠',
                    'critical': '🔴'
                }.get(level, '⚪')
                output += f"- {emoji} **{level.title()}:** {count} players\\n"
        
        output += "\\n## Player Details\\n"
        
        for player_detail in report['player_details']:
            quality = player_detail['data_quality']
            emoji = {
                'excellent': '🟢',
                'good': '🔵', 
                'fair': '🟡',
                'poor': '🟠',
                'critical': '🔴'
            }.get(quality['quality_level'], '⚪')
            
            output += f"""
### {emoji} {player_detail['name']}
- **Quality Score:** {quality['overall_score']:.1f}/100
- **Quality Level:** {quality['quality_level'].title()}
- **PUUID:** {'✅' if player_detail['puuid'] else '❌'}
- **Champion Masteries:** {player_detail['champion_masteries_count']}
- **Last Updated:** {player_detail['last_updated'] or 'Never'}

**Component Scores:**
- Basic Info: {quality['component_scores']['basic_info']:.1f}
- API Validation: {quality['component_scores']['api_validation']:.1f}
- Mastery Data: {quality['component_scores']['mastery_data']:.1f}
- Performance Data: {quality['component_scores']['performance_data']:.1f}
- Recency: {quality['component_scores']['recency']:.1f}
"""
            
            if quality['issues']:
                output += f"**Issues:** {', '.join(quality['issues'])}\\n"
            
            if quality['suggestions']:
                output += f"**Suggestions:** {', '.join(quality['suggestions'][:2])}\\n"
        
        # Add recommendations
        if report['refresh_recommendations']:
            output += "\\n## 🔄 Refresh Recommendations\\n"
            for rec in report['refresh_recommendations'][:5]:  # Top 5
                priority_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(rec['priority'], '⚪')
                output += f"- {priority_emoji} **{rec['player_name']}** ({rec['priority']} priority): {rec['reason']}\\n"
        
        return output
    
    async def refresh_player_data_async(self, player_name: str) -> Dict[str, Any]:
        """Refresh data for a specific player."""
        # Find the player
        player = next((p for p in self.demo_players if p.name == player_name), None)
        if not player:
            return {
                'success': False,
                'message': f'Player "{player_name}" not found'
            }
        
        try:
            refresh_results = await self.validator.refresh_player_data(player)
            return {
                'success': True,
                'results': refresh_results
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Refresh failed: {str(e)}'
            }
    
    def refresh_player_data(self, player_name: str) -> str:
        """Gradio wrapper for player data refresh."""
        if not player_name:
            return "❌ Please select a player to refresh."
        
        result = asyncio.run(self.refresh_player_data_async(player_name))
        
        if not result['success']:
            return f"❌ **Refresh Failed**\\n\\n{result['message']}"
        
        refresh_data = result['results']
        
        output = f"""
✅ **Data Refresh Completed**

**Player:** {refresh_data['player_name']}
**Refresh Time:** {refresh_data['refresh_timestamp']}

**Operations Performed:**
{chr(10).join(f'- {op}' for op in refresh_data['operations_performed'])}

**Quality Improvement:**
- Before: {refresh_data['data_quality_before'].overall_score:.1f}/100 ({refresh_data['data_quality_before'].quality_level.value})
- After: {refresh_data['data_quality_after'].overall_score:.1f}/100 ({refresh_data['data_quality_after'].quality_level.value})
- Improvement: {refresh_data.get('quality_improvement', 0):.1f} points
"""
        
        if refresh_data['errors']:
            output += f"\\n**Errors:**\\n{chr(10).join(f'- {error}' for error in refresh_data['errors'])}"
        
        return output
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        with gr.Blocks(
            title="Advanced Player Validation Demo",
            theme=gr.themes.Soft(),
            css="""
            .quality-excellent { background-color: #d4edda !important; }
            .quality-good { background-color: #cce5ff !important; }
            .quality-fair { background-color: #fff3cd !important; }
            .quality-poor { background-color: #f8d7da !important; }
            .quality-critical { background-color: #f5c6cb !important; }
            """
        ) as interface:
            
            gr.Markdown("""
            # 🎮 Advanced Player Validation Demo
            
            This demo showcases the advanced player data validation and API integration features
            for the League of Legends Team Optimizer web interface.
            
            ## Features Demonstrated:
            - ✅ Real-time summoner name validation with Riot API
            - 🏆 Champion mastery data integration and display  
            - 📊 Data quality indicators and completeness scoring
            - 🔄 Automatic data refresh and update notifications
            - ⚠️ Error handling for API failures with fallback options
            """)
            
            with gr.Tab("🔍 Real-time Validation"):
                gr.Markdown("### Validate Summoner Names")
                
                with gr.Row():
                    summoner_input = gr.Textbox(
                        label="Summoner Name",
                        placeholder="Enter summoner name (e.g., TestPlayer)",
                        value="TestPlayer"
                    )
                    tag_input = gr.Textbox(
                        label="Tag Line", 
                        placeholder="Enter tag (e.g., NA1)",
                        value="NA1"
                    )
                
                validate_btn = gr.Button("🔍 Validate Summoner", variant="primary")
                validation_output = gr.Markdown()
                
                validate_btn.click(
                    fn=self.validate_summoner,
                    inputs=[summoner_input, tag_input],
                    outputs=validation_output
                )
                
                # Example buttons
                gr.Markdown("### Quick Examples:")
                with gr.Row():
                    gr.Button("Valid Player").click(
                        lambda: ("TestPlayer", "NA1"),
                        outputs=[summoner_input, tag_input]
                    )
                    gr.Button("Invalid Player").click(
                        lambda: ("NotFoundPlayer", "NA1"),
                        outputs=[summoner_input, tag_input]
                    )
            
            with gr.Tab("📊 Data Quality Assessment"):
                gr.Markdown("### Player Data Quality Report")
                
                quality_btn = gr.Button("📊 Generate Quality Report", variant="primary")
                quality_output = gr.Markdown()
                
                quality_btn.click(
                    fn=self.get_data_quality_report,
                    outputs=quality_output
                )
                
                # Auto-generate on load
                interface.load(
                    fn=self.get_data_quality_report,
                    outputs=quality_output
                )
            
            with gr.Tab("🔄 Data Refresh"):
                gr.Markdown("### Refresh Player Data")
                
                player_dropdown = gr.Dropdown(
                    choices=[p.name for p in self.demo_players],
                    label="Select Player to Refresh",
                    value=self.demo_players[0].name if self.demo_players else None
                )
                
                refresh_btn = gr.Button("🔄 Refresh Player Data", variant="primary")
                refresh_output = gr.Markdown()
                
                refresh_btn.click(
                    fn=self.refresh_player_data,
                    inputs=player_dropdown,
                    outputs=refresh_output
                )
            
            with gr.Tab("ℹ️ About"):
                gr.Markdown("""
                ## About This Demo
                
                This demonstration shows how the Advanced Player Validator integrates with the Gradio web interface
                to provide comprehensive player data validation and quality management.
                
                ### Key Components:
                
                1. **Real-time Validation**: Validates summoner names against the Riot API with caching and error handling
                2. **Data Quality Scoring**: Comprehensive scoring system that evaluates player data completeness and accuracy
                3. **Automatic Refresh**: Smart data refresh recommendations based on data age and quality
                4. **Error Handling**: Robust error handling with fallback options and user-friendly messages
                
                ### Data Quality Levels:
                - 🟢 **Excellent** (90-100%): Complete, recent, validated data
                - 🔵 **Good** (70-89%): Mostly complete with minor gaps
                - 🟡 **Fair** (50-69%): Adequate but missing some components
                - 🟠 **Poor** (30-49%): Significant data quality issues
                - 🔴 **Critical** (0-29%): Major data problems requiring immediate attention
                
                ### Integration Benefits:
                - Improved user experience with real-time feedback
                - Automated data quality management
                - Reduced manual data entry errors
                - Better team optimization recommendations
                """)
        
        return interface


def main():
    """Launch the Gradio demo interface."""
    print("🚀 Starting Advanced Player Validation Demo...")
    
    # Create the interface
    demo_interface = GradioValidationInterface()
    interface = demo_interface.create_interface()
    
    # Launch the interface
    print("🌐 Launching Gradio interface...")
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()