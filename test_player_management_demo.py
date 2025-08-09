"""
Demo script to test the player management functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.gradio_interface_controller import GradioInterface

def test_player_management():
    """Test the player management functionality."""
    try:
        # Initialize core engine
        print("Initializing core engine...")
        core_engine = CoreEngine()
        
        # Create Gradio interface
        print("Creating Gradio interface...")
        interface = GradioInterface(core_engine)
        
        # Create the interface
        print("Building interface...")
        demo = interface.create_interface()
        
        print("✅ Player management interface created successfully!")
        print("🚀 Launching interface...")
        
        # Launch the interface
        demo.launch(
            share=False,
            server_name="127.0.0.1",
            server_port=7860,
            debug=True,
            show_error=True
        )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_player_management()