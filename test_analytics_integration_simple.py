#!/usr/bin/env python3
"""
Simple test to verify analytics integration with core engine.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

def test_core_engine_analytics_integration():
    """Test that core engine can be created with analytics integration."""
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Mock configuration
        mock_config = Mock()
        mock_config.data_directory = temp_dir / "data"
        mock_config.cache_directory = temp_dir / "cache"
        mock_config.data_directory.mkdir(exist_ok=True)
        mock_config.cache_directory.mkdir(exist_ok=True)
        
        # Mock all dependencies
        with patch('lol_team_optimizer.core_engine.Config', return_value=mock_config), \
             patch('lol_team_optimizer.core_engine.DataManager'), \
             patch('lol_team_optimizer.core_engine.MatchManager'), \
             patch('lol_team_optimizer.core_engine.RiotAPIClient'), \
             patch('lol_team_optimizer.core_engine.ChampionDataManager'), \
             patch('lol_team_optimizer.core_engine.PerformanceCalculator'), \
             patch('lol_team_optimizer.core_engine.SynergyManager'), \
             patch('lol_team_optimizer.core_engine.OptimizationEngine'), \
             patch('lol_team_optimizer.core_engine.DataMigrator'), \
             patch('lol_team_optimizer.core_engine.AnalyticsCacheManager'), \
             patch('lol_team_optimizer.core_engine.BaselineManager'), \
             patch('lol_team_optimizer.core_engine.StatisticalAnalyzer'), \
             patch('lol_team_optimizer.core_engine.ChampionSynergyAnalyzer'), \
             patch('lol_team_optimizer.core_engine.HistoricalAnalyticsEngine'), \
             patch('lol_team_optimizer.core_engine.ChampionRecommendationEngine'):
            
            from lol_team_optimizer.core_engine import CoreEngine
            
            # Create core engine
            engine = CoreEngine()
            
            # Verify analytics components are available
            assert hasattr(engine, 'analytics_available')
            assert hasattr(engine, 'analytics_cache_manager')
            assert hasattr(engine, 'baseline_manager')
            assert hasattr(engine, 'historical_analytics_engine')
            assert hasattr(engine, 'champion_recommendation_engine')
            
            # Verify analytics methods are available
            assert hasattr(engine, 'analyze_player_performance')
            assert hasattr(engine, 'get_champion_recommendations')
            assert hasattr(engine, 'calculate_performance_trends')
            assert hasattr(engine, 'generate_comparative_analysis')
            assert hasattr(engine, 'get_analytics_cache_statistics')
            assert hasattr(engine, 'invalidate_analytics_cache')
            assert hasattr(engine, 'update_player_baselines')
            assert hasattr(engine, 'migrate_analytics_data')
            
            # Test analytics unavailable scenario
            engine.analytics_available = False
            result = engine.analyze_player_performance("test-puuid")
            assert "error" in result
            assert "unavailable" in result["error"].lower()
            
            print("✓ Core engine analytics integration test passed!")
            
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_core_engine_analytics_integration()