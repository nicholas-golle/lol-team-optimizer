#!/usr/bin/env python3
"""
Simple test to verify the advanced player validator functionality.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock

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


def test_basic_functionality():
    """Test basic validator functionality."""
    print("Testing basic validator functionality...")
    
    # Create config
    config = Config()
    config.riot_api_key = "test_api_key"
    config.riot_api_rate_limit = 100
    config.cache_directory = "test_cache"
    
    # Create mock riot client
    mock_client = Mock(spec=RiotAPIClient)
    mock_client.get_summoner_data.return_value = {
        'puuid': 'test_puuid_123',
        'id': 'test_summoner_id',
        'summonerLevel': 150,
        'name': 'TestPlayer',
        'tagLine': 'NA1'
    }
    mock_client.get_ranked_stats.return_value = [
        {
            'queueType': 'RANKED_SOLO_5x5',
            'tier': 'DIAMOND',
            'rank': 'III',
            'leaguePoints': 45,
            'wins': 67,
            'losses': 43
        }
    ]
    mock_client.get_champion_mastery_score.return_value = 125000
    mock_client.get_all_champion_masteries.return_value = [
        {
            'championId': 1,
            'championLevel': 7,
            'championPoints': 45000,
            'chestGranted': True,
            'tokensEarned': 0,
            'lastPlayTime': int(datetime.now().timestamp() * 1000)
        }
    ]
    
    # Create validator
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Test data quality calculation
    player = Player(
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
    
    quality = validator.calculate_data_quality(player)
    print(f"Data quality score: {quality.overall_score}")
    print(f"Quality level: {quality.quality_level}")
    print(f"Missing fields: {quality.missing_fields}")
    print(f"Quality issues: {quality.quality_issues}")
    
    assert quality.overall_score > 0
    assert isinstance(quality.quality_level, DataQualityLevel)
    
    print("✓ Basic functionality test passed!")


async def test_async_validation():
    """Test async validation functionality."""
    print("Testing async validation...")
    
    # Create config
    config = Config()
    config.riot_api_key = "test_api_key"
    config.riot_api_rate_limit = 100
    config.cache_directory = "test_cache"
    
    # Create mock riot client
    mock_client = Mock(spec=RiotAPIClient)
    mock_client.get_summoner_data.return_value = {
        'puuid': 'test_puuid_123',
        'id': 'test_summoner_id',
        'summonerLevel': 150
    }
    mock_client.get_ranked_stats.return_value = []
    mock_client.get_champion_mastery_score.return_value = 0
    
    # Create validator
    validator = AdvancedPlayerValidator(config, mock_client)
    
    # Test validation
    result = await validator.validate_summoner_real_time("TestPlayer", "NA1")
    
    print(f"Validation status: {result.status}")
    print(f"Is valid: {result.is_valid}")
    print(f"Message: {result.message}")
    
    assert isinstance(result, ValidationResult)
    assert result.status in [ValidationStatus.VALID, ValidationStatus.ERROR]
    
    print("✓ Async validation test passed!")


def test_validation_summary():
    """Test validation summary functionality."""
    print("Testing validation summary...")
    
    config = Config()
    validator = AdvancedPlayerValidator(config, None)
    
    players = [
        Player(name="Player1", summoner_name="Player1#NA1", puuid="puuid1"),
        Player(name="Player2", summoner_name="Player2#NA1", puuid=""),
        Player(name="Player3", summoner_name="", puuid="")
    ]
    
    summary = validator.get_validation_summary(players)
    
    print(f"Total players: {summary['total_players']}")
    print(f"Players with PUUID: {summary['players_with_puuid']}")
    print(f"Recommendations: {summary['recommendations']}")
    
    assert summary['total_players'] == 3
    assert summary['players_with_puuid'] == 1
    assert len(summary['recommendations']) > 0
    
    print("✓ Validation summary test passed!")


def main():
    """Run all tests."""
    print("Running Advanced Player Validator Tests...")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        print()
        
        asyncio.run(test_async_validation())
        print()
        
        test_validation_summary()
        print()
        
        print("=" * 50)
        print("All tests passed! ✓")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)