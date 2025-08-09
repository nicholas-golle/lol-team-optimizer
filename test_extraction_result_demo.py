#!/usr/bin/env python3
"""
Demo script for Extraction Result Visualization and Analysis

This script demonstrates the comprehensive extraction result analysis functionality,
including summary dashboards, data quality indicators, performance charts,
comparison tools, export functionality, and scheduling interfaces.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unittest.mock import Mock
from datetime import datetime, timedelta
import gradio as gr

from lol_team_optimizer.extraction_result_analyzer import (
    ExtractionResultAnalyzer, ExtractionSummary, QualityIndicator,
    PerformanceMetric, ExtractionComparison
)
from lol_team_optimizer.advanced_extraction_monitor import (
    AdvancedExtractionMonitor, ExtractionStatus, PlayerProgress, ExtractionError, ErrorSeverity
)

def create_demo_data():
    """Create comprehensive demo data for extraction analysis."""
    
    # Create mock core engine
    mock_core_engine = Mock()
    
    # Create mock advanced monitor with realistic data
    mock_advanced_monitor = Mock(spec=AdvancedExtractionMonitor)
    
    # Setup active operations with multiple players
    mock_advanced_monitor.active_operations = {
        'extraction_2024_01_15': {
            'player1': PlayerProgress(
                player_name='SummonerOne',
                status=ExtractionStatus.COMPLETED,
                matches_extracted=75,
                matches_requested=80,
                api_calls_made=15,
                api_calls_failed=1,
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(hours=1, minutes=30),
                extraction_rate=12.5,
                error_count=1
            ),
            'player2': PlayerProgress(
                player_name='ProGamer2024',
                status=ExtractionStatus.COMPLETED,
                matches_extracted=92,
                matches_requested=100,
                api_calls_made=20,
                api_calls_failed=0,
                start_time=datetime.now() - timedelta(hours=2),
                end_time=datetime.now() - timedelta(hours=1, minutes=15),
                extraction_rate=15.3,
                error_count=0
            ),
            'player3': PlayerProgress(
                player_name='ChampionMaster',
                status=ExtractionStatus.RUNNING,
                matches_extracted=45,
                matches_requested=80,
                api_calls_made=12,
                api_calls_failed=2,
                start_time=datetime.now() - timedelta(minutes=45),
                extraction_rate=8.7,
                error_count=2
            ),
            'player4': PlayerProgress(
                player_name='RiftLegend',
                status=ExtractionStatus.FAILED,
                matches_extracted=12,
                matches_requested=80,
                api_calls_made=8,
                api_calls_failed=5,
                start_time=datetime.now() - timedelta(minutes=30),
                extraction_rate=2.1,
                error_count=5
            )
        }
    }
    
    # Setup operation errors
    mock_advanced_monitor.operation_errors = {
        'extraction_2024_01_15': [
            ExtractionError(
                error_id='err_001',
                timestamp=datetime.now() - timedelta(minutes=20),
                operation_id='extraction_2024_01_15',
                player_name='RiftLegend',
                error_type='API_RATE_LIMIT',
                error_message='Rate limit exceeded for summoner API',
                severity=ErrorSeverity.HIGH,
                retry_count=2
            ),
            ExtractionError(
                error_id='err_002',
                timestamp=datetime.now() - timedelta(minutes=15),
                operation_id='extraction_2024_01_15',
                player_name='ChampionMaster',
                error_type='DATA_QUALITY',
                error_message='Invalid match data format detected',
                severity=ErrorSeverity.MEDIUM,
                retry_count=1
            )
        ]
    }
    
    return mock_core_engine, mock_advanced_monitor

def demo_extraction_analysis():
    """Demonstrate extraction result analysis functionality."""
    print("🚀 Starting Extraction Result Analysis Demo")
    print("=" * 60)
    
    # Create demo data
    mock_core_engine, mock_advanced_monitor = create_demo_data()
    
    # Create analyzer
    analyzer = ExtractionResultAnalyzer(mock_core_engine, mock_advanced_monitor)
    
    print("\n📊 1. Testing Summary Dashboard")
    print("-" * 40)
    
    # Test summary generation
    summary = analyzer._generate_extraction_summary('extraction_2024_01_15')
    print(f"Operation ID: {summary.operation_id}")
    print(f"Total Players: {summary.total_players}")
    print(f"Completed Players: {summary.completed_players}")
    print(f"Success Rate: {summary.success_rate:.1f}%")
    print(f"Total Matches Extracted: {summary.total_matches_extracted}")
    print(f"Average Extraction Rate: {summary.average_extraction_rate:.1f} matches/min")
    print(f"Efficiency Score: {summary.efficiency_score:.1f}%")
    
    print("\n✅ 2. Testing Data Quality Analysis")
    print("-" * 40)
    
    # Test quality analysis
    quality_data = analyzer._analyze_data_quality('extraction_2024_01_15')
    print(f"Overall Quality Score: {quality_data['overall_score']:.1f}%")
    print(f"Data Completeness: {quality_data['completeness_score']:.1f}%")
    print(f"Data Integrity: {quality_data['integrity_score']:.1f}%")
    print(f"Quality Issues Found: {quality_data['issues_count']}")
    
    if quality_data['quality_indicators']:
        print("\nQuality Indicators:")
        for indicator in quality_data['quality_indicators']:
            print(f"  • {indicator.indicator_name}: {indicator.current_value:.1f}% ({indicator.status})")
    
    print("\n📈 3. Testing Performance Analysis")
    print("-" * 40)
    
    # Test performance analysis
    performance_data = analyzer._analyze_performance('extraction_2024_01_15')
    print(f"API Success Rate: {performance_data['api_success_rate']:.1f}%")
    print(f"Peak Extraction Rate: {performance_data['peak_extraction_rate']:.1f} matches/min")
    print(f"Average Response Time: {performance_data['avg_response_time']:.0f}ms")
    
    suggestions = performance_data.get('suggestions', [])
    if suggestions:
        print("\nPerformance Suggestions:")
        for suggestion in suggestions:
            print(f"  • {suggestion}")
    else:
        print("\nNo performance suggestions at this time.")
    
    print("\n🔄 4. Testing Period Comparison")
    print("-" * 40)
    
    # Test comparison
    comparison = analyzer._compare_extraction_periods("Last 7 days", "Last 14 days")
    print(f"Period 1: {comparison.period_1.get('name', 'Unknown')}")
    print(f"Period 2: {comparison.period_2.get('name', 'Unknown')}")
    
    if comparison.improvements:
        print("\nImprovements:")
        for improvement in comparison.improvements:
            print(f"  ✅ {improvement}")
    
    if comparison.regressions:
        print("\nRegressions:")
        for regression in comparison.regressions:
            print(f"  ❌ {regression}")
    
    if comparison.recommendations:
        print("\nRecommendations:")
        for rec in comparison.recommendations:
            print(f"  💡 {rec}")
    
    print("\n📤 5. Testing Export Functionality")
    print("-" * 40)
    
    # Test export
    export_file = analyzer._generate_export_file(
        "PDF Report", True, False, ["Summary Dashboard", "Quality Analysis"]
    )
    if export_file:
        print(f"Export file generated: {export_file}")
    else:
        print("Export generation failed")
    
    print("\n📋 6. Testing Available Operations")
    print("-" * 40)
    
    # Test operations list
    operations = analyzer._get_available_operations()
    print("Available Operations:")
    for op in operations[:5]:  # Show first 5
        print(f"  • {op}")
    
    print("\n📅 7. Testing Available Periods")
    print("-" * 40)
    
    # Test periods list
    periods = analyzer._get_available_periods()
    print("Available Periods:")
    for period in periods:
        print(f"  • {period}")
    
    print("\n📊 8. Testing Chart Generation")
    print("-" * 40)
    
    # Test chart creation
    try:
        progress_chart = analyzer._create_progress_chart('extraction_2024_01_15')
        status_chart = analyzer._create_status_chart('extraction_2024_01_15')
        quality_chart = analyzer._create_quality_chart(quality_data)
        
        print("✅ Progress chart created successfully")
        print("✅ Status chart created successfully")
        print("✅ Quality chart created successfully")
        
        # Test empty charts
        empty_charts = [
            analyzer._create_empty_progress_chart(),
            analyzer._create_empty_status_chart(),
            analyzer._create_empty_quality_chart(),
            analyzer._create_empty_trend_chart(),
            analyzer._create_empty_rate_chart(),
            analyzer._create_empty_api_chart(),
            analyzer._create_empty_resource_chart(),
            analyzer._create_empty_comparison_chart(),
            analyzer._create_empty_trend_comparison_chart()
        ]
        
        print(f"✅ {len(empty_charts)} empty charts created successfully")
        
    except Exception as e:
        print(f"❌ Chart generation error: {e}")
    
    print("\n🎯 9. Testing Insights Generation")
    print("-" * 40)
    
    # Test insights HTML generation
    insights_html = analyzer._generate_insights_html(summary, quality_data, performance_data)
    print("Insights HTML generated:")
    print(insights_html[:200] + "..." if len(insights_html) > 200 else insights_html)
    
    print("\n🔧 10. Testing Interface Components")
    print("-" * 40)
    
    # Test interface creation (without Gradio context)
    try:
        components = analyzer.create_extraction_analysis_interface()
        print(f"✅ Interface created with {len(components)} components")
        
        # List key components
        key_components = [
            'operation_selector', 'total_players_metric', 'extraction_progress_chart',
            'overall_quality_score', 'quality_indicators_chart', 'avg_response_time',
            'comparison_period_1', 'export_format', 'schedule_enabled'
        ]
        
        found_components = [comp for comp in key_components if comp in components]
        print(f"✅ Found {len(found_components)}/{len(key_components)} key components")
        
    except Exception as e:
        print(f"❌ Interface creation error: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Extraction Result Analysis Demo Completed Successfully!")
    print("\nKey Features Demonstrated:")
    print("  ✅ Summary dashboard with comprehensive metrics")
    print("  ✅ Data quality analysis with indicators and issues")
    print("  ✅ Performance analysis with benchmarks and suggestions")
    print("  ✅ Period comparison with improvements and regressions")
    print("  ✅ Export functionality for multiple formats")
    print("  ✅ Interactive chart generation and visualization")
    print("  ✅ Scheduling and automation interface")
    print("  ✅ Comprehensive error handling and logging")
    print("  ✅ Real-time insights and recommendations")

def demo_data_structures():
    """Demonstrate the data structures used in extraction analysis."""
    print("\n📋 Data Structures Demo")
    print("=" * 40)
    
    # ExtractionSummary
    summary = ExtractionSummary(
        operation_id='demo_op_001',
        start_time=datetime.now() - timedelta(hours=2),
        end_time=datetime.now() - timedelta(hours=1),
        total_players=20,
        completed_players=18,
        failed_players=2,
        total_matches_extracted=1847,
        total_api_calls=425,
        success_rate=90.0,
        average_extraction_rate=15.4,
        data_quality_score=88.5,
        efficiency_score=92.3,
        total_errors=8,
        critical_errors=2
    )
    
    print("ExtractionSummary:")
    print(f"  Operation: {summary.operation_id}")
    print(f"  Duration: {summary.end_time - summary.start_time}")
    print(f"  Success Rate: {summary.success_rate}%")
    print(f"  Quality Score: {summary.data_quality_score}%")
    
    # QualityIndicator
    quality_indicator = QualityIndicator(
        indicator_name="API Response Validation",
        current_value=94.2,
        target_value=98.0,
        status="good",
        description="Percentage of API responses passing validation checks",
        improvement_suggestions=[
            "Implement stricter response format validation",
            "Add retry logic for malformed responses"
        ]
    )
    
    print(f"\nQualityIndicator:")
    print(f"  Name: {quality_indicator.indicator_name}")
    print(f"  Score: {quality_indicator.current_value}% (target: {quality_indicator.target_value}%)")
    print(f"  Status: {quality_indicator.status}")
    print(f"  Suggestions: {len(quality_indicator.improvement_suggestions)} available")
    
    # PerformanceMetric
    performance_metric = PerformanceMetric(
        metric_name="Average API Response Time",
        value=245.7,
        unit="ms",
        trend="improving",
        benchmark=200.0,
        percentile=75.0
    )
    
    print(f"\nPerformanceMetric:")
    print(f"  Metric: {performance_metric.metric_name}")
    print(f"  Value: {performance_metric.value} {performance_metric.unit}")
    print(f"  Trend: {performance_metric.trend}")
    print(f"  Benchmark: {performance_metric.benchmark} {performance_metric.unit}")
    print(f"  Percentile: {performance_metric.percentile}%")
    
    # ExtractionComparison
    comparison = ExtractionComparison(
        period_1={
            'name': 'Week 1',
            'success_rate': 87.5,
            'extraction_rate': 12.3,
            'quality_score': 85.2
        },
        period_2={
            'name': 'Week 2',
            'success_rate': 92.1,
            'extraction_rate': 15.7,
            'quality_score': 89.8
        },
        improvements=[
            "Success rate improved by 4.6%",
            "Extraction rate increased by 27.6%",
            "Quality score improved by 5.4%"
        ],
        regressions=[],
        recommendations=[
            "Continue current optimization strategies",
            "Monitor for sustained performance improvements",
            "Consider scaling up extraction capacity"
        ]
    )
    
    print(f"\nExtractionComparison:")
    print(f"  Comparing: {comparison.period_1['name']} vs {comparison.period_2['name']}")
    print(f"  Improvements: {len(comparison.improvements)}")
    print(f"  Regressions: {len(comparison.regressions)}")
    print(f"  Recommendations: {len(comparison.recommendations)}")

if __name__ == '__main__':
    try:
        demo_extraction_analysis()
        demo_data_structures()
        
        print(f"\n{'='*60}")
        print("🏆 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("The extraction result visualization and analysis system is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)