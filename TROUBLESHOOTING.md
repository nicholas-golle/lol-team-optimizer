# Troubleshooting Guide - Streamlined Interface

This guide helps you resolve common issues with the League of Legends Team Optimizer's streamlined interface.

## 🚨 Quick Diagnostics

### System Health Check
1. **Launch the application**: `python main.py`
2. **Check system status** displayed at startup
3. **Go to Settings** (option 4) → **System Diagnostics**
4. **Run connectivity tests** and review results

### Common Status Indicators
- ✅ **Green indicators**: System working properly
- ⚠️ **Yellow warnings**: Partial functionality, may need attention
- ❌ **Red errors**: Critical issues requiring immediate action

## 🔧 Installation and Setup Issues

### Python Not Found
**Symptoms**: `'python' is not recognized` or `command not found`

**Solutions**:
```bash
# Windows - try python3 or py
python3 main.py
py main.py

# macOS/Linux - use python3
python3 main.py

# Or reinstall Python with PATH option checked
```

### Dependencies Missing
**Symptoms**: `ModuleNotFoundError` or import errors

**Solutions**:
```bash
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Or install individually
pip install requests numpy scipy python-dotenv

# For virtual environment issues
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Permission Errors
**Symptoms**: `Permission denied` when writing files

**Solutions**:
- **Windows**: Run Command Prompt as Administrator
- **macOS/Linux**: Use `sudo` or fix directory permissions
- **Alternative**: Use virtual environment in user directory

## 🔑 API Key Issues

### "API: ⚠️ Offline" Status
**Symptoms**: System shows offline mode, limited functionality

**Diagnosis Steps**:
1. **Check .env file exists** with `RIOT_API_KEY=RGAPI-...`
2. **Verify key format** starts with `RGAPI-` and is complete
3. **Test connectivity** in Settings → System Diagnostics

**Solutions**:
```bash
# Create or update .env file
echo "RIOT_API_KEY=RGAPI-your-key-here" > .env

# Or set environment variable
export RIOT_API_KEY=RGAPI-your-key-here  # Linux/macOS
set RIOT_API_KEY=RGAPI-your-key-here     # Windows
```

### "401 Unauthorized" Errors
**Symptoms**: API calls fail with authentication errors

**Common Causes & Solutions**:
- **Expired development key**: Regenerate at [developer.riotgames.com](https://developer.riotgames.com/)
- **Invalid key format**: Ensure key includes `RGAPI-` prefix
- **Typos in key**: Copy-paste the complete key without spaces
- **Wrong region**: Verify you're using the correct regional endpoint

### "403 Forbidden" Errors
**Symptoms**: API access denied despite valid key

**Solutions**:
- **Check key permissions** in Riot Developer Portal
- **Verify account status** - ensure Riot account is in good standing
- **Regional restrictions** - some keys are region-locked

### "429 Rate Limited" Errors
**Symptoms**: "Too many requests" errors, temporary API blocks

**Solutions**:
- **Wait 2 minutes** for rate limit reset
- **Reduce concurrent operations** - add players one at a time
- **Check for multiple instances** running simultaneously
- **Consider personal API key** for higher limits

## 👥 Player Management Issues

### "Player Not Found" Errors
**Symptoms**: Cannot add players, invalid Riot ID messages

**Solutions**:
```bash
# Correct format examples
Faker#KR1          ✅ Correct
TSM Bjergsen#NA1    ✅ Correct  
Faker               ❌ Missing tag
Faker#              ❌ Incomplete tag
#KR1                ❌ Missing name
```

### "Insufficient Players" for Optimization
**Symptoms**: Cannot run optimization, not enough players

**Solutions**:
1. **Add more players**: Need minimum 5 for full optimization
2. **Check player data**: Ensure players were saved successfully
3. **Verify player status**: Use View Analysis to check data completeness

### Missing Player Data
**Symptoms**: Players show 📝 (basic data only) instead of 📊🏆⭐

**Solutions**:
1. **Refresh player data**: Settings → Data Management → Refresh All Players
2. **Check API connectivity**: Ensure API key is working
3. **Verify recent activity**: Players need recent matches for performance data
4. **Set custom preferences**: Add role preferences manually if needed

## 🎯 Optimization Issues

### Poor Optimization Results
**Symptoms**: Low scores, unexpected role assignments, poor team composition

**Diagnosis**:
1. **Check data quality**: View Analysis → Team Overview
2. **Review player preferences**: Ensure preferences reflect actual roles
3. **Verify performance data**: Check if players have recent match history

**Solutions**:
- **Update preferences**: Set custom role preferences for key players
- **Refresh data**: Get latest performance metrics from API
- **Add more players**: Larger pool provides better optimization options
- **Check role coverage**: Ensure you have players suitable for all roles

### "Optimization Failed" Errors
**Symptoms**: Optimization process fails with error messages

**Common Causes & Solutions**:
- **Data corruption**: Clear cache in Settings → Cache Management
- **API issues**: Check connectivity and try again
- **Insufficient data**: Ensure players have minimum required data
- **System resources**: Close other applications if memory is limited

### Slow Optimization Performance
**Symptoms**: Optimization takes very long or appears to hang

**Solutions**:
- **Reduce player count**: Optimize with fewer players initially
- **Clear cache**: Remove old cached data taking up memory
- **Check system resources**: Ensure adequate RAM and CPU available
- **Update data selectively**: Refresh only essential player data

## 📊 Analysis and Display Issues

### Missing Champion Recommendations
**Symptoms**: No champion suggestions in optimization results

**Solutions**:
1. **Check champion data**: Settings → System Diagnostics → Champion Data Status
2. **Refresh champion masteries**: Update player data to get latest mastery info
3. **Verify API access**: Champion data requires API connectivity

### Incomplete Performance Analysis
**Symptoms**: Limited performance metrics, missing trend data

**Solutions**:
- **Ensure recent matches**: Players need recent game history
- **Check match data access**: Some data requires specific API permissions
- **Update player data**: Refresh to get latest performance metrics

### Synergy Analysis Not Available
**Symptoms**: No team synergy data in analysis results

**Solutions**:
1. **Update synergy database**: Settings → Data Management → Update Synergy Data
2. **Check shared match history**: Players need games played together
3. **Verify API access**: Synergy analysis requires match history access

## 🔧 System Performance Issues

### High Memory Usage
**Symptoms**: System becomes slow, high RAM consumption

**Solutions**:
```bash
# Clear all caches
Settings → Cache Management → Clear All Caches

# Reduce cache size in .env
MAX_CACHE_SIZE_MB=25
CACHE_DURATION_HOURS=1

# Restart application
```

### Slow Startup
**Symptoms**: Application takes long time to initialize

**Solutions**:
- **Clear expired cache**: Remove old cached data
- **Check disk space**: Ensure adequate storage available
- **Reduce champion data**: Clear and reload champion database
- **Check antivirus**: Ensure application isn't being scanned repeatedly

### Network Connectivity Issues
**Symptoms**: API calls fail, timeout errors

**Solutions**:
- **Check internet connection**: Verify general connectivity
- **Test Riot API status**: Visit [developer.riotgames.com/api-status](https://developer.riotgames.com/api-status)
- **Configure firewall**: Allow Python/application through firewall
- **Try different network**: Test with mobile hotspot or different connection

## 🐛 Debug Mode and Logging

### Enable Debug Mode
Add to your `.env` file:
```
DEBUG=true
LOG_LEVEL=DEBUG
```

### Check Log Files
Logs are stored in `data/logs/`:
- `app.log`: General application logs
- `errors.log`: Detailed error information
- `debug.log`: Verbose debug information (debug mode only)

### Useful Debug Commands
```bash
# View recent errors
tail -n 50 data/logs/errors.log

# Monitor real-time logs
tail -f data/logs/app.log

# Check system status
python -c "from lol_team_optimizer.core_engine import CoreEngine; print(CoreEngine().system_status)"
```

## 🆘 Getting Additional Help

### Before Reporting Issues
1. **Enable debug mode** and reproduce the issue
2. **Check system diagnostics** in Settings
3. **Review relevant log files** for error details
4. **Try basic troubleshooting** steps from this guide

### Information to Include
When reporting issues, provide:
- **Operating system** and Python version
- **Complete error messages** from logs
- **Steps to reproduce** the issue
- **System status** from diagnostics
- **Configuration details** (without API key)

### Support Resources
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check README.md for detailed information
- **API Status**: Monitor Riot API service status
- **Community**: Connect with other users for tips and solutions

## 🔄 Recovery Procedures

### Complete Reset
If all else fails, perform a complete reset:

```bash
# Backup important data
cp -r data/ data_backup/

# Clear all data and cache
rm -rf data/ cache/

# Restart application (will recreate directories)
python main.py
```

### Selective Reset
For specific issues:

```bash
# Clear only cache
rm -rf cache/

# Clear only player data
rm -rf data/players.json

# Clear only logs
rm -rf data/logs/
```

### Configuration Reset
Reset to default configuration:

```bash
# Backup current config
cp .env .env.backup

# Create minimal config
echo "RIOT_API_KEY=your-key-here" > .env
```

---

**Still having issues? Enable debug mode, check the logs, and create a detailed issue report on GitHub with the information above.**