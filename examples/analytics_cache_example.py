"""
Example demonstrating the Analytics Cache Manager usage.

This example shows how to use the AnalyticsCacheManager to optimize
analytics operations performance through intelligent caching.
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

from lol_team_optimizer.analytics_cache_manager import AnalyticsCacheManager
from lol_team_optimizer.config import Config
from lol_team_optimizer.analytics_models import (
    PlayerAnalytics,
    PerformanceMetrics,
    DateRange,
    ChampionPerformanceMetrics
)


def create_sample_analytics_data(player_id: str) -> PlayerAnalytics:
    """Create sample analytics data for demonstration."""
    date_range = DateRange(
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now()
    )
    
    performance = PerformanceMetrics(
        games_played=25,
        wins=16,
        losses=9,
        total_kills=125,
        total_deaths=62,
        total_assists=187,
        total_cs=6250,
        total_vision_score=750,
        total_damage_to_champions=250000,
        total_gold_earned=375000,
        total_game_duration=45000  # 12.5 hours in seconds
    )
    
    return PlayerAnalytics(
        puuid=player_id,
        player_name=f"Player {player_id}",
        analysis_period=date_range,
        overall_performance=performance
    )


def expensive_analytics_function(player_id: str, champion_id: int, role: str) -> dict:
    """Simulate an expensive analytics calculation."""
    print(f"Performing expensive calculation for {player_id}, champion {champion_id}, role {role}")
    
    # Simulate computation time
    time.sleep(0.1)  # 100ms delay
    
    return {
        'player_id': player_id,
        'champion_id': champion_id,
        'role': role,
        'win_rate': 0.65,
        'avg_kda': 2.8,
        'performance_score': 85.5,
        'calculated_at': datetime.now().isoformat()
    }


def demonstrate_basic_caching():
    """Demonstrate basic caching functionality."""
    print("=== Basic Caching Demo ===")
    
    # Initialize cache manager
    config = Config(cache_directory="cache", max_cache_size_mb=5)
    cache_manager = AnalyticsCacheManager(config)
    
    player_id = "demo_player_123"
    champion_id = 157  # Yasuo
    role = "middle"
    
    # First call - cache miss (slow)
    print("First call (cache miss):")
    start_time = time.time()
    
    # Check cache first
    cache_key = cache_manager.generate_cache_key(
        "champion_performance",
        player_id=player_id,
        champion_id=champion_id,
        role=role
    )
    
    cached_result = cache_manager.get_cached_analytics(cache_key)
    if cached_result is None:
        # Cache miss - perform expensive calculation
        result = expensive_analytics_function(player_id, champion_id, role)
        cache_manager.cache_analytics(cache_key, result, ttl=3600)  # Cache for 1 hour
    else:
        result = cached_result
    
    first_call_time = time.time() - start_time
    print(f"Result: {result}")
    print(f"Time taken: {first_call_time:.3f} seconds")
    
    # Second call - cache hit (fast)
    print("\nSecond call (cache hit):")
    start_time = time.time()
    
    cached_result = cache_manager.get_cached_analytics(cache_key)
    if cached_result is None:
        result = expensive_analytics_function(player_id, champion_id, role)
        cache_manager.cache_analytics(cache_key, result, ttl=3600)
    else:
        result = cached_result
    
    second_call_time = time.time() - start_time
    print(f"Result: {result}")
    print(f"Time taken: {second_call_time:.3f} seconds")
    
    speedup = first_call_time / second_call_time if second_call_time > 0 else float('inf')
    print(f"Speedup: {speedup:.1f}x faster")
    
    return cache_manager


def demonstrate_function_result_caching(cache_manager: AnalyticsCacheManager):
    """Demonstrate function result caching pattern."""
    print("\n=== Function Result Caching Demo ===")
    
    def cached_analytics_function(player_id: str, champion_id: int, role: str):
        """Analytics function with built-in caching."""
        # Try to get cached result
        cached_result = cache_manager.get_cached_analytics_result(
            "cached_analytics_function",
            player_id=player_id,
            champion_id=champion_id,
            role=role
        )
        
        if cached_result is not None:
            print(f"Cache hit for {player_id}, {champion_id}, {role}")
            return cached_result
        
        # Cache miss - perform calculation
        print(f"Cache miss for {player_id}, {champion_id}, {role}")
        result = expensive_analytics_function(player_id, champion_id, role)
        
        # Cache the result
        cache_manager.cache_analytics_result(
            "cached_analytics_function",
            result,
            player_id=player_id,
            champion_id=champion_id,
            role=role
        )
        
        return result
    
    # Test with multiple calls
    players = ["player_1", "player_2", "player_1"]  # player_1 appears twice
    champions = [157, 238, 157]  # Yasuo, Zed, Yasuo
    roles = ["middle", "middle", "middle"]
    
    for player, champion, role in zip(players, champions, roles):
        start_time = time.time()
        result = cached_analytics_function(player, champion, role)
        call_time = time.time() - start_time
        print(f"Call time: {call_time:.3f} seconds")


def demonstrate_cache_statistics(cache_manager: AnalyticsCacheManager):
    """Demonstrate cache statistics tracking."""
    print("\n=== Cache Statistics Demo ===")
    
    # Generate some cache activity
    for i in range(10):
        key = f"stats_demo_{i}"
        data = create_sample_analytics_data(f"player_{i}")
        cache_manager.cache_analytics(key, data)
    
    # Access some cached items
    for i in range(5):
        cache_manager.get_cached_analytics(f"stats_demo_{i}")
    
    # Try to access non-existent items
    for i in range(3):
        cache_manager.get_cached_analytics(f"nonexistent_{i}")
    
    # Get and display statistics
    stats = cache_manager.get_cache_statistics()
    
    print(f"Total requests: {stats.total_requests}")
    print(f"Cache hits: {stats.cache_hits}")
    print(f"Cache misses: {stats.cache_misses}")
    print(f"Hit rate: {stats.hit_rate:.2%}")
    print(f"Total entries: {stats.total_entries}")
    print(f"Total size: {stats.total_size_bytes:,} bytes")
    print(f"Memory cache entries: {stats.memory_cache_entries}")
    print(f"Persistent cache entries: {stats.persistent_cache_entries}")


def demonstrate_cache_invalidation(cache_manager: AnalyticsCacheManager):
    """Demonstrate cache invalidation patterns."""
    print("\n=== Cache Invalidation Demo ===")
    
    # Add entries for multiple players
    players = ["player_A", "player_B", "player_C"]
    for player in players:
        for champion_id in [157, 238, 91]:  # Yasuo, Zed, Talon
            key = f"player_performance:{player}:champion_{champion_id}"
            data = {
                'player': player,
                'champion_id': champion_id,
                'performance_data': f"data_for_{player}_{champion_id}"
            }
            cache_manager.cache_analytics(key, data)
    
    print(f"Added cache entries for {len(players)} players")
    
    # Invalidate all entries for player_A
    invalidated = cache_manager.invalidate_cache("player_performance:player_A:*")
    print(f"Invalidated {invalidated} entries for player_A")
    
    # Verify invalidation
    for champion_id in [157, 238, 91]:
        key = f"player_performance:player_A:champion_{champion_id}"
        result = cache_manager.get_cached_analytics(key)
        print(f"player_A champion {champion_id}: {'Found' if result else 'Not found'}")
    
    # Check that other players' data is still cached
    key = f"player_performance:player_B:champion_157"
    result = cache_manager.get_cached_analytics(key)
    print(f"player_B champion 157: {'Found' if result else 'Not found'}")


def demonstrate_persistent_vs_memory_caching(cache_manager: AnalyticsCacheManager):
    """Demonstrate difference between persistent and memory caching."""
    print("\n=== Persistent vs Memory Caching Demo ===")
    
    # Add data to memory cache only
    memory_data = {"type": "memory_only", "data": "temporary_data"}
    cache_manager.cache_analytics("memory_test", memory_data, persistent=False)
    
    # Add data to both memory and persistent cache
    persistent_data = {"type": "persistent", "data": "important_data"}
    cache_manager.cache_analytics("persistent_test", persistent_data, persistent=True)
    
    print("Added data to memory and persistent caches")
    
    # Verify both are accessible
    memory_result = cache_manager.get_cached_analytics("memory_test")
    persistent_result = cache_manager.get_cached_analytics("persistent_test")
    
    print(f"Memory data: {'Found' if memory_result else 'Not found'}")
    print(f"Persistent data: {'Found' if persistent_result else 'Not found'}")
    
    # Clear memory cache
    cache_manager.clear_cache(memory_only=True)
    print("Cleared memory cache")
    
    # Check accessibility after memory clear
    memory_result = cache_manager.get_cached_analytics("memory_test")
    persistent_result = cache_manager.get_cached_analytics("persistent_test")
    
    print(f"Memory data after clear: {'Found' if memory_result else 'Not found'}")
    print(f"Persistent data after clear: {'Found' if persistent_result else 'Not found'}")


def main():
    """Run all cache manager demonstrations."""
    print("Analytics Cache Manager Demonstration")
    print("=" * 50)
    
    # Basic caching
    cache_manager = demonstrate_basic_caching()
    
    # Function result caching
    demonstrate_function_result_caching(cache_manager)
    
    # Cache statistics
    demonstrate_cache_statistics(cache_manager)
    
    # Cache invalidation
    demonstrate_cache_invalidation(cache_manager)
    
    # Persistent vs memory caching
    demonstrate_persistent_vs_memory_caching(cache_manager)
    
    print("\n=== Final Statistics ===")
    final_stats = cache_manager.get_cache_statistics()
    print(f"Total requests: {final_stats.total_requests}")
    print(f"Hit rate: {final_stats.hit_rate:.2%}")
    print(f"Total cache size: {final_stats.total_size_bytes:,} bytes")
    
    print("\nDemo completed successfully!")


if __name__ == "__main__":
    main()