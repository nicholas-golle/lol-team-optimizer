#!/usr/bin/env python3
"""Debug imports step by step."""

print("Testing imports step by step...")

try:
    print("Step 1: Basic imports")
    import logging
    import json
    import uuid
    from datetime import datetime, timedelta
    from typing import Dict, List, Optional, Tuple, Any, Union
    from dataclasses import dataclass, field, asdict
    from collections import defaultdict
    import statistics
    import numpy as np
    print("✓ Basic imports ok")
    
    print("Step 2: Plotly imports")
    try:
        import plotly.graph_objects as go
        import plotly.express as px
        from plotly.subplots import make_subplots
        import pandas as pd
        PLOTLY_AVAILABLE = True
        print("✓ Plotly imports ok")
    except ImportError:
        print("! Plotly not available, using mocks")
        PLOTLY_AVAILABLE = False
    
    print("Step 3: Local imports")
    from lol_team_optimizer.analytics_models import (
        ChampionRecommendation, TeamContext, ChampionPerformanceMetrics,
        AnalyticsFilters, DateRange, AnalyticsError, InsufficientDataError
    )
    print("✓ analytics_models ok")
    
    from lol_team_optimizer.champion_recommendation_engine import ChampionRecommendationEngine
    print("✓ champion_recommendation_engine ok")
    
    from lol_team_optimizer.advanced_recommendation_customizer import AdvancedRecommendationCustomizer
    print("✓ advanced_recommendation_customizer ok")
    
    from lol_team_optimizer.analytics_sharing_system import AnalyticsSharingSystem
    print("✓ analytics_sharing_system ok")
    
    from lol_team_optimizer.config import Config
    print("✓ config ok")
    
    print("Step 4: Define dataclass")
    @dataclass
    class TestConfig:
        color_scheme: str = "viridis"
        chart_height: int = 500
    
    print(f"✓ TestConfig defined: {TestConfig}")
    
    print("Step 5: Define class")
    class TestAnalyzer:
        def __init__(self, config: Optional[TestConfig] = None):
            self.config = config or TestConfig()
    
    print(f"✓ TestAnalyzer defined: {TestAnalyzer}")
    
    print("Step 6: Test module import")
    import lol_team_optimizer.recommendation_visualization_analyzer as rva
    print(f"✓ Module imported: {rva}")
    print(f"Available items: {[x for x in dir(rva) if not x.startswith('_')]}")
    
    print("All tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()