"""
Unit tests for the configuration module.
"""

import os
import pytest
from unittest.mock import patch
from lol_team_optimizer.config import Config, load_config, get_config


class TestConfig:
    """Test cases for the Config data class."""
    
    def test_config_creation_with_valid_api_key(self):
        """Test creating config with valid API key."""
        config = Config(riot_api_key="test-api-key-123")
        
        assert config.riot_api_key == "test-api-key-123"
        assert config.riot_api_base_url == "https://americas.api.riotgames.com"
        assert config.riot_api_rate_limit == 120
        assert config.cache_duration_hours == 1
        assert config.individual_weight == 0.6
        assert config.preference_weight == 0.3
        assert config.synergy_weight == 0.1
    
    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    def test_config_creation_without_api_key_allows_offline_mode(self):
        """Test that missing API key allows offline mode."""
        config = Config()
        assert config.riot_api_key == ""  # Empty string for offline mode
    
    @patch.dict(os.environ, {"RIOT_API_KEY": "env-api-key"})
    def test_config_gets_api_key_from_environment(self):
        """Test that config gets API key from environment variable."""
        config = Config()
        assert config.riot_api_key == "env-api-key"
    
    def test_config_weight_validation(self):
        """Test that performance weights must sum to 1.0."""
        # Valid weights
        Config(
            riot_api_key="test-key",
            individual_weight=0.5,
            preference_weight=0.3,
            synergy_weight=0.2
        )
        
        # Invalid weights (don't sum to 1.0)
        with pytest.raises(ValueError, match="Performance weights must sum to 1.0"):
            Config(
                riot_api_key="test-key",
                individual_weight=0.5,
                preference_weight=0.3,
                synergy_weight=0.3  # Total = 1.1
            )
    
    def test_config_positive_value_validation(self):
        """Test validation of positive values."""
        # Invalid cache duration
        with pytest.raises(ValueError, match="Cache duration must be positive"):
            Config(riot_api_key="test-key", cache_duration_hours=0)
        
        # Invalid max matches
        with pytest.raises(ValueError, match="Max matches to analyze must be positive"):
            Config(riot_api_key="test-key", max_matches_to_analyze=0)
        
        # Invalid timeout
        with pytest.raises(ValueError, match="Request timeout must be positive"):
            Config(riot_api_key="test-key", request_timeout_seconds=0)


class TestLoadConfig:
    """Test cases for the load_config function."""
    
    @patch.dict(os.environ, {
        "RIOT_API_KEY": "test-key",
        "CACHE_DURATION_HOURS": "2",
        "INDIVIDUAL_WEIGHT": "0.7",
        "PREFERENCE_WEIGHT": "0.2",
        "SYNERGY_WEIGHT": "0.1"
    })
    def test_load_config_from_environment(self):
        """Test loading configuration from environment variables."""
        config = load_config()
        
        assert config.riot_api_key == "test-key"
        assert config.cache_duration_hours == 2
        assert config.individual_weight == 0.7
        assert config.preference_weight == 0.2
        assert config.synergy_weight == 0.1
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_with_defaults(self):
        """Test loading configuration with default values (offline mode)."""
        config = load_config()
        assert config.riot_api_key == ""  # Offline mode
    
    @patch.dict(os.environ, {
        "RIOT_API_KEY": "test-key",
        "CACHE_DURATION_HOURS": "invalid"
    })
    def test_load_config_with_invalid_environment_values(self):
        """Test that invalid environment values raise appropriate errors."""
        with pytest.raises(ValueError):
            load_config()


class TestGetConfig:
    """Test cases for the get_config function."""
    
    @patch.dict(os.environ, {"RIOT_API_KEY": "test-key"})
    def test_get_config_success(self):
        """Test successful config retrieval."""
        config = get_config()
        assert isinstance(config, Config)
        assert config.riot_api_key == "test-key"
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_config_offline_mode(self):
        """Test config retrieval in offline mode."""
        config = get_config()
        assert config.riot_api_key == ""  # Offline mode