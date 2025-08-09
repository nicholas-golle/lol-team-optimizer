"""
Advanced Extraction Monitoring Demo

This script demonstrates the advanced extraction monitoring and error handling
capabilities, including per-player progress tracking, API rate limit monitoring,
retry logic with exponential backoff, data quality validation, performance metrics,
and extraction cancellation with proper cleanup.
"""

import time
import logging
from datetime import datetime
from typing import List

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player
from lol_team_optimizer.advanced_extraction_monitor import (
    AdvancedExtractionMonitor,
    ExtractionStatus,
    ErrorSeverity
)
from lol_team_optimizer.enhanced_match_extraction_interface import EnhancedMatchExtractionInterface


def setup_logging():
    """Setup logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('advanced_extraction_demo.log')
        ]
    )


def create_sample_players() -> List[Player]:
    """Create sample players for testing."""
    return [
        Player(name="DemoPlayer1", summoner_name="TestSummoner1"),
        Player(name="DemoPlayer2", summoner_name="TestSummoner2"),
        Player(name="DemoPlayer3", summoner_name="TestSummoner3"),
        Player(name="DemoPlayer4", summoner_name="TestSummoner4"),
        Player(name="DemoPlayer5", summoner_name="TestSummoner5")
    ]


def demo_basic_monitoring():
    """Demonstrate basic monitoring capabilities."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Monitoring Capabilities")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        # Start monitoring
        monitor.start_monitoring()
        print("✅ Advanced monitoring started")
        
        # Create sample extraction operation
        players = create_sample_players()
        operation_id = "demo_operation_1"
        
        monitor.create_extraction_operation(operation_id, players)
        print(f"✅ Created extraction operation: {operation_id}")
        
        # Simulate progress updates
        for i, player in enumerate(players):
            print(f"📊 Updating progress for {player.name}")
            
            # Start extraction
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.RUNNING,
                'start_time': datetime.now(),
                'current_step': 'Fetching match history',
                'matches_requested': 100
            })
            
            time.sleep(1)  # Simulate processing time
            
            # Simulate some matches extracted
            matches_extracted = 25 + (i * 10)
            monitor.update_player_progress(operation_id, player.name, {
                'matches_extracted': matches_extracted,
                'current_step': f'Extracted {matches_extracted} matches',
                'extraction_rate': 15.0 + (i * 2)
            })
            
            time.sleep(0.5)
            
            # Complete extraction
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.COMPLETED,
                'end_time': datetime.now(),
                'current_step': 'Extraction completed successfully'
            })
        
        # Get operation status
        status = monitor.get_operation_status(operation_id)
        print(f"\n📈 Operation Status:")
        print(f"   Total Players: {status['total_players']}")
        print(f"   Completed: {status['completed_players']}")
        print(f"   Progress: {status['progress_percentage']:.1f}%")
        print(f"   Total Matches: {status['total_matches_extracted']}")
        
        # Wait for cleanup
        time.sleep(2)
        
        # Stop monitoring
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")
        
    except Exception as e:
        print(f"❌ Error in basic monitoring demo: {e}")


def demo_error_handling_and_retry():
    """Demonstrate error handling and retry logic."""
    print("\n" + "="*60)
    print("DEMO 2: Error Handling and Retry Logic")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        monitor.start_monitoring()
        print("✅ Advanced monitoring started")
        
        # Create extraction operation
        players = create_sample_players()[:3]  # Use fewer players for error demo
        operation_id = "demo_operation_2"
        
        monitor.create_extraction_operation(operation_id, players)
        print(f"✅ Created extraction operation: {operation_id}")
        
        # Simulate various error scenarios
        error_scenarios = [
            ("network_timeout", "Connection timeout", ErrorSeverity.MEDIUM),
            ("rate_limit_exceeded", "API rate limit exceeded", ErrorSeverity.HIGH),
            ("invalid_summoner", "Summoner not found", ErrorSeverity.HIGH)
        ]
        
        for i, (player, (error_type, error_msg, severity)) in enumerate(zip(players, error_scenarios)):
            print(f"\n🔄 Processing {player.name}")
            
            # Start extraction
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.RUNNING,
                'start_time': datetime.now(),
                'current_step': 'Starting extraction'
            })
            
            time.sleep(0.5)
            
            # Simulate error
            error_id = monitor.record_extraction_error(
                operation_id, player.name, error_type, error_msg, severity
            )
            print(f"❌ Recorded error: {error_type} - {error_msg}")
            
            # Check if should retry
            error = next(e for e in monitor.operation_errors[operation_id] if e.error_id == error_id)
            should_retry = monitor.retry_manager.should_retry(error)
            print(f"🔄 Should retry: {should_retry}")
            
            if should_retry:
                # Simulate retry
                retry_delay = monitor.retry_manager.get_retry_delay(error_id, 0)
                print(f"⏱️ Retry delay: {retry_delay:.2f} seconds")
                
                monitor.retry_manager.record_retry_attempt(error_id)
                
                # Simulate successful retry
                monitor.update_player_progress(operation_id, player.name, {
                    'status': ExtractionStatus.COMPLETED,
                    'end_time': datetime.now(),
                    'matches_extracted': 30,
                    'current_step': 'Completed after retry'
                })
                print(f"✅ Retry successful for {player.name}")
            else:
                # Mark as failed
                monitor.update_player_progress(operation_id, player.name, {
                    'status': ExtractionStatus.FAILED,
                    'end_time': datetime.now(),
                    'current_step': f'Failed: {error_msg}'
                })
                print(f"❌ Extraction failed for {player.name}")
        
        # Get final status
        status = monitor.get_operation_status(operation_id)
        print(f"\n📈 Final Status:")
        print(f"   Completed: {status['completed_players']}")
        print(f"   Failed: {status['failed_players']}")
        print(f"   Total Errors: {status['total_errors']}")
        
        # Show recent errors
        print(f"\n🔍 Recent Errors:")
        for error in status['recent_errors']:
            print(f"   {error['player_name']}: {error['error_type']} - {error['error_message']}")
        
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")
        
    except Exception as e:
        print(f"❌ Error in error handling demo: {e}")


def demo_rate_limit_monitoring():
    """Demonstrate API rate limit monitoring."""
    print("\n" + "="*60)
    print("DEMO 3: API Rate Limit Monitoring")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        print("✅ Rate limit monitor initialized")
        
        # Simulate API requests
        endpoint = "match_history"
        
        print(f"\n🚦 Testing rate limit for endpoint: {endpoint}")
        
        # Make several requests
        for i in range(10):
            can_make_request = monitor.rate_monitor.can_make_request(endpoint)
            print(f"Request {i+1}: Can make request = {can_make_request}")
            
            if can_make_request:
                monitor.rate_monitor.record_request(endpoint, success=True)
                print(f"   ✅ Request recorded successfully")
            else:
                wait_time = monitor.rate_monitor.get_wait_time(endpoint)
                print(f"   ⏱️ Must wait {wait_time:.2f} seconds")
            
            time.sleep(0.1)
        
        # Get current metrics
        metrics = monitor.rate_monitor.get_current_metrics()
        print(f"\n📊 Rate Limit Metrics:")
        print(f"   Global Throttled: {metrics['global_throttled']}")
        print(f"   Recent Requests: {metrics['recent_requests']}")
        
        if endpoint in metrics['endpoints']:
            endpoint_metrics = metrics['endpoints'][endpoint]
            print(f"   {endpoint} - Requests Made: {endpoint_metrics['requests_made']}")
            print(f"   {endpoint} - Can Make Request: {endpoint_metrics['can_make_request']}")
        
        # Simulate rate limit response
        print(f"\n🚫 Simulating rate limit response")
        from unittest.mock import Mock
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '30'}
        
        monitor.rate_monitor.handle_rate_limit_response(endpoint, mock_response)
        
        # Check if throttled
        can_make_request = monitor.rate_monitor.can_make_request(endpoint)
        wait_time = monitor.rate_monitor.get_wait_time(endpoint)
        
        print(f"   After rate limit response:")
        print(f"   Can make request: {can_make_request}")
        print(f"   Wait time: {wait_time:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Error in rate limit monitoring demo: {e}")


def demo_data_quality_validation():
    """Demonstrate data quality validation."""
    print("\n" + "="*60)
    print("DEMO 4: Data Quality Validation")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        print("✅ Data quality validator initialized")
        
        # Test valid match data
        print(f"\n✅ Testing valid match data")
        valid_match_data = {
            'gameId': 12345,
            'gameCreation': 1234567890,
            'gameDuration': 1800,  # 30 minutes
            'queueId': 420,
            'participants': [{'participantId': i} for i in range(10)],
            'teams': [{'teamId': 100}, {'teamId': 200}]
        }
        
        checks = monitor.quality_validator.validate_match_data(valid_match_data)
        quality_score = monitor.quality_validator.calculate_quality_score(checks)
        
        print(f"   Quality Score: {quality_score:.1f}%")
        print(f"   Validation Checks:")
        for check in checks:
            status = "✅" if check.passed else "❌"
            print(f"     {status} {check.check_name}: {check.message}")
        
        # Test invalid match data
        print(f"\n❌ Testing invalid match data")
        invalid_match_data = {
            'gameId': 12345,
            'gameDuration': 60,  # Too short
            'participants': [{'participantId': i} for i in range(5)]  # Wrong count
            # Missing required fields
        }
        
        checks = monitor.quality_validator.validate_match_data(invalid_match_data)
        quality_score = monitor.quality_validator.calculate_quality_score(checks)
        
        print(f"   Quality Score: {quality_score:.1f}%")
        print(f"   Validation Checks:")
        for check in checks:
            status = "✅" if check.passed else "❌"
            print(f"     {status} {check.check_name}: {check.message}")
            if not check.passed and check.data_sample:
                print(f"       Sample: {check.data_sample}")
        
        # Test participant data validation
        print(f"\n🔍 Testing participant data validation")
        invalid_participant = {
            'championId': 1,
            'spell1Id': 4,
            'teamId': 300,  # Invalid team ID
            # Missing required fields
        }
        
        participant_checks = monitor.quality_validator.validate_participant_data(invalid_participant)
        participant_score = monitor.quality_validator.calculate_quality_score(participant_checks)
        
        print(f"   Participant Quality Score: {participant_score:.1f}%")
        for check in participant_checks:
            status = "✅" if check.passed else "❌"
            print(f"     {status} {check.check_name}: {check.message}")
        
    except Exception as e:
        print(f"❌ Error in data quality validation demo: {e}")


def demo_performance_metrics():
    """Demonstrate performance metrics collection."""
    print("\n" + "="*60)
    print("DEMO 5: Performance Metrics Collection")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        monitor.start_monitoring()
        print("✅ Performance metrics collector initialized")
        
        # Create extraction operation
        players = create_sample_players()
        operation_id = "demo_operation_metrics"
        
        monitor.create_extraction_operation(operation_id, players)
        print(f"✅ Created extraction operation: {operation_id}")
        
        # Simulate extraction with varying performance
        for i, player in enumerate(players):
            print(f"📊 Processing {player.name}")
            
            # Simulate different performance characteristics
            extraction_rate = 10.0 + (i * 2)  # Varying rates
            matches_extracted = 40 + (i * 5)
            api_calls = 20 + (i * 2)
            errors = i % 2  # Some players have errors
            
            # Update progress
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.RUNNING,
                'start_time': datetime.now(),
                'matches_extracted': matches_extracted,
                'api_calls_made': api_calls,
                'error_count': errors,
                'extraction_rate': extraction_rate
            })
            
            time.sleep(0.5)
            
            # Complete extraction
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.COMPLETED,
                'end_time': datetime.now()
            })
        
        # Wait for metrics to be processed
        time.sleep(2)
        
        # Get performance metrics
        metrics = monitor.get_performance_metrics(operation_id)
        
        if metrics:
            print(f"\n📈 Performance Metrics:")
            print(f"   Total Players: {metrics.total_players}")
            print(f"   Completed Players: {metrics.completed_players}")
            print(f"   Total Matches Extracted: {metrics.total_matches_extracted}")
            print(f"   Average Extraction Rate: {metrics.average_extraction_rate:.2f} matches/min")
            print(f"   Peak Extraction Rate: {metrics.peak_extraction_rate:.2f} matches/min")
            print(f"   Efficiency Score: {metrics.efficiency_score:.1f}%")
            print(f"   Data Quality Score: {metrics.data_quality_score:.1f}%")
            
            # Get optimization suggestions
            suggestions = monitor.metrics_collector.get_optimization_suggestions(metrics)
            if suggestions:
                print(f"\n💡 Optimization Suggestions:")
                for suggestion in suggestions:
                    print(f"   • {suggestion}")
            else:
                print(f"\n✅ No optimization suggestions - performance is good!")
        else:
            print(f"❌ No performance metrics available")
        
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")
        
    except Exception as e:
        print(f"❌ Error in performance metrics demo: {e}")


def demo_extraction_cancellation():
    """Demonstrate extraction cancellation with proper cleanup."""
    print("\n" + "="*60)
    print("DEMO 6: Extraction Cancellation and Cleanup")
    print("="*60)
    
    try:
        # Initialize core engine
        core_engine = CoreEngine()
        
        # Create advanced monitor
        monitor = AdvancedExtractionMonitor(
            core_engine.config,
            core_engine.riot_client
        )
        
        monitor.start_monitoring()
        print("✅ Advanced monitoring started")
        
        # Create extraction operation
        players = create_sample_players()
        operation_id = "demo_operation_cancel"
        
        monitor.create_extraction_operation(operation_id, players)
        print(f"✅ Created extraction operation: {operation_id}")
        
        # Start some extractions
        for i, player in enumerate(players[:3]):
            monitor.update_player_progress(operation_id, player.name, {
                'status': ExtractionStatus.RUNNING,
                'start_time': datetime.now(),
                'current_step': f'Processing matches for {player.name}'
            })
            
            print(f"🔄 Started extraction for {player.name}")
            time.sleep(0.5)
        
        # Check operation status before cancellation
        status = monitor.get_operation_status(operation_id)
        print(f"\n📊 Status before cancellation:")
        print(f"   Running Players: {status['running_players']}")
        print(f"   Can Cancel: {status['can_cancel']}")
        
        # Cancel the operation
        print(f"\n🛑 Cancelling extraction operation...")
        success = monitor.cancel_operation(operation_id)
        print(f"   Cancellation successful: {success}")
        
        # Check if operation should be cancelled
        should_cancel = monitor.should_cancel_operation(operation_id)
        print(f"   Should cancel check: {should_cancel}")
        
        # Wait a moment for cleanup
        time.sleep(1)
        
        # Check final status
        final_status = monitor.get_operation_status(operation_id)
        print(f"\n📊 Status after cancellation:")
        print(f"   Running Players: {final_status['running_players']}")
        print(f"   Cancelled Players: {sum(1 for p in final_status['players'].values() if p['status'] == 'cancelled')}")
        
        # Show player statuses
        print(f"\n👥 Player Statuses:")
        for player_name, player_status in final_status['players'].items():
            print(f"   {player_name}: {player_status['status']}")
        
        # Wait for automatic cleanup
        print(f"\n🧹 Waiting for automatic cleanup...")
        time.sleep(3)
        
        # Check if operation was cleaned up
        try:
            cleanup_status = monitor.get_operation_status(operation_id)
            if 'error' in cleanup_status:
                print(f"✅ Operation cleaned up successfully")
            else:
                print(f"⏳ Operation still in cleanup process")
        except:
            print(f"✅ Operation cleaned up successfully")
        
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")
        
    except Exception as e:
        print(f"❌ Error in cancellation demo: {e}")


def main():
    """Run all demonstration scenarios."""
    print("🚀 Advanced Extraction Monitoring Demo")
    print("This demo showcases the comprehensive monitoring and error handling capabilities")
    print("of the advanced extraction monitoring system.")
    
    setup_logging()
    
    try:
        # Run all demos
        demo_basic_monitoring()
        demo_error_handling_and_retry()
        demo_rate_limit_monitoring()
        demo_data_quality_validation()
        demo_performance_metrics()
        demo_extraction_cancellation()
        
        print("\n" + "="*60)
        print("🎉 All demos completed successfully!")
        print("="*60)
        print("\nKey features demonstrated:")
        print("✅ Per-player progress tracking")
        print("✅ API rate limit monitoring and automatic throttling")
        print("✅ Retry logic with exponential backoff")
        print("✅ Data quality validation and integrity checks")
        print("✅ Performance metrics and optimization suggestions")
        print("✅ Extraction cancellation with proper cleanup")
        print("✅ Comprehensive error handling and recovery")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()