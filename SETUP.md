# Setup Guide - League of Legends Team Optimizer

This guide provides detailed setup instructions for different operating systems and use cases.

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 512 MB available memory
- **Storage**: 100 MB free disk space
- **Network**: Internet connection (for API features)

### Recommended Requirements
- **Python**: 3.9 or higher
- **RAM**: 1 GB available memory
- **Storage**: 500 MB free disk space (for caching)
- **Network**: Stable broadband connection

## Installation Methods

### Method 1: Standard Installation

1. **Download Python**:
   - Visit [python.org](https://www.python.org/downloads/)
   - Download Python 3.8+ for your operating system
   - During installation, check "Add Python to PATH"

2. **Clone or Download the Project**:
   ```bash
   # Using Git
   git clone <repository-url>
   cd lol-team-optimizer
   
   # Or download and extract the ZIP file
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Installation**:
   ```bash
   python main.py
   ```

### Method 2: Virtual Environment (Recommended)

1. **Create Virtual Environment**:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python main.py
   ```

### Method 3: Using Conda

1. **Create Conda Environment**:
   ```bash
   conda create -n lol-optimizer python=3.9
   conda activate lol-optimizer
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   python main.py
   ```

## Platform-Specific Setup

### Windows Setup

1. **Install Python from Microsoft Store** (easiest):
   - Open Microsoft Store
   - Search for "Python 3.9" or "Python 3.10"
   - Install the official Python package

2. **Alternative: Download from python.org**:
   - Download the Windows installer
   - Run installer as administrator
   - Check "Add Python to PATH"
   - Check "Install pip"

3. **Open Command Prompt or PowerShell**:
   ```cmd
   # Navigate to project directory
   cd C:\path\to\lol-team-optimizer
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run application
   python main.py
   ```

### macOS Setup

1. **Install Python using Homebrew** (recommended):
   ```bash
   # Install Homebrew if not already installed
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Python
   brew install python@3.9
   ```

2. **Alternative: Download from python.org**:
   - Download the macOS installer
   - Run the installer package

3. **Install and run**:
   ```bash
   # Navigate to project directory
   cd /path/to/lol-team-optimizer
   
   # Install dependencies
   pip3 install -r requirements.txt
   
   # Run application
   python3 main.py
   ```

### Linux Setup (Ubuntu/Debian)

1. **Install Python and pip**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **Install and run**:
   ```bash
   # Navigate to project directory
   cd /path/to/lol-team-optimizer
   
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run application
   python main.py
   ```

### Linux Setup (CentOS/RHEL/Fedora)

1. **Install Python and pip**:
   ```bash
   # CentOS/RHEL
   sudo yum install python3 python3-pip
   
   # Fedora
   sudo dnf install python3 python3-pip
   ```

2. **Follow the same steps as Ubuntu/Debian above**

## Riot API Key Setup

### Getting Your API Key

1. **Visit Riot Developer Portal**:
   - Go to [developer.riotgames.com](https://developer.riotgames.com/)
   - Sign in with your Riot Games account

2. **Create Application**:
   - Click "Create App" or use the development key
   - Fill in application details (for personal use)
   - Copy your API key

### Setting Up the API Key

#### Method 1: Environment Variable

**Windows (Command Prompt)**:
```cmd
set RIOT_API_KEY=RGAPI-your-key-here
python main.py
```

**Windows (PowerShell)**:
```powershell
$env:RIOT_API_KEY="RGAPI-your-key-here"
python main.py
```

**macOS/Linux**:
```bash
export RIOT_API_KEY=RGAPI-your-key-here
python main.py
```

#### Method 2: .env File (Recommended)

1. **Create .env file** in the project root:
   ```
   RIOT_API_KEY=RGAPI-your-key-here
   ```

2. **Run the application**:
   ```bash
   python main.py
   ```

#### Method 3: Permanent Environment Variable

**Windows**:
1. Open System Properties → Advanced → Environment Variables
2. Add new user variable: `RIOT_API_KEY` = `RGAPI-your-key-here`
3. Restart command prompt

**macOS/Linux**:
1. Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):
   ```bash
   export RIOT_API_KEY=RGAPI-your-key-here
   ```
2. Restart terminal or run `source ~/.bashrc`

## Configuration Examples

### Basic Configuration (.env file)

```env
# Riot API Configuration
RIOT_API_KEY=RGAPI-your-key-here
RIOT_API_BASE_URL=https://americas.api.riotgames.com
RIOT_API_RATE_LIMIT=120

# Performance Weights (must sum to 1.0)
INDIVIDUAL_WEIGHT=0.6
PREFERENCE_WEIGHT=0.3
SYNERGY_WEIGHT=0.1

# Cache Settings
CACHE_DURATION_HOURS=1
PLAYER_DATA_CACHE_HOURS=24
MAX_CACHE_SIZE_MB=50

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
MAX_MATCHES_TO_ANALYZE=20
```

### Advanced Configuration

```env
# Extended API Configuration
RIOT_API_KEY=RGAPI-your-key-here
RIOT_API_BASE_URL=https://americas.api.riotgames.com
RIOT_API_RATE_LIMIT=120
REQUEST_TIMEOUT_SECONDS=30
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0

# Custom Performance Weights
INDIVIDUAL_WEIGHT=0.5
PREFERENCE_WEIGHT=0.4
SYNERGY_WEIGHT=0.1

# Aggressive Caching
CACHE_DURATION_HOURS=6
PLAYER_DATA_CACHE_HOURS=48
MAX_CACHE_SIZE_MB=100

# Data Storage
DATA_DIRECTORY=data
CACHE_DIRECTORY=cache

# Debug Configuration
LOG_LEVEL=DEBUG
DEBUG=true
MAX_MATCHES_TO_ANALYZE=50
```

### Offline Mode Configuration

```env
# No API key - runs in offline mode
# RIOT_API_KEY=

# Rely more on preferences
INDIVIDUAL_WEIGHT=0.3
PREFERENCE_WEIGHT=0.7
SYNERGY_WEIGHT=0.0

# Longer cache retention
CACHE_DURATION_HOURS=168  # 1 week
PLAYER_DATA_CACHE_HOURS=168
MAX_CACHE_SIZE_MB=25

# Basic logging
LOG_LEVEL=INFO
DEBUG=false
```

## Verification Steps

### 1. Test Python Installation
```bash
python --version
# Should show Python 3.8 or higher
```

### 2. Test Dependencies
```bash
python -c "import requests, numpy, scipy; print('All dependencies installed')"
```

### 3. Test Application Startup
```bash
python main.py
# Should show the main menu without errors
```

### 4. Test API Connection (if configured)
- Run the application
- Go to System Maintenance → Test API Connectivity
- Should show successful connection

## Troubleshooting Setup Issues

### Python Not Found
- **Windows**: Reinstall Python with "Add to PATH" checked
- **macOS**: Use `python3` instead of `python`
- **Linux**: Install python3 package

### Permission Errors
- **Windows**: Run Command Prompt as Administrator
- **macOS/Linux**: Use `sudo` for system-wide installation or use virtual environment

### Module Not Found Errors
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or install individually
pip install requests numpy scipy python-dotenv
```

### API Key Issues
- Verify the key starts with "RGAPI-"
- Check the key hasn't expired
- Ensure no extra spaces in the key
- Test with a simple API call

### Network/Firewall Issues
- Check internet connection
- Verify firewall allows Python/pip
- Try using a VPN if corporate firewall blocks access
- Use `--trusted-host` flag with pip if needed:
  ```bash
  pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
  ```

## Performance Optimization

### For Better Performance
1. **Use SSD storage** for faster file I/O
2. **Increase cache size** if you have available RAM
3. **Use virtual environment** to avoid conflicts
4. **Enable debug mode** only when troubleshooting

### For Limited Resources
1. **Reduce cache size** in configuration
2. **Lower max matches to analyze**
3. **Use offline mode** to reduce API calls
4. **Clear cache regularly**

## Security Considerations

### API Key Security
- Never commit API keys to version control
- Use environment variables or .env files
- Regenerate keys if compromised
- Use development keys for testing

### Data Privacy
- All data is stored locally
- No data is sent to external servers (except Riot API)
- You can delete all data by removing the data directory

## Getting Help

If you encounter issues during setup:

1. **Check the error message** carefully
2. **Review this setup guide** for your platform
3. **Enable debug mode** for detailed logs
4. **Check the main README** for troubleshooting
5. **Search existing issues** on GitHub
6. **Create a new issue** with:
   - Your operating system
   - Python version
   - Complete error message
   - Steps you've tried

## Next Steps

After successful setup:

1. **Add your first players** using the application
2. **Set role preferences** for each player
3. **Run your first optimization**
4. **Explore advanced features** like performance analysis
5. **Configure the system** to match your preferences

Enjoy optimizing your League of Legends teams!