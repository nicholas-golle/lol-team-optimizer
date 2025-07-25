"""
Unit tests for the Riot API client.

Tests the RiotAPIClient class with mocked API responses to verify
rate limiting, caching, error handling, and data processing functionality.
"""

import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import requests

from lol_team_optimizer.riot_client import RiotAPIClient, RateLimiter, CacheEntry
from lol_team_optimizer.config import Config


class TestRateLimiter:
    """Test the RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(max_requests=100, time_window=60)
        assert limiter.max_requests == 100
        assert limiter.time_window == 60
        assert limiter.requests == []
    
    def test_can_make_request_when_empty(self):
        """Test that requests are allowed when no previous requests."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        assert limiter.can_make_request() is True
    
    def test_can_make_request_under_limit(self):
        """Test that requests are allowed under the limit."""
        limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Make 4 requests
        for _ in range(4):
            limiter.record_request()
        
        assert limiter.can_make_request() is True
    
    def test_cannot_make_request_at_limit(self):
        """Test that requests are blocked at the limit."""
        limiter = RateLimiter(max_requests=3, time_window=60)
        
        # Make 3 requests
        for _ in range(3):
            limiter.record_request()
        
        assert limiter.can_make_request() is False
    
    def test_old_requests_are_cleaned_up(self):
        """Test that old requests outside time window are removed."""
        limiter = RateLimiter(max_requests=2, time_window=1)  # 1 second window
        
        # Record a request
        limiter.record_request()
        assert limiter.can_make_request() is True
        
        # Record another request (at limit)
        limiter.record_request()
        assert limiter.can_make_request() is False
        
        # Wait for time window to pass
        time.sleep(1.1)
        
        # Should be able to make requests again
        assert limiter.can_make_request() is True
    
    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_requests=1, time_window=10)
        
        # No wait time when under limit
        assert limiter.wait_time() == 0.0
        
        # Record a request to hit the limit
        limiter.record_request()
        
        # Should have wait time close to the time window
        wait_time = limiter.wait_time()
        assert 9 <= wait_time <= 10


class TestRiotAPIClient:
    """Test the RiotAPIClient class."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return Config(
            riot_api_key="test_api_key",
            riot_api_base_url="https://test.api.riotgames.com",
            cache_duration_hours=1,
            max_retries=3,
            retry_backoff_factor=2.0,
            request_timeout_seconds=30,
            cache_directory="test_cache"
        )
    
    @pytest.fixture
    def client(self, config, tmp_path):
        """Create a test client with temporary cache directory."""
        config.cache_directory = str(tmp_path / "cache")
        return RiotAPIClient(config)
    
    def test_client_initialization(self, client, config):
        """Test client initializes correctly."""
        assert client.config == config
        assert client.rate_limiter.max_requests == config.riot_api_rate_limit
        assert client.session.headers['X-Riot-Token'] == config.riot_api_key
        assert client.cache == {}
    
    def test_cache_key_generation(self, client):
        """Test cache key generation is deterministic."""
        endpoint = "/test/endpoint"
        params = {"param1": "value1", "param2": "value2"}
        
        key1 = client._get_cache_key(endpoint, params)
        key2 = client._get_cache_key(endpoint, params)
        
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length
    
    def test_cache_storage_and_retrieval(self, client):
        """Test data can be stored and retrieved from cache."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Store data
        client._store_in_cache(cache_key, test_data)
        
        # Retrieve data
        retrieved_data = client._get_from_cache(cache_key)
        assert retrieved_data == test_data
    
    def test_cache_expiration(self, client):
        """Test that expired cache entries are not returned."""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Manually create expired cache entry
        expired_time = datetime.now() - timedelta(hours=2)
        client.cache[cache_key] = CacheEntry(
            data=test_data,
            timestamp=expired_time,
            expires_at=expired_time
        )
        
        # Should return None for expired entry
        retrieved_data = client._get_from_cache(cache_key)
        assert retrieved_data is None
        assert cache_key not in client.cache  # Should be cleaned up
    
    @patch('requests.Session.get')
    def test_successful_api_request(self, mock_get, client):
        """Test successful API request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "response"}
        mock_get.return_value = mock_response
        
        result = client._make_request("/test/endpoint", {"param": "value"})
        
        assert result == {"test": "response"}
        mock_get.assert_called_once()
    
    @patch('requests.Session.get')
    def test_api_request_with_caching(self, mock_get, client):
        """Test that cached responses are returned without API calls."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "response"}
        mock_get.return_value = mock_response
        
        endpoint = "/test/endpoint"
        params = {"param": "value"}
        
        # First request should call API
        result1 = client._make_request(endpoint, params)
        assert mock_get.call_count == 1
        
        # Second request should use cache
        result2 = client._make_request(endpoint, params)
        assert mock_get.call_count == 1  # No additional API call
        assert result1 == result2
    
    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_rate_limit_handling(self, mock_sleep, mock_get, client):
        """Test handling of rate limit responses."""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '5'}
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.RequestException):
            client._make_request("/test/endpoint")
        
        # Should have slept for retry-after duration
        mock_sleep.assert_called_with(5)
    
    @patch('requests.Session.get')
    @patch('time.sleep')
    def test_exponential_backoff_on_failure(self, mock_sleep, mock_get, client):
        """Test exponential backoff on request failures."""
        # Mock failed responses
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.RequestException("Server error")
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.RequestException):
            client._make_request("/test/endpoint")
        
        # Should have made max_retries attempts
        assert mock_get.call_count == client.config.max_retries
        
        # Should have used exponential backoff
        expected_sleeps = [2.0 ** i for i in range(client.config.max_retries - 1)]
        actual_sleeps = [call[0][0] for call in mock_sleep.call_args_list]
        assert actual_sleeps == expected_sleeps
    
    @patch('requests.Session.get')
    def test_404_not_found_handling(self, mock_get, client):
        """Test that 404 responses don't retry."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with pytest.raises(requests.RequestException, match="Resource not found"):
            client._make_request("/test/endpoint")
        
        # Should only make one attempt for 404
        assert mock_get.call_count == 1
    
    def test_get_summoner_data(self, client):
        """Test fetching summoner data with Riot ID."""
        account_data = {
            "puuid": "test_puuid",
            "gameName": "TestSummoner",
            "tagLine": "NA1"
        }
        summoner_data = {
            "id": "test_id",
            "puuid": "test_puuid",
            "summonerLevel": 100
        }
        expected_combined = {**account_data, **summoner_data}
        
        with patch.object(client, 'get_account_by_riot_id', return_value=account_data):
            with patch.object(client, 'get_summoner_by_puuid', return_value=summoner_data):
                result = client.get_summoner_data("TestSummoner#NA1")
                
                assert result == expected_combined
    
    @patch.object(RiotAPIClient, '_make_request')
    def test_get_match_history(self, mock_request, client):
        """Test fetching match history."""
        expected_matches = ["match1", "match2", "match3"]
        mock_request.return_value = expected_matches
        
        result = client.get_match_history("test_puuid", count=20)
        
        assert result == expected_matches
        mock_request.assert_called_once_with(
            "/lol/match/v5/matches/by-puuid/test_puuid/ids",
            {"count": 20}
        )
    
    @patch.object(RiotAPIClient, '_make_request')
    def test_get_match_history_with_queue_filter(self, mock_request, client):
        """Test fetching match history with queue filter."""
        expected_matches = ["match1", "match2"]
        mock_request.return_value = expected_matches
        
        result = client.get_match_history("test_puuid", count=10, queue=420)
        
        assert result == expected_matches
        mock_request.assert_called_once_with(
            "/lol/match/v5/matches/by-puuid/test_puuid/ids",
            {"count": 10, "queue": 420}
        )
    
    @patch.object(RiotAPIClient, '_make_request')
    def test_get_match_details(self, mock_request, client):
        """Test fetching match details."""
        expected_data = {
            "metadata": {"matchId": "test_match"},
            "info": {"gameDuration": 1800}
        }
        mock_request.return_value = expected_data
        
        result = client.get_match_details("test_match")
        
        assert result == expected_data
        mock_request.assert_called_once_with("/lol/match/v5/matches/test_match")
    
    @patch.object(RiotAPIClient, '_make_request')
    def test_get_ranked_stats(self, mock_request, client):
        """Test fetching ranked statistics."""
        expected_data = [
            {
                "queueType": "RANKED_SOLO_5x5",
                "tier": "GOLD",
                "rank": "II",
                "wins": 50,
                "losses": 30
            }
        ]
        mock_request.return_value = expected_data
        
        result = client.get_ranked_stats("test_summoner_id", "na1")
        
        assert result == expected_data
        mock_request.assert_called_once_with("/lol/league/v4/entries/by-summoner/test_summoner_id")
    
    def test_role_normalization(self, client):
        """Test role name normalization."""
        assert client._normalize_role("TOP") == "top"
        assert client._normalize_role("JUNGLE") == "jungle"
        assert client._normalize_role("MIDDLE") == "middle"
        assert client._normalize_role("BOTTOM") == "bottom"
        assert client._normalize_role("UTILITY") == "support"
        assert client._normalize_role("UNKNOWN") == "unknown"
    
    def test_calculate_role_performance_no_matches(self, client):
        """Test performance calculation with no matching role data."""
        matches = []
        result = client.calculate_role_performance(matches, "test_puuid", "top")
        
        expected = {
            'matches_played': 0,
            'win_rate': 0.0,
            'avg_kda': 0.0,
            'avg_cs_per_min': 0.0,
            'avg_vision_score': 0.0,
            'recent_form': 0.0
        }
        assert result == expected
    
    def test_calculate_role_performance_with_matches(self, client):
        """Test performance calculation with match data."""
        matches = [
            {
                'info': {
                    'gameDuration': 1800,  # 30 minutes
                    'participants': [
                        {
                            'puuid': 'test_puuid',
                            'teamPosition': 'TOP',
                            'win': True,
                            'kills': 5,
                            'deaths': 2,
                            'assists': 8,
                            'totalMinionsKilled': 150,
                            'neutralMinionsKilled': 10,
                            'visionScore': 25
                        }
                    ]
                }
            },
            {
                'info': {
                    'gameDuration': 2400,  # 40 minutes
                    'participants': [
                        {
                            'puuid': 'test_puuid',
                            'teamPosition': 'TOP',
                            'win': False,
                            'kills': 3,
                            'deaths': 4,
                            'assists': 6,
                            'totalMinionsKilled': 200,
                            'neutralMinionsKilled': 5,
                            'visionScore': 30
                        }
                    ]
                }
            }
        ]
        
        result = client.calculate_role_performance(matches, 'test_puuid', 'top')
        
        assert result['matches_played'] == 2
        assert result['win_rate'] == 0.5  # 1 win out of 2 matches
        assert result['avg_kda'] > 0  # Should calculate KDA
        assert result['avg_cs_per_min'] > 0  # Should calculate CS per minute
        assert result['avg_vision_score'] == 27.5  # Average of 25 and 30
    
    def test_get_champion_mastery_single(self, client):
        """Test fetching champion mastery for a specific champion."""
        mock_mastery_data = {
            'championId': 103,
            'championLevel': 7,
            'championPoints': 150000,
            'lastPlayTime': 1640995200000,
            'championPointsSinceLastLevel': 0,
            'championPointsUntilNextLevel': 0,
            'chestGranted': True,
            'tokensEarned': 0
        }
        
        with patch.object(client, '_make_request', return_value=mock_mastery_data):
            result = client.get_champion_mastery('test_puuid', champion_id=103)
            
            assert result == mock_mastery_data
            client._make_request.assert_called_once()
    
    def test_get_all_champion_masteries(self, client):
        """Test fetching all champion masteries for a player."""
        mock_masteries_data = [
            {
                'championId': 103,
                'championLevel': 7,
                'championPoints': 150000,
                'lastPlayTime': 1640995200000,
                'chestGranted': True
            },
            {
                'championId': 266,
                'championLevel': 5,
                'championPoints': 50000,
                'lastPlayTime': 1640908800000,
                'chestGranted': False
            }
        ]
        
        with patch.object(client, 'get_champion_mastery', return_value=mock_masteries_data):
            result = client.get_all_champion_masteries('test_puuid')
            
            assert result == mock_masteries_data
            assert len(result) == 2
    
    def test_get_top_champion_masteries(self, client):
        """Test fetching top champion masteries."""
        mock_masteries_data = [
            {'championId': 103, 'championPoints': 150000},
            {'championId': 266, 'championPoints': 100000},
            {'championId': 22, 'championPoints': 75000},
            {'championId': 1, 'championPoints': 50000}
        ]
        
        with patch.object(client, 'get_all_champion_masteries', return_value=mock_masteries_data):
            result = client.get_top_champion_masteries('test_puuid', count=3)
            
            assert len(result) == 3
            # Should be sorted by championPoints descending
            assert result[0]['championPoints'] == 150000
            assert result[1]['championPoints'] == 100000
            assert result[2]['championPoints'] == 75000
    
    def test_get_champion_mastery_score(self, client):
        """Test fetching total mastery score."""
        mock_score = 42
        
        with patch.object(client, '_make_request', return_value=mock_score):
            result = client.get_champion_mastery_score('test_puuid')
            
            assert result == mock_score
            client._make_request.assert_called_once()
    
    def test_champion_mastery_error_handling(self, client):
        """Test error handling in champion mastery methods."""
        with patch.object(client, '_make_request', side_effect=Exception("API Error")):
            # Should return empty list on error
            result = client.get_all_champion_masteries('test_puuid')
            assert result == []
            
            # Should return 0 on error
            score = client.get_champion_mastery_score('test_puuid')
            assert score == 0
    
    def test_clear_cache(self, client, tmp_path):
        """Test cache clearing functionality."""
        # Add some data to cache
        client._store_in_cache("test_key", {"test": "data"})
        assert len(client.cache) > 0
        
        # Clear cache
        client.clear_cache()
        assert len(client.cache) == 0
        
        # Cache file should be removed
        cache_file = Path(client.config.cache_directory) / "api_cache.json"
        assert not cache_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])