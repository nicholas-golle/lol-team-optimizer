"""
Demo script for testing the Match Extraction Interface

This script demonstrates the interactive match extraction interface
with progress tracking and comprehensive configuration options.
"""

import gradio as gr
from lol_team_optimizer.core_engine import CoreEngine
from lol_team_optimizer.match_extraction_interface import MatchExtractionInterface
from lol_team_optimizer.models import Player


def create_demo():
    """Create a demo of the match extraction interface."""
    
    # Initialize core engine
    try:
        core_engine = CoreEngine()
        print("✅ Core engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize core engine: {e}")
        return None
    
    # Add some demo players if none exist
    try:
        players = core_engine.data_manager.load_player_data()
        if not players:
            print("Adding demo players...")
            demo_players = [
                Player(name="DemoPlayer1", summoner_name="demo1#NA1", puuid=""),
                Player(name="DemoPlayer2", summoner_name="demo2#NA1", puuid=""),
                Player(name="DemoPlayer3", summoner_name="demo3#NA1", puuid="")
            ]
            
            for player in demo_players:
                core_engine.data_manager.add_player(player)
            
            print(f"✅ Added {len(demo_players)} demo players")
        else:
            print(f"✅ Found {len(players)} existing players")
    
    except Exception as e:
        print(f"⚠️ Error managing demo players: {e}")
    
    # Create match extraction interface
    try:
        extraction_interface = MatchExtractionInterface(core_engine)
        print("✅ Match extraction interface created successfully")
    except Exception as e:
        print(f"❌ Failed to create match extraction interface: {e}")
        return None
    
    # Create Gradio interface
    with gr.Blocks(
        title="Match Extraction Interface Demo",
        theme=gr.themes.Soft()
    ) as demo:
        
        gr.Markdown("""
        # 🎮 Match Extraction Interface Demo
        
        This demo showcases the interactive match extraction interface with:
        - **Real-time progress tracking** with detailed status updates
        - **Advanced configuration options** for extraction parameters
        - **Pause/resume functionality** for long-running operations
        - **Comprehensive logging** with detailed error reporting
        - **Extraction history** and operation management
        - **Scheduling and automation** options
        
        **Note:** This is a demo interface. Actual match extraction requires valid Riot API credentials.
        """)
        
        # System Status
        with gr.Row():
            gr.Markdown(f"""
            **System Status:**
            - ✅ Core Engine: Ready
            - {'✅' if core_engine.api_available else '⚠️'} Riot API: {'Connected' if core_engine.api_available else 'Not Available'}
            - {'✅' if core_engine.analytics_available else '⚠️'} Analytics: {'Available' if core_engine.analytics_available else 'Limited'}
            """)
        
        # Create the extraction interface
        try:
            extraction_components = extraction_interface.create_extraction_interface()
            print("✅ Extraction interface components created successfully")
        except Exception as e:
            print(f"❌ Error creating extraction interface components: {e}")
            gr.Markdown(f"**Error:** Failed to create extraction interface: {str(e)}")
            return None
        
        # Additional demo information
        with gr.Accordion("Demo Information", open=False):
            gr.Markdown("""
            ### Demo Features Demonstrated:
            
            1. **Configuration Panel**: 
               - Player selection with validation
               - Queue type filtering (Ranked, Normal, ARAM)
               - Extraction parameters (max matches, date range, batch size)
               - Advanced options (rate limiting, validation, retry logic)
            
            2. **Progress Tracking**:
               - Real-time progress bar and percentage
               - Detailed status messages and timeline
               - Extraction rate and estimated completion time
               - Current step and operation details
            
            3. **Control Operations**:
               - Start/pause/resume/cancel functionality
               - Configuration validation before starting
               - Save/load configuration presets
            
            4. **History and Logging**:
               - Complete extraction history with statistics
               - Real-time operation logs with auto-scroll
               - Export capabilities for logs and history
            
            5. **Scheduling and Automation**:
               - One-time scheduled extractions
               - Recurring extraction schedules
               - Automated operation management
            
            ### Usage Instructions:
            
            1. **Select a Player**: Choose from the dropdown (demo players are pre-loaded)
            2. **Configure Options**: Adjust extraction parameters as needed
            3. **Validate Configuration**: Click "Validate Configuration" to check settings
            4. **Start Extraction**: Click "Start Extraction" to begin the process
            5. **Monitor Progress**: Watch the real-time progress updates
            6. **Control Operation**: Use pause/resume/cancel as needed
            7. **Review Results**: Check the history and logs for details
            
            ### Technical Implementation:
            
            - **Modular Architecture**: Clean separation of concerns with dedicated components
            - **Thread-Safe Operations**: Background processing with proper synchronization
            - **Comprehensive Error Handling**: Graceful degradation and user-friendly messages
            - **Persistent State**: Configuration and history saved across sessions
            - **Extensible Design**: Easy to add new features and customization options
            """)
    
    return demo


if __name__ == "__main__":
    print("🚀 Starting Match Extraction Interface Demo...")
    
    demo = create_demo()
    
    if demo:
        print("✅ Demo created successfully!")
        print("🌐 Launching Gradio interface...")
        
        try:
            demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=False,
                debug=True,
                show_error=True
            )
        except Exception as e:
            print(f"❌ Failed to launch demo: {e}")
    else:
        print("❌ Failed to create demo")