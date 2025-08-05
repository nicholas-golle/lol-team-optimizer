# Riot Games API Key Setup Guide - Unified Configuration

This guide provides detailed instructions for obtaining and configuring your Riot Games API key for the streamlined League of Legends Team Optimizer interface.

## Why Do You Need an API Key?

The Riot Games API key enables the application to:

- **Validate player summoner names** and Riot IDs
- **Fetch real-time performance data** from recent matches
- **Analyze individual player statistics** across different roles
- **Calculate team synergy** based on historical performance
- **Provide accurate optimization** based on current game data

**Without an API key**, the application runs in "offline mode" and relies only on:
- Cached data from previous sessions
- User-provided role preferences
- Basic optimization algorithms

## Getting Your API Key

### Step 1: Create a Riot Games Account

If you don't already have one:

1. Visit [Riot Games](https://www.riotgames.com/)
2. Click "Sign Up" and create an account
3. Verify your email address
4. Complete account setup

### Step 2: Access the Developer Portal

1. Go to [Riot Developer Portal](https://developer.riotgames.com/)
2. Sign in with your Riot Games account
3. Accept the Terms of Service if prompted

### Step 3: Get Your Development API Key

For personal use and testing:

1. On the developer portal homepage, you'll see a **"Development API Key"** section
2. Your development key is displayed immediately - it looks like:
   ```
   RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
3. Click the **"Regenerate"** button if you need a new key
4. Copy the entire key (including the "RGAPI-" prefix)

**Important Notes about Development Keys:**
- Valid for 24 hours only
- Rate limited to 100 requests every 2 minutes
- Intended for development and testing
- Must be regenerated daily

### Step 4: Create a Personal API Key (Optional)

For extended use:

1. Click **"Create App"** in the developer portal
2. Fill out the application form:
   - **App Name**: "League Team Optimizer" (or your preferred name)
   - **Description**: "Personal tool for optimizing League of Legends team compositions"
   - **App URL**: Leave blank or use your GitHub repository
   - **Callback URLs**: Leave blank
3. Select **"Personal"** as the app type
4. Submit the application

**Personal API Key Benefits:**
- Valid for longer periods
- Higher rate limits
- More stable for regular use

## Configuring Your API Key

### Method 1: Environment Variable (Recommended)

#### Windows (Command Prompt)
```cmd
# Set for current session
set RIOT_API_KEY=RGAPI-your-key-here

# Set permanently (requires admin)
setx RIOT_API_KEY "RGAPI-your-key-here"
```

#### Windows (PowerShell)
```powershell
# Set for current session
$env:RIOT_API_KEY="RGAPI-your-key-here"

# Set permanently
[Environment]::SetEnvironmentVariable("RIOT_API_KEY", "RGAPI-your-key-here", "User")
```

#### macOS/Linux (Bash/Zsh)
```bash
# Set for current session
export RIOT_API_KEY=RGAPI-your-key-here

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export RIOT_API_KEY=RGAPI-your-key-here' >> ~/.bashrc
source ~/.bashrc
```

### Method 2: .env File (Easy and Secure)

1. **Create a .env file** in your project root directory
2. **Add your API key**:
   ```
   RIOT_API_KEY=RGAPI-your-key-here
   ```
3. **Save the file**
4. **Never commit this file to version control**

### Method 3: Configuration File

You can also set the API key in your application configuration by modifying the `.env` file or environment variables as shown in the main README.

## Testing Your API Key

### Using the Streamlined Application

1. **Start the application**:
   ```bash
   python main.py
   ```

2. **Check the system status display**:
   - ✅ If API is working: Shows "API: ✅ Available" in system status
   - ❌ If API has issues: Shows "API: ⚠️ Offline" with offline mode warning

3. **Test API connectivity**:
   - Go to **Settings** (option 4) → **System Diagnostics** → **Test API Connectivity**
   - Should show successful connection, rate limits, and regional endpoint status

### Manual Testing

You can test your API key manually using curl or a web browser:

```bash
# Replace YOUR_API_KEY with your actual key
curl -H "X-Riot-Token: YOUR_API_KEY" \
  "https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/YourSummonerName/NA1"
```

**Expected Response:**
- ✅ **Success (200)**: JSON data with account information
- ❌ **Unauthorized (401)**: Invalid or expired API key
- ❌ **Forbidden (403)**: API key doesn't have required permissions
- ❌ **Rate Limited (429)**: Too many requests

## Regional Configuration

The API base URL depends on your region:

### Americas
```
RIOT_API_BASE_URL=https://americas.api.riotgames.com
```
**Covers**: North America, Brazil, Latin America

### Europe
```
RIOT_API_BASE_URL=https://europe.api.riotgames.com
```
**Covers**: EUW, EUNE, Turkey, Russia

### Asia
```
RIOT_API_BASE_URL=https://asia.api.riotgames.com
```
**Covers**: Korea, Japan, Oceania, Southeast Asia

## Rate Limits and Best Practices

### Understanding Rate Limits

**Development API Key:**
- 100 requests every 2 minutes
- Shared across all your applications

**Personal API Key:**
- Higher limits (varies by approval)
- Dedicated to your application

### Best Practices

1. **Cache Responses**: The application automatically caches API responses
2. **Batch Requests**: Minimize API calls by batching operations
3. **Handle Rate Limits**: The application includes automatic retry logic
4. **Monitor Usage**: Check rate limit headers in responses

### Rate Limit Configuration

You can adjust rate limiting in your configuration:

```env
# Requests per 2 minutes (adjust based on your key type)
RIOT_API_RATE_LIMIT=100

# Request timeout
REQUEST_TIMEOUT_SECONDS=30

# Retry configuration
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2.0
```

## Troubleshooting

### Common Issues

#### "API key not found" or "Running in offline mode"
**Causes:**
- API key not set in environment
- Typo in environment variable name
- API key not properly formatted

**Solutions:**
- Verify `RIOT_API_KEY` environment variable is set
- Check for typos (should start with "RGAPI-")
- Restart your terminal/command prompt after setting

#### "401 Unauthorized" errors
**Causes:**
- Invalid API key
- Expired development key (24-hour limit)
- API key doesn't match the region

**Solutions:**
- Regenerate your development key
- Verify the key is copied correctly
- Check that you're using the right regional endpoint

#### "403 Forbidden" errors
**Causes:**
- API key doesn't have required permissions
- Requesting data for wrong region
- Account restrictions

**Solutions:**
- Ensure your API key has the right permissions
- Verify you're querying the correct region
- Check if your Riot account has any restrictions

#### "429 Rate Limited" errors
**Causes:**
- Exceeded rate limits
- Too many concurrent requests
- Shared development key usage

**Solutions:**
- Wait for rate limit reset (2 minutes)
- Reduce concurrent operations
- Consider getting a personal API key

#### Network/Connection errors
**Causes:**
- Internet connectivity issues
- Firewall blocking requests
- Riot API downtime

**Solutions:**
- Check internet connection
- Verify firewall settings
- Check [Riot API Status](https://developer.riotgames.com/api-status)

### Debug Mode

Enable debug mode for detailed API logging:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

This will show:
- All API requests and responses
- Rate limit status
- Detailed error information
- Performance metrics

### API Status and Downtime

Check official status:
- [Riot API Status Page](https://developer.riotgames.com/api-status)
- [Riot Service Status](https://status.riotgames.com/)

## Security Best Practices

### Protecting Your API Key

1. **Never commit API keys to version control**
   ```bash
   # Add to .gitignore
   .env
   *.key
   ```

2. **Use environment variables or .env files**
3. **Regenerate keys if compromised**
4. **Don't share keys in screenshots or logs**
5. **Use different keys for different projects**

### Key Rotation

**Development Keys:**
- Automatically expire after 24 hours
- Regenerate daily for active development

**Personal Keys:**
- Rotate periodically for security
- Monitor usage for suspicious activity

## Advanced Configuration

### Multiple Regions

If you work with players from multiple regions:

```env
# Primary region
RIOT_API_BASE_URL=https://americas.api.riotgames.com
DEFAULT_REGION=na1

# You can manually specify regions when adding players
```

### Custom Rate Limiting

For personal API keys with higher limits:

```env
# Adjust based on your key's limits
RIOT_API_RATE_LIMIT=500
REQUEST_TIMEOUT_SECONDS=60
```

### Caching Strategy

Optimize for your usage pattern:

```env
# Aggressive caching (less API calls)
CACHE_DURATION_HOURS=6
PLAYER_DATA_CACHE_HOURS=48

# Fresh data (more API calls)
CACHE_DURATION_HOURS=0.5
PLAYER_DATA_CACHE_HOURS=12
```

## Getting Help

If you're still having issues:

1. **Check the main README** for general troubleshooting
2. **Enable debug mode** for detailed logs
3. **Test your API key manually** using curl
4. **Check Riot API status** for service issues
5. **Review rate limits** and usage patterns
6. **Create an issue** on GitHub with:
   - Your configuration (without the actual API key)
   - Error messages
   - Debug logs (with sensitive data removed)

## Useful Resources

- [Riot Developer Portal](https://developer.riotgames.com/)
- [API Documentation](https://developer.riotgames.com/apis)
- [Rate Limiting Guide](https://developer.riotgames.com/docs/portal#web-apis_rate-limiting)
- [Regional Endpoints](https://developer.riotgames.com/docs/lol#routing-values_platform-routing-values)
- [API Status Page](https://developer.riotgames.com/api-status)

Remember: The API key enables powerful features, but the application works in offline mode too. Start with a development key for testing, then consider a personal key for regular use.