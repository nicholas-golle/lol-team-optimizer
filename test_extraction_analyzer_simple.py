#!/usr/bin/env python3
"""
Simple test for extraction result analyzer functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock
from datetime import datetime

from lol_team_optimizer.extraction_result_analyzer import (
    ExtractionResultAnalyzer, ExtractionSummary, QualityIndicator,
    PerformanceMetric, ExtractionComparison
)
from lol_team_optimizer.advanced_extraction_monitor import (
    AdvancedExtractionMonitor, ExtractionStatus, PlayerProgress
)

def test_extraction_result_analyzer():
    """Test basic functionality of ExtractionResultAnalyzer."""
    print("Testing ExtractionResultAnalyzer...")
    
    # Create mock objects
    mock_core_engine = Mock()
    mock_advanced_monitor = Mock(spec=AdvancedExtractionMonitor)
    
    # Setup mock data
    mock_advanced_monitor.active_operations = {
        'test_op_1': {
            'player1': PlayerProgress(
                player_name='player1',
                status=ExtractionStatus.COMPLETED,
                matches_extracted=50,
                api_calls_made=10,
                extraction_rate=5.0
            )
        }
    }
    mock_advanced_monitor.operation_errors = {'test_op_1': []}
    
    # Create analyzer
    analyzer = ExtractionResultAnalyzer(mock_core_engine, mock_advanced_monitor)
    
    # Test initialization
    assert analyzer.core_engine is not None
    assert analyzer.advanced_monitor is not None
    assert analyzer.visualization_manager is not None
    print("✓ Initialization test passed")
    
    # Test interface creation
    components = analyzer.create_extraction_analysis_interface()
    assert isinstance(components, dict)
    assert len(components) > 0
    print("✓ Interface creation test passed")
    
    # Test summary generation
    summary = analyzer._generate_extraction_summary('test_op_1')
    assert isinstance(summary, ExtractionSummary)
    assert summary.operation_id == 'test_op_1'
    print("✓ Summary generation test passed")
    
    # Test quality analysis
    quality_data = analyzer._analyze_data_quality('test_op_1')
    assert isinstance(quality_data, dict)
    assert 'overall_score' in quality_data
    print("✓ Quality analysis test passed")
    
    # Test performance analysis
    performance_data = analyzer._analyze_performance('test_op_1')
    assert isinstance(performance_data, dict)
    assert 'metrics' in performance_data
    print("✓ Performance analysis test passed")
    
    # Test chart creation
    progress_chart = analyzer._create_empty_progress_chart()
    assert progress_chart is not None
    print("✓ Chart creation test passed")
    
    # Test comparison
    comparison = analyzer._compare_extraction_periods("Last 7 days", "Last 14 days")
    assert isinstance(comparison, ExtractionComparison)
    print("✓ Comparison test passed")
    
    print("All tests passed! ✅")

def test_data_classes():
    """Test data class creation."""
    print("Testing data classes...")
    
    # Test ExtractionSummary
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
    assert summary.operation_id == 'test'
    assert summary.success_rate == 80.0
    print("✓ ExtractionSummary test passed")
    
    # Test QualityIndicator
    indicator = QualityIndicator(
        indicator_name="Test Indicator",
        current_value=85.0,
        target_value=90.0,
        status="good",
        description="Test description"
    )
    assert indicator.indicator_name == "Test Indicator"
    assert indicator.status == "good"
    print("✓ QualityIndicator test passed")
    
    # Test PerformanceMetric
    metric = PerformanceMetric(
        metric_name="Test Metric",
        value=75.0,
        unit="%",
        trend="improving"
    )
    assert metric.metric_name == "Test Metric"
    assert metric.trend == "improving"
    print("✓ PerformanceMetric test passed")
    
    print("Data class tests passed! ✅")

if __name__ == '__main__':
    try:
        test_data_classes()
        test_extraction_result_analyzer()
        print("\n🎉 All extraction result analyzer tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)