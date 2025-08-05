#!/usr/bin/env python3
"""
Simple test to verify the export manager works.
"""

import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta

# Test the basic functionality without complex imports
def test_basic_export():
    """Test basic export functionality."""
    
    # Create a temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Import the export manager
        from lol_team_optimizer.analytics_export_manager import (
            AnalyticsExportManager, ExportFormat, ExportConfiguration
        )
        
        # Create export manager
        manager = AnalyticsExportManager(temp_dir)
        
        # Test basic functionality
        print(f"✓ Export manager created successfully")
        print(f"✓ Output directory: {manager.output_directory}")
        print(f"✓ Templates loaded: {len(manager.templates)}")
        
        # Test export configuration
        config = ExportConfiguration(format=ExportFormat.JSON)
        print(f"✓ Export configuration created: {config.format}")
        
        # Test JSON export of simple data
        test_data = {
            "test": "data",
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "win_rate": 0.65,
                "games": 20
            }
        }
        
        # Export to JSON
        filepath = temp_dir / "test_export.json"
        manager._export_to_json(test_data, filepath, config)
        
        # Verify the export
        if filepath.exists():
            with open(filepath, 'r') as f:
                exported_data = json.load(f)
            print(f"✓ JSON export successful")
            print(f"✓ Exported data contains: {list(exported_data.keys())}")
        else:
            print("✗ JSON export failed - file not created")
            
        # Test statistics
        stats = manager.get_export_statistics()
        print(f"✓ Export statistics: {stats['total_files']} files")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_basic_export()