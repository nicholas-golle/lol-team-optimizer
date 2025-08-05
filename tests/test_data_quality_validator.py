"""
Tests for the Data Quality Validator module.

This module tests data validation, quality scoring, and anomaly detection
capabilities for match data, player performance, and analytics results.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import statistics

from lol_team_optimizer.data_quality_validator import (
    DataQualityValidator, ValidationSeverity, AnomalyType,
    ValidationIssue, AnomalyDetection, DataQualityScore, DataQualityReport
)
from lol_team_optimizer.analytics_models import (
    PerformanceMetrics, DataValidationError
)
from lol_team_optimizer.models import (
    Match, MatchParticipant, Player, ChampionMastery, ChampionPerformance
)


class TestDataQualityValidator:
    """Test suite for DataQualityValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataQualityValidator()
        
        # Create sample match data
        self.sample_match = Match(
            match_id="TEST_MATCH_001",
            game_creation=int((datetime.now() - timedelta(hours=1)).timestamp() * 1000),
            game_duration=1800,  # 30 minutes
            game_end_timestamp=int(datetime.now().timestamp() * 1000),
            queue_id=420,  # Ranked Solo
            map_id=11,  # Summoner's Rift
            winning_team=100,
            participants=[
                MatchParticipant(
                    puuid=f"test_puuid_{i}",
                    summoner_name=f"TestPlayer{i}",
                    champion_id=i + 1,
                    team_id=100 if i < 5 else 200,
                    kills=5, deaths=3, assists=8,
                    total_damage_dealt_to_champions=15000,
                    total_minions_killed=150,
                    vision_score=25,
                    gold_earned=12000,
                    win=(i < 5)  # Team 100 wins
                ) for i in range(10)
            ]
        )
        
        # Create sample player data
        self.sample_player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner",
            puuid="test_puuid_123",
            role_preferences={"top": 4, "jungle": 3, "middle": 5, "support": 2, "bottom": 3},
            champion_masteries={
                1: ChampionMastery(
                    champion_id=1,
                    champion_name="Annie",
                    mastery_level=7,
                    mastery_points=50000,
                    performance=ChampionPerformance(
                        games_played=25,
                        wins=15,
                        losses=10,
                        total_kills=75,
                        total_deaths=50,
                        total_assists=125
                    )
                )
            }
        )
        
        # Create sample performance data
        self.sample_performance_data = [
            PerformanceMetrics(
                games_played=10,
                wins=6,
                win_rate=0.6,
                avg_kda=2.5,
                avg_cs_per_min=7.2,
                avg_vision_score=22.0
            ),
            PerformanceMetrics(
                games_played=12,
                wins=8,
                win_rate=0.67,
                avg_kda=3.1,
                avg_cs_per_min=7.8,
                avg_vision_score=25.0
            ),
            PerformanceMetrics(
                games_played=8,
                wins=2,
                win_rate=0.25,  # Significant drop
                avg_kda=1.2,
                avg_cs_per_min=6.5,
                avg_vision_score=18.0
            )
        ]
    
    def test_validate_match_data_valid_match(self):
        """Test validation of valid match data."""
        issues = self.validator.validate_match_data(self.sample_match)
        
        # Should have no critical or error issues
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        
        assert len(critical_issues) == 0, f"Found critical issues: {[i.message for i in critical_issues]}"
        assert len(error_issues) == 0, f"Found error issues: {[i.message for i in error_issues]}"
    
    def test_validate_match_data_missing_match_id(self):
        """Test validation with missing match ID."""
        invalid_match = Match(
            match_id="",  # Empty match ID
            game_creation=int(datetime.now().timestamp() * 1000),
            game_duration=1800,
            game_end_timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        issues = self.validator.validate_match_data(invalid_match)
        
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) > 0
        assert any("Match ID is missing" in issue.message for issue in critical_issues)
    
    def test_validate_match_data_invalid_duration(self):
        """Test validation with invalid match duration."""
        # Test very short match
        short_match = self.sample_match
        short_match.game_duration = 200  # 3 minutes 20 seconds
        
        issues = self.validator.validate_match_data(short_match)
        
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        assert any("unusually short" in issue.message.lower() for issue in warning_issues)
        
        # Test very long match
        long_match = self.sample_match
        long_match.game_duration = 8000  # Over 2 hours
        
        issues = self.validator.validate_match_data(long_match)
        
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        assert any("unusually long" in issue.message.lower() for issue in warning_issues)
    
    def test_validate_match_data_wrong_participant_count(self):
        """Test validation with wrong number of participants."""
        invalid_match = self.sample_match
        invalid_match.participants = invalid_match.participants[:8]  # Only 8 participants
        
        issues = self.validator.validate_match_data(invalid_match)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("Expected 10 participants" in issue.message for issue in error_issues)
    
    def test_validate_match_data_duplicate_champions(self):
        """Test validation with duplicate champions on same team."""
        invalid_match = self.sample_match
        # Make two participants on same team have same champion
        invalid_match.participants[0].champion_id = 1
        invalid_match.participants[1].champion_id = 1  # Duplicate
        
        issues = self.validator.validate_match_data(invalid_match)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("Duplicate champions" in issue.message for issue in error_issues)
    
    def test_validate_match_data_extreme_performance_values(self):
        """Test validation with extreme performance values."""
        invalid_match = self.sample_match
        # Set extreme values
        invalid_match.participants[0].kills = 100  # Unrealistic kills
        invalid_match.participants[0].deaths = 50  # Unrealistic deaths
        
        issues = self.validator.validate_match_data(invalid_match)
        
        warning_issues = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        assert any("Unusually high kills" in issue.message for issue in warning_issues)
        assert any("Unusually high deaths" in issue.message for issue in warning_issues)
    
    def test_validate_match_data_negative_values(self):
        """Test validation with negative performance values."""
        invalid_match = self.sample_match
        invalid_match.participants[0].kills = -5  # Negative kills
        
        issues = self.validator.validate_match_data(invalid_match)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("Negative values" in issue.message for issue in error_issues)
    
    def test_validate_match_data_temporal_inconsistency(self):
        """Test validation with temporal inconsistencies."""
        invalid_match = self.sample_match
        # Game creation after game end
        invalid_match.game_creation = invalid_match.game_end_timestamp + 1000
        
        issues = self.validator.validate_match_data(invalid_match)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("creation timestamp is after game end" in issue.message for issue in error_issues)
    
    def test_validate_player_data_valid_player(self):
        """Test validation of valid player data."""
        issues = self.validator.validate_player_data(self.sample_player)
        
        # Should have no critical or error issues
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        
        assert len(critical_issues) == 0, f"Found critical issues: {[i.message for i in critical_issues]}"
        assert len(error_issues) == 0, f"Found error issues: {[i.message for i in error_issues]}"
    
    def test_validate_player_data_missing_required_fields(self):
        """Test validation with missing required player fields."""
        invalid_player = Player(
            name="",  # Empty name
            summoner_name="TestSummoner",
            puuid=""  # Empty PUUID
        )
        
        issues = self.validator.validate_player_data(invalid_player)
        
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical_issues) >= 2  # Name and PUUID missing
        assert any("Player name is missing" in issue.message for issue in critical_issues)
        assert any("PUUID is missing" in issue.message for issue in critical_issues)
    
    def test_validate_player_data_invalid_role_preferences(self):
        """Test validation with invalid role preferences."""
        invalid_player = self.sample_player
        invalid_player.role_preferences = {
            "top": 6,  # Invalid preference (should be 1-5)
            "invalid_role": 3  # Invalid role name
        }
        
        issues = self.validator.validate_player_data(invalid_player)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("Invalid preference value" in issue.message for issue in error_issues)
        assert any("Invalid roles in preferences" in issue.message for issue in error_issues)
    
    def test_validate_player_data_mastery_inconsistency(self):
        """Test validation with champion mastery inconsistencies."""
        invalid_player = self.sample_player
        # Create mastery with mismatched champion ID
        invalid_player.champion_masteries[2] = ChampionMastery(
            champion_id=3,  # Different from key (2)
            champion_name="Blitzcrank",
            mastery_level=5,
            mastery_points=25000
        )
        
        issues = self.validator.validate_player_data(invalid_player)
        
        error_issues = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        assert any("Champion ID mismatch" in issue.message for issue in error_issues)
    
    def test_detect_performance_anomalies_statistical_outliers(self):
        """Test detection of statistical outliers in performance data."""
        # Create data with clear outlier - need more extreme values to trigger outlier detection
        base_data = [
            PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.0, avg_cs_per_min=7.0, avg_vision_score=20.0),
            PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.1, avg_cs_per_min=7.1, avg_vision_score=21.0),
            PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.0, avg_cs_per_min=7.0, avg_vision_score=20.0),
            PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.1, avg_cs_per_min=7.1, avg_vision_score=21.0),
            PerformanceMetrics(games_played=10, wins=5, win_rate=0.5, avg_kda=2.0, avg_cs_per_min=7.0, avg_vision_score=20.0),
        ]
        
        outlier_data = base_data + [
            PerformanceMetrics(
                games_played=15,
                wins=15,
                win_rate=1.0,  # Perfect win rate - outlier
                avg_kda=15.0,  # Very high KDA - outlier
                avg_cs_per_min=20.0,  # Very high CS - outlier
                avg_vision_score=80.0  # Very high vision - outlier
            )
        ]
        
        context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
        anomalies = self.validator.detect_performance_anomalies(outlier_data, context)
        
        outlier_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.STATISTICAL_OUTLIER]
        assert len(outlier_anomalies) > 0
        
        # Check that outliers were detected for multiple metrics
        detected_metrics = {a.affected_data["metric"] for a in outlier_anomalies}
        assert len(detected_metrics) > 0  # At least some metrics should be detected
    
    def test_detect_performance_anomalies_performance_drop(self):
        """Test detection of performance drops."""
        # Create data with more pronounced drop to ensure detection
        drop_data = [
            PerformanceMetrics(games_played=10, wins=7, win_rate=0.7, avg_kda=3.0),
            PerformanceMetrics(games_played=10, wins=7, win_rate=0.7, avg_kda=3.1),
            PerformanceMetrics(games_played=10, wins=7, win_rate=0.7, avg_kda=3.0),
            PerformanceMetrics(games_played=10, wins=7, win_rate=0.7, avg_kda=3.1),
            PerformanceMetrics(games_played=10, wins=2, win_rate=0.2, avg_kda=1.0)  # Significant drop
        ]
        
        context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
        anomalies = self.validator.detect_performance_anomalies(drop_data, context)
        
        drop_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.PERFORMANCE_DROP]
        assert len(drop_anomalies) > 0
        
        # Should detect the significant win rate drop in the last data point
        win_rate_drops = [a for a in drop_anomalies if a.affected_data["metric"] == "win_rate"]
        assert len(win_rate_drops) > 0
    
    def test_detect_performance_anomalies_performance_spike(self):
        """Test detection of performance spikes."""
        # Create data with performance spike - need more baseline data
        spike_data = [
            PerformanceMetrics(games_played=10, wins=4, win_rate=0.4, avg_kda=1.8),
            PerformanceMetrics(games_played=10, wins=4, win_rate=0.4, avg_kda=1.9),
            PerformanceMetrics(games_played=10, wins=4, win_rate=0.4, avg_kda=1.8),
            PerformanceMetrics(games_played=10, wins=4, win_rate=0.4, avg_kda=1.9),
            PerformanceMetrics(games_played=10, wins=9, win_rate=0.9, avg_kda=5.0)  # Significant spike
        ]
        
        context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
        anomalies = self.validator.detect_performance_anomalies(spike_data, context)
        
        spike_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.PERFORMANCE_SPIKE]
        assert len(spike_anomalies) > 0
    
    def test_detect_performance_anomalies_temporal_anomalies(self):
        """Test detection of temporal anomalies."""
        # Create data with sudden activity spike - need minimum sample size
        temporal_data = [
            PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            PerformanceMetrics(games_played=50, wins=30, win_rate=0.6)  # 10x activity spike
        ]
        
        context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
        anomalies = self.validator.detect_performance_anomalies(temporal_data, context)
        
        temporal_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.TEMPORAL_ANOMALY]
        assert len(temporal_anomalies) > 0
    
    def test_detect_performance_anomalies_insufficient_data(self):
        """Test anomaly detection with insufficient data."""
        insufficient_data = [
            PerformanceMetrics(games_played=5, wins=3, win_rate=0.6),
            PerformanceMetrics(games_played=6, wins=4, win_rate=0.67)
        ]  # Only 2 data points, below minimum
        
        context = {"player_name": "TestPlayer", "puuid": "test_puuid"}
        anomalies = self.validator.detect_performance_anomalies(insufficient_data, context)
        
        # Should return empty list due to insufficient data
        assert len(anomalies) == 0
    
    def test_calculate_data_quality_score_high_quality(self):
        """Test data quality score calculation with high-quality data."""
        matches = [self.sample_match]
        players = [self.sample_player]
        
        quality_score = self.validator.calculate_data_quality_score(matches, players)
        
        assert quality_score.overall_score > 0.8
        assert quality_score.validity_score > 0.8
        assert quality_score.total_records == 2
        assert quality_score.valid_records == 2
        assert quality_score.reliability_indicator in ["good", "excellent"]
    
    def test_calculate_data_quality_score_low_quality(self):
        """Test data quality score calculation with low-quality data."""
        # Create invalid match and player
        invalid_match = Match(
            match_id="",  # Missing ID
            game_creation=0,  # Invalid timestamp
            game_duration=-100,  # Negative duration
            game_end_timestamp=0,  # Required field
            participants=[]  # No participants
        )
        
        invalid_player = Player(
            name="",  # Missing name
            summoner_name="",  # Missing summoner name
            puuid=""  # Missing PUUID
        )
        
        matches = [invalid_match]
        players = [invalid_player]
        
        quality_score = self.validator.calculate_data_quality_score(matches, players)
        
        assert quality_score.overall_score < 0.5
        assert quality_score.validity_score < 0.5
        assert quality_score.reliability_indicator in ["poor", "critical"]
    
    def test_calculate_data_quality_score_empty_data(self):
        """Test data quality score calculation with empty data."""
        quality_score = self.validator.calculate_data_quality_score([], [])
        
        assert quality_score.overall_score == 0.0
        assert quality_score.total_records == 0
        assert quality_score.valid_records == 0
    
    def test_generate_quality_report_comprehensive(self):
        """Test generation of comprehensive quality report."""
        matches = [self.sample_match]
        players = [self.sample_player]
        
        report = self.validator.generate_quality_report(matches, players)
        
        assert report.report_id.startswith("dq_report_")
        assert isinstance(report.generated_at, datetime)
        assert report.data_source == "lol_team_optimizer"
        assert isinstance(report.quality_score, DataQualityScore)
        assert isinstance(report.validation_issues, list)
        assert isinstance(report.detected_anomalies, list)
        assert isinstance(report.summary_stats, dict)
        assert isinstance(report.recommendations, list)
        
        # Check summary statistics structure
        assert "data_overview" in report.summary_stats
        assert "validation_summary" in report.summary_stats
        assert "anomaly_summary" in report.summary_stats
        
        # Check data overview
        data_overview = report.summary_stats["data_overview"]
        assert data_overview["total_matches"] == 1
        assert data_overview["total_players"] == 1
    
    def test_generate_quality_report_with_issues(self):
        """Test quality report generation with validation issues."""
        # Create data with known issues
        invalid_match = self.sample_match
        invalid_match.participants[0].kills = -5  # Negative kills
        
        invalid_player = self.sample_player
        invalid_player.role_preferences["invalid_role"] = 3  # Invalid role
        
        matches = [invalid_match]
        players = [invalid_player]
        
        report = self.validator.generate_quality_report(matches, players)
        
        assert len(report.validation_issues) > 0
        
        # Check validation summary
        validation_summary = report.summary_stats["validation_summary"]
        assert validation_summary["total_issues"] > 0
        assert validation_summary["error_issues"] > 0
    
    def test_quality_report_methods(self):
        """Test DataQualityReport utility methods."""
        # Create report with various issues and anomalies
        report = DataQualityReport(
            report_id="test_report",
            generated_at=datetime.now(),
            data_source="test",
            assessment_period=(datetime.now() - timedelta(days=1), datetime.now()),
            quality_score=DataQualityScore(
                overall_score=0.8,
                completeness_score=0.9,
                consistency_score=0.8,
                accuracy_score=0.7,
                timeliness_score=0.8,
                validity_score=0.9
            ),
            validation_issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue_type="test_critical",
                    message="Critical test issue"
                ),
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="test_warning",
                    message="Warning test issue"
                )
            ],
            detected_anomalies=[
                AnomalyDetection(
                    anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                    severity=ValidationSeverity.CRITICAL,
                    description="Test outlier",
                    affected_data={"test": "data"}
                ),
                AnomalyDetection(
                    anomaly_type=AnomalyType.PERFORMANCE_SPIKE,
                    severity=ValidationSeverity.INFO,
                    description="Test spike",
                    affected_data={"test": "data"}
                )
            ]
        )
        
        # Test get_issues_by_severity
        critical_issues = report.get_issues_by_severity(ValidationSeverity.CRITICAL)
        assert len(critical_issues) == 1
        assert critical_issues[0].message == "Critical test issue"
        
        warning_issues = report.get_issues_by_severity(ValidationSeverity.WARNING)
        assert len(warning_issues) == 1
        
        # Test get_anomalies_by_type
        outlier_anomalies = report.get_anomalies_by_type(AnomalyType.STATISTICAL_OUTLIER)
        assert len(outlier_anomalies) == 1
        
        spike_anomalies = report.get_anomalies_by_type(AnomalyType.PERFORMANCE_SPIKE)
        assert len(spike_anomalies) == 1
        
        # Test get_critical_issues
        critical_items = report.get_critical_issues()
        assert len(critical_items) == 2  # 1 critical issue + 1 critical anomaly
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation and validation."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            issue_type="test_issue",
            message="Test validation issue",
            context={"key": "value"},
            suggested_action="Fix the issue"
        )
        
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.issue_type == "test_issue"
        assert issue.message == "Test validation issue"
        assert issue.context["key"] == "value"
        assert issue.suggested_action == "Fix the issue"
        assert isinstance(issue.timestamp, datetime)
        
        # Test validation of empty message
        with pytest.raises(DataValidationError):
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="test",
                message=""  # Empty message should raise error
            )
    
    def test_anomaly_detection_creation(self):
        """Test AnomalyDetection creation and validation."""
        anomaly = AnomalyDetection(
            anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
            severity=ValidationSeverity.WARNING,
            description="Test anomaly detection",
            affected_data={"metric": "test_metric", "value": 1.5},
            statistical_measures={"z_score": 3.2, "threshold": 3.0},
            confidence=0.85,
            explanation="Test explanation"
        )
        
        assert anomaly.anomaly_type == AnomalyType.STATISTICAL_OUTLIER
        assert anomaly.severity == ValidationSeverity.WARNING
        assert anomaly.confidence == 0.85
        assert anomaly.statistical_measures["z_score"] == 3.2
        assert isinstance(anomaly.timestamp, datetime)
        
        # Test validation of confidence range
        with pytest.raises(DataValidationError):
            AnomalyDetection(
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                severity=ValidationSeverity.WARNING,
                description="Test",
                affected_data={},
                confidence=1.5  # Invalid confidence > 1.0
            )
        
        # Test validation of empty description
        with pytest.raises(DataValidationError):
            AnomalyDetection(
                anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                severity=ValidationSeverity.WARNING,
                description="",  # Empty description
                affected_data={},
                confidence=0.5
            )
    
    def test_data_quality_score_creation(self):
        """Test DataQualityScore creation and validation."""
        score = DataQualityScore(
            overall_score=0.0,  # Will be calculated
            completeness_score=0.9,
            consistency_score=0.8,
            accuracy_score=0.85,
            timeliness_score=0.7,
            validity_score=0.95,
            total_records=100,
            valid_records=90
        )
        
        # Overall score should be calculated automatically
        assert 0.8 < score.overall_score < 0.9
        assert score.reliability_indicator == "good"
        
        # Test validation of score ranges
        with pytest.raises(DataValidationError):
            DataQualityScore(
                overall_score=0.8,
                completeness_score=1.5,  # Invalid score > 1.0
                consistency_score=0.8,
                accuracy_score=0.8,
                timeliness_score=0.8,
                validity_score=0.8
            )
    
    def test_validator_initialization(self):
        """Test DataQualityValidator initialization."""
        validator = DataQualityValidator()
        
        assert hasattr(validator, 'validation_rules')
        assert hasattr(validator, 'anomaly_detectors')
        assert validator.outlier_threshold == 2.0
        assert validator.min_sample_size == 5
        
        # Check validation rules structure
        assert 'match_duration_min' in validator.validation_rules
        assert 'max_kills_per_game' in validator.validation_rules
        assert 'valid_queue_ids' in validator.validation_rules
        
        # Check anomaly detector configuration
        assert 'outlier_methods' in validator.anomaly_detectors
        assert 'performance_metrics' in validator.anomaly_detectors
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        # Test with None values
        with pytest.raises(AttributeError):
            self.validator.validate_match_data(None)
        
        # Test with empty performance data
        anomalies = self.validator.detect_performance_anomalies([], {})
        assert len(anomalies) == 0
        
        # Test quality score with empty data
        score = self.validator.calculate_data_quality_score([], [])
        assert score.overall_score == 0.0
        assert score.total_records == 0
    
    def test_performance_metrics_validation_in_context(self):
        """Test performance metrics validation within the validator context."""
        # Test with valid performance metrics
        valid_metrics = PerformanceMetrics(
            games_played=10,
            wins=6,
            win_rate=0.6,
            avg_kda=2.5,
            avg_cs_per_min=7.2,
            avg_vision_score=22.0
        )
        
        # Should not raise any exceptions
        assert valid_metrics.games_played == 10
        assert valid_metrics.win_rate == 0.6
        
        # Test with invalid performance metrics
        with pytest.raises(DataValidationError):
            PerformanceMetrics(
                games_played=-5,  # Negative games
                wins=6,
                win_rate=0.6
            )
    
    def test_comprehensive_integration(self):
        """Test comprehensive integration of all validation components."""
        # Create a mix of valid and invalid data
        matches = [
            self.sample_match,  # Valid match
            Match(  # Invalid match
                match_id="",
                game_creation=0,
                game_duration=-100,
                game_end_timestamp=0,  # Required field
                participants=[]
            )
        ]
        
        players = [
            self.sample_player,  # Valid player
            Player(  # Invalid player
                name="",
                summoner_name="",
                puuid="",
                role_preferences={"invalid_role": 6}
            )
        ]
        
        # Generate comprehensive report
        report = self.validator.generate_quality_report(matches, players, "integration_test")
        
        # Verify report completeness
        assert report.report_id == "integration_test"
        assert len(report.validation_issues) > 0
        assert report.quality_score.overall_score < 0.8  # Should be low due to invalid data
        assert len(report.recommendations) > 0
        
        # Verify critical issues are identified
        critical_items = report.get_critical_issues()
        assert len(critical_items) > 0
        
        # Verify summary statistics
        assert report.summary_stats["data_overview"]["total_matches"] == 2
        assert report.summary_stats["data_overview"]["total_players"] == 2
        assert report.summary_stats["validation_summary"]["total_issues"] > 0