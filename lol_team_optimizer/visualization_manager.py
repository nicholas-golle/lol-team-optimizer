"""
Advanced Visualization Manager for Interactive Charts

This module provides comprehensive visualization capabilities for the Gradio web interface,
including interactive charts, drill-down capabilities, and dynamic filtering using Plotly.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import gradio as gr
from enum import Enum
import colorsys
import math

from .models import Player, ChampionPerformance, PerformanceData, TeamAssignment
from .analytics_models import (
    PerformanceMetrics, ChampionPerformanceMetrics, PlayerAnalytics,
    TrendAnalysis, ComparativeRankings, ChampionRecommendation,
    TeamComposition, SynergyEffects
)


class ChartType(Enum):
    """Supported chart types."""
    RADAR = "radar"
    HEATMAP = "heatmap"
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    SUNBURST = "sunburst"
    TREEMAP = "treemap"


@dataclass
class ChartConfiguration:
    """Configuration for interactive charts."""
    chart_type: ChartType
    title: str
    data_source: str
    filters: List[str] = field(default_factory=list)
    color_scheme: str = "viridis"
    interactive_features: List[str] = field(default_factory=list)
    export_options: List[str] = field(default_factory=list)
    height: int = 500
    width: Optional[int] = None
    show_legend: bool = True
    animation_enabled: bool = True


@dataclass
class DrillDownData:
    """Data structure for drill-down functionality."""
    level: int
    parent_key: str
    data: Dict[str, Any]
    available_drill_downs: List[str] = field(default_factory=list)


class ColorSchemeManager:
    """Manages color schemes for consistent visualization."""
    
    def __init__(self):
        """Initialize color scheme manager."""
        self.logger = logging.getLogger(__name__)
        self._initialize_color_schemes()
    
    def _initialize_color_schemes(self):
        """Initialize predefined color schemes."""
        self.schemes = {
            "lol_classic": {
                "primary": "#C89B3C",  # Gold
                "secondary": "#0F2027",  # Dark blue
                "accent": "#463714",  # Dark gold
                "success": "#0596AA",  # Teal
                "warning": "#F0E6D2",  # Light gold
                "danger": "#C8AA6E",  # Muted gold
                "roles": {
                    "top": "#FF6B6B",
                    "jungle": "#4ECDC4", 
                    "middle": "#45B7D1",
                    "bottom": "#96CEB4",
                    "support": "#FFEAA7"
                }
            },
            "performance": {
                "excellent": "#2ECC71",
                "good": "#3498DB", 
                "average": "#F39C12",
                "poor": "#E74C3C",
                "gradient": ["#E74C3C", "#F39C12", "#F1C40F", "#2ECC71"]
            },
            "synergy": {
                "high": "#27AE60",
                "medium": "#F39C12",
                "low": "#E67E22",
                "negative": "#E74C3C",
                "neutral": "#95A5A6"
            }
        }
    
    def get_color_palette(self, scheme_name: str, count: int) -> List[str]:
        """Get color palette for a specific scheme."""
        if scheme_name not in self.schemes:
            # Fallback to default Plotly colors
            return px.colors.qualitative.Set1[:count]
        
        scheme = self.schemes[scheme_name]
        
        if "gradient" in scheme:
            return self._interpolate_colors(scheme["gradient"], count)
        elif "roles" in scheme:
            colors = list(scheme["roles"].values())
            return (colors * ((count // len(colors)) + 1))[:count]
        else:
            colors = list(scheme.values())
            return (colors * ((count // len(colors)) + 1))[:count]
    
    def _interpolate_colors(self, base_colors: List[str], count: int) -> List[str]:
        """Interpolate between base colors to create a gradient."""
        if count <= len(base_colors):
            return base_colors[:count]
        
        # Convert hex to RGB
        rgb_colors = []
        for color in base_colors:
            hex_color = color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            rgb_colors.append(rgb)
        
        # Interpolate
        interpolated = []
        segments = len(rgb_colors) - 1
        colors_per_segment = count // segments
        
        for i in range(segments):
            start_color = rgb_colors[i]
            end_color = rgb_colors[i + 1]
            
            for j in range(colors_per_segment):
                ratio = j / colors_per_segment
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                interpolated.append(f"rgb({r},{g},{b})")
        
        # Add remaining colors if needed
        while len(interpolated) < count:
            last_color = rgb_colors[-1]
            interpolated.append(f"rgb({last_color[0]},{last_color[1]},{last_color[2]})")
        
        return interpolated[:count]


class VisualizationManager:
    """Manages all data visualizations for the web interface."""
    
    def __init__(self):
        """Initialize visualization manager."""
        self.logger = logging.getLogger(__name__)
        self.color_manager = ColorSchemeManager()
        self.chart_cache: Dict[str, go.Figure] = {}
        self.default_layout = self._create_default_layout()
        self.drill_down_cache: Dict[str, Dict[str, Any]] = {}
        self.export_formats = ['png', 'svg', 'pdf', 'html', 'json']
    
    def _create_default_layout(self) -> Dict[str, Any]:
        """Create default layout configuration."""
        return {
            "font": {"family": "Arial, sans-serif", "size": 12},
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
            "showlegend": True,
            "hovermode": "closest"
        }
    
    def create_player_performance_radar(self, player_data: Dict[str, Any], 
                                      config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create radar chart for player performance metrics."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.RADAR,
                title="Player Performance Radar",
                data_source="player_performance"
            )
        
        try:
            # Extract performance metrics
            metrics = player_data.get('performance_metrics', {})
            roles = player_data.get('roles', ['overall'])
            
            fig = go.Figure()
            
            # Define radar chart categories
            categories = [
                'Win Rate', 'KDA', 'CS/Min', 'Vision Score', 
                'Damage/Min', 'Gold/Min', 'Recent Form'
            ]
            
            colors = self.color_manager.get_color_palette("lol_classic", len(roles))
            
            for i, role in enumerate(roles):
                role_metrics = metrics.get(role, {})
                
                # Normalize values to 0-100 scale for radar chart
                values = [
                    role_metrics.get('win_rate', 0) * 100,
                    min(role_metrics.get('avg_kda', 0) * 20, 100),  # Scale KDA
                    min(role_metrics.get('avg_cs_per_min', 0) * 2, 100),  # Scale CS
                    min(role_metrics.get('avg_vision_score', 0) * 2, 100),  # Scale vision
                    min(role_metrics.get('avg_damage_per_min', 0) / 10, 100),  # Scale damage
                    min(role_metrics.get('avg_gold_per_min', 0) / 10, 100),  # Scale gold
                    (role_metrics.get('recent_form', 0) + 1) * 50  # Scale form (-1 to 1 -> 0 to 100)
                ]
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=role.title(),
                    line_color=colors[i],
                    fillcolor=colors[i],
                    opacity=0.6,
                    hovertemplate="<b>%{theta}</b><br>Value: %{r:.1f}<extra></extra>"
                ))
            
            # Update layout
            fig.update_layout(
                title=config.title,
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        ticksuffix="%"
                    )
                ),
                **self.default_layout,
                height=config.height
            )
            
            # Add drill-down capability
            fig = self._add_drill_down_capability(fig, player_data)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating player performance radar: {e}")
            return self._create_error_chart("Failed to create player performance radar")
    
    def create_team_synergy_heatmap(self, synergy_matrix: Dict[str, Any],
                                  config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create heatmap visualization for team synergy."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.HEATMAP,
                title="Team Synergy Matrix",
                data_source="synergy_data"
            )
        
        try:
            players = synergy_matrix.get('players', [])
            synergy_data = synergy_matrix.get('synergy_scores', {})
            
            if not players:
                return self._create_empty_chart("No player data available")
            
            # Create synergy matrix
            n_players = len(players)
            matrix = np.zeros((n_players, n_players))
            
            for i, player1 in enumerate(players):
                for j, player2 in enumerate(players):
                    if i == j:
                        matrix[i][j] = 1.0  # Perfect synergy with self
                    else:
                        key = tuple(sorted([player1, player2]))
                        matrix[i][j] = synergy_data.get(key, 0.0)
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=matrix,
                x=players,
                y=players,
                colorscale='RdYlGn',
                zmid=0,
                zmin=-1,
                zmax=1,
                hovertemplate="<b>%{y} + %{x}</b><br>Synergy: %{z:.2f}<extra></extra>",
                colorbar=dict(
                    title="Synergy Score"
                )
            ))
            
            # Update layout
            fig.update_layout(
                title=config.title,
                xaxis_title="Player",
                yaxis_title="Player",
                **self.default_layout,
                height=config.height
            )
            
            # Add annotations for better readability
            annotations = []
            for i, player1 in enumerate(players):
                for j, player2 in enumerate(players):
                    if i != j:  # Don't annotate diagonal
                        annotations.append(
                            dict(
                                x=j, y=i,
                                text=f"{matrix[i][j]:.2f}",
                                showarrow=False,
                                font=dict(color="white" if abs(matrix[i][j]) > 0.5 else "black")
                            )
                        )
            
            fig.update_layout(annotations=annotations)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating team synergy heatmap: {e}")
            return self._create_error_chart("Failed to create team synergy heatmap")
    
    def create_champion_recommendation_chart(self, recommendations: List[Dict[str, Any]],
                                           config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create bar chart for champion recommendations."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.BAR,
                title="Champion Recommendations",
                data_source="recommendations"
            )
        
        try:
            if not recommendations:
                return self._create_empty_chart("No recommendations available")
            
            # Sort recommendations by score
            sorted_recs = sorted(recommendations, key=lambda x: x.get('score', 0), reverse=True)
            
            champions = [rec.get('champion_name', 'Unknown') for rec in sorted_recs]
            scores = [rec.get('score', 0) * 100 for rec in sorted_recs]  # Convert to percentage
            confidence = [rec.get('confidence', 0) * 100 for rec in sorted_recs]
            
            # Create bar chart with confidence indicators
            fig = go.Figure()
            
            # Main recommendation bars
            fig.add_trace(go.Bar(
                x=champions,
                y=scores,
                name='Recommendation Score',
                marker_color=self.color_manager.get_color_palette("performance", len(champions)),
                hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}%<extra></extra>",
                text=[f"{score:.1f}%" for score in scores],
                textposition='auto'
            ))
            
            # Confidence indicators as error bars
            fig.add_trace(go.Scatter(
                x=champions,
                y=scores,
                error_y=dict(
                    type='data',
                    array=[(100 - conf) / 4 for conf in confidence],  # Scale confidence to error bar size
                    visible=True,
                    color='rgba(0,0,0,0.3)'
                ),
                mode='markers',
                marker=dict(size=8, color='rgba(0,0,0,0.6)'),
                name='Confidence',
                hovertemplate="<b>%{x}</b><br>Confidence: %{customdata:.1f}%<extra></extra>",
                customdata=confidence,
                showlegend=False
            ))
            
            # Update layout
            fig.update_layout(
                title=config.title,
                xaxis_title="Champion",
                yaxis_title="Recommendation Score (%)",
                **self.default_layout,
                height=config.height,
                yaxis=dict(range=[0, 100])
            )
            
            # Add champion role annotations
            annotations = []
            for i, rec in enumerate(sorted_recs):
                role = rec.get('role', 'Unknown')
                annotations.append(
                    dict(
                        x=i, y=scores[i] + 5,
                        text=role.title(),
                        showarrow=False,
                        font=dict(size=10, color="gray")
                    )
                )
            
            fig.update_layout(annotations=annotations)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating champion recommendation chart: {e}")
            return self._create_error_chart("Failed to create champion recommendation chart")
    
    def create_performance_trend_line(self, trend_data: Dict[str, Any],
                                    config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create line chart for performance trends over time."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.LINE,
                title="Performance Trends",
                data_source="trend_data"
            )
        
        try:
            time_series = trend_data.get('time_series', {})
            metrics = trend_data.get('metrics', ['win_rate'])
            
            if not time_series:
                return self._create_empty_chart("No trend data available")
            
            fig = go.Figure()
            
            colors = self.color_manager.get_color_palette("performance", len(metrics))
            
            for i, metric in enumerate(metrics):
                metric_data = time_series.get(metric, {})
                dates = list(metric_data.keys())
                values = list(metric_data.values())
                
                if dates and values:
                    # Convert string dates to datetime if needed
                    if isinstance(dates[0], str):
                        dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) for date in dates]
                    
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=values,
                        mode='lines+markers',
                        name=metric.replace('_', ' ').title(),
                        line=dict(color=colors[i], width=2),
                        marker=dict(size=6),
                        hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Value: %{y:.2f}<extra></extra>"
                    ))
            
            # Add trend lines
            for i, metric in enumerate(metrics):
                metric_data = time_series.get(metric, {})
                if len(metric_data) > 1:
                    dates = list(metric_data.keys())
                    values = list(metric_data.values())
                    
                    if isinstance(dates[0], str):
                        dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) for date in dates]
                    
                    # Calculate trend line
                    x_numeric = [(date - dates[0]).days for date in dates]
                    z = np.polyfit(x_numeric, values, 1)
                    trend_line = np.poly1d(z)
                    
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=[trend_line(x) for x in x_numeric],
                        mode='lines',
                        name=f'{metric.replace("_", " ").title()} Trend',
                        line=dict(color=colors[i], width=1, dash='dash'),
                        opacity=0.7,
                        showlegend=False,
                        hoverinfo='skip'
                    ))
            
            # Update layout
            layout_config = self.default_layout.copy()
            layout_config.update({
                'title': config.title,
                'xaxis_title': "Date",
                'yaxis_title': "Performance Value",
                'height': config.height,
                'hovermode': 'x unified'
            })
            fig.update_layout(**layout_config)
            
            # Add range selector
            fig.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=7, label="7d", step="day", stepmode="backward"),
                            dict(count=30, label="30d", step="day", stepmode="backward"),
                            dict(count=90, label="90d", step="day", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                )
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating performance trend line: {e}")
            return self._create_error_chart("Failed to create performance trend line")
    
    def create_composition_comparison(self, compositions: List[Dict[str, Any]],
                                   config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create comparison visualization for team compositions."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.BAR,
                title="Team Composition Comparison",
                data_source="compositions"
            )
        
        try:
            if not compositions:
                return self._create_empty_chart("No compositions to compare")
            
            # Extract composition data
            comp_names = [comp.get('name', f'Composition {i+1}') for i, comp in enumerate(compositions)]
            win_rates = [comp.get('win_rate', 0) * 100 for comp in compositions]
            synergy_scores = [comp.get('synergy_score', 0) * 100 for comp in compositions]
            confidence_scores = [comp.get('confidence', 0) * 100 for comp in compositions]
            
            # Create grouped bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Win Rate',
                x=comp_names,
                y=win_rates,
                marker_color=self.color_manager.schemes['performance']['good'],
                hovertemplate="<b>%{x}</b><br>Win Rate: %{y:.1f}%<extra></extra>"
            ))
            
            fig.add_trace(go.Bar(
                name='Synergy Score',
                x=comp_names,
                y=synergy_scores,
                marker_color=self.color_manager.schemes['synergy']['high'],
                hovertemplate="<b>%{x}</b><br>Synergy: %{y:.1f}%<extra></extra>"
            ))
            
            fig.add_trace(go.Bar(
                name='Confidence',
                x=comp_names,
                y=confidence_scores,
                marker_color=self.color_manager.schemes['lol_classic']['accent'],
                hovertemplate="<b>%{x}</b><br>Confidence: %{y:.1f}%<extra></extra>"
            ))
            
            # Update layout
            fig.update_layout(
                title=config.title,
                xaxis_title="Team Composition",
                yaxis_title="Score (%)",
                barmode='group',
                **self.default_layout,
                height=config.height,
                yaxis=dict(range=[0, 100])
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating composition comparison: {e}")
            return self._create_error_chart("Failed to create composition comparison")
    
    def _add_drill_down_capability(self, fig: go.Figure, drill_down_data: Dict[str, Any]) -> go.Figure:
        """Add drill-down interactions to charts."""
        try:
            # Add click event handling for drill-down
            # Note: This would typically be handled by JavaScript in the frontend
            # For now, we'll add the data structure to support it
            
            fig.update_layout(
                clickmode='event+select',
                dragmode='select'
            )
            
            # Store drill-down data in figure metadata
            # Note: Plotly figures don't have a meta attribute by default
            # We'll store it in the figure's layout for now
            fig.update_layout(meta={'drill_down_data': drill_down_data})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error adding drill-down capability: {e}")
            return fig
    
    def _create_error_chart(self, error_message: str) -> go.Figure:
        """Create error chart when visualization fails."""
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="red")
        )
        
        fig.update_layout(
            title="Visualization Error",
            **self.default_layout,
            height=400
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with informative message."""
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
            title="No Data Available",
            **self.default_layout,
            height=300
        )
        
        return fig
    
    def create_player_performance_radar_with_drill_down(self, player_data: Dict[str, Any], 
                                                       role_breakdown: bool = True,
                                                       config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create advanced radar chart with role-specific breakdowns and drill-down."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.RADAR,
                title="Player Performance Analysis",
                data_source="player_performance_detailed"
            )
        
        try:
            player_name = player_data.get('player_name', 'Unknown Player')
            performance_data = player_data.get('performance_by_role', {})
            
            if not performance_data:
                return self._create_empty_chart("No performance data available")
            
            fig = go.Figure()
            
            # Enhanced radar chart categories with more detailed metrics
            categories = [
                'Win Rate', 'KDA Ratio', 'CS/Min', 'Vision Score', 
                'Damage/Min', 'Gold/Min', 'Kill Participation',
                'First Blood Rate', 'Objective Control', 'Recent Form'
            ]
            
            colors = self.color_manager.get_color_palette("lol_classic", len(performance_data))
            
            # Create traces for each role with detailed metrics
            for i, (role, metrics) in enumerate(performance_data.items()):
                # Normalize and calculate advanced metrics
                values = self._calculate_advanced_radar_values(metrics)
                
                # Add confidence intervals as error bars
                confidence_intervals = metrics.get('confidence_intervals', {})
                error_values = [confidence_intervals.get(cat.lower().replace(' ', '_').replace('/', '_'), 0) 
                              for cat in categories]
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=f"{role.title()} (n={metrics.get('games_played', 0)})",
                    line=dict(color=colors[i], width=2),
                    fillcolor=colors[i],
                    opacity=0.3,
                    hovertemplate="<b>%{theta}</b><br>" +
                                 f"Role: {role.title()}<br>" +
                                 "Value: %{r:.1f}<br>" +
                                 "Games: " + str(metrics.get('games_played', 0)) +
                                 "<extra></extra>",
                    customdata=[{
                        'role': role,
                        'category': cat,
                        'raw_value': metrics.get(cat.lower().replace(' ', '_').replace('/', '_'), 0),
                        'percentile': metrics.get(f"{cat.lower().replace(' ', '_').replace('/', '_')}_percentile", 0),
                        'trend': metrics.get(f"{cat.lower().replace(' ', '_').replace('/', '_')}_trend", 'stable')
                    } for cat in categories]
                ))
            
            # Add statistical significance indicators
            if len(performance_data) > 1:
                self._add_significance_indicators(fig, performance_data, categories)
            
            # Enhanced layout with drill-down capabilities
            layout_config = self.default_layout.copy()
            layout_config.update({
                'title': f"{config.title} - {player_name}",
                'polar': dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        ticksuffix="%",
                        gridcolor="rgba(128,128,128,0.3)",
                        linecolor="rgba(128,128,128,0.5)"
                    ),
                    angularaxis=dict(
                        gridcolor="rgba(128,128,128,0.3)",
                        linecolor="rgba(128,128,128,0.5)"
                    )
                ),
                'height': config.height,
                'showlegend': True,
                'legend': dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            })
            fig.update_layout(**layout_config)
            fig.update_layout(**layout_config)
            
            # Store drill-down data
            drill_down_key = f"radar_{player_name}_{datetime.now().isoformat()}"
            self.drill_down_cache[drill_down_key] = {
                'type': 'player_performance_radar',
                'player_data': player_data,
                'detailed_metrics': performance_data,
                'available_breakdowns': ['by_champion', 'by_time_period', 'by_teammate']
            }
            
            # Add drill-down metadata
            fig.update_layout(meta={'drill_down_key': drill_down_key})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating advanced player performance radar: {e}")
            return self._create_error_chart("Failed to create advanced player performance radar")
    
    def create_champion_performance_heatmap_with_significance(self, champion_data: Dict[str, Any],
                                                            config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create champion performance heatmap with statistical significance indicators."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.HEATMAP,
                title="Champion Performance Matrix",
                data_source="champion_performance_stats"
            )
        
        try:
            champions = champion_data.get('champions', [])
            metrics = champion_data.get('metrics', ['win_rate', 'avg_kda', 'pick_rate'])
            performance_matrix = champion_data.get('performance_matrix', {})
            significance_matrix = champion_data.get('significance_matrix', {})
            
            if not champions or not metrics:
                return self._create_empty_chart("No champion performance data available")
            
            # Create performance matrix
            z_values = []
            hover_text = []
            significance_text = []
            
            for champion in champions:
                row_values = []
                row_hover = []
                row_significance = []
                
                for metric in metrics:
                    key = f"{champion}_{metric}"
                    value = performance_matrix.get(key, 0)
                    significance = significance_matrix.get(key, {})
                    
                    row_values.append(value)
                    
                    # Create detailed hover text
                    hover_info = f"<b>{champion}</b><br>"
                    hover_info += f"{metric.replace('_', ' ').title()}: {value:.2f}<br>"
                    
                    if significance:
                        p_value = significance.get('p_value', 1.0)
                        effect_size = significance.get('effect_size', 0.0)
                        sample_size = significance.get('sample_size', 0)
                        
                        hover_info += f"P-value: {p_value:.4f}<br>"
                        hover_info += f"Effect Size: {effect_size:.3f}<br>"
                        hover_info += f"Sample Size: {sample_size}<br>"
                        
                        if p_value < 0.001:
                            sig_level = "***"
                        elif p_value < 0.01:
                            sig_level = "**"
                        elif p_value < 0.05:
                            sig_level = "*"
                        else:
                            sig_level = ""
                        
                        hover_info += f"Significance: {sig_level if sig_level else 'n.s.'}"
                        row_significance.append(sig_level)
                    else:
                        row_significance.append("")
                    
                    row_hover.append(hover_info)
                
                z_values.append(row_values)
                hover_text.append(row_hover)
                significance_text.append(row_significance)
            
            # Create heatmap with custom colorscale
            fig = go.Figure(data=go.Heatmap(
                z=z_values,
                x=[metric.replace('_', ' ').title() for metric in metrics],
                y=champions,
                colorscale='RdYlGn',
                zmid=0.5,  # Assuming normalized values
                zmin=0,
                zmax=1,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,
                colorbar=dict(
                    title="Performance Score"
                )
            ))
            
            # Add significance annotations
            annotations = []
            for i, champion in enumerate(champions):
                for j, metric in enumerate(metrics):
                    if significance_text[i][j]:
                        annotations.append(
                            dict(
                                x=j, y=i,
                                text=significance_text[i][j],
                                showarrow=False,
                                font=dict(
                                    color="white" if z_values[i][j] < 0.5 else "black",
                                    size=16,
                                    family="Arial Black"
                                )
                            )
                        )
            
            # Update layout
            fig.update_layout(
                title=config.title,
                xaxis_title="Performance Metrics",
                yaxis_title="Champions",
                annotations=annotations,
                **self.default_layout,
                height=max(400, len(champions) * 25),  # Dynamic height based on champions
                width=max(600, len(metrics) * 100)     # Dynamic width based on metrics
            )
            
            # Store drill-down data
            drill_down_key = f"champion_heatmap_{datetime.now().isoformat()}"
            self.drill_down_cache[drill_down_key] = {
                'type': 'champion_performance_heatmap',
                'champion_data': champion_data,
                'available_breakdowns': ['by_role', 'by_patch', 'by_elo_range']
            }
            
            fig.update_layout(meta={'drill_down_key': drill_down_key})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating champion performance heatmap: {e}")
            return self._create_error_chart("Failed to create champion performance heatmap")
    
    def create_team_synergy_matrix_interactive(self, synergy_data: Dict[str, Any],
                                             config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create interactive team synergy matrix with exploration capabilities."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.HEATMAP,
                title="Team Synergy Analysis Matrix",
                data_source="synergy_analysis"
            )
        
        try:
            players = synergy_data.get('players', [])
            synergy_matrix = synergy_data.get('synergy_scores', {})
            confidence_matrix = synergy_data.get('confidence_scores', {})
            sample_sizes = synergy_data.get('sample_sizes', {})
            
            if not players:
                return self._create_empty_chart("No synergy data available")
            
            n_players = len(players)
            z_values = np.zeros((n_players, n_players))
            hover_text = []
            
            for i, player1 in enumerate(players):
                row_hover = []
                for j, player2 in enumerate(players):
                    if i == j:
                        z_values[i][j] = 1.0  # Perfect synergy with self
                        hover_info = f"<b>{player1}</b><br>Self-synergy: 100%"
                    else:
                        key = tuple(sorted([player1, player2]))
                        synergy_score = synergy_matrix.get(key, 0.0)
                        confidence = confidence_matrix.get(key, 0.0)
                        sample_size = sample_sizes.get(key, 0)
                        
                        z_values[i][j] = synergy_score
                        
                        # Create detailed hover information
                        hover_info = f"<b>{player1} + {player2}</b><br>"
                        hover_info += f"Synergy Score: {synergy_score:.3f}<br>"
                        hover_info += f"Confidence: {confidence:.1%}<br>"
                        hover_info += f"Games Together: {sample_size}<br>"
                        
                        # Add performance indicators
                        if synergy_score > 0.7:
                            hover_info += "Rating: Excellent Synergy"
                        elif synergy_score > 0.5:
                            hover_info += "Rating: Good Synergy"
                        elif synergy_score > 0.3:
                            hover_info += "Rating: Average Synergy"
                        else:
                            hover_info += "Rating: Poor Synergy"
                    
                    row_hover.append(hover_info)
                hover_text.append(row_hover)
            
            # Create interactive heatmap
            fig = go.Figure(data=go.Heatmap(
                z=z_values,
                x=players,
                y=players,
                colorscale=[
                    [0.0, '#d73027'],    # Poor synergy - Red
                    [0.3, '#fc8d59'],    # Below average - Orange
                    [0.5, '#fee08b'],    # Average - Yellow
                    [0.7, '#d9ef8b'],    # Good - Light Green
                    [1.0, '#91bfdb']     # Excellent - Blue
                ],
                zmid=0.5,
                zmin=0,
                zmax=1,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_text,
                colorbar=dict(
                    title="Synergy Score",
                    tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                    ticktext=['Poor', 'Below Avg', 'Average', 'Good', 'Excellent']
                )
            ))
            
            # Add synergy score annotations
            annotations = []
            for i, player1 in enumerate(players):
                for j, player2 in enumerate(players):
                    if i != j:  # Don't annotate diagonal
                        score = z_values[i][j]
                        color = "white" if score < 0.5 else "black"
                        annotations.append(
                            dict(
                                x=j, y=i,
                                text=f"{score:.2f}",
                                showarrow=False,
                                font=dict(color=color, size=10)
                            )
                        )
            
            # Update layout with interactive features
            fig.update_layout(
                title=config.title,
                xaxis_title="Player",
                yaxis_title="Player",
                annotations=annotations,
                **self.default_layout,
                height=max(500, n_players * 40),
                width=max(500, n_players * 40),
                xaxis=dict(side="bottom"),
                yaxis=dict(autorange="reversed")  # Reverse y-axis for better readability
            )
            
            # Store drill-down data
            drill_down_key = f"synergy_matrix_{datetime.now().isoformat()}"
            self.drill_down_cache[drill_down_key] = {
                'type': 'team_synergy_matrix',
                'synergy_data': synergy_data,
                'available_breakdowns': ['by_champion_pair', 'by_role_combination', 'by_game_phase']
            }
            
            fig.update_layout(meta={'drill_down_key': drill_down_key})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating team synergy matrix: {e}")
            return self._create_error_chart("Failed to create team synergy matrix")
    
    def create_performance_trend_with_predictions(self, trend_data: Dict[str, Any],
                                                config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create performance trend visualization with predictive analytics."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.LINE,
                title="Performance Trends with Predictions",
                data_source="trend_analysis_predictive"
            )
        
        try:
            time_series = trend_data.get('time_series', {})
            predictions = trend_data.get('predictions', {})
            confidence_bands = trend_data.get('confidence_bands', {})
            metrics = trend_data.get('metrics', ['win_rate'])
            
            if not time_series:
                return self._create_empty_chart("No trend data available")
            
            fig = go.Figure()
            colors = self.color_manager.get_color_palette("performance", len(metrics))
            
            for i, metric in enumerate(metrics):
                metric_data = time_series.get(metric, {})
                prediction_data = predictions.get(metric, {})
                confidence_data = confidence_bands.get(metric, {})
                
                if not metric_data:
                    continue
                
                # Historical data
                dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) if isinstance(date, str) else date 
                        for date in metric_data.keys()]
                values = list(metric_data.values())
                
                # Add historical trend line
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name=f'{metric.replace("_", " ").title()} (Historical)',
                    line=dict(color=colors[i], width=3),
                    marker=dict(size=6),
                    hovertemplate="<b>%{fullData.name}</b><br>" +
                                 "Date: %{x}<br>" +
                                 "Value: %{y:.3f}<extra></extra>"
                ))
                
                # Add predictions if available
                if prediction_data:
                    pred_dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) if isinstance(date, str) else date 
                                 for date in prediction_data.keys()]
                    pred_values = list(prediction_data.values())
                    
                    fig.add_trace(go.Scatter(
                        x=pred_dates,
                        y=pred_values,
                        mode='lines+markers',
                        name=f'{metric.replace("_", " ").title()} (Predicted)',
                        line=dict(color=colors[i], width=2, dash='dash'),
                        marker=dict(size=4, symbol='diamond'),
                        hovertemplate="<b>%{fullData.name}</b><br>" +
                                     "Date: %{x}<br>" +
                                     "Predicted: %{y:.3f}<extra></extra>"
                    ))
                
                # Add confidence bands
                if confidence_data:
                    conf_dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) if isinstance(date, str) else date 
                                 for date in confidence_data.keys()]
                    upper_bounds = [conf['upper'] for conf in confidence_data.values()]
                    lower_bounds = [conf['lower'] for conf in confidence_data.values()]
                    
                    # Upper confidence bound
                    fig.add_trace(go.Scatter(
                        x=conf_dates,
                        y=upper_bounds,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    # Lower confidence bound with fill
                    # Extract RGB values from color string for transparency
                    if colors[i].startswith('rgb('):
                        rgb_values = colors[i][4:-1]
                        fill_color = f'rgba({rgb_values}, 0.2)'
                    elif colors[i].startswith('#'):
                        # Convert hex to RGB
                        hex_color = colors[i].lstrip('#')
                        rgb = tuple(int(hex_color[j:j+2], 16) for j in (0, 2, 4))
                        fill_color = f'rgba({rgb[0]},{rgb[1]},{rgb[2]}, 0.2)'
                    else:
                        fill_color = 'rgba(128,128,128, 0.2)'  # Fallback
                    
                    fig.add_trace(go.Scatter(
                        x=conf_dates,
                        y=lower_bounds,
                        mode='lines',
                        line=dict(width=0),
                        fill='tonexty',
                        fillcolor=fill_color,
                        name=f'{metric.replace("_", " ").title()} Confidence',
                        hovertemplate="<b>Confidence Band</b><br>" +
                                     "Date: %{x}<br>" +
                                     "Range: %{y:.3f} - %{customdata:.3f}<extra></extra>",
                        customdata=upper_bounds
                    ))
                
                # Add trend analysis annotations
                if len(values) > 1:
                    recent_trend = self._calculate_trend_direction(values[-5:] if len(values) >= 5 else values)
                    trend_color = "green" if recent_trend > 0 else "red" if recent_trend < 0 else "gray"
                    trend_text = "↗" if recent_trend > 0 else "↘" if recent_trend < 0 else "→"
                    
                    fig.add_annotation(
                        x=dates[-1],
                        y=values[-1],
                        text=f"{trend_text} {abs(recent_trend):.1%}",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor=trend_color,
                        font=dict(color=trend_color, size=12)
                    )
            
            # Update layout with enhanced features
            layout_config = self.default_layout.copy()
            layout_config.update({
                'title': config.title,
                'xaxis_title': "Date",
                'yaxis_title': "Performance Value",
                'height': config.height,
                'hovermode': 'x unified',
                'xaxis': dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=7, label="7d", step="day", stepmode="backward"),
                            dict(count=30, label="30d", step="day", stepmode="backward"),
                            dict(count=90, label="90d", step="day", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                )
            })
            fig.update_layout(**layout_config)
            
            # Store drill-down data
            drill_down_key = f"trend_analysis_{datetime.now().isoformat()}"
            self.drill_down_cache[drill_down_key] = {
                'type': 'performance_trend_predictive',
                'trend_data': trend_data,
                'available_breakdowns': ['by_metric', 'by_time_granularity', 'prediction_details']
            }
            
            fig.update_layout(meta={'drill_down_key': drill_down_key})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating performance trend with predictions: {e}")
            return self._create_error_chart("Failed to create performance trend visualization")
    
    def create_comparative_analysis_chart(self, comparison_data: Dict[str, Any],
                                        config: Optional[ChartConfiguration] = None) -> go.Figure:
        """Create comparative analysis charts for multiple players or time periods."""
        if config is None:
            config = ChartConfiguration(
                chart_type=ChartType.BAR,
                title="Comparative Performance Analysis",
                data_source="comparative_analysis"
            )
        
        try:
            comparison_type = comparison_data.get('comparison_type', 'players')  # 'players' or 'time_periods'
            entities = comparison_data.get('entities', [])  # Players or time periods
            metrics = comparison_data.get('metrics', [])
            performance_data = comparison_data.get('performance_data', {})
            statistical_tests = comparison_data.get('statistical_tests', {})
            
            if not entities or not metrics:
                return self._create_empty_chart("No comparison data available")
            
            # Create subplots for multiple metrics
            subplot_titles = [metric.replace('_', ' ').title() for metric in metrics]
            fig = make_subplots(
                rows=len(metrics),
                cols=1,
                subplot_titles=subplot_titles,
                vertical_spacing=0.1
            )
            
            colors = self.color_manager.get_color_palette("lol_classic", len(entities))
            
            for metric_idx, metric in enumerate(metrics):
                metric_values = []
                error_values = []
                hover_texts = []
                
                for entity in entities:
                    key = f"{entity}_{metric}"
                    value = performance_data.get(key, {})
                    
                    mean_value = value.get('mean', 0)
                    std_error = value.get('std_error', 0)
                    sample_size = value.get('sample_size', 0)
                    
                    metric_values.append(mean_value)
                    error_values.append(std_error)
                    
                    # Create detailed hover text
                    hover_text = f"<b>{entity}</b><br>"
                    hover_text += f"{metric.replace('_', ' ').title()}: {mean_value:.3f}<br>"
                    hover_text += f"Std Error: ±{std_error:.3f}<br>"
                    hover_text += f"Sample Size: {sample_size}<br>"
                    
                    # Add statistical significance if available
                    stat_test = statistical_tests.get(f"{metric}_{entity}", {})
                    if stat_test:
                        p_value = stat_test.get('p_value', 1.0)
                        effect_size = stat_test.get('effect_size', 0.0)
                        
                        if p_value < 0.001:
                            sig_marker = "***"
                        elif p_value < 0.01:
                            sig_marker = "**"
                        elif p_value < 0.05:
                            sig_marker = "*"
                        else:
                            sig_marker = "n.s."
                        
                        hover_text += f"Significance: {sig_marker}<br>"
                        hover_text += f"Effect Size: {effect_size:.3f}"
                    
                    hover_texts.append(hover_text)
                
                # Add bar chart for this metric
                fig.add_trace(
                    go.Bar(
                        x=entities,
                        y=metric_values,
                        error_y=dict(type='data', array=error_values, visible=True),
                        name=metric.replace('_', ' ').title(),
                        marker_color=colors,
                        hovertemplate="%{customdata}<extra></extra>",
                        customdata=hover_texts,
                        showlegend=(metric_idx == 0)  # Only show legend for first metric
                    ),
                    row=metric_idx + 1,
                    col=1
                )
                
                # Add significance annotations
                max_value = max(metric_values) if metric_values else 0
                for i, entity in enumerate(entities):
                    stat_test = statistical_tests.get(f"{metric}_{entity}", {})
                    if stat_test:
                        p_value = stat_test.get('p_value', 1.0)
                        if p_value < 0.05:
                            sig_marker = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*"
                            fig.add_annotation(
                                x=i,
                                y=metric_values[i] + error_values[i] + max_value * 0.05,
                                text=sig_marker,
                                showarrow=False,
                                font=dict(size=14, color="red"),
                                row=metric_idx + 1,
                                col=1
                            )
            
            # Update layout
            layout_config = self.default_layout.copy()
            layout_config.update({
                'title': config.title,
                'height': max(400, len(metrics) * 200),
                'showlegend': True
            })
            fig.update_layout(**layout_config)
            
            # Update x and y axis labels
            for i in range(len(metrics)):
                fig.update_xaxes(title_text=comparison_type.title(), row=i + 1, col=1)
                fig.update_yaxes(title_text="Performance Value", row=i + 1, col=1)
            
            # Store drill-down data
            drill_down_key = f"comparative_analysis_{datetime.now().isoformat()}"
            self.drill_down_cache[drill_down_key] = {
                'type': 'comparative_analysis',
                'comparison_data': comparison_data,
                'available_breakdowns': ['detailed_statistics', 'pairwise_comparisons', 'effect_sizes']
            }
            
            fig.update_layout(meta={'drill_down_key': drill_down_key})
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating comparative analysis chart: {e}")
            return self._create_error_chart("Failed to create comparative analysis chart")
    
    def export_chart(self, fig: go.Figure, filename: str, format: str = 'png', 
                    width: int = 1200, height: int = 800) -> str:
        """Export chart in multiple formats."""
        try:
            if format not in self.export_formats:
                raise ValueError(f"Unsupported export format: {format}")
            
            export_path = f"{filename}.{format}"
            
            if format == 'png':
                fig.write_image(export_path, width=width, height=height, format='png')
            elif format == 'svg':
                fig.write_image(export_path, width=width, height=height, format='svg')
            elif format == 'pdf':
                fig.write_image(export_path, width=width, height=height, format='pdf')
            elif format == 'html':
                fig.write_html(export_path, include_plotlyjs=True)
            elif format == 'json':
                fig.write_json(export_path)
            
            self.logger.info(f"Chart exported successfully to {export_path}")
            return export_path
            
        except Exception as e:
            self.logger.error(f"Error exporting chart: {e}")
            raise
    
    def get_drill_down_data(self, drill_down_key: str, breakdown_type: str) -> Dict[str, Any]:
        """Get drill-down data for interactive exploration."""
        try:
            if drill_down_key not in self.drill_down_cache:
                raise ValueError(f"Drill-down key not found: {drill_down_key}")
            
            cached_data = self.drill_down_cache[drill_down_key]
            
            if breakdown_type not in cached_data.get('available_breakdowns', []):
                raise ValueError(f"Breakdown type not available: {breakdown_type}")
            
            # Return appropriate drill-down data based on type
            return {
                'breakdown_type': breakdown_type,
                'data': cached_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting drill-down data: {e}")
            return {}
    
    def _calculate_advanced_radar_values(self, metrics: Dict[str, Any]) -> List[float]:
        """Calculate normalized values for advanced radar chart."""
        try:
            # Extract and normalize metrics to 0-100 scale
            win_rate = metrics.get('win_rate', 0) * 100
            kda = min(metrics.get('avg_kda', 0) * 20, 100)
            cs_per_min = min(metrics.get('avg_cs_per_min', 0) * 2, 100)
            vision_score = min(metrics.get('avg_vision_score', 0) * 2, 100)
            damage_per_min = min(metrics.get('avg_damage_per_min', 0) / 10, 100)
            gold_per_min = min(metrics.get('avg_gold_per_min', 0) / 10, 100)
            kill_participation = metrics.get('kill_participation', 0) * 100
            first_blood_rate = metrics.get('first_blood_rate', 0) * 100
            objective_control = metrics.get('objective_control_score', 0) * 100
            recent_form = (metrics.get('recent_form', 0) + 1) * 50  # -1 to 1 -> 0 to 100
            
            return [win_rate, kda, cs_per_min, vision_score, damage_per_min, 
                   gold_per_min, kill_participation, first_blood_rate, 
                   objective_control, recent_form]
            
        except Exception as e:
            self.logger.error(f"Error calculating radar values: {e}")
            return [0] * 10
    
    def _add_significance_indicators(self, fig: go.Figure, performance_data: Dict[str, Any], 
                                   categories: List[str]) -> None:
        """Add statistical significance indicators to radar chart."""
        try:
            # This would add visual indicators for statistically significant differences
            # between roles or other comparisons
            pass
        except Exception as e:
            self.logger.error(f"Error adding significance indicators: {e}")
    
    def _calculate_trend_direction(self, values: List[float]) -> float:
        """Calculate trend direction and strength."""
        try:
            if len(values) < 2:
                return 0.0
            
            # Simple linear regression slope
            n = len(values)
            x = list(range(n))
            
            x_mean = sum(x) / n
            y_mean = sum(values) / n
            
            numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return 0.0
            
            slope = numerator / denominator
            
            # Normalize slope to percentage change
            if y_mean != 0:
                return (slope * (n - 1)) / y_mean
            else:
                return 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating trend direction: {e}")
            return 0.0


class InteractiveChartBuilder:
    """Builds interactive charts with filtering and drill-down capabilities."""
    
    def __init__(self, visualization_manager: VisualizationManager):
        """Initialize interactive chart builder."""
        self.viz_manager = visualization_manager
        self.logger = logging.getLogger(__name__)
        self.active_filters = {}
        self.drill_down_history = []
    
    def build_filterable_chart(self, data: Dict[str, Any], chart_type: str,
                             filters: List[str]) -> Tuple[go.Figure, List[gr.Component]]:
        """Build chart with associated filter components."""
        try:
            # Create filter components
            filter_components = self._create_filter_components(filters, data)
            
            # Create initial chart
            chart_config = ChartConfiguration(
                chart_type=ChartType(chart_type),
                title=data.get('title', 'Interactive Chart'),
                data_source=data.get('source', 'unknown'),
                filters=filters
            )
            
            # Route to appropriate chart creation method
            try:
                chart_type_enum = ChartType(chart_type)
                if chart_type_enum == ChartType.RADAR:
                    fig = self.viz_manager.create_player_performance_radar(data, chart_config)
                elif chart_type_enum == ChartType.HEATMAP:
                    fig = self.viz_manager.create_team_synergy_heatmap(data, chart_config)
                elif chart_type_enum == ChartType.BAR:
                    fig = self.viz_manager.create_champion_recommendation_chart(data.get('recommendations', []), chart_config)
                elif chart_type_enum == ChartType.LINE:
                    fig = self.viz_manager.create_performance_trend_line(data, chart_config)
                else:
                    fig = self.viz_manager._create_error_chart(f"Unsupported chart type: {chart_type}")
            except ValueError:
                fig = self.viz_manager._create_error_chart(f"Unsupported chart type: {chart_type}")
            
            return fig, filter_components
            
        except Exception as e:
            self.logger.error(f"Error building filterable chart: {e}")
            error_fig = self.viz_manager._create_error_chart("Failed to build interactive chart")
            return error_fig, []
    
    def add_drill_down_capability(self, fig: go.Figure, drill_down_data: Dict[str, Any]) -> go.Figure:
        """Add drill-down interactions to charts with enhanced functionality."""
        try:
            # Enhanced drill-down with click event handling
            fig.update_layout(
                clickmode='event+select',
                dragmode='select'
            )
            
            # Add custom JavaScript for drill-down interactions
            # Note: This would be handled by the frontend in a real implementation
            drill_down_config = {
                'enabled': True,
                'levels': drill_down_data.get('available_breakdowns', []),
                'current_level': 0,
                'data_key': drill_down_data.get('data_key', ''),
                'interaction_modes': ['click', 'hover', 'select']
            }
            
            # Store drill-down configuration in figure metadata
            current_meta = fig.layout.meta or {}
            current_meta.update({
                'drill_down_config': drill_down_config,
                'drill_down_data': drill_down_data
            })
            fig.update_layout(meta=current_meta)
            
            # Add drill-down indicators to chart elements
            self._add_drill_down_indicators(fig, drill_down_data)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error adding drill-down capability: {e}")
            return fig
    
    def handle_drill_down_event(self, chart_id: str, click_data: Dict[str, Any]) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down events and return updated chart."""
        try:
            # Extract click information
            point_data = click_data.get('points', [{}])[0]
            x_value = point_data.get('x')
            y_value = point_data.get('y')
            trace_name = point_data.get('fullData', {}).get('name', '')
            
            # Get drill-down data from cache
            drill_down_key = click_data.get('drill_down_key', '')
            if not drill_down_key or drill_down_key not in self.viz_manager.drill_down_cache:
                return None, {'error': 'No drill-down data available'}
            
            cached_data = self.viz_manager.drill_down_cache[drill_down_key]
            chart_type = cached_data.get('type', '')
            
            # Route to appropriate drill-down handler
            if chart_type == 'player_performance_radar':
                return self._handle_radar_drill_down(cached_data, x_value, y_value, trace_name)
            elif chart_type == 'champion_performance_heatmap':
                return self._handle_heatmap_drill_down(cached_data, x_value, y_value)
            elif chart_type == 'team_synergy_matrix':
                return self._handle_synergy_drill_down(cached_data, x_value, y_value)
            elif chart_type == 'performance_trend_predictive':
                return self._handle_trend_drill_down(cached_data, x_value, y_value)
            elif chart_type == 'comparative_analysis':
                return self._handle_comparative_drill_down(cached_data, x_value, y_value)
            else:
                return None, {'error': f'Unsupported chart type for drill-down: {chart_type}'}
            
        except Exception as e:
            self.logger.error(f"Error handling drill-down event: {e}")
            return None, {'error': str(e)}
    
    def create_drill_down_breadcrumb(self) -> List[Dict[str, str]]:
        """Create breadcrumb navigation for drill-down levels."""
        try:
            breadcrumbs = []
            for i, level in enumerate(self.drill_down_history):
                breadcrumbs.append({
                    'level': i,
                    'title': level.get('title', f'Level {i}'),
                    'description': level.get('description', ''),
                    'active': i == len(self.drill_down_history) - 1
                })
            return breadcrumbs
        except Exception as e:
            self.logger.error(f"Error creating drill-down breadcrumb: {e}")
            return []
    
    def _create_filter_components(self, filters: List[str], data: Dict[str, Any]) -> List[gr.Component]:
        """Create Gradio components for chart filters."""
        components = []
        
        for filter_name in filters:
            if filter_name == "player":
                players = data.get('available_players', [])
                component = gr.Dropdown(
                    choices=players,
                    label="Player Filter",
                    multiselect=True,
                    value=players[:3] if len(players) > 3 else players
                )
                components.append(component)
                
            elif filter_name == "champion":
                champions = data.get('available_champions', [])
                component = gr.Dropdown(
                    choices=champions,
                    label="Champion Filter",
                    multiselect=True
                )
                components.append(component)
                
            elif filter_name == "role":
                component = gr.CheckboxGroup(
                    choices=["Top", "Jungle", "Middle", "Bottom", "Support"],
                    label="Role Filter",
                    value=["Top", "Jungle", "Middle", "Bottom", "Support"]
                )
                components.append(component)
                
            elif filter_name == "date_range":
                start_date = gr.Textbox(
                    label="Start Date",
                    placeholder="YYYY-MM-DD"
                )
                end_date = gr.Textbox(
                    label="End Date",
                    placeholder="YYYY-MM-DD"
                )
                components.extend([start_date, end_date])
                
            elif filter_name == "metric":
                metrics = data.get('available_metrics', ['win_rate', 'kda', 'cs_per_min'])
                component = gr.CheckboxGroup(
                    choices=[metric.replace('_', ' ').title() for metric in metrics],
                    label="Metrics",
                    value=[metrics[0].replace('_', ' ').title()] if metrics else []
                )
                components.append(component)
                
        return components
    
    def _add_drill_down_indicators(self, fig: go.Figure, drill_down_data: Dict[str, Any]) -> None:
        """Add visual indicators for drill-down capability."""
        try:
            # Add subtle visual cues that elements are clickable
            # This could include cursor changes, hover effects, etc.
            
            # Add drill-down instruction annotation
            fig.add_annotation(
                text="💡 Click on chart elements to drill down for more details",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                xanchor='left', yanchor='top',
                showarrow=False,
                font=dict(size=10, color="gray"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            )
            
        except Exception as e:
            self.logger.error(f"Error adding drill-down indicators: {e}")
    
    def _handle_radar_drill_down(self, cached_data: Dict[str, Any], x_value: Any, 
                                y_value: Any, trace_name: str) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down for radar charts."""
        try:
            player_data = cached_data.get('player_data', {})
            detailed_metrics = cached_data.get('detailed_metrics', {})
            
            # Extract role from trace name
            role = trace_name.split(' (')[0].lower() if '(' in trace_name else 'overall'
            
            # Create detailed breakdown for the selected role
            role_data = detailed_metrics.get(role, {})
            
            # Create a detailed bar chart for the specific role
            categories = ['Win Rate', 'KDA Ratio', 'CS/Min', 'Vision Score', 
                         'Damage/Min', 'Gold/Min', 'Kill Participation',
                         'First Blood Rate', 'Objective Control', 'Recent Form']
            
            values = self.viz_manager._calculate_advanced_radar_values(role_data)
            
            fig = go.Figure(data=go.Bar(
                x=categories,
                y=values,
                marker_color=self.viz_manager.color_manager.get_color_palette("performance", len(categories)),
                hovertemplate="<b>%{x}</b><br>Value: %{y:.1f}%<extra></extra>"
            ))
            
            fig.update_layout(
                title=f"Detailed Performance Breakdown - {role.title()} Role",
                xaxis_title="Performance Metrics",
                yaxis_title="Performance Score (%)",
                **self.viz_manager.default_layout,
                height=500
            )
            
            # Add to drill-down history
            self.drill_down_history.append({
                'title': f'{role.title()} Role Details',
                'description': f'Detailed breakdown for {role} role performance',
                'level': 'role_detail'
            })
            
            return fig, {'success': True, 'level': 'role_detail'}
            
        except Exception as e:
            self.logger.error(f"Error handling radar drill-down: {e}")
            return None, {'error': str(e)}
    
    def _handle_heatmap_drill_down(self, cached_data: Dict[str, Any], x_value: Any, 
                                  y_value: Any) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down for heatmap charts."""
        try:
            champion_data = cached_data.get('champion_data', {})
            
            # Get the selected champion and metric
            champions = champion_data.get('champions', [])
            metrics = champion_data.get('metrics', [])
            
            if isinstance(x_value, int) and 0 <= x_value < len(metrics):
                selected_metric = metrics[x_value]
            else:
                selected_metric = x_value if x_value in metrics else metrics[0] if metrics else 'win_rate'
            
            if isinstance(y_value, int) and 0 <= y_value < len(champions):
                selected_champion = champions[y_value]
            else:
                selected_champion = y_value if y_value in champions else champions[0] if champions else 'Unknown'
            
            # Create detailed time series for the selected champion and metric
            time_series_data = champion_data.get('time_series', {}).get(f"{selected_champion}_{selected_metric}", {})
            
            if time_series_data:
                dates = [datetime.fromisoformat(date.replace('Z', '+00:00')) if isinstance(date, str) else date 
                        for date in time_series_data.keys()]
                values = list(time_series_data.values())
                
                fig = go.Figure(data=go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name=f'{selected_champion} - {selected_metric.replace("_", " ").title()}',
                    line=dict(width=3),
                    marker=dict(size=8),
                    hovertemplate="<b>%{fullData.name}</b><br>Date: %{x}<br>Value: %{y:.3f}<extra></extra>"
                ))
                
                fig.update_layout(
                    title=f"{selected_champion} - {selected_metric.replace('_', ' ').title()} Over Time",
                    xaxis_title="Date",
                    yaxis_title=selected_metric.replace('_', ' ').title(),
                    **self.viz_manager.default_layout,
                    height=500
                )
            else:
                # Create a placeholder chart if no time series data
                fig = self.viz_manager._create_empty_chart(
                    f"No time series data available for {selected_champion} - {selected_metric}"
                )
            
            # Add to drill-down history
            self.drill_down_history.append({
                'title': f'{selected_champion} Details',
                'description': f'Time series for {selected_metric.replace("_", " ").title()}',
                'level': 'champion_detail'
            })
            
            return fig, {'success': True, 'level': 'champion_detail'}
            
        except Exception as e:
            self.logger.error(f"Error handling heatmap drill-down: {e}")
            return None, {'error': str(e)}
    
    def _handle_synergy_drill_down(self, cached_data: Dict[str, Any], x_value: Any, 
                                  y_value: Any) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down for synergy matrix charts."""
        try:
            synergy_data = cached_data.get('synergy_data', {})
            players = synergy_data.get('players', [])
            
            # Get the selected player pair
            if isinstance(x_value, int) and 0 <= x_value < len(players):
                player1 = players[x_value]
            else:
                player1 = x_value if x_value in players else players[0] if players else 'Unknown'
            
            if isinstance(y_value, int) and 0 <= y_value < len(players):
                player2 = players[y_value]
            else:
                player2 = y_value if y_value in players else players[0] if players else 'Unknown'
            
            if player1 == player2:
                # Show individual player performance
                player_performance = synergy_data.get('individual_performance', {}).get(player1, {})
                
                metrics = ['Win Rate', 'Avg KDA', 'CS/Min', 'Vision Score', 'Damage/Min']
                values = [
                    player_performance.get('win_rate', 0) * 100,
                    player_performance.get('avg_kda', 0) * 20,
                    player_performance.get('avg_cs_per_min', 0) * 2,
                    player_performance.get('avg_vision_score', 0) * 2,
                    player_performance.get('avg_damage_per_min', 0) / 10
                ]
                
                fig = go.Figure(data=go.Bar(
                    x=metrics,
                    y=values,
                    marker_color=self.viz_manager.color_manager.get_color_palette("performance", len(metrics)),
                    hovertemplate="<b>%{x}</b><br>Value: %{y:.1f}<extra></extra>"
                ))
                
                fig.update_layout(
                    title=f"Individual Performance - {player1}",
                    xaxis_title="Performance Metrics",
                    yaxis_title="Performance Score",
                    **self.viz_manager.default_layout,
                    height=500
                )
                
                drill_down_title = f'{player1} Individual Performance'
                drill_down_description = f'Detailed performance metrics for {player1}'
                
            else:
                # Show detailed synergy analysis for the pair
                pair_key = tuple(sorted([player1, player2]))
                pair_data = synergy_data.get('detailed_synergy', {}).get(pair_key, {})
                
                # Create champion combination analysis
                champion_pairs = pair_data.get('champion_combinations', {})
                
                if champion_pairs:
                    combinations = list(champion_pairs.keys())
                    synergy_scores = [champion_pairs[combo].get('synergy_score', 0) for combo in combinations]
                    win_rates = [champion_pairs[combo].get('win_rate', 0) * 100 for combo in combinations]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        name='Synergy Score',
                        x=combinations,
                        y=synergy_scores,
                        yaxis='y',
                        marker_color='blue',
                        opacity=0.7
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='Win Rate (%)',
                        x=combinations,
                        y=win_rates,
                        yaxis='y2',
                        marker_color='green',
                        opacity=0.7
                    ))
                    
                    fig.update_layout(
                        title=f"Champion Synergy Analysis - {player1} & {player2}",
                        xaxis_title="Champion Combinations",
                        yaxis=dict(title="Synergy Score", side="left"),
                        yaxis2=dict(title="Win Rate (%)", side="right", overlaying="y"),
                        **self.viz_manager.default_layout,
                        height=500
                    )
                else:
                    fig = self.viz_manager._create_empty_chart(
                        f"No detailed synergy data available for {player1} & {player2}"
                    )
                
                drill_down_title = f'{player1} & {player2} Synergy'
                drill_down_description = f'Detailed synergy analysis for the player pair'
            
            # Add to drill-down history
            self.drill_down_history.append({
                'title': drill_down_title,
                'description': drill_down_description,
                'level': 'synergy_detail'
            })
            
            return fig, {'success': True, 'level': 'synergy_detail'}
            
        except Exception as e:
            self.logger.error(f"Error handling synergy drill-down: {e}")
            return None, {'error': str(e)}
    
    def _handle_trend_drill_down(self, cached_data: Dict[str, Any], x_value: Any, 
                                y_value: Any) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down for trend charts."""
        try:
            trend_data = cached_data.get('trend_data', {})
            
            # Create detailed statistical analysis for the selected point
            selected_date = x_value
            
            # Get all metrics for the selected date
            time_series = trend_data.get('time_series', {})
            metrics_at_date = {}
            
            for metric, series in time_series.items():
                if selected_date in series:
                    metrics_at_date[metric] = series[selected_date]
            
            if metrics_at_date:
                metrics = list(metrics_at_date.keys())
                values = list(metrics_at_date.values())
                
                fig = go.Figure(data=go.Bar(
                    x=[metric.replace('_', ' ').title() for metric in metrics],
                    y=values,
                    marker_color=self.viz_manager.color_manager.get_color_palette("performance", len(metrics)),
                    hovertemplate="<b>%{x}</b><br>Value: %{y:.3f}<extra></extra>"
                ))
                
                fig.update_layout(
                    title=f"Performance Snapshot - {selected_date}",
                    xaxis_title="Metrics",
                    yaxis_title="Performance Value",
                    **self.viz_manager.default_layout,
                    height=500
                )
            else:
                fig = self.viz_manager._create_empty_chart(
                    f"No data available for {selected_date}"
                )
            
            # Add to drill-down history
            self.drill_down_history.append({
                'title': f'Performance Snapshot',
                'description': f'Detailed metrics for {selected_date}',
                'level': 'trend_detail'
            })
            
            return fig, {'success': True, 'level': 'trend_detail'}
            
        except Exception as e:
            self.logger.error(f"Error handling trend drill-down: {e}")
            return None, {'error': str(e)}
    
    def _handle_comparative_drill_down(self, cached_data: Dict[str, Any], x_value: Any, 
                                      y_value: Any) -> Tuple[go.Figure, Dict[str, Any]]:
        """Handle drill-down for comparative analysis charts."""
        try:
            comparison_data = cached_data.get('comparison_data', {})
            entities = comparison_data.get('entities', [])
            
            # Get the selected entity
            if isinstance(x_value, int) and 0 <= x_value < len(entities):
                selected_entity = entities[x_value]
            else:
                selected_entity = x_value if x_value in entities else entities[0] if entities else 'Unknown'
            
            # Create detailed statistical breakdown for the selected entity
            entity_stats = comparison_data.get('detailed_stats', {}).get(selected_entity, {})
            
            if entity_stats:
                stats_names = list(entity_stats.keys())
                stats_values = list(entity_stats.values())
                
                fig = go.Figure(data=go.Bar(
                    x=stats_names,
                    y=stats_values,
                    marker_color=self.viz_manager.color_manager.get_color_palette("lol_classic", len(stats_names)),
                    hovertemplate="<b>%{x}</b><br>Value: %{y:.3f}<extra></extra>"
                ))
                
                fig.update_layout(
                    title=f"Detailed Statistics - {selected_entity}",
                    xaxis_title="Statistical Measures",
                    yaxis_title="Value",
                    **self.viz_manager.default_layout,
                    height=500
                )
            else:
                fig = self.viz_manager._create_empty_chart(
                    f"No detailed statistics available for {selected_entity}"
                )
            
            # Add to drill-down history
            self.drill_down_history.append({
                'title': f'{selected_entity} Details',
                'description': f'Detailed statistical breakdown',
                'level': 'comparative_detail'
            })
            
            return fig, {'success': True, 'level': 'comparative_detail'}
            
        except Exception as e:
            self.logger.error(f"Error handling comparative drill-down: {e}")
            return None, {'error': str(e)}
        
        return components
    
    def update_chart_with_filters(self, original_data: Dict[str, Any], 
                                filter_values: Dict[str, Any]) -> go.Figure:
        """Update chart based on filter selections."""
        try:
            # Apply filters to data
            filtered_data = self._apply_filters(original_data, filter_values)
            
            # Recreate chart with filtered data
            chart_type = filtered_data.get('chart_type', 'bar')
            config = ChartConfiguration(
                chart_type=ChartType(chart_type),
                title=filtered_data.get('title', 'Filtered Chart'),
                data_source=filtered_data.get('source', 'filtered')
            )
            
            # Route to appropriate chart creation method
            try:
                chart_type_enum = ChartType(chart_type)
                if chart_type_enum == ChartType.RADAR:
                    return self.viz_manager.create_player_performance_radar(filtered_data, config)
                elif chart_type_enum == ChartType.HEATMAP:
                    return self.viz_manager.create_team_synergy_heatmap(filtered_data, config)
                elif chart_type_enum == ChartType.BAR:
                    return self.viz_manager.create_champion_recommendation_chart(
                        filtered_data.get('recommendations', []), config
                    )
                elif chart_type_enum == ChartType.LINE:
                    return self.viz_manager.create_performance_trend_line(filtered_data, config)
                else:
                    return self.viz_manager._create_error_chart(f"Unsupported chart type: {chart_type}")
            except ValueError:
                return self.viz_manager._create_error_chart(f"Unsupported chart type: {chart_type}")
                
        except Exception as e:
            self.logger.error(f"Error updating chart with filters: {e}")
            return self.viz_manager._create_error_chart("Failed to apply filters")
    
    def _apply_filters(self, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filter values to data."""
        filtered_data = data.copy()
        
        # Apply player filter
        if 'player' in filters and filters['player']:
            selected_players = filters['player']
            if 'performance_metrics' in filtered_data:
                filtered_metrics = {}
                for player in selected_players:
                    if player in filtered_data['performance_metrics']:
                        filtered_metrics[player] = filtered_data['performance_metrics'][player]
                filtered_data['performance_metrics'] = filtered_metrics
        
        # Apply champion filter
        if 'champion' in filters and filters['champion']:
            selected_champions = filters['champion']
            if 'recommendations' in filtered_data:
                filtered_recs = [
                    rec for rec in filtered_data['recommendations']
                    if rec.get('champion_name') in selected_champions
                ]
                filtered_data['recommendations'] = filtered_recs
        
        # Apply role filter
        if 'role' in filters and filters['role']:
            selected_roles = [role.lower() for role in filters['role']]
            if 'roles' in filtered_data:
                filtered_data['roles'] = [
                    role for role in filtered_data['roles']
                    if role.lower() in selected_roles
                ]
        
        # Apply date range filter
        if 'start_date' in filters and 'end_date' in filters:
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            
            if start_date and end_date:
                try:
                    start_dt = datetime.fromisoformat(start_date)
                    end_dt = datetime.fromisoformat(end_date)
                    
                    # Filter time series data
                    if 'time_series' in filtered_data:
                        filtered_series = {}
                        for metric, series_data in filtered_data['time_series'].items():
                            filtered_series[metric] = {
                                date: value for date, value in series_data.items()
                                if start_dt <= datetime.fromisoformat(date.replace('Z', '+00:00')) <= end_dt
                            }
                        filtered_data['time_series'] = filtered_series
                        
                except ValueError as e:
                    self.logger.warning(f"Invalid date format in filters: {e}")
        
        return filtered_data
    
    def create_dashboard_layout(self, charts: List[Tuple[go.Figure, str]]) -> gr.Blocks:
        """Create dashboard layout with multiple charts."""
        try:
            with gr.Blocks(title="Analytics Dashboard") as dashboard:
                gr.Markdown("# Analytics Dashboard")
                
                # Create tabs for different chart categories
                with gr.Tabs():
                    chart_categories = {}
                    
                    # Group charts by category
                    for fig, category in charts:
                        if category not in chart_categories:
                            chart_categories[category] = []
                        chart_categories[category].append(fig)
                    
                    # Create tab for each category
                    for category, category_charts in chart_categories.items():
                        with gr.Tab(category.title()):
                            # Create grid layout for charts in this category
                            if len(category_charts) == 1:
                                gr.Plot(category_charts[0])
                            elif len(category_charts) == 2:
                                with gr.Row():
                                    with gr.Column():
                                        gr.Plot(category_charts[0])
                                    with gr.Column():
                                        gr.Plot(category_charts[1])
                            else:
                                # Create grid for more charts
                                charts_per_row = 2
                                for i in range(0, len(category_charts), charts_per_row):
                                    with gr.Row():
                                        for j in range(charts_per_row):
                                            if i + j < len(category_charts):
                                                with gr.Column():
                                                    gr.Plot(category_charts[i + j])
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error creating dashboard layout: {e}")
            # Return simple fallback dashboard
            with gr.Blocks(title="Dashboard Error") as error_dashboard:
                gr.Markdown("# Dashboard Error")
                gr.Markdown(f"Failed to create dashboard: {str(e)}")
            return error_dashboard