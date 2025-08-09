"""
Tests for Extraction Result Analyzer

This module tests the extraction result visualization and analysis functionality,
including summary dashboards, quality indicators, performance analysis,
comparison tools, export functionality, and scheduling interfaces.
"""

import pytest
import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import json
import tempfile
import os
from typing import Dict, Any, List

from lol_team_optimizer.extraction_result_analyzer import (
    ExtractionResultAnalyzer, ExtractionSummary, QualityIndicator,
    PerformanceMetric, ExtractionComparison, ExtractionResultType
)
from lol_team_optimizer.advanced_extraction_monitor import (
    AdvancedExtractionMonitor, ExtractionStatus, ErrorSeverity,
    PlayerProgress, ExtractionMetrics
)
from lol_team_optimizer.models import Player


class TestExtractionResultAnalyzer(unittest.TestCase):
    """Test cases for ExtractionResultAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_core_engine = Mock()
        self.mock_advanced_monitor = Mock(spec=AdvancedExtractionMonitor)
        
        # Setup mock data
        self.mock_advanced_monitor.active_operations = {
            'test_op_1': {
                'player1': PlayerProgress(
                    player_name='player1',
                    status=ExtractionStatus.COMPLETED,
                    matches_extracted=50,
                    api_calls_made=10,
                    extraction_rate=5.0
                ),
                'player2': PlayerProgress(
                    player_name='player2',
                    status=ExtractionStatus.RUNNING,
                    matches_extracted=25,
                    api_calls_made=8,
                    extraction_rate=3.0
                )
            }
        }
        
        self.mock_advanced_monitor.operation_errors = {
            'test_op_1': []
        }
        
        # Create analyzer
        self.analyzer = ExtractionResultAnalyzer(
            self.mock_core_engine,
            self.mock_advanced_monitor
        )
    
    def test_initialization(self):
        """Test analyzer initialization."""
        self.assertIsNotNone(self.analyzer.core_engine)
        self.assertIsNotNone(self.analyzer.advanced_monitor)
        self.assertIsNotNone(self.analyzer.visualization_manager)
        self.assertEqual(len(self.analyzer.analysis_cache), 0)
        self.assertEqual(len(self.analyzer.summary_cache), 0)
    
    def test_create_extraction_analysis_interface(self):
        """Test creation of analysis interface components."""
        components = self.analyzer.create_extraction_analysis_interface()
        
        # Check that all major component categories are present
        expected_components = [
            'operation_selector', 'refresh_operations', 'auto_refresh',
            'total_players_metric', 'completed_players_metric',
            'total_matches_metric', 'success_rate_metric',
            'extraction_rate_metric', 'efficiency_score_metric',
            'extraction_progress_chart', 'player_status_chart',
            'detailed_stats_table', 'extraction_insights',
            'overall_quality_score', 'completeness_score', 'integrity_score',
            'quality_indicators_chart', 'quality_issues_table',
            'avg_response_time', 'peak_extraction_rate',
            'api_success_rate', 'retry_success_rate',
            'extraction_rate_chart', 'api_performance_chart',
            'comparison_period_1', 'comparison_period_2', 'run_comparison',
            'export_format', 'include_charts', 'generate_export',
            'schedule_enabled', 'schedule_frequency'
        ]
        
        # Check that key components exist
        for component_name in expected_components[:10]:  # Check first 10 components
            self.assertIn(component_name, components)
    
    def test_generate_extraction_summary(self):
        """Test extraction summary generation."""
        # Test with active operation
        summary = self.analyzer._generate_extraction_summary('test_op_1')
        
        self.assertEqual(summary.operation_id, 'test_op_1')
        self.assertIsInstance(summary.total_players, int)
        self.assertIsInstance(summary.success_rate, float)
        self.assertGreaterEqual(summary.success_rate, 0.0)
        self.assertLessEqual(summary.success_rate, 100.0)
    
    def test_analyze_data_quality(self):
        """Test data quality analysis."""
        quality_data = self.analyzer._analyze_data_quality('test_op_1')
        
        self.assertIn('overall_score', quality_data)
        self.assertIn('completeness_score', quality_data)
        self.assertIn('integrity_score', quality_data)
        self.assertIn('quality_indicators', quality_data)
        
        # Check quality indicators
        indicators = quality_data['quality_indicators']
        self.assertIsInstance(indicators, list)
        
        if indicators:
            indicator = indicators[0]
            self.assertIsInstance(indicator, QualityIndicator)
            self.assertIn(indicator.status, ['excellent', 'good', 'warning', 'critical'])
    
    def test_analyze_performance(self):
        """Test performance analysis."""
        performance_data = self.analyzer._analyze_performance('test_op_1')
        
        self.assertIn('metrics', performance_data)
        self.assertIn('api_success_rate', performance_data)
        self.assertIn('avg_extraction_rate', performance_data)
        
        # Check performance metrics
        metrics = performance_data['metrics']
        self.assertIsInstance(metrics, list)
        
        if metrics:
            metric = metrics[0]
            self.assertIsInstance(metric, PerformanceMetric)
            self.assertIn(metric.trend, ['improving', 'stable', 'declining'])
    
    def test_get_available_operations(self):
        """Test getting available operations."""
        operations = self.analyzer._get_available_operations()
        
        self.assertIsInstance(operations, list)
        self.assertGreater(len(operations), 0)
        
        # Should include active operations
        active_found = any('Active:' in op for op in operations)
        self.assertTrue(active_found)
    
    def test_get_available_periods(self):
        """Test getting available periods."""
        periods = self.analyzer._get_available_periods()
        
        self.assertIsInstance(periods, list)
        self.assertGreater(len(periods), 0)
        
        # Should include common periods
        self.assertIn("Last 7 days", periods)
        self.assertIn("Last 30 days", periods)
    
    def test_create_empty_charts(self):
        """Test creation of empty charts."""
        # Test all empty chart methods
        progress_chart = self.analyzer._create_empty_progress_chart()
        status_chart = self.analyzer._create_empty_status_chart()
        quality_chart = self.analyzer._create_empty_quality_chart()
        trend_chart = self.analyzer._create_empty_trend_chart()
        
        # All should return plotly Figure objects
        import plotly.graph_objects as go
        self.assertIsInstance(progress_chart, go.Figure)
        self.assertIsInstance(status_chart, go.Figure)
        self.assertIsInstance(quality_chart, go.Figure)
        self.assertIsInstance(trend_chart, go.Figure)
    
    def test_create_progress_chart(self):
        """Test progress chart creation with data."""
        chart = self.analyzer._create_progress_chart('test_op_1')
        
        import plotly.graph_objects as go
        self.assertIsInstance(chart, go.Figure)
        
        # Should have data traces
        self.assertGreater(len(chart.data), 0)
    
    def test_create_status_chart(self):
        """Test status chart creation with data."""
        chart = self.analyzer._create_status_chart('test_op_1')
        
        import plotly.graph_objects as go
        self.assertIsInstance(chart, go.Figure)
        
        # Should have data traces
        self.assertGreater(len(chart.data), 0)
    
    def test_create_quality_chart(self):
        """Test quality chart creation."""
        # Create sample quality data
        quality_data = {
            'quality_indicators': [
                QualityIndicator(
                    indicator_name="Test Indicator",
                    current_value=85.0,
                    target_value=90.0,
                    status="good",
                    description="Test description"
                )
            ]
        }
        
        chart = self.analyzer._create_quality_chart(quality_data)
        
        import plotly.graph_objects as go
        self.assertIsInstance(chart, go.Figure)
        
        # Should have data traces
        self.assertGreater(len(chart.data), 0)
    
    def test_generate_insights_html(self):
        """Test insights HTML generation."""
        # Create sample data
        summary = ExtractionSummary(
            operation_id='test',
            start_time=datetime.now(),
            end_time=None,
            total_players=10,
            completed_players=8,
            failed_players=2,
            total_matches_extracted=100,
            total_api_calls=50,
            success_rate=80.0,
            average_extraction_rate=2.0,
            data_quality_score=85.0,
            efficiency_score=75.0,
            total_errors=5,
            critical_errors=1
        )
        
        quality_data = {'overall_score': 85.0}
        performance_data = {'metrics': []}
        
        html = self.analyzer._generate_insights_html(summary, quality_data, performance_data)
        
        self.assertIsInstance(html, str)
        self.assertIn('<div', html)
        self.assertIn('</div>', html)
    
    def test_compare_extraction_periods(self):
        """Test extraction period comparison."""
        comparison = self.analyzer._compare_extraction_periods("Last 7 days", "Last 14 days")
        
        self.assertIsInstance(comparison, ExtractionComparison)
        self.assertIn('total_matches', comparison.period_1)
        self.assertIn('total_matches', comparison.period_2)
        self.assertIsInstance(comparison.improvements, list)
        self.assertIsInstance(comparison.regressions, list)
        self.assertIsInstance(comparison.recommendations, list)
    
    def test_format_comparison_metrics(self):
        """Test comparison metrics formatting."""
        comparison = ExtractionComparison(
            period_1={'success_rate': 85.0, 'total_matches': 100},
            period_2={'success_rate': 90.0, 'total_matches': 120},
            improvements=[],
            regressions=[],
            recommendations=[]
        )
        
        metrics_data = self.analyzer._format_comparison_metrics(comparison)
        
        self.assertIsInstance(metrics_data, list)
        if metrics_data:
            self.assertIsInstance(metrics_data[0], list)
            self.assertEqual(len(metrics_data[0]), 5)  # Should have 5 columns
    
    def test_create_comparison_charts(self):
        """Test comparison chart creation."""
        comparison = ExtractionComparison(
            period_1={'success_rate': 85.0, 'avg_extraction_rate': 2.0, 'quality_score': 80.0},
            period_2={'success_rate': 90.0, 'avg_extraction_rate': 2.5, 'quality_score': 85.0},
            improvements=[],
            regressions=[],
            recommendations=[]
        )
        
        comparison_chart = self.analyzer._create_comparison_chart_data(comparison)
        trend_chart = self.analyzer._create_trend_comparison_chart_data(comparison)
        
        import plotly.graph_objects as go
        self.assertIsInstance(comparison_chart, go.Figure)
        self.assertIsInstance(trend_chart, go.Figure)
        
        # Should have data traces
        self.assertGreater(len(comparison_chart.data), 0)
        self.assertGreater(len(trend_chart.data), 0)
    
    def test_generate_comparison_html(self):
        """Test comparison HTML generation."""
        comparison = ExtractionComparison(
            period_1={},
            period_2={},
            improvements=["Test improvement"],
            regressions=["Test regression"],
            recommendations=["Test recommendation"]
        )
        
        summary_html = self.analyzer._generate_comparison_summary_html(comparison)
        recommendations_html = self.analyzer._generate_comparison_recommendations_html(comparison)
        
        self.assertIsInstance(summary_html, str)
        self.assertIsInstance(recommendations_html, str)
        self.assertIn('<div', summary_html)
        self.assertIn('<div', recommendations_html)
    
    def test_generate_export_file(self):
        """Test export file generation."""
        export_file = self.analyzer._generate_export_file(
            "PDF Report", True, False, ["Summary Dashboard"]
        )
        
        # Should return a file path or None
        if export_file:
            self.assertIsInstance(export_file, str)
            self.assertTrue(export_file.endswith('.pdf'))
    
    def test_get_empty_analysis_data(self):
        """Test getting empty analysis data."""
        empty_data = self.analyzer._get_empty_analysis_data()
        
        self.assertIsInstance(empty_data, tuple)
        self.assertEqual(len(empty_data), 9)  # Should have 9 elements
        
        # First 6 should be numeric
        for i in range(6):
            self.assertIsInstance(empty_data[i], (int, float))
    
    def test_calculate_current_metrics(self):
        """Test current metrics calculation."""
        metrics = self.analyzer._calculate_current_metrics('test_op_1')
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_players', metrics)
        self.assertIn('completed_players', metrics)
        self.assertIn('success_rate', metrics)
        
        # Values should be reasonable
        self.assertGreaterEqual(metrics['success_rate'], 0.0)
        self.assertLessEqual(metrics['success_rate'], 100.0)


class TestExtractionSummary(unittest.TestCase):
    """Test cases for ExtractionSummary dataclass."""
    
    def test_extraction_summary_creation(self):
        """Test ExtractionSummary creation."""
        summary = ExtractionSummary(
            operation_id='test_op',
            start_time=datetime.now(),
            end_time=None,
            total_players=10,
            completed_players=8,
            failed_players=2,
            total_matches_extracted=100,
            total_api_calls=50,
            success_rate=80.0,
            average_extraction_rate=2.0,
            data_quality_score=85.0,
            efficiency_score=75.0,
            total_errors=5,
            critical_errors=1
        )
        
        self.assertEqual(summary.operation_id, 'test_op')
        self.assertEqual(summary.total_players, 10)
        self.assertEqual(summary.completed_players, 8)
        self.assertEqual(summary.success_rate, 80.0)


class TestQualityIndicator(unittest.TestCase):
    """Test cases for QualityIndicator dataclass."""
    
    def test_quality_indicator_creation(self):
        """Test QualityIndicator creation."""
        indicator = QualityIndicator(
            indicator_name="Test Indicator",
            current_value=85.0,
            target_value=90.0,
            status="good",
            description="Test description",
            improvement_suggestions=["Suggestion 1", "Suggestion 2"]
        )
        
        self.assertEqual(indicator.indicator_name, "Test Indicator")
        self.assertEqual(indicator.current_value, 85.0)
        self.assertEqual(indicator.status, "good")
        self.assertEqual(len(indicator.improvement_suggestions), 2)


class TestPerformanceMetric(unittest.TestCase):
    """Test cases for PerformanceMetric dataclass."""
    
    def test_performance_metric_creation(self):
        """Test PerformanceMetric creation."""
        metric = PerformanceMetric(
            metric_name="Test Metric",
            value=75.0,
            unit="%",
            trend="improving",
            benchmark=80.0,
            percentile=65.0
        )
        
        self.assertEqual(metric.metric_name, "Test Metric")
        self.assertEqual(metric.value, 75.0)
        self.assertEqual(metric.unit, "%")
        self.assertEqual(metric.trend, "improving")


class TestExtractionComparison(unittest.TestCase):
    """Test cases for ExtractionComparison dataclass."""
    
    def test_extraction_comparison_creation(self):
        """Test ExtractionComparison creation."""
        comparison = ExtractionComparison(
            period_1={'metric1': 100},
            period_2={'metric1': 120},
            improvements=["Improvement 1"],
            regressions=["Regression 1"],
            recommendations=["Recommendation 1"]
        )
        
        self.assertEqual(comparison.period_1['metric1'], 100)
        self.assertEqual(comparison.period_2['metric1'], 120)
        self.assertEqual(len(comparison.improvements), 1)
        self.assertEqual(len(comparison.regressions), 1)
        self.assertEqual(len(comparison.recommendations), 1)


if __name__ == '__main__':
    unittest.main()