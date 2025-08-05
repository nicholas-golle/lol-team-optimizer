"""
Data Quality Validation and Anomaly Detection for League of Legends Team Optimizer.

This module provides comprehensive data validation, quality scoring, and anomaly detection
capabilities for match data, player performance, and analytics results.
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from enum import Enum
import math

from .analytics_models import (
    DataValidationError, PerformanceMetrics, ChampionPerformanceMetrics,
    ConfidenceInterval, SignificanceTest
)
from .models import Match, MatchParticipant, Player, ChampionMastery


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""
    STATISTICAL_OUTLIER = "statistical_outlier"
    PERFORMANCE_SPIKE = "performance_spike"
    PERFORMANCE_DROP = "performance_drop"
    DATA_INCONSISTENCY = "data_inconsistency"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    CHAMPION_ANOMALY = "champion_anomaly"
    ROLE_ANOMALY = "role_anomaly"


@dataclass
class ValidationIssue:
    """Represents a data validation issue."""
    
    severity: ValidationSeverity
    issue_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate issue data."""
        if not self.message:
            raise DataValidationError("Validation issue message cannot be empty")


@dataclass
class AnomalyDetection:
    """Represents a detected anomaly in the data."""
    
    anomaly_type: AnomalyType
    severity: ValidationSeverity
    description: str
    affected_data: Dict[str, Any]
    statistical_measures: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    explanation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate anomaly detection data."""
        if not 0 <= self.confidence <= 1:
            raise DataValidationError("Confidence must be between 0 and 1")
        
        if not self.description:
            raise DataValidationError("Anomaly description cannot be empty")


@dataclass
class DataQualityScore:
    """Represents overall data quality assessment."""
    
    overall_score: float  # 0.0 to 1.0
    completeness_score: float
    consistency_score: float
    accuracy_score: float
    timeliness_score: float
    validity_score: float
    
    # Detailed metrics
    total_records: int = 0
    valid_records: int = 0
    missing_data_percentage: float = 0.0
    inconsistency_count: int = 0
    anomaly_count: int = 0
    
    # Quality indicators
    confidence_level: float = 0.0
    reliability_indicator: str = "unknown"
    
    def __post_init__(self):
        """Validate and calculate overall score."""
        scores = [
            self.completeness_score, self.consistency_score, self.accuracy_score,
            self.timeliness_score, self.validity_score
        ]
        
        for score in scores:
            if not 0 <= score <= 1:
                raise DataValidationError("All quality scores must be between 0 and 1")
        
        # Calculate overall score as weighted average
        if self.overall_score == 0.0:
            weights = [0.25, 0.20, 0.25, 0.15, 0.15]  # Emphasize completeness and accuracy
            self.overall_score = sum(score * weight for score, weight in zip(scores, weights))
        
        # Determine reliability indicator
        if self.overall_score >= 0.9:
            self.reliability_indicator = "excellent"
        elif self.overall_score >= 0.8:
            self.reliability_indicator = "good"
        elif self.overall_score >= 0.7:
            self.reliability_indicator = "fair"
        elif self.overall_score >= 0.6:
            self.reliability_indicator = "poor"
        else:
            self.reliability_indicator = "critical"


@dataclass
class DataQualityReport:
    """Comprehensive data quality assessment report."""
    
    report_id: str
    generated_at: datetime
    data_source: str
    assessment_period: Tuple[datetime, datetime]
    
    # Quality assessment
    quality_score: DataQualityScore
    validation_issues: List[ValidationIssue] = field(default_factory=list)
    detected_anomalies: List[AnomalyDetection] = field(default_factory=list)
    
    # Summary statistics
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get validation issues by severity level."""
        return [issue for issue in self.validation_issues if issue.severity == severity]
    
    def get_anomalies_by_type(self, anomaly_type: AnomalyType) -> List[AnomalyDetection]:
        """Get anomalies by type."""
        return [anomaly for anomaly in self.detected_anomalies if anomaly.anomaly_type == anomaly_type]
    
    def get_critical_issues(self) -> List[Union[ValidationIssue, AnomalyDetection]]:
        """Get all critical issues and anomalies."""
        critical_issues = self.get_issues_by_severity(ValidationSeverity.CRITICAL)
        critical_anomalies = [a for a in self.detected_anomalies if a.severity == ValidationSeverity.CRITICAL]
        return critical_issues + critical_anomalies


class DataQualityValidator:
    """Main data quality validation and anomaly detection system."""
    
    def __init__(self):
        """Initialize the data quality validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._initialize_validation_rules()
        self.anomaly_detectors = self._initialize_anomaly_detectors()
        
        # Statistical thresholds for anomaly detection
        self.outlier_threshold = 2.0  # Standard deviations (lowered for better detection)
        self.performance_spike_threshold = 2.5
        self.performance_drop_threshold = -2.0
        self.min_sample_size = 5
    
    def validate_match_data(self, match: Match) -> List[ValidationIssue]:
        """
        Validate match data integrity and consistency.
        
        Args:
            match: Match object to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            # Basic match validation
            issues.extend(self._validate_match_basic_fields(match))
            
            # Participant validation
            issues.extend(self._validate_match_participants(match))
            
            # Team composition validation
            issues.extend(self._validate_team_composition(match))
            
            # Performance data validation
            issues.extend(self._validate_performance_data(match))
            
            # Temporal validation
            issues.extend(self._validate_temporal_consistency(match))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="validation_error",
                message=f"Critical error during match validation: {str(e)}",
                context={"match_id": match.match_id}
            ))
        
        return issues
    
    def validate_player_data(self, player: Player) -> List[ValidationIssue]:
        """
        Validate player data integrity and consistency.
        
        Args:
            player: Player object to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            # Basic player validation
            issues.extend(self._validate_player_basic_fields(player))
            
            # Champion mastery validation
            issues.extend(self._validate_champion_masteries(player))
            
            # Role preferences validation
            issues.extend(self._validate_role_preferences(player))
            
            # Performance cache validation
            issues.extend(self._validate_performance_cache(player))
            
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="validation_error",
                message=f"Critical error during player validation: {str(e)}",
                context={"player_name": player.name, "puuid": player.puuid}
            ))
        
        return issues
    
    def detect_performance_anomalies(self, 
                                   performance_data: List[PerformanceMetrics],
                                   context: Dict[str, Any]) -> List[AnomalyDetection]:
        """
        Detect anomalies in performance data using statistical methods.
        
        Args:
            performance_data: List of performance metrics to analyze
            context: Context information for the analysis
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        if len(performance_data) < self.min_sample_size:
            return anomalies
        
        try:
            # Statistical outlier detection
            anomalies.extend(self._detect_statistical_outliers(performance_data, context))
            
            # Performance spike/drop detection
            anomalies.extend(self._detect_performance_changes(performance_data, context))
            
            # Temporal anomaly detection
            anomalies.extend(self._detect_temporal_anomalies(performance_data, context))
            
            # Champion-specific anomaly detection
            if "champion_data" in context:
                anomalies.extend(self._detect_champion_anomalies(performance_data, context))
            
        except Exception as e:
            self.logger.error(f"Error detecting performance anomalies: {str(e)}")
        
        return anomalies
    
    def calculate_data_quality_score(self, 
                                   matches: List[Match],
                                   players: List[Player]) -> DataQualityScore:
        """
        Calculate comprehensive data quality score.
        
        Args:
            matches: List of matches to assess
            players: List of players to assess
            
        Returns:
            Data quality score assessment
        """
        total_records = len(matches) + len(players)
        if total_records == 0:
            return DataQualityScore(
                overall_score=0.0,
                completeness_score=0.0,
                consistency_score=0.0,
                accuracy_score=0.0,
                timeliness_score=0.0,
                validity_score=0.0
            )
        
        # Validate all data and collect issues
        all_issues = []
        valid_records = 0
        
        for match in matches:
            match_issues = self.validate_match_data(match)
            all_issues.extend(match_issues)
            if not any(issue.severity == ValidationSeverity.CRITICAL for issue in match_issues):
                valid_records += 1
        
        for player in players:
            player_issues = self.validate_player_data(player)
            all_issues.extend(player_issues)
            if not any(issue.severity == ValidationSeverity.CRITICAL for issue in player_issues):
                valid_records += 1
        
        # Calculate individual quality scores
        completeness_score = self._calculate_completeness_score(matches, players)
        consistency_score = self._calculate_consistency_score(all_issues)
        accuracy_score = self._calculate_accuracy_score(all_issues)
        timeliness_score = self._calculate_timeliness_score(matches, players)
        validity_score = valid_records / total_records if total_records > 0 else 0.0
        
        # Count issues by severity
        critical_issues = len([i for i in all_issues if i.severity == ValidationSeverity.CRITICAL])
        error_issues = len([i for i in all_issues if i.severity == ValidationSeverity.ERROR])
        
        return DataQualityScore(
            overall_score=0.0,  # Will be calculated in __post_init__
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            accuracy_score=accuracy_score,
            timeliness_score=timeliness_score,
            validity_score=validity_score,
            total_records=total_records,
            valid_records=valid_records,
            missing_data_percentage=(total_records - valid_records) / total_records * 100,
            inconsistency_count=error_issues,
            anomaly_count=critical_issues,
            confidence_level=min(1.0, valid_records / max(total_records, 1))
        )
    
    def generate_quality_report(self, 
                              matches: List[Match],
                              players: List[Player],
                              report_id: Optional[str] = None) -> DataQualityReport:
        """
        Generate comprehensive data quality report.
        
        Args:
            matches: List of matches to assess
            players: List of players to assess
            report_id: Optional report identifier
            
        Returns:
            Comprehensive data quality report
        """
        if report_id is None:
            report_id = f"dq_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate quality score
        quality_score = self.calculate_data_quality_score(matches, players)
        
        # Collect all validation issues
        all_issues = []
        for match in matches:
            all_issues.extend(self.validate_match_data(match))
        for player in players:
            all_issues.extend(self.validate_player_data(player))
        
        # Detect anomalies in performance data
        all_anomalies = []
        for player in players:
            if player.performance_cache:
                performance_data = []
                for role, perf_dict in player.performance_cache.items():
                    if isinstance(perf_dict, dict) and 'performance' in perf_dict:
                        performance_data.append(perf_dict['performance'])
                
                if performance_data:
                    context = {"player_name": player.name, "puuid": player.puuid}
                    anomalies = self.detect_performance_anomalies(performance_data, context)
                    all_anomalies.extend(anomalies)
        
        # Generate summary statistics
        summary_stats = self._generate_summary_statistics(matches, players, all_issues, all_anomalies)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(quality_score, all_issues, all_anomalies)
        
        # Determine assessment period
        if matches:
            match_dates = [match.game_creation_datetime for match in matches]
            assessment_period = (min(match_dates), max(match_dates))
        else:
            now = datetime.now()
            assessment_period = (now - timedelta(days=30), now)
        
        return DataQualityReport(
            report_id=report_id,
            generated_at=datetime.now(),
            data_source="lol_team_optimizer",
            assessment_period=assessment_period,
            quality_score=quality_score,
            validation_issues=all_issues,
            detected_anomalies=all_anomalies,
            summary_stats=summary_stats,
            recommendations=recommendations
        )
    
    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """Initialize validation rules configuration."""
        return {
            "match_duration_min": 300,  # 5 minutes minimum
            "match_duration_max": 7200,  # 2 hours maximum
            "valid_queue_ids": {420, 440, 450, 400, 430},  # Common ranked/normal queues
            "valid_map_ids": {11, 12},  # Summoner's Rift, Howling Abyss
            "max_kills_per_game": 50,
            "max_deaths_per_game": 30,
            "max_assists_per_game": 60,
            "max_cs_per_minute": 15.0,
            "max_vision_score_per_minute": 5.0,
            "max_damage_per_minute": 2000.0,
            "max_gold_per_minute": 1000.0
        }
    
    def _initialize_anomaly_detectors(self) -> Dict[str, Any]:
        """Initialize anomaly detection configuration."""
        return {
            "outlier_methods": ["z_score", "iqr", "modified_z_score"],
            "performance_metrics": ["win_rate", "avg_kda", "avg_cs_per_min", "avg_vision_score"],
            "temporal_window_days": 30,
            "min_games_for_analysis": 5
        }
    
    def _validate_match_basic_fields(self, match: Match) -> List[ValidationIssue]:
        """Validate basic match fields."""
        issues = []
        
        # Match ID validation
        if not match.match_id or not match.match_id.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="missing_data",
                message="Match ID is missing or empty",
                context={"match_id": match.match_id}
            ))
        
        # Duration validation
        rules = self.validation_rules
        if match.game_duration < rules["match_duration_min"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                issue_type="data_anomaly",
                message=f"Match duration ({match.game_duration}s) is unusually short",
                context={"match_id": match.match_id, "duration": match.game_duration},
                suggested_action="Verify match was not a remake or early surrender"
            ))
        elif match.game_duration > rules["match_duration_max"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                issue_type="data_anomaly",
                message=f"Match duration ({match.game_duration}s) is unusually long",
                context={"match_id": match.match_id, "duration": match.game_duration}
            ))
        
        # Queue and map validation
        if match.queue_id not in rules["valid_queue_ids"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                issue_type="data_quality",
                message=f"Uncommon queue ID: {match.queue_id}",
                context={"match_id": match.match_id, "queue_id": match.queue_id}
            ))
        
        if match.map_id not in rules["valid_map_ids"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                issue_type="data_quality",
                message=f"Uncommon map ID: {match.map_id}",
                context={"match_id": match.match_id, "map_id": match.map_id}
            ))
        
        return issues
    
    def _validate_match_participants(self, match: Match) -> List[ValidationIssue]:
        """Validate match participants data."""
        issues = []
        
        # Participant count validation
        if len(match.participants) != 10:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="data_inconsistency",
                message=f"Expected 10 participants, found {len(match.participants)}",
                context={"match_id": match.match_id, "participant_count": len(match.participants)}
            ))
        
        # Team distribution validation
        team_counts = {}
        for participant in match.participants:
            team_counts[participant.team_id] = team_counts.get(participant.team_id, 0) + 1
        
        if len(team_counts) != 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="data_inconsistency",
                message=f"Expected 2 teams, found {len(team_counts)}",
                context={"match_id": match.match_id, "team_counts": team_counts}
            ))
        
        for team_id, count in team_counts.items():
            if count != 5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="data_inconsistency",
                    message=f"Team {team_id} has {count} players, expected 5",
                    context={"match_id": match.match_id, "team_id": team_id, "count": count}
                ))
        
        # Individual participant validation
        for participant in match.participants:
            issues.extend(self._validate_participant_data(participant, match.match_id))
        
        return issues
    
    def _validate_participant_data(self, participant: MatchParticipant, match_id: str) -> List[ValidationIssue]:
        """Validate individual participant data."""
        issues = []
        rules = self.validation_rules
        
        # Basic field validation
        if not participant.puuid:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="missing_data",
                message="Participant PUUID is missing",
                context={"match_id": match_id, "summoner_name": participant.summoner_name}
            ))
        
        if participant.champion_id <= 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="invalid_data",
                message=f"Invalid champion ID: {participant.champion_id}",
                context={"match_id": match_id, "puuid": participant.puuid}
            ))
        
        # Performance validation
        if participant.kills > rules["max_kills_per_game"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                issue_type="data_anomaly",
                message=f"Unusually high kills: {participant.kills}",
                context={"match_id": match_id, "puuid": participant.puuid, "kills": participant.kills}
            ))
        
        if participant.deaths > rules["max_deaths_per_game"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                issue_type="data_anomaly",
                message=f"Unusually high deaths: {participant.deaths}",
                context={"match_id": match_id, "puuid": participant.puuid, "deaths": participant.deaths}
            ))
        
        if participant.assists > rules["max_assists_per_game"]:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                issue_type="data_anomaly",
                message=f"Unusually high assists: {participant.assists}",
                context={"match_id": match_id, "puuid": participant.puuid, "assists": participant.assists}
            ))
        
        # Negative values validation
        if any(value < 0 for value in [participant.kills, participant.deaths, participant.assists,
                                     participant.total_damage_dealt_to_champions, participant.total_minions_killed,
                                     participant.neutral_minions_killed, participant.vision_score, participant.gold_earned]):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="invalid_data",
                message="Negative values found in participant performance data",
                context={"match_id": match_id, "puuid": participant.puuid}
            ))
        
        return issues
    
    def _validate_team_composition(self, match: Match) -> List[ValidationIssue]:
        """Validate team composition and role assignments."""
        issues = []
        
        # Check for duplicate champions on same team
        for team_id in [100, 200]:
            team_participants = match.get_participants_by_team(team_id)
            champion_ids = [p.champion_id for p in team_participants]
            
            if len(champion_ids) != len(set(champion_ids)):
                duplicate_champions = [cid for cid in champion_ids if champion_ids.count(cid) > 1]
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="data_inconsistency",
                    message=f"Duplicate champions on team {team_id}: {duplicate_champions}",
                    context={"match_id": match.match_id, "team_id": team_id, "duplicates": duplicate_champions}
                ))
        
        # Validate role assignments
        for team_id in [100, 200]:
            team_participants = match.get_participants_by_team(team_id)
            roles = [p.individual_position for p in team_participants if p.individual_position]
            
            expected_roles = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"}
            if len(roles) == 5 and set(roles) != expected_roles:
                missing_roles = expected_roles - set(roles)
                extra_roles = set(roles) - expected_roles
                
                if missing_roles or extra_roles:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="data_quality",
                        message=f"Unusual role distribution on team {team_id}",
                        context={
                            "match_id": match.match_id,
                            "team_id": team_id,
                            "roles": roles,
                            "missing": list(missing_roles),
                            "extra": list(extra_roles)
                        }
                    ))
        
        return issues
    
    def _validate_performance_data(self, match: Match) -> List[ValidationIssue]:
        """Validate performance data consistency."""
        issues = []
        
        # Calculate per-minute rates and validate
        game_duration_minutes = match.game_duration / 60.0
        rules = self.validation_rules
        
        for participant in match.participants:
            if game_duration_minutes > 0:
                cs_per_min = participant.cs_total / game_duration_minutes
                vision_per_min = participant.vision_score / game_duration_minutes
                damage_per_min = participant.total_damage_dealt_to_champions / game_duration_minutes
                gold_per_min = participant.gold_earned / game_duration_minutes
                
                if cs_per_min > rules["max_cs_per_minute"]:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="data_anomaly",
                        message=f"Unusually high CS/min: {cs_per_min:.1f}",
                        context={"match_id": match.match_id, "puuid": participant.puuid, "cs_per_min": cs_per_min}
                    ))
                
                if vision_per_min > rules["max_vision_score_per_minute"]:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="data_anomaly",
                        message=f"Unusually high vision score/min: {vision_per_min:.1f}",
                        context={"match_id": match.match_id, "puuid": participant.puuid, "vision_per_min": vision_per_min}
                    ))
                
                if damage_per_min > rules["max_damage_per_minute"]:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="data_anomaly",
                        message=f"Unusually high damage/min: {damage_per_min:.0f}",
                        context={"match_id": match.match_id, "puuid": participant.puuid, "damage_per_min": damage_per_min}
                    ))
                
                if gold_per_min > rules["max_gold_per_minute"]:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="data_anomaly",
                        message=f"Unusually high gold/min: {gold_per_min:.0f}",
                        context={"match_id": match.match_id, "puuid": participant.puuid, "gold_per_min": gold_per_min}
                    ))
        
        return issues
    
    def _validate_temporal_consistency(self, match: Match) -> List[ValidationIssue]:
        """Validate temporal consistency of match data."""
        issues = []
        
        # Check timestamp consistency
        if match.game_creation > match.game_end_timestamp:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="data_inconsistency",
                message="Game creation timestamp is after game end timestamp",
                context={
                    "match_id": match.match_id,
                    "creation": match.game_creation,
                    "end": match.game_end_timestamp
                }
            ))
        
        # Check if match is from the future
        now_timestamp = int(datetime.now().timestamp() * 1000)
        if match.game_creation > now_timestamp:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="data_inconsistency",
                message="Match creation timestamp is in the future",
                context={"match_id": match.match_id, "creation": match.game_creation}
            ))
        
        # Check calculated vs reported duration
        if match.game_end_timestamp > 0 and match.game_creation > 0:
            calculated_duration = (match.game_end_timestamp - match.game_creation) / 1000
            duration_diff = abs(calculated_duration - match.game_duration)
            
            if duration_diff > 60:  # More than 1 minute difference
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="data_inconsistency",
                    message=f"Duration mismatch: reported {match.game_duration}s, calculated {calculated_duration:.0f}s",
                    context={
                        "match_id": match.match_id,
                        "reported_duration": match.game_duration,
                        "calculated_duration": calculated_duration
                    }
                ))
        
        return issues
    
    def _validate_player_basic_fields(self, player: Player) -> List[ValidationIssue]:
        """Validate basic player fields."""
        issues = []
        
        # Required fields validation
        if not player.name or not player.name.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="missing_data",
                message="Player name is missing or empty",
                context={"puuid": player.puuid}
            ))
        
        if not player.summoner_name or not player.summoner_name.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="missing_data",
                message="Summoner name is missing or empty",
                context={"player_name": player.name, "puuid": player.puuid}
            ))
        
        if not player.puuid or not player.puuid.strip():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                issue_type="missing_data",
                message="Player PUUID is missing or empty",
                context={"player_name": player.name}
            ))
        
        return issues
    
    def _validate_champion_masteries(self, player: Player) -> List[ValidationIssue]:
        """Validate champion mastery data."""
        issues = []
        
        for champion_id, mastery in player.champion_masteries.items():
            # Validate champion ID consistency
            if champion_id != mastery.champion_id:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="data_inconsistency",
                    message=f"Champion ID mismatch in mastery data: key={champion_id}, value={mastery.champion_id}",
                    context={"player_name": player.name, "champion_id": champion_id}
                ))
            
            # Validate mastery level and points consistency
            if mastery.mastery_level > 7:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="data_anomaly",
                    message=f"Unusually high mastery level: {mastery.mastery_level}",
                    context={"player_name": player.name, "champion_id": champion_id, "level": mastery.mastery_level}
                ))
            
            # Check for reasonable mastery points for level
            expected_points = self._get_expected_mastery_points(mastery.mastery_level)
            if expected_points and mastery.mastery_points < expected_points * 0.5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    issue_type="data_inconsistency",
                    message=f"Low mastery points for level {mastery.mastery_level}: {mastery.mastery_points}",
                    context={"player_name": player.name, "champion_id": champion_id}
                ))
        
        return issues
    
    def _validate_role_preferences(self, player: Player) -> List[ValidationIssue]:
        """Validate role preferences data."""
        issues = []
        
        valid_roles = {"top", "jungle", "middle", "support", "bottom"}
        
        # Check for invalid roles
        invalid_roles = set(player.role_preferences.keys()) - valid_roles
        if invalid_roles:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                issue_type="invalid_data",
                message=f"Invalid roles in preferences: {invalid_roles}",
                context={"player_name": player.name, "invalid_roles": list(invalid_roles)}
            ))
        
        # Check preference values
        for role, preference in player.role_preferences.items():
            if not 1 <= preference <= 5:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="invalid_data",
                    message=f"Invalid preference value for {role}: {preference} (should be 1-5)",
                    context={"player_name": player.name, "role": role, "preference": preference}
                ))
        
        return issues
    
    def _validate_performance_cache(self, player: Player) -> List[ValidationIssue]:
        """Validate performance cache data."""
        issues = []
        
        for role, cache_data in player.performance_cache.items():
            if not isinstance(cache_data, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    issue_type="invalid_data",
                    message=f"Performance cache for {role} is not a dictionary",
                    context={"player_name": player.name, "role": role}
                ))
                continue
            
            # Validate cache structure
            if 'last_updated' in cache_data:
                try:
                    if isinstance(cache_data['last_updated'], str):
                        datetime.fromisoformat(cache_data['last_updated'].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        issue_type="invalid_data",
                        message=f"Invalid timestamp in performance cache for {role}",
                        context={"player_name": player.name, "role": role}
                    ))
        
        return issues
    
    def _detect_statistical_outliers(self, 
                                   performance_data: List[PerformanceMetrics],
                                   context: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect statistical outliers in performance data."""
        anomalies = []
        
        # Extract numeric values for key metrics
        metrics = {
            'win_rate': [p.win_rate for p in performance_data],
            'avg_kda': [p.avg_kda for p in performance_data],
            'avg_cs_per_min': [p.avg_cs_per_min for p in performance_data],
            'avg_vision_score': [p.avg_vision_score for p in performance_data]
        }
        
        for metric_name, values in metrics.items():
            if len(values) < self.min_sample_size:
                continue
            
            # Calculate statistical measures
            mean_val = statistics.mean(values)
            stdev_val = statistics.stdev(values) if len(values) > 1 else 0
            
            if stdev_val == 0:
                continue
            
            # Z-score outlier detection
            for i, value in enumerate(values):
                z_score = abs(value - mean_val) / stdev_val
                
                if z_score > self.outlier_threshold:
                    anomalies.append(AnomalyDetection(
                        anomaly_type=AnomalyType.STATISTICAL_OUTLIER,
                        severity=ValidationSeverity.WARNING if z_score < 4.0 else ValidationSeverity.ERROR,
                        description=f"Statistical outlier detected in {metric_name}",
                        affected_data={
                            "metric": metric_name,
                            "value": value,
                            "index": i,
                            "context": context
                        },
                        statistical_measures={
                            "z_score": z_score,
                            "mean": mean_val,
                            "std_dev": stdev_val,
                            "threshold": self.outlier_threshold
                        },
                        confidence=min(1.0, z_score / 5.0),
                        explanation=f"Value {value:.3f} is {z_score:.2f} standard deviations from mean {mean_val:.3f}"
                    ))
        
        return anomalies
    
    def _detect_performance_changes(self, 
                                  performance_data: List[PerformanceMetrics],
                                  context: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect significant performance spikes or drops."""
        anomalies = []
        
        if len(performance_data) < 3:
            return anomalies
        
        # Analyze trends in key metrics
        metrics = {
            'win_rate': [p.win_rate for p in performance_data],
            'avg_kda': [p.avg_kda for p in performance_data]
        }
        
        for metric_name, values in metrics.items():
            # Calculate moving averages to detect changes
            window_size = min(5, len(values) // 2)
            if window_size < 2:
                continue
            
            for i in range(window_size, len(values)):
                recent_avg = statistics.mean(values[i-window_size:i])
                current_value = values[i]
                
                if recent_avg == 0:
                    continue
                
                change_ratio = (current_value - recent_avg) / recent_avg
                
                # Detect significant spikes
                if change_ratio > 0.5:  # 50% improvement
                    anomalies.append(AnomalyDetection(
                        anomaly_type=AnomalyType.PERFORMANCE_SPIKE,
                        severity=ValidationSeverity.INFO,
                        description=f"Performance spike detected in {metric_name}",
                        affected_data={
                            "metric": metric_name,
                            "current_value": current_value,
                            "recent_average": recent_avg,
                            "index": i,
                            "context": context
                        },
                        statistical_measures={
                            "change_ratio": change_ratio,
                            "improvement_percentage": change_ratio * 100
                        },
                        confidence=min(1.0, abs(change_ratio)),
                        explanation=f"Current {metric_name} ({current_value:.3f}) is {change_ratio*100:.1f}% higher than recent average ({recent_avg:.3f})"
                    ))
                
                # Detect significant drops
                elif change_ratio < -0.3:  # 30% decline
                    anomalies.append(AnomalyDetection(
                        anomaly_type=AnomalyType.PERFORMANCE_DROP,
                        severity=ValidationSeverity.WARNING,
                        description=f"Performance drop detected in {metric_name}",
                        affected_data={
                            "metric": metric_name,
                            "current_value": current_value,
                            "recent_average": recent_avg,
                            "index": i,
                            "context": context
                        },
                        statistical_measures={
                            "change_ratio": change_ratio,
                            "decline_percentage": abs(change_ratio) * 100
                        },
                        confidence=min(1.0, abs(change_ratio)),
                        explanation=f"Current {metric_name} ({current_value:.3f}) is {abs(change_ratio)*100:.1f}% lower than recent average ({recent_avg:.3f})"
                    ))
        
        return anomalies
    
    def _detect_temporal_anomalies(self, 
                                 performance_data: List[PerformanceMetrics],
                                 context: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect temporal anomalies in performance data."""
        anomalies = []
        
        # Check for unusual patterns in games played
        games_played = [p.games_played for p in performance_data]
        
        if len(games_played) >= 3:
            # Detect sudden spikes in activity
            for i in range(1, len(games_played)):
                if games_played[i] > games_played[i-1] * 3:  # 3x increase
                    anomalies.append(AnomalyDetection(
                        anomaly_type=AnomalyType.TEMPORAL_ANOMALY,
                        severity=ValidationSeverity.INFO,
                        description="Sudden increase in game activity detected",
                        affected_data={
                            "previous_games": games_played[i-1],
                            "current_games": games_played[i],
                            "index": i,
                            "context": context
                        },
                        statistical_measures={
                            "activity_ratio": games_played[i] / max(games_played[i-1], 1)
                        },
                        confidence=0.7,
                        explanation=f"Games played increased from {games_played[i-1]} to {games_played[i]}"
                    ))
        
        return anomalies
    
    def _detect_champion_anomalies(self, 
                                 performance_data: List[PerformanceMetrics],
                                 context: Dict[str, Any]) -> List[AnomalyDetection]:
        """Detect champion-specific anomalies."""
        anomalies = []
        
        # This would be implemented with champion-specific data
        # For now, return empty list as we don't have champion context in PerformanceMetrics
        
        return anomalies
    
    def _calculate_completeness_score(self, matches: List[Match], players: List[Player]) -> float:
        """Calculate data completeness score."""
        if not matches and not players:
            return 0.0
        
        total_fields = 0
        complete_fields = 0
        
        # Check match completeness
        for match in matches:
            total_fields += 10  # Key match fields
            if match.match_id: complete_fields += 1
            if match.game_duration > 0: complete_fields += 1
            if match.game_creation > 0: complete_fields += 1
            if match.game_end_timestamp > 0: complete_fields += 1
            if match.queue_id > 0: complete_fields += 1
            if match.map_id > 0: complete_fields += 1
            if match.participants: complete_fields += 1
            if match.winning_team > 0: complete_fields += 1
            if match.game_mode: complete_fields += 1
            if match.game_version: complete_fields += 1
        
        # Check player completeness
        for player in players:
            total_fields += 5  # Key player fields
            if player.name: complete_fields += 1
            if player.summoner_name: complete_fields += 1
            if player.puuid: complete_fields += 1
            if player.role_preferences: complete_fields += 1
            if player.champion_masteries: complete_fields += 1
        
        return complete_fields / max(total_fields, 1)
    
    def _calculate_consistency_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate data consistency score based on validation issues."""
        if not issues:
            return 1.0
        
        # Weight issues by severity
        severity_weights = {
            ValidationSeverity.INFO: 0.1,
            ValidationSeverity.WARNING: 0.3,
            ValidationSeverity.ERROR: 0.7,
            ValidationSeverity.CRITICAL: 1.0
        }
        
        consistency_issues = [i for i in issues if "inconsistency" in i.issue_type]
        if not consistency_issues:
            return 1.0
        
        total_weight = sum(severity_weights[issue.severity] for issue in consistency_issues)
        max_possible_weight = len(consistency_issues) * 1.0
        
        return max(0.0, 1.0 - (total_weight / max_possible_weight))
    
    def _calculate_accuracy_score(self, issues: List[ValidationIssue]) -> float:
        """Calculate data accuracy score based on validation issues."""
        if not issues:
            return 1.0
        
        # Weight issues by severity
        severity_weights = {
            ValidationSeverity.INFO: 0.05,
            ValidationSeverity.WARNING: 0.2,
            ValidationSeverity.ERROR: 0.5,
            ValidationSeverity.CRITICAL: 1.0
        }
        
        accuracy_issues = [i for i in issues if i.issue_type in ["invalid_data", "data_anomaly"]]
        if not accuracy_issues:
            return 1.0
        
        total_weight = sum(severity_weights[issue.severity] for issue in accuracy_issues)
        max_possible_weight = len(accuracy_issues) * 1.0
        
        return max(0.0, 1.0 - (total_weight / max_possible_weight))
    
    def _calculate_timeliness_score(self, matches: List[Match], players: List[Player]) -> float:
        """Calculate data timeliness score."""
        if not matches and not players:
            return 0.0
        
        now = datetime.now()
        total_score = 0.0
        count = 0
        
        # Check match timeliness
        for match in matches:
            if match.last_updated:
                age_days = (now - match.last_updated).days
                # Score decreases with age, 1.0 for recent data, 0.0 for very old data
                score = max(0.0, 1.0 - (age_days / 365.0))  # 1 year decay
                total_score += score
                count += 1
        
        # Check player timeliness
        for player in players:
            if player.last_updated:
                age_days = (now - player.last_updated).days
                score = max(0.0, 1.0 - (age_days / 90.0))  # 3 month decay
                total_score += score
                count += 1
        
        return total_score / max(count, 1)
    
    def _get_expected_mastery_points(self, level: int) -> Optional[int]:
        """Get expected minimum mastery points for a given level."""
        level_thresholds = {
            1: 0,
            2: 1800,
            3: 4200,
            4: 8400,
            5: 12600,
            6: 21600,
            7: 21600  # Level 6 and 7 have same point requirement
        }
        return level_thresholds.get(level)
    
    def _generate_summary_statistics(self, 
                                   matches: List[Match],
                                   players: List[Player],
                                   issues: List[ValidationIssue],
                                   anomalies: List[AnomalyDetection]) -> Dict[str, Any]:
        """Generate summary statistics for the quality report."""
        return {
            "data_overview": {
                "total_matches": len(matches),
                "total_players": len(players),
                "assessment_date": datetime.now().isoformat()
            },
            "validation_summary": {
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if i.severity == ValidationSeverity.CRITICAL]),
                "error_issues": len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
                "warning_issues": len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
                "info_issues": len([i for i in issues if i.severity == ValidationSeverity.INFO])
            },
            "anomaly_summary": {
                "total_anomalies": len(anomalies),
                "outliers": len([a for a in anomalies if a.anomaly_type == AnomalyType.STATISTICAL_OUTLIER]),
                "performance_spikes": len([a for a in anomalies if a.anomaly_type == AnomalyType.PERFORMANCE_SPIKE]),
                "performance_drops": len([a for a in anomalies if a.anomaly_type == AnomalyType.PERFORMANCE_DROP]),
                "temporal_anomalies": len([a for a in anomalies if a.anomaly_type == AnomalyType.TEMPORAL_ANOMALY])
            }
        }
    
    def _generate_recommendations(self, 
                                quality_score: DataQualityScore,
                                issues: List[ValidationIssue],
                                anomalies: List[AnomalyDetection]) -> List[str]:
        """Generate recommendations based on quality assessment."""
        recommendations = []
        
        # Overall quality recommendations
        if quality_score.overall_score < 0.7:
            recommendations.append("Overall data quality is below acceptable threshold. Consider data cleanup and validation improvements.")
        
        # Completeness recommendations
        if quality_score.completeness_score < 0.8:
            recommendations.append("Data completeness is low. Review data collection processes to ensure all required fields are captured.")
        
        # Consistency recommendations
        if quality_score.consistency_score < 0.8:
            recommendations.append("Data consistency issues detected. Implement stricter validation rules and data normalization procedures.")
        
        # Critical issue recommendations
        critical_issues = [i for i in issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical data issues immediately to prevent system failures.")
        
        # Anomaly recommendations
        if len(anomalies) > 10:
            recommendations.append("High number of anomalies detected. Consider reviewing data collection and processing pipelines.")
        
        # Performance anomaly recommendations
        performance_anomalies = [a for a in anomalies if a.anomaly_type in [AnomalyType.PERFORMANCE_SPIKE, AnomalyType.PERFORMANCE_DROP]]
        if performance_anomalies:
            recommendations.append("Performance anomalies detected. Review player performance data for accuracy and investigate unusual patterns.")
        
        return recommendations