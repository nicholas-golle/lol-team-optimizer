#!/usr/bin/env python3
"""
Comprehensive Analytics Test Suite Runner

This script runs the complete analytics test suite including:
- End-to-end integration tests
- Performance benchmarks
- Data quality tests
- Statistical accuracy tests
- User interface tests
- Load tests

Usage:
    python tests/run_comprehensive_analytics_tests.py [--quick] [--performance] [--full]
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path


def run_test_suite(test_pattern: str, description: str, timeout: int = 300) -> bool:
    """Run a test suite and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            test_pattern, 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True, timeout=timeout + 30)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Duration: {duration:.2f} seconds")
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout:
                # Show summary line
                lines = result.stdout.strip().split('\n')
                for line in lines[-5:]:
                    if 'passed' in line or 'failed' in line or 'error' in line:
                        print(f"   {line}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout[-1000:])  # Last 1000 chars
            if result.stderr:
                print("STDERR:")
                print(result.stderr[-1000:])  # Last 1000 chars
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (>{timeout}s)")
        return False
    except Exception as e:
        print(f"💥 {description} - ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run comprehensive analytics test suite")
    parser.add_argument("--quick", action="store_true", 
                       help="Run only quick tests (skip performance and load tests)")
    parser.add_argument("--performance", action="store_true",
                       help="Run only performance and load tests")
    parser.add_argument("--full", action="store_true",
                       help="Run complete test suite (default)")
    
    args = parser.parse_args()
    
    # Default to full suite if no specific option chosen
    if not (args.quick or args.performance):
        args.full = True
    
    print("🚀 Starting Comprehensive Analytics Test Suite")
    print(f"Test mode: {'Quick' if args.quick else 'Performance' if args.performance else 'Full'}")
    
    results = []
    
    if args.quick or args.full:
        # Quick tests - core functionality
        test_suites = [
            ("tests/test_analytics_comprehensive_final_suite.py::TestDataQualityScenarios", 
             "Data Quality Tests", 60),
            ("tests/test_analytics_comprehensive_final_suite.py::TestStatisticalAccuracy", 
             "Statistical Accuracy Tests", 60),
            ("tests/test_analytics_comprehensive_final_suite.py::TestUserInterfaceFeatures", 
             "User Interface Tests", 120),
        ]
        
        for pattern, description, timeout in test_suites:
            success = run_test_suite(pattern, description, timeout)
            results.append((description, success))
    
    if args.performance or args.full:
        # Performance tests - may take longer
        performance_suites = [
            ("tests/test_analytics_comprehensive_final_suite.py::TestLargeDatasetPerformance", 
             "Large Dataset Performance Tests", 300),
            ("tests/test_analytics_comprehensive_final_suite.py::TestConcurrentAnalyticsOperations", 
             "Concurrent Operations Load Testing", 600),
            ("tests/test_analytics_performance_benchmarks.py::TestAnalyticsPerformanceBenchmarks", 
             "Performance Benchmarks", 600),
        ]
        
        for pattern, description, timeout in performance_suites:
            success = run_test_suite(pattern, description, timeout)
            results.append((description, success))
    
    if args.full:
        # Integration tests - comprehensive workflows
        integration_suites = [
            ("tests/test_analytics_comprehensive_final_suite.py::TestEndToEndAnalyticsWorkflows", 
             "End-to-End Workflow Tests", 300),
            ("tests/test_analytics_integration_workflows.py::TestCompleteAnalyticsWorkflows", 
             "Integration Workflow Tests", 300),
            ("tests/test_analytics_integration_workflows.py::TestAnalyticsSystemResilience", 
             "System Resilience Tests", 180),
        ]
        
        for pattern, description, timeout in integration_suites:
            success = run_test_suite(pattern, description, timeout)
            results.append((description, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUITE SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:12} {description}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All test suites completed successfully!")
        return 0
    else:
        print("⚠️  Some test suites failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())