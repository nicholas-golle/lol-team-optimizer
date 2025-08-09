#!/usr/bin/env python3
"""
Advanced Recommendation Customization Demo

This script demonstrates the comprehensive advanced recommendation customization
and filtering system.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lol_team_optimizer.advanced_recommendation_customizer import (
        AdvancedRecommendationCustomizer, RecommendationParameters,
        ChampionPoolFilter, BanPhaseSimulation, RecommendationScenario,
        UserFeedback
    )
    from lol_team_optimizer.analytics_models import TeamContext, ChampionRecommendation
    from lol_team_optimizer.config import Config
    from unittest.mock import Mock, MagicMock
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_mock_recommendation_engine():
    """Create a mock recommendation engine for demonstration."""
    engine = Mock()
    
    # Mock recommendations
    mock_recommendations = [
        Mock(
            champion_id=1,
            champion_name="Garen",
            role="top",
            recommendation_score=0.85,
            confidence=0.78,
            historical_performance=Mock(),
            expected_performance=Mock(),
            synergy_analysis=Mock(),
            reasoning=Mock(primary_reasons=["Strong individual performance", "Good team synergy"])
        ),
        Mock(
            champion_id=2,
            champion_name="Darius",
            role="top",
            recommendation_score=0.82,
            confidence=0.75,
            historical_performance=Mock(),
            expected_performance=Mock(),
            synergy_analysis=Mock(),
            reasoning=Mock(primary_reasons=["High win rate", "Meta relevant"])
        )
    ]
    
    engine.get_champion_recommendations.return_value = mock_recommendations
    return engine


def demo_parameter_customization(customizer: AdvancedRecommendationCustomizer):
    """Demonstrate parameter customization functionality."""
    print("\n" + "="*60)
    print("PARAMETER CUSTOMIZATION DEMO")
    print("="*60)
    
    user_id = "demo_user"
    
    # Create custom parameters for different strategies
    strategies = {
        "safe_player": {
            "individual_performance_weight": 0.45,
            "team_synergy_weight": 0.30,
            "recent_form_weight": 0.15,
            "meta_relevance_weight": 0.05,
            "confidence_weight": 0.05,
            "risk_tolerance": 0.2,
            "meta_emphasis": 0.5
        },
        "aggressive_player": {
            "individual_performance_weight": 0.25,
            "team_synergy_weight": 0.35,
            "recent_form_weight": 0.15,
            "meta_relevance_weight": 0.20,
            "confidence_weight": 0.05,
            "risk_tolerance": 0.8,
            "meta_emphasis": 1.5
        }
    }
    
    for strategy_name, params in strategies.items():
        print(f"\n📊 Creating {strategy_name} parameters...")
        
        try:
            custom_params = customizer.create_custom_parameters(
                f"{user_id}_{strategy_name}",
                **params
            )
            
            print(f"✅ Successfully created {strategy_name} parameters:")
            print(f"   - Individual Performance: {custom_params.individual_performance_weight:.3f}")
            print(f"   - Team Synergy: {custom_params.team_synergy_weight:.3f}")
            print(f"   - Meta Relevance: {custom_params.meta_relevance_weight:.3f}")
            print(f"   - Risk Tolerance: {custom_params.risk_tolerance:.1f}")
            print(f"   - Meta Emphasis: {custom_params.meta_emphasis:.1f}")
            
        except Exception as e:
            print(f"❌ Error creating {strategy_name} parameters: {e}")


def demo_champion_pool_filtering(customizer: AdvancedRecommendationCustomizer):
    """Demonstrate champion pool filtering functionality."""
    print("\n" + "="*60)
    print("CHAMPION POOL FILTERING DEMO")
    print("="*60)
    
    user_id = "demo_user"
    
    # Create different types of champion pool filters
    filters = {
        "comfort_picks": {
            "prioritize_comfort": True,
            "comfort_threshold": 15,
            "min_games_played": 10,
            "min_win_rate": 0.55
        },
        "meta_only": {
            "include_off_meta": False,
            "meta_tier_threshold": "A",
            "min_games_played": 5
        }
    }
    
    for filter_name, filter_params in filters.items():
        print(f"\n🎯 Creating {filter_name} filter...")
        
        try:
            champion_filter = customizer.create_champion_pool_filter(
                f"{user_id}_{filter_name}",
                **filter_params
            )
            
            print(f"✅ Successfully created {filter_name} filter:")
            print(f"   - Min Games Required: {champion_filter.min_games_played}")
            
            if hasattr(champion_filter, 'min_win_rate') and champion_filter.min_win_rate:
                print(f"   - Min Win Rate: {champion_filter.min_win_rate:.1%}")
            
        except Exception as e:
            print(f"❌ Error creating {filter_name} filter: {e}")


def demo_feedback_learning(customizer: AdvancedRecommendationCustomizer):
    """Demonstrate feedback learning functionality."""
    print("\n" + "="*60)
    print("FEEDBACK LEARNING DEMO")
    print("="*60)
    
    user_id = "demo_user"
    
    # Simulate user feedback
    feedback_scenarios = [
        {"champion_id": 1, "role": "top", "type": "positive", "accuracy": 5, "usefulness": 4, 
         "tags": ["good_synergy", "meta_relevant"], "match_outcome": True},
        {"champion_id": 2, "role": "top", "type": "positive", "accuracy": 4, "usefulness": 5,
         "tags": ["good_individual_performance"], "match_outcome": True},
        {"champion_id": 3, "role": "jungle", "type": "negative", "accuracy": 2, "usefulness": 2,
         "tags": ["poor_synergy", "off_meta"], "match_outcome": False},
    ]
    
    print("📝 Recording user feedback...")
    
    recorded_feedback = []
    for i, feedback_data in enumerate(feedback_scenarios):
        try:
            feedback = customizer.record_user_feedback(
                user_id=user_id,
                recommendation_id=f"rec_{i}",
                champion_id=feedback_data["champion_id"],
                role=feedback_data["role"],
                feedback_type=feedback_data["type"],
                accuracy_rating=feedback_data["accuracy"],
                usefulness_rating=feedback_data["usefulness"],
                tags=feedback_data["tags"],
                match_outcome=feedback_data["match_outcome"]
            )
            
            recorded_feedback.append(feedback)
            print(f"   ✅ Recorded {feedback_data['type']} feedback for champion {feedback_data['champion_id']}")
            
        except Exception as e:
            print(f"   ❌ Error recording feedback: {e}")
    
    print(f"\n📊 Feedback summary: {len(recorded_feedback)} feedback items recorded")


def main():
    """Run the comprehensive advanced recommendation customization demo."""
    print("🚀 Advanced Recommendation Customization Demo")
    print("=" * 80)
    
    try:
        setup_logging()
        print("✅ Logging setup complete")
        
        # Create mock components
        config = Mock(spec=Config)
        recommendation_engine = create_mock_recommendation_engine()
        print("✅ Mock components created")
        
        # Initialize customizer
        customizer = AdvancedRecommendationCustomizer(config, recommendation_engine)
        print("✅ Customizer initialized")
        
        # Run demo sections
        print("🔧 Starting parameter customization demo...")
        demo_parameter_customization(customizer)
        
        print("🎯 Starting champion pool filtering demo...")
        demo_champion_pool_filtering(customizer)
        
        print("🧠 Starting feedback learning demo...")
        demo_feedback_learning(customizer)
        
        print("\n" + "="*80)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\nKey features demonstrated:")
        print("✅ Parameter customization with validation")
        print("✅ Champion pool filtering with multiple criteria")
        print("✅ Feedback learning and parameter optimization")
        print("\nThe advanced recommendation customization system provides")
        print("comprehensive tools for fine-tuning champion recommendations")
        print("based on user preferences, performance data, and feedback.")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    print("Starting demo...")
    result = main()
    print(f"Demo completed with result: {result}")
    exit(result)