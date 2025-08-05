"""
Historical Analytics Engine for the League of Legends Team Optimizer.

This module provides the core analytics processing engine that transforms raw
historical match data into meaningful insights, performance analysis, and
comparative analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from .models import Match, MatchParticipant
from .analytics_models import (
    AnalyticsFilters, PlayerAnalytics, ChampionPerformanceMetrics,
    PerformanceMetrics, PerformanceDelta, TrendAnalysis, ComparativeRankings,
    DateRange, RecentFormMetrics, AnalyticsError, InsufficientDataError,
    TimeSeriesPoint
)
from .baseline_manager import BaselineManager, BaselineContext
from .statistical_analyzer import StatisticalAnalyzer, TrendAnalysisMethod
from .comparative_analyzer import (
    ComparativeAnalyzer, MultiPlayerComparison, PeerGroupAnalysis,
    RoleSpecificRanking, ChampionSpecificRanking
)
from .analytics_batch_processor import AnalyticsBatchProcessor
from .incremental_analytics_updater import IncrementalAnalyticsUpdater
from .query_optimizer import QueryOptimizer
from .config import Config


@dataclass
class ComparativeAnalytics:
    """Result of comparative analysis between multiple players."""
    
    players: List[str]  # PUUIDs
    comparison_metric: str
    player_values: Dict[str, float]  # puuid -> metric_value
    rankings: Dict[str, int]  # puuid -> rank (1-based)
    percentiles: Dict[str, float]  # puuid -> percentile
    statistical_significance: Optional[Dict[Tuple[str, str], float]] = None  # (puuid1, puuid2) -> p_value
    analysis_period: Optional[DateRange] = None
    sample_sizes: Dict[str, int] = field(default_factory=dict)  # puuid -> sample_size


class AnalyticsCacheManager:
    """Simple cache manager for analytics operations."""
    
    def __init__(self, max_cache_size: int = 1000):
        """Initialize cache manager."""
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.max_cache_size = max_cache_size
        self.cache_ttl_minutes = 30
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(minutes=self.cache_ttl_minutes):
                return value
            else:
                del self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Cache a value with timestamp."""
        # Simple LRU eviction if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (value, datetime.now())
    
    def invalidate(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]


class HistoricalAnalyticsEngine:
    """
    Main analytics engine for processing historical match data.
    
    Provides comprehensive analytics capabilities including player performance
    analysis, champion performance analysis, trend analysis, and comparative
    analysis across multiple players.
    """
    
    def __init__(self, config: Config, match_manager, baseline_manager: BaselineManager, 
                 cache_manager=None):
        """
        Initialize the historical analytics engine.
        
        Args:
            config: Configuration object
            match_manager: MatchManager instance for data access
            baseline_manager: BaselineManager for baseline calculations
            cache_manager: Optional AnalyticsCacheManager instance
        """
        self.config = config
        self.match_manager = match_manager
        self.baseline_manager = baseline_manager
        self.statistical_analyzer = StatisticalAnalyzer()
        self.comparative_analyzer = ComparativeAnalyzer(config, match_manager, baseline_manager)
        
        # Initialize cache manager
        if cache_manager:
            self.cache_manager = cache_manager
        else:
            from .analytics_cache_manager import AnalyticsCacheManager
            self.cache_manager = AnalyticsCacheManager(config)
        
        # Initialize optimization components
        self.batch_processor = AnalyticsBatchProcessor(config, self, match_manager)
        self.incremental_updater = IncrementalAnalyticsUpdater(
            config, self, match_manager, self.cache_manager
        )
        self.query_optimizer = QueryOptimizer(config, match_manager)
        
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.min_games_for_analysis = 5
        self.recent_form_window_days = 30
        self.trend_analysis_min_points = 10
    
    def analyze_player_performance(
        self,
        puuid: str,
        filters: Optional[AnalyticsFilters] = None
    ) -> PlayerAnalytics:
        """
        Analyze comprehensive performance for a player.
        
        Args:
            puuid: Player's PUUID
            filters: Optional filters to apply to analysis
            
        Returns:
            PlayerAnalytics object with comprehensive analysis
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If analysis fails
        """
        try:
            # Generate cache key
            cache_key = f"player_analytics_{puuid}_{hash(str(filters))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached player analytics for {puuid}")
                return cached_result
            
            # Get matches for the player
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < self.min_games_for_analysis:
                raise InsufficientDataError(
                    required_games=self.min_games_for_analysis,
                    available_games=len(matches),
                    context=f"player performance analysis for {puuid}"
                )
            
            # Determine analysis period
            if filters and filters.date_range:
                analysis_period = filters.date_range
            else:
                # Use date range from actual matches
                match_dates = [match.game_creation_datetime for match, _ in matches]
                analysis_period = DateRange(
                    start_date=min(match_dates),
                    end_date=max(match_dates)
                )
            
            # Calculate overall performance
            overall_performance = self._calculate_performance_metrics(matches)
            
            # Calculate role-specific performance
            role_performance = self._calculate_role_performance(matches)
            
            # Calculate champion-specific performance
            champion_performance = self._calculate_champion_performance(matches, puuid)
            
            # Calculate trend analysis
            trend_analysis = self._calculate_trend_analysis(matches, puuid)
            
            # Calculate comparative rankings (simplified for now)
            comparative_rankings = self._calculate_comparative_rankings(puuid, overall_performance)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(matches, overall_performance)
            
            # Get player name from first match
            player_name = matches[0][1].summoner_name if matches else "Unknown"
            
            analytics = PlayerAnalytics(
                puuid=puuid,
                player_name=player_name,
                analysis_period=analysis_period,
                overall_performance=overall_performance,
                role_performance=role_performance,
                champion_performance=champion_performance,
                trend_analysis=trend_analysis,
                comparative_rankings=comparative_rankings,
                confidence_scores=confidence_scores
            )
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, analytics)
            
            self.logger.info(f"Analyzed performance for {puuid} with {len(matches)} matches")
            return analytics
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze player performance: {e}")
    
    def analyze_champion_performance(
        self,
        puuid: str,
        champion_id: int,
        role: str,
        filters: Optional[AnalyticsFilters] = None
    ) -> ChampionPerformanceMetrics:
        """
        Analyze performance for a specific player-champion-role combination.
        
        Args:
            puuid: Player's PUUID
            champion_id: Champion ID
            role: Role played
            filters: Optional filters to apply
            
        Returns:
            ChampionPerformanceMetrics object
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If analysis fails
        """
        try:
            # Generate cache key
            cache_key = f"champion_analytics_{puuid}_{champion_id}_{role}_{hash(str(filters))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached champion analytics for {puuid}-{champion_id}-{role}")
                return cached_result
            
            # Get matches for the specific champion-role combination
            champion_filters = filters or AnalyticsFilters()
            champion_filters.champions = [champion_id]
            champion_filters.roles = [role]
            
            matches = self._get_filtered_matches(puuid, champion_filters)
            
            if len(matches) < self.min_games_for_analysis:
                raise InsufficientDataError(
                    required_games=self.min_games_for_analysis,
                    available_games=len(matches),
                    context=f"champion performance analysis for {puuid}-{champion_id}-{role}"
                )
            
            # Calculate performance metrics
            performance = self._calculate_performance_metrics(matches)
            
            # Calculate performance vs baseline
            baseline_context = BaselineContext(
                puuid=puuid,
                champion_id=champion_id,
                role=role
            )
            
            try:
                baseline = self.baseline_manager.calculate_player_baseline(baseline_context)
                performance_vs_baseline = self.baseline_manager.calculate_performance_delta(
                    performance, baseline
                )
            except InsufficientDataError:
                self.logger.warning(f"Insufficient data for baseline calculation for {puuid}-{champion_id}-{role}")
                performance_vs_baseline = None
            
            # Calculate recent form
            recent_form = self._calculate_recent_form(matches)
            
            # Calculate synergy scores (simplified for now)
            synergy_scores = self._calculate_synergy_scores(matches, puuid)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(matches, performance)
            
            # Get champion name from first match
            champion_name = matches[0][1].champion_name if matches else f"Champion_{champion_id}"
            
            champion_analytics = ChampionPerformanceMetrics(
                champion_id=champion_id,
                champion_name=champion_name,
                role=role,
                performance=performance,
                performance_vs_baseline=performance_vs_baseline,
                recent_form=recent_form,
                synergy_scores=synergy_scores,
                confidence_scores=confidence_scores
            )
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, champion_analytics)
            
            self.logger.info(f"Analyzed champion performance for {puuid}-{champion_id}-{role} with {len(matches)} matches")
            return champion_analytics
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze champion performance: {e}")
    
    def calculate_performance_trends(
        self,
        puuid: str,
        time_window_days: int = 90,
        metric: str = "win_rate"
    ) -> TrendAnalysis:
        """
        Calculate performance trends over a time window.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Time window for trend analysis
            metric: Metric to analyze trends for
            
        Returns:
            TrendAnalysis object
            
        Raises:
            InsufficientDataError: If not enough data for trend analysis
            AnalyticsError: If analysis fails
        """
        try:
            # Generate cache key
            cache_key = f"trends_{puuid}_{time_window_days}_{metric}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached trend analysis for {puuid}")
                return cached_result
            
            # Get matches within time window
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < self.trend_analysis_min_points:
                raise InsufficientDataError(
                    required_games=self.trend_analysis_min_points,
                    available_games=len(matches),
                    context=f"trend analysis for {puuid}"
                )
            
            # Create time series data
            time_series = self._create_time_series_data(matches, metric)
            
            # Perform trend analysis
            trend_result = self.statistical_analyzer.calculate_trend_analysis(
                time_series,
                method=TrendAnalysisMethod.LINEAR_REGRESSION
            )
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, trend_result)
            
            self.logger.info(f"Calculated trend analysis for {puuid} over {time_window_days} days")
            return trend_result
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate performance trends: {e}")
    
    def calculate_comprehensive_performance_trends(
        self,
        puuid: str,
        time_window_days: int = 180,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, TrendAnalysis]:
        """
        Calculate comprehensive performance trends across multiple metrics.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Time window for trend analysis
            metrics: List of metrics to analyze (defaults to key performance metrics)
            
        Returns:
            Dictionary mapping metric names to TrendAnalysis objects
            
        Raises:
            InsufficientDataError: If not enough data for trend analysis
            AnalyticsError: If analysis fails
        """
        try:
            if metrics is None:
                metrics = ["win_rate", "avg_kda", "avg_cs_per_min", "avg_vision_score", "avg_damage_per_min"]
            
            # Generate cache key
            cache_key = f"comprehensive_trends_{puuid}_{time_window_days}_{hash(tuple(metrics))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached comprehensive trend analysis for {puuid}")
                return cached_result
            
            # Get matches within time window
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < self.trend_analysis_min_points:
                raise InsufficientDataError(
                    required_games=self.trend_analysis_min_points,
                    available_games=len(matches),
                    context=f"comprehensive trend analysis for {puuid}"
                )
            
            trend_results = {}
            
            # Analyze trends for each metric
            for metric in metrics:
                try:
                    time_series = self._create_time_series_data(matches, metric)
                    
                    if len(time_series) >= self.trend_analysis_min_points:
                        trend_result = self.statistical_analyzer.calculate_trend_analysis(
                            time_series,
                            method=TrendAnalysisMethod.LINEAR_REGRESSION
                        )
                        trend_results[metric] = trend_result
                    else:
                        self.logger.warning(f"Insufficient data for {metric} trend analysis")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to analyze trend for {metric}: {e}")
            
            if not trend_results:
                raise AnalyticsError("No trends could be calculated for any metric")
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, trend_results)
            
            self.logger.info(f"Calculated comprehensive trend analysis for {puuid} across {len(trend_results)} metrics")
            return trend_results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate comprehensive performance trends: {e}")
    
    def calculate_champion_specific_trends(
        self,
        puuid: str,
        champion_id: int,
        role: str,
        time_window_days: int = 120,
        metrics: Optional[List[str]] = None
    ) -> Dict[str, TrendAnalysis]:
        """
        Calculate performance trends for a specific champion-role combination.
        
        Args:
            puuid: Player's PUUID
            champion_id: Champion ID
            role: Role played
            time_window_days: Time window for trend analysis
            metrics: List of metrics to analyze
            
        Returns:
            Dictionary mapping metric names to TrendAnalysis objects
            
        Raises:
            InsufficientDataError: If not enough data for trend analysis
            AnalyticsError: If analysis fails
        """
        try:
            if metrics is None:
                metrics = ["win_rate", "avg_kda", "avg_cs_per_min", "avg_vision_score"]
            
            # Generate cache key
            cache_key = f"champion_trends_{puuid}_{champion_id}_{role}_{time_window_days}_{hash(tuple(metrics))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached champion trend analysis for {puuid}-{champion_id}-{role}")
                return cached_result
            
            # Get matches for specific champion-role combination
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date),
                champions=[champion_id],
                roles=[role]
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < self.trend_analysis_min_points:
                raise InsufficientDataError(
                    required_games=self.trend_analysis_min_points,
                    available_games=len(matches),
                    context=f"champion trend analysis for {puuid}-{champion_id}-{role}"
                )
            
            trend_results = {}
            
            # Analyze trends for each metric
            for metric in metrics:
                try:
                    time_series = self._create_time_series_data(matches, metric)
                    
                    if len(time_series) >= self.trend_analysis_min_points:
                        trend_result = self.statistical_analyzer.calculate_trend_analysis(
                            time_series,
                            method=TrendAnalysisMethod.LINEAR_REGRESSION
                        )
                        trend_results[metric] = trend_result
                    else:
                        self.logger.warning(f"Insufficient data for {metric} champion trend analysis")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to analyze champion trend for {metric}: {e}")
            
            if not trend_results:
                raise AnalyticsError("No champion trends could be calculated for any metric")
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, trend_results)
            
            self.logger.info(f"Calculated champion trend analysis for {puuid}-{champion_id}-{role} across {len(trend_results)} metrics")
            return trend_results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate champion-specific trends: {e}")
    
    def detect_meta_shifts(
        self,
        puuid: str,
        time_window_days: int = 365,
        shift_detection_window: int = 30
    ) -> Dict[str, Any]:
        """
        Detect meta shifts and adaptation patterns in player performance.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Total time window to analyze
            shift_detection_window: Window size for detecting shifts
            
        Returns:
            Dictionary containing meta shift analysis results
            
        Raises:
            InsufficientDataError: If not enough data for analysis
            AnalyticsError: If analysis fails
        """
        try:
            # Generate cache key
            cache_key = f"meta_shifts_{puuid}_{time_window_days}_{shift_detection_window}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached meta shift analysis for {puuid}")
                return cached_result
            
            # Get matches within time window
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < 50:  # Need substantial data for meta shift detection
                raise InsufficientDataError(
                    required_games=50,
                    available_games=len(matches),
                    context=f"meta shift analysis for {puuid}"
                )
            
            # Analyze champion pick patterns over time
            champion_shifts = self._analyze_champion_pick_shifts(matches, shift_detection_window)
            
            # Analyze performance adaptation patterns
            performance_adaptation = self._analyze_performance_adaptation(matches, shift_detection_window)
            
            # Detect role flexibility changes
            role_flexibility = self._analyze_role_flexibility_changes(matches, shift_detection_window)
            
            # Identify potential meta shift periods
            meta_shift_periods = self._identify_meta_shift_periods(matches, shift_detection_window)
            
            results = {
                "champion_shifts": champion_shifts,
                "performance_adaptation": performance_adaptation,
                "role_flexibility": role_flexibility,
                "meta_shift_periods": meta_shift_periods,
                "analysis_period": DateRange(start_date=start_date, end_date=end_date),
                "total_matches": len(matches)
            }
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, results)
            
            self.logger.info(f"Detected meta shifts for {puuid} over {time_window_days} days")
            return results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to detect meta shifts: {e}")
    
    def identify_seasonal_patterns(
        self,
        puuid: str,
        time_window_days: int = 730,  # 2 years for seasonal analysis
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Identify seasonal and temporal performance patterns.
        
        Args:
            puuid: Player's PUUID
            time_window_days: Time window for seasonal analysis
            metrics: List of metrics to analyze for seasonal patterns
            
        Returns:
            Dictionary containing seasonal pattern analysis results
            
        Raises:
            InsufficientDataError: If not enough data for seasonal analysis
            AnalyticsError: If analysis fails
        """
        try:
            if metrics is None:
                metrics = ["win_rate", "avg_kda", "avg_cs_per_min"]
            
            # Generate cache key
            cache_key = f"seasonal_patterns_{puuid}_{time_window_days}_{hash(tuple(metrics))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached seasonal pattern analysis for {puuid}")
                return cached_result
            
            # Get matches within time window
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < 100:  # Need substantial data for seasonal analysis
                raise InsufficientDataError(
                    required_games=100,
                    available_games=len(matches),
                    context=f"seasonal pattern analysis for {puuid}"
                )
            
            seasonal_results = {}
            
            # Analyze each metric for seasonal patterns
            for metric in metrics:
                try:
                    # Create time series data
                    time_series = self._create_time_series_data(matches, metric)
                    
                    if len(time_series) >= 50:
                        # Analyze monthly patterns
                        monthly_patterns = self._analyze_monthly_patterns(time_series)
                        
                        # Analyze day-of-week patterns
                        weekly_patterns = self._analyze_weekly_patterns(time_series)
                        
                        # Analyze time-of-day patterns (if available)
                        hourly_patterns = self._analyze_hourly_patterns(time_series)
                        
                        seasonal_results[metric] = {
                            "monthly_patterns": monthly_patterns,
                            "weekly_patterns": weekly_patterns,
                            "hourly_patterns": hourly_patterns
                        }
                    else:
                        self.logger.warning(f"Insufficient data for {metric} seasonal analysis")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to analyze seasonal patterns for {metric}: {e}")
            
            if not seasonal_results:
                raise AnalyticsError("No seasonal patterns could be calculated for any metric")
            
            results = {
                "seasonal_patterns": seasonal_results,
                "analysis_period": DateRange(start_date=start_date, end_date=end_date),
                "total_matches": len(matches)
            }
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, results)
            
            self.logger.info(f"Identified seasonal patterns for {puuid} across {len(seasonal_results)} metrics")
            return results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to identify seasonal patterns: {e}")
    
    def predict_performance_trends(
        self,
        puuid: str,
        prediction_days: int = 30,
        metrics: Optional[List[str]] = None,
        historical_window_days: int = 180
    ) -> Dict[str, Any]:
        """
        Predict future performance trends based on historical data.
        
        Args:
            puuid: Player's PUUID
            prediction_days: Number of days to predict into the future
            metrics: List of metrics to predict
            historical_window_days: Historical data window for prediction
            
        Returns:
            Dictionary containing performance predictions
            
        Raises:
            InsufficientDataError: If not enough data for prediction
            AnalyticsError: If prediction fails
        """
        try:
            if metrics is None:
                metrics = ["win_rate", "avg_kda", "avg_cs_per_min"]
            
            # Generate cache key
            cache_key = f"performance_predictions_{puuid}_{prediction_days}_{historical_window_days}_{hash(tuple(metrics))}"
            cached_result = self.cache_manager.get_cached_analytics(cache_key)
            if cached_result:
                self.logger.debug(f"Using cached performance predictions for {puuid}")
                return cached_result
            
            # Get historical matches
            end_date = datetime.now()
            start_date = end_date - timedelta(days=historical_window_days)
            
            filters = AnalyticsFilters(
                date_range=DateRange(start_date=start_date, end_date=end_date)
            )
            
            matches = self._get_filtered_matches(puuid, filters)
            
            if len(matches) < 30:  # Need substantial data for prediction
                raise InsufficientDataError(
                    required_games=30,
                    available_games=len(matches),
                    context=f"performance prediction for {puuid}"
                )
            
            predictions = {}
            
            # Generate predictions for each metric
            for metric in metrics:
                try:
                    time_series = self._create_time_series_data(matches, metric)
                    
                    if len(time_series) >= 20:
                        prediction = self._predict_metric_trend(time_series, prediction_days)
                        predictions[metric] = prediction
                    else:
                        self.logger.warning(f"Insufficient data for {metric} prediction")
                        
                except Exception as e:
                    self.logger.warning(f"Failed to predict trend for {metric}: {e}")
            
            if not predictions:
                raise AnalyticsError("No predictions could be generated for any metric")
            
            results = {
                "predictions": predictions,
                "prediction_period_days": prediction_days,
                "historical_period": DateRange(start_date=start_date, end_date=end_date),
                "prediction_confidence": self._calculate_prediction_confidence(matches, metrics),
                "total_historical_matches": len(matches)
            }
            
            # Cache the result
            self.cache_manager.cache_analytics(cache_key, results)
            
            self.logger.info(f"Generated performance predictions for {puuid} across {len(predictions)} metrics")
            return results
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to predict performance trends: {e}")
    
    def generate_comparative_analysis(
        self,
        puuids: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> Dict[str, MultiPlayerComparison]:
        """
        Generate comprehensive comparative analysis between multiple players.
        
        Args:
            puuids: List of player PUUIDs to compare
            metrics: List of metrics to compare (defaults to standard metrics)
            filters: Optional filters to apply
            
        Returns:
            Dictionary mapping metric names to MultiPlayerComparison objects
            
        Raises:
            AnalyticsError: If analysis fails
        """
        try:
            self.logger.info(f"Generating comparative analysis for {len(puuids)} players")
            
            # Use the dedicated comparative analyzer
            comparisons = self.comparative_analyzer.compare_players(
                puuids, metrics, filters
            )
            
            self.logger.info(f"Generated comparative analysis across {len(comparisons)} metrics")
            return comparisons
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to generate comparative analysis: {e}")
    
    def calculate_player_percentile_rankings(
        self,
        target_player: str,
        comparison_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ) -> ComparativeRankings:
        """
        Calculate percentile rankings for a player against a comparison pool.
        
        Args:
            target_player: PUUID of target player
            comparison_pool: List of player PUUIDs to compare against
            metrics: List of metrics to rank (defaults to standard metrics)
            filters: Optional filters to apply
            
        Returns:
            ComparativeRankings object
            
        Raises:
            AnalyticsError: If ranking calculation fails
        """
        try:
            self.logger.info(f"Calculating percentile rankings for {target_player}")
            
            rankings = self.comparative_analyzer.calculate_percentile_rankings(
                target_player, comparison_pool, metrics, filters
            )
            
            self.logger.info(f"Calculated percentile rankings: {rankings.overall_percentile:.1f}th percentile")
            return rankings
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate percentile rankings: {e}")
    
    def analyze_player_peer_group(
        self,
        target_player: str,
        skill_tier: str,
        peer_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ):
        """
        Analyze player performance within a peer group of similar skill level.
        
        Args:
            target_player: PUUID of target player
            skill_tier: Skill tier for peer grouping
            peer_pool: List of potential peer player PUUIDs
            metrics: List of metrics to analyze
            filters: Optional filters to apply
            
        Returns:
            PeerGroupAnalysis object
            
        Raises:
            AnalyticsError: If analysis fails
        """
        try:
            from .comparative_analyzer import SkillTier
            
            # Convert string to SkillTier enum
            skill_tier_enum = SkillTier(skill_tier.lower())
            
            self.logger.info(f"Analyzing peer group for {target_player} in {skill_tier} tier")
            
            analysis = self.comparative_analyzer.analyze_peer_group(
                target_player, skill_tier_enum, peer_pool, metrics, filters
            )
            
            self.logger.info(f"Peer group analysis complete: {len(analysis.strengths)} strengths, {len(analysis.weaknesses)} weaknesses")
            return analysis
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to analyze peer group: {e}")
    
    def calculate_role_specific_rankings(
        self,
        player_puuid: str,
        role: str,
        role_player_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ):
        """
        Calculate role-specific rankings for a player.
        
        Args:
            player_puuid: PUUID of target player
            role: Role to analyze
            role_player_pool: List of player PUUIDs who play this role
            metrics: List of metrics to rank
            filters: Optional filters to apply
            
        Returns:
            RoleSpecificRanking object
            
        Raises:
            AnalyticsError: If ranking calculation fails
        """
        try:
            self.logger.info(f"Calculating role-specific rankings for {player_puuid} in {role}")
            
            ranking = self.comparative_analyzer.calculate_role_specific_rankings(
                player_puuid, role, role_player_pool, metrics, filters
            )
            
            self.logger.info(f"Role-specific rankings calculated for {role}")
            return ranking
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate role-specific rankings: {e}")
    
    def calculate_champion_specific_rankings(
        self,
        player_puuid: str,
        champion_id: int,
        champion_player_pool: List[str],
        metrics: Optional[List[str]] = None,
        filters: Optional[AnalyticsFilters] = None
    ):
        """
        Calculate champion-specific rankings for a player.
        
        Args:
            player_puuid: PUUID of target player
            champion_id: Champion ID to analyze
            champion_player_pool: List of player PUUIDs who play this champion
            metrics: List of metrics to rank
            filters: Optional filters to apply
            
        Returns:
            ChampionSpecificRanking object
            
        Raises:
            AnalyticsError: If ranking calculation fails
        """
        try:
            self.logger.info(f"Calculating champion-specific rankings for {player_puuid} on champion {champion_id}")
            
            ranking = self.comparative_analyzer.calculate_champion_specific_rankings(
                player_puuid, champion_id, champion_player_pool, metrics, filters
            )
            
            self.logger.info(f"Champion-specific rankings calculated: {ranking.mastery_level} mastery level")
            return ranking
            
        except Exception as e:
            if isinstance(e, (InsufficientDataError, AnalyticsError)):
                raise
            raise AnalyticsError(f"Failed to calculate champion-specific rankings: {e}")
    
    def prepare_comparative_visualization_data(
        self,
        comparisons: Dict[str, MultiPlayerComparison],
        format_type: str = "radar_chart"
    ) -> Dict[str, Any]:
        """
        Prepare comparative analysis data for visualization.
        
        Args:
            comparisons: Dictionary of metric comparisons
            format_type: Type of visualization format
            
        Returns:
            Dictionary containing visualization-ready data
            
        Raises:
            AnalyticsError: If data preparation fails
        """
        try:
            self.logger.info(f"Preparing comparative visualization data for {format_type}")
            
            viz_data = self.comparative_analyzer.prepare_comparative_visualization_data(
                comparisons, format_type
            )
            
            self.logger.info(f"Visualization data prepared for {format_type}")
            return viz_data
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to prepare visualization data: {e}")
            
        except Exception as e:
            if isinstance(e, AnalyticsError):
                raise
            raise AnalyticsError(f"Failed to generate comparative analysis: {e}")
    
    def _get_filtered_matches(
        self,
        puuid: str,
        filters: Optional[AnalyticsFilters]
    ) -> List[Tuple[Match, MatchParticipant]]:
        """Get matches for a player with applied filters."""
        all_matches = self.match_manager.get_matches_for_player(puuid)
        filtered_matches = []
        
        for match in all_matches:
            participant = match.get_participant_by_puuid(puuid)
            if not participant:
                continue
            
            # Apply filters
            if filters:
                # Date range filter
                if filters.date_range:
                    match_date = match.game_creation_datetime
                    if not filters.date_range.contains(match_date):
                        continue
                
                # Champion filter
                if filters.champions and participant.champion_id not in filters.champions:
                    continue
                
                # Role filter
                if filters.roles:
                    normalized_role = self._normalize_role(participant.individual_position)
                    if normalized_role not in filters.roles:
                        continue
                
                # Queue type filter
                if filters.queue_types and match.queue_id not in filters.queue_types:
                    continue
                
                # Win only filter
                if filters.win_only is not None and participant.win != filters.win_only:
                    continue
                
                # Teammates filter
                if filters.teammates:
                    match_puuids = {p.puuid for p in match.participants}
                    if not any(teammate in match_puuids for teammate in filters.teammates):
                        continue
            
            filtered_matches.append((match, participant))
        
        return filtered_matches
    
    def _calculate_performance_metrics(
        self,
        matches: List[Tuple[Match, MatchParticipant]]
    ) -> PerformanceMetrics:
        """Calculate performance metrics from matches."""
        if not matches:
            return PerformanceMetrics()
        
        total_games = len(matches)
        total_wins = sum(1 for _, participant in matches if participant.win)
        total_kills = sum(participant.kills for _, participant in matches)
        total_deaths = sum(participant.deaths for _, participant in matches)
        total_assists = sum(participant.assists for _, participant in matches)
        total_cs = sum(participant.cs_total for _, participant in matches)
        total_vision = sum(participant.vision_score for _, participant in matches)
        total_damage = sum(participant.total_damage_dealt_to_champions for _, participant in matches)
        total_gold = sum(participant.gold_earned for _, participant in matches)
        total_duration = sum(match.game_duration for match, _ in matches)
        
        # Calculate derived metrics
        win_rate = total_wins / total_games
        avg_kda = (total_kills + total_assists) / max(total_deaths, 1)
        avg_cs_per_min = total_cs / (total_duration / 60) if total_duration > 0 else 0
        avg_vision_score = total_vision / total_games
        avg_damage_per_min = total_damage / (total_duration / 60) if total_duration > 0 else 0
        avg_gold_per_min = total_gold / (total_duration / 60) if total_duration > 0 else 0
        avg_game_duration = total_duration / (total_games * 60)
        
        return PerformanceMetrics(
            games_played=total_games,
            wins=total_wins,
            losses=total_games - total_wins,
            win_rate=win_rate,
            total_kills=total_kills,
            total_deaths=total_deaths,
            total_assists=total_assists,
            avg_kda=avg_kda,
            total_cs=total_cs,
            avg_cs_per_min=avg_cs_per_min,
            total_vision_score=total_vision,
            avg_vision_score=avg_vision_score,
            total_damage_to_champions=total_damage,
            avg_damage_per_min=avg_damage_per_min,
            total_gold_earned=total_gold,
            avg_gold_per_min=avg_gold_per_min,
            total_game_duration=total_duration,
            avg_game_duration=avg_game_duration
        )
    
    def _calculate_role_performance(
        self,
        matches: List[Tuple[Match, MatchParticipant]]
    ) -> Dict[str, PerformanceMetrics]:
        """Calculate performance metrics by role."""
        role_matches = defaultdict(list)
        
        for match, participant in matches:
            role = self._normalize_role(participant.individual_position)
            role_matches[role].append((match, participant))
        
        role_performance = {}
        for role, role_match_list in role_matches.items():
            if len(role_match_list) >= self.min_games_for_analysis:
                role_performance[role] = self._calculate_performance_metrics(role_match_list)
        
        return role_performance
    
    def _calculate_champion_performance(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        puuid: str
    ) -> Dict[int, ChampionPerformanceMetrics]:
        """Calculate performance metrics by champion."""
        champion_matches = defaultdict(list)
        
        for match, participant in matches:
            champion_matches[participant.champion_id].append((match, participant))
        
        champion_performance = {}
        for champion_id, champion_match_list in champion_matches.items():
            if len(champion_match_list) >= self.min_games_for_analysis:
                performance = self._calculate_performance_metrics(champion_match_list)
                
                # Get champion name and role from first match
                first_match, first_participant = champion_match_list[0]
                champion_name = first_participant.champion_name
                role = self._normalize_role(first_participant.individual_position)
                
                # Calculate performance vs baseline
                baseline_context = BaselineContext(
                    puuid=puuid,
                    champion_id=champion_id,
                    role=role
                )
                
                try:
                    baseline = self.baseline_manager.calculate_player_baseline(baseline_context)
                    performance_vs_baseline = self.baseline_manager.calculate_performance_delta(
                        performance, baseline
                    )
                except (InsufficientDataError, Exception) as e:
                    self.logger.debug(f"Could not calculate baseline for {puuid}-{champion_id}-{role}: {e}")
                    performance_vs_baseline = None
                
                # Calculate recent form
                recent_form = self._calculate_recent_form(champion_match_list)
                
                # Calculate synergy scores (simplified for now)
                synergy_scores = self._calculate_synergy_scores(champion_match_list, puuid)
                
                # Calculate confidence scores
                confidence_scores = self._calculate_confidence_scores(champion_match_list, performance)
                
                champion_performance[champion_id] = ChampionPerformanceMetrics(
                    champion_id=champion_id,
                    champion_name=champion_name,
                    role=role,
                    performance=performance,
                    performance_vs_baseline=performance_vs_baseline,
                    recent_form=recent_form,
                    synergy_scores=synergy_scores,
                    confidence_scores=confidence_scores
                )
        
        return champion_performance
    
    def _calculate_trend_analysis(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        puuid: str
    ) -> Optional[TrendAnalysis]:
        """Calculate trend analysis for player performance."""
        if len(matches) < self.trend_analysis_min_points:
            return None
        
        try:
            # Create time series for win rate
            time_series = self._create_time_series_data(matches, "win_rate")
            
            # Perform trend analysis
            trend_result = self.statistical_analyzer.calculate_trend_analysis(
                time_series,
                method=TrendAnalysisMethod.LINEAR_REGRESSION
            )
            
            return trend_result
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate trend analysis: {e}")
            return None
    
    def _calculate_comparative_rankings(
        self,
        puuid: str,
        performance: PerformanceMetrics
    ) -> Optional[ComparativeRankings]:
        """Calculate comparative rankings (simplified implementation)."""
        # This is a simplified implementation
        # In a full implementation, you would compare against a larger dataset
        return ComparativeRankings(
            overall_percentile=50.0,  # Placeholder
            peer_group_size=100,  # Placeholder
            ranking_basis="all_players"
        )
    
    def _calculate_recent_form(
        self,
        matches: List[Tuple[Match, MatchParticipant]]
    ) -> Optional[RecentFormMetrics]:
        """Calculate recent form metrics."""
        if not matches:
            return None
        
        # Sort matches by date (most recent first)
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation, reverse=True)
        
        # Take recent matches within the window
        recent_cutoff = datetime.now() - timedelta(days=self.recent_form_window_days)
        recent_matches = [
            (match, participant) for match, participant in sorted_matches
            if match.game_creation_datetime >= recent_cutoff
        ]
        
        if len(recent_matches) < 3:  # Need at least 3 games for form analysis
            return None
        
        # Calculate recent metrics
        recent_games = len(recent_matches)
        recent_wins = sum(1 for _, participant in recent_matches if participant.win)
        recent_win_rate = recent_wins / recent_games
        
        recent_kills = sum(participant.kills for _, participant in recent_matches)
        recent_deaths = sum(participant.deaths for _, participant in recent_matches)
        recent_assists = sum(participant.assists for _, participant in recent_matches)
        recent_avg_kda = (recent_kills + recent_assists) / max(recent_deaths, 1)
        
        # Determine trend direction (simplified)
        if len(recent_matches) >= 6:
            first_half = recent_matches[len(recent_matches)//2:]
            second_half = recent_matches[:len(recent_matches)//2]
            
            first_half_wr = sum(1 for _, p in first_half if p.win) / len(first_half)
            second_half_wr = sum(1 for _, p in second_half if p.win) / len(second_half)
            
            if second_half_wr > first_half_wr + 0.1:
                trend_direction = "improving"
                trend_strength = min((second_half_wr - first_half_wr) * 2, 1.0)
            elif first_half_wr > second_half_wr + 0.1:
                trend_direction = "declining"
                trend_strength = min((first_half_wr - second_half_wr) * 2, 1.0)
            else:
                trend_direction = "stable"
                trend_strength = 0.5
        else:
            trend_direction = "stable"
            trend_strength = 0.5
        
        # Calculate form score (-1 to 1)
        form_score = (recent_win_rate - 0.5) * 2  # Convert 0-1 to -1 to 1
        
        return RecentFormMetrics(
            recent_games=recent_games,
            recent_win_rate=recent_win_rate,
            recent_avg_kda=recent_avg_kda,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            form_score=form_score
        )
    
    def _calculate_synergy_scores(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        puuid: str
    ) -> Dict[str, float]:
        """Calculate synergy scores with teammates (simplified)."""
        teammate_performance = defaultdict(list)
        
        for match, participant in matches:
            if participant.win:
                # Find teammates in this match
                for other_participant in match.participants:
                    if (other_participant.puuid != puuid and 
                        other_participant.team_id == participant.team_id):
                        teammate_performance[other_participant.puuid].append(1.0)
            else:
                for other_participant in match.participants:
                    if (other_participant.puuid != puuid and 
                        other_participant.team_id == participant.team_id):
                        teammate_performance[other_participant.puuid].append(0.0)
        
        # Calculate average performance with each teammate
        synergy_scores = {}
        for teammate_puuid, performances in teammate_performance.items():
            if len(performances) >= 3:  # Need at least 3 games together
                avg_performance = statistics.mean(performances)
                # Convert to synergy score (-1 to 1, where 0.5 win rate = 0 synergy)
                synergy_scores[teammate_puuid] = (avg_performance - 0.5) * 2
        
        return synergy_scores
    
    def _calculate_confidence_scores(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        performance: PerformanceMetrics
    ) -> Dict[str, float]:
        """Calculate confidence scores for metrics based on sample size."""
        sample_size = len(matches)
        
        # Simple confidence calculation based on sample size
        base_confidence = min(sample_size / 20.0, 1.0)  # Max confidence at 20+ games
        
        return {
            "overall": base_confidence,
            "win_rate": base_confidence,
            "kda": base_confidence,
            "cs_per_min": base_confidence,
            "vision_score": base_confidence,
            "damage_per_min": base_confidence
        }
    
    def _create_time_series_data(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        metric: str
    ) -> List[TimeSeriesPoint]:
        """Create time series data for trend analysis."""
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation)
        
        time_series = []
        for match, participant in sorted_matches:
            timestamp = match.game_creation_datetime
            
            if metric == "win_rate":
                value = 1.0 if participant.win else 0.0
            elif metric == "kda":
                value = (participant.kills + participant.assists) / max(participant.deaths, 1)
            elif metric == "cs_per_min":
                value = participant.cs_total / (match.game_duration / 60) if match.game_duration > 0 else 0
            elif metric == "vision_score":
                value = participant.vision_score
            elif metric == "damage_per_min":
                value = participant.total_damage_dealt_to_champions / (match.game_duration / 60) if match.game_duration > 0 else 0
            else:
                value = 0.0
            
            time_series.append(TimeSeriesPoint(timestamp=timestamp, value=value))
        
        return time_series
    
    def _extract_metric_values(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        metric: str
    ) -> List[float]:
        """Extract metric values for statistical analysis."""
        values = []
        
        for match, participant in matches:
            if metric == "win_rate":
                values.append(1.0 if participant.win else 0.0)
            elif metric == "kda":
                values.append((participant.kills + participant.assists) / max(participant.deaths, 1))
            elif metric == "cs_per_min":
                if match.game_duration > 0:
                    values.append(participant.cs_total / (match.game_duration / 60))
                else:
                    values.append(0.0)
            elif metric == "vision_score":
                values.append(participant.vision_score)
            elif metric == "damage_per_min":
                if match.game_duration > 0:
                    values.append(participant.total_damage_dealt_to_champions / (match.game_duration / 60))
                else:
                    values.append(0.0)
        
        return values
    
    def _normalize_role(self, position: str) -> str:
        """Normalize position string to standard role."""
        position = position.lower()
        
        role_mapping = {
            'top': 'top',
            'jungle': 'jungle',
            'middle': 'middle',
            'mid': 'middle',
            'bottom': 'bottom',
            'bot': 'bottom',
            'adc': 'bottom',
            'support': 'support',
            'utility': 'support'
        }
        
        return role_mapping.get(position, position) 
   
    # Helper methods for comprehensive trend analysis
    
    def _analyze_champion_pick_shifts(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        window_size: int
    ) -> Dict[str, Any]:
        """Analyze champion pick pattern shifts over time."""
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation)
        
        # Group matches into time windows
        windows = []
        current_window = []
        window_start = sorted_matches[0][0].game_creation_datetime
        
        for match, participant in sorted_matches:
            match_date = match.game_creation_datetime
            
            # Check if we need to start a new window
            if (match_date - window_start).days >= window_size:
                if current_window:
                    windows.append(current_window)
                current_window = [(match, participant)]
                window_start = match_date
            else:
                current_window.append((match, participant))
        
        # Add the last window
        if current_window:
            windows.append(current_window)
        
        # Analyze champion diversity and shifts between windows
        champion_shifts = []
        for i in range(len(windows) - 1):
            current_champions = set(p.champion_id for _, p in windows[i])
            next_champions = set(p.champion_id for _, p in windows[i + 1])
            
            # Calculate champion pool overlap
            overlap = len(current_champions & next_champions)
            total_unique = len(current_champions | next_champions)
            overlap_ratio = overlap / total_unique if total_unique > 0 else 0
            
            champion_shifts.append({
                "window_start": windows[i][0][0].game_creation_datetime,
                "window_end": windows[i + 1][-1][0].game_creation_datetime,
                "overlap_ratio": overlap_ratio,
                "new_champions": list(next_champions - current_champions),
                "dropped_champions": list(current_champions - next_champions)
            })
        
        return {
            "shifts": champion_shifts,
            "total_windows": len(windows),
            "avg_overlap_ratio": statistics.mean([s["overlap_ratio"] for s in champion_shifts]) if champion_shifts else 0
        }
    
    def _analyze_performance_adaptation(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        window_size: int
    ) -> Dict[str, Any]:
        """Analyze how performance adapts over time windows."""
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation)
        
        # Group matches into time windows
        windows = []
        current_window = []
        window_start = sorted_matches[0][0].game_creation_datetime
        
        for match, participant in sorted_matches:
            match_date = match.game_creation_datetime
            
            if (match_date - window_start).days >= window_size:
                if current_window:
                    windows.append(current_window)
                current_window = [(match, participant)]
                window_start = match_date
            else:
                current_window.append((match, participant))
        
        if current_window:
            windows.append(current_window)
        
        # Calculate performance metrics for each window
        window_performances = []
        for window in windows:
            if len(window) >= 3:  # Need minimum games for reliable metrics
                performance = self._calculate_performance_metrics(window)
                window_performances.append({
                    "start_date": window[0][0].game_creation_datetime,
                    "end_date": window[-1][0].game_creation_datetime,
                    "games": len(window),
                    "win_rate": performance.win_rate,
                    "avg_kda": performance.avg_kda,
                    "avg_cs_per_min": performance.avg_cs_per_min
                })
        
        # Analyze adaptation patterns
        adaptation_score = 0.0
        if len(window_performances) >= 2:
            # Calculate trend in performance over windows
            win_rates = [w["win_rate"] for w in window_performances]
            if len(win_rates) >= 3:
                # Simple linear trend calculation
                x_values = list(range(len(win_rates)))
                correlation = statistics.correlation(x_values, win_rates) if len(win_rates) > 1 else 0
                adaptation_score = max(0, correlation)  # Positive correlation indicates improvement
        
        return {
            "window_performances": window_performances,
            "adaptation_score": adaptation_score,
            "total_windows": len(window_performances)
        }
    
    def _analyze_role_flexibility_changes(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        window_size: int
    ) -> Dict[str, Any]:
        """Analyze changes in role flexibility over time."""
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation)
        
        # Group matches into time windows
        windows = []
        current_window = []
        window_start = sorted_matches[0][0].game_creation_datetime
        
        for match, participant in sorted_matches:
            match_date = match.game_creation_datetime
            
            if (match_date - window_start).days >= window_size:
                if current_window:
                    windows.append(current_window)
                current_window = [(match, participant)]
                window_start = match_date
            else:
                current_window.append((match, participant))
        
        if current_window:
            windows.append(current_window)
        
        # Analyze role diversity in each window
        role_flexibility = []
        for window in windows:
            roles = [self._normalize_role(p.individual_position) for _, p in window]
            unique_roles = set(roles)
            
            role_flexibility.append({
                "start_date": window[0][0].game_creation_datetime,
                "end_date": window[-1][0].game_creation_datetime,
                "unique_roles": len(unique_roles),
                "roles_played": list(unique_roles),
                "games": len(window)
            })
        
        # Calculate flexibility trend
        flexibility_scores = [w["unique_roles"] for w in role_flexibility]
        avg_flexibility = statistics.mean(flexibility_scores) if flexibility_scores else 0
        
        return {
            "role_flexibility": role_flexibility,
            "avg_flexibility": avg_flexibility,
            "max_flexibility": max(flexibility_scores) if flexibility_scores else 0
        }
    
    def _identify_meta_shift_periods(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        window_size: int
    ) -> List[Dict[str, Any]]:
        """Identify potential meta shift periods based on performance changes."""
        # Sort matches by date
        sorted_matches = sorted(matches, key=lambda x: x[0].game_creation)
        
        # Create sliding windows for performance analysis
        shift_periods = []
        window_step = window_size // 2  # Overlapping windows
        
        for i in range(0, len(sorted_matches) - window_size, window_step):
            window_matches = sorted_matches[i:i + window_size]
            
            if len(window_matches) >= 10:  # Minimum matches for analysis
                performance = self._calculate_performance_metrics(window_matches)
                
                # Calculate performance variance as indicator of meta instability
                win_values = [1.0 if p.win else 0.0 for _, p in window_matches]
                performance_variance = statistics.variance(win_values) if len(win_values) > 1 else 0
                
                shift_periods.append({
                    "start_date": window_matches[0][0].game_creation_datetime,
                    "end_date": window_matches[-1][0].game_creation_datetime,
                    "win_rate": performance.win_rate,
                    "performance_variance": performance_variance,
                    "games": len(window_matches)
                })
        
        # Identify periods with high variance as potential meta shifts
        if shift_periods:
            avg_variance = statistics.mean([p["performance_variance"] for p in shift_periods])
            high_variance_periods = [
                p for p in shift_periods 
                if p["performance_variance"] > avg_variance * 1.5
            ]
            
            return high_variance_periods
        
        return []
    
    def _analyze_monthly_patterns(self, time_series: List[TimeSeriesPoint]) -> Dict[int, float]:
        """Analyze performance patterns by month."""
        monthly_data = defaultdict(list)
        
        for point in time_series:
            month = point.timestamp.month
            monthly_data[month].append(point.value)
        
        monthly_averages = {}
        for month, values in monthly_data.items():
            if len(values) >= 3:  # Need minimum data points
                monthly_averages[month] = statistics.mean(values)
        
        return monthly_averages
    
    def _analyze_weekly_patterns(self, time_series: List[TimeSeriesPoint]) -> Dict[int, float]:
        """Analyze performance patterns by day of week."""
        weekly_data = defaultdict(list)
        
        for point in time_series:
            day_of_week = point.timestamp.weekday()  # 0 = Monday, 6 = Sunday
            weekly_data[day_of_week].append(point.value)
        
        weekly_averages = {}
        for day, values in weekly_data.items():
            if len(values) >= 3:  # Need minimum data points
                weekly_averages[day] = statistics.mean(values)
        
        return weekly_averages
    
    def _analyze_hourly_patterns(self, time_series: List[TimeSeriesPoint]) -> Dict[int, float]:
        """Analyze performance patterns by hour of day."""
        hourly_data = defaultdict(list)
        
        for point in time_series:
            hour = point.timestamp.hour
            hourly_data[hour].append(point.value)
        
        hourly_averages = {}
        for hour, values in hourly_data.items():
            if len(values) >= 2:  # Need minimum data points
                hourly_averages[hour] = statistics.mean(values)
        
        return hourly_averages
    
    def _predict_metric_trend(
        self,
        time_series: List[TimeSeriesPoint],
        prediction_days: int
    ) -> Dict[str, Any]:
        """Predict future trend for a specific metric."""
        try:
            # Convert to numerical format for prediction
            timestamps = [point.timestamp for point in time_series]
            values = [point.value for point in time_series]
            
            # Convert timestamps to days since first timestamp
            start_time = timestamps[0]
            numeric_times = [(ts - start_time).total_seconds() / 86400 for ts in timestamps]
            
            # Simple linear regression for prediction
            if len(numeric_times) >= 3:
                # Calculate linear trend
                x_mean = statistics.mean(numeric_times)
                y_mean = statistics.mean(values)
                
                numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(numeric_times, values))
                denominator = sum((x - x_mean) ** 2 for x in numeric_times)
                
                if denominator != 0:
                    slope = numerator / denominator
                    intercept = y_mean - slope * x_mean
                    
                    # Predict future values
                    last_time = numeric_times[-1]
                    future_time = last_time + prediction_days
                    predicted_value = slope * future_time + intercept
                    
                    # Calculate prediction confidence based on R-squared
                    predicted_values = [slope * x + intercept for x in numeric_times]
                    ss_res = sum((y - pred) ** 2 for y, pred in zip(values, predicted_values))
                    ss_tot = sum((y - y_mean) ** 2 for y in values)
                    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                    
                    return {
                        "predicted_value": predicted_value,
                        "trend_slope": slope,
                        "confidence": max(0, r_squared),
                        "prediction_date": start_time + timedelta(days=future_time),
                        "trend_direction": "improving" if slope > 0 else "declining" if slope < 0 else "stable"
                    }
            
            # Fallback to simple average if regression fails
            recent_values = values[-min(10, len(values)):]  # Last 10 values
            predicted_value = statistics.mean(recent_values)
            
            return {
                "predicted_value": predicted_value,
                "trend_slope": 0.0,
                "confidence": 0.3,  # Low confidence for simple average
                "prediction_date": timestamps[-1] + timedelta(days=prediction_days),
                "trend_direction": "stable"
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to predict metric trend: {e}")
            return {
                "predicted_value": 0.0,
                "trend_slope": 0.0,
                "confidence": 0.0,
                "prediction_date": datetime.now() + timedelta(days=prediction_days),
                "trend_direction": "unknown"
            }
    
    def _calculate_prediction_confidence(
        self,
        matches: List[Tuple[Match, MatchParticipant]],
        metrics: List[str]
    ) -> Dict[str, float]:
        """Calculate confidence scores for predictions based on data quality."""
        sample_size = len(matches)
        
        # Base confidence on sample size
        size_confidence = min(sample_size / 50.0, 1.0)  # Max confidence at 50+ games
        
        # Calculate data recency factor
        if matches:
            sorted_matches = sorted(matches, key=lambda x: x[0].game_creation, reverse=True)
            most_recent = sorted_matches[0][0].game_creation_datetime
            days_since_recent = (datetime.now() - most_recent).days
            recency_confidence = max(0, 1.0 - (days_since_recent / 30.0))  # Decay over 30 days
        else:
            recency_confidence = 0.0
        
        # Calculate data consistency (simplified)
        consistency_confidence = 0.8  # Placeholder
        
        # Combine factors
        overall_confidence = (size_confidence * 0.4 + 
                            recency_confidence * 0.3 + 
                            consistency_confidence * 0.3)
        
        return {metric: overall_confidence for metric in metrics}    

    # Optimized Analytics Methods
    
    def batch_analyze_multiple_players(
        self,
        puuids: List[str],
        filters: Optional[AnalyticsFilters] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, PlayerAnalytics]:
        """
        Analyze multiple players using batch processing for improved performance.
        
        Args:
            puuids: List of player PUUIDs to analyze
            filters: Optional filters to apply to all analyses
            progress_callback: Optional progress callback function
            
        Returns:
            Dictionary mapping PUUIDs to PlayerAnalytics objects
            
        Raises:
            AnalyticsError: If batch processing fails
        """
        try:
            self.logger.info(f"Starting batch analysis for {len(puuids)} players")
            
            # Use batch processor for parallel execution
            batch_result = self.batch_processor.batch_analyze_players(
                puuids, filters, progress_callback
            )
            
            # Extract successful results
            successful_results = batch_result.successful_results
            
            # Log any errors
            if batch_result.errors:
                for task_id, error in batch_result.errors.items():
                    self.logger.error(f"Batch analysis failed for {task_id}: {error}")
            
            self.logger.info(f"Batch analysis completed: {len(successful_results)} successful, "
                           f"{len(batch_result.errors)} failed")
            
            return successful_results
            
        except Exception as e:
            raise AnalyticsError(f"Batch player analysis failed: {e}")
    
    def update_analytics_incrementally(
        self,
        puuid: str,
        force_full_update: bool = False
    ) -> bool:
        """
        Update analytics for a player incrementally for better performance.
        
        Args:
            puuid: Player's PUUID
            force_full_update: If True, recalculate all analytics
            
        Returns:
            True if update was successful
            
        Raises:
            AnalyticsError: If incremental update fails
        """
        try:
            result = self.incremental_updater.update_player_analytics(
                puuid, force_full_update
            )
            
            if result.errors:
                error_msg = "; ".join(result.errors)
                self.logger.error(f"Incremental update had errors: {error_msg}")
                return False
            
            self.logger.info(f"Incremental update successful for {puuid}: "
                           f"{result.new_matches_processed} matches processed")
            return True
            
        except Exception as e:
            raise AnalyticsError(f"Incremental analytics update failed: {e}")
    
    def get_players_needing_updates(self, max_age_hours: int = 24) -> List[str]:
        """
        Get list of players whose analytics need updating.
        
        Args:
            max_age_hours: Maximum age of analytics before update is needed
            
        Returns:
            List of player PUUIDs needing updates
        """
        return self.incremental_updater.get_players_needing_updates(max_age_hours)
    
    def execute_optimized_query(
        self,
        filters: AnalyticsFilters,
        query_type: str = "general"
    ) -> List[Match]:
        """
        Execute an optimized query for match data.
        
        Args:
            filters: Query filters
            query_type: Type of query for optimization
            
        Returns:
            List of matching matches
            
        Raises:
            AnalyticsError: If query execution fails
        """
        try:
            return self.query_optimizer.execute_optimized_query(filters, query_type)
        except Exception as e:
            raise AnalyticsError(f"Optimized query execution failed: {e}")
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics for optimization features.
        
        Returns:
            Dictionary containing optimization statistics
        """
        try:
            stats = {
                'batch_processing': self.batch_processor.batch_processor.get_performance_metrics(),
                'incremental_updates': self.incremental_updater.get_update_statistics(),
                'query_optimization': self.query_optimizer.get_query_statistics(),
                'cache_performance': self.cache_manager.get_cache_statistics()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get optimization statistics: {e}")
            return {}
    
    def cleanup_optimization_data(self, days: int = 90) -> Dict[str, int]:
        """
        Clean up old optimization data to free up space.
        
        Args:
            days: Number of days to keep data
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            cleanup_stats = {}
            
            # Clean up incremental update data
            incremental_stats = self.incremental_updater.cleanup_old_data(days)
            cleanup_stats.update(incremental_stats)
            
            # Clean up query cache
            self.query_optimizer.clear_cache()
            cleanup_stats['query_cache_cleared'] = True
            
            # Clean up analytics cache
            expired_entries = self.cache_manager.cleanup_expired_entries()
            cleanup_stats['expired_cache_entries'] = expired_entries
            
            self.logger.info(f"Optimization data cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup optimization data: {e}")
            return {}
    
    def _get_filtered_matches_optimized(
        self,
        puuid: str,
        filters: Optional[AnalyticsFilters]
    ) -> List[Tuple[Match, MatchParticipant]]:
        """
        Get matches for a player with filters applied using optimized queries.
        
        Args:
            puuid: Player's PUUID
            filters: Optional filters to apply
            
        Returns:
            List of (match, participant) tuples
        """
        try:
            # Use query optimizer for efficient filtering
            if filters:
                # Add player filter if not already present
                if not filters.player_puuids:
                    filters.player_puuids = [puuid]
                elif puuid not in filters.player_puuids:
                    filters.player_puuids.append(puuid)
                
                # Execute optimized query
                matches = self.query_optimizer.execute_optimized_query(filters, "player_matches")
            else:
                # Fallback to match manager
                matches = self.match_manager.get_matches_for_player(puuid)
            
            # Convert to (match, participant) tuples
            filtered_matches = []
            for match in matches:
                participant = match.get_participant_by_puuid(puuid)
                if participant:
                    filtered_matches.append((match, participant))
            
            return filtered_matches
            
        except Exception as e:
            self.logger.warning(f"Query optimization failed, falling back to basic filtering: {e}")
            # Fallback to original implementation
            matches = self.match_manager.get_matches_for_player(puuid)
            
            filtered_matches = []
            for match in matches:
                participant = match.get_participant_by_puuid(puuid)
                if participant and self._match_passes_filters(match, participant, filters):
                    filtered_matches.append((match, participant))
            
            return filtered_matches
    
    def _match_passes_filters(
        self,
        match: Match,
        participant: MatchParticipant,
        filters: Optional[AnalyticsFilters]
    ) -> bool:
        """
        Check if a match passes the given filters.
        
        Args:
            match: Match to check
            participant: Participant to check
            filters: Filters to apply
            
        Returns:
            True if match passes all filters
        """
        if not filters:
            return True
        
        # Date filter
        if filters.date_range:
            match_date = datetime.fromtimestamp(match.game_creation / 1000)
            if not filters.date_range.contains(match_date):
                return False
        
        # Champion filter
        if filters.champions and participant.champion_id not in filters.champions:
            return False
        
        # Role filter
        if filters.roles and participant.individual_position.lower() not in [r.lower() for r in filters.roles]:
            return False
        
        # Queue filter
        if filters.queue_types and match.queue_id not in filters.queue_types:
            return False
        
        # Win filter
        if filters.win_only is not None and participant.win != filters.win_only:
            return False
        
        return True