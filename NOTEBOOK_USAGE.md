# Jupyter Notebook Usage Guide - Simplified Interface

## Overview

The simplified Jupyter notebook interface provides a clean, notebook-optimized way to use the League of Legends Team Optimizer. It's built as a thin wrapper around the unified core engine, ensuring consistency with the streamlined CLI while providing notebook-friendly output formatting.

## Key Features

### ✨ Streamlined Design
- **Single Setup Cell**: One cell handles all initialization
- **Core Engine Integration**: All functions call the unified core system directly
- **Notebook-Optimized Output**: Enhanced formatting for Jupyter/Colab environments
- **Smart Error Handling**: Contextual troubleshooting and helpful tips

### 🔧 No Code Duplication
- All business logic handled by the core engine
- Notebook functions are simple wrappers with enhanced display
- Consistent behavior across CLI and notebook interfaces
- Unified data management and optimization algorithms

## Usage Pattern

### 1. Initialization
Run the single setup cell to initialize the system:
```python
# This cell handles environment detection, dependency installation,
# API setup, and core engine initialization automatically
```

### 2. Player Management
```python
# Add players with automatic data fetching
add_player("PlayerName", "gameName#tagLine")

# View current roster with data completeness indicators
list_players()

# Check system status
system_status()
```

### 3. Team Optimization
```python
# Run optimization with smart defaults
result = optimize_team()

# Or specify players manually
result = optimize_team(["Player1", "Player2", "Player3", "Player4", "Player5"])
```

### 4. Analysis
```python
# Get comprehensive team analysis
analysis = analyze_players()

# Or analyze specific players
analysis = analyze_players(["Player1", "Player2"])
```

## Function Reference

### Core Functions

#### `add_player(name, riot_id, auto_fetch=True)`
- Adds a player using the core engine
- Automatically fetches API data if available
- Shows data completeness and progress toward optimization
- **Core Engine Method**: `engine.add_player_with_data()`

#### `list_players()`
- Lists all players with enhanced status display
- Shows data completeness indicators (📊🏆⭐📝)
- Displays preferred roles and data freshness
- **Core Engine Method**: `engine.data_manager.load_player_data()`

#### `optimize_team(player_names=None, auto_select=True)`
- Runs team optimization with notebook-friendly output
- Automatically selects best players if not specified
- Shows role assignments, scores, and champion recommendations
- **Core Engine Method**: `engine.optimize_team_smart()`

#### `analyze_players(player_names=None)`
- Provides comprehensive team and player analysis
- Shows system status, team readiness, and recommendations
- Analyzes all players or specified subset
- **Core Engine Method**: `engine.get_comprehensive_analysis()`

#### `system_status()`
- Displays current system health and configuration
- Shows player count, API status, and data quality
- Provides next steps and recommendations
- **Core Engine Data**: `engine.system_status`

## Visual Indicators

### Data Completeness
- 🟢 **Fresh/Complete**: Recent data, high completeness
- 🟡 **Partial/Aging**: Some data missing or older
- 🔴 **Poor/Stale**: Limited data or very old
- ⚫ **None**: No data available

### Player Status Icons
- 📊 **Performance Data**: Has match history and performance metrics
- 🏆 **Champion Data**: Has champion mastery information
- ⭐ **Preferences**: Has custom role preferences set
- 📝 **Basic**: Basic player information only

### Score Indicators
- 🟢 **High Score**: 4.0+ (excellent performance)
- 🟡 **Medium Score**: 2.0-3.9 (good performance)
- 🔴 **Low Score**: <2.0 (needs improvement)

## Troubleshooting

### Common Issues

#### Setup Problems
- **Import Errors**: Restart runtime and re-run setup cell
- **API Issues**: Check API key format and internet connection
- **Permission Errors**: Ensure write access to data directories

#### Player Management
- **Player Not Found**: Verify Riot ID spelling and format
- **API Rate Limits**: Wait a few minutes before retrying
- **Data Fetching Fails**: System continues with limited functionality

#### Optimization Issues
- **Not Enough Players**: Add more players or use partial optimization
- **Poor Results**: Check data quality and player preferences
- **Slow Performance**: Reduce player count or check system resources

### Best Practices

1. **API Key Setup**: Get your free key from https://developer.riotgames.com/
2. **Riot ID Format**: Always use `gameName#tagLine` format
3. **Data Quality**: Monitor completeness indicators for best results
4. **Regular Updates**: Refresh player data periodically
5. **Error Handling**: Functions provide contextual help for issues

## Core Engine Integration

The notebook interface is designed as a thin wrapper around the unified core engine that also powers the streamlined CLI:

```
Streamlined CLI ──┐
                  ├── Core Engine ── Business Logic
Notebook Interface ──┘        ↓              ↓
     ↓                   Unified API    Optimization
Enhanced Display        Data Mgmt      Algorithms  
Error Handling         API Client     Calculations
User Feedback          Smart Defaults  Team Analysis
```

This unified architecture ensures:
- **Consistency**: Identical logic and results across CLI and notebook
- **Maintainability**: Single source of truth for all business logic
- **Reliability**: Thoroughly tested core system with proven algorithms
- **Feature Parity**: All CLI capabilities available in notebook format

## Advanced Usage

### Custom Workflows
```python
# Batch player addition
players = [
    ("Player1", "name1#tag1"),
    ("Player2", "name2#tag2"),
    ("Player3", "name3#tag3")
]

for name, riot_id in players:
    add_player(name, riot_id)

# Multiple optimization runs
for i in range(3):
    print(f"\\nOptimization Run {i+1}:")
    result = optimize_team()
```

### Integration with Other Tools
```python
# Export results for external analysis
import json

result = optimize_team()
if result:
    # Access core engine data directly
    assignments = result.best_assignment.assignments
    scores = result.best_assignment.individual_scores
    
    # Export to JSON
    export_data = {
        'assignments': assignments,
        'scores': scores,
        'timestamp': str(datetime.now())
    }
    
    with open('optimization_results.json', 'w') as f:
        json.dump(export_data, f, indent=2)
```

## Support

For additional help:
- Check the main [README.md](README.md) for general information
- Review [API_SETUP.md](API_SETUP.md) for API configuration
- Examine the core engine source for advanced customization
- Use the CLI interface for additional features not available in the notebook