# Deployment Guide for Render

This guide explains how to deploy your Telegram Story Userbot to Render cloud platform while keeping your account safe from bans.

## Prerequisites

- A Telegram account with Premium subscription
- Telegram API credentials (API ID and API Hash from https://my.telegram.org/apps)
- A Render account (free tier available)
- A string session (see setup below)

## Step 1: Generate a String Session

For deployment, using a string session is recommended over a file session:

1. **Install dependencies locally:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Edit config.py temporarily:**
   - Set your `API_ID` and `API_HASH`
   - Set your `PHONE_NUMBER`

3. **Generate string session:**
   ```bash
   python generate_session.py
   ```

4. **Copy the output** - you'll need this for Render environment variables

## Step 2: Prepare for Render Deployment

### Option A: Using Render Dashboard (Recommended)

1. **Fork or create a new repository** with this code
2. **Push your code to GitHub/GitLab**

3. **Create a new Web Service on Render:**
   - Go to https://dashboard.render.com
   - Click "New +" → "Web Service"
   - Connect your repository
   - Configure build and start commands (these are in `render.yaml`)

4. **Set Environment Variables:**
   - `API_ID`: Your Telegram API ID (number)
   - `API_HASH`: Your Telegram API hash
   - `STRING_SESSION`: The string session you generated
   - `WATCH_GROUP`: Your group username or ID
   - `MIN_STORY_DELAY`: 300 (5 minutes between stories)
   - `MAX_STORIES_PER_HOUR`: 5
   - `MAX_STORIES_PER_DAY`: 30
   - `COOLDOWN_HOURS`: 1
   - `LOG_LEVEL`: INFO

5. **Click "Deploy Web Service"**

### Option B: Using render.yaml

1. **Add your string session to environment:**
   ```bash
   export STRING_SESSION="your_string_session_here"
   export API_ID="12345678"
   export API_HASH="your_api_hash"
   export WATCH_GROUP="your_group"
   ```

2. **Install Render CLI:**
   ```bash
   pip install render-cli
   ```

3. **Deploy:**
   ```bash
   render deploy
   ```

## Step 3: Monitor Your Bot

After deployment:

1. **View logs** in Render dashboard to see activity
2. **Send a DM** to your bot account to get whitelisted
3. **Post an image** in your watched group to test

## Account Safety Features

Your bot includes several protections to prevent account bans:

### Rate Limiting (Configurable)

- **MIN_STORY_DELAY**: Minimum time between stories (default: 5 minutes)
- **MAX_STORIES_PER_HOUR**: Maximum stories per hour (default: 5)
- **MAX_STORIES_PER_DAY**: Maximum stories per day (default: 30)
- **COOLDOWN_HOURS**: Cooldown after hitting daily limit (default: 1 hour)

**Recommended Settings for Safety:**
- Conservative: 600s delay, 3/hour, 15/day
- Standard: 300s delay, 5/hour, 30/day
- Aggressive (higher risk): 180s delay, 8/hour, 50/day

### Other Safety Measures

1. **Automatic cooldowns**: Bot stops posting when limits are reached
2. **Persistent state**: Rate limits survive restarts
3. **Whitelist-only stories**: Stories only visible to approved users
4. **Single message processing**: Processes one image at a time

## Best Practices to Avoid Bans

### 1. **Use a Dedicated Account**
- Don't use your primary personal account
- Create a separate account just for the bot
- Add a phone number you can afford to lose

### 2. **Start Slow and Ramp Up**
- First week: Use conservative settings (10 stories/day max)
- Monitor for any warnings from Telegram
- Gradually increase limits over time

### 3. **Avoid Spam Patterns**
- Don't post at regular intervals (mix it up)
- Take breaks - don't run 24/7 initially
- Respect group activity levels

### 4. **Monitor Logs Regularly**
- Check for "Rate limit" messages - they're protecting you
- Watch for any error messages from Telegram
- Be aware of any CAPTCHA requests

### 5. **Keep Group Activity Natural**
- The bot only mirrors what's posted in your group
- If your group posts 100 images/day, that's what the bot processes
- Consider the source group's posting frequency

## Troubleshooting

### "Cooldown active" in logs
- This is normal and protects your account
- Wait for the cooldown period to expire
- Adjust MAX_STORIES_PER_DAY if this happens too often

### Session disconnected
- Generate a new string session locally
- Update the STRING_SESSION environment variable
- Redeploy

### Bot not posting stories
- Check logs for rate limit messages
- Verify WATCH_GROUP is correct
- Ensure the bot account is in the group
- Check that the bot has Premium subscription

### SQLite database error on deployment
- This issue has been fixed - session files now automatically use the persistent disk
- The bot creates the `/opt/render/project/data` directory automatically
- All session data, state files, and logs are stored in persistent storage
- No manual intervention required - redeploy to apply the fix

### Render deployment failed
- Verify all environment variables are set
- Check requirements.txt has correct dependencies
- Review Render build logs for specific errors

## Updating the Bot

To update your bot after initial deployment:

1. Make changes to your code locally
2. Commit and push to your repository
3. Render will automatically detect changes and redeploy

## Cost

- **Render Free Tier**: 750 hours/month (enough for continuous operation)
- **Paid plans**: Start at $7/month if you need more resources

## Security Tips

1. **Never commit** your string session or API hash to git
2. **Always use environment variables** for sensitive data
3. **Keep your API credentials** secure - they're account-specific
4. **Rotate your string session** if you suspect compromise

## Support

- Check Render logs for deployment issues
- Review userbot.log for runtime issues
- Verify Telegram account has active Premium subscription
- Ensure the bot account is still active and not restricted

---

**Disclaimer**: This bot operates using Telegram's MTProto API. While rate limiting and other protections are implemented, use at your own risk and comply with Telegram's Terms of Service.
