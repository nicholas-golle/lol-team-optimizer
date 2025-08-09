#!/usr/bin/env python3
"""
Simple launcher for the LoL Team Optimizer Gradio UI

This script provides a simple way to launch the Gradio interface,
with fallback options if the main UI fails to load.
"""

import sys
import os
import traceback

def main():
    """Main launcher function."""
    print("🎮 LoL Team Optimizer - Gradio UI Launcher")
    print("=" * 50)
    
    # Add current directory to Python path
    if os.getcwd() not in sys.path:
        sys.path.append(os.getcwd())
    
    # Try to import and launch the main UI
    try:
        print("📦 Importing Gradio UI...")
        
        # Check if gradio_ui.py exists
        if not os.path.exists('gradio_ui.py'):
            raise FileNotFoundError("gradio_ui.py not found in current directory")
        
        # Import the UI
        from gradio_ui import GradioUI, launch_ui
        
        print("✅ Successfully imported Gradio UI")
        print("🚀 Launching interface...")
        
        # Launch the UI
        launch_ui(share=True, server_port=7860)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n🔧 Trying alternative import method...")
        
        try:
            # Try importing the module directly
            import importlib.util
            
            spec = importlib.util.spec_from_file_location("gradio_ui", "gradio_ui.py")
            gradio_ui_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gradio_ui_module)
            
            print("✅ Alternative import successful")
            print("🚀 Launching interface...")
            
            # Launch using the imported module
            gradio_ui_module.launch_ui(share=True, server_port=7860)
            
        except Exception as alt_error:
            print(f"❌ Alternative import also failed: {alt_error}")
            create_fallback_interface()
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("\n📁 Current directory contents:")
        for item in sorted(os.listdir('.')):
            if item.endswith('.py') or os.path.isdir(item):
                print(f"   {item}")
        create_fallback_interface()
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("\n🔍 Full error details:")
        traceback.print_exc()
        create_fallback_interface()


def create_fallback_interface():
    """Create a simple fallback interface."""
    print("\n🔄 Creating fallback interface...")
    
    try:
        import gradio as gr
        
        def show_status():
            return """
            # 🎮 LoL Team Optimizer - Fallback Mode
            
            The main interface could not be loaded. This is usually due to:
            
            ## Common Issues:
            1. **Missing dependencies** - Run the installation cell again
            2. **Repository not cloned** - Make sure the repository was downloaded
            3. **API key not configured** - Set up your Riot API key
            4. **Python path issues** - Restart the runtime and try again
            
            ## Next Steps:
            1. Restart the runtime (Runtime → Restart runtime)
            2. Re-run all setup cells from the beginning
            3. Make sure all dependencies are installed
            4. Verify your API key is configured
            
            ## Manual Setup:
            If issues persist, you can try running the core engine directly:
            
            ```python
            from lol_team_optimizer.core_engine import CoreEngine
            engine = CoreEngine()
            ```
            """
        
        def check_dependencies():
            """Check if required dependencies are available."""
            results = []
            
            # Check core dependencies
            deps = [
                ('gradio', 'Gradio web framework'),
                ('plotly', 'Plotting library'),
                ('pandas', 'Data analysis library'),
                ('requests', 'HTTP library'),
            ]
            
            for dep, desc in deps:
                try:
                    __import__(dep)
                    results.append(f"✅ {dep} - {desc}")
                except ImportError:
                    results.append(f"❌ {dep} - {desc} (MISSING)")
            
            # Check LoL Team Optimizer modules
            lol_modules = [
                ('lol_team_optimizer.core_engine', 'Core engine'),
                ('lol_team_optimizer.models', 'Data models'),
                ('lol_team_optimizer.config', 'Configuration'),
            ]
            
            results.append("\n**LoL Team Optimizer Modules:**")
            for module, desc in lol_modules:
                try:
                    __import__(module)
                    results.append(f"✅ {module} - {desc}")
                except ImportError as e:
                    results.append(f"❌ {module} - {desc} (ERROR: {e})")
            
            return "\n".join(results)
        
        def check_files():
            """Check if required files exist."""
            results = []
            
            required_files = [
                'gradio_ui.py',
                'lol_team_optimizer/',
                'lol_team_optimizer/core_engine.py',
                'lol_team_optimizer/models.py',
            ]
            
            results.append("**File Check:**")
            for file_path in required_files:
                if os.path.exists(file_path):
                    results.append(f"✅ {file_path}")
                else:
                    results.append(f"❌ {file_path} (MISSING)")
            
            return "\n".join(results)
        
        # Create the fallback interface
        with gr.Blocks(title="LoL Team Optimizer - Fallback") as demo:
            gr.Markdown("# 🎮 LoL Team Optimizer - Fallback Mode")
            
            with gr.Tabs():
                with gr.Tab("📋 Status"):
                    status_output = gr.Markdown(show_status())
                
                with gr.Tab("🔍 Diagnostics"):
                    gr.Markdown("## Dependency Check")
                    dep_check_btn = gr.Button("Check Dependencies")
                    dep_output = gr.Markdown()
                    
                    gr.Markdown("## File Check")
                    file_check_btn = gr.Button("Check Files")
                    file_output = gr.Markdown()
                    
                    dep_check_btn.click(fn=check_dependencies, outputs=dep_output)
                    file_check_btn.click(fn=check_files, outputs=file_output)
                
                with gr.Tab("🔧 Manual Setup"):
                    gr.Markdown("""
                    ## Manual Setup Instructions
                    
                    If the automatic setup failed, try these manual steps:
                    
                    ### 1. Install Dependencies
                    ```bash
                    pip install gradio plotly pandas requests python-dotenv
                    ```
                    
                    ### 2. Clone Repository
                    ```bash
                    git clone https://github.com/yourusername/lol-team-optimizer.git
                    cd lol-team-optimizer
                    ```
                    
                    ### 3. Set API Key
                    ```python
                    import os
                    os.environ['RIOT_API_KEY'] = 'your_api_key_here'
                    ```
                    
                    ### 4. Launch UI
                    ```python
                    from gradio_ui import launch_ui
                    launch_ui(share=True)
                    ```
                    """)
        
        print("✅ Fallback interface created")
        print("🚀 Launching fallback interface...")
        
        demo.launch(share=True, server_port=7860)
        
    except Exception as fallback_error:
        print(f"❌ Even the fallback interface failed: {fallback_error}")
        print("This suggests a serious environment issue.")
        print("\nPlease try:")
        print("1. Restart the runtime completely")
        print("2. Re-run the installation cell")
        print("3. Check your internet connection")
        print("4. Verify Colab is working properly")


if __name__ == "__main__":
    main()