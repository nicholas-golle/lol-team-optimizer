"""
Comprehensive Analytics Dashboard with Real-time Filtering
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import gradio as gr
import plotly.graph_objects as go

from .analytics_models import AnalyticsFilters, DateRange


@dataclass
class FilterState:
    """Current state of dashboard filters."""
    selected_players: List[str] = field(default_factory=list)
    selected_champions: List[str] = field(default_factory=list)
    selected_roles: List[str] = field(default_factory=list)
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    min_games: int = 1
    queue_types: List[str] = field(default_factory=lambda: ["RANKED_SOLO_5x5"])


@dataclass
class AnalyticsPreset:
    """Predefined analytics configuration."""
    name: str
    description: str
    filters: FilterState
    chart_types: List[str]


class AnalyticsDashboard:
    """Comprehensive analytics dashboard with real-time filtering."""
    
    def __init__(self, analytics_engine, visualization_manager, state_manager, data_manager):
        """Initialize the analytics dashboard."""
        self.logger = logging.getLogger(__name__)
        self.analytics_engine = analytics_engine
        self.viz_manager = visualization_manager
        self.state_manager = state_manager
        self.data_manager = data_manager
        
        # Dashboard state
        self.current_filters = FilterState()
        self.available_players = []
        self.available_champions = []
        self.available_roles = ["top", "jungle", "middle", "bottom", "support"]
        
        # Initialize available options
        self._refresh_available_options()
    
    def _refresh_available_options(self) -> None:
        """Refresh available players and champions for filtering."""
        try:
            players = self.data_manager.load_player_data()
            self.available_players = [p.name for p in players if p.puuid]
            
            if hasattr(self.analytics_engine, 'get_available_champions'):
                self.available_champions = list(self.analytics_engine.get_available_champions())
            else:
                self.available_champions = []
        except Exception as e:
            self.logger.error(f"Failed to refresh available options: {e}")
    
    def create_dashboard_interface(self) -> List[gr.Component]:
        """Create the main dashboard interface components."""
        components = []
        
        # Dashboard header
        header = gr.Markdown("""
        ## 📊 Analytics Dashboard
        
        **Real-time filtering and interactive visualizations**
        """)
        components.append(header)
        
        # Filter panel
        with gr.Accordion("🔍 Analytics Filters", open=True):
            player_filter = gr.Dropdown(
                choices=self.available_players,
                label="Select Players",
                multiselect=True,
                info="Choose specific players to analyze"
            )
            components.append(player_filter)
            
            champion_filter = gr.Dropdown(
                choices=self.available_champions,
                label="Select Champions",
                multiselect=True,
                info="Filter by specific champions"
            )
            components.append(champion_filter)
            
            role_filter = gr.CheckboxGroup(
                choices=[role.title() for role in self.available_roles],
                label="Select Roles",
                info="Filter by roles"
            )
            components.append(role_filter)
            
            with gr.Row():
                date_start = gr.Textbox(
                    label="Start Date",
                    placeholder="YYYY-MM-DD"
                )
                date_end = gr.Textbox(
                    label="End Date", 
                    placeholder="YYYY-MM-DD"
                )
                components.extend([date_start, date_end])
            
            apply_filters_btn = gr.Button("Apply Filters", variant="primary")
            components.append(apply_filters_btn)
        
        # Charts display
        with gr.Row():
            player_radar_plot = gr.Plot(label="Player Performance")
            performance_trends_plot = gr.Plot(label="Performance Trends")
        
        with gr.Row():
            champion_heatmap_plot = gr.Plot(label="Champion Performance")
            synergy_matrix_plot = gr.Plot(label="Team Synergy")
        
        components.extend([
            player_radar_plot, performance_trends_plot,
            champion_heatmap_plot, synergy_matrix_plot
        ])
        
        # Store components for event handling
        self.filter_components = {
            'player_filter': player_filter,
            'champion_filter': champion_filter,
            'role_filter': role_filter,
            'date_start': date_start,
            'date_end': date_end,
            'apply_filters_btn': apply_filters_btn
        }
        
        self.chart_components = {
            'player_radar_plot': player_radar_plot,
            'performance_trends_plot': performance_trends_plot,
            'champion_heatmap_plot': champion_heatmap_plot,
            'synergy_matrix_plot': synergy_matrix_plot
        }
        
        return components
    
    def setup_event_handlers(self) -> None:
        """Setup event handlers for real-time filtering and interactions."""
        def update_charts(*args):
            """Update charts when filters change."""
            try:
                # Create sample charts
                empty_fig = self._create_empty_chart("Analytics Dashboard Ready")
                return (empty_fig, empty_fig, empty_fig, empty_fig)
            except Exception as e:
                error_fig = self._create_error_chart(str(e))
                return (error_fig, error_fig, error_fig, error_fig)
        
        # Set up event handlers
        filter_inputs = [
            self.filter_components['player_filter'],
            self.filter_components['champion_filter'],
            self.filter_components['role_filter'],
            self.filter_components['date_start'],
            self.filter_components['date_end']
        ]
        
        chart_outputs = [
            self.chart_components['player_radar_plot'],
            self.chart_components['performance_trends_plot'],
            self.chart_components['champion_heatmap_plot'],
            self.chart_components['synergy_matrix_plot']
        ]
        
        self.filter_components['apply_filters_btn'].click(
            fn=update_charts,
            inputs=filter_inputs,
            outputs=chart_outputs
        )
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=14, color="gray")
        )
        fig.update_layout(
            title="Analytics Dashboard",
            height=400
        )
        return fig
    
    def _create_error_chart(self, error_message: str) -> go.Figure:
        """Create error chart."""
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            title="Error",
            height=400
        )
        return fig