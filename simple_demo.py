#!/usr/bin/env python3
"""Simple demo to test the advanced recommendation customization."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 Simple Advanced Recommendation Demo")
    
    try:
        print("Step 1: Importing modules...")
        from lol_team_optimizer.advanced_recommendation_customizer import (
            AdvancedRecommendationCustomizer, RecommendationParameters
        )
        from lol_team_optimizer.config import Config
        from unittest.mock import Mock
        print("✅ Imports successful")
        
        print("Step 2: Creating mock components...")
        config = Mock(spec=Config)
        recommendation_engine = Mock()
        recommendation_engine.get_champion_recommendations.return_value = []
        print("✅ Mock components created")
        
        print("Step 3: Initializing customizer...")
        customizer = AdvancedRecommendationCustomizer(config, recommendation_engine)
        print("✅ Customizer initialized")
        
        print("Step 4: Testing parameter creation...")
        params = customizer.create_custom_parameters(
            "test_user",
            individual_performance_weight=0.4,
            team_synergy_weight=0.3,
            recent_form_weight=0.15,
            meta_relevance_weight=0.1,
            confidence_weight=0.05
        )
        print(f"✅ Parameters created: {params.individual_performance_weight}")
        
        print("Step 5: Testing feedback recording...")
        feedback = customizer.record_user_feedback(
            user_id="test_user",
            recommendation_id="test_rec",
            champion_id=1,
            role="top",
            feedback_type="positive",
            accuracy_rating=4,
            usefulness_rating=5
        )
        print(f"✅ Feedback recorded: {feedback.feedback_type}")
        
        print("\n🎉 All tests passed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    result = main()
    print(f"Demo result: {result}")
    sys.exit(result)