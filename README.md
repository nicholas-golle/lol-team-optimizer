# League of Legends Team Optimizer

A Python application that analyzes player data to determine optimal role assignments for League of Legends teams. The system integrates with the Riot Games API to fetch performance data and combines it with user preferences to make data-driven team composition decisions.

## Features

- **Intelligent Team Optimization**: Uses mathematical optimization algorithms to find the best role assignments
- **Riot API Integration**: Fetches real player performance data from Riot Games API
- **Advanced Synergy Analysis**: Analyzes player synergies based on actual match history and performance when playing together
- **Champion Mastery Integration**: Considers champion pool depth and competency levels in optimization decisions
- **Role Preference Management**: Allows players to set and update their role preferences
- **Performance Analysis**: Analyzes individual player performance across multiple metrics (KDA, CS, vision, win rate)
- **Champion Recommendations**: Provides champion suggestions for each role assignment with confidence scoring
- **Offline Mode**: Works without API access using cached data and preferences
- **Comprehensive Caching**: Reduces API calls and improves performance
- **Detailed Explanations**: Provides reasoning behind optimization decisions with performance breakdowns

## Quick Start

### Option 1: Google Colab (Recommended for Quick Start)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nicholas-golle/lol-team-optimizer/blob/main/LoL_Team_Optimizer_Colab.ipynb)

1. Click the "Open in Colab" button above
2. Run the setup cell to install dependencies
3. Enter your Riot API key when prompted
4. Start optimizing teams!

### Option 2: Local Installation

#### Prerequisites

- Python 3.8 or higher
- Riot Games API key (optional, for enhanced features)

#### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd lol-team-optimizer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your Riot API key** (optional but recommended):
   ```bash
   # On Windows
   set RIOT_API_KEY=your_api_key_here
   
   # On macOS/Linux
   export RIOT_API_KEY=your_api_key_here
   ```
   
   Or create a `.env` file in the project root:
   ```
   RIOT_API_KEY=your_api_key_here
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

## Getting Your Riot API Key

1. Visit the [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot Games account
3. Create a new application or use the development key
4. Copy your API key and set it as an environment variable

**Note**: The application can run without an API key in offline mode, but you'll miss out on real-time performance data and player validation features.

## Usage Guide

### Main Menu Options

When you start the application, you'll see the main menu with these options:

1. **Manage Players** - Add, remove, or update player information
2. **Manage Preferences** - Set role preferences for players
3. **Optimize Team** - Run team optimization and see results
4. **View Player Data** - Display detailed player information
5. **System Maintenance** - Cache management and system utilities
6. **Exit** - Close the application

### Adding Players

1. Select "Manage Players" from the main menu
2. Choose "Add New Player"
3. Enter the player's name and Riot ID (e.g., "PlayerName#NA1")
4. The system will validate the Riot ID if API is available
5. Set initial role preferences (1-5 scale, where 5 is most preferred)

### Setting Role Preferences

Role preferences help the optimizer understand which positions players prefer:

- **5**: Strongly prefer this role
- **4**: Like this role
- **3**: Neutral about this role
- **2**: Dislike this role
- **1**: Strongly dislike this role

### Running Team Optimization

1. Ensure you have at least 5 players in the system
2. Select "Optimize Team" from the main menu
3. Choose which players to include (if you have more than 5)
4. Review the optimization results
5. Optionally view alternative team compositions

### Understanding Results

The optimization results show:

- **Role Assignments**: Which player is assigned to each role
- **Total Score**: Overall team composition score
- **Individual Scores**: Performance score for each player in their assigned role
- **Detailed Analysis**: Explanation of why assignments were made
- **Alternative Compositions**: Other viable team setups

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

### Scoring System Documentation
For information about how the system calculates scores and makes optimization decisions:
- **[Scoring Quick Reference](SCORING_QUICK_REFERENCE.md)** - Quick guide to score ranges, meanings, and interpretation
- **[Scoring Calculations Documentation](SCORING_CALCULATIONS.md)** - Comprehensive technical guide to all algorithms, formulas, and calculations

### Additional Documentation
- **[API Setup Guide](API_SETUP.md)** - How to obtain and configure your Riot API key
- **[Setup Instructions](SETUP.md)** - Detailed installation and configuration guide

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

### Common Issues

**"API key not found" or running in offline mode**
- Set your `RIOT_API_KEY` environment variable
- Verify the API key is valid and not expired
- Check your internet connection

**"Permission denied" errors**
- Ensure the application has write permissions to the data directory
- Try running as administrator (Windows) or with sudo (macOS/Linux)

**"Rate limit exceeded" errors**
- Wait a few minutes before making more API requests
- The application automatically handles rate limiting with backoff

**"No players found" or insufficient players**
- Add at least 5 players to the system
- Verify player Riot IDs are correct
- Check that player data was saved properly

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Set environment variable
export DEBUG=true

# Or add to .env file
DEBUG=true
```

Debug mode provides:
- Detailed operation logging
- Performance metrics
- Error context and stack traces
- API request/response logging

### Log Files

The application creates several log files in the `data/logs/` directory:

- `app.log`: General application logs
- `errors.log`: Detailed error information
- `performance.log`: Performance metrics
- `user_actions.log`: User interaction tracking
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