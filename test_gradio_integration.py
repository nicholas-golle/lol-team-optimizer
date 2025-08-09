#!/usr/bin/env python3
"""
Integration test for the enhanced Gradio interface controller.

This script tests the complete integration of the enhanced interface
with the core engine to ensure everything works together properly.
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the lol_team_optimizer to the path
sys.path.append('lol_team_optimizer')

def test_interface_creation():
    """Test that the interface can be created successfully."""
    print("Testing interface creation...")
    
    # Mock the core engine to avoid dependencies
    with patch('lol_team_optimizer.gradio_interface_controller.CoreEngine') as mock_core_engine_class:
        mock_core_engine = Mock()
        mock_core_engine.api_available = True
        mock_core_engine.analytics_available = True
        mock_core_engine.get_migration_status.return_value = None
        mock_core_engine.data_manager.load_player_data.return_value = []
        mock_core_engine_class.return_value = mock_core_engine
        
        # Import and create interface
        from lol_team_optimizer.gradio_interface_controller import GradioInterface
        
        interface = GradioInterface()
        
        # Verify initialization
        assert interface.core_engine == mock_core_engine
        assert interface.state_manager is not None
        assert interface.data_flow_manager is not None
        assert interface.error_handler is not None
        
        print("✅ Interface creation successful")
        return True

def test_state_management():
    """Test state management functionality."""
    print("Testing state management...")
    
    from lol_team_optimizer.gradio_interface_controller import StateManager
    
    state_manager = StateManager()
    
    # Create session
    session_id = state_manager.create_session()
    assert session_id is not None
    assert len(session_id) > 0
    
    # Update session state
    success = state_manager.update_session_state(session_id, "current_tab", "analytics")
    assert success
    
    # Verify state
    session = state_manager.get_session(session_id)
    assert session is not None
    assert session.current_tab == "analytics"
    
    # Test caching
    state_manager.cache_result("test_key", "test_value")
    cached_value = state_manager.get_cached_result("test_key")
    assert cached_value == "test_value"
    
    print("✅ State management successful")
    return True

def test_component_creation():
    """Test component creation functionality."""
    print("Testing component creation...")
    
    from lol_team_optimizer.gradio_components import (
        PlayerManagementComponents,
        AnalyticsComponents,
        ProgressComponents
    )
    
    # Mock gradio components
    with patch('lol_team_optimizer.gradio_components.gr') as mock_gr:
        mock_gr.Textbox.return_value = Mock()
        mock_gr.Dropdown.return_value = Mock()
        mock_gr.Button.return_value = Mock()
        mock_gr.Progress.return_value = Mock()
        mock_gr.Markdown.return_value = Mock()
        mock_gr.HTML.return_value = Mock()
        mock_gr.CheckboxGroup.return_value = Mock()
        mock_gr.Slider.return_value = Mock()
        mock_gr.Radio.return_value = Mock()
        
        # Test player form creation
        player_form = PlayerManagementComponents.create_player_form()
        assert len(player_form) == 4  # name, summoner_name, riot_id, region
        
        # Test analytics filter creation
        analytics_filters = AnalyticsComponents.create_filter_panel()
        assert len(analytics_filters) == 7  # Various filter components
        
        # Test progress tracker creation
        progress_bar, status_text, detailed_status = ProgressComponents.create_progress_tracker()
        assert progress_bar is not None
        assert status_text is not None
        assert detailed_status is not None
        
        print("✅ Component creation successful")
        return True

def test_data_flow():
    """Test data flow management."""
    print("Testing data flow management...")
    
    from lol_team_optimizer.gradio_interface_controller import DataFlowManager, StateManager
    
    # Mock core engine
    mock_core_engine = Mock()
    mock_core_engine.data_manager.add_player = Mock()
    mock_core_engine.data_manager.load_player_data.return_value = []
    
    state_manager = StateManager()
    data_flow_manager = DataFlowManager(mock_core_engine, state_manager)
    
    # Test player update
    session_id = state_manager.create_session()
    player_data = {
        "name": "Test Player",
        "summoner_name": "TestSummoner#NA1"
    }
    
    result = data_flow_manager.handle_player_update(session_id, player_data)
    assert result.success
    assert "Successfully added player" in result.message
    
    # Verify core engine was called
    mock_core_engine.data_manager.add_player.assert_called_once()
    
    print("✅ Data flow management successful")
    return True

def test_error_handling():
    """Test error handling functionality."""
    print("Testing error handling...")
    
    from lol_team_optimizer.gradio_interface_controller import WebErrorHandler
    
    error_handler = WebErrorHandler()
    
    # Test generic error
    error = Exception("Test error")
    result = error_handler.handle_error(error, "test_context")
    
    assert not result.success
    assert result.message is not None
    assert result.error_details is not None
    
    # Test error logging
    error_log = error_handler.get_error_log()
    assert len(error_log) > 0
    assert error_log[0]["error_message"] == "Test error"
    assert error_log[0]["context"] == "test_context"
    
    print("✅ Error handling successful")
    return True

def main():
    """Run all integration tests."""
    print("🚀 Starting Gradio Interface Integration Tests")
    print("=" * 60)
    
    tests = [
        test_interface_creation,
        test_state_management,
        test_component_creation,
        test_data_flow,
        test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)