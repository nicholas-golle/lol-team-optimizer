"""
Advanced Player Data Validation and API Integration

This module provides comprehensive player data validation with real-time Riot API integration,
champion mastery data fetching, data quality scoring, and robust error handling.
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from .models import Player, ChampionMastery, ChampionPerformance
from .riot_client import RiotAPIClient
from .config import Config


class ValidationStatus(Enum):
    """Status of validation operations."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"
    TIMEOUT = "timeout"


class DataQualityLevel(Enum):
    """Data quality levels for player information."""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    FAIR = "fair"           # 50-69%
    POOR = "poor"           # 30-49%
    CRITICAL = "critical"   # 0-29%


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    status: ValidationStatus
    is_valid: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    error_code: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class PlayerDataQuality:
    """Comprehensive data quality assessment for a player."""
    player_name: str
    overall_score: float  # 0-100
    quality_level: DataQualityLevel
    
    # Individual component scores
    basic_info_score: float = 0.0
    api_validation_score: float = 0.0
    mastery_data_score: float = 0.0
    performance_data_score: float = 0.0
    recency_score: float = 0.0
    
    # Detailed assessments
    missing_fields: List[str] = field(default_factory=list)
    outdated_fields: List[str] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    last_assessment: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calculate overall quality level based on score."""
        if self.overall_score >= 90:
            self.quality_level = DataQualityLevel.EXCELLENT
        elif self.overall_score >= 70:
            self.quality_level = DataQualityLevel.GOOD
        elif self.overall_score >= 50:
            self.quality_level = DataQualityLevel.FAIR
        elif self.overall_score >= 30:
            self.quality_level = DataQualityLevel.POOR
        else:
            self.quality_level = DataQualityLevel.CRITICAL


@dataclass
class APIValidationCache:
    """Cache for API validation results to avoid repeated calls."""
    summoner_validations: Dict[str, ValidationResult] = field(default_factory=dict)
    mastery_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rank_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_cleanup: datetime = field(default_factory=datetime.now)
    
    def cleanup_expired(self, max_age_hours: int = 24):
        """Remove expired cache entries."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Clean summoner validations
        expired_keys = [
            key for key, result in self.summoner_validations.items()
            if result.timestamp < cutoff_time
        ]
        for key in expired_keys:
            del self.summoner_validations[key]
        
        # Clean mastery data
        expired_mastery = [
            key for key, data in self.mastery_data.items()
            if data.get('timestamp', datetime.min) < cutoff_time
        ]
        for key in expired_mastery:
            del self.mastery_data[key]
        
        # Clean rank data
        expired_rank = [
            key for key, data in self.rank_data.items()
            if data.get('timestamp', datetime.min) < cutoff_time
        ]
        for key in expired_rank:
            del self.rank_data[key]
        
        self.last_cleanup = datetime.now()


class AdvancedPlayerValidator:
    """
    Advanced player data validator with real-time API integration.
    
    Provides comprehensive validation including:
    - Real-time summoner name validation with Riot API
    - Rank verification and automatic data fetching
    - Champion mastery data integration
    - Data quality indicators and completeness scoring
    - Automatic data refresh and update notifications
    - Robust error handling with fallback options
    """
    
    def __init__(self, config: Config, riot_client: Optional[RiotAPIClient] = None):
        """Initialize the advanced validator."""
        self.config = config
        self.riot_client = riot_client
        self.logger = logging.getLogger(__name__)
        self.validation_cache = APIValidationCache()
        
        # Validation settings
        self.validation_timeout = 10  # seconds
        self.max_concurrent_validations = 5
        self.retry_attempts = 3
        
        # Data quality thresholds
        self.quality_thresholds = {
            'basic_info_weight': 0.25,
            'api_validation_weight': 0.30,
            'mastery_data_weight': 0.20,
            'performance_data_weight': 0.15,
            'recency_weight': 0.10
        }
    
    async def validate_summoner_real_time(self, summoner_name: str, tag_line: str, 
                                        region: str = "americas", platform: str = "na1") -> ValidationResult:
        """
        Validate summoner name in real-time using Riot API.
        
        Args:
            summoner_name: The summoner's game name
            tag_line: The summoner's tag line (without #)
            region: Regional routing (americas, asia, europe)
            platform: Platform routing (na1, euw1, etc.)
            
        Returns:
            ValidationResult with detailed validation information
        """
        if not self.riot_client:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                is_valid=False,
                message="Riot API client not available",
                error_code="NO_API_CLIENT"
            )
        
        # Create cache key
        cache_key = f"{summoner_name}#{tag_line}@{region}"
        
        # Check cache first
        if cache_key in self.validation_cache.summoner_validations:
            cached_result = self.validation_cache.summoner_validations[cache_key]
            # Return cached result if less than 1 hour old
            if (datetime.now() - cached_result.timestamp).total_seconds() < 3600:
                return cached_result
        
        try:
            # Validate with timeout
            validation_task = asyncio.create_task(
                self._perform_api_validation(summoner_name, tag_line, region, platform)
            )
            
            result = await asyncio.wait_for(validation_task, timeout=self.validation_timeout)
            
            # Cache successful result
            self.validation_cache.summoner_validations[cache_key] = result
            
            return result
            
        except asyncio.TimeoutError:
            result = ValidationResult(
                status=ValidationStatus.TIMEOUT,
                is_valid=False,
                message=f"Validation timed out after {self.validation_timeout} seconds",
                error_code="TIMEOUT",
                suggestions=["Try again later", "Check your internet connection"]
            )
            
        except Exception as e:
            self.logger.error(f"API validation error for {cache_key}: {e}")
            result = ValidationResult(
                status=ValidationStatus.ERROR,
                is_valid=False,
                message=f"Validation failed: {str(e)}",
                error_code="API_ERROR",
                suggestions=["Check summoner name spelling", "Verify region selection"]
            )
        
        # Cache failed result for shorter duration
        self.validation_cache.summoner_validations[cache_key] = result
        return result
    
    async def _perform_api_validation(self, summoner_name: str, tag_line: str, 
                                    region: str, platform: str) -> ValidationResult:
        """Perform the actual API validation with retries."""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                # Get summoner data
                summoner_data = self.riot_client.get_summoner_data(
                    f"{summoner_name}#{tag_line}", region, platform
                )
                
                if summoner_data and summoner_data.get('puuid'):
                    # Get additional data
                    puuid = summoner_data['puuid']
                    summoner_id = summoner_data.get('id', '')
                    
                    # Fetch rank data
                    rank_data = None
                    try:
                        rank_data = self.riot_client.get_ranked_stats(summoner_id, platform)
                    except Exception as e:
                        self.logger.warning(f"Could not fetch rank data: {e}")
                    
                    # Fetch mastery score
                    mastery_score = 0
                    try:
                        mastery_score = self.riot_client.get_champion_mastery_score(puuid, platform)
                    except Exception as e:
                        self.logger.warning(f"Could not fetch mastery score: {e}")
                    
                    return ValidationResult(
                        status=ValidationStatus.VALID,
                        is_valid=True,
                        message=f"Summoner {summoner_name}#{tag_line} validated successfully",
                        details={
                            'puuid': puuid,
                            'summoner_id': summoner_id,
                            'summoner_level': summoner_data.get('summonerLevel', 0),
                            'rank_data': rank_data,
                            'mastery_score': mastery_score,
                            'region': region,
                            'platform': platform
                        }
                    )
                else:
                    return ValidationResult(
                        status=ValidationStatus.INVALID,
                        is_valid=False,
                        message=f"Summoner {summoner_name}#{tag_line} not found",
                        error_code="SUMMONER_NOT_FOUND",
                        suggestions=[
                            "Check spelling of summoner name",
                            "Verify tag line is correct",
                            "Ensure correct region is selected"
                        ]
                    )
                    
            except Exception as e:
                last_error = e
                if attempt < self.retry_attempts - 1:
                    # Wait before retry with exponential backoff
                    wait_time = (2 ** attempt) * 1.0
                    await asyncio.sleep(wait_time)
                    continue
        
        # All retries failed
        return ValidationResult(
            status=ValidationStatus.ERROR,
            is_valid=False,
            message=f"Validation failed after {self.retry_attempts} attempts: {str(last_error)}",
            error_code="RETRY_EXHAUSTED"
        )
    
    async def fetch_champion_mastery_data(self, puuid: str, platform: str = "na1") -> Dict[str, Any]:
        """
        Fetch comprehensive champion mastery data for a player.
        
        Args:
            puuid: Player's PUUID
            platform: Platform to query
            
        Returns:
            Dictionary containing mastery data and analysis
        """
        if not self.riot_client:
            return {'error': 'Riot API client not available'}
        
        cache_key = f"mastery_{puuid}@{platform}"
        
        # Check cache
        if cache_key in self.validation_cache.mastery_data:
            cached_data = self.validation_cache.mastery_data[cache_key]
            # Return cached data if less than 6 hours old
            if (datetime.now() - cached_data.get('timestamp', datetime.min)).total_seconds() < 21600:
                return cached_data
        
        try:
            # Fetch all champion masteries
            all_masteries = self.riot_client.get_all_champion_masteries(puuid, platform)
            mastery_score = self.riot_client.get_champion_mastery_score(puuid, platform)
            
            # Analyze mastery data
            analysis = self._analyze_mastery_data(all_masteries)
            
            mastery_data = {
                'total_champions': len(all_masteries),
                'mastery_score': mastery_score,
                'masteries': all_masteries,
                'analysis': analysis,
                'timestamp': datetime.now(),
                'platform': platform
            }
            
            # Cache the result
            self.validation_cache.mastery_data[cache_key] = mastery_data
            
            return mastery_data
            
        except Exception as e:
            self.logger.error(f"Error fetching mastery data for {puuid}: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def _analyze_mastery_data(self, masteries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze champion mastery data to provide insights."""
        if not masteries:
            return {
                'total_champions': 0,
                'mastery_levels': {},
                'top_champions': [],
                'role_distribution': {},
                'recent_activity': False
            }
        
        # Count mastery levels
        mastery_levels = {}
        for mastery in masteries:
            level = mastery.get('championLevel', 0)
            mastery_levels[level] = mastery_levels.get(level, 0) + 1
        
        # Get top champions by mastery points
        top_champions = sorted(
            masteries,
            key=lambda x: x.get('championPoints', 0),
            reverse=True
        )[:10]
        
        # Estimate role distribution based on champion types
        # This is a simplified estimation - in a real implementation,
        # you'd use champion data to determine typical roles
        role_distribution = self._estimate_role_distribution(masteries)
        
        # Check for recent activity
        recent_activity = any(
            mastery.get('lastPlayTime', 0) > (time.time() - 30 * 24 * 3600) * 1000
            for mastery in masteries
        )
        
        return {
            'total_champions': len(masteries),
            'mastery_levels': mastery_levels,
            'top_champions': [
                {
                    'championId': champ.get('championId'),
                    'championLevel': champ.get('championLevel'),
                    'championPoints': champ.get('championPoints'),
                    'lastPlayTime': champ.get('lastPlayTime')
                }
                for champ in top_champions
            ],
            'role_distribution': role_distribution,
            'recent_activity': recent_activity,
            'high_mastery_count': mastery_levels.get(7, 0) + mastery_levels.get(6, 0),
            'total_mastery_points': sum(m.get('championPoints', 0) for m in masteries)
        }
    
    def _estimate_role_distribution(self, masteries: List[Dict[str, Any]]) -> Dict[str, int]:
        """Estimate role distribution based on champion masteries."""
        # This is a simplified implementation
        # In practice, you'd use champion data to map champions to typical roles
        
        role_counts = {
            'top': 0,
            'jungle': 0,
            'middle': 0,
            'bottom': 0,
            'support': 0
        }
        
        # For demonstration, we'll use a simple heuristic based on champion IDs
        # In reality, you'd have a proper champion-to-role mapping
        for mastery in masteries:
            champion_id = mastery.get('championId', 0)
            mastery_points = mastery.get('championPoints', 0)
            
            # Simple heuristic - distribute based on champion ID ranges
            # This is just for demonstration
            if champion_id % 5 == 0:
                role_counts['top'] += mastery_points
            elif champion_id % 5 == 1:
                role_counts['jungle'] += mastery_points
            elif champion_id % 5 == 2:
                role_counts['middle'] += mastery_points
            elif champion_id % 5 == 3:
                role_counts['bottom'] += mastery_points
            else:
                role_counts['support'] += mastery_points
        
        return role_counts
    
    def calculate_data_quality(self, player: Player, 
                             validation_result: Optional[ValidationResult] = None,
                             mastery_data: Optional[Dict[str, Any]] = None) -> PlayerDataQuality:
        """
        Calculate comprehensive data quality score for a player.
        
        Args:
            player: Player object to assess
            validation_result: Recent API validation result
            mastery_data: Champion mastery data
            
        Returns:
            PlayerDataQuality assessment
        """
        quality = PlayerDataQuality(
            player_name=player.name, 
            overall_score=0.0,
            quality_level=DataQualityLevel.CRITICAL  # Will be updated in __post_init__
        )
        
        # 1. Basic Information Score (25%)
        basic_score = self._calculate_basic_info_score(player, quality)
        
        # 2. API Validation Score (30%)
        api_score = self._calculate_api_validation_score(validation_result, quality)
        
        # 3. Mastery Data Score (20%)
        mastery_score = self._calculate_mastery_data_score(mastery_data, quality)
        
        # 4. Performance Data Score (15%)
        performance_score = self._calculate_performance_data_score(player, quality)
        
        # 5. Recency Score (10%)
        recency_score = self._calculate_recency_score(player, quality)
        
        # Calculate weighted overall score
        weights = self.quality_thresholds
        quality.overall_score = (
            basic_score * weights['basic_info_weight'] +
            api_score * weights['api_validation_weight'] +
            mastery_score * weights['mastery_data_weight'] +
            performance_score * weights['performance_data_weight'] +
            recency_score * weights['recency_weight']
        )
        
        # Store individual scores
        quality.basic_info_score = basic_score
        quality.api_validation_score = api_score
        quality.mastery_data_score = mastery_score
        quality.performance_data_score = performance_score
        quality.recency_score = recency_score
        
        # Update quality level based on final score
        if quality.overall_score >= 90:
            quality.quality_level = DataQualityLevel.EXCELLENT
        elif quality.overall_score >= 70:
            quality.quality_level = DataQualityLevel.GOOD
        elif quality.overall_score >= 50:
            quality.quality_level = DataQualityLevel.FAIR
        elif quality.overall_score >= 30:
            quality.quality_level = DataQualityLevel.POOR
        else:
            quality.quality_level = DataQualityLevel.CRITICAL
        
        # Generate improvement suggestions
        self._generate_improvement_suggestions(quality)
        
        return quality
    
    def _calculate_basic_info_score(self, player: Player, quality: PlayerDataQuality) -> float:
        """Calculate score for basic player information completeness."""
        score = 0.0
        max_score = 100.0
        
        # Required fields
        if player.name and player.name.strip():
            score += 30
        else:
            quality.missing_fields.append("player_name")
        
        if player.summoner_name and player.summoner_name.strip():
            score += 30
        else:
            quality.missing_fields.append("summoner_name")
        
        # Role preferences
        if player.role_preferences:
            valid_prefs = sum(1 for pref in player.role_preferences.values() 
                            if isinstance(pref, int) and 1 <= pref <= 5)
            score += (valid_prefs / 5) * 20  # 20 points for complete role preferences
        else:
            quality.missing_fields.append("role_preferences")
        
        # PUUID (indicates API validation)
        if player.puuid:
            score += 20
        else:
            quality.missing_fields.append("puuid")
        
        return min(score, max_score)
    
    def _calculate_api_validation_score(self, validation_result: Optional[ValidationResult], 
                                      quality: PlayerDataQuality) -> float:
        """Calculate score based on API validation status."""
        if not validation_result:
            quality.quality_issues.append("No API validation performed")
            return 0.0
        
        if validation_result.status == ValidationStatus.VALID:
            score = 100.0
            
            # Bonus for additional data
            details = validation_result.details
            if details.get('rank_data'):
                score += 10  # Bonus for rank data
            if details.get('mastery_score', 0) > 0:
                score += 10  # Bonus for mastery data
                
            return min(score, 100.0)
            
        elif validation_result.status == ValidationStatus.INVALID:
            quality.quality_issues.append("Summoner validation failed")
            return 0.0
            
        elif validation_result.status == ValidationStatus.TIMEOUT:
            quality.quality_issues.append("API validation timed out")
            return 25.0  # Partial credit
            
        elif validation_result.status == ValidationStatus.ERROR:
            quality.quality_issues.append(f"API validation error: {validation_result.message}")
            return 10.0  # Minimal credit
            
        else:
            return 0.0
    
    def _calculate_mastery_data_score(self, mastery_data: Optional[Dict[str, Any]], 
                                    quality: PlayerDataQuality) -> float:
        """Calculate score based on champion mastery data availability and quality."""
        if not mastery_data or 'error' in mastery_data:
            quality.missing_fields.append("champion_mastery_data")
            return 0.0
        
        analysis = mastery_data.get('analysis', {})
        total_champions = analysis.get('total_champions', 0)
        mastery_score = mastery_data.get('mastery_score', 0)
        
        score = 0.0
        
        # Base score for having mastery data
        if total_champions > 0:
            score += 40
        
        # Score based on number of champions played
        if total_champions >= 50:
            score += 20
        elif total_champions >= 20:
            score += 15
        elif total_champions >= 10:
            score += 10
        elif total_champions >= 5:
            score += 5
        
        # Score based on mastery score
        if mastery_score >= 100000:
            score += 20
        elif mastery_score >= 50000:
            score += 15
        elif mastery_score >= 20000:
            score += 10
        elif mastery_score >= 10000:
            score += 5
        
        # Bonus for high mastery champions
        high_mastery = analysis.get('high_mastery_count', 0)
        if high_mastery >= 5:
            score += 15
        elif high_mastery >= 3:
            score += 10
        elif high_mastery >= 1:
            score += 5
        
        # Bonus for recent activity
        if analysis.get('recent_activity', False):
            score += 5
        else:
            quality.outdated_fields.append("champion_mastery_data")
        
        return min(score, 100.0)
    
    def _calculate_performance_data_score(self, player: Player, quality: PlayerDataQuality) -> float:
        """Calculate score based on performance data availability."""
        if not player.performance_cache:
            quality.missing_fields.append("performance_data")
            return 0.0
        
        score = 0.0
        roles_with_data = 0
        
        for role, perf_data in player.performance_cache.items():
            if perf_data and isinstance(perf_data, dict):
                roles_with_data += 1
                
                # Check for key performance metrics
                if perf_data.get('matches_played', 0) > 0:
                    score += 10
                if 'win_rate' in perf_data:
                    score += 5
                if 'avg_kda' in perf_data:
                    score += 5
        
        # Bonus for multiple roles
        if roles_with_data >= 3:
            score += 20
        elif roles_with_data >= 2:
            score += 10
        elif roles_with_data >= 1:
            score += 5
        
        return min(score, 100.0)
    
    def _calculate_recency_score(self, player: Player, quality: PlayerDataQuality) -> float:
        """Calculate score based on data recency."""
        if not player.last_updated:
            quality.outdated_fields.append("last_updated")
            return 0.0
        
        days_since_update = (datetime.now() - player.last_updated).days
        
        if days_since_update <= 1:
            return 100.0
        elif days_since_update <= 7:
            return 80.0
        elif days_since_update <= 30:
            return 60.0
        elif days_since_update <= 90:
            return 40.0
        else:
            quality.outdated_fields.append("player_data")
            return 20.0
    
    def _generate_improvement_suggestions(self, quality: PlayerDataQuality):
        """Generate specific suggestions for improving data quality."""
        suggestions = []
        
        if quality.overall_score < 50:
            suggestions.append("Critical data quality issues detected - immediate attention required")
        
        if "puuid" in quality.missing_fields:
            suggestions.append("Validate summoner name with Riot API to fetch PUUID")
        
        if "champion_mastery_data" in quality.missing_fields:
            suggestions.append("Fetch champion mastery data to improve recommendations")
        
        if "performance_data" in quality.missing_fields:
            suggestions.append("Extract match history to calculate performance metrics")
        
        if "player_data" in quality.outdated_fields:
            suggestions.append("Update player data - information is outdated")
        
        if quality.api_validation_score < 50:
            suggestions.append("Re-validate summoner information with Riot API")
        
        if quality.mastery_data_score < 30:
            suggestions.append("Player appears to have limited champion experience")
        
        quality.improvement_suggestions = suggestions
    
    async def refresh_player_data(self, player: Player, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Refresh all player data including validation, mastery, and performance.
        
        Args:
            player: Player to refresh
            force_refresh: Force refresh even if data is recent
            
        Returns:
            Dictionary with refresh results and updated data
        """
        refresh_results = {
            'player_name': player.name,
            'refresh_timestamp': datetime.now(),
            'operations_performed': [],
            'errors': [],
            'data_quality_before': None,
            'data_quality_after': None
        }
        
        try:
            # Calculate initial data quality
            initial_quality = self.calculate_data_quality(player)
            refresh_results['data_quality_before'] = initial_quality
            
            # 1. Validate summoner if needed
            validation_result = None
            if not player.puuid or force_refresh:
                if player.summoner_name:
                    # Extract tag from summoner name if present
                    if '#' in player.summoner_name:
                        summoner_name, tag = player.summoner_name.split('#', 1)
                    else:
                        summoner_name = player.summoner_name
                        tag = "NA1"  # Default tag
                    
                    validation_result = await self.validate_summoner_real_time(
                        summoner_name, tag
                    )
                    
                    if validation_result.is_valid:
                        player.puuid = validation_result.details.get('puuid', '')
                        refresh_results['operations_performed'].append('summoner_validation')
                    else:
                        refresh_results['errors'].append(f"Summoner validation failed: {validation_result.message}")
            
            # 2. Fetch mastery data if we have PUUID
            mastery_data = None
            if player.puuid:
                mastery_data = await self.fetch_champion_mastery_data(player.puuid)
                if 'error' not in mastery_data:
                    # Update player's champion masteries
                    self._update_player_masteries(player, mastery_data)
                    refresh_results['operations_performed'].append('mastery_data_fetch')
                else:
                    refresh_results['errors'].append(f"Mastery data fetch failed: {mastery_data['error']}")
            
            # 3. Update last_updated timestamp
            player.last_updated = datetime.now()
            
            # Calculate final data quality
            final_quality = self.calculate_data_quality(player, validation_result, mastery_data)
            refresh_results['data_quality_after'] = final_quality
            
            # Add quality improvement info
            quality_improvement = final_quality.overall_score - initial_quality.overall_score
            refresh_results['quality_improvement'] = quality_improvement
            
            if quality_improvement > 0:
                refresh_results['operations_performed'].append('data_quality_improved')
            
        except Exception as e:
            self.logger.error(f"Error refreshing player data for {player.name}: {e}")
            refresh_results['errors'].append(f"Refresh failed: {str(e)}")
        
        return refresh_results
    
    def _update_player_masteries(self, player: Player, mastery_data: Dict[str, Any]):
        """Update player's champion mastery data from API response."""
        masteries = mastery_data.get('masteries', [])
        
        # Clear existing masteries
        player.champion_masteries.clear()
        
        # Add new mastery data
        for mastery_info in masteries:
            champion_id = mastery_info.get('championId')
            if champion_id:
                mastery = ChampionMastery(
                    champion_id=champion_id,
                    mastery_level=mastery_info.get('championLevel', 0),
                    mastery_points=mastery_info.get('championPoints', 0),
                    chest_granted=mastery_info.get('chestGranted', False),
                    tokens_earned=mastery_info.get('tokensEarned', 0),
                    last_play_time=datetime.fromtimestamp(
                        mastery_info.get('lastPlayTime', 0) / 1000
                    ) if mastery_info.get('lastPlayTime') else None
                )
                
                player.champion_masteries[champion_id] = mastery
    
    def get_validation_summary(self, players: List[Player]) -> Dict[str, Any]:
        """
        Get a summary of validation status for multiple players.
        
        Args:
            players: List of players to summarize
            
        Returns:
            Summary statistics and recommendations
        """
        summary = {
            'total_players': len(players),
            'validated_players': 0,
            'players_with_puuid': 0,
            'players_with_mastery_data': 0,
            'quality_distribution': {level.value: 0 for level in DataQualityLevel},
            'common_issues': {},
            'recommendations': []
        }
        
        for player in players:
            # Count validated players
            if player.puuid:
                summary['players_with_puuid'] += 1
            
            if player.champion_masteries:
                summary['players_with_mastery_data'] += 1
            
            # Calculate quality for summary
            quality = self.calculate_data_quality(player)
            summary['quality_distribution'][quality.quality_level.value] += 1
            
            # Collect common issues
            for issue in quality.quality_issues:
                summary['common_issues'][issue] = summary['common_issues'].get(issue, 0) + 1
        
        # Generate recommendations
        if summary['players_with_puuid'] < summary['total_players']:
            missing_puuid = summary['total_players'] - summary['players_with_puuid']
            summary['recommendations'].append(
                f"Validate {missing_puuid} players with Riot API to fetch PUUIDs"
            )
        
        if summary['players_with_mastery_data'] < summary['players_with_puuid']:
            missing_mastery = summary['players_with_puuid'] - summary['players_with_mastery_data']
            summary['recommendations'].append(
                f"Fetch mastery data for {missing_mastery} validated players"
            )
        
        critical_quality = summary['quality_distribution'][DataQualityLevel.CRITICAL.value]
        if critical_quality > 0:
            summary['recommendations'].append(
                f"Address critical data quality issues for {critical_quality} players"
            )
        
        return summary
    
    def cleanup_cache(self):
        """Clean up expired cache entries."""
        self.validation_cache.cleanup_expired()
    
    async def batch_validate_players(self, players: List[Player], 
                                   max_concurrent: int = 5) -> Dict[str, ValidationResult]:
        """
        Validate multiple players concurrently with rate limiting.
        
        Args:
            players: List of players to validate
            max_concurrent: Maximum concurrent validations
            
        Returns:
            Dictionary mapping player names to validation results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def validate_single_player(player: Player) -> Tuple[str, ValidationResult]:
            async with semaphore:
                if not player.summoner_name:
                    return player.name, ValidationResult(
                        status=ValidationStatus.INVALID,
                        is_valid=False,
                        message="No summoner name provided",
                        error_code="MISSING_SUMMONER_NAME"
                    )
                
                # Extract tag from summoner name if present
                if '#' in player.summoner_name:
                    summoner_name, tag = player.summoner_name.split('#', 1)
                else:
                    summoner_name = player.summoner_name
                    tag = "NA1"  # Default tag
                
                result = await self.validate_summoner_real_time(summoner_name, tag)
                return player.name, result
        
        # Create tasks for all players
        tasks = [validate_single_player(player) for player in players]
        
        # Execute with progress tracking
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in completed_results:
            if isinstance(result, Exception):
                self.logger.error(f"Validation task failed: {result}")
                continue
            
            player_name, validation_result = result
            results[player_name] = validation_result
        
        return results
    
    def get_data_refresh_recommendations(self, players: List[Player]) -> List[Dict[str, Any]]:
        """
        Get recommendations for data refresh based on player data age and quality.
        
        Args:
            players: List of players to analyze
            
        Returns:
            List of refresh recommendations with priorities
        """
        recommendations = []
        
        for player in players:
            quality = self.calculate_data_quality(player)
            
            # High priority: Critical quality or no PUUID
            if quality.quality_level == DataQualityLevel.CRITICAL or not player.puuid:
                recommendations.append({
                    'player_name': player.name,
                    'priority': 'HIGH',
                    'reason': 'Critical data quality issues',
                    'actions': ['validate_summoner', 'fetch_mastery_data'],
                    'estimated_improvement': 40.0
                })
            
            # Medium priority: Outdated data
            elif player.last_updated and (datetime.now() - player.last_updated).days > 7:
                recommendations.append({
                    'player_name': player.name,
                    'priority': 'MEDIUM',
                    'reason': 'Data is outdated (>7 days)',
                    'actions': ['refresh_mastery_data', 'update_performance_cache'],
                    'estimated_improvement': 15.0
                })
            
            # Low priority: Missing mastery data
            elif not player.champion_masteries and player.puuid:
                recommendations.append({
                    'player_name': player.name,
                    'priority': 'LOW',
                    'reason': 'Missing champion mastery data',
                    'actions': ['fetch_mastery_data'],
                    'estimated_improvement': 20.0
                })
        
        # Sort by priority and estimated improvement
        priority_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        recommendations.sort(
            key=lambda x: (priority_order[x['priority']], x['estimated_improvement']),
            reverse=True
        )
        
        return recommendations
    
    def create_validation_report(self, players: List[Player]) -> Dict[str, Any]:
        """
        Create a comprehensive validation report for all players.
        
        Args:
            players: List of players to report on
            
        Returns:
            Comprehensive validation report
        """
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_players': len(players),
            'summary': self.get_validation_summary(players),
            'player_details': [],
            'refresh_recommendations': self.get_data_refresh_recommendations(players),
            'cache_statistics': {
                'summoner_validations_cached': len(self.validation_cache.summoner_validations),
                'mastery_data_cached': len(self.validation_cache.mastery_data),
                'rank_data_cached': len(self.validation_cache.rank_data),
                'last_cache_cleanup': self.validation_cache.last_cleanup.isoformat()
            }
        }
        
        # Add detailed player information
        for player in players:
            quality = self.calculate_data_quality(player)
            
            player_detail = {
                'name': player.name,
                'summoner_name': player.summoner_name,
                'puuid': bool(player.puuid),
                'last_updated': player.last_updated.isoformat() if player.last_updated else None,
                'data_quality': {
                    'overall_score': quality.overall_score,
                    'quality_level': quality.quality_level.value,
                    'component_scores': {
                        'basic_info': quality.basic_info_score,
                        'api_validation': quality.api_validation_score,
                        'mastery_data': quality.mastery_data_score,
                        'performance_data': quality.performance_data_score,
                        'recency': quality.recency_score
                    },
                    'issues': quality.quality_issues,
                    'missing_fields': quality.missing_fields,
                    'outdated_fields': quality.outdated_fields,
                    'suggestions': quality.improvement_suggestions
                },
                'champion_masteries_count': len(player.champion_masteries),
                'role_preferences_complete': len(player.role_preferences) == 5,
                'performance_cache_roles': list(player.performance_cache.keys())
            }
            
            report['player_details'].append(player_detail)
        
        return report