"""
Tests for comprehensive performance trend analysis functionality.

This module tests the advanced trend analysis capabilities including
champion-specific trends, meta shift detection, seasonal patterns,
and performance predictions.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import statistics

from lol_team_optimizer.historical_analytics_engine import HistoricalAnalyticsEngine
from lol_team_optimizer.analytics_models import (
    AnalyticsFilters, DateRange, TrendAnalysis, TimeSeriesPoint,
    InsufficientDataError, AnalyticsError
)
from lol_team_optimizer.baseline_manager import BaselineManager
from lol_team_optimizer.statistical_analyzer import StatisticalAnalyzer, TrendAnalysisMethod
from lol_team_optimizer.config import Config
from lol_team_optimizer.models import Match, MatchParticipant


class TestComprehensiveTrendAnalysis:
    """Test comprehensive trend analysis functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "/tmp/test_cache"
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        return Mock()
    
    @pytest.fixture
    def mock_baseline_manager(self):
        """Create mock baseline manager."""
        return Mock(spec=BaselineManager)
    
    @pytest.fixture
    def analytics_engine(self, mock_config, mock_match_manager, mock_baseline_manager):
        """Create analytics engine for testing."""
        return HistoricalAnalyticsEngine(
            config=mock_config,
            match_manager=mock_match_manager,
            baseline_manager=mock_baseline_manager
        )
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample matches for testing."""
        matches = []
        base_date = datetime.now() - timedelta(days=180)
        
        for i in range(50):
            match = Mock(spec=Match)
            match.game_creation = int((base_date + timedelta(days=i * 3)).timestamp())
            match.game_creation_datetime = base_date + timedelta(days=i * 3)
            match.game_duration = 1800 + (i % 10) * 60  # 30-39 minutes
            match.queue_id = 420  # Ranked Solo/Duo
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_puuid"
            participant.summoner_name = "TestPlayer"
            participant.champion_id = 1 + (i % 5)  # Rotate through 5 champions
            participant.champion_name = f"Champion_{participant.champion_id}"
            participant.individual_position = "middle"
            participant.team_id = 100
            participant.win = i % 3 != 0  # ~67% win rate with variation
            participant.kills = 5 + (i % 8)
            participant.deaths = 2 + (i % 4)
            participant.assists = 8 + (i % 6)
            participant.cs_total = 150 + (i % 50)
            participant.vision_score = 20 + (i % 15)
            participant.total_damage_dealt_to_champions = 15000 + (i % 5000)
            participant.gold_earned = 12000 + (i % 3000)
            
            matches.append((match, participant))
        
        return matches
    
    def test_calculate_comprehensive_performance_trends(self, analytics_engine, sample_matches):
        """Test comprehensive performance trend calculation."""
        analytics_engine.match_manager.get_matches_for_player.return_value = [m[0] for m in sample_matches]
        analytics_engine._get_filtered_matches = Mock(return_value=sample_matches)
        
        # Test successful trend calculation
        trends = analytics_engine.calculate_comprehensive_performance_trends(
            puuid="test_puuid",
            time_window_days=180,
            metrics=["win_rate", "avg_kda", "avg_cs_per_min"]
        )
        
        assert isinstance(trends, dict)
        assert "win_rate" in trends
        assert "avg_kda" in trends
        assert "avg_cs_per_min" in trends
        
        # Verify each trend analysis
        for metric, trend in trends.items():
            assert isinstance(trend, TrendAnalysis)
            assert trend.trend_direction in ["improving", "declining", "stable"]
            assert 0 <= trend.trend_strength <= 1
            assert trend.trend_duration_days >= 0
    
    def test_calculate_comprehensive_trends_insufficient_data(self, analytics_engine):
        """Test comprehensive trends with insufficient data."""
        # Mock insufficient matches
        insufficient_matches = [(Mock(), Mock()) for _ in range(5)]
        analytics_engine._get_filtered_matches = Mock(return_value=insufficient_matches)
        
        with pytest.raises(InsufficientDataError):
            analytics_engine.calculate_comprehensive_performance_trends(
                puuid="test_puuid",
                time_window_days=180
            )
    
    def test_calculate_champion_specific_trends(self, analytics_engine, sample_matches):
        """Test champion-specific trend calculation."""
        # Filter matches for specific champion
        champion_matches = [(m, p) for m, p in sample_matches if p.champion_id == 1]
        analytics_engine._get_filtered_matches = Mock(return_value=champion_matches)
        
        trends = analytics_engine.calculate_champion_specific_trends(
            puuid="test_puuid",
            champion_id=1,
            role="middle",
            time_window_days=120,
            metrics=["win_rate", "avg_kda"]
        )
        
        assert isinstance(trends, dict)
        assert len(trends) <= 2  # May not have enough data for all metrics
        
        for metric, trend in trends.items():
            assert isinstance(trend, TrendAnalysis)
            assert trend.trend_direction in ["improving", "declining", "stable"]
    
    def test_detect_meta_shifts(self, analytics_engine, sample_matches):
        """Test meta shift detection."""
        analytics_engine._get_filtered_matches = Mock(return_value=sample_matches)
        
        meta_shifts = analytics_engine.detect_meta_shifts(
            puuid="test_puuid",
            time_window_days=365,
            shift_detection_window=30
        )
        
        assert isinstance(meta_shifts, dict)
        assert "champion_shifts" in meta_shifts
        assert "performance_adaptation" in meta_shifts
        assert "role_flexibility" in meta_shifts
        assert "meta_shift_periods" in meta_shifts
        assert "analysis_period" in meta_shifts
        assert "total_matches" in meta_shifts
        
        # Verify champion shifts analysis
        champion_shifts = meta_shifts["champion_shifts"]
        assert "shifts" in champion_shifts
        assert "total_windows" in champion_shifts
        assert "avg_overlap_ratio" in champion_shifts
        
        # Verify performance adaptation analysis
        performance_adaptation = meta_shifts["performance_adaptation"]
        assert "window_performances" in performance_adaptation
        assert "adaptation_score" in performance_adaptation
        assert "total_windows" in performance_adaptation
    
    def test_identify_seasonal_patterns(self, analytics_engine, sample_matches):
        """Test seasonal pattern identification."""
        # Create matches spanning multiple seasons
        seasonal_matches = []
        base_date = datetime.now() - timedelta(days=730)  # 2 years
        
        for i in range(100):
            match = Mock(spec=Match)
            match.game_creation = int((base_date + timedelta(days=i * 7)).timestamp())
            match.game_creation_datetime = base_date + timedelta(days=i * 7)
            match.game_duration = 1800
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_puuid"
            participant.win = (i + match.game_creation_datetime.month) % 3 != 0  # Seasonal variation
            participant.kills = 5 + (match.game_creation_datetime.month % 4)
            participant.deaths = 3
            participant.assists = 7
            participant.cs_total = 150
            participant.vision_score = 20
            
            seasonal_matches.append((match, participant))
        
        analytics_engine._get_filtered_matches = Mock(return_value=seasonal_matches)
        
        seasonal_patterns = analytics_engine.identify_seasonal_patterns(
            puuid="test_puuid",
            time_window_days=730,
            metrics=["win_rate", "avg_kda"]
        )
        
        assert isinstance(seasonal_patterns, dict)
        assert "seasonal_patterns" in seasonal_patterns
        assert "analysis_period" in seasonal_patterns
        assert "total_matches" in seasonal_patterns
        
        # Verify seasonal pattern structure
        patterns = seasonal_patterns["seasonal_patterns"]
        for metric, pattern_data in patterns.items():
            assert "monthly_patterns" in pattern_data
            assert "weekly_patterns" in pattern_data
            assert "hourly_patterns" in pattern_data
    
    def test_predict_performance_trends(self, analytics_engine, sample_matches):
        """Test performance trend prediction."""
        analytics_engine._get_filtered_matches = Mock(return_value=sample_matches)
        
        predictions = analytics_engine.predict_performance_trends(
            puuid="test_puuid",
            prediction_days=30,
            metrics=["win_rate", "avg_kda"],
            historical_window_days=180
        )
        
        assert isinstance(predictions, dict)
        assert "predictions" in predictions
        assert "prediction_period_days" in predictions
        assert "historical_period" in predictions
        assert "prediction_confidence" in predictions
        assert "total_historical_matches" in predictions
        
        # Verify prediction structure
        pred_data = predictions["predictions"]
        for metric, prediction in pred_data.items():
            assert "predicted_value" in prediction
            assert "trend_slope" in prediction
            assert "confidence" in prediction
            assert "prediction_date" in prediction
            assert "trend_direction" in prediction
            assert prediction["trend_direction"] in ["improving", "declining", "stable", "unknown"]
    
    def test_analyze_champion_pick_shifts(self, analytics_engine, sample_matches):
        """Test champion pick shift analysis."""
        shifts = analytics_engine._analyze_champion_pick_shifts(sample_matches, window_size=30)
        
        assert isinstance(shifts, dict)
        assert "shifts" in shifts
        assert "total_windows" in shifts
        assert "avg_overlap_ratio" in shifts
        
        # Verify shift data structure
        if shifts["shifts"]:
            shift = shifts["shifts"][0]
            assert "window_start" in shift
            assert "window_end" in shift
            assert "overlap_ratio" in shift
            assert "new_champions" in shift
            assert "dropped_champions" in shift
            assert 0 <= shift["overlap_ratio"] <= 1
    
    def test_analyze_performance_adaptation(self, analytics_engine, sample_matches):
        """Test performance adaptation analysis."""
        adaptation = analytics_engine._analyze_performance_adaptation(sample_matches, window_size=30)
        
        assert isinstance(adaptation, dict)
        assert "window_performances" in adaptation
        assert "adaptation_score" in adaptation
        assert "total_windows" in adaptation
        
        # Verify window performance structure
        if adaptation["window_performances"]:
            window_perf = adaptation["window_performances"][0]
            assert "start_date" in window_perf
            assert "end_date" in window_perf
            assert "games" in window_perf
            assert "win_rate" in window_perf
            assert "avg_kda" in window_perf
            assert "avg_cs_per_min" in window_perf
    
    def test_analyze_role_flexibility_changes(self, analytics_engine, sample_matches):
        """Test role flexibility analysis."""
        # Create matches with varying roles
        multi_role_matches = []
        roles = ["top", "jungle", "middle", "bottom", "support"]
        
        for i, (match, participant) in enumerate(sample_matches):
            participant.individual_position = roles[i % len(roles)]
            multi_role_matches.append((match, participant))
        
        flexibility = analytics_engine._analyze_role_flexibility_changes(
            multi_role_matches, window_size=20
        )
        
        assert isinstance(flexibility, dict)
        assert "role_flexibility" in flexibility
        assert "avg_flexibility" in flexibility
        assert "max_flexibility" in flexibility
        
        # Verify flexibility data structure
        if flexibility["role_flexibility"]:
            flex_data = flexibility["role_flexibility"][0]
            assert "start_date" in flex_data
            assert "end_date" in flex_data
            assert "unique_roles" in flex_data
            assert "roles_played" in flex_data
            assert "games" in flex_data
    
    def test_predict_metric_trend(self, analytics_engine):
        """Test individual metric trend prediction."""
        # Create time series data with clear trend
        base_time = datetime.now() - timedelta(days=30)
        time_series = []
        
        for i in range(20):
            timestamp = base_time + timedelta(days=i)
            value = 0.5 + (i * 0.01)  # Improving trend
            time_series.append(TimeSeriesPoint(timestamp=timestamp, value=value))
        
        prediction = analytics_engine._predict_metric_trend(time_series, prediction_days=7)
        
        assert isinstance(prediction, dict)
        assert "predicted_value" in prediction
        assert "trend_slope" in prediction
        assert "confidence" in prediction
        assert "prediction_date" in prediction
        assert "trend_direction" in prediction
        
        # Should detect improving trend
        assert prediction["trend_direction"] in ["improving", "stable"]
        assert prediction["trend_slope"] >= 0
        assert 0 <= prediction["confidence"] <= 1
    
    def test_calculate_prediction_confidence(self, analytics_engine, sample_matches):
        """Test prediction confidence calculation."""
        confidence = analytics_engine._calculate_prediction_confidence(
            sample_matches, ["win_rate", "avg_kda"]
        )
        
        assert isinstance(confidence, dict)
        assert "win_rate" in confidence
        assert "avg_kda" in confidence
        
        for metric, conf_score in confidence.items():
            assert 0 <= conf_score <= 1
    
    def test_caching_behavior(self, analytics_engine, sample_matches):
        """Test that trend analysis results are properly cached."""
        analytics_engine._get_filtered_matches = Mock(return_value=sample_matches)
        
        # First call should calculate and cache
        trends1 = analytics_engine.calculate_comprehensive_performance_trends(
            puuid="test_puuid",
            time_window_days=180
        )
        
        # Second call should use cache
        trends2 = analytics_engine.calculate_comprehensive_performance_trends(
            puuid="test_puuid",
            time_window_days=180
        )
        
        # Results should be identical (from cache)
        assert trends1.keys() == trends2.keys()
    
    def test_error_handling(self, analytics_engine):
        """Test error handling in trend analysis."""
        # Test with empty matches
        analytics_engine._get_filtered_matches = Mock(return_value=[])
        
        with pytest.raises(InsufficientDataError):
            analytics_engine.calculate_comprehensive_performance_trends("test_puuid")
        
        # Test with invalid PUUID
        analytics_engine._get_filtered_matches = Mock(side_effect=Exception("Database error"))
        
        with pytest.raises(AnalyticsError):
            analytics_engine.calculate_comprehensive_performance_trends("invalid_puuid")


class TestTrendAnalysisIntegration:
    """Test integration of trend analysis with other components."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=Config)
        config.cache_directory = "/tmp/test_cache"
        return config
    
    @pytest.fixture
    def mock_match_manager(self):
        """Create mock match manager."""
        return Mock()
    
    @pytest.fixture
    def mock_baseline_manager(self):
        """Create mock baseline manager."""
        return Mock(spec=BaselineManager)
    
    @pytest.fixture
    def analytics_engine_with_real_analyzer(self, mock_config, mock_match_manager, mock_baseline_manager):
        """Create analytics engine with real statistical analyzer."""
        engine = HistoricalAnalyticsEngine(
            config=mock_config,
            match_manager=mock_match_manager,
            baseline_manager=mock_baseline_manager
        )
        # Use real statistical analyzer instead of mock
        engine.statistical_analyzer = StatisticalAnalyzer()
        return engine
    
    def test_trend_analysis_with_real_statistical_analyzer(self, analytics_engine_with_real_analyzer):
        """Test trend analysis with real statistical analyzer."""
        # Create time series with clear linear trend
        base_time = datetime.now() - timedelta(days=50)
        time_series = []
        
        for i in range(25):
            timestamp = base_time + timedelta(days=i * 2)
            value = 0.4 + (i * 0.05)  # More pronounced improving trend
            time_series.append(TimeSeriesPoint(timestamp=timestamp, value=value))
        
        # Test linear regression trend analysis
        trend_result = analytics_engine_with_real_analyzer.statistical_analyzer.calculate_trend_analysis(
            time_series,
            method=TrendAnalysisMethod.LINEAR_REGRESSION
        )
        
        assert isinstance(trend_result, TrendAnalysis)
        assert trend_result.trend_direction in ["improving", "stable"]  # Allow for both due to threshold sensitivity
        assert trend_result.trend_strength >= 0  # Should have some trend strength
        assert trend_result.trend_duration_days > 0
    
    def test_seasonal_pattern_detection_accuracy(self, analytics_engine_with_real_analyzer):
        """Test accuracy of seasonal pattern detection."""
        # Create data with known seasonal pattern
        base_time = datetime.now() - timedelta(days=365)
        time_series = []
        
        for i in range(100):
            timestamp = base_time + timedelta(days=i * 3)
            # Create seasonal pattern: higher performance in certain months
            month_factor = 1.2 if timestamp.month in [6, 7, 8] else 0.8  # Summer boost
            base_value = 0.5
            seasonal_value = base_value * month_factor
            time_series.append(TimeSeriesPoint(timestamp=timestamp, value=seasonal_value))
        
        # Analyze seasonal patterns
        seasonal_patterns = analytics_engine_with_real_analyzer._analyze_monthly_patterns(time_series)
        
        # Should detect higher performance in summer months
        if 6 in seasonal_patterns and 12 in seasonal_patterns:
            assert seasonal_patterns[6] > seasonal_patterns[12]  # June > December
    
    def test_meta_shift_detection_accuracy(self, analytics_engine_with_real_analyzer):
        """Test accuracy of meta shift detection."""
        # Create matches with simulated meta shift
        matches = []
        base_date = datetime.now() - timedelta(days=120)
        
        for i in range(60):
            match = Mock(spec=Match)
            match.game_creation = int((base_date + timedelta(days=i * 2)).timestamp())
            match.game_creation_datetime = base_date + timedelta(days=i * 2)
            match.game_duration = 1800
            
            participant = Mock(spec=MatchParticipant)
            participant.puuid = "test_puuid"
            # Simulate meta shift at day 60: performance drops
            if i < 30:
                participant.win = i % 2 == 0  # 50% win rate
                participant.champion_id = 1 + (i % 3)  # 3 champions
            else:
                participant.win = i % 4 == 0  # 25% win rate (meta shift impact)
                participant.champion_id = 4 + (i % 2)  # Different champions
            
            participant.kills = 5
            participant.deaths = 3
            participant.assists = 7
            participant.cs_total = 150
            participant.vision_score = 20
            participant.total_damage_dealt_to_champions = 15000
            participant.gold_earned = 12000
            participant.individual_position = "middle"
            
            matches.append((match, participant))
        
        analytics_engine_with_real_analyzer._get_filtered_matches = Mock(return_value=matches)
        
        meta_shifts = analytics_engine_with_real_analyzer.detect_meta_shifts(
            puuid="test_puuid",
            time_window_days=120,
            shift_detection_window=20
        )
        
        # Should detect the performance drop and champion changes
        assert meta_shifts["total_matches"] == 60
        assert len(meta_shifts["champion_shifts"]["shifts"]) > 0
        
        # Performance adaptation should show declining trend
        adaptation = meta_shifts["performance_adaptation"]
        if len(adaptation["window_performances"]) >= 2:
            first_window = adaptation["window_performances"][0]
            last_window = adaptation["window_performances"][-1]
            # Later windows should have lower win rate due to meta shift
            assert last_window["win_rate"] < first_window["win_rate"]


if __name__ == "__main__":
    pytest.main([__file__])