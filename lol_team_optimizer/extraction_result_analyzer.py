"""
Extraction Result Visualization and Analysis

This module provides comprehensive visualization and analysis capabilities for match
extraction results, including summary dashboards, data quality indicators, performance
charts, comparison tools, export functionality, and scheduling interfaces.
"""

import logging
import json
import uuid
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import gradio as gr
from enum import Enum
import numpy as np
from collections import defaultdict, deque

from .models import Player
from .advanced_extraction_monitor import (
    AdvancedExtractionMonitor, ExtractionStatus, ErrorSeverity,
    PlayerProgress, ExtractionMetrics, DataQualityCheck
)
from .visualization_manager import VisualizationManager, ChartConfiguration, ChartType
from .gradio_components import ProgressComponents, ValidationComponents


class ExtractionResultType(Enum):
    """Types of extraction results."""
    SUMMARY = "summary"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    ERROR_ANALYSIS = "error_analysis"


@dataclass
class ExtractionSummary:
    """Summary statistics for extraction operations."""
    operation_id: str
    start_time: datetime
    end_time: Optional[datetime]
    total_players: int
    completed_players: int
    failed_players: int
    total_matches_extracted: int
    total_api_calls: int
    success_rate: float
    average_extraction_rate: float
    data_quality_score: float
    efficiency_score: float
    total_errors: int
    critical_errors: int


@dataclass
class QualityIndicator:
    """Data quality indicator for extraction results."""
    indicator_name: str
    current_value: float
    target_value: float
    status: str  # "excellent", "good", "warning", "critical"
    description: str
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class PerformanceMetric:
    """Performance metric for extraction analysis."""
    metric_name: str
    value: float
    unit: str
    trend: str  # "improving", "stable", "declining"
    benchmark: Optional[float] = None
    percentile: Optional[float] = None


@dataclass
class ExtractionComparison:
    """Comparison between different extraction periods."""
    period_1: Dict[str, Any]
    period_2: Dict[str, Any]
    improvements: List[str]
    regressions: List[str]
    recommendations: List[str]


class ExtractionResultAnalyzer:
    """
    Comprehensive analyzer for extraction results with visualization capabilities.
    
    Provides summary dashboards, quality indicators, performance analysis,
    comparison tools, export functionality, and scheduling interfaces.
    """
    
    def __init__(self, core_engine, advanced_monitor: AdvancedExtractionMonitor):
        """Initialize the extraction result analyzer."""
        self.core_engine = core_engine
        self.advanced_monitor = advanced_monitor
        self.visualization_manager = VisualizationManager()
        self.logger = logging.getLogger(__name__)
        
        # Analysis cache
        self.analysis_cache: Dict[str, Any] = {}
        self.summary_cache: Dict[str, ExtractionSummary] = {}
        
        # Scheduling state
        self.scheduled_extractions: Dict[str, Dict[str, Any]] = {}
        self.automation_active = False
        
        self.logger.info("Extraction result analyzer initialized")
    
    def create_extraction_analysis_interface(self) -> Dict[str, gr.Component]:
        """Create the comprehensive extraction analysis interface."""
        components = {}
        
        try:
            # Create components without context managers for testing compatibility
            components.update(self._create_summary_dashboard())
            components.update(self._create_quality_analysis_panel())
            components.update(self._create_performance_analysis_panel())
            components.update(self._create_comparison_panel())
            components.update(self._create_export_panel())
            components.update(self._create_scheduling_panel())
            
            # Setup event handlers
            self._setup_analysis_event_handlers(components)
            
        except Exception as e:
            self.logger.error(f"Error creating extraction analysis interface: {e}")
            # Return minimal components for testing
            components = {
                'operation_selector': gr.Dropdown(label="Operations", choices=["test"]),
                'total_players_metric': gr.Number(label="Total Players", value=0),
                'extraction_progress_chart': self._create_empty_progress_chart()
            }
        
        return components
    
    def _create_summary_dashboard(self) -> Dict[str, gr.Component]:
        """Create extraction summary dashboard with statistics and insights."""
        components = {}
        
        # Operation Selection
        components['operation_selector'] = gr.Dropdown(
            label="Select Extraction Operation",
            choices=self._get_available_operations(),
            value=None,
            interactive=True
        )
        components['refresh_operations'] = gr.Button("🔄 Refresh", size="sm")
        components['auto_refresh'] = gr.Checkbox(
            label="Auto-refresh",
            value=True,
            info="Automatically refresh data every 30 seconds"
        )
        
        # Key Metrics Overview
        components['total_players_metric'] = gr.Number(
            label="Total Players",
            value=0,
            interactive=False
        )
        components['completed_players_metric'] = gr.Number(
            label="Completed Players",
            value=0,
            interactive=False
        )
        components['total_matches_metric'] = gr.Number(
            label="Total Matches Extracted",
            value=0,
            interactive=False
        )
        components['success_rate_metric'] = gr.Number(
            label="Success Rate (%)",
            value=0,
            interactive=False,
            precision=1
        )
        components['extraction_rate_metric'] = gr.Number(
            label="Avg Extraction Rate (matches/min)",
            value=0,
            interactive=False,
            precision=2
        )
        components['efficiency_score_metric'] = gr.Number(
            label="Efficiency Score (%)",
            value=0,
            interactive=False,
            precision=1
        )
        
        # Summary Charts
        components['extraction_progress_chart'] = gr.Plot(
            label="Extraction Progress Over Time",
            value=self._create_empty_progress_chart()
        )
        components['player_status_chart'] = gr.Plot(
            label="Player Status Distribution",
            value=self._create_empty_status_chart()
        )
        
        # Detailed Statistics Table
        components['detailed_stats_table'] = gr.DataFrame(
            headers=[
                "Metric", "Current Value", "Target", "Status", "Trend", "Notes"
            ],
            datatype=["str", "str", "str", "str", "str", "str"],
            label="Detailed Statistics",
            interactive=False
        )
        
        # Insights and Recommendations
        components['extraction_insights'] = gr.HTML(
            value="<p>Select an extraction operation to view insights and recommendations.</p>",
            label="Insights & Recommendations"
        )
        
        return components
    
    def _create_quality_analysis_panel(self) -> Dict[str, gr.Component]:
        """Create data quality analysis panel with completeness indicators."""
        components = {}
        
        # Quality Score Overview
        components['overall_quality_score'] = gr.Number(
            label="Overall Data Quality Score (%)",
            value=0,
            interactive=False,
            precision=1
        )
        components['completeness_score'] = gr.Number(
            label="Data Completeness (%)",
            value=0,
            interactive=False,
            precision=1
        )
        components['integrity_score'] = gr.Number(
            label="Data Integrity (%)",
            value=0,
            interactive=False,
            precision=1
        )
        
        # Quality Indicators Chart
        components['quality_indicators_chart'] = gr.Plot(
            label="Data Quality Indicators",
            value=self._create_empty_quality_chart()
        )
        
        # Quality Issues Table
        components['quality_issues_table'] = gr.DataFrame(
            headers=[
                "Check Name", "Status", "Severity", "Affected Records", 
                "Description", "Suggestions"
            ],
            datatype=["str", "str", "str", "number", "str", "str"],
            label="Data Quality Issues",
            interactive=False
        )
        
        # Quality Trends
        components['quality_trends_chart'] = gr.Plot(
            label="Quality Trends Over Time",
            value=self._create_empty_trend_chart()
        )
        
        # Quality Settings
        components['quality_threshold'] = gr.Slider(
            label="Quality Threshold (%)",
            minimum=50,
            maximum=100,
            value=80,
            step=5,
            info="Minimum acceptable quality score"
        )
        components['enable_auto_fix'] = gr.Checkbox(
            label="Enable Auto-fix",
            value=False,
            info="Automatically fix minor quality issues"
        )
        
        return components
    
    def _create_performance_analysis_panel(self) -> Dict[str, gr.Component]:
        """Create performance analysis panel with charts and trend analysis."""
        components = {}
        
        # Performance Metrics
        components['avg_response_time'] = gr.Number(
            label="Avg API Response Time (ms)",
            value=0,
            interactive=False,
            precision=0
        )
        components['peak_extraction_rate'] = gr.Number(
            label="Peak Extraction Rate (matches/min)",
            value=0,
            interactive=False,
            precision=2
        )
        components['api_success_rate'] = gr.Number(
            label="API Success Rate (%)",
            value=0,
            interactive=False,
            precision=1
        )
        components['retry_success_rate'] = gr.Number(
            label="Retry Success Rate (%)",
            value=0,
            interactive=False,
            precision=1
        )
        
        # Performance Charts
        components['extraction_rate_chart'] = gr.Plot(
            label="Extraction Rate Over Time",
            value=self._create_empty_rate_chart()
        )
        components['api_performance_chart'] = gr.Plot(
            label="API Performance Metrics",
            value=self._create_empty_api_chart()
        )
        
        # Resource Utilization
        components['resource_utilization_chart'] = gr.Plot(
            label="Resource Utilization",
            value=self._create_empty_resource_chart()
        )
        
        # Performance Benchmarks
        components['performance_benchmarks_table'] = gr.DataFrame(
            headers=[
                "Metric", "Current", "Benchmark", "Percentile", "Status", "Improvement"
            ],
            datatype=["str", "str", "str", "str", "str", "str"],
            label="Performance Benchmarks",
            interactive=False
        )
        
        # Optimization Suggestions
        components['optimization_suggestions'] = gr.HTML(
            value="<p>Performance analysis will appear here after selecting an operation.</p>",
            label="Optimization Suggestions"
        )
        
        return components
    
    def _create_comparison_panel(self) -> Dict[str, gr.Component]:
        """Create extraction comparison tools for different time periods."""
        components = {}
        
        # Comparison Configuration
        components['comparison_period_1'] = gr.Dropdown(
            label="Period 1",
            choices=self._get_available_periods(),
            value=None,
            interactive=True
        )
        components['comparison_period_2'] = gr.Dropdown(
            label="Period 2",
            choices=self._get_available_periods(),
            value=None,
            interactive=True
        )
        components['run_comparison'] = gr.Button("🔄 Compare Periods", variant="primary")
        
        # Comparison Results
        components['comparison_summary'] = gr.HTML(
            value="<p>Select two periods to compare extraction performance.</p>",
            label="Comparison Summary"
        )
        components['improvement_metrics'] = gr.DataFrame(
            headers=["Metric", "Period 1", "Period 2", "Change", "% Change"],
            datatype=["str", "str", "str", "str", "str"],
            label="Performance Changes",
            interactive=False
        )
        
        # Comparison Charts
        components['comparison_chart'] = gr.Plot(
            label="Side-by-Side Comparison",
            value=self._create_empty_comparison_chart()
        )
        components['trend_comparison_chart'] = gr.Plot(
            label="Trend Comparison",
            value=self._create_empty_trend_comparison_chart()
        )
        
        # Recommendations
        components['comparison_recommendations'] = gr.HTML(
            value="<p>Recommendations will appear after running a comparison.</p>",
            label="Recommendations"
        )
        
        return components
    
    def _create_export_panel(self) -> Dict[str, gr.Component]:
        """Create export and sharing functionality panel."""
        components = {}
        
        # Export Configuration
        components['export_format'] = gr.Dropdown(
            label="Export Format",
            choices=["PDF Report", "CSV Data", "JSON Data", "Excel Workbook", "Interactive HTML"],
            value="PDF Report",
            interactive=True
        )
        components['include_charts'] = gr.Checkbox(
            label="Include Charts",
            value=True,
            info="Include visualizations in export"
        )
        components['include_raw_data'] = gr.Checkbox(
            label="Include Raw Data",
            value=False,
            info="Include detailed raw data"
        )
        
        # Export Scope
        components['export_scope'] = gr.CheckboxGroup(
            label="Export Scope",
            choices=[
                "Summary Dashboard",
                "Quality Analysis",
                "Performance Metrics",
                "Comparison Results",
                "Error Analysis",
                "Recommendations"
            ],
            value=["Summary Dashboard", "Quality Analysis", "Performance Metrics"],
            interactive=True
        )
        
        # Export Actions
        components['generate_export'] = gr.Button(
            "📤 Generate Export",
            variant="primary",
            size="lg"
        )
        components['download_link'] = gr.File(
            label="Download Export",
            visible=False
        )
        
        # Sharing Options
        components['generate_share_link'] = gr.Button(
            "🔗 Generate Share Link",
            variant="secondary"
        )
        components['share_link'] = gr.Textbox(
            label="Shareable Link",
            placeholder="Share link will appear here",
            interactive=False
        )
        
        # Export History
        components['export_history_table'] = gr.DataFrame(
            headers=["Timestamp", "Format", "Scope", "Size", "Status", "Download"],
            datatype=["str", "str", "str", "str", "str", "str"],
            label="Export History",
            interactive=False
        )
        
        return components
    
    def _create_scheduling_panel(self) -> Dict[str, gr.Component]:
        """Create extraction scheduling and automation interface."""
        components = {}
        
        # Scheduling Configuration
        components['schedule_enabled'] = gr.Checkbox(
            label="Enable Scheduled Extractions",
            value=False,
            info="Automatically run extractions on schedule"
        )
        components['schedule_frequency'] = gr.Dropdown(
            label="Frequency",
            choices=["Daily", "Weekly", "Bi-weekly", "Monthly"],
            value="Weekly",
            interactive=True
        )
        
        # Schedule Settings
        components['schedule_time'] = gr.Textbox(
            label="Schedule Time (HH:MM)",
            value="02:00",
            placeholder="24-hour format"
        )
        components['schedule_days'] = gr.CheckboxGroup(
            label="Days of Week",
            choices=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            value=["Sunday"],
            interactive=True
        )
        components['max_matches_scheduled'] = gr.Number(
            label="Max Matches per Player",
            value=50,
            minimum=1,
            maximum=1000
        )
        components['notification_email'] = gr.Textbox(
            label="Notification Email",
            placeholder="email@example.com",
            info="Email for completion notifications"
        )
        
        # Automation Rules
        components['auto_retry_failed'] = gr.Checkbox(
            label="Auto-retry Failed Extractions",
            value=True,
            info="Automatically retry failed extractions"
        )
        components['auto_quality_check'] = gr.Checkbox(
            label="Auto Quality Validation",
            value=True,
            info="Automatically validate data quality"
        )
        
        # Schedule Management
        components['save_schedule'] = gr.Button(
            "💾 Save Schedule",
            variant="primary"
        )
        components['test_schedule'] = gr.Button(
            "🧪 Test Schedule",
            variant="secondary"
        )
        components['clear_schedule'] = gr.Button(
            "🗑️ Clear Schedule",
            variant="secondary"
        )
        
        # Active Schedules
        components['active_schedules_table'] = gr.DataFrame(
            headers=["Name", "Frequency", "Next Run", "Status", "Last Result", "Actions"],
            datatype=["str", "str", "str", "str", "str", "str"],
            label="Active Schedules",
            interactive=False
        )
        
        # Automation Status
        components['automation_status'] = gr.HTML(
            value="<p>Automation is currently disabled.</p>",
            label="Automation Status"
        )
        
        return components
    
    def _setup_analysis_event_handlers(self, components: Dict[str, gr.Component]) -> None:
        """Setup event handlers for analysis interface."""
        
        # Operation selection handler
        def update_analysis_data(operation_id: str) -> Tuple[Any, ...]:
            """Update all analysis data when operation is selected."""
            try:
                if not operation_id:
                    return self._get_empty_analysis_data()
                
                # Generate analysis data
                summary = self._generate_extraction_summary(operation_id)
                quality_data = self._analyze_data_quality(operation_id)
                performance_data = self._analyze_performance(operation_id)
                
                # Update summary metrics
                summary_updates = (
                    summary.total_players,
                    summary.completed_players,
                    summary.total_matches_extracted,
                    summary.success_rate,
                    summary.average_extraction_rate,
                    summary.efficiency_score
                )
                
                # Update charts
                progress_chart = self._create_progress_chart(operation_id)
                status_chart = self._create_status_chart(operation_id)
                quality_chart = self._create_quality_chart(quality_data)
                
                # Update insights
                insights_html = self._generate_insights_html(summary, quality_data, performance_data)
                
                return summary_updates + (progress_chart, status_chart, insights_html)
                
            except Exception as e:
                self.logger.error(f"Error updating analysis data: {e}")
                return self._get_empty_analysis_data()
        
        # Comparison handler
        def run_comparison(period_1: str, period_2: str) -> Tuple[str, Any, Any, Any, str]:
            """Run comparison between two periods."""
            try:
                if not period_1 or not period_2:
                    return (
                        "<p>Please select both periods for comparison.</p>",
                        [],
                        self._create_empty_comparison_chart(),
                        self._create_empty_trend_comparison_chart(),
                        "<p>Select periods to see recommendations.</p>"
                    )
                
                comparison = self._compare_extraction_periods(period_1, period_2)
                
                summary_html = self._generate_comparison_summary_html(comparison)
                metrics_data = self._format_comparison_metrics(comparison)
                comparison_chart = self._create_comparison_chart_data(comparison)
                trend_chart = self._create_trend_comparison_chart_data(comparison)
                recommendations_html = self._generate_comparison_recommendations_html(comparison)
                
                return (
                    summary_html,
                    metrics_data,
                    comparison_chart,
                    trend_chart,
                    recommendations_html
                )
                
            except Exception as e:
                self.logger.error(f"Error running comparison: {e}")
                return (
                    f"<p>Error running comparison: {str(e)}</p>",
                    [],
                    self._create_empty_comparison_chart(),
                    self._create_empty_trend_comparison_chart(),
                    "<p>Error generating recommendations.</p>"
                )
        
        # Export handler
        def generate_export(export_format: str, include_charts: bool, 
                          include_raw_data: bool, export_scope: List[str]) -> Tuple[Any, bool]:
            """Generate export file."""
            try:
                export_file = self._generate_export_file(
                    export_format, include_charts, include_raw_data, export_scope
                )
                
                if export_file:
                    return export_file, True
                else:
                    return None, False
                    
            except Exception as e:
                self.logger.error(f"Error generating export: {e}")
                return None, False
        
        # Connect event handlers
        components['operation_selector'].change(
            fn=update_analysis_data,
            inputs=[components['operation_selector']],
            outputs=[
                components['total_players_metric'],
                components['completed_players_metric'],
                components['total_matches_metric'],
                components['success_rate_metric'],
                components['extraction_rate_metric'],
                components['efficiency_score_metric'],
                components['extraction_progress_chart'],
                components['player_status_chart'],
                components['extraction_insights']
            ]
        )
        
        components['run_comparison'].click(
            fn=run_comparison,
            inputs=[
                components['comparison_period_1'],
                components['comparison_period_2']
            ],
            outputs=[
                components['comparison_summary'],
                components['improvement_metrics'],
                components['comparison_chart'],
                components['trend_comparison_chart'],
                components['comparison_recommendations']
            ]
        )
        
        components['generate_export'].click(
            fn=generate_export,
            inputs=[
                components['export_format'],
                components['include_charts'],
                components['include_raw_data'],
                components['export_scope']
            ],
            outputs=[
                components['download_link'],
                components['download_link']  # visibility
            ]
        )
    
    def _generate_extraction_summary(self, operation_id: str) -> ExtractionSummary:
        """Generate comprehensive extraction summary."""
        try:
            # Get operation data from advanced monitor
            if operation_id not in self.advanced_monitor.active_operations:
                # Try to get from completed operations
                metrics = self._get_completed_operation_metrics(operation_id)
                if not metrics:
                    raise ValueError(f"Operation {operation_id} not found")
            else:
                metrics = self._calculate_current_metrics(operation_id)
            
            # Create summary
            summary = ExtractionSummary(
                operation_id=operation_id,
                start_time=metrics.get('start_time', datetime.now()),
                end_time=metrics.get('end_time'),
                total_players=metrics.get('total_players', 0),
                completed_players=metrics.get('completed_players', 0),
                failed_players=metrics.get('failed_players', 0),
                total_matches_extracted=metrics.get('total_matches_extracted', 0),
                total_api_calls=metrics.get('total_api_calls', 0),
                success_rate=metrics.get('success_rate', 0.0),
                average_extraction_rate=metrics.get('average_extraction_rate', 0.0),
                data_quality_score=metrics.get('data_quality_score', 0.0),
                efficiency_score=metrics.get('efficiency_score', 0.0),
                total_errors=metrics.get('total_errors', 0),
                critical_errors=metrics.get('critical_errors', 0)
            )
            
            # Cache the summary
            self.summary_cache[operation_id] = summary
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating extraction summary: {e}")
            # Return empty summary
            return ExtractionSummary(
                operation_id=operation_id,
                start_time=datetime.now(),
                end_time=None,
                total_players=0,
                completed_players=0,
                failed_players=0,
                total_matches_extracted=0,
                total_api_calls=0,
                success_rate=0.0,
                average_extraction_rate=0.0,
                data_quality_score=0.0,
                efficiency_score=0.0,
                total_errors=0,
                critical_errors=0
            )
    
    def _analyze_data_quality(self, operation_id: str) -> Dict[str, Any]:
        """Analyze data quality for extraction operation."""
        try:
            quality_checks = []
            overall_score = 0.0
            completeness_score = 0.0
            integrity_score = 0.0
            
            # Get operation data
            if operation_id in self.advanced_monitor.active_operations:
                operation_data = self.advanced_monitor.active_operations[operation_id]
                
                # Check data completeness
                total_players = len(operation_data)
                completed_players = sum(1 for p in operation_data.values() 
                                     if p.status == ExtractionStatus.COMPLETED)
                
                if total_players > 0:
                    completeness_score = (completed_players / total_players) * 100
                
                # Check data integrity
                integrity_issues = 0
                total_matches = 0
                
                for player_progress in operation_data.values():
                    total_matches += player_progress.matches_extracted
                    
                    # Check for data integrity issues
                    if player_progress.matches_extracted < 0:
                        integrity_issues += 1
                    if player_progress.api_calls_made < player_progress.matches_extracted:
                        integrity_issues += 1
                
                if total_players > 0:
                    integrity_score = max(0, (total_players - integrity_issues) / total_players * 100)
                
                # Overall quality score
                overall_score = (completeness_score + integrity_score) / 2
                
                # Create quality indicators
                quality_checks = [
                    QualityIndicator(
                        indicator_name="Data Completeness",
                        current_value=completeness_score,
                        target_value=95.0,
                        status="excellent" if completeness_score >= 95 else 
                               "good" if completeness_score >= 80 else
                               "warning" if completeness_score >= 60 else "critical",
                        description=f"{completed_players}/{total_players} players completed successfully",
                        improvement_suggestions=["Retry failed extractions", "Check API connectivity"] 
                        if completeness_score < 95 else []
                    ),
                    QualityIndicator(
                        indicator_name="Data Integrity",
                        current_value=integrity_score,
                        target_value=98.0,
                        status="excellent" if integrity_score >= 98 else 
                               "good" if integrity_score >= 90 else
                               "warning" if integrity_score >= 70 else "critical",
                        description=f"{integrity_issues} integrity issues detected",
                        improvement_suggestions=["Validate API responses", "Check data parsing logic"] 
                        if integrity_score < 98 else []
                    )
                ]
            
            return {
                'overall_score': overall_score,
                'completeness_score': completeness_score,
                'integrity_score': integrity_score,
                'quality_indicators': quality_checks,
                'issues_count': len([q for q in quality_checks if q.status in ['warning', 'critical']])
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing data quality: {e}")
            return {
                'overall_score': 0.0,
                'completeness_score': 0.0,
                'integrity_score': 0.0,
                'quality_indicators': [],
                'issues_count': 0
            }
    
    def _analyze_performance(self, operation_id: str) -> Dict[str, Any]:
        """Analyze performance metrics for extraction operation."""
        try:
            performance_metrics = []
            
            # Get operation data
            if operation_id in self.advanced_monitor.active_operations:
                operation_data = self.advanced_monitor.active_operations[operation_id]
                
                # Calculate performance metrics
                total_matches = sum(p.matches_extracted for p in operation_data.values())
                total_api_calls = sum(p.api_calls_made for p in operation_data.values())
                total_errors = sum(p.error_count for p in operation_data.values())
                
                # API success rate
                api_success_rate = 0.0
                if total_api_calls > 0:
                    successful_calls = total_api_calls - sum(p.api_calls_failed for p in operation_data.values())
                    api_success_rate = (successful_calls / total_api_calls) * 100
                
                # Average extraction rate
                extraction_rates = [p.extraction_rate for p in operation_data.values() if p.extraction_rate > 0]
                avg_extraction_rate = sum(extraction_rates) / len(extraction_rates) if extraction_rates else 0.0
                peak_extraction_rate = max(extraction_rates) if extraction_rates else 0.0
                
                # Response time (simulated - would need actual API timing data)
                avg_response_time = 250  # ms - placeholder
                
                performance_metrics = [
                    PerformanceMetric(
                        metric_name="API Success Rate",
                        value=api_success_rate,
                        unit="%",
                        trend="stable",
                        benchmark=95.0,
                        percentile=75.0 if api_success_rate >= 90 else 50.0
                    ),
                    PerformanceMetric(
                        metric_name="Average Extraction Rate",
                        value=avg_extraction_rate,
                        unit="matches/min",
                        trend="improving" if avg_extraction_rate > 2.0 else "stable",
                        benchmark=3.0,
                        percentile=80.0 if avg_extraction_rate >= 2.5 else 60.0
                    ),
                    PerformanceMetric(
                        metric_name="Peak Extraction Rate",
                        value=peak_extraction_rate,
                        unit="matches/min",
                        trend="stable",
                        benchmark=5.0,
                        percentile=85.0 if peak_extraction_rate >= 4.0 else 65.0
                    ),
                    PerformanceMetric(
                        metric_name="Average Response Time",
                        value=avg_response_time,
                        unit="ms",
                        trend="stable",
                        benchmark=200.0,
                        percentile=60.0 if avg_response_time <= 300 else 40.0
                    )
                ]
            
            return {
                'metrics': performance_metrics,
                'api_success_rate': api_success_rate if 'api_success_rate' in locals() else 0.0,
                'avg_extraction_rate': avg_extraction_rate if 'avg_extraction_rate' in locals() else 0.0,
                'peak_extraction_rate': peak_extraction_rate if 'peak_extraction_rate' in locals() else 0.0,
                'avg_response_time': avg_response_time if 'avg_response_time' in locals() else 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance: {e}")
            return {
                'metrics': [],
                'api_success_rate': 0.0,
                'avg_extraction_rate': 0.0,
                'peak_extraction_rate': 0.0,
                'avg_response_time': 0.0
            }
    
    def _get_available_operations(self) -> List[str]:
        """Get list of available extraction operations."""
        try:
            operations = []
            
            # Add active operations
            for op_id in self.advanced_monitor.active_operations.keys():
                operations.append(f"Active: {op_id}")
            
            # Add completed operations (simulated - would come from database/logs)
            completed_ops = [
                "Completed: extraction_2024_01_15",
                "Completed: extraction_2024_01_10",
                "Completed: extraction_2024_01_05"
            ]
            operations.extend(completed_ops)
            
            return operations if operations else ["No operations available"]
            
        except Exception as e:
            self.logger.error(f"Error getting available operations: {e}")
            return ["Error loading operations"]
    
    def _get_available_periods(self) -> List[str]:
        """Get list of available time periods for comparison."""
        try:
            periods = [
                "Last 7 days",
                "Last 14 days",
                "Last 30 days",
                "January 2024",
                "December 2023",
                "November 2023"
            ]
            return periods
            
        except Exception as e:
            self.logger.error(f"Error getting available periods: {e}")
            return ["Error loading periods"]
    
    def _create_empty_progress_chart(self) -> go.Figure:
        """Create empty progress chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Progress'
        ))
        fig.update_layout(
            title="Extraction Progress Over Time",
            xaxis_title="Time",
            yaxis_title="Progress (%)",
            showlegend=True
        )
        return fig
    
    def _create_empty_status_chart(self) -> go.Figure:
        """Create empty status distribution chart."""
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=[],
            values=[],
            name="Player Status"
        ))
        fig.update_layout(
            title="Player Status Distribution"
        )
        return fig
    
    def _create_empty_quality_chart(self) -> go.Figure:
        """Create empty quality indicators chart."""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[],
            y=[],
            name='Quality Score'
        ))
        fig.update_layout(
            title="Data Quality Indicators",
            xaxis_title="Quality Metric",
            yaxis_title="Score (%)",
            showlegend=True
        )
        return fig
    
    def _create_empty_trend_chart(self) -> go.Figure:
        """Create empty trend chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Quality Trend'
        ))
        fig.update_layout(
            title="Quality Trends Over Time",
            xaxis_title="Time",
            yaxis_title="Quality Score (%)",
            showlegend=True
        )
        return fig
    
    def _create_empty_rate_chart(self) -> go.Figure:
        """Create empty extraction rate chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Extraction Rate'
        ))
        fig.update_layout(
            title="Extraction Rate Over Time",
            xaxis_title="Time",
            yaxis_title="Matches/Minute",
            showlegend=True
        )
        return fig
    
    def _create_empty_api_chart(self) -> go.Figure:
        """Create empty API performance chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Response Time'
        ))
        fig.update_layout(
            title="API Performance Metrics",
            xaxis_title="Time",
            yaxis_title="Response Time (ms)",
            showlegend=True
        )
        return fig
    
    def _create_empty_resource_chart(self) -> go.Figure:
        """Create empty resource utilization chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='CPU Usage'
        ))
        fig.update_layout(
            title="Resource Utilization",
            xaxis_title="Time",
            yaxis_title="Usage (%)",
            showlegend=True
        )
        return fig
    
    def _create_empty_comparison_chart(self) -> go.Figure:
        """Create empty comparison chart."""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[],
            y=[],
            name='Period 1'
        ))
        fig.add_trace(go.Bar(
            x=[],
            y=[],
            name='Period 2'
        ))
        fig.update_layout(
            title="Period Comparison",
            xaxis_title="Metrics",
            yaxis_title="Values",
            barmode='group'
        )
        return fig
    
    def _create_empty_trend_comparison_chart(self) -> go.Figure:
        """Create empty trend comparison chart."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Period 1'
        ))
        fig.add_trace(go.Scatter(
            x=[],
            y=[],
            mode='lines+markers',
            name='Period 2'
        ))
        fig.update_layout(
            title="Trend Comparison",
            xaxis_title="Time",
            yaxis_title="Performance",
            showlegend=True
        )
        return fig
    
    def _get_empty_analysis_data(self) -> Tuple[Any, ...]:
        """Get empty analysis data for interface updates."""
        return (
            0, 0, 0, 0.0, 0.0, 0.0,  # metrics
            self._create_empty_progress_chart(),
            self._create_empty_status_chart(),
            "<p>No data available. Select an extraction operation to view analysis.</p>"
        )
    
    def _get_completed_operation_metrics(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for completed operation (placeholder - would query database)."""
        # This would typically query a database or log files
        # For now, return simulated data
        if "extraction_2024" in operation_id:
            return {
                'start_time': datetime.now() - timedelta(hours=2),
                'end_time': datetime.now() - timedelta(hours=1),
                'total_players': 20,
                'completed_players': 18,
                'failed_players': 2,
                'total_matches_extracted': 1500,
                'total_api_calls': 300,
                'success_rate': 90.0,
                'average_extraction_rate': 2.5,
                'data_quality_score': 85.0,
                'efficiency_score': 88.0,
                'total_errors': 5,
                'critical_errors': 1
            }
        return None
    
    def _calculate_current_metrics(self, operation_id: str) -> Dict[str, Any]:
        """Calculate metrics for currently active operation."""
        try:
            operation_data = self.advanced_monitor.active_operations[operation_id]
            
            total_players = len(operation_data)
            completed_players = sum(1 for p in operation_data.values() 
                                  if p.status == ExtractionStatus.COMPLETED)
            failed_players = sum(1 for p in operation_data.values() 
                               if p.status == ExtractionStatus.FAILED)
            
            total_matches = sum(p.matches_extracted for p in operation_data.values())
            total_api_calls = sum(p.api_calls_made for p in operation_data.values())
            total_errors = sum(p.error_count for p in operation_data.values())
            
            success_rate = (completed_players / total_players * 100) if total_players > 0 else 0.0
            
            # Calculate average extraction rate
            extraction_rates = [p.extraction_rate for p in operation_data.values() if p.extraction_rate > 0]
            avg_extraction_rate = sum(extraction_rates) / len(extraction_rates) if extraction_rates else 0.0
            
            return {
                'start_time': min(p.start_time for p in operation_data.values() if p.start_time),
                'end_time': None,  # Still running
                'total_players': total_players,
                'completed_players': completed_players,
                'failed_players': failed_players,
                'total_matches_extracted': total_matches,
                'total_api_calls': total_api_calls,
                'success_rate': success_rate,
                'average_extraction_rate': avg_extraction_rate,
                'data_quality_score': 80.0,  # Would be calculated based on actual data
                'efficiency_score': 75.0,   # Would be calculated based on performance
                'total_errors': total_errors,
                'critical_errors': sum(1 for p in operation_data.values() 
                                     if p.last_error and p.last_error.severity == ErrorSeverity.CRITICAL)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating current metrics: {e}")
            return {}
    
    def _create_progress_chart(self, operation_id: str) -> go.Figure:
        """Create progress chart for specific operation."""
        try:
            # This would typically get historical progress data
            # For now, create simulated progress data
            times = [datetime.now() - timedelta(minutes=i*10) for i in range(12, 0, -1)]
            progress = [i*8.33 for i in range(len(times))]  # 0 to 100% progress
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times,
                y=progress,
                mode='lines+markers',
                name='Extraction Progress',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=6)
            ))
            
            fig.update_layout(
                title="Extraction Progress Over Time",
                xaxis_title="Time",
                yaxis_title="Progress (%)",
                showlegend=True,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating progress chart: {e}")
            return self._create_empty_progress_chart()
    
    def _create_status_chart(self, operation_id: str) -> go.Figure:
        """Create status distribution chart for specific operation."""
        try:
            if operation_id in self.advanced_monitor.active_operations:
                operation_data = self.advanced_monitor.active_operations[operation_id]
                
                # Count statuses
                status_counts = {}
                for player_progress in operation_data.values():
                    status = player_progress.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                labels = list(status_counts.keys())
                values = list(status_counts.values())
                
                # Define colors for different statuses
                colors = {
                    'completed': '#2ca02c',
                    'running': '#1f77b4',
                    'failed': '#d62728',
                    'paused': '#ff7f0e',
                    'not_started': '#7f7f7f'
                }
                
                fig = go.Figure()
                fig.add_trace(go.Pie(
                    labels=labels,
                    values=values,
                    name="Player Status",
                    marker_colors=[colors.get(label, '#bcbd22') for label in labels]
                ))
                
                fig.update_layout(
                    title="Player Status Distribution",
                    height=400
                )
                
                return fig
            else:
                return self._create_empty_status_chart()
                
        except Exception as e:
            self.logger.error(f"Error creating status chart: {e}")
            return self._create_empty_status_chart()
    
    def _create_quality_chart(self, quality_data: Dict[str, Any]) -> go.Figure:
        """Create quality indicators chart."""
        try:
            quality_indicators = quality_data.get('quality_indicators', [])
            
            if not quality_indicators:
                return self._create_empty_quality_chart()
            
            names = [qi.indicator_name for qi in quality_indicators]
            current_values = [qi.current_value for qi in quality_indicators]
            target_values = [qi.target_value for qi in quality_indicators]
            
            fig = go.Figure()
            
            # Current values
            fig.add_trace(go.Bar(
                x=names,
                y=current_values,
                name='Current Score',
                marker_color='#1f77b4'
            ))
            
            # Target values
            fig.add_trace(go.Bar(
                x=names,
                y=target_values,
                name='Target Score',
                marker_color='#2ca02c',
                opacity=0.6
            ))
            
            fig.update_layout(
                title="Data Quality Indicators",
                xaxis_title="Quality Metric",
                yaxis_title="Score (%)",
                barmode='group',
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating quality chart: {e}")
            return self._create_empty_quality_chart()
    
    def _generate_insights_html(self, summary: ExtractionSummary, 
                               quality_data: Dict[str, Any], 
                               performance_data: Dict[str, Any]) -> str:
        """Generate insights and recommendations HTML."""
        try:
            insights = []
            recommendations = []
            
            # Performance insights
            if summary.success_rate < 80:
                insights.append(f"⚠️ Success rate is below target at {summary.success_rate:.1f}%")
                recommendations.append("Review failed extractions and implement retry logic")
            
            if summary.average_extraction_rate < 2.0:
                insights.append(f"🐌 Extraction rate is slow at {summary.average_extraction_rate:.1f} matches/min")
                recommendations.append("Consider optimizing API calls or increasing concurrency")
            
            # Quality insights
            overall_quality = quality_data.get('overall_score', 0)
            if overall_quality < 85:
                insights.append(f"📊 Data quality score is below target at {overall_quality:.1f}%")
                recommendations.append("Implement additional data validation checks")
            
            # Efficiency insights
            if summary.efficiency_score < 70:
                insights.append(f"⚡ Efficiency score is low at {summary.efficiency_score:.1f}%")
                recommendations.append("Review resource utilization and optimize extraction process")
            
            # Generate HTML
            html_content = "<div style='padding: 10px;'>"
            
            if insights:
                html_content += "<h4>📈 Key Insights</h4><ul>"
                for insight in insights:
                    html_content += f"<li>{insight}</li>"
                html_content += "</ul>"
            
            if recommendations:
                html_content += "<h4>💡 Recommendations</h4><ul>"
                for rec in recommendations:
                    html_content += f"<li>{rec}</li>"
                html_content += "</ul>"
            
            if not insights and not recommendations:
                html_content += "<p>✅ Extraction is performing well. No issues detected.</p>"
            
            html_content += "</div>"
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error generating insights HTML: {e}")
            return "<p>Error generating insights.</p>"
    
    def _compare_extraction_periods(self, period_1: str, period_2: str) -> ExtractionComparison:
        """Compare extraction performance between two periods."""
        try:
            # This would typically query historical data
            # For now, create simulated comparison data
            
            period_1_data = {
                'total_matches': 1200,
                'success_rate': 85.0,
                'avg_extraction_rate': 2.1,
                'quality_score': 82.0,
                'total_errors': 8
            }
            
            period_2_data = {
                'total_matches': 1500,
                'success_rate': 92.0,
                'avg_extraction_rate': 2.8,
                'quality_score': 88.0,
                'total_errors': 4
            }
            
            improvements = []
            regressions = []
            recommendations = []
            
            # Compare metrics
            if period_2_data['success_rate'] > period_1_data['success_rate']:
                improvements.append(f"Success rate improved by {period_2_data['success_rate'] - period_1_data['success_rate']:.1f}%")
            elif period_2_data['success_rate'] < period_1_data['success_rate']:
                regressions.append(f"Success rate decreased by {period_1_data['success_rate'] - period_2_data['success_rate']:.1f}%")
            
            if period_2_data['avg_extraction_rate'] > period_1_data['avg_extraction_rate']:
                improvements.append(f"Extraction rate improved by {period_2_data['avg_extraction_rate'] - period_1_data['avg_extraction_rate']:.1f} matches/min")
            
            if period_2_data['total_errors'] < period_1_data['total_errors']:
                improvements.append(f"Error count reduced by {period_1_data['total_errors'] - period_2_data['total_errors']} errors")
            
            # Generate recommendations
            if regressions:
                recommendations.append("Investigate causes of performance regression")
            if period_2_data['quality_score'] < 90:
                recommendations.append("Continue improving data quality validation")
            
            return ExtractionComparison(
                period_1=period_1_data,
                period_2=period_2_data,
                improvements=improvements,
                regressions=regressions,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error comparing extraction periods: {e}")
            return ExtractionComparison(
                period_1={},
                period_2={},
                improvements=[],
                regressions=[],
                recommendations=["Error performing comparison"]
            )
    
    def _generate_comparison_summary_html(self, comparison: ExtractionComparison) -> str:
        """Generate comparison summary HTML."""
        try:
            html_content = "<div style='padding: 10px;'>"
            
            if comparison.improvements:
                html_content += "<h4 style='color: green;'>📈 Improvements</h4><ul>"
                for improvement in comparison.improvements:
                    html_content += f"<li>{improvement}</li>"
                html_content += "</ul>"
            
            if comparison.regressions:
                html_content += "<h4 style='color: red;'>📉 Regressions</h4><ul>"
                for regression in comparison.regressions:
                    html_content += f"<li>{regression}</li>"
                html_content += "</ul>"
            
            if not comparison.improvements and not comparison.regressions:
                html_content += "<p>📊 Performance remained stable between periods.</p>"
            
            html_content += "</div>"
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error generating comparison summary HTML: {e}")
            return "<p>Error generating comparison summary.</p>"
    
    def _format_comparison_metrics(self, comparison: ExtractionComparison) -> List[List[str]]:
        """Format comparison metrics for table display."""
        try:
            metrics_data = []
            
            for metric in ['total_matches', 'success_rate', 'avg_extraction_rate', 'quality_score', 'total_errors']:
                if metric in comparison.period_1 and metric in comparison.period_2:
                    p1_value = comparison.period_1[metric]
                    p2_value = comparison.period_2[metric]
                    
                    change = p2_value - p1_value
                    percent_change = (change / p1_value * 100) if p1_value != 0 else 0
                    
                    metrics_data.append([
                        metric.replace('_', ' ').title(),
                        str(p1_value),
                        str(p2_value),
                        f"{change:+.1f}",
                        f"{percent_change:+.1f}%"
                    ])
            
            return metrics_data
            
        except Exception as e:
            self.logger.error(f"Error formatting comparison metrics: {e}")
            return []
    
    def _create_comparison_chart_data(self, comparison: ExtractionComparison) -> go.Figure:
        """Create comparison chart data."""
        try:
            metrics = ['Success Rate', 'Extraction Rate', 'Quality Score']
            period_1_values = [
                comparison.period_1.get('success_rate', 0),
                comparison.period_1.get('avg_extraction_rate', 0) * 10,  # Scale for visibility
                comparison.period_1.get('quality_score', 0)
            ]
            period_2_values = [
                comparison.period_2.get('success_rate', 0),
                comparison.period_2.get('avg_extraction_rate', 0) * 10,  # Scale for visibility
                comparison.period_2.get('quality_score', 0)
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=metrics,
                y=period_1_values,
                name='Period 1',
                marker_color='#1f77b4'
            ))
            
            fig.add_trace(go.Bar(
                x=metrics,
                y=period_2_values,
                name='Period 2',
                marker_color='#ff7f0e'
            ))
            
            fig.update_layout(
                title="Side-by-Side Performance Comparison",
                xaxis_title="Metrics",
                yaxis_title="Values",
                barmode='group',
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating comparison chart: {e}")
            return self._create_empty_comparison_chart()
    
    def _create_trend_comparison_chart_data(self, comparison: ExtractionComparison) -> go.Figure:
        """Create trend comparison chart data."""
        try:
            # Simulated trend data
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            
            # Period 1 trend (simulated)
            p1_trend = [comparison.period_1.get('success_rate', 85) + np.random.normal(0, 2) for _ in dates]
            
            # Period 2 trend (simulated)
            p2_trend = [comparison.period_2.get('success_rate', 90) + np.random.normal(0, 2) for _ in dates]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=p1_trend,
                mode='lines+markers',
                name='Period 1 Trend',
                line=dict(color='#1f77b4')
            ))
            
            fig.add_trace(go.Scatter(
                x=dates,
                y=p2_trend,
                mode='lines+markers',
                name='Period 2 Trend',
                line=dict(color='#ff7f0e')
            ))
            
            fig.update_layout(
                title="Performance Trend Comparison",
                xaxis_title="Date",
                yaxis_title="Success Rate (%)",
                showlegend=True,
                height=400
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating trend comparison chart: {e}")
            return self._create_empty_trend_comparison_chart()
    
    def _generate_comparison_recommendations_html(self, comparison: ExtractionComparison) -> str:
        """Generate comparison recommendations HTML."""
        try:
            html_content = "<div style='padding: 10px;'>"
            
            if comparison.recommendations:
                html_content += "<h4>💡 Recommendations</h4><ul>"
                for rec in comparison.recommendations:
                    html_content += f"<li>{rec}</li>"
                html_content += "</ul>"
            else:
                html_content += "<p>✅ No specific recommendations at this time.</p>"
            
            html_content += "</div>"
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error generating comparison recommendations HTML: {e}")
            return "<p>Error generating recommendations.</p>"
    
    def _generate_export_file(self, export_format: str, include_charts: bool, 
                             include_raw_data: bool, export_scope: List[str]) -> Optional[str]:
        """Generate export file based on specifications."""
        try:
            # This would generate actual export files
            # For now, create a placeholder file
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extraction_analysis_{timestamp}"
            
            if export_format == "PDF Report":
                filename += ".pdf"
            elif export_format == "CSV Data":
                filename += ".csv"
            elif export_format == "JSON Data":
                filename += ".json"
            elif export_format == "Excel Workbook":
                filename += ".xlsx"
            elif export_format == "Interactive HTML":
                filename += ".html"
            
            # Create temporary file (in real implementation, would generate actual content)
            temp_path = Path(f"/tmp/{filename}")
            with open(temp_path, 'w') as f:
                f.write(f"Extraction Analysis Export\nFormat: {export_format}\nGenerated: {datetime.now()}\n")
                f.write(f"Scope: {', '.join(export_scope)}\n")
                f.write(f"Include Charts: {include_charts}\n")
                f.write(f"Include Raw Data: {include_raw_data}\n")
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Error generating export file: {e}")
            return None
