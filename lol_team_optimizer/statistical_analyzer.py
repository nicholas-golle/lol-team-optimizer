"""
Statistical Analyzer for advanced statistical operations.

This module provides comprehensive statistical analysis capabilities for the
League of Legends Team Optimizer, including confidence intervals, significance
testing, correlation analysis, outlier detection, and trend analysis.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau, chi2_contingency
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import warnings

from .analytics_models import (
    StatisticalAnalysisError, DataValidationError, ConfidenceInterval, 
    SignificanceTest, TrendAnalysis
)


class ConfidenceIntervalMethod(Enum):
    """Methods for calculating confidence intervals."""
    NORMAL = "normal"
    T_DISTRIBUTION = "t_distribution"
    BOOTSTRAP = "bootstrap"
    WILSON = "wilson"  # For proportions
    CLOPPER_PEARSON = "clopper_pearson"  # For proportions


class OutlierDetectionMethod(Enum):
    """Methods for outlier detection."""
    Z_SCORE = "z_score"
    MODIFIED_Z_SCORE = "modified_z_score"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"


class TrendAnalysisMethod(Enum):
    """Methods for trend analysis."""
    LINEAR_REGRESSION = "linear_regression"
    POLYNOMIAL = "polynomial"
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    correlation_coefficient: float
    p_value: float
    method: str
    sample_size: int
    
    def is_significant(self, alpha: float = 0.05) -> bool:
        """Check if correlation is statistically significant."""
        return self.p_value < alpha
    
    def strength_description(self) -> str:
        """Describe correlation strength."""
        abs_corr = abs(self.correlation_coefficient)
        if abs_corr < 0.1:
            return "negligible"
        elif abs_corr < 0.3:
            return "weak"
        elif abs_corr < 0.5:
            return "moderate"
        elif abs_corr < 0.7:
            return "strong"
        else:
            return "very strong"


@dataclass
class RegressionResult:
    """Result of regression analysis."""
    coefficients: List[float]
    intercept: float
    r_squared: float
    adjusted_r_squared: float
    p_values: List[float]
    standard_errors: List[float]
    residuals: List[float]
    predictions: List[float]
    method: str
    feature_names: List[str]
    
    def get_significant_features(self, alpha: float = 0.05) -> List[str]:
        """Get list of statistically significant features."""
        return [
            name for name, p_val in zip(self.feature_names, self.p_values)
            if p_val < alpha
        ]


@dataclass
class OutlierAnalysis:
    """Result of outlier detection analysis."""
    outlier_indices: List[int]
    outlier_scores: List[float]
    threshold: float
    method: str
    total_points: int
    
    @property
    def outlier_percentage(self) -> float:
        """Calculate percentage of outliers."""
        if self.total_points == 0:
            return 0.0
        return (len(self.outlier_indices) / self.total_points) * 100


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = None


class StatisticalAnalyzer:
    """Advanced statistical analysis for historical match data."""
    
    def __init__(self, random_state: int = 42):
        """
        Initialize the statistical analyzer.
        
        Args:
            random_state: Random seed for reproducible results
        """
        self.random_state = random_state
        np.random.seed(random_state)
        
        # Suppress sklearn warnings for cleaner output
        warnings.filterwarnings('ignore', category=UserWarning)
    
    def calculate_confidence_interval(
        self,
        data: List[float],
        confidence_level: float = 0.95,
        method: ConfidenceIntervalMethod = ConfidenceIntervalMethod.T_DISTRIBUTION
    ) -> ConfidenceInterval:
        """
        Calculate confidence interval for data using specified method.
        
        Args:
            data: List of numerical values
            confidence_level: Confidence level (0 < confidence_level < 1)
            method: Method to use for calculation
            
        Returns:
            ConfidenceInterval object
            
        Raises:
            StatisticalAnalysisError: If calculation fails
            DataValidationError: If input data is invalid
        """
        if not data:
            raise DataValidationError("Data cannot be empty")
        
        if not 0 < confidence_level < 1:
            raise DataValidationError("Confidence level must be between 0 and 1")
        
        try:
            data_array = np.array(data)
            n = len(data_array)
            mean = np.mean(data_array)
            
            if method == ConfidenceIntervalMethod.NORMAL:
                # Normal distribution (z-score)
                std_err = stats.sem(data_array)
                z_score = stats.norm.ppf((1 + confidence_level) / 2)
                margin_error = z_score * std_err
                
            elif method == ConfidenceIntervalMethod.T_DISTRIBUTION:
                # t-distribution (recommended for small samples)
                std_err = stats.sem(data_array)
                t_score = stats.t.ppf((1 + confidence_level) / 2, n - 1)
                margin_error = t_score * std_err
                
            elif method == ConfidenceIntervalMethod.BOOTSTRAP:
                # Bootstrap method
                return self._bootstrap_confidence_interval(data_array, confidence_level)
                
            elif method == ConfidenceIntervalMethod.WILSON:
                # Wilson score interval (for proportions)
                if not all(0 <= x <= 1 for x in data_array):
                    raise DataValidationError("Wilson method requires proportion data (0-1)")
                return self._wilson_confidence_interval(data_array, confidence_level)
                
            elif method == ConfidenceIntervalMethod.CLOPPER_PEARSON:
                # Clopper-Pearson interval (for proportions)
                if not all(0 <= x <= 1 for x in data_array):
                    raise DataValidationError("Clopper-Pearson method requires proportion data (0-1)")
                return self._clopper_pearson_confidence_interval(data_array, confidence_level)
            
            else:
                raise StatisticalAnalysisError(f"Unknown confidence interval method: {method}")
            
            lower_bound = mean - margin_error
            upper_bound = mean + margin_error
            
            return ConfidenceInterval(
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                confidence_level=confidence_level,
                sample_size=n
            )
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to calculate confidence interval: {str(e)}")
    
    def perform_significance_testing(
        self,
        sample1: List[float],
        sample2: Optional[List[float]] = None,
        test_type: str = "auto",
        alternative: str = "two-sided"
    ) -> SignificanceTest:
        """
        Perform statistical significance testing.
        
        Args:
            sample1: First sample data
            sample2: Second sample data (optional for one-sample tests)
            test_type: Type of test ("auto", "t_test", "mann_whitney", "chi_square", "ks_test")
            alternative: Alternative hypothesis ("two-sided", "less", "greater")
            
        Returns:
            SignificanceTest object
            
        Raises:
            StatisticalAnalysisError: If test fails
            DataValidationError: If input data is invalid
        """
        if not sample1:
            raise DataValidationError("Sample1 cannot be empty")
        
        valid_alternatives = ["two-sided", "less", "greater"]
        if alternative not in valid_alternatives:
            raise DataValidationError(f"Alternative must be one of: {valid_alternatives}")
        
        try:
            sample1_array = np.array(sample1)
            
            if sample2 is None:
                # One-sample tests
                if test_type == "auto" or test_type == "t_test":
                    # One-sample t-test against zero
                    statistic, p_value = stats.ttest_1samp(sample1_array, 0, alternative=alternative)
                    return SignificanceTest(
                        test_type="one_sample_t_test",
                        statistic=statistic,
                        p_value=p_value,
                        degrees_of_freedom=len(sample1_array) - 1
                    )
                else:
                    raise StatisticalAnalysisError(f"Test type {test_type} not supported for one sample")
            
            else:
                # Two-sample tests
                sample2_array = np.array(sample2)
                
                if test_type == "auto":
                    # Choose appropriate test based on data characteristics
                    test_type = self._choose_appropriate_test(sample1_array, sample2_array)
                
                if test_type == "t_test":
                    # Independent samples t-test
                    statistic, p_value = stats.ttest_ind(
                        sample1_array, sample2_array, alternative=alternative
                    )
                    df = len(sample1_array) + len(sample2_array) - 2
                    effect_size = self._calculate_cohens_d(sample1_array, sample2_array)
                    
                    return SignificanceTest(
                        test_type="independent_t_test",
                        statistic=statistic,
                        p_value=p_value,
                        degrees_of_freedom=df,
                        effect_size=effect_size
                    )
                
                elif test_type == "mann_whitney":
                    # Mann-Whitney U test (non-parametric)
                    statistic, p_value = stats.mannwhitneyu(
                        sample1_array, sample2_array, alternative=alternative
                    )
                    
                    return SignificanceTest(
                        test_type="mann_whitney_u",
                        statistic=statistic,
                        p_value=p_value
                    )
                
                elif test_type == "ks_test":
                    # Kolmogorov-Smirnov test
                    statistic, p_value = stats.ks_2samp(sample1_array, sample2_array)
                    
                    return SignificanceTest(
                        test_type="kolmogorov_smirnov",
                        statistic=statistic,
                        p_value=p_value
                    )
                
                elif test_type == "chi_square":
                    # Chi-square test (requires contingency table)
                    return self._perform_chi_square_test(sample1_array, sample2_array)
                
                else:
                    raise StatisticalAnalysisError(f"Unknown test type: {test_type}")
        
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to perform significance test: {str(e)}")
    
    def perform_one_sample_test(
        self,
        sample: List[float],
        expected_value: float,
        test_type: str = "t_test",
        alternative: str = "two-sided"
    ) -> SignificanceTest:
        """
        Perform one-sample statistical test against expected value.
        
        Args:
            sample: Sample data
            expected_value: Expected value to test against
            test_type: Type of test ("t_test", "wilcoxon")
            alternative: Alternative hypothesis ("two-sided", "less", "greater")
            
        Returns:
            SignificanceTest object
            
        Raises:
            StatisticalAnalysisError: If test fails
            DataValidationError: If input data is invalid
        """
        if not sample:
            raise DataValidationError("Sample cannot be empty")
        
        valid_alternatives = ["two-sided", "less", "greater"]
        if alternative not in valid_alternatives:
            raise DataValidationError(f"Alternative must be one of: {valid_alternatives}")
        
        try:
            sample_array = np.array(sample)
            
            if test_type == "t_test":
                # One-sample t-test
                statistic, p_value = stats.ttest_1samp(sample_array, expected_value, alternative=alternative)
                return SignificanceTest(
                    test_type="one_sample_t_test",
                    statistic=statistic,
                    p_value=p_value,
                    degrees_of_freedom=len(sample_array) - 1
                )
            
            elif test_type == "wilcoxon":
                # Wilcoxon signed-rank test (non-parametric)
                differences = sample_array - expected_value
                statistic, p_value = stats.wilcoxon(differences, alternative=alternative)
                return SignificanceTest(
                    test_type="wilcoxon_signed_rank",
                    statistic=statistic,
                    p_value=p_value
                )
            
            else:
                raise StatisticalAnalysisError(f"Unknown test type: {test_type}")
                
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to perform one-sample test: {str(e)}")
    
    def analyze_correlations(
        self,
        variables: Dict[str, List[float]],
        method: str = "pearson"
    ) -> Dict[Tuple[str, str], CorrelationResult]:
        """
        Analyze correlations between multiple variables.
        
        Args:
            variables: Dictionary of variable names to data lists
            method: Correlation method ("pearson", "spearman", "kendall")
            
        Returns:
            Dictionary of variable pairs to correlation results
            
        Raises:
            StatisticalAnalysisError: If analysis fails
            DataValidationError: If input data is invalid
        """
        if len(variables) < 2:
            raise DataValidationError("Need at least 2 variables for correlation analysis")
        
        valid_methods = ["pearson", "spearman", "kendall"]
        if method not in valid_methods:
            raise DataValidationError(f"Method must be one of: {valid_methods}")
        
        # Validate all variables have same length
        lengths = [len(data) for data in variables.values()]
        if len(set(lengths)) > 1:
            raise DataValidationError("All variables must have the same length")
        
        try:
            results = {}
            var_names = list(variables.keys())
            
            for i in range(len(var_names)):
                for j in range(i + 1, len(var_names)):
                    var1, var2 = var_names[i], var_names[j]
                    data1, data2 = variables[var1], variables[var2]
                    
                    if method == "pearson":
                        corr, p_value = pearsonr(data1, data2)
                    elif method == "spearman":
                        corr, p_value = spearmanr(data1, data2)
                    elif method == "kendall":
                        corr, p_value = kendalltau(data1, data2)
                    
                    results[(var1, var2)] = CorrelationResult(
                        correlation_coefficient=corr,
                        p_value=p_value,
                        method=method,
                        sample_size=len(data1)
                    )
            
            return results
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to analyze correlations: {str(e)}")
    
    def perform_regression_analysis(
        self,
        dependent: List[float],
        independent: List[List[float]],
        feature_names: List[str],
        method: str = "linear",
        regularization: Optional[str] = None
    ) -> RegressionResult:
        """
        Perform regression analysis.
        
        Args:
            dependent: Dependent variable values
            independent: Independent variable values (features)
            feature_names: Names of features
            method: Regression method ("linear", "polynomial")
            regularization: Regularization type ("ridge", "lasso", None)
            
        Returns:
            RegressionResult object
            
        Raises:
            StatisticalAnalysisError: If analysis fails
            DataValidationError: If input data is invalid
        """
        if not dependent:
            raise DataValidationError("Dependent variable cannot be empty")
        
        if not independent:
            raise DataValidationError("Independent variables cannot be empty")
        
        if len(feature_names) != len(independent[0]):
            raise DataValidationError("Number of feature names must match number of features")
        
        try:
            X = np.array(independent)
            y = np.array(dependent)
            
            if len(X) != len(y):
                raise DataValidationError("Independent and dependent variables must have same length")
            
            # Choose regression model
            if regularization == "ridge":
                model = Ridge(random_state=self.random_state)
            elif regularization == "lasso":
                model = Lasso(random_state=self.random_state)
            else:
                model = LinearRegression()
            
            # Fit model
            model.fit(X, y)
            
            # Make predictions
            predictions = model.predict(X)
            residuals = y - predictions
            
            # Calculate R-squared
            r_squared = r2_score(y, predictions)
            
            # Calculate adjusted R-squared
            n = len(y)
            p = X.shape[1]
            adjusted_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - p - 1)
            
            # Calculate p-values and standard errors (for linear regression only)
            if regularization is None:
                p_values, std_errors = self._calculate_regression_statistics(X, y, model)
            else:
                # Regularized models don't have standard p-values
                p_values = [np.nan] * len(feature_names)
                std_errors = [np.nan] * len(feature_names)
            
            return RegressionResult(
                coefficients=model.coef_.tolist(),
                intercept=model.intercept_,
                r_squared=r_squared,
                adjusted_r_squared=adjusted_r_squared,
                p_values=p_values,
                standard_errors=std_errors,
                residuals=residuals.tolist(),
                predictions=predictions.tolist(),
                method=f"{method}_{regularization}" if regularization else method,
                feature_names=feature_names
            )
            
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to perform regression analysis: {str(e)}")
    
    def detect_outliers(
        self,
        data: List[float],
        method: OutlierDetectionMethod = OutlierDetectionMethod.MODIFIED_Z_SCORE,
        threshold: Optional[float] = None
    ) -> OutlierAnalysis:
        """
        Detect outliers in data using specified method.
        
        Args:
            data: List of numerical values
            method: Outlier detection method
            threshold: Custom threshold (method-specific)
            
        Returns:
            OutlierAnalysis object
            
        Raises:
            StatisticalAnalysisError: If detection fails
            DataValidationError: If input data is invalid
        """
        if not data:
            raise DataValidationError("Data cannot be empty")
        
        try:
            data_array = np.array(data)
            
            if method == OutlierDetectionMethod.Z_SCORE:
                return self._detect_outliers_z_score(data_array, threshold or 3.0)
            
            elif method == OutlierDetectionMethod.MODIFIED_Z_SCORE:
                return self._detect_outliers_modified_z_score(data_array, threshold or 3.5)
            
            elif method == OutlierDetectionMethod.IQR:
                return self._detect_outliers_iqr(data_array, threshold or 1.5)
            
            elif method == OutlierDetectionMethod.ISOLATION_FOREST:
                return self._detect_outliers_isolation_forest(data_array, threshold or 0.1)
            
            elif method == OutlierDetectionMethod.LOCAL_OUTLIER_FACTOR:
                return self._detect_outliers_lof(data_array, threshold or 1.5)
            
            else:
                raise StatisticalAnalysisError(f"Unknown outlier detection method: {method}")
                
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to detect outliers: {str(e)}")
    
    def calculate_trend_analysis(
        self,
        time_series: List[TimeSeriesPoint],
        method: TrendAnalysisMethod = TrendAnalysisMethod.LINEAR_REGRESSION,
        window_size: Optional[int] = None
    ) -> TrendAnalysis:
        """
        Analyze trends in time series data.
        
        Args:
            time_series: List of time series points
            method: Trend analysis method
            window_size: Window size for moving average methods
            
        Returns:
            TrendAnalysis object
            
        Raises:
            StatisticalAnalysisError: If analysis fails
            DataValidationError: If input data is invalid
        """
        if not time_series:
            raise DataValidationError("Time series cannot be empty")
        
        if len(time_series) < 3:
            raise DataValidationError("Need at least 3 points for trend analysis")
        
        try:
            # Sort by timestamp
            sorted_series = sorted(time_series, key=lambda x: x.timestamp)
            
            timestamps = [point.timestamp for point in sorted_series]
            values = [point.value for point in sorted_series]
            
            # Convert timestamps to numeric values (days since first timestamp)
            start_time = timestamps[0]
            numeric_times = [(ts - start_time).total_seconds() / 86400 for ts in timestamps]
            
            if method == TrendAnalysisMethod.LINEAR_REGRESSION:
                return self._analyze_linear_trend(numeric_times, values, timestamps)
            
            elif method == TrendAnalysisMethod.MOVING_AVERAGE:
                window = window_size or max(3, len(values) // 10)
                return self._analyze_moving_average_trend(numeric_times, values, timestamps, window)
            
            elif method == TrendAnalysisMethod.EXPONENTIAL_SMOOTHING:
                return self._analyze_exponential_smoothing_trend(numeric_times, values, timestamps)
            
            else:
                raise StatisticalAnalysisError(f"Trend analysis method {method} not implemented")
                
        except Exception as e:
            raise StatisticalAnalysisError(f"Failed to analyze trend: {str(e)}")
    
    # Private helper methods
    
    def _bootstrap_confidence_interval(
        self,
        data: np.ndarray,
        confidence_level: float,
        n_bootstrap: int = 1000
    ) -> ConfidenceInterval:
        """Calculate confidence interval using bootstrap method."""
        # Set random state for reproducible results
        rng = np.random.RandomState(self.random_state)
        bootstrap_means = []
        n = len(data)
        
        for _ in range(n_bootstrap):
            bootstrap_sample = rng.choice(data, size=n, replace=True)
            bootstrap_means.append(np.mean(bootstrap_sample))
        
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = np.percentile(bootstrap_means, lower_percentile)
        upper_bound = np.percentile(bootstrap_means, upper_percentile)
        
        return ConfidenceInterval(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            sample_size=n
        )
    
    def _wilson_confidence_interval(
        self,
        data: np.ndarray,
        confidence_level: float
    ) -> ConfidenceInterval:
        """Calculate Wilson score confidence interval for proportions."""
        n = len(data)
        p = np.mean(data)
        z = stats.norm.ppf((1 + confidence_level) / 2)
        
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
        
        return ConfidenceInterval(
            lower_bound=max(0, center - margin),
            upper_bound=min(1, center + margin),
            confidence_level=confidence_level,
            sample_size=n
        )
    
    def _clopper_pearson_confidence_interval(
        self,
        data: np.ndarray,
        confidence_level: float
    ) -> ConfidenceInterval:
        """Calculate Clopper-Pearson confidence interval for proportions."""
        n = len(data)
        successes = int(np.sum(data))
        alpha = 1 - confidence_level
        
        if successes == 0:
            lower_bound = 0
        else:
            lower_bound = stats.beta.ppf(alpha / 2, successes, n - successes + 1)
        
        if successes == n:
            upper_bound = 1
        else:
            upper_bound = stats.beta.ppf(1 - alpha / 2, successes + 1, n - successes)
        
        return ConfidenceInterval(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence_level=confidence_level,
            sample_size=n
        )
    
    def _choose_appropriate_test(self, sample1: np.ndarray, sample2: np.ndarray) -> str:
        """Choose appropriate statistical test based on data characteristics."""
        # Check for normality using Shapiro-Wilk test
        _, p1 = stats.shapiro(sample1)
        _, p2 = stats.shapiro(sample2)
        
        # If both samples appear normal, use t-test
        if p1 > 0.05 and p2 > 0.05:
            return "t_test"
        else:
            # Use non-parametric test
            return "mann_whitney"
    
    def _calculate_cohens_d(self, sample1: np.ndarray, sample2: np.ndarray) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(sample1), len(sample2)
        var1, var2 = np.var(sample1, ddof=1), np.var(sample2, ddof=1)
        
        # Pooled standard deviation
        pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        return (np.mean(sample1) - np.mean(sample2)) / pooled_std
    
    def _perform_chi_square_test(self, sample1: np.ndarray, sample2: np.ndarray) -> SignificanceTest:
        """Perform chi-square test of independence."""
        # Create contingency table
        # This is a simplified version - in practice, you'd need categorical data
        contingency_table = np.array([[len(sample1), len(sample2)], 
                                     [np.sum(sample1), np.sum(sample2)]])
        
        chi2, p_value, dof, expected = chi2_contingency(contingency_table)
        
        return SignificanceTest(
            test_type="chi_square",
            statistic=chi2,
            p_value=p_value,
            degrees_of_freedom=dof
        )
    
    def _calculate_regression_statistics(
        self,
        X: np.ndarray,
        y: np.ndarray,
        model: LinearRegression
    ) -> Tuple[List[float], List[float]]:
        """Calculate p-values and standard errors for linear regression."""
        n = len(y)
        p = X.shape[1]
        
        # Calculate residual sum of squares
        predictions = model.predict(X)
        residuals = y - predictions
        rss = np.sum(residuals**2)
        
        # Calculate standard errors
        mse = rss / (n - p - 1)
        var_coef = mse * np.linalg.inv(X.T @ X).diagonal()
        std_errors = np.sqrt(var_coef)
        
        # Calculate t-statistics and p-values
        t_stats = model.coef_ / std_errors
        p_values = [2 * (1 - stats.t.cdf(abs(t), n - p - 1)) for t in t_stats]
        
        return p_values, std_errors.tolist()
    
    def _detect_outliers_z_score(self, data: np.ndarray, threshold: float) -> OutlierAnalysis:
        """Detect outliers using z-score method."""
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return OutlierAnalysis([], [], threshold, "z_score", len(data))
        
        z_scores = np.abs((data - mean) / std)
        outlier_indices = np.where(z_scores > threshold)[0].tolist()
        outlier_scores = z_scores[outlier_indices].tolist()
        
        return OutlierAnalysis(
            outlier_indices=outlier_indices,
            outlier_scores=outlier_scores,
            threshold=threshold,
            method="z_score",
            total_points=len(data)
        )
    
    def _detect_outliers_modified_z_score(self, data: np.ndarray, threshold: float) -> OutlierAnalysis:
        """Detect outliers using modified z-score method (median-based)."""
        median = np.median(data)
        mad = np.median(np.abs(data - median))
        
        if mad == 0:
            return OutlierAnalysis([], [], threshold, "modified_z_score", len(data))
        
        modified_z_scores = 0.6745 * (data - median) / mad
        outlier_indices = np.where(np.abs(modified_z_scores) > threshold)[0].tolist()
        outlier_scores = np.abs(modified_z_scores)[outlier_indices].tolist()
        
        return OutlierAnalysis(
            outlier_indices=outlier_indices,
            outlier_scores=outlier_scores,
            threshold=threshold,
            method="modified_z_score",
            total_points=len(data)
        )
    
    def _detect_outliers_iqr(self, data: np.ndarray, threshold: float) -> OutlierAnalysis:
        """Detect outliers using IQR method."""
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        outlier_mask = (data < lower_bound) | (data > upper_bound)
        outlier_indices = np.where(outlier_mask)[0].tolist()
        
        # Calculate outlier scores as distance from bounds
        outlier_scores = []
        for idx in outlier_indices:
            value = data[idx]
            if value < lower_bound:
                score = (lower_bound - value) / iqr
            else:
                score = (value - upper_bound) / iqr
            outlier_scores.append(score)
        
        return OutlierAnalysis(
            outlier_indices=outlier_indices,
            outlier_scores=outlier_scores,
            threshold=threshold,
            method="iqr",
            total_points=len(data)
        )
    
    def _detect_outliers_isolation_forest(self, data: np.ndarray, contamination: float) -> OutlierAnalysis:
        """Detect outliers using Isolation Forest."""
        try:
            from sklearn.ensemble import IsolationForest
            
            # Reshape data for sklearn
            X = data.reshape(-1, 1)
            
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=self.random_state
            )
            outlier_labels = iso_forest.fit_predict(X)
            outlier_scores = iso_forest.decision_function(X)
            
            outlier_indices = np.where(outlier_labels == -1)[0].tolist()
            outlier_score_values = (-outlier_scores[outlier_indices]).tolist()
            
            return OutlierAnalysis(
                outlier_indices=outlier_indices,
                outlier_scores=outlier_score_values,
                threshold=contamination,
                method="isolation_forest",
                total_points=len(data)
            )
            
        except ImportError:
            raise StatisticalAnalysisError("sklearn required for Isolation Forest")
    
    def _detect_outliers_lof(self, data: np.ndarray, threshold: float) -> OutlierAnalysis:
        """Detect outliers using Local Outlier Factor."""
        try:
            from sklearn.neighbors import LocalOutlierFactor
            
            # Reshape data for sklearn
            X = data.reshape(-1, 1)
            
            lof = LocalOutlierFactor(n_neighbors=min(20, len(data) - 1))
            outlier_labels = lof.fit_predict(X)
            outlier_scores = -lof.negative_outlier_factor_
            
            outlier_indices = np.where(outlier_scores > threshold)[0].tolist()
            outlier_score_values = outlier_scores[outlier_indices].tolist()
            
            return OutlierAnalysis(
                outlier_indices=outlier_indices,
                outlier_scores=outlier_score_values,
                threshold=threshold,
                method="local_outlier_factor",
                total_points=len(data)
            )
            
        except ImportError:
            raise StatisticalAnalysisError("sklearn required for Local Outlier Factor")
    
    def _analyze_linear_trend(
        self,
        numeric_times: List[float],
        values: List[float],
        timestamps: List[datetime]
    ) -> TrendAnalysis:
        """Analyze trend using linear regression."""
        X = np.array(numeric_times).reshape(-1, 1)
        y = np.array(values)
        
        model = LinearRegression()
        model.fit(X, y)
        
        slope = model.coef_[0]
        
        # Determine trend direction and strength
        if abs(slope) < 0.01:
            direction = "stable"
            strength = 0.0
        elif slope > 0:
            direction = "improving"
            strength = min(1.0, abs(slope) / np.std(values))
        else:
            direction = "declining"
            strength = min(1.0, abs(slope) / np.std(values))
        
        duration_days = int(max(numeric_times) - min(numeric_times))
        
        return TrendAnalysis(
            trend_direction=direction,
            trend_strength=strength,
            trend_duration_days=duration_days,
            key_metrics_trends={"slope": slope},
            inflection_points=[],
            seasonal_patterns={}
        )
    
    def _analyze_moving_average_trend(
        self,
        numeric_times: List[float],
        values: List[float],
        timestamps: List[datetime],
        window: int
    ) -> TrendAnalysis:
        """Analyze trend using moving average."""
        values_array = np.array(values)
        
        # Calculate moving average
        moving_avg = []
        for i in range(len(values_array)):
            start_idx = max(0, i - window + 1)
            end_idx = i + 1
            moving_avg.append(np.mean(values_array[start_idx:end_idx]))
        
        # Calculate trend from moving average
        first_half = np.mean(moving_avg[:len(moving_avg)//2])
        second_half = np.mean(moving_avg[len(moving_avg)//2:])
        
        trend_change = second_half - first_half
        
        if abs(trend_change) < 0.01 * np.std(values):
            direction = "stable"
            strength = 0.0
        elif trend_change > 0:
            direction = "improving"
            strength = min(1.0, abs(trend_change) / np.std(values))
        else:
            direction = "declining"
            strength = min(1.0, abs(trend_change) / np.std(values))
        
        duration_days = int(max(numeric_times) - min(numeric_times))
        
        return TrendAnalysis(
            trend_direction=direction,
            trend_strength=strength,
            trend_duration_days=duration_days,
            key_metrics_trends={"moving_average_change": trend_change},
            inflection_points=[],
            seasonal_patterns={}
        )
    
    def _analyze_exponential_smoothing_trend(
        self,
        numeric_times: List[float],
        values: List[float],
        timestamps: List[datetime]
    ) -> TrendAnalysis:
        """Analyze trend using exponential smoothing."""
        alpha = 0.3  # Smoothing parameter
        values_array = np.array(values)
        
        # Calculate exponentially smoothed values
        smoothed = [values_array[0]]
        for i in range(1, len(values_array)):
            smoothed_value = alpha * values_array[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(smoothed_value)
        
        # Calculate trend from smoothed values
        trend_change = smoothed[-1] - smoothed[0]
        
        if abs(trend_change) < 0.01 * np.std(values):
            direction = "stable"
            strength = 0.0
        elif trend_change > 0:
            direction = "improving"
            strength = min(1.0, abs(trend_change) / np.std(values))
        else:
            direction = "declining"
            strength = min(1.0, abs(trend_change) / np.std(values))
        
        duration_days = int(max(numeric_times) - min(numeric_times))
        
        return TrendAnalysis(
            trend_direction=direction,
            trend_strength=strength,
            trend_duration_days=duration_days,
            key_metrics_trends={"exponential_smoothing_change": trend_change},
            inflection_points=[],
            seasonal_patterns={}
        ) 
   
    def _find_inflection_points(
        self,
        numeric_times: List[float],
        values: List[float],
        timestamps: List[datetime]
    ) -> List[datetime]:
        """Find inflection points in the time series."""
        if len(values) < 5:
            return []
        
        inflection_points = []
        
        # Look for points where the trend changes significantly
        window_size = max(3, len(values) // 10)
        
        for i in range(window_size, len(values) - window_size):
            # Calculate slopes before and after this point
            before_x = numeric_times[i - window_size:i]
            before_y = values[i - window_size:i]
            after_x = numeric_times[i:i + window_size]
            after_y = values[i:i + window_size]
            
            if len(before_x) >= 2 and len(after_x) >= 2:
                # Simple slope calculation
                before_slope = (before_y[-1] - before_y[0]) / (before_x[-1] - before_x[0]) if before_x[-1] != before_x[0] else 0
                after_slope = (after_y[-1] - after_y[0]) / (after_x[-1] - after_x[0]) if after_x[-1] != after_x[0] else 0
                
                # Check for significant slope change
                slope_change = abs(after_slope - before_slope)
                if slope_change > 0.1:  # Threshold for significant change
                    inflection_points.append(timestamps[i])
        
        return inflection_points
    
    def _detect_simple_seasonal_patterns(
        self,
        timestamps: List[datetime],
        values: List[float]
    ) -> Dict[str, float]:
        """Detect simple seasonal patterns in the data."""
        if len(timestamps) < 30:  # Need sufficient data
            return {}
        
        # Group by month and calculate averages
        monthly_data = {}
        for timestamp, value in zip(timestamps, values):
            month = timestamp.month
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(value)
        
        monthly_averages = {}
        for month, month_values in monthly_data.items():
            if len(month_values) >= 3:  # Need sufficient data per month
                monthly_averages[f"month_{month}"] = statistics.mean(month_values)
        
        return monthly_averages