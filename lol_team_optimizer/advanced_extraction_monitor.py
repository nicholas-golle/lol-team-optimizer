"""
Advanced Extraction Monitoring and Error Handling

This module provides comprehensive monitoring, error handling, and recovery mechanisms
for match extraction operations. It includes per-player progress tracking, API rate
limit monitoring, retry logic with exponential backoff, data quality validation,
performance metrics, and extraction cancellation with proper cleanup.
"""

import logging
import json
import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import requests
from collections import defaultdict, deque

from .models import Player
from .riot_client import RiotAPIClient
from .config import Config


class ExtractionStatus(Enum):
    """Enumeration of extraction operation statuses."""
    NOT_STARTED = "not_started"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class APIRateLimit:
    """API rate limit tracking information."""
    endpoint: str
    requests_made: int = 0
    requests_limit: int = 120
    window_start: datetime = field(default_factory=datetime.now)
    window_duration: int = 120  # seconds
    current_delay: float = 1.0
    throttled: bool = False
    throttle_until: Optional[datetime] = None


@dataclass
class ExtractionError:
    """Detailed error information for extraction operations."""
    error_id: str
    timestamp: datetime
    operation_id: str
    player_name: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    retry_count: int = 0
    max_retries: int = 3
    resolved: bool = False
    resolution_message: Optional[str] = None


@dataclass
class PlayerProgress:
    """Detailed progress tracking for individual players."""
    player_name: str
    status: ExtractionStatus
    matches_requested: int = 0
    matches_extracted: int = 0
    matches_failed: int = 0
    api_calls_made: int = 0
    api_calls_failed: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_step: str = ""
    error_count: int = 0
    last_error: Optional[ExtractionError] = None
    extraction_rate: float = 0.0  # matches per minute
    estimated_completion: Optional[datetime] = None


@dataclass
class ExtractionMetrics:
    """Performance metrics for extraction operations."""
    operation_id: str
    total_players: int
    completed_players: int
    failed_players: int
    total_matches_extracted: int
    total_api_calls: int
    total_errors: int
    average_extraction_rate: float
    peak_extraction_rate: float
    total_duration: Optional[float] = None
    efficiency_score: float = 0.0
    data_quality_score: float = 0.0


@dataclass
class DataQualityCheck:
    """Data quality validation result."""
    check_name: str
    passed: bool
    message: str
    severity: ErrorSeverity
    data_sample: Optional[Dict[str, Any]] = None


class APIRateLimitMonitor:
    """Monitors and manages API rate limits with automatic throttling."""
    
    def __init__(self, config: Config):
        """Initialize the rate limit monitor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rate_limits: Dict[str, APIRateLimit] = {}
        self.global_throttle = False
        self.global_throttle_until: Optional[datetime] = None
        self.request_history = deque(maxlen=1000)  # Keep last 1000 requests
        
    def can_make_request(self, endpoint: str = "default") -> bool:
        """Check if a request can be made without exceeding rate limits."""
        now = datetime.now()
        
        # Check global throttle
        if self.global_throttle and self.global_throttle_until:
            if now < self.global_throttle_until:
                return False
            else:
                self.global_throttle = False
                self.global_throttle_until = None
        
        # Get or create rate limit tracker for endpoint
        if endpoint not in self.rate_limits:
            self.rate_limits[endpoint] = APIRateLimit(endpoint=endpoint)
        
        rate_limit = self.rate_limits[endpoint]
        
        # Check endpoint-specific throttle
        if rate_limit.throttled and rate_limit.throttle_until:
            if now < rate_limit.throttle_until:
                return False
            else:
                rate_limit.throttled = False
                rate_limit.throttle_until = None
        
        # Check if we're within rate limits
        window_elapsed = (now - rate_limit.window_start).total_seconds()
        if window_elapsed >= rate_limit.window_duration:
            # Reset window
            rate_limit.requests_made = 0
            rate_limit.window_start = now
        
        return rate_limit.requests_made < rate_limit.requests_limit
    
    def record_request(self, endpoint: str = "default", success: bool = True) -> None:
        """Record a request and update rate limit tracking."""
        now = datetime.now()
        
        if endpoint not in self.rate_limits:
            self.rate_limits[endpoint] = APIRateLimit(endpoint=endpoint)
        
        rate_limit = self.rate_limits[endpoint]
        rate_limit.requests_made += 1
        
        # Record in history
        self.request_history.append({
            'timestamp': now,
            'endpoint': endpoint,
            'success': success
        })
        
        self.logger.debug(f"Recorded request to {endpoint}: {rate_limit.requests_made}/{rate_limit.requests_limit}")
    
    def handle_rate_limit_response(self, endpoint: str, response: requests.Response) -> None:
        """Handle rate limit response from API."""
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                throttle_duration = int(retry_after)
            else:
                throttle_duration = 60  # Default 1 minute
            
            throttle_until = datetime.now() + timedelta(seconds=throttle_duration)
            
            # Create rate limit tracker if it doesn't exist
            if endpoint not in self.rate_limits:
                self.rate_limits[endpoint] = APIRateLimit(endpoint=endpoint)
            
            self.rate_limits[endpoint].throttled = True
            self.rate_limits[endpoint].throttle_until = throttle_until
            
            self.logger.warning(f"Rate limited on {endpoint}, throttled until {throttle_until}")
    
    def get_wait_time(self, endpoint: str = "default") -> float:
        """Get the time to wait before making the next request."""
        if not self.can_make_request(endpoint):
            now = datetime.now()
            
            # Check global throttle
            if self.global_throttle and self.global_throttle_until:
                return (self.global_throttle_until - now).total_seconds()
            
            # Check endpoint throttle
            if endpoint in self.rate_limits:
                rate_limit = self.rate_limits[endpoint]
                if rate_limit.throttled and rate_limit.throttle_until:
                    return (rate_limit.throttle_until - now).total_seconds()
                
                # Calculate wait time based on rate limit window
                window_elapsed = (now - rate_limit.window_start).total_seconds()
                remaining_window = rate_limit.window_duration - window_elapsed
                if remaining_window > 0:
                    return remaining_window
        
        return 0.0
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current rate limit metrics."""
        now = datetime.now()
        metrics = {
            'global_throttled': self.global_throttle,
            'endpoints': {},
            'recent_requests': len([r for r in self.request_history 
                                  if (now - r['timestamp']).total_seconds() < 300])  # Last 5 minutes
        }
        
        for endpoint, rate_limit in self.rate_limits.items():
            window_elapsed = (now - rate_limit.window_start).total_seconds()
            metrics['endpoints'][endpoint] = {
                'requests_made': rate_limit.requests_made,
                'requests_limit': rate_limit.requests_limit,
                'window_elapsed': window_elapsed,
                'throttled': rate_limit.throttled,
                'can_make_request': self.can_make_request(endpoint)
            }
        
        return metrics


class ExtractionRetryManager:
    """Manages retry logic with exponential backoff for failed extractions."""
    
    def __init__(self, config: Config):
        """Initialize the retry manager."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.retry_attempts: Dict[str, int] = {}
        self.backoff_delays: Dict[str, float] = {}
        self.max_retries = config.max_retries
        self.base_delay = 1.0
        self.max_delay = 300.0  # 5 minutes
        self.backoff_multiplier = 2.0
    
    def should_retry(self, error: ExtractionError) -> bool:
        """Determine if an operation should be retried."""
        # Don't retry critical errors or if max retries exceeded
        if error.severity == ErrorSeverity.CRITICAL:
            return False
        
        if error.retry_count >= error.max_retries:
            return False
        
        # Don't retry certain error types
        non_retryable_errors = [
            "invalid_api_key",
            "forbidden",
            "not_found",
            "invalid_summoner_name"
        ]
        
        if any(err_type in error.error_type.lower() for err_type in non_retryable_errors):
            return False
        
        return True
    
    def get_retry_delay(self, error_id: str, attempt: int) -> float:
        """Calculate retry delay with exponential backoff."""
        if error_id not in self.backoff_delays:
            self.backoff_delays[error_id] = self.base_delay
        
        delay = self.backoff_delays[error_id] * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        import random
        jitter = random.uniform(0.8, 1.2)
        delay *= jitter
        
        self.backoff_delays[error_id] = delay
        return delay
    
    def record_retry_attempt(self, error_id: str) -> None:
        """Record a retry attempt."""
        if error_id not in self.retry_attempts:
            self.retry_attempts[error_id] = 0
        
        self.retry_attempts[error_id] += 1
        self.logger.info(f"Retry attempt {self.retry_attempts[error_id]} for error {error_id}")
    
    def reset_retry_state(self, error_id: str) -> None:
        """Reset retry state for successful operation."""
        if error_id in self.retry_attempts:
            del self.retry_attempts[error_id]
        if error_id in self.backoff_delays:
            del self.backoff_delays[error_id]


class DataQualityValidator:
    """Validates extraction data quality and integrity."""
    
    def __init__(self, config: Config):
        """Initialize the data quality validator."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._load_validation_rules()
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load data validation rules."""
        return {
            'match_data': {
                'required_fields': [
                    'gameId', 'gameCreation', 'gameDuration', 'queueId',
                    'participants', 'teams'
                ],
                'min_game_duration': 180,  # 3 minutes
                'max_game_duration': 7200,  # 2 hours
                'expected_participants': 10
            },
            'participant_data': {
                'required_fields': [
                    'championId', 'spell1Id', 'spell2Id', 'teamId',
                    'stats'
                ],
                'valid_team_ids': [100, 200]
            },
            'timeline_data': {
                'required_fields': ['frames'],
                'min_frames': 1
            }
        }
    
    def validate_match_data(self, match_data: Dict[str, Any]) -> List[DataQualityCheck]:
        """Validate match data quality."""
        checks = []
        rules = self.validation_rules['match_data']
        
        # Check required fields
        missing_fields = []
        for field in rules['required_fields']:
            if field not in match_data:
                missing_fields.append(field)
        
        if missing_fields:
            checks.append(DataQualityCheck(
                check_name="required_fields",
                passed=False,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                severity=ErrorSeverity.HIGH,
                data_sample={'missing_fields': missing_fields}
            ))
        else:
            checks.append(DataQualityCheck(
                check_name="required_fields",
                passed=True,
                message="All required fields present",
                severity=ErrorSeverity.LOW
            ))
        
        # Check game duration
        if 'gameDuration' in match_data:
            duration = match_data['gameDuration']
            if duration < rules['min_game_duration'] or duration > rules['max_game_duration']:
                checks.append(DataQualityCheck(
                    check_name="game_duration",
                    passed=False,
                    message=f"Invalid game duration: {duration} seconds",
                    severity=ErrorSeverity.MEDIUM,
                    data_sample={'game_duration': duration}
                ))
            else:
                checks.append(DataQualityCheck(
                    check_name="game_duration",
                    passed=True,
                    message="Game duration within expected range",
                    severity=ErrorSeverity.LOW
                ))
        
        # Check participant count
        if 'participants' in match_data:
            participant_count = len(match_data['participants'])
            if participant_count != rules['expected_participants']:
                checks.append(DataQualityCheck(
                    check_name="participant_count",
                    passed=False,
                    message=f"Unexpected participant count: {participant_count}",
                    severity=ErrorSeverity.HIGH,
                    data_sample={'participant_count': participant_count}
                ))
            else:
                checks.append(DataQualityCheck(
                    check_name="participant_count",
                    passed=True,
                    message="Correct participant count",
                    severity=ErrorSeverity.LOW
                ))
        
        return checks
    
    def validate_participant_data(self, participant_data: Dict[str, Any]) -> List[DataQualityCheck]:
        """Validate participant data quality."""
        checks = []
        rules = self.validation_rules['participant_data']
        
        # Check required fields
        missing_fields = []
        for field in rules['required_fields']:
            if field not in participant_data:
                missing_fields.append(field)
        
        if missing_fields:
            checks.append(DataQualityCheck(
                check_name="participant_required_fields",
                passed=False,
                message=f"Missing participant fields: {', '.join(missing_fields)}",
                severity=ErrorSeverity.HIGH,
                data_sample={'missing_fields': missing_fields}
            ))
        else:
            checks.append(DataQualityCheck(
                check_name="participant_required_fields",
                passed=True,
                message="All participant fields present",
                severity=ErrorSeverity.LOW
            ))
        
        # Check team ID
        if 'teamId' in participant_data:
            team_id = participant_data['teamId']
            if team_id not in rules['valid_team_ids']:
                checks.append(DataQualityCheck(
                    check_name="team_id",
                    passed=False,
                    message=f"Invalid team ID: {team_id}",
                    severity=ErrorSeverity.MEDIUM,
                    data_sample={'team_id': team_id}
                ))
            else:
                checks.append(DataQualityCheck(
                    check_name="team_id",
                    passed=True,
                    message="Valid team ID",
                    severity=ErrorSeverity.LOW
                ))
        
        return checks
    
    def calculate_quality_score(self, checks: List[DataQualityCheck]) -> float:
        """Calculate overall data quality score from validation checks."""
        if not checks:
            return 0.0
        
        total_weight = 0
        weighted_score = 0
        
        severity_weights = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        
        for check in checks:
            weight = severity_weights[check.severity]
            total_weight += weight
            if check.passed:
                weighted_score += weight
        
        return (weighted_score / total_weight) * 100 if total_weight > 0 else 0.0


class PerformanceMetricsCollector:
    """Collects and analyzes extraction performance metrics."""
    
    def __init__(self, config: Config):
        """Initialize the performance metrics collector."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[ExtractionMetrics] = []
        self.real_time_metrics: Dict[str, Any] = {}
        
    def start_operation_tracking(self, operation_id: str, total_players: int) -> None:
        """Start tracking metrics for an extraction operation."""
        self.real_time_metrics[operation_id] = {
            'start_time': datetime.now(),
            'total_players': total_players,
            'completed_players': 0,
            'failed_players': 0,
            'total_matches_extracted': 0,
            'total_api_calls': 0,
            'total_errors': 0,
            'extraction_rates': deque(maxlen=100),  # Keep last 100 rate measurements
            'quality_scores': deque(maxlen=100)
        }
    
    def update_player_metrics(self, operation_id: str, player_progress: PlayerProgress) -> None:
        """Update metrics based on player progress."""
        if operation_id not in self.real_time_metrics:
            return
        
        metrics = self.real_time_metrics[operation_id]
        
        if player_progress.status == ExtractionStatus.COMPLETED:
            metrics['completed_players'] += 1
            metrics['total_matches_extracted'] += player_progress.matches_extracted
        elif player_progress.status == ExtractionStatus.FAILED:
            metrics['failed_players'] += 1
        
        metrics['total_api_calls'] += player_progress.api_calls_made
        metrics['total_errors'] += player_progress.error_count
        
        # Record extraction rate
        if player_progress.extraction_rate > 0:
            metrics['extraction_rates'].append(player_progress.extraction_rate)
    
    def calculate_efficiency_score(self, operation_id: str) -> float:
        """Calculate extraction efficiency score."""
        if operation_id not in self.real_time_metrics:
            return 0.0
        
        metrics = self.real_time_metrics[operation_id]
        
        # Factors for efficiency calculation
        success_rate = metrics['completed_players'] / max(metrics['total_players'], 1)
        error_rate = metrics['total_errors'] / max(metrics['total_api_calls'], 1)
        
        # Average extraction rate
        rates = list(metrics['extraction_rates'])
        avg_rate = sum(rates) / len(rates) if rates else 0
        
        # Normalize rate (assuming 10 matches/minute is good)
        rate_score = min(avg_rate / 10.0, 1.0)
        
        # Combined efficiency score
        efficiency = (success_rate * 0.4 + (1 - error_rate) * 0.3 + rate_score * 0.3) * 100
        return max(0, min(100, efficiency))
    
    def finalize_operation_metrics(self, operation_id: str) -> ExtractionMetrics:
        """Finalize and store metrics for completed operation."""
        if operation_id not in self.real_time_metrics:
            raise ValueError(f"No metrics found for operation {operation_id}")
        
        metrics_data = self.real_time_metrics[operation_id]
        end_time = datetime.now()
        duration = (end_time - metrics_data['start_time']).total_seconds()
        
        # Calculate final metrics
        rates = list(metrics_data['extraction_rates'])
        avg_rate = sum(rates) / len(rates) if rates else 0
        peak_rate = max(rates) if rates else 0
        
        quality_scores = list(metrics_data['quality_scores'])
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        final_metrics = ExtractionMetrics(
            operation_id=operation_id,
            total_players=metrics_data['total_players'],
            completed_players=metrics_data['completed_players'],
            failed_players=metrics_data['failed_players'],
            total_matches_extracted=metrics_data['total_matches_extracted'],
            total_api_calls=metrics_data['total_api_calls'],
            total_errors=metrics_data['total_errors'],
            average_extraction_rate=avg_rate,
            peak_extraction_rate=peak_rate,
            total_duration=duration,
            efficiency_score=self.calculate_efficiency_score(operation_id),
            data_quality_score=avg_quality
        )
        
        self.metrics_history.append(final_metrics)
        del self.real_time_metrics[operation_id]
        
        return final_metrics
    
    def get_optimization_suggestions(self, metrics: ExtractionMetrics) -> List[str]:
        """Generate optimization suggestions based on metrics."""
        suggestions = []
        
        if metrics.efficiency_score < 70:
            suggestions.append("Consider reducing batch size to improve success rate")
        
        if metrics.total_errors / max(metrics.total_api_calls, 1) > 0.1:
            suggestions.append("High error rate detected - check API key and network connectivity")
        
        if metrics.average_extraction_rate < 5:
            suggestions.append("Low extraction rate - consider increasing rate limit delay")
        
        if metrics.data_quality_score < 80:
            suggestions.append("Data quality issues detected - enable stricter validation")
        
        if metrics.failed_players / max(metrics.total_players, 1) > 0.2:
            suggestions.append("High player failure rate - check player data validity")
        
        return suggestions


class AdvancedExtractionMonitor:
    """
    Advanced monitoring system for match extraction operations.
    
    Provides comprehensive monitoring, error handling, retry logic, data quality
    validation, performance metrics, and extraction management capabilities.
    """
    
    def __init__(self, config: Config, riot_client: RiotAPIClient):
        """Initialize the advanced extraction monitor."""
        self.config = config
        self.riot_client = riot_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.rate_monitor = APIRateLimitMonitor(config)
        self.retry_manager = ExtractionRetryManager(config)
        self.quality_validator = DataQualityValidator(config)
        self.metrics_collector = PerformanceMetricsCollector(config)
        
        # State tracking
        self.active_operations: Dict[str, Dict[str, PlayerProgress]] = {}
        self.operation_errors: Dict[str, List[ExtractionError]] = {}
        self.cancellation_events: Dict[str, threading.Event] = {}
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        
    def start_monitoring(self) -> None:
        """Start the monitoring background thread."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()
            self.logger.info("Started extraction monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop the monitoring background thread."""
        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        self.logger.info("Stopped extraction monitoring")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in background thread."""
        while self.monitoring_active:
            try:
                # Update real-time metrics
                self._update_real_time_metrics()
                
                # Check for stalled operations
                self._check_stalled_operations()
                
                # Process retry queue
                self._process_retry_queue()
                
                # Cleanup completed operations
                self._cleanup_completed_operations()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer on error
    
    def create_extraction_operation(self, operation_id: str, players: List[Player]) -> None:
        """Create a new extraction operation for monitoring."""
        self.active_operations[operation_id] = {}
        self.operation_errors[operation_id] = []
        self.cancellation_events[operation_id] = threading.Event()
        
        # Initialize player progress tracking
        for player in players:
            self.active_operations[operation_id][player.name] = PlayerProgress(
                player_name=player.name,
                status=ExtractionStatus.NOT_STARTED
            )
        
        # Start metrics tracking
        self.metrics_collector.start_operation_tracking(operation_id, len(players))
        
        self.logger.info(f"Created extraction operation {operation_id} for {len(players)} players")
    
    def update_player_progress(self, operation_id: str, player_name: str, 
                             progress_update: Dict[str, Any]) -> None:
        """Update progress for a specific player."""
        if operation_id not in self.active_operations:
            return
        
        if player_name not in self.active_operations[operation_id]:
            return
        
        progress = self.active_operations[operation_id][player_name]
        
        # Update progress fields
        for key, value in progress_update.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        
        # Update metrics
        self.metrics_collector.update_player_metrics(operation_id, progress)
        
        self.logger.debug(f"Updated progress for {player_name} in operation {operation_id}")
    
    def record_extraction_error(self, operation_id: str, player_name: str, 
                              error_type: str, error_message: str, 
                              severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> str:
        """Record an extraction error."""
        error_id = str(uuid.uuid4())
        error = ExtractionError(
            error_id=error_id,
            timestamp=datetime.now(),
            operation_id=operation_id,
            player_name=player_name,
            error_type=error_type,
            error_message=error_message,
            severity=severity
        )
        
        if operation_id not in self.operation_errors:
            self.operation_errors[operation_id] = []
        
        self.operation_errors[operation_id].append(error)
        
        # Update player progress
        if operation_id in self.active_operations and player_name in self.active_operations[operation_id]:
            progress = self.active_operations[operation_id][player_name]
            progress.error_count += 1
            progress.last_error = error
        
        self.logger.error(f"Recorded {severity.value} error {error_id}: {error_message}")
        return error_id
    
    def should_cancel_operation(self, operation_id: str) -> bool:
        """Check if an operation should be cancelled."""
        if operation_id not in self.cancellation_events:
            return False
        
        return self.cancellation_events[operation_id].is_set()
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an extraction operation."""
        if operation_id not in self.cancellation_events:
            return False
        
        self.cancellation_events[operation_id].set()
        
        # Update all player statuses
        if operation_id in self.active_operations:
            for progress in self.active_operations[operation_id].values():
                if progress.status in [ExtractionStatus.RUNNING, ExtractionStatus.RETRYING]:
                    progress.status = ExtractionStatus.CANCELLED
                    progress.end_time = datetime.now()
        
        self.logger.info(f"Cancelled extraction operation {operation_id}")
        return True
    
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get comprehensive status for an extraction operation."""
        if operation_id not in self.active_operations:
            return {'error': 'Operation not found'}
        
        players_progress = self.active_operations[operation_id]
        errors = self.operation_errors.get(operation_id, [])
        
        # Calculate overall statistics
        total_players = len(players_progress)
        completed_players = sum(1 for p in players_progress.values() 
                              if p.status == ExtractionStatus.COMPLETED)
        failed_players = sum(1 for p in players_progress.values() 
                           if p.status == ExtractionStatus.FAILED)
        running_players = sum(1 for p in players_progress.values() 
                            if p.status == ExtractionStatus.RUNNING)
        
        total_matches = sum(p.matches_extracted for p in players_progress.values())
        total_errors = len(errors)
        
        # Calculate progress percentage
        progress_percentage = (completed_players / total_players * 100) if total_players > 0 else 0
        
        return {
            'operation_id': operation_id,
            'total_players': total_players,
            'completed_players': completed_players,
            'failed_players': failed_players,
            'running_players': running_players,
            'progress_percentage': progress_percentage,
            'total_matches_extracted': total_matches,
            'total_errors': total_errors,
            'players': {name: {
                'status': progress.status.value,
                'matches_extracted': progress.matches_extracted,
                'matches_failed': progress.matches_failed,
                'error_count': progress.error_count,
                'extraction_rate': progress.extraction_rate,
                'current_step': progress.current_step
            } for name, progress in players_progress.items()},
            'recent_errors': [
                {
                    'error_id': error.error_id,
                    'timestamp': error.timestamp.isoformat(),
                    'player_name': error.player_name,
                    'error_type': error.error_type,
                    'error_message': error.error_message,
                    'severity': error.severity.value
                }
                for error in errors[-10:]  # Last 10 errors
            ],
            'rate_limit_status': self.rate_monitor.get_current_metrics(),
            'can_cancel': operation_id in self.cancellation_events
        }
    
    def get_performance_metrics(self, operation_id: str) -> Optional[ExtractionMetrics]:
        """Get performance metrics for an operation."""
        # Check if operation is completed
        if operation_id not in self.active_operations:
            # Look in metrics history
            for metrics in self.metrics_collector.metrics_history:
                if metrics.operation_id == operation_id:
                    return metrics
            return None
        
        # For active operations, return current metrics
        if operation_id in self.metrics_collector.real_time_metrics:
            metrics_data = self.metrics_collector.real_time_metrics[operation_id]
            return ExtractionMetrics(
                operation_id=operation_id,
                total_players=metrics_data['total_players'],
                completed_players=metrics_data['completed_players'],
                failed_players=metrics_data['failed_players'],
                total_matches_extracted=metrics_data['total_matches_extracted'],
                total_api_calls=metrics_data['total_api_calls'],
                total_errors=metrics_data['total_errors'],
                average_extraction_rate=sum(metrics_data['extraction_rates']) / len(metrics_data['extraction_rates']) if metrics_data['extraction_rates'] else 0,
                peak_extraction_rate=max(metrics_data['extraction_rates']) if metrics_data['extraction_rates'] else 0,
                efficiency_score=self.metrics_collector.calculate_efficiency_score(operation_id),
                data_quality_score=sum(metrics_data['quality_scores']) / len(metrics_data['quality_scores']) if metrics_data['quality_scores'] else 0
            )
        
        return None
    
    def _update_real_time_metrics(self) -> None:
        """Update real-time metrics for all active operations."""
        for operation_id, players_progress in self.active_operations.items():
            for progress in players_progress.values():
                # Calculate extraction rate
                if progress.start_time and progress.matches_extracted > 0:
                    elapsed = (datetime.now() - progress.start_time).total_seconds() / 60  # minutes
                    if elapsed > 0:
                        progress.extraction_rate = progress.matches_extracted / elapsed
                
                # Estimate completion time
                if progress.extraction_rate > 0 and progress.matches_requested > progress.matches_extracted:
                    remaining_matches = progress.matches_requested - progress.matches_extracted
                    remaining_minutes = remaining_matches / progress.extraction_rate
                    progress.estimated_completion = datetime.now() + timedelta(minutes=remaining_minutes)
    
    def _check_stalled_operations(self) -> None:
        """Check for stalled operations and handle them."""
        stall_threshold = timedelta(minutes=10)  # Consider stalled after 10 minutes of no progress
        
        for operation_id, players_progress in self.active_operations.items():
            for player_name, progress in players_progress.items():
                if progress.status == ExtractionStatus.RUNNING and progress.start_time:
                    time_since_start = datetime.now() - progress.start_time
                    if time_since_start > stall_threshold and progress.matches_extracted == 0:
                        self.logger.warning(f"Detected stalled operation for {player_name} in {operation_id}")
                        
                        # Record stall error
                        self.record_extraction_error(
                            operation_id, player_name, "stalled_operation",
                            f"Operation stalled for {time_since_start.total_seconds()/60:.1f} minutes",
                            ErrorSeverity.HIGH
                        )
    
    def _process_retry_queue(self) -> None:
        """Process retry queue for failed operations."""
        for operation_id, errors in self.operation_errors.items():
            for error in errors:
                if not error.resolved and self.retry_manager.should_retry(error):
                    delay = self.retry_manager.get_retry_delay(error.error_id, error.retry_count)
                    
                    # Check if enough time has passed for retry
                    time_since_error = (datetime.now() - error.timestamp).total_seconds()
                    if time_since_error >= delay:
                        self.logger.info(f"Retrying operation for error {error.error_id}")
                        error.retry_count += 1
                        self.retry_manager.record_retry_attempt(error.error_id)
                        
                        # Update player status to retrying
                        if (operation_id in self.active_operations and 
                            error.player_name in self.active_operations[operation_id]):
                            progress = self.active_operations[operation_id][error.player_name]
                            progress.status = ExtractionStatus.RETRYING
    
    def _cleanup_completed_operations(self) -> None:
        """Clean up completed operations from active tracking."""
        completed_operations = []
        
        for operation_id, players_progress in self.active_operations.items():
            all_completed = all(
                progress.status in [ExtractionStatus.COMPLETED, ExtractionStatus.FAILED, ExtractionStatus.CANCELLED]
                for progress in players_progress.values()
            )
            
            if all_completed:
                completed_operations.append(operation_id)
        
        for operation_id in completed_operations:
            # Finalize metrics
            try:
                final_metrics = self.metrics_collector.finalize_operation_metrics(operation_id)
                self.logger.info(f"Finalized metrics for operation {operation_id}: "
                               f"efficiency={final_metrics.efficiency_score:.1f}%, "
                               f"quality={final_metrics.data_quality_score:.1f}%")
            except Exception as e:
                self.logger.error(f"Error finalizing metrics for {operation_id}: {e}")
            
            # Clean up tracking data
            del self.active_operations[operation_id]
            if operation_id in self.cancellation_events:
                del self.cancellation_events[operation_id]
            
            self.logger.info(f"Cleaned up completed operation {operation_id}")