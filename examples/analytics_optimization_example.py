"""
Example demonstrating analytics optimization features.

This example shows how to use batch processing, incremental updates,
and query optimization to improve analytics performance.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from lol_team_optimizer.config import Config
from lol_team_optimizer.historical_analytics_engine import HistoricalAnalyticsEngine
from lol_team_optimizer.analytics_models import AnalyticsFilters, DateRange
from lol_team_optimizer.analytics_batch_processor import BatchProgress
from lol_team_optimizer.match_manager import MatchManager
from lol_team_optimizer.baseline_manager import BaselineManager


def progress_callback(progress: BatchProgress):
    """Progress callback for batch operations."""
    print(f"Progress: {progress.progress_percentage:.1f}% "
          f"({progress.completed_tasks}/{progress.total_tasks}) "
          f"Current: {progress.current_task}")


def demonstrate_batch_processing():
    """Demonstrate batch processing for multiple players."""
    print("=== Batch Processing Demo ===")
    
    # Initialize components
    config = Config()
    match_manager = MatchManager(config)
    baseline_manager = BaselineManager(config, match_manager)
    analytics_engine = HistoricalAnalyticsEngine(config, match_manager, baseline_manager)
    
    # Get list of players to analyze
    stats = match_manager.get_match_statistics()
    print(f"Total matches in database: {stats['total_matches']}")
    
    # Get recent matches to find active players
    recent_matches = match_manager.get_recent_matches(days=30, limit=100)
    player_puuids = set()
    
    for match in recent_matches:
        for participant in match.participants:
            player_puuids.add(participant.puuid)
            if len(player_puuids) >= 10:  # Limit for demo
                break
        if len(player_puuids) >= 10:
            break
    
    player_list = list(player_puuids)
    print(f"Analyzing {len(player_list)} players")
    
    # Create filters for recent performance
    filters = AnalyticsFilters(
        date_range=DateRange(
            start_date=datetime.now() - timedelta(days=60),
            end_date=datetime.now()
        ),
        queue_types=[420, 440]  # Ranked Solo/Duo and Ranked Flex
    )
    
    # Batch analyze players
    start_time = time.time()
    
    try:
        results = analytics_engine.batch_analyze_multiple_players(
            player_list,
            filters=filters,
            progress_callback=progress_callback
        )
        
        batch_time = time.time() - start_time
        
        print(f"\nBatch processing completed in {batch_time:.2f} seconds")
        print(f"Successfully analyzed {len(results)} players")
        
        # Show sample results
        for i, (puuid, analytics) in enumerate(results.items()):
            if i >= 3:  # Show first 3 results
                break
            
            print(f"\nPlayer {analytics.player_name}:")
            print(f"  Overall win rate: {analytics.overall_performance.win_rate:.1f}%")
            print(f"  Average KDA: {analytics.overall_performance.avg_kda:.2f}")
            print(f"  Games analyzed: {analytics.overall_performance.games_played}")
            
            # Show champion performance
            if analytics.champion_performance:
                best_champion = max(
                    analytics.champion_performance.values(),
                    key=lambda cp: cp.performance.win_rate
                )
                print(f"  Best champion: {best_champion.champion_name} "
                      f"({best_champion.performance.win_rate:.1f}% win rate)")
        
    except Exception as e:
        print(f"Batch processing failed: {e}")


def demonstrate_incremental_updates():
    """Demonstrate incremental analytics updates."""
    print("\n=== Incremental Updates Demo ===")
    
    # Initialize components
    config = Config()
    match_manager = MatchManager(config)
    baseline_manager = BaselineManager(config, match_manager)
    analytics_engine = HistoricalAnalyticsEngine(config, match_manager, baseline_manager)
    
    # Find players needing updates
    players_needing_updates = analytics_engine.get_players_needing_updates(max_age_hours=24)
    print(f"Found {len(players_needing_updates)} players needing updates")
    
    if not players_needing_updates:
        print("No players need updates at this time")
        return
    
    # Update first few players incrementally
    update_count = min(5, len(players_needing_updates))
    players_to_update = players_needing_updates[:update_count]
    
    print(f"Updating {len(players_to_update)} players incrementally...")
    
    start_time = time.time()
    successful_updates = 0
    
    for puuid in players_to_update:
        try:
            success = analytics_engine.update_analytics_incrementally(puuid)
            if success:
                successful_updates += 1
                print(f"✓ Updated player {puuid}")
            else:
                print(f"✗ Failed to update player {puuid}")
                
        except Exception as e:
            print(f"✗ Error updating player {puuid}: {e}")
    
    update_time = time.time() - start_time
    
    print(f"\nIncremental updates completed in {update_time:.2f} seconds")
    print(f"Successfully updated {successful_updates}/{len(players_to_update)} players")
    
    # Show update statistics
    update_stats = analytics_engine.incremental_updater.get_update_statistics()
    print(f"\nUpdate Statistics:")
    print(f"  Total players tracked: {update_stats['total_players_tracked']}")
    print(f"  Total matches processed: {update_stats['total_matches_processed']}")
    print(f"  Average matches per player: {update_stats['average_matches_processed']:.1f}")


def demonstrate_query_optimization():
    """Demonstrate query optimization features."""
    print("\n=== Query Optimization Demo ===")
    
    # Initialize components
    config = Config()
    match_manager = MatchManager(config)
    baseline_manager = BaselineManager(config, match_manager)
    analytics_engine = HistoricalAnalyticsEngine(config, match_manager, baseline_manager)
    
    # Get some players for testing
    recent_matches = match_manager.get_recent_matches(days=7, limit=50)
    if not recent_matches:
        print("No recent matches found for query optimization demo")
        return
    
    # Extract unique players and champions
    players = set()
    champions = set()
    
    for match in recent_matches:
        for participant in match.participants:
            players.add(participant.puuid)
            champions.add(participant.champion_id)
    
    player_list = list(players)[:5]  # First 5 players
    champion_list = list(champions)[:3]  # First 3 champions
    
    print(f"Testing queries with {len(player_list)} players and {len(champion_list)} champions")
    
    # Test different query types
    query_tests = [
        {
            'name': 'Player-specific query',
            'filters': AnalyticsFilters(player_puuids=player_list[:2])
        },
        {
            'name': 'Champion-specific query',
            'filters': AnalyticsFilters(champions=champion_list)
        },
        {
            'name': 'Role-specific query',
            'filters': AnalyticsFilters(roles=['MIDDLE', 'BOTTOM'])
        },
        {
            'name': 'Recent matches query',
            'filters': AnalyticsFilters(
                date_range=DateRange(
                    start_date=datetime.now() - timedelta(days=7),
                    end_date=datetime.now()
                )
            )
        },
        {
            'name': 'Complex query',
            'filters': AnalyticsFilters(
                player_puuids=player_list[:1],
                champions=champion_list[:2],
                roles=['MIDDLE'],
                queue_types=[420],
                date_range=DateRange(
                    start_date=datetime.now() - timedelta(days=30),
                    end_date=datetime.now()
                )
            )
        }
    ]
    
    # Execute queries and measure performance
    for test in query_tests:
        print(f"\nExecuting {test['name']}...")
        
        start_time = time.time()
        try:
            results = analytics_engine.execute_optimized_query(
                test['filters'],
                test['name'].lower().replace(' ', '_')
            )
            
            query_time = time.time() - start_time
            
            print(f"  Results: {len(results)} matches")
            print(f"  Query time: {query_time:.3f} seconds")
            
            if results:
                # Show sample match info
                sample_match = results[0]
                match_date = datetime.fromtimestamp(sample_match.game_creation / 1000)
                print(f"  Sample match: {sample_match.match_id} ({match_date.strftime('%Y-%m-%d %H:%M')})")
            
        except Exception as e:
            print(f"  Query failed: {e}")
    
    # Show query statistics
    query_stats = analytics_engine.query_optimizer.get_query_statistics()
    if query_stats:
        print(f"\nQuery Statistics:")
        for query_type, stats in query_stats.items():
            print(f"  {query_type}:")
            print(f"    Executions: {stats['execution_count']}")
            print(f"    Avg time: {stats['average_execution_time']:.3f}s")
            print(f"    Cache hit rate: {stats['cache_hit_rate']:.1f}%")


def demonstrate_performance_monitoring():
    """Demonstrate performance monitoring and statistics."""
    print("\n=== Performance Monitoring Demo ===")
    
    # Initialize components
    config = Config()
    match_manager = MatchManager(config)
    baseline_manager = BaselineManager(config, match_manager)
    analytics_engine = HistoricalAnalyticsEngine(config, match_manager, baseline_manager)
    
    # Get optimization statistics
    stats = analytics_engine.get_optimization_statistics()
    
    print("Optimization Statistics:")
    
    # Batch processing stats
    if 'batch_processing' in stats:
        batch_stats = stats['batch_processing']
        print(f"\nBatch Processing:")
        print(f"  Total batches processed: {batch_stats.get('total_batches_processed', 0)}")
        print(f"  Total tasks processed: {batch_stats.get('total_tasks_processed', 0)}")
        print(f"  Average batch size: {batch_stats.get('average_batch_size', 0):.1f}")
        print(f"  Average time per task: {batch_stats.get('average_processing_time_per_task', 0):.3f}s")
    
    # Incremental update stats
    if 'incremental_updates' in stats:
        update_stats = stats['incremental_updates']
        print(f"\nIncremental Updates:")
        print(f"  Players tracked: {update_stats.get('total_players_tracked', 0)}")
        print(f"  Matches processed: {update_stats.get('total_matches_processed', 0)}")
        print(f"  Players needing update: {update_stats.get('players_needing_update', 0)}")
    
    # Query optimization stats
    if 'query_optimization' in stats:
        query_stats = stats['query_optimization']
        print(f"\nQuery Optimization:")
        for query_type, type_stats in query_stats.items():
            print(f"  {query_type}:")
            print(f"    Executions: {type_stats.get('execution_count', 0)}")
            print(f"    Cache hit rate: {type_stats.get('cache_hit_rate', 0):.1f}%")
    
    # Cache performance stats
    if 'cache_performance' in stats:
        cache_stats = stats['cache_performance']
        print(f"\nCache Performance:")
        print(f"  Hit rate: {cache_stats.hit_rate:.1f}%")
        print(f"  Total entries: {cache_stats.total_entries}")
        print(f"  Memory cache: {cache_stats.memory_cache_entries} entries")
        print(f"  Persistent cache: {cache_stats.persistent_cache_entries} entries")
        print(f"  Total size: {cache_stats.total_size_bytes / 1024 / 1024:.1f} MB")


def demonstrate_cleanup():
    """Demonstrate cleanup of optimization data."""
    print("\n=== Cleanup Demo ===")
    
    # Initialize components
    config = Config()
    match_manager = MatchManager(config)
    baseline_manager = BaselineManager(config, match_manager)
    analytics_engine = HistoricalAnalyticsEngine(config, match_manager, baseline_manager)
    
    print("Cleaning up old optimization data...")
    
    try:
        cleanup_stats = analytics_engine.cleanup_optimization_data(days=30)
        
        print("Cleanup completed:")
        for key, value in cleanup_stats.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Cleanup failed: {e}")


def main():
    """Run all optimization demos."""
    print("Analytics Optimization Features Demo")
    print("=" * 50)
    
    try:
        # Run demonstrations
        demonstrate_batch_processing()
        demonstrate_incremental_updates()
        demonstrate_query_optimization()
        demonstrate_performance_monitoring()
        demonstrate_cleanup()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()