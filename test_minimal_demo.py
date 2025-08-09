#!/usr/bin/env python3
"""Minimal test to debug the import issue."""

print("Testing step by step...")

# Test if we can import the module
try:
    import lol_team_optimizer.recommendation_visualization_analyzer as rva
    print("✓ Module imported")
    print(f"Module file: {rva.__file__}")
    print(f"Module contents: {[x for x in dir(rva) if not x.startswith('_')]}")
except Exception as e:
    print(f"✗ Module import failed: {e}")
    exit(1)

# Test if we can see the class
try:
    cls = getattr(rva, 'RecommendationVisualizationAnalyzer', None)
    if cls:
        print(f"✓ Class found: {cls}")
    else:
        print("✗ Class not found")
        
        # Let's see what classes are available
        classes = []
        for name in dir(rva):
            obj = getattr(rva, name)
            if isinstance(obj, type):
                classes.append(name)
        print(f"Available classes: {classes}")
        
        # Let's see what dataclasses are available
        dataclasses = []
        for name in dir(rva):
            obj = getattr(rva, name)
            if hasattr(obj, '__dataclass_fields__'):
                dataclasses.append(name)
        print(f"Available dataclasses: {dataclasses}")
        
except Exception as e:
    print(f"✗ Error checking class: {e}")

# Let's try to read the file and see what's actually in it
try:
    with open('lol_team_optimizer/recommendation_visualization_analyzer.py', 'r') as f:
        content = f.read()
        
    if 'class RecommendationVisualizationAnalyzer' in content:
        print("✓ Class definition found in file")
    else:
        print("✗ Class definition NOT found in file")
        
    # Count lines
    lines = content.split('\n')
    print(f"File has {len(lines)} lines")
    
    # Find class definitions
    class_lines = [i for i, line in enumerate(lines) if line.strip().startswith('class ')]
    print(f"Class definitions at lines: {class_lines}")
    
    for line_num in class_lines:
        print(f"  Line {line_num + 1}: {lines[line_num].strip()}")
        
except Exception as e:
    print(f"✗ Error reading file: {e}")

print("Done.")