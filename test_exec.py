#!/usr/bin/env python3
"""Test exec of the module."""

try:
    with open('lol_team_optimizer/recommendation_visualization_analyzer.py', 'r') as f:
        content = f.read()
    
    print("Executing module content...")
    exec(content)
    print("Execution complete")
    
    # Check if classes are defined
    if 'RecommendationVisualizationConfig' in locals():
        print(f"✓ RecommendationVisualizationConfig: {RecommendationVisualizationConfig}")
    else:
        print("✗ RecommendationVisualizationConfig not defined")
    
    if 'RecommendationVisualizationAnalyzer' in locals():
        print(f"✓ RecommendationVisualizationAnalyzer: {RecommendationVisualizationAnalyzer}")
    else:
        print("✗ RecommendationVisualizationAnalyzer not defined")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()