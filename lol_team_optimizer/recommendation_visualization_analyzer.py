# -*- coding: utf-8 -*-
"""
Recommendation Visualization and Analysis Tools

This module provides comprehensive visualization and analysis tools for champion
recommendations, including confidence visualization, synergy analysis charts,
comparison matrices, trend analysis, success rate tracking, and export functionality.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics
import numpy as np

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    # Create mock objects for when plotly is not available
    class MockFigure:
        def __init__(self):
            pass
        def add_trace(self, *args, **kwargs):
            pass
        def update_layout(self, *args, **kwargs):
            pass
        def update_xaxes(self, *args, **kwargs):
            pass
        def update_yaxes(self, *args, **kwargs):
            pass
        def add_annotation(self, *args, **kwargs):
            pass
        def write_html(self, *args, **kwargs):
            pass
    
    class MockGo:
        Figure = MockFigure
        Bar = lambda *args, **kwargs: None
        Scatter = lambda *args, **kwargs: None
        Heatmap = lambda *args, **kwargs: None
    
    go = MockGo()

from .analytics_models import (
    ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
    AnalyticsFilters, DateRange, AnalyticsError, InsufficientDataError
)
from .champion_recommendation_engine import ChampionRecommendationEngine
from .advanced_recommendation_customizer import AdvancedRecommendationCustomizer
from .analytics_sharing_system import AnalyticsSharingSystem
from .config import Config


@dataclass
class RecommendationVisualizationConfig:
    """Configuration for recommendation visualizations."""
    
    # Chart styling
    color_scheme: str = "viridis"
    chart_height: int = 500
    chart_width: int = 800
    
    # Confidence visualization
    confidence_bands: bool = True
    uncertainty_alpha: float = 0.3
    
    # Synergy visualization
    synergy_heatmap_size: Tuple[int, int] = (600, 600)
    synergy_threshold: float = 0.1
    
    # Trend analysis
    trend_window_days: int = 90
    trend_smoothing: bool = True
    
    # Export settings
    export_formats: List[str] = field(default_factory=lambda: ["png", "html", "pdf"])
    export_dpi: int = 300


@dataclass
class RecommendationTrendData:
    """Data structure for recommendation trend analysis."""
    
    champion_id: int
    champion_name: str
    role: str
    
    # Time series data
    dates: List[datetime]
    scores: List[float]
    confidence_values: List[float]
    usage_rates: List[float]
    success_rates: List[float]
    
    # Trend statistics
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    volatility: float
    
    # Performance metrics
    avg_score: float
    score_std: float
    peak_score: float
    peak_date: datetime


@dataclass
class SynergyAnalysisResult:
    """Result of synergy analysis between champions."""
    
    champion_pairs: List[Tuple[int, int]]
    synergy_matrix: Dict[Tuple[int, int], float]
    interaction_effects: Dict[str, Any]
    
    # Statistical analysis
    strongest_synergies: List[Tuple[int, int, float]]
    weakest_synergies: List[Tuple[int, int, float]]
    synergy_clusters: List[List[int]]
    
    # Visualization data
    heatmap_data: np.ndarray
    champion_labels: List[str]


@dataclass
class RecommendationComparisonMatrix:
    """Matrix for comparing recommendations across scenarios."""
    
    scenarios: List[str]
    champions: List[int]
    champion_names: List[str]
    
    # Comparison data
    score_matrix: np.ndarray  # scenarios x champions
    confidence_matrix: np.ndarray
    rank_matrix: np.ndarray
    
    # Analysis results
    consistency_scores: Dict[int, float]  # champion_id -> consistency
    scenario_difficulty: Dict[str, float]  # scenario -> difficulty
    champion_versatility: Dict[int, float]  # champion_id -> versatility


@dataclass
class RecommendationSuccessMetrics:
    """Metrics for tracking recommendation success rates."""
    
    champion_id: int
    champion_name: str
    role: str
    
    # Success tracking
    total_recommendations: int
    successful_outcomes: int
    success_rate: float
    
    # Performance metrics
    avg_game_duration: float
    avg_kda: float
    avg_damage_dealt: float
    avg_gold_earned: float
    
    # Confidence correlation
    confidence_accuracy: float  # How well confidence predicts success
    overconfidence_bias: float  # Tendency to be overconfident
    
    # Time-based metrics
    recent_success_rate: float  # Last 30 days
    trend_direction: str
    improvement_rate: float

class RecommendationVisualizationAnalyzer:
    """
    Advanced visualization and analysis tools for champion recommendations.
    
    Provides comprehensive visualization capabilities including confidence bands,
    synergy analysis, comparison matrices, trend analysis, and success tracking.
    """
    
    def __init__(self, 
                 recommendation_engine: ChampionRecommendationEngine,
                 customizer: AdvancedRecommendationCustomizer,
                 sharing_system: AnalyticsSharingSystem,
                 config: Optional[RecommendationVisualizationConfig] = None):
        """
        Initialize the recommendation visualization analyzer.
        
        Args:
            recommendation_engine: Engine for generating recommendations
            customizer: Advanced customization system
            sharing_system: System for sharing and exporting results
            config: Visualization configuration
        """
        self.recommendation_engine = recommendation_engine
        self.customizer = customizer
        self.sharing_system = sharing_system
        self.config = config or RecommendationVisualizationConfig()
        
        self.logger = logging.getLogger(__name__)
        
        # Cache for expensive computations
        self._trend_cache: Dict[str, RecommendationTrendData] = {}
        self._synergy_cache: Dict[str, SynergyAnalysisResult] = {}
        self._success_metrics_cache: Dict[str, RecommendationSuccessMetrics] = {}
        
        # Color schemes for visualizations
        if PLOTLY_AVAILABLE:
            self.color_schemes = {
                'viridis': px.colors.sequential.Viridis,
                'plasma': px.colors.sequential.Plasma,
                'blues': px.colors.sequential.Blues,
                'reds': px.colors.sequential.Reds,
                'custom': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            }
        else:
            self.color_schemes = {
                'viridis': ['#440154', '#31688e', '#35b779', '#fde725'],
                'plasma': ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636'],
                'blues': ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#c6dbef'],
                'reds': ['#a50f15', '#de2d26', '#fb6a4a', '#fc9272', '#fcbba1'],
                'custom': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            }
    
    def create_confidence_visualization(self, 
                                      recommendations: List[ChampionRecommendation],
                                      include_uncertainty_bands: bool = True) -> go.Figure:
        """
        Create visualization showing recommendation confidence with uncertainty bands.
        
        Args:
            recommendations: List of champion recommendations
            include_uncertainty_bands: Whether to include uncertainty visualization
            
        Returns:
            Plotly figure with confidence visualization
        """
        try:
            if not recommendations:
                return self._create_empty_chart("No recommendations to visualize")
            
            # Prepare data
            champions = [rec.champion_name for rec in recommendations]
            scores = [rec.recommendation_score for rec in recommendations]
            confidences = [rec.confidence for rec in recommendations]
            
            # Calculate uncertainty bands
            uncertainties = [1.0 - conf for conf in confidences]
            upper_bounds = [score + unc * 0.5 for score, unc in zip(scores, uncertainties)]
            lower_bounds = [max(0, score - unc * 0.5) for score, unc in zip(scores, uncertainties)]
            
            # Create figure
            fig = go.Figure()
            
            # Add main recommendation bars
            fig.add_trace(go.Bar(
                x=champions,
                y=scores,
                name='Recommendation Score',
                marker_color=confidences,
                marker_colorscale=self.color_schemes[self.config.color_scheme],
                marker_colorbar=dict(title="Confidence"),
                text=[f"{score:.2f}" for score in scores],
                textposition='outside',
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Score: %{y:.3f}<br>"
                    "Confidence: %{marker.color:.3f}<br>"
                    "<extra></extra>"
                )
            ))
            
            # Add uncertainty bands if requested
            if include_uncertainty_bands:
                fig.add_trace(go.Scatter(
                    x=champions + champions[::-1],
                    y=upper_bounds + lower_bounds[::-1],
                    fill='toself',
                    fillcolor=f'rgba(128, 128, 128, {self.config.uncertainty_alpha})',
                    line=dict(color='rgba(255,255,255,0)'),
                    name='Uncertainty Band',
                    showlegend=True,
                    hoverinfo='skip'
                ))
            
            # Update layout
            fig.update_layout(
                title="Champion Recommendations with Confidence Visualization",
                xaxis_title="Champions",
                yaxis_title="Recommendation Score",
                height=self.config.chart_height,
                width=self.config.chart_width,
                template="plotly_white",
                showlegend=True
            )
            
            # Rotate x-axis labels if many champions
            if len(champions) > 8:
                fig.update_xaxes(tickangle=45)
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating confidence visualization: {e}")
            return self._create_error_chart(f"Error creating visualization: {str(e)}")
    
    def create_synergy_analysis_chart(self, 
                                    team_context: TeamContext,
                                    role: str,
                                    candidate_champions: List[int]) -> go.Figure:
        """
        Create synergy analysis chart showing champion interaction effects.
        
        Args:
            team_context: Current team composition context
            role: Role to analyze synergies for
            candidate_champions: List of candidate champion IDs
            
        Returns:
            Plotly figure with synergy analysis
        """
        try:
            # Generate synergy analysis
            synergy_result = self._analyze_champion_synergies(
                team_context, role, candidate_champions
            )
            
            if not synergy_result:
                return self._create_empty_chart("No synergy data available")
            
            # Create synergy heatmap
            fig = go.Figure(data=go.Heatmap(
                z=synergy_result.heatmap_data,
                x=synergy_result.champion_labels,
                y=synergy_result.champion_labels,
                colorscale=self.config.color_scheme,
                hoverongaps=False,
                hovertemplate=(
                    "Champion 1: %{y}<br>"
                    "Champion 2: %{x}<br>"
                    "Synergy Score: %{z:.3f}<br>"
                    "<extra></extra>"
                )
            ))
            
            # Update layout
            fig.update_layout(
                title=f"Champion Synergy Analysis - {role.title()} Role",
                width=self.config.synergy_heatmap_size[0],
                height=self.config.synergy_heatmap_size[1],
                template="plotly_white"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating synergy analysis chart: {e}")
            return self._create_error_chart(f"Error creating synergy analysis: {str(e)}")
    
    def create_recommendation_comparison_matrix(self, 
                                              scenarios: List[Dict[str, Any]],
                                              role: str) -> go.Figure:
        """
        Create comparison matrix for recommendations across multiple scenarios.
        
        Args:
            scenarios: List of scenario configurations
            role: Role to analyze
            
        Returns:
            Plotly figure with comparison matrix
        """
        try:
            if not scenarios:
                return self._create_empty_chart("No scenarios to compare")
            
            # Generate recommendations for each scenario
            comparison_data = self._generate_scenario_comparisons(scenarios, role)
            
            if not comparison_data:
                return self._create_empty_chart("No comparison data available")
            
            # Create basic figure for now
            fig = go.Figure()
            fig.update_layout(
                title=f"Recommendation Comparison Matrix - {role.title()} Role",
                height=800,
                width=1200,
                template="plotly_white"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating comparison matrix: {e}")
            return self._create_error_chart(f"Error creating comparison matrix: {str(e)}")
    
    def create_recommendation_trend_analysis(self, 
                                           champion_id: int,
                                           role: str,
                                           days_back: int = 90) -> go.Figure:
        """
        Create trend analysis visualization for recommendation performance over time.
        
        Args:
            champion_id: Champion to analyze
            role: Role context
            days_back: Number of days to analyze
            
        Returns:
            Plotly figure with trend analysis
        """
        try:
            # Get trend data
            trend_data = self._get_recommendation_trend_data(champion_id, role, days_back)
            
            if not trend_data or not trend_data.dates:
                return self._create_empty_chart("No trend data available")
            
            # Create basic figure for now
            fig = go.Figure()
            fig.update_layout(
                title=f"Recommendation Trend Analysis - {trend_data.champion_name} ({role.title()})",
                height=600,
                width=1000,
                template="plotly_white"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating trend analysis: {e}")
            return self._create_error_chart(f"Error creating trend analysis: {str(e)}")
    
    def create_success_rate_tracking_chart(self, 
                                         role: Optional[str] = None,
                                         time_period_days: int = 30) -> go.Figure:
        """
        Create visualization for tracking recommendation success rates.
        
        Args:
            role: Specific role to analyze (None for all roles)
            time_period_days: Time period for analysis
            
        Returns:
            Plotly figure with success rate tracking
        """
        try:
            # Get success metrics
            success_metrics = self._get_success_rate_metrics(role, time_period_days)
            
            if not success_metrics:
                return self._create_empty_chart("No success rate data available")
            
            # Create basic figure for now
            fig = go.Figure()
            fig.update_layout(
                title=f"Recommendation Success Rate Tracking{' - ' + role.title() + ' Role' if role else ''}",
                height=800,
                width=1200,
                template="plotly_white"
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating success rate tracking chart: {e}")
            return self._create_error_chart(f"Error creating success tracking: {str(e)}")
    
    def export_recommendation_analysis(self, 
                                     analysis_type: str,
                                     data: Dict[str, Any],
                                     format: str = "html") -> Dict[str, Any]:
        """
        Export recommendation analysis results in various formats.
        
        Args:
            analysis_type: Type of analysis to export
            data: Analysis data to export
            format: Export format (html, png, pdf, json)
            
        Returns:
            Export result with file path and metadata
        """
        try:
            export_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Prepare export data
            export_data = {
                'analysis_type': analysis_type,
                'timestamp': timestamp,
                'data': data,
                'metadata': {
                    'export_id': export_id,
                    'format': format,
                    'config': asdict(self.config)
                }
            }
            
            # Use sharing system for export
            result = self.sharing_system.export_analysis(
                analysis_data=export_data,
                export_format=format,
                filename=f"recommendation_analysis_{analysis_type}_{timestamp}"
            )
            
            self.logger.info(f"Exported recommendation analysis: {export_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error exporting recommendation analysis: {e}")
            raise AnalyticsError(f"Export failed: {str(e)}")
    
    def share_recommendation_analysis(self, 
                                    analysis_data: Dict[str, Any],
                                    share_options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Share recommendation analysis results with specified options.
        
        Args:
            analysis_data: Analysis data to share
            share_options: Sharing configuration
            
        Returns:
            Sharing result with URLs and access information
        """
        try:
            # Use sharing system
            result = self.sharing_system.create_shareable_analysis(
                analysis_data=analysis_data,
                share_config=share_options
            )
            
            self.logger.info(f"Shared recommendation analysis: {result.get('share_id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error sharing recommendation analysis: {e}")
            raise AnalyticsError(f"Sharing failed: {str(e)}")
    
    # Helper methods
    
    def _analyze_champion_synergies(self, 
                                  team_context: TeamContext,
                                  role: str,
                                  candidate_champions: List[int]) -> Optional[SynergyAnalysisResult]:
        """Analyze synergies between champions."""
        try:
            # Mock implementation for now
            all_champions = candidate_champions[:5]  # Limit for demo
            n_champions = len(all_champions)
            heatmap_data = np.random.rand(n_champions, n_champions)
            
            champion_labels = [f"Champion_{champ_id}" for champ_id in all_champions]
            
            result = SynergyAnalysisResult(
                champion_pairs=[(i, j) for i in all_champions for j in all_champions if i != j],
                synergy_matrix={(i, j): 0.75 for i in all_champions for j in all_champions if i != j},
                interaction_effects={},
                strongest_synergies=[(all_champions[0], all_champions[1], 0.9)],
                weakest_synergies=[(all_champions[-1], all_champions[-2], 0.3)],
                synergy_clusters=[],
                heatmap_data=heatmap_data,
                champion_labels=champion_labels
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing champion synergies: {e}")
            return None
    
    def _generate_scenario_comparisons(self, 
                                     scenarios: List[Dict[str, Any]],
                                     role: str) -> Optional[RecommendationComparisonMatrix]:
        """Generate comparison matrix for multiple scenarios."""
        try:
            # Mock implementation for now
            scenarios_list = [s.get('name', f'Scenario {i}') for i, s in enumerate(scenarios)]
            champions_list = [1, 2, 3, 4, 5]
            champion_names = [f"Champion_{i}" for i in champions_list]
            
            n_scenarios = len(scenarios_list)
            n_champions = len(champions_list)
            
            score_matrix = np.random.rand(n_scenarios, n_champions)
            confidence_matrix = np.random.rand(n_scenarios, n_champions)
            rank_matrix = np.random.randint(1, n_champions + 1, (n_scenarios, n_champions))
            
            return RecommendationComparisonMatrix(
                scenarios=scenarios_list,
                champions=champions_list,
                champion_names=champion_names,
                score_matrix=score_matrix,
                confidence_matrix=confidence_matrix,
                rank_matrix=rank_matrix,
                consistency_scores={i: 0.8 for i in champions_list},
                scenario_difficulty={s: 0.5 for s in scenarios_list},
                champion_versatility={i: 0.7 for i in champions_list}
            )
            
        except Exception as e:
            self.logger.error(f"Error generating scenario comparisons: {e}")
            return None
    
    def _get_recommendation_trend_data(self, 
                                     champion_id: int,
                                     role: str,
                                     days_back: int) -> Optional[RecommendationTrendData]:
        """Get trend data for a specific champion."""
        try:
            # Mock implementation for now
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            dates = []
            scores = []
            current_date = start_date
            
            while current_date <= end_date:
                dates.append(current_date)
                scores.append(0.7 + 0.2 * np.random.random())
                current_date += timedelta(days=1)
            
            result = RecommendationTrendData(
                champion_id=champion_id,
                champion_name=f"Champion_{champion_id}",
                role=role,
                dates=dates,
                scores=scores,
                confidence_values=[0.8 + 0.1 * np.random.random() for _ in dates],
                usage_rates=[0.3 + 0.2 * np.random.random() for _ in dates],
                success_rates=[0.6 + 0.2 * np.random.random() for _ in dates],
                trend_direction="stable",
                trend_strength=0.5,
                volatility=0.1,
                avg_score=np.mean(scores),
                score_std=np.std(scores),
                peak_score=max(scores),
                peak_date=dates[scores.index(max(scores))]
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting trend data: {e}")
            return None
    
    def _get_success_rate_metrics(self, 
                                role: Optional[str],
                                time_period_days: int) -> List[RecommendationSuccessMetrics]:
        """Get success rate metrics for champions."""
        try:
            # Mock implementation for now
            metrics = []
            champion_ids = [1, 2, 3, 4, 5]
            
            for champion_id in champion_ids:
                metric = RecommendationSuccessMetrics(
                    champion_id=champion_id,
                    champion_name=f"Champion_{champion_id}",
                    role=role or "any",
                    total_recommendations=100,
                    successful_outcomes=75,
                    success_rate=0.75,
                    avg_game_duration=28.5,
                    avg_kda=2.1,
                    avg_damage_dealt=18500.0,
                    avg_gold_earned=12000.0,
                    confidence_accuracy=0.85,
                    overconfidence_bias=0.05,
                    recent_success_rate=0.78,
                    trend_direction="stable",
                    improvement_rate=0.01
                )
                metrics.append(metric)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting success rate metrics: {e}")
            return []
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=message,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            height=self.config.chart_height,
            width=self.config.chart_width,
            template="plotly_white",
            showlegend=False
        )
        return fig
    
    def _create_error_chart(self, error_message: str) -> go.Figure:
        """Create an error chart with error message."""
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=f"Error: {error_message}",
            showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            height=self.config.chart_height,
            width=self.config.chart_width,
            template="plotly_white",
            showlegend=False
        )
        return fig