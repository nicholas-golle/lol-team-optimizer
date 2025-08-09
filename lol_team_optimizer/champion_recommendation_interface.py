"""
Intelligent Champion Recommendation Interface for Gradio Web Interface

This module provides an advanced champion recommendation interface with
drag-and-drop team composition building, real-time updates, detailed
reasoning, confidence scoring, and alternative strategies.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
import json

import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .core_engine import CoreEngine
from .champion_recommendation_engine import ChampionRecommendationEngine
from .analytics_models import TeamContext, PlayerRoleAssignment, ChampionRecommendation
from .models import Player
from .champion_data import ChampionDataManager
from .gradio_components import ComponentConfig, ValidationComponents


@dataclass
class RecommendationSession:
    """Manages a recommendation session state."""
    
    session_id: str
    team_composition: Dict[str, Optional[PlayerRoleAssignment]] = field(default_factory=dict)
    recommendation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_strategy: str = "balanced"
    filters: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Initialize default team composition."""
        if not self.team_composition:
            self.team_composition = {
                "top": None,
                "jungle": None,
                "middle": None,
                "bottom": None,
                "support": None
            }


@dataclass
class RecommendationStrategy:
    """Defines a recommendation strategy with custom weights."""
    
    name: str
    description: str
    weights: Dict[str, float]
    risk_tolerance: float
    meta_emphasis: float
    
    @classmethod
    def get_default_strategies(cls) -> Dict[str, 'RecommendationStrategy']:
        """Get default recommendation strategies."""
        return {
            "safe": cls(
                name="Safe",
                description="Conservative picks with proven performance",
                weights={
                    'individual_performance': 0.45,
                    'team_synergy': 0.30,
                    'recent_form': 0.15,
                    'meta_relevance': 0.05,
                    'confidence': 0.05
                },
                risk_tolerance=0.2,
                meta_emphasis=0.5
            ),
            "balanced": cls(
                name="Balanced",
                description="Well-rounded approach balancing all factors",
                weights={
                    'individual_performance': 0.35,
                    'team_synergy': 0.25,
                    'recent_form': 0.20,
                    'meta_relevance': 0.10,
                    'confidence': 0.10
                },
                risk_tolerance=0.5,
                meta_emphasis=1.0
            ),
            "aggressive": cls(
                name="Aggressive",
                description="High-risk, high-reward picks emphasizing meta and synergy",
                weights={
                    'individual_performance': 0.25,
                    'team_synergy': 0.35,
                    'recent_form': 0.15,
                    'meta_relevance': 0.20,
                    'confidence': 0.05
                },
                risk_tolerance=0.8,
                meta_emphasis=1.5
            ),
            "counter_pick": cls(
                name="Counter-Pick",
                description="Focus on countering enemy composition",
                weights={
                    'individual_performance': 0.30,
                    'team_synergy': 0.20,
                    'recent_form': 0.15,
                    'meta_relevance': 0.25,
                    'confidence': 0.10
                },
                risk_tolerance=0.6,
                meta_emphasis=1.2
            )
        }


class ChampionRecommendationInterface:
    """
    Advanced champion recommendation interface with drag-and-drop team building,
    real-time updates, and comprehensive analysis.
    """
    
    def __init__(self, core_engine: CoreEngine):
        """Initialize the champion recommendation interface."""
        self.core_engine = core_engine
        self.logger = logging.getLogger(__name__)
        
        # Initialize recommendation engine
        if hasattr(core_engine, 'champion_recommendation_engine'):
            self.recommendation_engine = core_engine.champion_recommendation_engine
        else:
            # Create recommendation engine if not available
            self.recommendation_engine = ChampionRecommendationEngine(
                config=core_engine.config,
                analytics_engine=core_engine.historical_analytics_engine,
                champion_data_manager=core_engine.champion_data_manager,
                baseline_manager=core_engine.baseline_manager
            )
        
        # Session management
        self.sessions: Dict[str, RecommendationSession] = {}
        self.strategies = RecommendationStrategy.get_default_strategies()
        
        # Component configuration
        self.config = ComponentConfig()
        
        # Cache for performance
        self.player_cache: Dict[str, List[Player]] = {}
        self.champion_cache: Dict[str, List[Dict]] = {}
        
        self.logger.info("Champion recommendation interface initialized")
    
    def create_recommendation_interface(self) -> None:
        """Create the complete champion recommendation interface within the current Gradio context."""
        # Create session
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = RecommendationSession(session_id=session_id)
        
        # Store session ID for later use
        self.current_session_id = session_id
        
        # Header and description
        gr.Markdown("""
        # 🎯 Intelligent Champion Recommendations
        
        Build your team composition with AI-powered champion recommendations based on 
        historical performance, team synergy, and strategic considerations.
        """)
        
        # Strategy selection and controls
        with gr.Row():
            strategy_selector = gr.Dropdown(
                choices=[(s.description, k) for k, s in self.strategies.items()],
                value="balanced",
                label="Recommendation Strategy",
                info="Choose your strategic approach"
            )
            
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
            reset_btn = gr.Button("🗑️ Reset Team", size="sm", variant="secondary")
        
        # Team composition builder
        self._create_team_builder_ui(session_id)
        
        # Recommendation panel
        self._create_recommendation_panel_ui(session_id)
        
        # Analysis and visualization
        self._create_analysis_panel_ui(session_id)
        
        # History and comparison
        self._create_history_panel_ui(session_id)
    
    def _create_team_builder_ui(self, session_id: str) -> None:
        """Create the drag-and-drop team composition builder UI."""
        gr.Markdown("## 👥 Team Composition Builder")
        
        # Team composition display
        with gr.Row():
            for role in ["top", "jungle", "middle", "bottom", "support"]:
                with gr.Column():
                    # Role header
                    gr.Markdown(f"### {role.title()}")
                    
                    # Player assignment
                    player_dropdown = gr.Dropdown(
                        label="Player",
                        choices=self._get_player_choices(),
                        value=None,
                        interactive=True,
                        info=f"Assign player to {role}"
                    )
                    
                    # Champion assignment
                    champion_dropdown = gr.Dropdown(
                        label="Champion",
                        choices=[],
                        value=None,
                        interactive=True,
                        info=f"Select champion for {role}"
                    )
                    
                    # Assignment status
                    status_display = gr.HTML(
                        self._create_role_status_display(role, None, None)
                    )
        
        # Team synergy overview
        team_synergy_display = gr.HTML(
            self._create_team_synergy_display(session_id)
        )
    
    def _create_recommendation_panel_ui(self, session_id: str) -> None:
        """Create the recommendation panel with detailed analysis UI."""
        gr.Markdown("## 🤖 AI Recommendations")
        
        # Target role selection
        with gr.Row():
            target_role = gr.Dropdown(
                choices=["top", "jungle", "middle", "bottom", "support"],
                value="top",
                label="Get Recommendations For",
                info="Select role to get champion recommendations"
            )
            
            get_recommendations_btn = gr.Button(
                "Get Recommendations", 
                variant="primary"
            )
        
        # Recommendation filters
        with gr.Accordion("Advanced Filters", open=False):
            with gr.Row():
                min_confidence = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.3,
                    step=0.1,
                    label="Minimum Confidence",
                    info="Filter recommendations by confidence score"
                )
                
                max_recommendations = gr.Slider(
                    minimum=3,
                    maximum=15,
                    value=8,
                    step=1,
                    label="Max Recommendations",
                    info="Maximum number of recommendations to show"
                )
            
            with gr.Row():
                include_off_meta = gr.Checkbox(
                    label="Include Off-Meta Picks",
                    value=False,
                    info="Include champions not currently in meta"
                )
                
                prioritize_comfort = gr.Checkbox(
                    label="Prioritize Comfort Picks",
                    value=True,
                    info="Favor champions the player has experience with"
                )
        
        # Recommendations display
        recommendations_display = gr.HTML("")
        
        # Recommendation details
        with gr.Accordion("Recommendation Details", open=False):
            selected_recommendation = gr.Dropdown(
                label="Select Recommendation for Details",
                choices=[],
                value=None
            )
            recommendation_analysis = gr.HTML("")
            recommendation_chart = gr.Plot()
        
        # Simple event handler for demo
        def handle_get_recommendations(role: str) -> str:
            return f"""
            <div style="padding: 15px; border: 1px solid #007bff; border-radius: 8px; background: #f8f9fa;">
                <h4>🎯 Sample Recommendations for {role.title()}</h4>
                <div style="margin: 10px 0;">
                    <div style="padding: 8px; margin: 4px 0; border: 1px solid #28a745; border-radius: 4px; background: #d4edda;">
                        <strong>1. Champion A (85% confidence)</strong><br>
                        <small>• Strong individual performance<br>• Good team synergy<br>• Meta relevant</small>
                    </div>
                    <div style="padding: 8px; margin: 4px 0; border: 1px solid #28a745; border-radius: 4px; background: #d4edda;">
                        <strong>2. Champion B (78% confidence)</strong><br>
                        <small>• High comfort level<br>• Proven track record<br>• Safe pick</small>
                    </div>
                    <div style="padding: 8px; margin: 4px 0; border: 1px solid #ffc107; border-radius: 4px; background: #fff3cd;">
                        <strong>3. Champion C (65% confidence)</strong><br>
                        <small>• Counter-pick potential<br>• Recent form improvement<br>• Moderate risk</small>
                    </div>
                </div>
            </div>
            """
        
        get_recommendations_btn.click(
            fn=handle_get_recommendations,
            inputs=[target_role],
            outputs=[recommendations_display]
        )
    
    def _create_analysis_panel_ui(self, session_id: str) -> None:
        """Create the analysis and visualization panel UI."""
        gr.Markdown("## 📊 Team Analysis")
        
        # Analysis tabs
        with gr.Tabs():
            # Synergy Analysis Tab
            with gr.Tab("Team Synergy"):
                synergy_matrix = gr.Plot()
                synergy_explanation = gr.Markdown("Assign champions to see synergy analysis")
            
            # Performance Projection Tab
            with gr.Tab("Performance Projection"):
                performance_chart = gr.Plot()
                performance_metrics = gr.HTML("Build your team to see performance projections")
            
            # Risk Assessment Tab
            with gr.Tab("Risk Assessment"):
                risk_chart = gr.Plot()
                risk_analysis = gr.Markdown("Team composition needed for risk assessment")
            
            # Meta Analysis Tab
            with gr.Tab("Meta Analysis"):
                meta_chart = gr.Plot()
                meta_insights = gr.Markdown("Add champions to see meta analysis")
    
    def _create_history_panel_ui(self, session_id: str) -> None:
        """Create the recommendation history and comparison panel UI."""
        gr.Markdown("## 📚 Recommendation History")
        
        # History controls
        with gr.Row():
            save_composition_btn = gr.Button(
                "💾 Save Current Composition", 
                variant="secondary"
            )
            load_composition = gr.Dropdown(
                label="Load Saved Composition",
                choices=[],
                value=None
            )
            compare_compositions_btn = gr.Button(
                "🔍 Compare Compositions",
                variant="secondary"
            )
        
        # History display
        history_display = gr.HTML("""
        <div style="padding: 20px; text-align: center; color: #666;">
            <p>No saved compositions yet. Save your current composition to build a history.</p>
        </div>
        """)
        
        # Comparison results
        comparison_results = gr.HTML("")
        comparison_chart = gr.Plot()
    
    def _setup_event_handlers(self, components: Dict[str, gr.Component], session_id: str) -> None:
        """Setup all event handlers for the recommendation interface."""
        
        # Strategy change handler
        components['strategy_selector'].change(
            fn=lambda strategy: self._handle_strategy_change(session_id, strategy),
            inputs=[components['strategy_selector']],
            outputs=[
                components['recommendations_display'],
                components['team_synergy_display']
            ]
        )
        
        # Team composition change handlers
        for role in ["top", "jungle", "middle", "bottom", "support"]:
            # Player assignment change
            components[f'{role}_player'].change(
                fn=lambda player, r=role: self._handle_player_assignment(session_id, r, player),
                inputs=[components[f'{role}_player']],
                outputs=[
                    components[f'{role}_champion'],
                    components[f'{role}_status'],
                    components['team_synergy_display']
                ]
            )
            
            # Champion assignment change
            components[f'{role}_champion'].change(
                fn=lambda champion, r=role: self._handle_champion_assignment(session_id, r, champion),
                inputs=[components[f'{role}_champion']],
                outputs=[
                    components[f'{role}_status'],
                    components['team_synergy_display'],
                    components['recommendations_display']
                ]
            )
        
        # Recommendation generation
        components['get_recommendations_btn'].click(
            fn=lambda role, strategy, min_conf, max_recs, off_meta, comfort: 
                self._generate_recommendations(
                    session_id, role, strategy, min_conf, max_recs, off_meta, comfort
                ),
            inputs=[
                components['target_role'],
                components['strategy_selector'],
                components['min_confidence'],
                components['max_recommendations'],
                components['include_off_meta'],
                components['prioritize_comfort']
            ],
            outputs=[
                components['recommendations_display'],
                components['selected_recommendation']
            ]
        )
        
        # Recommendation details
        components['selected_recommendation'].change(
            fn=lambda rec_id: self._show_recommendation_details(session_id, rec_id),
            inputs=[components['selected_recommendation']],
            outputs=[
                components['recommendation_analysis'],
                components['recommendation_chart']
            ]
        )
        
        # Analysis updates
        for role in ["top", "jungle", "middle", "bottom", "support"]:
            components[f'{role}_champion'].change(
                fn=lambda: self._update_analysis_panels(session_id),
                inputs=[],
                outputs=[
                    components['synergy_matrix'],
                    components['performance_chart'],
                    components['risk_chart'],
                    components['meta_chart']
                ]
            )
        
        # History management
        components['save_composition_btn'].click(
            fn=lambda: self._save_composition(session_id),
            inputs=[],
            outputs=[
                components['load_composition'],
                components['history_display']
            ]
        )
        
        components['load_composition'].change(
            fn=lambda comp_id: self._load_composition(session_id, comp_id),
            inputs=[components['load_composition']],
            outputs=[
                components[f'{role}_player'] for role in ["top", "jungle", "middle", "bottom", "support"]
            ] + [
                components[f'{role}_champion'] for role in ["top", "jungle", "middle", "bottom", "support"]
            ]
        )
        
        # Refresh and reset
        components['refresh_btn'].click(
            fn=lambda: self._refresh_interface(session_id),
            inputs=[],
            outputs=[
                components[f'{role}_player'] for role in ["top", "jungle", "middle", "bottom", "support"]
            ]
        )
        
        components['reset_btn'].click(
            fn=lambda: self._reset_team_composition(session_id),
            inputs=[],
            outputs=[
                components[f'{role}_player'] for role in ["top", "jungle", "middle", "bottom", "support"]
            ] + [
                components[f'{role}_champion'] for role in ["top", "jungle", "middle", "bottom", "support"]
            ] + [
                components['team_synergy_display'],
                components['recommendations_display']
            ]
        )
    
    def _handle_strategy_change(self, session_id: str, strategy: str) -> Tuple[str, str]:
        """Handle strategy selection change."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return "Session not found", ""
            
            session.current_strategy = strategy
            session.last_updated = datetime.now()
            
            # Update recommendations display
            recommendations_html = self._create_strategy_info_display(strategy)
            synergy_html = self._create_team_synergy_display(session_id)
            
            return recommendations_html, synergy_html
            
        except Exception as e:
            self.logger.error(f"Error handling strategy change: {e}")
            return f"Error: {str(e)}", ""
    
    def _handle_player_assignment(self, session_id: str, role: str, player_selection: str) -> Tuple[List, str, str]:
        """Handle player assignment to role."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return [], "Session not found", ""
            
            # Update team composition
            if player_selection and player_selection != "None":
                # Parse player selection (format: "Player Name (summoner_name)")
                player_name = player_selection.split(" (")[0]
                
                # Find player
                players = self._get_available_players()
                player = next((p for p in players if p.name == player_name), None)
                
                if player:
                    # Create a mock PlayerRoleAssignment since we don't have the exact class
                    from dataclasses import dataclass
                    
                    @dataclass
                    class PlayerRoleAssignment:
                        puuid: str
                        player_name: str
                        role: str
                        champion_id: Optional[int] = None
                    
                    session.team_composition[role] = PlayerRoleAssignment(
                        puuid=player.puuid,
                        player_name=player.name,
                        role=role,
                        champion_id=None
                    )
                else:
                    session.team_composition[role] = None
            else:
                session.team_composition[role] = None
            
            session.last_updated = datetime.now()
            
            # Get champion choices for this player/role
            champion_choices = self._get_champion_choices_for_player_role(player_selection, role)
            
            # Update status display
            status_html = self._create_role_status_display(role, player_selection, None)
            
            # Update team synergy
            synergy_html = self._create_team_synergy_display(session_id)
            
            return champion_choices, status_html, synergy_html
            
        except Exception as e:
            self.logger.error(f"Error handling player assignment: {e}")
            return [], f"Error: {str(e)}", ""
    
    def _handle_champion_assignment(self, session_id: str, role: str, champion_selection: str) -> Tuple[str, str, str]:
        """Handle champion assignment to role."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return "Session not found", "", ""
            
            # Update champion in team composition
            if session.team_composition[role] and champion_selection:
                # Parse champion selection to get champion ID
                champion_id = self._parse_champion_selection(champion_selection)
                session.team_composition[role].champion_id = champion_id
            
            session.last_updated = datetime.now()
            
            # Update displays
            player_selection = None
            if session.team_composition[role]:
                player_selection = session.team_composition[role].player_name
            
            status_html = self._create_role_status_display(role, player_selection, champion_selection)
            synergy_html = self._create_team_synergy_display(session_id)
            recommendations_html = self._update_recommendations_based_on_composition(session_id)
            
            return status_html, synergy_html, recommendations_html
            
        except Exception as e:
            self.logger.error(f"Error handling champion assignment: {e}")
            return f"Error: {str(e)}", "", ""
    
    def _generate_recommendations(
        self, 
        session_id: str, 
        target_role: str, 
        strategy: str,
        min_confidence: float,
        max_recommendations: int,
        include_off_meta: bool,
        prioritize_comfort: bool
    ) -> Tuple[str, List]:
        """Generate champion recommendations for the target role."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return "Session not found", []
            
            # Get assigned player for target role
            role_assignment = session.team_composition.get(target_role)
            if not role_assignment or not role_assignment.puuid:
                return "No player assigned to this role", []
            
            # Create team context
            team_context = self._create_team_context(session)
            
            # Get strategy weights
            strategy_config = self.strategies.get(strategy, self.strategies["balanced"])
            
            # Generate recommendations
            recommendations = self.recommendation_engine.get_champion_recommendations(
                puuid=role_assignment.puuid,
                role=target_role,
                team_context=team_context,
                max_recommendations=max_recommendations,
                custom_weights=strategy_config.weights
            )
            
            # Filter by confidence
            recommendations = [r for r in recommendations if r.confidence >= min_confidence]
            
            # Apply meta filtering
            if not include_off_meta:
                recommendations = self._filter_meta_recommendations(recommendations)
            
            # Apply comfort filtering
            if prioritize_comfort:
                recommendations = self._prioritize_comfort_picks(recommendations, role_assignment.puuid)
            
            # Store in session history
            session.recommendation_history.append({
                'timestamp': datetime.now(),
                'role': target_role,
                'strategy': strategy,
                'recommendations': recommendations,
                'filters': {
                    'min_confidence': min_confidence,
                    'max_recommendations': max_recommendations,
                    'include_off_meta': include_off_meta,
                    'prioritize_comfort': prioritize_comfort
                }
            })
            
            # Create display HTML
            recommendations_html = self._create_recommendations_display(recommendations, strategy_config)
            
            # Create dropdown choices for details
            recommendation_choices = [
                (f"{r.champion_name} ({r.confidence:.1%})", f"{r.champion_id}_{target_role}")
                for r in recommendations
            ]
            
            return recommendations_html, recommendation_choices
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return f"Error generating recommendations: {str(e)}", []
    
    def _show_recommendation_details(self, session_id: str, recommendation_id: str) -> Tuple[str, go.Figure]:
        """Show detailed analysis for a specific recommendation."""
        try:
            if not recommendation_id:
                return "", go.Figure()
            
            # Parse recommendation ID
            champion_id, role = recommendation_id.split("_")
            champion_id = int(champion_id)
            
            # Get latest recommendations from session
            session = self.sessions.get(session_id)
            if not session or not session.recommendation_history:
                return "No recommendation data available", go.Figure()
            
            latest_recommendations = session.recommendation_history[-1]['recommendations']
            recommendation = next(
                (r for r in latest_recommendations if r.champion_id == champion_id), 
                None
            )
            
            if not recommendation:
                return "Recommendation not found", go.Figure()
            
            # Create detailed analysis HTML
            analysis_html = self._create_detailed_recommendation_analysis(recommendation)
            
            # Create recommendation breakdown chart
            chart = self._create_recommendation_breakdown_chart(recommendation)
            
            return analysis_html, chart
            
        except Exception as e:
            self.logger.error(f"Error showing recommendation details: {e}")
            return f"Error: {str(e)}", go.Figure()
    
    def _update_analysis_panels(self, session_id: str) -> Tuple[go.Figure, go.Figure, go.Figure, go.Figure]:
        """Update all analysis panels based on current team composition."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return go.Figure(), go.Figure(), go.Figure(), go.Figure()
            
            # Create analysis charts
            synergy_chart = self._create_synergy_matrix_chart(session)
            performance_chart = self._create_performance_projection_chart(session)
            risk_chart = self._create_risk_assessment_chart(session)
            meta_chart = self._create_meta_analysis_chart(session)
            
            return synergy_chart, performance_chart, risk_chart, meta_chart
            
        except Exception as e:
            self.logger.error(f"Error updating analysis panels: {e}")
            return go.Figure(), go.Figure(), go.Figure(), go.Figure()
    
    def _save_composition(self, session_id: str) -> Tuple[List, str]:
        """Save current team composition to history."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return [], "Session not found"
            
            # Create composition save
            composition_save = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now(),
                'composition': session.team_composition.copy(),
                'strategy': session.current_strategy
            }
            
            # Add to history (in a real implementation, this would be persisted)
            if not hasattr(session, 'saved_compositions'):
                session.saved_compositions = []
            session.saved_compositions.append(composition_save)
            
            # Update dropdown choices
            choices = [
                (f"{comp['timestamp'].strftime('%Y-%m-%d %H:%M')} - {comp['strategy']}", comp['id'])
                for comp in session.saved_compositions
            ]
            
            # Create history display
            history_html = self._create_history_display(session)
            
            return choices, history_html
            
        except Exception as e:
            self.logger.error(f"Error saving composition: {e}")
            return [], f"Error: {str(e)}"
    
    def _load_composition(self, session_id: str, composition_id: str) -> Tuple[str, ...]:
        """Load a saved team composition."""
        try:
            session = self.sessions.get(session_id)
            if not session or not hasattr(session, 'saved_compositions'):
                return tuple([""] * 10)  # 5 players + 5 champions
            
            # Find composition
            composition = next(
                (comp for comp in session.saved_compositions if comp['id'] == composition_id),
                None
            )
            
            if not composition:
                return tuple([""] * 10)
            
            # Load composition into session
            session.team_composition = composition['composition'].copy()
            session.current_strategy = composition['strategy']
            
            # Create return values for all dropdowns
            result = []
            
            # Player assignments
            for role in ["top", "jungle", "middle", "bottom", "support"]:
                assignment = session.team_composition.get(role)
                if assignment and assignment.player_name:
                    result.append(f"{assignment.player_name} ({assignment.player_name})")
                else:
                    result.append("")
            
            # Champion assignments
            for role in ["top", "jungle", "middle", "bottom", "support"]:
                assignment = session.team_composition.get(role)
                if assignment and assignment.champion_id:
                    champion_name = self._get_champion_name(assignment.champion_id)
                    result.append(f"{champion_name} ({assignment.champion_id})")
                else:
                    result.append("")
            
            return tuple(result)
            
        except Exception as e:
            self.logger.error(f"Error loading composition: {e}")
            return tuple([""] * 10)
    
    def _refresh_interface(self, session_id: str) -> Tuple[List, ...]:
        """Refresh the interface with updated player data."""
        try:
            # Clear caches
            self.player_cache.clear()
            self.champion_cache.clear()
            
            # Get updated player choices
            player_choices = self._get_player_choices()
            
            return tuple([player_choices] * 5)  # 5 roles
            
        except Exception as e:
            self.logger.error(f"Error refreshing interface: {e}")
            return tuple([[]]*5)
    
    def _reset_team_composition(self, session_id: str) -> Tuple[str, ...]:
        """Reset the team composition to empty state."""
        try:
            session = self.sessions.get(session_id)
            if session:
                session.team_composition = {
                    "top": None,
                    "jungle": None,
                    "middle": None,
                    "bottom": None,
                    "support": None
                }
                session.last_updated = datetime.now()
            
            # Return empty values for all components
            empty_values = [""] * 10  # 5 players + 5 champions
            empty_values.extend(["", ""])  # synergy display + recommendations display
            
            return tuple(empty_values)
            
        except Exception as e:
            self.logger.error(f"Error resetting team composition: {e}")
            return tuple([""] * 12)
    
    # Helper methods for UI creation and data processing
    
    def _create_role_status_display(self, role: str, player: Optional[str], champion: Optional[str]) -> str:
        """Create status display for a role assignment."""
        if not player:
            return f"""
            <div style="padding: 8px; border: 2px dashed #ccc; border-radius: 4px; text-align: center; color: #666;">
                <i>No player assigned</i>
            </div>
            """
        
        if not champion:
            return f"""
            <div style="padding: 8px; border: 2px solid #ffc107; border-radius: 4px; background: #fff3cd;">
                <strong>👤 {player}</strong><br>
                <i>Champion needed</i>
            </div>
            """
        
        return f"""
        <div style="padding: 8px; border: 2px solid #28a745; border-radius: 4px; background: #d4edda;">
            <strong>👤 {player}</strong><br>
            <strong>🏆 {champion}</strong>
        </div>
        """
    
    def _create_team_synergy_display(self, session_id: str) -> str:
        """Create team synergy overview display."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return "Session not found"
            
            # Count assigned roles
            assigned_roles = sum(1 for assignment in session.team_composition.values() if assignment)
            total_roles = len(session.team_composition)
            
            # Calculate basic synergy score (placeholder)
            synergy_score = 0.5  # This would be calculated from actual synergy analysis
            
            synergy_color = "#28a745" if synergy_score > 0.6 else "#ffc107" if synergy_score > 0.4 else "#dc3545"
            
            return f"""
            <div style="padding: 15px; border: 1px solid #ddd; border-radius: 8px; margin: 10px 0;">
                <h4 style="margin: 0 0 10px 0;">Team Composition Status</h4>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>Roles Filled:</strong> {assigned_roles}/{total_roles}<br>
                        <strong>Team Synergy:</strong> <span style="color: {synergy_color};">{synergy_score:.1%}</span>
                    </div>
                    <div style="width: 60px; height: 60px; border-radius: 50%; background: conic-gradient({synergy_color} {synergy_score*360}deg, #eee 0deg); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {synergy_score:.0%}
                    </div>
                </div>
            </div>
            """
            
        except Exception as e:
            self.logger.error(f"Error creating team synergy display: {e}")
            return f"Error: {str(e)}"
    
    def _create_strategy_info_display(self, strategy: str) -> str:
        """Create strategy information display."""
        strategy_config = self.strategies.get(strategy, self.strategies["balanced"])
        
        return f"""
        <div style="padding: 15px; border: 1px solid #007bff; border-radius: 8px; background: #f8f9fa;">
            <h4 style="color: #007bff; margin: 0 0 10px 0;">🎯 {strategy_config.name} Strategy</h4>
            <p style="margin: 0 0 10px 0;">{strategy_config.description}</p>
            <div style="font-size: 0.9em;">
                <strong>Focus Areas:</strong><br>
                • Individual Performance: {strategy_config.weights['individual_performance']:.0%}<br>
                • Team Synergy: {strategy_config.weights['team_synergy']:.0%}<br>
                • Recent Form: {strategy_config.weights['recent_form']:.0%}<br>
                • Meta Relevance: {strategy_config.weights['meta_relevance']:.0%}<br>
                • Confidence: {strategy_config.weights['confidence']:.0%}
            </div>
        </div>
        """
    
    def _create_recommendations_display(self, recommendations: List[ChampionRecommendation], strategy_config: RecommendationStrategy) -> str:
        """Create the recommendations display HTML."""
        if not recommendations:
            return """
            <div style="padding: 20px; text-align: center; color: #666;">
                <h4>No recommendations available</h4>
                <p>Assign a player to a role and click "Get Recommendations" to see AI-powered champion suggestions.</p>
            </div>
            """
        
        html_parts = ["""
        <div style="padding: 15px;">
            <h4 style="margin: 0 0 15px 0;">🤖 AI Champion Recommendations</h4>
        """]
        
        for i, rec in enumerate(recommendations[:8]):  # Limit to top 8
            confidence_color = "#28a745" if rec.confidence > 0.7 else "#ffc107" if rec.confidence > 0.5 else "#dc3545"
            
            # Create reasoning summary
            reasoning_points = []
            if hasattr(rec, 'reasoning') and rec.reasoning:
                reasoning_points = rec.reasoning.key_factors[:3]  # Top 3 factors
            
            reasoning_html = ""
            if reasoning_points:
                reasoning_html = "<br>".join([f"• {point}" for point in reasoning_points])
            
            html_parts.append(f"""
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 8px 0; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <h5 style="margin: 0; color: #333;">{i+1}. {rec.champion_name}</h5>
                        <div style="font-size: 0.9em; color: #666; margin: 4px 0;">
                            {reasoning_html}
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.2em; font-weight: bold; color: {confidence_color};">
                            {rec.confidence:.0%}
                        </div>
                        <div style="font-size: 0.8em; color: #666;">
                            Confidence
                        </div>
                    </div>
                </div>
            </div>
            """)
        
        html_parts.append("</div>")
        return "".join(html_parts)
    
    def _create_detailed_recommendation_analysis(self, recommendation: ChampionRecommendation) -> str:
        """Create detailed analysis HTML for a specific recommendation."""
        return f"""
        <div style="padding: 15px;">
            <h4>{recommendation.champion_name} - Detailed Analysis</h4>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">
                <div>
                    <h5>Performance Metrics</h5>
                    <p><strong>Confidence:</strong> {recommendation.confidence:.1%}</p>
                    <p><strong>Recommendation Score:</strong> {recommendation.recommendation_score:.2f}</p>
                </div>
                <div>
                    <h5>Historical Performance</h5>
                    <p><strong>Games Played:</strong> {getattr(recommendation.historical_performance.performance, 'games_played', 'N/A')}</p>
                    <p><strong>Win Rate:</strong> {getattr(recommendation.historical_performance.performance, 'win_rate', 0):.1%}</p>
                </div>
            </div>
            
            <div style="margin: 15px 0;">
                <h5>Reasoning</h5>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">
                    {self._format_recommendation_reasoning(recommendation)}
                </div>
            </div>
        </div>
        """
    
    def _format_recommendation_reasoning(self, recommendation: ChampionRecommendation) -> str:
        """Format the reasoning for a recommendation."""
        if not hasattr(recommendation, 'reasoning') or not recommendation.reasoning:
            return "No detailed reasoning available."
        
        reasoning = recommendation.reasoning
        parts = []
        
        if hasattr(reasoning, 'key_factors'):
            parts.extend([f"• {factor}" for factor in reasoning.key_factors])
        
        if hasattr(reasoning, 'performance_summary'):
            parts.append(f"<br><strong>Performance:</strong> {reasoning.performance_summary}")
        
        if hasattr(reasoning, 'synergy_summary'):
            parts.append(f"<strong>Synergy:</strong> {reasoning.synergy_summary}")
        
        return "<br>".join(parts) if parts else "Analysis in progress..."
    
    def _create_recommendation_breakdown_chart(self, recommendation: ChampionRecommendation) -> go.Figure:
        """Create a breakdown chart for recommendation scoring."""
        try:
            # Create sample data (in real implementation, this would come from the recommendation engine)
            categories = ['Individual Performance', 'Team Synergy', 'Recent Form', 'Meta Relevance', 'Confidence']
            values = [0.8, 0.6, 0.7, 0.5, recommendation.confidence]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=recommendation.champion_name,
                line_color='rgb(0, 123, 255)'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1]
                    )),
                showlegend=True,
                title=f"{recommendation.champion_name} - Recommendation Breakdown"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating recommendation breakdown chart: {e}")
            return go.Figure()
    
    def _create_synergy_matrix_chart(self, session: RecommendationSession) -> go.Figure:
        """Create synergy matrix visualization."""
        try:
            # Get assigned champions
            assigned_champions = []
            roles = []
            
            for role, assignment in session.team_composition.items():
                if assignment and assignment.champion_id:
                    champion_name = self._get_champion_name(assignment.champion_id)
                    assigned_champions.append(champion_name)
                    roles.append(role.title())
            
            if len(assigned_champions) < 2:
                fig = go.Figure()
                fig.add_annotation(
                    text="Assign at least 2 champions to see synergy analysis",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font_size=16
                )
                fig.update_layout(title="Team Synergy Matrix")
                return fig
            
            # Create sample synergy matrix (in real implementation, calculate actual synergies)
            try:
                import numpy as np
                n = len(assigned_champions)
                synergy_matrix = np.random.uniform(0.3, 0.9, (n, n))
                np.fill_diagonal(synergy_matrix, 1.0)
            except ImportError:
                # Fallback without numpy
                n = len(assigned_champions)
                synergy_matrix = [[0.7 + 0.2 * ((i + j) % 3) / 3 for j in range(n)] for i in range(n)]
                for i in range(n):
                    synergy_matrix[i][i] = 1.0
            
            fig = go.Figure(data=go.Heatmap(
                z=synergy_matrix,
                x=assigned_champions,
                y=assigned_champions,
                colorscale='RdYlGn',
                zmin=0, zmax=1,
                text=[[f"{val:.2f}" for val in row] for row in synergy_matrix],
                texttemplate="%{text}",
                textfont={"size": 12},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="Team Synergy Matrix",
                xaxis_title="Champions",
                yaxis_title="Champions"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating synergy matrix chart: {e}")
            return go.Figure()
    
    def _create_performance_projection_chart(self, session: RecommendationSession) -> go.Figure:
        """Create performance projection chart."""
        try:
            # Sample performance projection data
            metrics = ['Win Rate', 'Early Game', 'Mid Game', 'Late Game', 'Team Fighting']
            current_values = [0.65, 0.7, 0.6, 0.8, 0.75]
            projected_values = [0.68, 0.72, 0.65, 0.82, 0.78]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Current Performance',
                x=metrics,
                y=current_values,
                marker_color='lightblue'
            ))
            
            fig.add_trace(go.Bar(
                name='Projected Performance',
                x=metrics,
                y=projected_values,
                marker_color='darkblue'
            ))
            
            fig.update_layout(
                title='Performance Projection',
                xaxis_title='Metrics',
                yaxis_title='Score',
                barmode='group',
                yaxis=dict(range=[0, 1])
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating performance projection chart: {e}")
            return go.Figure()
    
    def _create_risk_assessment_chart(self, session: RecommendationSession) -> go.Figure:
        """Create risk assessment chart."""
        try:
            # Sample risk assessment data
            risk_factors = ['Champion Mastery', 'Meta Stability', 'Team Synergy', 'Counter-Pick Risk', 'Execution Difficulty']
            risk_levels = [0.2, 0.4, 0.3, 0.6, 0.5]  # 0 = low risk, 1 = high risk
            
            colors = ['green' if r < 0.3 else 'orange' if r < 0.6 else 'red' for r in risk_levels]
            
            fig = go.Figure(go.Bar(
                x=risk_factors,
                y=risk_levels,
                marker_color=colors,
                text=[f"{r:.1%}" for r in risk_levels],
                textposition='auto'
            ))
            
            fig.update_layout(
                title='Risk Assessment',
                xaxis_title='Risk Factors',
                yaxis_title='Risk Level',
                yaxis=dict(range=[0, 1])
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating risk assessment chart: {e}")
            return go.Figure()
    
    def _create_meta_analysis_chart(self, session: RecommendationSession) -> go.Figure:
        """Create meta analysis chart."""
        try:
            # Sample meta analysis data
            champions = []
            meta_scores = []
            
            for role, assignment in session.team_composition.items():
                if assignment and assignment.champion_id:
                    champion_name = self._get_champion_name(assignment.champion_id)
                    champions.append(f"{champion_name} ({role.title()})")
                    # Sample meta score without numpy
                    import random
                    meta_scores.append(random.uniform(0.4, 0.9))
            
            if not champions:
                fig = go.Figure()
                fig.add_annotation(
                    text="Assign champions to see meta analysis",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font_size=16
                )
                fig.update_layout(title="Meta Analysis")
                return fig
            
            colors = ['green' if s > 0.7 else 'orange' if s > 0.5 else 'red' for s in meta_scores]
            
            fig = go.Figure(go.Bar(
                x=champions,
                y=meta_scores,
                marker_color=colors,
                text=[f"{s:.1%}" for s in meta_scores],
                textposition='auto'
            ))
            
            fig.update_layout(
                title='Meta Relevance Analysis',
                xaxis_title='Champions',
                yaxis_title='Meta Score',
                yaxis=dict(range=[0, 1])
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating meta analysis chart: {e}")
            return go.Figure()
    
    def _create_history_display(self, session: RecommendationSession) -> str:
        """Create history display HTML."""
        if not hasattr(session, 'saved_compositions') or not session.saved_compositions:
            return """
            <div style="padding: 20px; text-align: center; color: #666;">
                <p>No saved compositions yet. Save your current composition to build a history.</p>
            </div>
            """
        
        html_parts = ["<div style='padding: 15px;'>"]
        
        for comp in reversed(session.saved_compositions[-5:]):  # Show last 5
            timestamp = comp['timestamp'].strftime('%Y-%m-%d %H:%M')
            strategy = comp['strategy'].title()
            
            # Count assigned roles
            assigned_count = sum(1 for assignment in comp['composition'].values() if assignment)
            
            html_parts.append(f"""
            <div style="border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin: 5px 0;">
                <strong>{timestamp}</strong> - {strategy} Strategy<br>
                <small>Roles assigned: {assigned_count}/5</small>
            </div>
            """)
        
        html_parts.append("</div>")
        return "".join(html_parts)
    
    # Utility methods
    
    def _get_available_players(self) -> List[Player]:
        """Get list of available players."""
        try:
            if 'players' not in self.player_cache:
                self.player_cache['players'] = self.core_engine.data_manager.load_player_data()
            return self.player_cache['players']
        except Exception as e:
            self.logger.error(f"Error getting available players: {e}")
            return []
    
    def _get_player_choices(self) -> List[str]:
        """Get player choices for dropdowns."""
        players = self._get_available_players()
        return [f"{p.name} ({p.summoner_name})" for p in players]
    
    def _get_champion_choices_for_player_role(self, player_selection: str, role: str) -> List[str]:
        """Get champion choices for a specific player and role."""
        try:
            if not player_selection or player_selection == "None":
                return []
            
            # In a real implementation, this would get the player's champion pool for the role
            # For now, return a sample list
            sample_champions = [
                "Aatrox (266)", "Ahri (103)", "Akali (84)", "Alistar (12)", "Amumu (32)",
                "Anivia (34)", "Annie (1)", "Ashe (22)", "Azir (268)", "Bard (432)"
            ]
            
            return sample_champions[:10]  # Limit to 10 for demo
            
        except Exception as e:
            self.logger.error(f"Error getting champion choices: {e}")
            return []
    
    def _parse_champion_selection(self, champion_selection: str) -> Optional[int]:
        """Parse champion selection to extract champion ID."""
        try:
            if not champion_selection or "(" not in champion_selection:
                return None
            
            # Extract ID from format "Champion Name (ID)"
            champion_id_str = champion_selection.split("(")[-1].rstrip(")")
            return int(champion_id_str)
            
        except (ValueError, IndexError) as e:
            self.logger.error(f"Error parsing champion selection: {e}")
            return None
    
    def _get_champion_name(self, champion_id: int) -> str:
        """Get champion name by ID."""
        try:
            if hasattr(self.core_engine, 'champion_data_manager'):
                name = self.core_engine.champion_data_manager.get_champion_name(champion_id)
                if name:
                    return name
            
            # Fallback to generic name
            return f"Champion_{champion_id}"
            
        except Exception as e:
            self.logger.error(f"Error getting champion name: {e}")
            return f"Champion_{champion_id}"
    
    def _create_team_context(self, session: RecommendationSession) -> TeamContext:
        """Create team context from session composition."""
        try:
            existing_picks = {}
            
            for role, assignment in session.team_composition.items():
                if assignment and assignment.champion_id:
                    existing_picks[role] = assignment
            
            # Create a mock TeamContext since we don't have the exact class structure
            from dataclasses import dataclass
            
            @dataclass
            class TeamContext:
                existing_picks: Dict = None
                banned_champions: List = None
                enemy_composition: Dict = None
                available_champions: Optional[List] = None
                
                def __post_init__(self):
                    if self.existing_picks is None:
                        self.existing_picks = {}
                    if self.banned_champions is None:
                        self.banned_champions = []
                    if self.enemy_composition is None:
                        self.enemy_composition = {}
            
            return TeamContext(
                existing_picks=existing_picks,
                banned_champions=[],
                enemy_composition={},
                available_champions=None
            )
            
        except Exception as e:
            self.logger.error(f"Error creating team context: {e}")
            # Return a basic mock context
            from dataclasses import dataclass
            
            @dataclass
            class TeamContext:
                existing_picks: Dict = None
                banned_champions: List = None
                enemy_composition: Dict = None
                available_champions: Optional[List] = None
                
                def __post_init__(self):
                    if self.existing_picks is None:
                        self.existing_picks = {}
                    if self.banned_champions is None:
                        self.banned_champions = []
                    if self.enemy_composition is None:
                        self.enemy_composition = {}
            
            return TeamContext()
    
    def _filter_meta_recommendations(self, recommendations: List[ChampionRecommendation]) -> List[ChampionRecommendation]:
        """Filter recommendations to include only meta-relevant champions."""
        # In a real implementation, this would filter based on current meta data
        return recommendations  # For now, return all
    
    def _prioritize_comfort_picks(self, recommendations: List[ChampionRecommendation], puuid: str) -> List[ChampionRecommendation]:
        """Prioritize champions the player has experience with."""
        # In a real implementation, this would reorder based on player's champion mastery
        return recommendations  # For now, return as-is
    
    def _update_recommendations_based_on_composition(self, session_id: str) -> str:
        """Update recommendations display based on current composition."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return ""
            
            # Count assigned champions
            assigned_count = sum(1 for assignment in session.team_composition.values() 
                               if assignment and assignment.champion_id)
            
            if assigned_count == 0:
                return """
                <div style="padding: 15px; text-align: center; color: #666;">
                    <p>Assign players and champions to see updated recommendations</p>
                </div>
                """
            
            return f"""
            <div style="padding: 15px; background: #f8f9fa; border-radius: 4px;">
                <h5>Composition Updated</h5>
                <p>Team has {assigned_count}/5 champions assigned. Recommendations will adapt to your current composition.</p>
            </div>
            """
            
        except Exception as e:
            self.logger.error(f"Error updating recommendations: {e}")
            return f"Error: {str(e)}"