# 🎮 League of Legends Team Optimizer v2.0

**Advanced Analytics & Team Optimization Platform with Modern Web UI**

A comprehensive platform for analyzing League of Legends gameplay, optimizing team compositions, and providing AI-powered champion recommendations. Now featuring a modern **Gradio web interface** with interactive charts, real-time analytics, and multiple deployment options including Google Colab support.

## ✨ NEW: Gradio Web Interface

🌟 **Major Update**: Now includes a beautiful web interface built with Gradio!

- 🖥️ **Modern Web UI**: Interactive interface with tabbed navigation
- 📊 **Real-time Charts**: Dynamic visualizations using Plotly
- 📱 **Mobile Friendly**: Works on any device with a web browser
- 🔗 **Shareable URLs**: Public links for team collaboration
- ☁️ **Google Colab**: One-click setup in the cloud
- 🎭 **Demo Mode**: Try it out with sample data (no API key needed)

### Quick Start with Web UI:
```bash
# Install dependencies
pip install -r requirements_gradio.txt

# Launch web interface
python launch_gradio.py --share
```

Or try the **[Google Colab notebook](LoL_Team_Optimizer_Gradio_Colab.ipynb)** for instant access!

## Features

### 🎯 Streamlined Interface
- **4-Option Menu**: Quick Optimize, Manage Players, View Analysis, and Settings
- **Smart Workflows**: Integrated processes that handle player selection and data fetching automatically
- **Intelligent Defaults**: Automatic data enhancement and preference management
- **One-Click Optimization**: Complete team optimization with minimal user input

### 🚀 Core Capabilities
- **Advanced Team Optimization**: Mathematical algorithms find optimal role assignments
- **Riot API Integration**: Real-time player performance data from Riot Games API
- **Champion Mastery Analysis**: Deep champion pool and competency evaluation
- **Team Synergy Scoring**: Data-driven analysis of player chemistry and performance
- **Performance Analytics**: Multi-metric analysis (KDA, CS, vision, win rate, trends)
- **Champion Recommendations**: AI-powered champion suggestions with confidence scoring
- **Offline Mode**: Full functionality using cached data and preferences
- **Smart Caching**: Optimized API usage with intelligent data retention

## Quick Start

### 🚀 Streamlined Workflow (3 Steps)

1. **Install and Run**:
   ```bash
   git clone <repository-url>
   cd lol-team-optimizer
   pip install -r requirements.txt
   python main.py
   ```

2. **Add Players**: Use option 2 or quick action 'a' to add your team members
3. **Optimize**: Use option 1 for instant team optimization with smart defaults

### 📱 Alternative: Jupyter Notebook

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nicholas-golle/lol-team-optimizer/blob/main/LoL_Team_Optimizer_Colab.ipynb)

The simplified notebook interface provides the same core functionality with notebook-optimized display and single-cell setup.

### ⚙️ Prerequisites

- **Python**: 3.8 or higher
- **API Key**: Optional but recommended for enhanced features ([Get yours here](https://developer.riotgames.com/))

### 🔑 API Key Setup (Optional)

Create a `.env` file in the project root:
```
RIOT_API_KEY=RGAPI-your-key-here
```

Or set as environment variable:
```bash
# Windows
set RIOT_API_KEY=RGAPI-your-key-here

# macOS/Linux  
export RIOT_API_KEY=RGAPI-your-key-here
```

**Note**: The application works in offline mode without an API key, using cached data and preferences.

## Getting Your Riot API Key

1. Visit the [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot Games account
3. Create a new application or use the development key
4. Copy your API key and set it as an environment variable

**Note**: The application can run without an API key in offline mode, but you'll miss out on real-time performance data and player validation features.

## Streamlined Interface Guide

### 🎯 4-Option Main Menu

The new streamlined interface consolidates all functionality into 4 intuitive options:

#### 1. 🎯 Quick Optimize
**One-click team optimization with smart automation**
- Automatically selects best players based on data quality
- Handles missing data and preferences inline
- Provides comprehensive results with champion recommendations
- Offers follow-up actions like alternatives and detailed analysis

#### 2. 👥 Manage Players  
**Consolidated player management in one place**
- Add new players with automatic API data fetching
- Edit existing players and update preferences
- Remove players or perform bulk operations
- View detailed player statistics and data completeness

#### 3. 📊 View Analysis
**Comprehensive insights and team analytics**
- Team overview and optimization readiness assessment
- Individual player analysis and role suitability comparisons
- Champion pool analysis across all players
- Team synergy analysis with performance data
- Historical trends and improvement recommendations

#### 4. ⚙️ Settings
**System configuration and maintenance**
- API connectivity testing and diagnostics
- Cache management and data refresh utilities
- System health checks and troubleshooting
- Export capabilities and backup options

### ⚡ Quick Actions

From the main menu, use these shortcuts:
- **'a'** - Quick add player
- **'o'** - Quick optimize
- **'h'** - Help and detailed guide

### 🚀 Typical Workflow

1. **First Time**: Add 5+ players using option 2 or quick action 'a'
2. **Optimize**: Use option 1 for instant team optimization
3. **Analyze**: Use option 3 for detailed insights and comparisons
4. **Maintain**: Use option 4 for system health and updates

### 📊 Understanding Results

Optimization results include:
- **Role Assignments**: Optimal player-to-role mapping
- **Performance Scores**: Individual and team performance metrics
- **Champion Recommendations**: Top 3 champions per role with mastery data
- **Team Synergy**: Data-driven chemistry analysis
- **Alternative Compositions**: Other viable team setups
- **Detailed Explanations**: AI-powered reasoning for decisions

## Configuration

The application can be configured through environment variables:

### API Configuration
- `RIOT_API_KEY`: Your Riot Games API key
- `RIOT_API_BASE_URL`: API base URL (default: https://americas.api.riotgames.com)
- `RIOT_API_RATE_LIMIT`: Requests per 2 minutes (default: 120)

### Performance Weights
- `INDIVIDUAL_WEIGHT`: Weight for individual performance (default: 0.6)
- `PREFERENCE_WEIGHT`: Weight for role preferences (default: 0.3)
- `SYNERGY_WEIGHT`: Weight for team synergy (default: 0.1)

### Cache Settings
- `CACHE_DURATION_HOURS`: API response cache duration (default: 1)
- `PLAYER_DATA_CACHE_HOURS`: Player data cache duration (default: 24)
- `MAX_CACHE_SIZE_MB`: Maximum cache size in MB (default: 50)

### Data Storage
- `DATA_DIRECTORY`: Directory for data files (default: data)
- `CACHE_DIRECTORY`: Directory for cache files (default: cache)

### Application Settings
- `LOG_LEVEL`: Logging level (default: INFO)
- `DEBUG`: Enable debug mode (default: false)
- `MAX_MATCHES_TO_ANALYZE`: Number of recent matches to analyze (default: 20)

## Documentation

### 📚 Getting Started
- **[Quick Start Guide](QUICK_START_GUIDE.md)** - Get up and running in 5 minutes with the streamlined interface
- **[Menu Examples](MENU_EXAMPLES.md)** - Detailed examples and use cases for each of the 4 main menu options
- **[Setup Instructions](SETUP.md)** - Comprehensive installation and configuration guide
- **[API Setup Guide](API_SETUP.md)** - Unified API key configuration for the streamlined interface

### 🔧 Usage and Troubleshooting
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions for the streamlined interface
- **[Notebook Usage](NOTEBOOK_USAGE.md)** - Simplified Jupyter/Colab interface guide

### 📊 Technical Documentation
- **[Scoring Quick Reference](SCORING_QUICK_REFERENCE.md)** - Score ranges, meanings, and interpretation
- **[Scoring Calculations](SCORING_CALCULATIONS.md)** - Technical guide to algorithms and formulas

## Advanced Features

### System Maintenance

The system maintenance menu provides tools for:

- **Clear Expired Cache**: Remove old cached data
- **View Cache Statistics**: See cache usage and performance
- **Validate Player Data**: Check data consistency
- **Refresh Player Data**: Update all player information from API
- **Export Player Data**: Create backup of player information

### Performance Analysis

The application analyzes multiple performance metrics:

- **KDA Ratio**: Kill/Death/Assist performance
- **CS per Minute**: Creep score farming efficiency
- **Vision Score**: Ward placement and vision control
- **Win Rate**: Success rate in specific roles
- **Recent Form**: Performance trends over recent matches

### Team Synergy Analysis

The system provides comprehensive synergy analysis based on actual match history:

#### Data-Driven Synergy Scoring
- **Match History Analysis**: Analyzes games where players played together on the same team
- **Win Rate Tracking**: Calculates success rates for specific player combinations
- **Role Combination Analysis**: Tracks performance for specific role pairings (e.g., Player A top + Player B jungle)
- **Champion Synergy**: Identifies successful champion combinations between players

#### Synergy Features
- **Update Synergy Data**: Fetches recent match history to build comprehensive synergy database
- **Player Synergy Analysis**: View best and worst teammates for individual players
- **Team Synergy Reports**: Analyze synergy for groups of players with detailed breakdowns
- **Historical Tracking**: Maintains persistent synergy data with temporal weighting for recent games

#### Synergy Scoring Factors
- **Overall Win Rate**: Success rate when playing together across all games
- **Performance Metrics**: Combined KDA, vision score, and game impact when teamed
- **Recency Weighting**: Recent games weighted more heavily than historical data
- **Sample Size Confidence**: Larger game samples provide more reliable synergy scores
- **Role-Specific Analysis**: Different synergy scores for different role combinations

The synergy system transforms team optimization from theoretical role compatibility to data-driven analysis of actual player chemistry and performance.

## Troubleshooting

### 🚨 Quick Solutions

**System shows "API: ⚠️ Offline"**
- Check your `.env` file contains `RIOT_API_KEY=RGAPI-your-key-here`
- Verify API key is valid at [developer.riotgames.com](https://developer.riotgames.com/)
- Test connectivity in Settings → System Diagnostics

**"No players found" or insufficient players**
- Add players using option 2 (Manage Players) or quick action 'a'
- Ensure Riot IDs use format `gameName#tagLine`
- Check system status shows players were saved successfully

**Poor optimization results**
- Set custom role preferences for key players
- Refresh player data to get latest performance metrics
- Ensure players have recent match history for accurate analysis

**Application runs slowly**
- Clear cache in Settings → Cache Management
- Reduce cache size in configuration
- Check available system memory and close other applications

### 🔧 Advanced Troubleshooting

For comprehensive troubleshooting including installation issues, API problems, and performance optimization, see the **[Troubleshooting Guide](TROUBLESHOOTING.md)**.

### 📊 Debug Mode

Enable detailed logging by adding to your `.env` file:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

This provides:
- Detailed operation logging and performance metrics
- API request/response information
- Error context and stack traces
- System diagnostics and health information

### 📁 Log Files

Check `data/logs/` directory for:
- `app.log`: General application activity
- `errors.log`: Detailed error information and stack traces
- `debug.log`: Verbose debug information (debug mode only)

## API Rate Limits

The Riot Games API has rate limits:

- **Personal API Key**: 100 requests every 2 minutes
- **Production API Key**: Higher limits available

The application automatically:
- Respects rate limits with exponential backoff
- Caches responses to minimize API calls
- Provides graceful degradation when limits are exceeded

## Data Privacy

The application:
- Stores data locally on your machine
- Does not transmit personal data to external servers
- Only communicates with Riot Games API for game data
- Allows you to export and delete your data at any time

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## Support

For support:

1. Check this README for common solutions
2. Review the troubleshooting section
3. Enable debug mode for detailed logs
4. Check the GitHub issues page
5. Create a new issue with detailed information

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Disclaimer

This application is not affiliated with Riot Games. League of Legends is a trademark of Riot Games, Inc.