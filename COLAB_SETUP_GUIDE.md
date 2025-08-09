# 🎮 LoL Team Optimizer - Colab Setup Guide

## 🚨 Fixing "No module named 'gradio_ui'" Error

If you encounter the error `No module named 'gradio_ui'` when running the Colab notebook, follow these steps:

### Quick Fix (Recommended)

1. **Restart the Runtime**
   - Go to `Runtime` → `Restart runtime`
   - This clears any cached imports

2. **Re-run Setup Cells**
   - Run the installation cell again
   - Make sure all dependencies install successfully

3. **Use Alternative Launch Method**
   ```python
   # Instead of importing gradio_ui, run this directly:
   exec(open('launch_gradio.py').read())
   ```

### Detailed Troubleshooting

#### Step 1: Verify Repository Structure
```python
import os
print("📁 Current directory:", os.getcwd())
print("📋 Files in directory:")
for item in sorted(os.listdir('.')):
    if item.endswith('.py') or os.path.isdir(item):
        print(f"   {item}")
```

#### Step 2: Check Required Files
The following files should be present:
- ✅ `gradio_ui.py` - Main UI file
- ✅ `launch_gradio.py` - Alternative launcher
- ✅ `lol_team_optimizer/` - Core package directory
- ✅ `lol_team_optimizer/core_engine.py` - Core engine

#### Step 3: Manual Import Test
```python
# Test if the module can be imported
try:
    import sys
    sys.path.append('.')
    from gradio_ui import GradioUI, launch_ui
    print("✅ Import successful!")
except ImportError as e:
    print(f"❌ Import failed: {e}")
```

#### Step 4: Alternative Launch Methods

**Method 1: Direct Execution**
```python
exec(open('gradio_ui.py').read())
```

**Method 2: Using Launcher Script**
```python
exec(open('launch_gradio.py').read())
```

**Method 3: Manual Module Loading**
```python
import importlib.util
spec = importlib.util.spec_from_file_location("gradio_ui", "gradio_ui.py")
gradio_ui_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gradio_ui_module)
gradio_ui_module.launch_ui(share=True)
```

### Common Issues and Solutions

#### Issue 1: Repository Not Cloned Properly
**Solution:** Re-clone the repository
```python
!rm -rf lol_team_optimizer gradio_ui.py launch_gradio.py
!git clone https://github.com/nicholas-golle/lol-team-optimizer.git .
```

#### Issue 2: Python Path Issues
**Solution:** Add current directory to path
```python
import sys
import os
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
```

#### Issue 3: Dependencies Missing
**Solution:** Reinstall dependencies
```python
!pip install --upgrade gradio plotly pandas requests python-dotenv nest-asyncio
```

#### Issue 4: Colab Environment Issues
**Solution:** Complete runtime restart
1. `Runtime` → `Factory reset runtime`
2. Re-run all cells from the beginning

### Fallback Interface

If all else fails, you can create a minimal interface:

```python
import gradio as gr

def create_minimal_interface():
    with gr.Blocks(title="LoL Team Optimizer - Minimal") as demo:
        gr.Markdown("# 🎮 LoL Team Optimizer - Minimal Mode")
        gr.Markdown("""
        The full interface couldn't load, but you can still use the core functionality.
        
        **Next Steps:**
        1. Check the troubleshooting guide
        2. Restart the runtime and try again
        3. Verify all files are present
        """)
        
        # Basic functionality test
        def test_core():
            try:
                from lol_team_optimizer.core_engine import CoreEngine
                engine = CoreEngine()
                return "✅ Core engine loaded successfully!"
            except Exception as e:
                return f"❌ Core engine failed: {e}"
        
        test_btn = gr.Button("Test Core Engine")
        test_output = gr.Markdown()
        test_btn.click(fn=test_core, outputs=test_output)
    
    return demo

# Launch minimal interface
demo = create_minimal_interface()
demo.launch(share=True)
```

### Getting Help

If you're still having issues:

1. **Check the Error Details**
   - Look at the full error traceback
   - Note which specific import is failing

2. **Verify Environment**
   - Make sure you're using a standard Colab runtime
   - Check that your internet connection is stable

3. **Try a Fresh Start**
   - Create a new Colab notebook
   - Copy and paste the cells one by one

4. **Report Issues**
   - If the problem persists, create an issue on the GitHub repository
   - Include the full error message and your setup details

## 🎯 Quick Start Commands

For a quick start, run these commands in order:

```python
# 1. Install dependencies
!pip install -q gradio plotly pandas requests python-dotenv nest-asyncio

# 2. Clone repository
!git clone https://github.com/nicholas-golle/lol-team-optimizer.git .

# 3. Launch interface
exec(open('launch_gradio.py').read())
```

This should get you up and running quickly! 🚀