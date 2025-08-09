"""
Tests for Advanced Player Data Validation and API Integration

This module tests the comprehensive player validation system including:
- Real-time summoner validation
- Champion mastery integration
- Data quality assessment
- Error handling and fallback options
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from lol_team_optimizer.advanced_player_validator import (
    AdvancedPlayerValidator,
    ValidationStatus,
    ValidationResult,
    DataQualityLevel,
    PlayerDataQuality,
    APIValidationCache
)
from lol_team_optimizer.models import Player, ChampionMastery
from lol_team_optimizer.config import Config
from lol_team_optimizer.riot_client import RiotAPIClient


class TestAdvancedPlayerValidator:
    """Test suite for AdvancedPlayerValidator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.riot_api_key = "test_api_key"
        config.riot_api_rate_limit = 100
        config.cache_directory = "test_cache"
        return config
    
    @pytest.fixture
    def mock_riot_client(self):
        """Create mock Riot API client."""
        client = Mock(spec=RiotAPIClient)
        
        # Mock successful summoner data response
        client.get_summoner_data.return_value = {
            'puuid': 'test_puuid_123',
            'id': 'test_summoner_id',
            'summonerLevel': 150,
            'name': 'TestPlayer',
            'tagLine': 'NA1'
        }
        
        # Mock ranked stats response
        client.get_ranked_stats.return_value = [
            {
                'queueType': 'RANKED_SOLO_5x5',
                'tier': 'DIAMOND',
                'rank': 'III',
                'leaguePoints': 45,
                'wins': 67,
                'losses': 43
            }
        ]
        
        # Mock mastery score response
        client.get_champion_mastery_score.return_value = 125000
        
        # Add logger attribute
        client.logger = Mock()
        
        # Mock all champion masteries response
        client.get_all_champion_masteries.return_value = [
            {
                'championId': 1,
                'championLevel': 7,
                'championPoints': 45000,
                'chestGranted': True,
                'tokensEarned': 0,
                'lastPlayTime': int(datetime.now().timestamp() * 1000)
            },
            {
                'championId': 2,
                'championLevel': 6,
                'championPoints': 32000,
                'chestGranted': False,
                'tokensEarned': 2,
                'lastPlayTime': int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
            }
        ]
        
        return client
    
    @pytest.fixture
    def validator(self, config, mock_riot_client):
        """Create validator instance with mocked dependencies."""
        return AdvancedPlayerValidator(config, mock_riot_client)
    
    @pytest.fixture
    def sample_player(self):
        """Create sample player for testing."""
        return Player(
            name="TestPlayer",
            summoner_name="TestSummoner#NA1",
            puuid="test_puuid_123",
            role_preferences={
                "top": 4,
                "jungle": 2,
                "middle": 5,
                "bottom": 3,
                "support": 1
            },
            last_updated=datetime.now() - timedelta(days=1)
        )
    
    @pytest.mark.asyncio
    async def test_validate_summoner_real_time_success(self, validator):
        """Test successful real-time summoner validation."""
        result = await validator.validate_summoner_real_time("TestPlayer", "NA1")
        
        assert result.status == ValidationStatus.VALID
        assert result.is_valid is True
        assert "TestPlayer#NA1 validated successfully" in result.message
        assert result.details['puuid'] == 'test_puuid_123'
        assert result.details['summoner_level'] == 150
        assert result.details['rank_data'] is not None
        assert result.details['mastery_score'] == 125000
    
    @pytest.mark.asyncio
    async def test_validate_summoner_real_time_not_found(self, validator, mock_riot_client):
        """Test summoner validation when summoner is not found."""
        mock_riot_client.get_summoner_data.return_value = None
        
        result = await validator.validate_summoner_real_time("NonExistentPlayer", "NA1")
        
        assert result.status == ValidationStatus.INVALID
        assert result.is_valid is False
        assert "not found" in result.message
        assert result.error_code == "SUMMONER_NOT_FOUND"
        assert len(result.suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_validate_summoner_real_time_api_error(self, validator, mock_riot_client):
        """Test summoner validation with API error."""
        mock_riot_client.get_summoner_data.side_effect = Exception("API Error")
        
        result = await validator.validate_summoner_real_time("TestPlayer", "NA1")
        
        assert result.status == ValidationStatus.ERROR
        assert result.is_valid is False
        assert "API Error" in result.message
        assert result.error_code == "RETRY_EXHAUSTED"
    
    @pytest.mark.asyncio
    async def test_validate_summoner_real_time_timeout(self, validator):
        """Test summoner validation timeout."""
        validator.validation_timeout = 0.001  # Very short timeout
        
        result = await validator.validate_summoner_real_time("TestPlayer", "NA1")
        
        assert result.status == ValidationStatus.TIMEOUT
        assert result.is_valid is False
        assert "timed out" in result.message
        assert result.error_code == "TIMEOUT"
    
    @pytest.mark.asyncio
    async def test_validate_summoner_real_time_caching(self, validator):
        """Test that validation results are properly cached."""
        # First call
        result1 = await validator.validate_summoner_real_time("TestPlayer", "NA1")
        
        # Second call should use cache
        result2 = await validator.validate_summoner_real_time("TestPlayer", "NA1")
        
        assert result1.status == result2.status
        assert result1.details == result2.details
        
        # Verify only one API call was made
        validator.riot_client.get_summoner_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_champion_mastery_data_success(self, validator):
        """Test successful champion mastery data fetching."""
        mastery_data = await validator.fetch_champion_mastery_data("test_puuid_123")
        
        assert 'error' not in mastery_data
        assert mastery_data['total_champions'] == 2
        assert mastery_data['mastery_score'] == 125000
        assert len(mastery_data['masteries']) == 2
        assert mastery_data['analysis']['total_champions'] == 2
        assert mastery_data['analysis']['recent_activity'] is True
    
    @pytest.mark.asyncio
    async def test_fetch_champion_mastery_data_no_client(self, config):
        """Test mastery data fetching without Riot client."""
        validator = AdvancedPlayerValidator(config, None)
        
        mastery_data = await validator.fetch_champion_mastery_data("test_puuid_123")
        
        assert 'error' in mastery_data
        assert mastery_data['error'] == 'Riot API client not available'
    
    @pytest.mark.asyncio
    async def test_fetch_champion_mastery_data_api_error(self, validator, mock_riot_client):
        """Test mastery data fetching with API error."""
        mock_riot_client.get_all_champion_masteries.side_effect = Exception("API Error")
        
        mastery_data = await validator.fetch_champion_mastery_data("test_puuid_123")
        
        assert 'error' in mastery_data
        assert "API Error" in mastery_data['error']
    
    def test_calculate_data_quality_excellent(self, validator, sample_player):
        """Test data quality calculation for excellent quality player."""
        # Add mastery data
        sample_player.champion_masteries = {
            1: ChampionMastery(champion_id=1, mastery_level=7, mastery_points=50000),
            2: ChampionMastery(champion_id=2, mastery_level=6, mastery_points=30000)
        }
        
        # Add performance data
        sample_player.performance_cache = {
            'middle': {'matches_played': 20, 'win_rate': 0.65, 'avg_kda': 2.5}
        }
        
        # Mock validation result
        validation_result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Valid",
            details={'rank_data': [{'tier': 'DIAMOND'}], 'mastery_score': 80000}
        )
        
        # Mock mastery data
        mastery_data = {
            'total_champions': 50,
            'mastery_score': 80000,
            'analysis': {
                'total_champions': 50,
                'high_mastery_count': 5,
                'recent_activity': True
            }
        }
        
        quality = validator.calculate_data_quality(sample_player, validation_result, mastery_data)
        
        assert quality.overall_score >= 80.0
        assert quality.quality_level in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD]
        assert quality.basic_info_score > 80.0
        assert quality.api_validation_score > 90.0
        assert len(quality.missing_fields) == 0
    
    def test_calculate_data_quality_poor(self, validator):
        """Test data quality calculation for poor quality player."""
        poor_player = Player(
            name="PoorPlayer",
            summoner_name="",  # Missing summoner name
            puuid="",  # Missing PUUID
            role_preferences={},  # Missing role preferences
            last_updated=datetime.now() - timedelta(days=100)  # Very outdated
        )
        
        quality = validator.calculate_data_quality(poor_player)
        
        assert quality.overall_score < 50.0
        assert quality.quality_level in [DataQualityLevel.POOR, DataQualityLevel.CRITICAL]
        assert "summoner_name" in quality.missing_fields
        assert "puuid" in quality.missing_fields
        assert "role_preferences" in quality.missing_fields
        assert len(quality.improvement_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_refresh_player_data_success(self, validator, sample_player):
        """Test successful player data refresh."""
        # Remove PUUID to trigger validation
        sample_player.puuid = ""
        
        refresh_results = await validator.refresh_player_data(sample_player)
        
        assert refresh_results['player_name'] == sample_player.name
        assert 'summoner_validation' in refresh_results['operations_performed']
        assert 'mastery_data_fetch' in refresh_results['operations_performed']
        assert len(refresh_results['errors']) == 0
        assert refresh_results['data_quality_after'] is not None
        assert sample_player.puuid == 'test_puuid_123'  # Should be updated
    
    @pytest.mark.asyncio
    async def test_refresh_player_data_no_summoner_name(self, validator):
        """Test player data refresh with no summoner name."""
        player = Player(name="TestPlayer", summoner_name="")
        
        refresh_results = await validator.refresh_player_data(player)
        
        assert len(refresh_results['errors']) > 0
        assert refresh_results['data_quality_before'] is not None
        assert refresh_results['data_quality_after'] is not None
    
    @pytest.mark.asyncio
    async def test_batch_validate_players_success(self, validator):
        """Test successful batch validation of multiple players."""
        players = [
            Player(name="Player1", summoner_name="Player1#NA1"),
            Player(name="Player2", summoner_name="Player2#NA1"),
            Player(name="Player3", summoner_name="Player3#NA1")
        ]
        
        results = await validator.batch_validate_players(players, max_concurrent=2)
        
        assert len(results) == 3
        for player_name, result in results.items():
            assert isinstance(result, ValidationResult)
            assert result.status == ValidationStatus.VALID
    
    @pytest.mark.asyncio
    async def test_batch_validate_players_mixed_results(self, validator, mock_riot_client):
        """Test batch validation with mixed success/failure results."""
        players = [
            Player(name="ValidPlayer", summoner_name="ValidPlayer#NA1"),
            Player(name="InvalidPlayer", summoner_name=""),  # No summoner name
            Player(name="ErrorPlayer", summoner_name="ErrorPlayer#NA1")
        ]
        
        # Mock API to fail for ErrorPlayer
        def mock_get_summoner_data(riot_id, region, platform):
            if "ErrorPlayer" in riot_id:
                raise Exception("API Error")
            return validator.riot_client.get_summoner_data.return_value
        
        mock_riot_client.get_summoner_data.side_effect = mock_get_summoner_data
        
        results = await validator.batch_validate_players(players)
        
        assert len(results) == 3
        assert results["ValidPlayer"].status == ValidationStatus.VALID
        assert results["InvalidPlayer"].status == ValidationStatus.INVALID
        assert results["ErrorPlayer"].status == ValidationStatus.ERROR
    
    def test_get_validation_summary(self, validator):
        """Test validation summary generation."""
        players = [
            Player(name="Player1", summoner_name="Player1#NA1", puuid="puuid1"),
            Player(name="Player2", summoner_name="Player2#NA1", puuid=""),
            Player(name="Player3", summoner_name="", puuid="")
        ]
        
        # Add mastery data to first player
        players[0].champion_masteries = {
            1: ChampionMastery(champion_id=1, mastery_level=7, mastery_points=50000)
        }
        
        summary = validator.get_validation_summary(players)
        
        assert summary['total_players'] == 3
        assert summary['players_with_puuid'] == 1
        assert summary['players_with_mastery_data'] == 1
        assert len(summary['recommendations']) > 0
        assert any("Validate" in rec for rec in summary['recommendations'])
    
    def test_get_data_refresh_recommendations(self, validator):
        """Test data refresh recommendations generation."""
        players = [
            # High priority: no PUUID
            Player(name="Player1", summoner_name="Player1#NA1", puuid=""),
            
            # Medium priority: outdated data
            Player(name="Player2", summoner_name="Player2#NA1", puuid="puuid2",
                  last_updated=datetime.now() - timedelta(days=10)),
            
            # Low priority: missing mastery data
            Player(name="Player3", summoner_name="Player3#NA1", puuid="puuid3",
                  last_updated=datetime.now())
        ]
        
        recommendations = validator.get_data_refresh_recommendations(players)
        
        assert len(recommendations) == 3
        assert recommendations[0]['priority'] == 'HIGH'
        assert recommendations[1]['priority'] == 'MEDIUM'
        assert recommendations[2]['priority'] == 'LOW'
        
        # Check that recommendations are sorted by priority
        priorities = [rec['priority'] for rec in recommendations]
        assert priorities == ['HIGH', 'MEDIUM', 'LOW']
    
    def test_create_validation_report(self, validator, sample_player):
        """Test comprehensive validation report creation."""
        players = [sample_player]
        
        report = validator.create_validation_report(players)
        
        assert 'report_timestamp' in report
        assert report['total_players'] == 1
        assert 'summary' in report
        assert 'player_details' in report
        assert 'refresh_recommendations' in report
        assert 'cache_statistics' in report
        
        # Check player details
        player_detail = report['player_details'][0]
        assert player_detail['name'] == sample_player.name
        assert 'data_quality' in player_detail
        assert 'overall_score' in player_detail['data_quality']
        assert 'component_scores' in player_detail['data_quality']
    
    def test_cache_cleanup(self, validator):
        """Test cache cleanup functionality."""
        # Add some test data to cache
        old_timestamp = datetime.now() - timedelta(hours=25)
        recent_timestamp = datetime.now() - timedelta(hours=1)
        
        validator.validation_cache.summoner_validations['old_key'] = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Old validation",
            timestamp=old_timestamp
        )
        
        validator.validation_cache.summoner_validations['recent_key'] = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Recent validation",
            timestamp=recent_timestamp
        )
        
        # Cleanup should remove old entries
        validator.cleanup_cache()
        
        assert 'old_key' not in validator.validation_cache.summoner_validations
        assert 'recent_key' in validator.validation_cache.summoner_validations


class TestValidationResult:
    """Test suite for ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation with default values."""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Test validation"
        )
        
        assert result.status == ValidationStatus.VALID
        assert result.is_valid is True
        assert result.message == "Test validation"
        assert isinstance(result.details, dict)
        assert isinstance(result.timestamp, datetime)
        assert result.error_code is None
        assert isinstance(result.suggestions, list)


class TestPlayerDataQuality:
    """Test suite for PlayerDataQuality dataclass."""
    
    def test_quality_level_calculation(self):
        """Test automatic quality level calculation based on score."""
        # Test excellent quality
        excellent = PlayerDataQuality(player_name="Test", overall_score=95.0)
        assert excellent.quality_level == DataQualityLevel.EXCELLENT
        
        # Test good quality
        good = PlayerDataQuality(player_name="Test", overall_score=75.0)
        assert good.quality_level == DataQualityLevel.GOOD
        
        # Test fair quality
        fair = PlayerDataQuality(player_name="Test", overall_score=55.0)
        assert fair.quality_level == DataQualityLevel.FAIR
        
        # Test poor quality
        poor = PlayerDataQuality(player_name="Test", overall_score=35.0)
        assert poor.quality_level == DataQualityLevel.POOR
        
        # Test critical quality
        critical = PlayerDataQuality(player_name="Test", overall_score=15.0)
        assert critical.quality_level == DataQualityLevel.CRITICAL


class TestAPIValidationCache:
    """Test suite for APIValidationCache."""
    
    def test_cache_cleanup_expired(self):
        """Test cleanup of expired cache entries."""
        cache = APIValidationCache()
        
        # Add expired and recent entries
        old_timestamp = datetime.now() - timedelta(hours=25)
        recent_timestamp = datetime.now() - timedelta(hours=1)
        
        cache.summoner_validations['old'] = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Old",
            timestamp=old_timestamp
        )
        
        cache.summoner_validations['recent'] = ValidationResult(
            status=ValidationStatus.VALID,
            is_valid=True,
            message="Recent",
            timestamp=recent_timestamp
        )
        
        cache.mastery_data['old'] = {'timestamp': old_timestamp, 'data': 'old'}
        cache.mastery_data['recent'] = {'timestamp': recent_timestamp, 'data': 'recent'}
        
        # Cleanup with 24 hour max age
        cache.cleanup_expired(max_age_hours=24)
        
        # Old entries should be removed
        assert 'old' not in cache.summoner_validations
        assert 'recent' in cache.summoner_validations
        assert 'old' not in cache.mastery_data
        assert 'recent' in cache.mastery_data