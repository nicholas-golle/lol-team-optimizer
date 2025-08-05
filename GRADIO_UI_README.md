# 🎮 LoL Team Optimizer - Gradio Web UI

A modern, interactive web interface for the League of Legends Team Optimizer built with Gradio. This provides a user-friendly way to access all the advanced analytics and optimization features through a beautiful web interface.

## ✨ Features

### 🖥️ Modern Web Interface
- **Interactive UI**: Beautiful, responsive web interface
- **Real-time Updates**: Live data refresh and analysis
- **Mobile Friendly**: Works on any device with a web browser
- **Tabbed Navigation**: Organized interface with easy navigation
- **Dark/Light Themes**: Customizable appearance

### 📊 Advanced Analytics
- **Performance Charts**: Interactive radar charts and bar graphs
- **Statistical Analysis**: Confidence intervals and significance testing
- **Trend Analysis**: Time-series analysis of performance over time
- **Comparative Analysis**: Side-by-side player comparisons
- **Champion Performance**: Detailed champion-specific analytics

### 🎯 Smart Recommendations
- **AI-Powered Suggestions**: Machine learning-based champion recommendations
- **Role-Specific Analysis**: Tailored recommendations for each position
- **Meta Awareness**: Recommendations based on current patch and meta
- **Confidence Scoring**: Reliability indicators for each recommendation

### 👥 Team Management
- **Player Management**: Add and manage team players
- **Match Extraction**: Automated data collection from Riot API
- **Team Composition**: Analyze team synergy and optimization
- **Performance Tracking**: Monitor improvement over time

## 🚀 Quick Start

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/lol-team-optimizer.git
   cd lol-team-optimizer
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements_gradio.txt
   ```

3. **Set up your Riot API key**:
   ```bash
   export RIOT_API_KEY="your_api_key_here"
   ```

4. **Launch the interface**:
   ```bash
   python launch_gradio.py
   ```

### Using the Launcher Script

The launcher script provides additional options:

```bash
# Basic launch
python launch_gradio.py

# Launch with public sharing (creates shareable URL)
python launch_gradio.py --share

# Launch on custom port
python launch_gradio.py --port 8080

# Launch with custom host (for network access)
python launch_gradio.py --host 0.0.0.0

# Skip dependency installation check
python launch_gradio.py --no-install
```

### Google Colab

1. **Open the Colab notebook**:
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yourusername/lol-team-optimizer/blob/main/LoL_Team_Optimizer_Gradio_Colab.ipynb)

2. **Run the setup cells** to install dependencies

3. **Configure your API key** when prompted

4. **Launch the interface** - you'll get a public URL to access

## 📖 Usage Guide

### 1. 👥 Player Management

**Adding Players:**
1. Navigate to the "Player Management" tab
2. Fill in the player details:
   - **Player Name**: Display name for the player
   - **Summoner Name**: In-game summoner name
   - **Riot ID**: Full Riot ID (PlayerName#TAG)
   - **Region**: Player's server region
3. Click "Add Player"

**Managing Players:**
- View all current players in the interface
- Use "Refresh Player List" to update the display
- Players are automatically available in other tabs

### 2. 📥 Match Extraction

**Extracting Match Data:**
1. Go to the "Match Extraction" tab
2. Select a player from the dropdown
3. Choose the number of days of match history to extract (1-90)
4. Click "Extract Matches"
5. Wait for the extraction to complete

**Tips:**
- Start with 30 days for initial analysis
- Extract more data for better statistical accuracy
- Recent matches provide the most relevant insights

### 3. 📊 Analytics

**Viewing Performance Analytics:**
1. Navigate to the "Analytics" tab
2. Select a player from the dropdown
3. Choose the analysis period (7-180 days)
4. Click "Analyze Performance"

**Understanding the Results:**
- **Summary Report**: Overall performance metrics and top champions
- **Performance Chart**: Radar chart showing key performance areas
- **Champion Chart**: Bar chart of champion win rates

**Key Metrics:**
- **Win Rate**: Percentage of games won
- **KDA**: Kill/Death/Assist ratio
- **CS/Min**: Creep score per minute (farming efficiency)
- **Vision Score**: Map awareness and vision control
- **Damage/Min**: Combat effectiveness

### 4. 🎯 Champion Recommendations

**Getting Recommendations:**
1. Go to the "Champion Recommendations" tab
2. Select a player from the dropdown
3. Choose the role you want recommendations for
4. Click "Get Recommendations"

**Understanding Recommendations:**
- **Recommendation Score**: Overall recommendation strength (0-100%)
- **Confidence**: Reliability of the recommendation (0-100%)
- **Reasoning**: Why this champion is recommended

**Using Recommendations:**
- Higher scores indicate better matches for your playstyle
- Consider confidence levels when making decisions
- Try recommended champions in practice games first

### 5. 👥 Team Composition

**Analyzing Team Compositions:**
1. Navigate to the "Team Composition" tab
2. Select players for each position (minimum 2 players)
3. Click "Analyze Team"

**Results Include:**
- Individual player performance summaries
- Combined team win rate
- Synergy analysis (when available)
- Optimization recommendations

## 🎨 Interface Features

### Interactive Charts

**Performance Radar Chart:**
- Visual representation of key performance metrics
- Easy comparison across different areas
- Scaled to 0-100 for easy interpretation

**Champion Performance Chart:**
- Bar chart showing win rates for each champion
- Includes game count for statistical context
- Only shows champions with sufficient games (3+)

### Real-time Updates

- **Live Data Refresh**: Interface updates as you add data
- **Progress Indicators**: Visual feedback during long operations
- **Error Handling**: Clear error messages and recovery suggestions

### Responsive Design

- **Mobile Friendly**: Works on phones and tablets
- **Adaptive Layout**: Adjusts to different screen sizes
- **Touch Support**: Full touch interface support

## 🔧 Configuration

### Environment Variables

```bash
# Required
RIOT_API_KEY=your_riot_api_key_here

# Optional
LOL_OPTIMIZER_DEBUG=true          # Enable debug logging
LOL_OPTIMIZER_CACHE_SIZE=1000     # Cache size for analytics
LOL_OPTIMIZER_DATA_DIR=./data     # Data storage directory
```

### Customization Options

**Theme Customization:**
The interface uses Gradio's theming system. You can customize colors and styling by modifying the CSS in `gradio_ui.py`.

**Feature Toggles:**
You can enable/disable features by modifying the interface creation in the `create_interface()` method.

**Chart Customization:**
Modify the chart creation methods to change colors, scales, or chart types.

## 🐛 Troubleshooting

### Common Issues

**1. Interface won't start**
```bash
# Check dependencies
pip install -r requirements_gradio.txt

# Verify Python version (3.8+ required)
python --version

# Check for port conflicts
python launch_gradio.py --port 8080
```

**2. API key issues**
```bash
# Verify API key is set
echo $RIOT_API_KEY

# Test API key validity
curl -H "X-Riot-Token: $RIOT_API_KEY" \
  "https://na1.api.riotgames.com/lol/status/v4/platform-data"
```

**3. Match extraction fails**
- Verify player names and regions are correct
- Check API rate limits (wait a few minutes)
- Ensure players have recent match history
- Try extracting fewer days of data

**4. Analytics not working**
- Make sure match data has been extracted first
- Check that players have sufficient match history (10+ games)
- Verify the analysis period includes matches
- Try a longer analysis period

**5. Charts not displaying**
- Refresh the browser page
- Check browser console for JavaScript errors
- Try a different browser or incognito mode
- Ensure plotly is installed correctly

### Debug Mode

Enable debug mode for detailed logging:

```bash
export LOL_OPTIMIZER_DEBUG=true
python launch_gradio.py
```

### Performance Issues

**Slow Interface:**
- Reduce analysis periods
- Clear browser cache
- Close other browser tabs
- Check system resources

**Memory Issues:**
- Restart the interface
- Reduce cache size in configuration
- Extract data in smaller chunks

## 🔒 Security Considerations

### API Key Security

- **Never commit API keys** to version control
- **Use environment variables** for API key storage
- **Rotate API keys** regularly
- **Use production keys** only for production deployments

### Network Security

- **Local Access**: By default, the interface only accepts local connections
- **Public Sharing**: Use `--share` flag only when needed
- **Firewall**: Configure firewall rules for network deployments
- **HTTPS**: Use reverse proxy with SSL for production deployments

## 🚀 Deployment

### Local Development

```bash
# Development mode with auto-reload
python launch_gradio.py --share
```

### Production Deployment

**Using Docker:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements_gradio.txt

EXPOSE 7860

CMD ["python", "launch_gradio.py", "--host", "0.0.0.0"]
```

**Using systemd:**
```ini
[Unit]
Description=LoL Team Optimizer Gradio UI
After=network.target

[Service]
Type=simple
User=lol-optimizer
WorkingDirectory=/opt/lol-team-optimizer
Environment=RIOT_API_KEY=your_key_here
ExecStart=/usr/bin/python3 launch_gradio.py --host 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

### Cloud Deployment

**Heroku:**
1. Create `Procfile`: `web: python launch_gradio.py --host 0.0.0.0 --port $PORT`
2. Set environment variables in Heroku dashboard
3. Deploy using Git or GitHub integration

**Google Cloud Run:**
1. Build Docker image
2. Deploy to Cloud Run
3. Set environment variables
4. Configure custom domain (optional)

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements_gradio.txt
   pip install -r requirements-dev.txt  # If available
   ```
4. **Make your changes**
5. **Test thoroughly**
6. **Submit a pull request**

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for all functions and classes
- Include error handling and logging
- Write tests for new features

### Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=gradio_ui tests/

# Test the interface manually
python launch_gradio.py --no-install
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Gradio Team**: For the amazing web UI framework
- **Plotly**: For interactive charting capabilities
- **Riot Games**: For providing the League of Legends API
- **Community Contributors**: For feedback and improvements

## 📞 Support

- **Documentation**: Check this README and the main project docs
- **Issues**: Report bugs on the GitHub issue tracker
- **Discussions**: Join discussions on the GitHub repository
- **Discord**: Join our community Discord server (if available)

---

**Happy optimizing! 🎮🚀**