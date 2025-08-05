# Quick Start Guide - Streamlined Interface

Welcome to the League of Legends Team Optimizer's streamlined interface! This guide will get you up and running in minutes.

## 🚀 Installation (2 Minutes)

### Step 1: Download and Install
```bash
# Clone the repository
git clone <repository-url>
cd lol-team-optimizer

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Optional API Setup
Get enhanced features with a free API key from [Riot Developer Portal](https://developer.riotgames.com/):

```bash
# Create .env file
echo "RIOT_API_KEY=RGAPI-your-key-here" > .env
```

### Step 3: Launch
```bash
python main.py
```

## 🎯 First-Time Workflow (5 Minutes)

### Welcome Screen
When you first launch, you'll see:
- System status showing 0 players
- 4-option streamlined menu
- Quick tips for getting started

### Add Your First Players
1. **Choose option 2** (Manage Players) or **press 'a'** for quick add
2. **Enter player details**:
   - Player name: `YourTeammate`
   - Riot ID: `gameName#tagLine` (e.g., `Faker#KR1`)
3. **Repeat for 4-5 players** (minimum 5 recommended)

The system will automatically:
- ✅ Validate Riot IDs (if API available)
- 📊 Fetch performance data
- 🏆 Load champion mastery
- ⭐ Set default preferences

### Run Your First Optimization
1. **Choose option 1** (Quick Optimize) or **press 'o'**
2. **Select optimization mode**:
   - 🤖 Auto-select (recommended for beginners)
   - 👤 Manual selection
   - 🌐 Use all players
3. **Review and enhance data** (optional):
   - System will offer to fetch missing data
   - Set custom role preferences for better results
4. **Get results** with comprehensive analysis

## 📋 4-Option Menu Explained

### 🎯 Option 1: Quick Optimize
**What it does**: Complete team optimization in one streamlined workflow
**When to use**: When you want fast, accurate team compositions
**Features**:
- Smart player selection based on data quality
- Automatic data enhancement and preference prompting
- Comprehensive results with champion recommendations
- Follow-up actions for alternatives and analysis

### 👥 Option 2: Manage Players
**What it does**: All player operations in one consolidated interface
**When to use**: Adding new players, updating preferences, or reviewing roster
**Features**:
- Add players with automatic API data fetching
- Edit existing players and their role preferences
- Remove players or perform bulk operations
- View detailed player information and data completeness

### 📊 Option 3: View Analysis
**What it does**: Comprehensive team and player analytics dashboard
**When to use**: Deep analysis, comparisons, and strategic planning
**Features**:
- Team readiness assessment and optimization recommendations
- Side-by-side player comparisons with role suitability
- Champion pool analysis across all players
- Team synergy analysis with historical performance data
- Performance trends and improvement suggestions

### ⚙️ Option 4: Settings
**What it does**: System configuration, diagnostics, and maintenance
**When to use**: Troubleshooting, system health checks, or configuration changes
**Features**:
- API connectivity testing and rate limit monitoring
- Cache management and data refresh utilities
- System diagnostics and health reports
- Export logs and backup data

## 💡 Pro Tips for Best Results

### Data Quality Matters
- **API Key**: Provides real performance data and validation
- **Recent Activity**: Players with recent matches get better analysis
- **Custom Preferences**: Override defaults for players with strong role preferences

### Optimization Strategies
- **Start Simple**: Use auto-select for your first optimization
- **Iterate**: Run multiple optimizations with different player combinations
- **Analyze**: Use View Analysis to understand why certain assignments were made
- **Customize**: Adjust preferences based on results and re-optimize

### Understanding Indicators
- 🟢 **High scores** (4.0+): Excellent performance expected
- 🟡 **Medium scores** (2.0-3.9): Good performance, some room for improvement
- 🔴 **Low scores** (<2.0): Consider alternative assignments or role training

### Data Completeness Icons
- 📊 **Performance Data**: Has match history and performance metrics
- 🏆 **Champion Data**: Has champion mastery information
- ⭐ **Custom Preferences**: Has user-set role preferences
- 📝 **Basic Only**: Limited data, may need enhancement

## 🔧 Common First-Time Issues

### "No Players Found"
**Solution**: Add players using option 2 or quick action 'a'

### "API Key Not Found" / "Offline Mode"
**Solution**: 
1. Get free API key from [developer.riotgames.com](https://developer.riotgames.com/)
2. Add to `.env` file: `RIOT_API_KEY=RGAPI-your-key-here`
3. Restart application

### "Invalid Riot ID"
**Solution**: Use format `gameName#tagLine` (e.g., `Faker#KR1`, not just `Faker`)

### "Rate Limited" Errors
**Solution**: Wait 2 minutes, then try again. The system handles this automatically.

### Poor Optimization Results
**Solutions**:
1. Add more players (5+ recommended)
2. Set custom role preferences for key players
3. Ensure players have recent match history
4. Check data completeness in View Analysis

## 🎮 Example Walkthrough

Let's optimize a 5-player team:

### Step 1: Add Players
```
Option 2 → Add New Player
Player 1: TopLaner → TopMain#NA1
Player 2: Jungler → JungleKing#NA1  
Player 3: MidLaner → MidGod#NA1
Player 4: ADCMain → BotCarry#NA1
Player 5: Support → SupportPro#NA1
```

### Step 2: Quick Optimize
```
Option 1 → Auto-select best players → Enhance data (Y) → Set preferences (Y)
```

### Step 3: Review Results
```
Results show:
- Role assignments with confidence scores
- Champion recommendations per role
- Team synergy analysis
- Alternative compositions
```

### Step 4: Deep Analysis
```
Option 3 → View comprehensive analysis
- Individual player strengths/weaknesses
- Role coverage assessment
- Champion pool overlap analysis
- Performance trend insights
```

## 🚀 Next Steps

Once you're comfortable with the basics:

1. **Explore Advanced Features**:
   - Team synergy analysis with historical data
   - Champion pool optimization
   - Performance trend analysis

2. **Customize Your Experience**:
   - Adjust optimization weights in settings
   - Set up automated data refresh
   - Export results for external analysis

3. **Scale Your Usage**:
   - Add substitute players for flexibility
   - Track performance over time
   - Use for tournament preparation

## 📚 Additional Resources

- **[Full Documentation](README.md)**: Comprehensive feature guide
- **[API Setup Guide](API_SETUP.md)**: Detailed API configuration
- **[Troubleshooting](README.md#troubleshooting)**: Common issues and solutions
- **[Notebook Usage](NOTEBOOK_USAGE.md)**: Jupyter/Colab interface guide

## 🆘 Getting Help

If you encounter issues:

1. **Check system status** in option 4 (Settings)
2. **Enable debug mode** for detailed logs
3. **Review this guide** for common solutions
4. **Check the main README** for advanced troubleshooting
5. **Create an issue** on GitHub with detailed information

---

**Ready to optimize your team? Launch the application and press 'h' for in-app help anytime!**