"""
Basic test of player management functionality without launching UI.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.models import Player
from lol_team_optimizer.player_management_tab import PlayerManagementTab, PlayerValidator

def test_basic_functionality():
    """Test basic player management functionality."""
    print("🧪 Testing Player Management Functionality")
    print("=" * 50)
    
    try:
        # Test 1: Initialize core engine
        print("1. Initializing core engine...")
        core_engine = CoreEngine()
        print("   ✅ Core engine initialized")
        
        # Test 2: Test player validation
        print("2. Testing player validation...")
        validator = PlayerValidator()
        
        # Valid player
        valid, msg = validator.validate_player_name("TestPlayer")
        assert valid, f"Expected valid player name, got: {msg}"
        print("   ✅ Player name validation works")
        
        # Valid summoner name
        valid, msg = validator.validate_summoner_name("TestSummoner")
        assert valid, f"Expected valid summoner name, got: {msg}"
        print("   ✅ Summoner name validation works")
        
        # Valid riot tag
        valid, msg = validator.validate_riot_tag("NA1")
        assert valid, f"Expected valid riot tag, got: {msg}"
        print("   ✅ Riot tag validation works")
        
        # Test 3: Test player CRUD operations
        print("3. Testing player CRUD operations...")
        
        # Create a test player
        test_player = Player(
            name="TestPlayer",
            summoner_name="TestSummoner",
            puuid="",
            role_preferences={
                "top": 5,
                "jungle": 3,
                "middle": 2,
                "bottom": 1,
                "support": 4
            }
        )
        
        # Add player
        success = core_engine.data_manager.add_player(test_player)
        assert success, "Failed to add player"
        print("   ✅ Player added successfully")
        
        # Load players
        players = core_engine.data_manager.load_player_data()
        assert len(players) >= 1, "No players found after adding"
        print(f"   ✅ Loaded {len(players)} players")
        
        # Find our test player
        found_player = core_engine.data_manager.get_player_by_name("TestPlayer")
        assert found_player is not None, "Test player not found"
        assert found_player.summoner_name == "TestSummoner", "Player data mismatch"
        print("   ✅ Player retrieval works")
        
        # Update player
        found_player.role_preferences["top"] = 4
        core_engine.data_manager.update_player(found_player)
        
        updated_player = core_engine.data_manager.get_player_by_name("TestPlayer")
        assert updated_player.role_preferences["top"] == 4, "Player update failed"
        print("   ✅ Player update works")
        
        # Test 4: Test player management tab
        print("4. Testing player management tab...")
        player_tab = PlayerManagementTab(core_engine)
        assert player_tab.core_engine == core_engine, "Tab initialization failed"
        print("   ✅ Player management tab initialized")
        
        # Test export functionality
        csv_path = player_tab._export_csv(players, include_prefs=True)
        assert os.path.exists(csv_path), "CSV export failed"
        print("   ✅ CSV export works")
        
        # Clean up
        os.unlink(csv_path)
        
        # Delete test player
        deleted = core_engine.data_manager.delete_player("TestPlayer")
        assert deleted, "Failed to delete test player"
        print("   ✅ Player deletion works")
        
        print("\n🎉 All tests passed! Player management functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)