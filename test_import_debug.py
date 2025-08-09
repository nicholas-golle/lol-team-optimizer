#!/usr/bin/env python3
"""Debug import issues."""

try:
    print("Testing imports...")
    
    # Test basic imports
    import logging
    print("✓ logging")
    
    import json
    print("✓ json")
    
    import uuid
    print("✓ uuid")
    
    from datetime import datetime, timedelta
    print("✓ datetime")
    
    from typing import Dict, List, Optional, Tuple, Any, Union
    print("✓ typing")
    
    from dataclasses import dataclass, field, asdict
    print("✓ dataclasses")
    
    import numpy as np
    print("✓ numpy")
    
    import plotly.graph_objects as go
    print("✓ plotly.graph_objects")
    
    import plotly.express as px
    print("✓ plotly.express")
    
    from plotly.subplots import make_subplots
    print("✓ plotly.subplots")
    
    import pandas as pd
    print("✓ pandas")
    
    # Test local imports
    from lol_team_optimizer.analytics_models import ChampionRecommendation
    print("✓ ChampionRecommendation")
    
    from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
    print("✓ ChampionRecommendationEngine")
    
    from lol_team_optimizer.advanced_recommendation_customizer import AdvancedRecommendationCustomizer
    print("✓ AdvancedRecommendationCustomizer")
    
    from lol_team_optimizer.analytics_sharing_system import AnalyticsSharingSystem
    print("✓ AnalyticsSharingSystem")
    
    from lol_team_optimizer.config import Config
    print("✓ Config")
    
    print("\nAll imports successful! Now testing the module...")
    
    # Test the module import
    import lol_team_optimizer.recommendation_visualization_analyzer as rva
    print("✓ Module imported")
    
    # Check what's in the module
    print(f"Module contents: {[x for x in dir(rva) if not x.startswith('_')]}")
    
    # Try to access the class
    if hasattr(rva, 'RecommendationVisualizationAnalyzer'):
        print("✓ RecommendationVisualizationAnalyzer class found")
        cls = getattr(rva, 'RecommendationVisualizationAnalyzer')
        print(f"Class: {cls}")
    else:
        print("✗ RecommendationVisualizationAnalyzer class NOT found")
        
        # Check for other classes
        classes = [x for x in dir(rva) if isinstance(getattr(rva, x, None), type)]
        print(f"Available classes: {classes}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()