"""
State Management System Demonstration

This script demonstrates the comprehensive state management and caching
system for the Gradio web interface, showing session management, caching,
user preferences, and real-time synchronization features.
"""

import time
from datetime import datetime
from lol_team_optimizer.enhanced_state_manager import EnhancedStateManager
from lol_team_optimizer.web_state_models import (
    UserPreferences, OperationState, ShareableResult
)


def demonstrate_session_management():
    """Demonstrate session management capabilities."""
    print("🔄 Session Management Demo")
    print("=" * 50)
    
    # Create state manager
    state_manager = EnhancedStateManager(cache_size_mb=10, max_sessions=100)
    
    # Create multiple sessions
    sessions = []
    for i in range(3):
        preferences = UserPreferences(
            theme=f"theme_{i}",
            max_results_per_page=50 + i * 25,
            auto_refresh_interval=30 + i * 10
        )
        session_id = state_manager.create_session(preferences)
        sessions.append(session_id)
        print(f"  ✅ Created session {i+1}: {session_id[:8]}...")
    
    # Update session states
    for i, session_id in enumerate(sessions):
        state_manager.update_session_state(session_id, "current_tab", f"tab_{i}")
        state_manager.update_session_state(session_id, "selected_players", [f"player_{i}_1", f"player_{i}_2"])
        print(f"  📝 Updated session {i+1} state")
    
    # Verify session data
    for i, session_id in enumerate(sessions):
        session = state_manager.get_session(session_id)
        print(f"  📊 Session {i+1}: Tab={session.current_tab}, Players={len(session.selected_players)}, Theme={session.user_preferences.theme}")
    
    return state_manager, sessions


def demonstrate_caching_system(state_manager):
    """Demonstrate advanced caching capabilities."""
    print("\n💾 Caching System Demo")
    print("=" * 50)
    
    # Cache different types of data
    cache_data = [
        ("player_data", {"name": "TestPlayer", "rank": "Diamond", "role": "ADC"}),
        ("analytics_summary", {"win_rate": 0.68, "avg_kda": 2.3, "games_played": 150}),
        ("team_composition", {"top": "Garen", "jungle": "Graves", "mid": "Yasuo", "adc": "Jinx", "support": "Thresh"}),
        ("match_history", [{"match_id": f"match_{i}", "result": "win" if i % 2 == 0 else "loss"} for i in range(10)])
    ]
    
    # Cache data with different TTLs
    for key, data in cache_data:
        ttl = 60 if "player" in key else 30  # Player data cached longer
        success = state_manager.cache_result(key, data, ttl=ttl)
        print(f"  ✅ Cached {key}: {success}")
    
    # Cache with dependencies
    state_manager.cache_result("player_analytics", {"detailed_stats": "complex_data"}, 
                              ttl=45, dependencies=["player_data", "analytics_summary"])
    print("  🔗 Cached dependent data: player_analytics")
    
    # Retrieve cached data
    for key, _ in cache_data:
        cached = state_manager.get_cached_result(key)
        print(f"  📥 Retrieved {key}: {'✅' if cached else '❌'}")
    
    # Test cache invalidation
    print("  🗑️  Testing cache invalidation...")
    invalidated = state_manager.invalidate_cache("player_data")
    print(f"  📤 Invalidated keys: {invalidated}")
    
    # Verify dependent data was also invalidated
    dependent_data = state_manager.get_cached_result("player_analytics")
    print(f"  🔍 Dependent data after invalidation: {'❌ Invalidated' if not dependent_data else '✅ Still cached'}")


def demonstrate_operation_tracking(state_manager, session_id):
    """Demonstrate operation state tracking."""
    print("\n⚙️  Operation Tracking Demo")
    print("=" * 50)
    
    # Create a long-running operation
    operation = OperationState(
        operation_id="match_extraction_demo",
        operation_type="match_extraction",
        status="pending",
        progress_percentage=0.0,
        status_message="Initializing extraction..."
    )
    
    state_manager.add_operation(session_id, operation)
    print(f"  🚀 Started operation: {operation.operation_id}")
    
    # Simulate operation progress
    progress_steps = [
        (25.0, "running", "Fetching player data..."),
        (50.0, "running", "Extracting match history..."),
        (75.0, "running", "Processing match data..."),
        (100.0, "completed", "Extraction completed successfully!")
    ]
    
    for progress, status, message in progress_steps:
        time.sleep(0.5)  # Simulate work
        state_manager.update_operation(session_id, operation.operation_id, {
            "progress_percentage": progress,
            "status": status,
            "status_message": message
        })
        print(f"  📊 Progress: {progress}% - {message}")
    
    # Get final operation state
    session = state_manager.get_session(session_id)
    final_operation = session.operation_states[operation.operation_id]
    print(f"  ✅ Operation completed: {final_operation.status} ({final_operation.progress_percentage}%)")


def demonstrate_shareable_results(state_manager, session_id):
    """Demonstrate shareable results system."""
    print("\n🔗 Shareable Results Demo")
    print("=" * 50)
    
    # Create shareable analysis result
    analysis_data = {
        "player_performance": {
            "win_rate": 0.72,
            "avg_kda": 2.8,
            "best_champions": ["Jinx", "Caitlyn", "Ezreal"]
        },
        "team_synergy": {
            "overall_score": 8.5,
            "strengths": ["early_game", "team_fights"],
            "weaknesses": ["late_game_scaling"]
        },
        "recommendations": [
            "Focus on early game aggression",
            "Practice team fight positioning",
            "Consider late-game scaling champions"
        ]
    }
    
    result = state_manager.create_shareable_result(
        result_type="player_analysis",
        title="Comprehensive Player Performance Analysis",
        description="Detailed analysis of player performance with team synergy insights and strategic recommendations",
        data=analysis_data,
        session_id=session_id,
        expiration_hours=48
    )
    
    print(f"  📊 Created shareable result: {result.result_id[:8]}...")
    print(f"  📝 Title: {result.title}")
    print(f"  ⏰ Expires: {result.expiration_date.strftime('%Y-%m-%d %H:%M') if result.expiration_date else 'Never'}")
    
    # Access the shareable result (simulating external access)
    retrieved_result = state_manager.get_shareable_result(result.result_id)
    print(f"  🔍 Retrieved result: {'✅' if retrieved_result else '❌'}")
    print(f"  👁️  Access count: {retrieved_result.access_count if retrieved_result else 0}")
    
    # Access again to increment counter
    retrieved_again = state_manager.get_shareable_result(result.result_id)
    print(f"  👁️  Access count after second access: {retrieved_again.access_count if retrieved_again else 0}")


def demonstrate_real_time_events(state_manager, session_id):
    """Demonstrate real-time event system."""
    print("\n⚡ Real-time Events Demo")
    print("=" * 50)
    
    # Event tracking
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
        event_data = event.get("data", {})
        print(f"  📡 Event received: {event['type']} - {event_data.get('component_id', 'unknown')}")
    
    # Subscribe to events
    subscription_id = state_manager.subscribe_to_events("state_change", event_handler)
    print(f"  📻 Subscribed to events: {subscription_id[:8]}...")
    
    # Generate some state changes
    changes = [
        ("current_tab", "analytics"),
        ("selected_players", ["player1", "player2", "player3"]),
        ("active_filters", {"role": "adc", "rank": "diamond"}),
        ("view_mode", "detailed")
    ]
    
    for key, value in changes:
        state_manager.update_session_state(session_id, key, value)
        time.sleep(0.1)  # Allow event processing
    
    print(f"  📊 Total events received: {len(received_events)}")
    
    # Emit custom event
    state_manager.emit_event("custom_analysis_complete", {
        "analysis_type": "team_composition",
        "results": {"score": 8.7, "confidence": 0.92}
    })
    time.sleep(0.1)


def demonstrate_system_monitoring(state_manager):
    """Demonstrate system monitoring and statistics."""
    print("\n📈 System Monitoring Demo")
    print("=" * 50)
    
    # Get comprehensive system statistics
    stats = state_manager.get_system_statistics()
    
    print("  📊 System Statistics:")
    print(f"    Sessions:")
    print(f"      - Total: {stats['sessions']['total_sessions']}")
    print(f"      - Active: {stats['sessions']['active_sessions']}")
    print(f"      - Idle: {stats['sessions']['idle_sessions']}")
    
    print(f"    Cache:")
    print(f"      - Total entries: {stats['cache']['total_entries']}")
    print(f"      - Size: {stats['cache']['total_size_mb']:.2f} MB")
    print(f"      - Hit rate: {stats['cache']['hit_rate']:.2%}")
    print(f"      - Avg access time: {stats['cache']['average_access_time_ms']:.2f} ms")
    
    print(f"    Shared Results:")
    print(f"      - Total: {stats['shared_results']['total_results']}")
    print(f"      - Active: {stats['shared_results']['active_results']}")
    
    # Test cleanup
    cleanup_result = state_manager.cleanup_expired_data()
    print(f"  🧹 Cleanup completed: {cleanup_result}")


def main():
    """Run the complete state management demonstration."""
    print("🎮 League of Legends Team Optimizer")
    print("State Management System Demonstration")
    print("=" * 60)
    
    try:
        # Session management
        state_manager, sessions = demonstrate_session_management()
        
        # Use first session for remaining demos
        demo_session = sessions[0]
        
        # Caching system
        demonstrate_caching_system(state_manager)
        
        # Operation tracking
        demonstrate_operation_tracking(state_manager, demo_session)
        
        # Shareable results
        demonstrate_shareable_results(state_manager, demo_session)
        
        # Real-time events
        demonstrate_real_time_events(state_manager, demo_session)
        
        # System monitoring
        demonstrate_system_monitoring(state_manager)
        
        print("\n🎉 State Management System Demo Completed Successfully!")
        print("=" * 60)
        print("The enhanced state management system provides:")
        print("  ✅ Comprehensive session management")
        print("  ✅ Advanced caching with dependency tracking")
        print("  ✅ Operation state tracking and progress monitoring")
        print("  ✅ Shareable results with access control")
        print("  ✅ Real-time event synchronization")
        print("  ✅ System monitoring and statistics")
        print("  ✅ Persistent storage with multiple backends")
        print("  ✅ Thread-safe concurrent access")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()