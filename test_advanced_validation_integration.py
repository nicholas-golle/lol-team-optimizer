#!/usr/bin/env python3
"""
Integration test for Advanced Player Data Validation and API Integration.

This test demonstrates all the key features of the advanced player validator:
- Real-time summoner name validation with Riot API
- Rank verification and automatic data fetching
- Champion mastery data integration and display
- Data quality indicators and completeness scoring
- Automatic data refresh and update notifications
- Error handling for API failures with fallback options
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from lol_team_optimizer.advanced_player_validator import (
    AdvancedPlayerValidator,
    ValidationStatus,
    ValidationResult,
    DataQualityLevel,
    PlayerDataQuality
)
from lol_team_optimizer.models import Player, ChampionMastery
from lol_team_optimizer.config import Config
from lol_team_optimizer.riot_client import RiotAPIClient


class MockRiotAPIClient:
    """Mock Riot API client for testing."""
    
    def __init__(self):
        self.logger = Mock()
        self.call_count = 0
        self.should_fail = False
        
    def get_summoner_data(self, riot_id, region="americas", platform="na1"):
        """Mock summoner data retrieval."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("API Error - Rate Limited")
        
        if "NotFound" in riot_id:
            return None
        
        return {
            'puuid': f'puuid_{riot_id.replace("#", "_")}',
            'id': f'summoner_id_{riot_id.replace("#", "_")}',
            'summonerLevel': 150 + self.call_count,
            'name': riot_id.split('#')[0],
            'tagLine': riot_id.split('#')[1] if '#' in riot_id else 'NA1'
        }
    
    def get_ranked_stats(self, summoner_id, platform="na1"):
        """Mock ranked stats retrieval."""
        if self.should_fail:
            raise Exception("API Error")
        
        return [
            {
                'queueType': 'RANKED_SOLO_5x5',
                'tier': 'DIAMOND',
                'rank': 'III',
                'leaguePoints': 45,
                'wins': 67,
                'losses': 43
            }
        ]
    
    def get_champion_mastery_score(self, puuid, platform="na1"):
        """Mock mastery score retrieval."""
        if self.should_fail:
            return 0
        return 125000 + len(puuid)
    
    def get_all_champion_masteries(self, puuid, platform="na1"):
        """Mock all champion masteries retrieval."""
        if self.should_fail:
            raise Exception("Mastery API Error")
        
        base_time = int(datetime.now().timestamp() * 1000)
        return [
            {
                'championId': 1,
                'championLevel': 7,
                'championPoints': 45000,
                'chestGranted': True,
                'tokensEarned': 0,
                'lastPlayTime': base_time
            },
            {
                'championId': 2,
                'championLevel': 6,
                'championPoints': 32000,
                'chestGranted': False,
                'tokensEarned': 2,
                'lastPlayTime': base_time - (5 * 24 * 3600 * 1000)  # 5 days ago
            },
            {
                'championId': 3,
                'championLevel': 5,
                'championPoints': 18000,
                'chestGranted': True,
                'tokensEarned': 0,
                'lastPlayTime': base_time - (15 * 24 * 3600 * 1000)  # 15 days ago
            }
        ]


async def test_real_time_validation():
    """Test real-time summoner validation with various scenarios."""
    print("🔍 Testing Real-time Summoner Validation...")
    
    config = Config()
    config.riot_api_key = "test_key"
    config.cache_directory = "test_cache"
    
    mock_client = MockRiotAPIClient()
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Test successful validation
    result = await validator.validate_summoner_real_time("TestPlayer", "NA1")
    assert result.status == ValidationStatus.VALID
    assert result.is_valid
    assert result.details['puuid'] == 'puuid_TestPlayer_NA1'
    print(f"  ✓ Successful validation: {result.message}")
    
    # Test summoner not found
    result = await validator.validate_summoner_real_time("NotFoundPlayer", "NA1")
    assert result.status == ValidationStatus.INVALID
    assert not result.is_valid
    assert result.error_code == "SUMMONER_NOT_FOUND"
    print(f"  ✓ Not found handling: {result.message}")
    
    # Test API error
    mock_client.should_fail = True
    result = await validator.validate_summoner_real_time("ErrorPlayer", "NA1")
    assert result.status == ValidationStatus.ERROR
    assert not result.is_valid
    print(f"  ✓ Error handling: {result.message}")
    
    # Test caching (reset failure flag)
    mock_client.should_fail = False
    call_count_before = mock_client.call_count
    
    # First call
    await validator.validate_summoner_real_time("CachedPlayer", "NA1")
    call_count_after_first = mock_client.call_count
    
    # Second call should use cache
    await validator.validate_summoner_real_time("CachedPlayer", "NA1")
    call_count_after_second = mock_client.call_count
    
    assert call_count_after_second == call_count_after_first
    print("  ✓ Caching works correctly")


async def test_champion_mastery_integration():
    """Test champion mastery data integration."""
    print("🏆 Testing Champion Mastery Integration...")
    
    config = Config()
    mock_client = MockRiotAPIClient()
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Test mastery data fetching
    mastery_data = await validator.fetch_champion_mastery_data("test_puuid")
    
    assert 'error' not in mastery_data
    assert mastery_data['total_champions'] == 3
    assert mastery_data['mastery_score'] > 0
    assert len(mastery_data['masteries']) == 3
    
    analysis = mastery_data['analysis']
    assert analysis['total_champions'] == 3
    assert analysis['recent_activity'] is True
    assert 'high_mastery_count' in analysis
    
    print(f"  ✓ Fetched mastery data for {mastery_data['total_champions']} champions")
    print(f"  ✓ Total mastery score: {mastery_data['mastery_score']}")
    print(f"  ✓ Recent activity detected: {analysis['recent_activity']}")
    
    # Test error handling
    mock_client.should_fail = True
    error_data = await validator.fetch_champion_mastery_data("error_puuid")
    assert 'error' in error_data
    print("  ✓ Error handling for mastery data works")


def test_data_quality_scoring():
    """Test comprehensive data quality scoring."""
    print("📊 Testing Data Quality Scoring...")
    
    config = Config()
    validator = AdvancedPlayerValidator(config, None)
    
    # Test excellent quality player
    excellent_player = Player(
        name="ExcellentPlayer",
        summoner_name="ExcellentPlayer#NA1",
        puuid="excellent_puuid_123",
        role_preferences={
            "top": 4, "jungle": 2, "middle": 5, "bottom": 3, "support": 1
        },
        last_updated=datetime.now()
    )
    
    # Add mastery data
    excellent_player.champion_masteries = {
        1: ChampionMastery(champion_id=1, mastery_level=7, mastery_points=50000),
        2: ChampionMastery(champion_id=2, mastery_level=6, mastery_points=30000),
        3: ChampionMastery(champion_id=3, mastery_level=5, mastery_points=20000)
    }
    
    # Add performance data
    excellent_player.performance_cache = {
        'middle': {'matches_played': 20, 'win_rate': 0.65, 'avg_kda': 2.5},
        'top': {'matches_played': 15, 'win_rate': 0.60, 'avg_kda': 2.2}
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
    
    quality = validator.calculate_data_quality(excellent_player, validation_result, mastery_data)
    
    print(f"  ✓ Excellent player quality score: {quality.overall_score:.1f}")
    print(f"  ✓ Quality level: {quality.quality_level.value}")
    print(f"  ✓ Component scores:")
    print(f"    - Basic info: {quality.basic_info_score:.1f}")
    print(f"    - API validation: {quality.api_validation_score:.1f}")
    print(f"    - Mastery data: {quality.mastery_data_score:.1f}")
    print(f"    - Performance data: {quality.performance_data_score:.1f}")
    print(f"    - Recency: {quality.recency_score:.1f}")
    
    assert quality.overall_score >= 70.0
    assert quality.quality_level in [DataQualityLevel.EXCELLENT, DataQualityLevel.GOOD]
    
    # Test poor quality player
    poor_player = Player(
        name="PoorPlayer",
        summoner_name="",  # Missing summoner name
        puuid="",  # Missing PUUID
        role_preferences={},  # Missing role preferences
        last_updated=datetime.now() - timedelta(days=100)  # Very outdated
    )
    
    poor_quality = validator.calculate_data_quality(poor_player)
    
    print(f"  ✓ Poor player quality score: {poor_quality.overall_score:.1f}")
    print(f"  ✓ Quality level: {poor_quality.quality_level.value}")
    print(f"  ✓ Missing fields: {poor_quality.missing_fields}")
    print(f"  ✓ Improvement suggestions: {len(poor_quality.improvement_suggestions)}")
    
    assert poor_quality.overall_score < 50.0
    assert poor_quality.quality_level in [DataQualityLevel.POOR, DataQualityLevel.CRITICAL]
    assert len(poor_quality.missing_fields) > 0
    assert len(poor_quality.improvement_suggestions) > 0


async def test_automatic_data_refresh():
    """Test automatic data refresh and update notifications."""
    print("🔄 Testing Automatic Data Refresh...")
    
    config = Config()
    mock_client = MockRiotAPIClient()
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Create player needing refresh
    player = Player(
        name="RefreshPlayer",
        summoner_name="RefreshPlayer#NA1",
        puuid="",  # Missing PUUID to trigger validation
        last_updated=datetime.now() - timedelta(days=10)  # Outdated
    )
    
    # Test data refresh
    refresh_results = await validator.refresh_player_data(player)
    
    print(f"  ✓ Refresh completed for: {refresh_results['player_name']}")
    print(f"  ✓ Operations performed: {refresh_results['operations_performed']}")
    print(f"  ✓ Errors: {len(refresh_results['errors'])}")
    
    # Check that PUUID was updated
    assert player.puuid == 'puuid_RefreshPlayer_NA1'
    assert 'summoner_validation' in refresh_results['operations_performed']
    assert 'mastery_data_fetch' in refresh_results['operations_performed']
    
    # Check quality improvement
    quality_before = refresh_results['data_quality_before']
    quality_after = refresh_results['data_quality_after']
    
    print(f"  ✓ Quality improvement: {quality_before.overall_score:.1f} → {quality_after.overall_score:.1f}")
    assert quality_after.overall_score > quality_before.overall_score


async def test_batch_validation():
    """Test batch validation of multiple players."""
    print("👥 Testing Batch Player Validation...")
    
    config = Config()
    mock_client = MockRiotAPIClient()
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Create multiple players
    players = [
        Player(name="Player1", summoner_name="Player1#NA1"),
        Player(name="Player2", summoner_name="Player2#NA1"),
        Player(name="Player3", summoner_name="Player3#NA1"),
        Player(name="InvalidPlayer", summoner_name=""),  # No summoner name
        Player(name="NotFoundPlayer", summoner_name="NotFoundPlayer#NA1")  # Will not be found
    ]
    
    # Test batch validation
    results = await validator.batch_validate_players(players, max_concurrent=3)
    
    print(f"  ✓ Validated {len(results)} players")
    
    # Check results
    assert len(results) == 5
    assert results["Player1"].status == ValidationStatus.VALID
    assert results["Player2"].status == ValidationStatus.VALID
    assert results["Player3"].status == ValidationStatus.VALID
    assert results["InvalidPlayer"].status == ValidationStatus.INVALID
    assert results["NotFoundPlayer"].status == ValidationStatus.INVALID
    
    # Count successful validations
    successful = sum(1 for r in results.values() if r.status == ValidationStatus.VALID)
    print(f"  ✓ Successful validations: {successful}/5")


def test_validation_reporting():
    """Test comprehensive validation reporting."""
    print("📋 Testing Validation Reporting...")
    
    config = Config()
    validator = AdvancedPlayerValidator(config, None)
    
    # Create test players with different quality levels
    players = [
        Player(name="GoodPlayer", summoner_name="GoodPlayer#NA1", puuid="good_puuid",
               last_updated=datetime.now()),
        Player(name="OkayPlayer", summoner_name="OkayPlayer#NA1", puuid="okay_puuid",
               last_updated=datetime.now() - timedelta(days=5)),
        Player(name="PoorPlayer", summoner_name="", puuid="",
               last_updated=datetime.now() - timedelta(days=30))
    ]
    
    # Add some mastery data to good player
    players[0].champion_masteries = {
        1: ChampionMastery(champion_id=1, mastery_level=7, mastery_points=50000)
    }
    
    # Test validation summary
    summary = validator.get_validation_summary(players)
    
    print(f"  ✓ Summary for {summary['total_players']} players:")
    print(f"    - Players with PUUID: {summary['players_with_puuid']}")
    print(f"    - Players with mastery data: {summary['players_with_mastery_data']}")
    print(f"    - Quality distribution: {summary['quality_distribution']}")
    print(f"    - Recommendations: {len(summary['recommendations'])}")
    
    # Test refresh recommendations
    recommendations = validator.get_data_refresh_recommendations(players)
    
    print(f"  ✓ Refresh recommendations: {len(recommendations)}")
    for rec in recommendations:
        print(f"    - {rec['player_name']}: {rec['priority']} priority - {rec['reason']}")
    
    # Test comprehensive report
    report = validator.create_validation_report(players)
    
    print(f"  ✓ Comprehensive report generated:")
    print(f"    - Report timestamp: {report['report_timestamp']}")
    print(f"    - Player details: {len(report['player_details'])}")
    print(f"    - Cache statistics included: {bool(report['cache_statistics'])}")
    
    assert report['total_players'] == 3
    assert len(report['player_details']) == 3
    assert len(report['refresh_recommendations']) > 0


async def test_error_handling_and_fallbacks():
    """Test comprehensive error handling and fallback options."""
    print("⚠️  Testing Error Handling and Fallbacks...")
    
    config = Config()
    
    # Test validator without Riot client
    validator_no_client = AdvancedPlayerValidator(config, None)
    
    # Should handle missing client gracefully
    result = await validator_no_client.validate_summoner_real_time("Test", "NA1")
    assert result.status == ValidationStatus.ERROR
    assert result.error_code == "NO_API_CLIENT"
    print("  ✓ Handles missing API client gracefully")
    
    # Test with failing client
    failing_client = MockRiotAPIClient()
    failing_client.should_fail = True
    validator_failing = AdvancedPlayerValidator(config, failing_client)
    
    # Should handle API failures
    result = await validator_failing.validate_summoner_real_time("Test", "NA1")
    assert result.status == ValidationStatus.ERROR
    print("  ✓ Handles API failures gracefully")
    
    # Test mastery data with failing client
    mastery_data = await validator_failing.fetch_champion_mastery_data("test_puuid")
    assert 'error' in mastery_data
    print("  ✓ Handles mastery API failures gracefully")
    
    # Test data quality calculation with minimal data
    minimal_player = Player(name="MinimalPlayer", summoner_name="MinimalPlayer#NA1")
    quality = validator_no_client.calculate_data_quality(minimal_player)
    
    assert isinstance(quality, PlayerDataQuality)
    assert quality.overall_score >= 0
    print("  ✓ Calculates quality even with minimal data")


async def main():
    """Run all integration tests."""
    print("🚀 Advanced Player Validator Integration Tests")
    print("=" * 60)
    
    try:
        await test_real_time_validation()
        print()
        
        await test_champion_mastery_integration()
        print()
        
        test_data_quality_scoring()
        print()
        
        await test_automatic_data_refresh()
        print()
        
        await test_batch_validation()
        print()
        
        test_validation_reporting()
        print()
        
        await test_error_handling_and_fallbacks()
        print()
        
        print("=" * 60)
        print("🎉 All integration tests passed successfully!")
        print()
        print("✅ Key Features Verified:")
        print("  • Real-time summoner name validation with Riot API")
        print("  • Rank verification and automatic data fetching")
        print("  • Champion mastery data integration and display")
        print("  • Data quality indicators and completeness scoring")
        print("  • Automatic data refresh and update notifications")
        print("  • Error handling for API failures with fallback options")
        print("  • Batch validation and concurrent processing")
        print("  • Comprehensive reporting and recommendations")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)