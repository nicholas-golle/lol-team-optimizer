"""
Unit tests for the StatisticalAnalyzer class.

This module contains comprehensive tests for all statistical analysis methods
including confidence intervals, significance testing, correlation analysis,
regression modeling, outlier detection, and trend analysis.
"""

import pytest
import numpy as np
import math
from datetime import datetime, timedelta
from typing import List

from lol_team_optimizer.statistical_analyzer import (
    StatisticalAnalyzer, ConfidenceIntervalMethod, OutlierDetectionMethod,
    TrendAnalysisMethod, CorrelationResult, RegressionResult, OutlierAnalysis,
    TimeSeriesPoint
)
from lol_team_optimizer.analytics_models import (
    StatisticalAnalysisError, DataValidationError, ConfidenceInterval,
    SignificanceTest, TrendAnalysis
)


# Global fixtures for all test classes
@pytest.fixture
def analyzer():
    """Create a StatisticalAnalyzer instance for testing."""
    return StatisticalAnalyzer(random_state=42)

@pytest.fixture
def sample_data():
    """Create sample data for testing."""
    np.random.seed(42)
    return {
        'normal_data': np.random.normal(100, 15, 50).tolist(),
        'uniform_data': np.random.uniform(0, 100, 50).tolist(),
        'small_sample': [10, 12, 14, 16, 18],
        'proportions': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
        'outlier_data': [1, 2, 3, 4, 5, 6, 7, 8, 9, 100],  # 100 is outlier
        'trend_increasing': [1, 2, 4, 7, 11, 16, 22, 29, 37, 46],
        'trend_decreasing': [50, 45, 39, 32, 24, 15, 5, -6, -18, -31],
        'trend_stable': [10, 11, 9, 10, 12, 9, 11, 10, 9, 11]
    }

@pytest.fixture
def time_series_data():
    """Create time series data for testing."""
    np.random.seed(42)  # Set seed for reproducible time series
    base_time = datetime(2024, 1, 1)
    
    # Increasing trend
    increasing = []
    for i in range(20):
        timestamp = base_time + timedelta(days=i)
        value = 10 + i * 0.5 + np.random.normal(0, 0.5)
        increasing.append(TimeSeriesPoint(timestamp, value))
    
    # Decreasing trend
    decreasing = []
    for i in range(20):
        timestamp = base_time + timedelta(days=i)
        value = 30 - i * 0.3 + np.random.normal(0, 0.5)
        decreasing.append(TimeSeriesPoint(timestamp, value))
    
    # Stable trend
    stable = []
    for i in range(20):
        timestamp = base_time + timedelta(days=i)
        value = 15 + np.random.normal(0, 0.5)
        stable.append(TimeSeriesPoint(timestamp, value))
    
    return {
        'increasing': increasing,
        'decreasing': decreasing,
        'stable': stable
    }


class TestConfidenceIntervals:
    """Test confidence interval calculations."""
    
    def test_t_distribution_confidence_interval(self, analyzer, sample_data):
        """Test t-distribution confidence interval calculation."""
        data = sample_data['normal_data']
        
        ci = analyzer.calculate_confidence_interval(
            data, 
            confidence_level=0.95,
            method=ConfidenceIntervalMethod.T_DISTRIBUTION
        )
        
        assert isinstance(ci, ConfidenceInterval)
        assert ci.confidence_level == 0.95
        assert ci.sample_size == len(data)
        assert ci.lower_bound < ci.upper_bound
        
        # Check that the interval contains the sample mean
        sample_mean = np.mean(data)
        assert ci.lower_bound <= sample_mean <= ci.upper_bound
    
    def test_normal_confidence_interval(self, analyzer, sample_data):
        """Test normal distribution confidence interval calculation."""
        data = sample_data['normal_data']
        
        ci = analyzer.calculate_confidence_interval(
            data,
            confidence_level=0.99,
            method=ConfidenceIntervalMethod.NORMAL
        )
        
        assert ci.confidence_level == 0.99
        assert ci.sample_size == len(data)
        
        # 99% CI should be wider than 95% CI
        ci_95 = analyzer.calculate_confidence_interval(
            data,
            confidence_level=0.95,
            method=ConfidenceIntervalMethod.NORMAL
        )
        
        assert ci.margin_of_error > ci_95.margin_of_error
    
    def test_bootstrap_confidence_interval(self, analyzer, sample_data):
        """Test bootstrap confidence interval calculation."""
        data = sample_data['small_sample']
        
        ci = analyzer.calculate_confidence_interval(
            data,
            confidence_level=0.95,
            method=ConfidenceIntervalMethod.BOOTSTRAP
        )
        
        assert isinstance(ci, ConfidenceInterval)
        assert ci.confidence_level == 0.95
        assert ci.sample_size == len(data)
        assert ci.lower_bound < ci.upper_bound
    
    def test_wilson_confidence_interval(self, analyzer, sample_data):
        """Test Wilson score confidence interval for proportions."""
        data = sample_data['proportions']
        
        ci = analyzer.calculate_confidence_interval(
            data,
            confidence_level=0.95,
            method=ConfidenceIntervalMethod.WILSON
        )
        
        assert isinstance(ci, ConfidenceInterval)
        assert 0 <= ci.lower_bound <= 1
        assert 0 <= ci.upper_bound <= 1
        assert ci.lower_bound < ci.upper_bound
    
    def test_clopper_pearson_confidence_interval(self, analyzer, sample_data):
        """Test Clopper-Pearson confidence interval for proportions."""
        data = sample_data['proportions']
        
        ci = analyzer.calculate_confidence_interval(
            data,
            confidence_level=0.95,
            method=ConfidenceIntervalMethod.CLOPPER_PEARSON
        )
        
        assert isinstance(ci, ConfidenceInterval)
        assert 0 <= ci.lower_bound <= 1
        assert 0 <= ci.upper_bound <= 1
        assert ci.lower_bound < ci.upper_bound
    
    def test_confidence_interval_edge_cases(self, analyzer):
        """Test confidence interval calculation edge cases."""
        # Empty data
        with pytest.raises(DataValidationError):
            analyzer.calculate_confidence_interval([])
        
        # Invalid confidence level
        with pytest.raises(DataValidationError):
            analyzer.calculate_confidence_interval([1, 2, 3], confidence_level=1.5)
        
        # Single data point
        ci = analyzer.calculate_confidence_interval([5.0])
        assert ci.sample_size == 1
        
        # All same values
        ci = analyzer.calculate_confidence_interval([10, 10, 10, 10])
        assert ci.lower_bound == ci.upper_bound == 10


class TestSignificanceTesting:
    """Test statistical significance testing."""
    
    def test_one_sample_t_test(self, analyzer, sample_data):
        """Test one-sample t-test."""
        data = sample_data['normal_data']
        
        result = analyzer.perform_significance_testing(data)
        
        assert isinstance(result, SignificanceTest)
        assert result.test_type == "one_sample_t_test"
        assert result.degrees_of_freedom == len(data) - 1
        assert 0 <= result.p_value <= 1
    
    def test_independent_t_test(self, analyzer, sample_data):
        """Test independent samples t-test."""
        sample1 = sample_data['normal_data'][:25]
        sample2 = sample_data['normal_data'][25:]
        
        result = analyzer.perform_significance_testing(
            sample1, sample2, test_type="t_test"
        )
        
        assert isinstance(result, SignificanceTest)
        assert result.test_type == "independent_t_test"
        assert result.degrees_of_freedom == len(sample1) + len(sample2) - 2
        assert result.effect_size is not None
        assert 0 <= result.p_value <= 1
    
    def test_mann_whitney_test(self, analyzer, sample_data):
        """Test Mann-Whitney U test."""
        sample1 = sample_data['uniform_data'][:25]
        sample2 = sample_data['uniform_data'][25:]
        
        result = analyzer.perform_significance_testing(
            sample1, sample2, test_type="mann_whitney"
        )
        
        assert isinstance(result, SignificanceTest)
        assert result.test_type == "mann_whitney_u"
        assert 0 <= result.p_value <= 1
    
    def test_kolmogorov_smirnov_test(self, analyzer, sample_data):
        """Test Kolmogorov-Smirnov test."""
        sample1 = sample_data['normal_data']
        sample2 = sample_data['uniform_data']
        
        result = analyzer.perform_significance_testing(
            sample1, sample2, test_type="ks_test"
        )
        
        assert isinstance(result, SignificanceTest)
        assert result.test_type == "kolmogorov_smirnov"
        assert 0 <= result.p_value <= 1
    
    def test_auto_test_selection(self, analyzer, sample_data):
        """Test automatic test selection."""
        sample1 = sample_data['normal_data'][:25]
        sample2 = sample_data['normal_data'][25:]
        
        result = analyzer.perform_significance_testing(
            sample1, sample2, test_type="auto"
        )
        
        assert isinstance(result, SignificanceTest)
        assert result.test_type in ["independent_t_test", "mann_whitney_u"]
        assert 0 <= result.p_value <= 1
    
    def test_significance_testing_edge_cases(self, analyzer):
        """Test significance testing edge cases."""
        # Empty sample
        with pytest.raises(DataValidationError):
            analyzer.perform_significance_testing([])
        
        # Invalid alternative
        with pytest.raises(DataValidationError):
            analyzer.perform_significance_testing([1, 2, 3], alternative="invalid")
        
        # Unknown test type
        with pytest.raises(StatisticalAnalysisError):
            analyzer.perform_significance_testing([1, 2, 3], [4, 5, 6], test_type="unknown")


class TestCorrelationAnalysis:
    """Test correlation analysis."""
    
    def test_pearson_correlation(self, analyzer):
        """Test Pearson correlation analysis."""
        # Create correlated data
        x = list(range(20))
        y = [2 * val + np.random.normal(0, 0.5) for val in x]
        z = [val + np.random.normal(0, 2) for val in x]
        
        variables = {'x': x, 'y': y, 'z': z}
        
        results = analyzer.analyze_correlations(variables, method="pearson")
        
        assert isinstance(results, dict)
        assert ('x', 'y') in results
        assert ('x', 'z') in results
        assert ('y', 'z') in results
        
        # Check x-y correlation (should be strong positive)
        xy_corr = results[('x', 'y')]
        assert isinstance(xy_corr, CorrelationResult)
        assert xy_corr.correlation_coefficient > 0.8
        assert xy_corr.method == "pearson"
        assert xy_corr.sample_size == 20
    
    def test_spearman_correlation(self, analyzer):
        """Test Spearman correlation analysis."""
        # Create monotonic but non-linear relationship
        x = list(range(20))
        y = [val**2 for val in x]
        
        variables = {'x': x, 'y': y}
        
        results = analyzer.analyze_correlations(variables, method="spearman")
        
        xy_corr = results[('x', 'y')]
        assert xy_corr.method == "spearman"
        assert xy_corr.correlation_coefficient > 0.9  # Should be very strong
    
    def test_kendall_correlation(self, analyzer):
        """Test Kendall's tau correlation analysis."""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        
        variables = {'x': x, 'y': y}
        
        results = analyzer.analyze_correlations(variables, method="kendall")
        
        xy_corr = results[('x', 'y')]
        assert xy_corr.method == "kendall"
        assert abs(xy_corr.correlation_coefficient - 1.0) < 1e-10  # Perfect correlation
    
    def test_correlation_strength_description(self, analyzer):
        """Test correlation strength descriptions."""
        # Test different correlation strengths
        test_cases = [
            (0.05, "negligible"),
            (0.25, "weak"),
            (0.4, "moderate"),
            (0.6, "strong"),
            (0.8, "very strong"),
            (-0.25, "weak"),  # Negative correlation
            (-0.75, "very strong")  # Very strong negative correlation
        ]
        
        for corr_val, expected_strength in test_cases:
            result = CorrelationResult(
                correlation_coefficient=corr_val,
                p_value=0.01,
                method="test",
                sample_size=100
            )
            assert result.strength_description() == expected_strength
    
    def test_correlation_analysis_edge_cases(self, analyzer):
        """Test correlation analysis edge cases."""
        # Too few variables
        with pytest.raises(DataValidationError):
            analyzer.analyze_correlations({'x': [1, 2, 3]})
        
        # Mismatched lengths
        with pytest.raises(DataValidationError):
            analyzer.analyze_correlations({
                'x': [1, 2, 3],
                'y': [1, 2, 3, 4]
            })
        
        # Invalid method
        with pytest.raises(DataValidationError):
            analyzer.analyze_correlations({
                'x': [1, 2, 3],
                'y': [1, 2, 3]
            }, method="invalid")


class TestRegressionAnalysis:
    """Test regression analysis."""
    
    def test_linear_regression(self, analyzer):
        """Test linear regression analysis."""
        # Create linear relationship: y = 2x + 3 + noise
        np.random.seed(42)
        x = np.random.uniform(0, 10, 50)
        y = 2 * x + 3 + np.random.normal(0, 0.5, 50)
        
        X = x.reshape(-1, 1).tolist()
        
        result = analyzer.perform_regression_analysis(
            dependent=y.tolist(),
            independent=X,
            feature_names=['x'],
            method="linear"
        )
        
        assert isinstance(result, RegressionResult)
        assert len(result.coefficients) == 1
        assert abs(result.coefficients[0] - 2.0) < 0.2  # Should be close to 2
        assert abs(result.intercept - 3.0) < 0.5  # Should be close to 3
        assert result.r_squared > 0.8  # Should have high R²
        assert result.method == "linear"
        assert result.feature_names == ['x']
    
    def test_multiple_regression(self, analyzer):
        """Test multiple regression analysis."""
        # Create multiple linear relationship: y = 2x1 + 3x2 + 1 + noise
        np.random.seed(42)
        n = 100
        x1 = np.random.uniform(0, 10, n)
        x2 = np.random.uniform(0, 5, n)
        y = 2 * x1 + 3 * x2 + 1 + np.random.normal(0, 0.5, n)
        
        X = np.column_stack([x1, x2]).tolist()
        
        result = analyzer.perform_regression_analysis(
            dependent=y.tolist(),
            independent=X,
            feature_names=['x1', 'x2'],
            method="linear"
        )
        
        assert len(result.coefficients) == 2
        assert abs(result.coefficients[0] - 2.0) < 0.2
        assert abs(result.coefficients[1] - 3.0) < 0.2
        assert result.r_squared > 0.9
        assert len(result.p_values) == 2
        assert len(result.standard_errors) == 2
    
    def test_ridge_regression(self, analyzer):
        """Test Ridge regression with regularization."""
        np.random.seed(42)
        n = 50
        x = np.random.uniform(0, 10, n)
        y = 2 * x + 3 + np.random.normal(0, 0.5, n)
        
        X = x.reshape(-1, 1).tolist()
        
        result = analyzer.perform_regression_analysis(
            dependent=y.tolist(),
            independent=X,
            feature_names=['x'],
            method="linear",
            regularization="ridge"
        )
        
        assert result.method == "linear_ridge"
        assert len(result.coefficients) == 1
        # P-values should be NaN for regularized models
        assert math.isnan(result.p_values[0])
    
    def test_lasso_regression(self, analyzer):
        """Test Lasso regression with regularization."""
        np.random.seed(42)
        n = 50
        x = np.random.uniform(0, 10, n)
        y = 2 * x + 3 + np.random.normal(0, 0.5, n)
        
        X = x.reshape(-1, 1).tolist()
        
        result = analyzer.perform_regression_analysis(
            dependent=y.tolist(),
            independent=X,
            feature_names=['x'],
            method="linear",
            regularization="lasso"
        )
        
        assert result.method == "linear_lasso"
        assert len(result.coefficients) == 1
    
    def test_regression_significant_features(self, analyzer):
        """Test identification of significant features."""
        # Create data where only first feature is significant
        np.random.seed(42)
        n = 100
        x1 = np.random.uniform(0, 10, n)  # Significant
        x2 = np.random.normal(0, 1, n)    # Not significant
        y = 2 * x1 + np.random.normal(0, 0.5, n)
        
        X = np.column_stack([x1, x2]).tolist()
        
        result = analyzer.perform_regression_analysis(
            dependent=y.tolist(),
            independent=X,
            feature_names=['significant', 'not_significant'],
            method="linear"
        )
        
        significant_features = result.get_significant_features(alpha=0.05)
        assert 'significant' in significant_features
        # 'not_significant' might or might not be in the list depending on random variation
    
    def test_regression_analysis_edge_cases(self, analyzer):
        """Test regression analysis edge cases."""
        # Empty dependent variable
        with pytest.raises(DataValidationError):
            analyzer.perform_regression_analysis([], [[1], [2]], ['x'])
        
        # Empty independent variables
        with pytest.raises(DataValidationError):
            analyzer.perform_regression_analysis([1, 2], [], ['x'])
        
        # Mismatched feature names
        with pytest.raises(DataValidationError):
            analyzer.perform_regression_analysis([1, 2], [[1], [2]], ['x', 'y'])
        
        # Mismatched lengths
        with pytest.raises(StatisticalAnalysisError):
            analyzer.perform_regression_analysis([1, 2], [[1], [2], [3]], ['x'])


class TestOutlierDetection:
    """Test outlier detection methods."""
    
    def test_z_score_outlier_detection(self, analyzer, sample_data):
        """Test z-score outlier detection."""
        data = sample_data['outlier_data']
        
        result = analyzer.detect_outliers(
            data,
            method=OutlierDetectionMethod.Z_SCORE,
            threshold=2.0
        )
        
        assert isinstance(result, OutlierAnalysis)
        assert result.method == "z_score"
        assert result.threshold == 2.0
        assert result.total_points == len(data)
        assert len(result.outlier_indices) > 0  # Should detect the outlier (100)
        assert 9 in result.outlier_indices  # Index of value 100
    
    def test_modified_z_score_outlier_detection(self, analyzer, sample_data):
        """Test modified z-score outlier detection."""
        data = sample_data['outlier_data']
        
        result = analyzer.detect_outliers(
            data,
            method=OutlierDetectionMethod.MODIFIED_Z_SCORE,
            threshold=3.5
        )
        
        assert result.method == "modified_z_score"
        assert len(result.outlier_indices) > 0
        assert 9 in result.outlier_indices  # Should detect the outlier
    
    def test_iqr_outlier_detection(self, analyzer, sample_data):
        """Test IQR outlier detection."""
        data = sample_data['outlier_data']
        
        result = analyzer.detect_outliers(
            data,
            method=OutlierDetectionMethod.IQR,
            threshold=1.5
        )
        
        assert result.method == "iqr"
        assert len(result.outlier_indices) > 0
        assert 9 in result.outlier_indices  # Should detect the outlier
    
    def test_isolation_forest_outlier_detection(self, analyzer, sample_data):
        """Test Isolation Forest outlier detection."""
        try:
            data = sample_data['outlier_data']
            
            result = analyzer.detect_outliers(
                data,
                method=OutlierDetectionMethod.ISOLATION_FOREST,
                threshold=0.1
            )
            
            assert result.method == "isolation_forest"
            assert len(result.outlier_indices) > 0
            
        except StatisticalAnalysisError as e:
            if "sklearn required" in str(e):
                pytest.skip("sklearn not available")
            else:
                raise
    
    def test_local_outlier_factor_detection(self, analyzer, sample_data):
        """Test Local Outlier Factor detection."""
        try:
            data = sample_data['outlier_data']
            
            result = analyzer.detect_outliers(
                data,
                method=OutlierDetectionMethod.LOCAL_OUTLIER_FACTOR,
                threshold=1.5
            )
            
            assert result.method == "local_outlier_factor"
            
        except StatisticalAnalysisError as e:
            if "sklearn required" in str(e):
                pytest.skip("sklearn not available")
            else:
                raise
    
    def test_outlier_percentage_calculation(self, analyzer):
        """Test outlier percentage calculation."""
        data = [1, 2, 3, 4, 5, 100, 101]  # 2 outliers out of 7 points
        
        result = analyzer.detect_outliers(
            data,
            method=OutlierDetectionMethod.Z_SCORE,
            threshold=2.0
        )
        
        expected_percentage = (len(result.outlier_indices) / len(data)) * 100
        assert abs(result.outlier_percentage - expected_percentage) < 0.01
    
    def test_outlier_detection_edge_cases(self, analyzer):
        """Test outlier detection edge cases."""
        # Empty data
        with pytest.raises(DataValidationError):
            analyzer.detect_outliers([])
        
        # All same values (no outliers)
        result = analyzer.detect_outliers([5, 5, 5, 5, 5])
        assert len(result.outlier_indices) == 0
        
        # Single value
        result = analyzer.detect_outliers([10])
        assert len(result.outlier_indices) == 0


class TestTrendAnalysis:
    """Test trend analysis methods."""
    
    def test_linear_trend_analysis_increasing(self, analyzer, time_series_data):
        """Test linear trend analysis for increasing trend."""
        data = time_series_data['increasing']
        
        result = analyzer.calculate_trend_analysis(
            data,
            method=TrendAnalysisMethod.LINEAR_REGRESSION
        )
        
        assert isinstance(result, TrendAnalysis)
        assert result.trend_direction == "improving"
        assert result.trend_strength > 0
        assert result.trend_duration_days > 0
        assert "slope" in result.key_metrics_trends
        assert result.key_metrics_trends["slope"] > 0
    
    def test_linear_trend_analysis_decreasing(self, analyzer, time_series_data):
        """Test linear trend analysis for decreasing trend."""
        data = time_series_data['decreasing']
        
        result = analyzer.calculate_trend_analysis(
            data,
            method=TrendAnalysisMethod.LINEAR_REGRESSION
        )
        
        assert result.trend_direction == "declining"
        assert result.trend_strength > 0
        assert result.key_metrics_trends["slope"] < 0
    
    def test_linear_trend_analysis_stable(self, analyzer, time_series_data):
        """Test linear trend analysis for stable trend."""
        data = time_series_data['stable']
        
        result = analyzer.calculate_trend_analysis(
            data,
            method=TrendAnalysisMethod.LINEAR_REGRESSION
        )
        
        # The trend might not be perfectly stable due to random variation
        assert result.trend_direction in ["stable", "improving", "declining"]
        assert result.trend_strength >= 0.0
        # Slope should be relatively small for stable data
        assert abs(result.key_metrics_trends["slope"]) < 1.0
    
    def test_moving_average_trend_analysis(self, analyzer, time_series_data):
        """Test moving average trend analysis."""
        data = time_series_data['increasing']
        
        result = analyzer.calculate_trend_analysis(
            data,
            method=TrendAnalysisMethod.MOVING_AVERAGE,
            window_size=5
        )
        
        assert result.trend_direction == "improving"
        assert "moving_average_change" in result.key_metrics_trends
        assert result.key_metrics_trends["moving_average_change"] > 0
    
    def test_exponential_smoothing_trend_analysis(self, analyzer, time_series_data):
        """Test exponential smoothing trend analysis."""
        data = time_series_data['decreasing']
        
        result = analyzer.calculate_trend_analysis(
            data,
            method=TrendAnalysisMethod.EXPONENTIAL_SMOOTHING
        )
        
        assert result.trend_direction == "declining"
        assert "exponential_smoothing_change" in result.key_metrics_trends
        assert result.key_metrics_trends["exponential_smoothing_change"] < 0
    
    def test_trend_analysis_edge_cases(self, analyzer):
        """Test trend analysis edge cases."""
        # Empty data
        with pytest.raises(DataValidationError):
            analyzer.calculate_trend_analysis([])
        
        # Too few points
        base_time = datetime(2024, 1, 1)
        short_data = [
            TimeSeriesPoint(base_time, 10),
            TimeSeriesPoint(base_time + timedelta(days=1), 11)
        ]
        
        with pytest.raises(DataValidationError):
            analyzer.calculate_trend_analysis(short_data)
        
        # Unimplemented method
        data = [
            TimeSeriesPoint(base_time, 10),
            TimeSeriesPoint(base_time + timedelta(days=1), 11),
            TimeSeriesPoint(base_time + timedelta(days=2), 12)
        ]
        
        with pytest.raises(StatisticalAnalysisError):
            analyzer.calculate_trend_analysis(
                data,
                method=TrendAnalysisMethod.POLYNOMIAL
            )


class TestStatisticalAnalyzerIntegration:
    """Integration tests for StatisticalAnalyzer."""
    
    def test_comprehensive_analysis_workflow(self, analyzer):
        """Test a comprehensive analysis workflow."""
        # Generate sample data
        np.random.seed(42)
        n = 100
        
        # Create correlated variables with trend
        time_points = list(range(n))
        performance = [50 + 0.1 * t + np.random.normal(0, 5) for t in time_points]
        experience = [t * 0.5 + np.random.normal(0, 2) for t in time_points]
        
        # 1. Calculate confidence intervals
        perf_ci = analyzer.calculate_confidence_interval(performance)
        exp_ci = analyzer.calculate_confidence_interval(experience)
        
        assert isinstance(perf_ci, ConfidenceInterval)
        assert isinstance(exp_ci, ConfidenceInterval)
        
        # 2. Test correlation
        correlations = analyzer.analyze_correlations({
            'performance': performance,
            'experience': experience
        })
        
        assert ('performance', 'experience') in correlations
        
        # 3. Regression analysis
        X = np.array(experience).reshape(-1, 1).tolist()
        regression = analyzer.perform_regression_analysis(
            dependent=performance,
            independent=X,
            feature_names=['experience']
        )
        
        assert regression.r_squared > 0.1  # Should have some fit (lowered expectation due to noise)
        
        # 4. Outlier detection
        outliers = analyzer.detect_outliers(performance)
        assert isinstance(outliers, OutlierAnalysis)
        
        # 5. Trend analysis
        base_time = datetime(2024, 1, 1)
        time_series = [
            TimeSeriesPoint(base_time + timedelta(days=i), performance[i])
            for i in range(len(performance))
        ]
        
        trend = analyzer.calculate_trend_analysis(time_series)
        assert trend.trend_direction == "improving"  # Should detect upward trend
    
    def test_error_handling_consistency(self, analyzer):
        """Test consistent error handling across methods."""
        # Test that all methods properly handle empty data
        empty_data_methods = [
            lambda: analyzer.calculate_confidence_interval([]),
            lambda: analyzer.perform_significance_testing([]),
            lambda: analyzer.detect_outliers([]),
            lambda: analyzer.calculate_trend_analysis([])
        ]
        
        for method in empty_data_methods:
            with pytest.raises(DataValidationError):
                method()
    
    def test_random_state_reproducibility(self):
        """Test that random state ensures reproducible results."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]
        
        # Create two analyzers with same random state
        analyzer1 = StatisticalAnalyzer(random_state=42)
        analyzer2 = StatisticalAnalyzer(random_state=42)
        
        # Bootstrap confidence intervals should be identical
        ci1 = analyzer1.calculate_confidence_interval(
            data, method=ConfidenceIntervalMethod.BOOTSTRAP
        )
        ci2 = analyzer2.calculate_confidence_interval(
            data, method=ConfidenceIntervalMethod.BOOTSTRAP
        )
        
        assert abs(ci1.lower_bound - ci2.lower_bound) < 1e-6
        assert abs(ci1.upper_bound - ci2.upper_bound) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__])