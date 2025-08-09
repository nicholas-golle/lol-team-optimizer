"""
Simple test version to debug import issues.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
import plotly.graph_objects as go

@dataclass
class SimpleConfig:
    """Simple config for testing."""
    color_scheme: str = "viridis"
    chart_height: int = 500

class SimpleAnalyzer:
    """Simple analyzer for testing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = SimpleConfig()
    
    def test_method(self):
        """Test method."""
        return "Working!"

# Test if this works
if __name__ == "__main__":
    analyzer = SimpleAnalyzer()
    print(analyzer.test_method())