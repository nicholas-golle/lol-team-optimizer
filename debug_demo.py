#!/usr/bin/env python3
"""Debug demo script."""

print("Script started")

try:
    print("Attempting imports...")
    import sys
    import os
    print("Basic imports OK")
    
    # Add the project root to the Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print("Path added")
    
    from lol_team_optimizer.advanced_recommendation_customizer import RecommendationParameters
    print("RecommendationParameters imported")
    
    params = RecommendationParameters()
    print(f"Parameters created: {params}")
    
    print("✅ All tests passed")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("Script ending")