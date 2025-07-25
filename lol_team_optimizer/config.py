"""
Configuration management for the League of Legends Team Optimizer.

This module handles application settings, API keys, and configuration parameters.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Application configuration settings."""
    
    # Riot API Configuration
    riot_api_key: str = ""
    riot_api_base_url: str = "https://americas.api.riotgames.com"
    riot_api_rate_limit: int = 120  # requests per 2 minutes
    
    # Cache Configuration
    cache_duration_hours: int = 1  # API response cache duration
    player_data_cache_hours: int = 24  # Player data cache duration
    max_cache_size_mb: int = 50  # Maximum cache size in MB
    
    # Performance Calculation Weights
    individual_weight: float = 0.6  # Weight for individual performance
    preference_weight: float = 0.3  # Weight for role preferences
    synergy_weight: float = 0.1  # Weight for team synergy
    
    # Data Storage
    data_directory: str = "data"
    player_data_file: str = "players.json"
    cache_directory: str = "cache"
    
    # API Request Configuration
    max_matches_to_analyze: int = 20  # Number of recent matches to analyze
    request_timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    
    # Application Configuration
    log_level: str = "INFO"
    debug: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.riot_api_key:
            # Try to get API key from environment variable
            self.riot_api_key = os.getenv("RIOT_API_KEY", "")
        
        # API key is optional - application can run in offline mode without it
        # if not self.riot_api_key:
        #     raise ValueError("Riot API key is required. Set RIOT_API_KEY environment variable.")
        
        # Validate weights sum to 1.0
        total_weight = self.individual_weight + self.preference_weight + self.synergy_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Performance weights must sum to 1.0, got {total_weight}")
        
        # Validate positive values
        if self.cache_duration_hours <= 0:
            raise ValueError("Cache duration must be positive")
        if self.max_matches_to_analyze <= 0:
            raise ValueError("Max matches to analyze must be positive")
        if self.request_timeout_seconds <= 0:
            raise ValueError("Request timeout must be positive")


def load_config() -> Config:
    """Load configuration from environment variables and defaults."""
    return Config(
        riot_api_key=os.getenv("RIOT_API_KEY", ""),
        riot_api_base_url=os.getenv("RIOT_API_BASE_URL", "https://americas.api.riotgames.com"),
        cache_duration_hours=int(os.getenv("CACHE_DURATION_HOURS", "1")),
        player_data_cache_hours=int(os.getenv("PLAYER_DATA_CACHE_HOURS", "24")),
        max_cache_size_mb=int(os.getenv("MAX_CACHE_SIZE_MB", "50")),
        individual_weight=float(os.getenv("INDIVIDUAL_WEIGHT", "0.6")),
        preference_weight=float(os.getenv("PREFERENCE_WEIGHT", "0.3")),
        synergy_weight=float(os.getenv("SYNERGY_WEIGHT", "0.1")),
        data_directory=os.getenv("DATA_DIRECTORY", "data"),
        cache_directory=os.getenv("CACHE_DIRECTORY", "cache"),
        max_matches_to_analyze=int(os.getenv("MAX_MATCHES_TO_ANALYZE", "20")),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        retry_backoff_factor=float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug=os.getenv("DEBUG", "false").lower() == "true"
    )


def get_config() -> Config:
    """Get the application configuration instance."""
    try:
        return load_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please check your environment variables and try again.")
        raise