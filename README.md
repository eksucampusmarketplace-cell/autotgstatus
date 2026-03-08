# Telegram Premium Story Userbot

A Telegram userbot that automatically posts images from a specific group as Telegram Stories with rotating captions and privacy controls.

## ⚠️ Account Safety Notice

**This bot uses Telegram's MTProto API directly with your account. To minimize ban risk, the bot includes:**

- ✅ **Rate limiting** with configurable delays and daily limits
- ✅ **Automatic cooldowns** when limits are reached
- ✅ **Whitelist-only story viewing** for privacy
- ✅ **Graceful degradation** (no forced retries)

**Read [ACCOUNT_SAFETY.md](ACCOUNT_SAFETY.md) before deploying!**

## Features

- **Automatic Story Posting**: Listens for images in a specified Telegram group and posts them as stories
- **Image Composition**: Resizes, crops, and adds gradient overlays with captions using Pillow
- **Caption Rotation**: Randomly rotates through 200 captions with minimum gap enforcement
- **Privacy Controls**: Only whitelisted users can view stories
- **Auto-Whitelist**: Automatically adds users who send DMs to the whitelist
- **Persistent State**: Caption history and whitelist survive restarts
- **Rate Limiting**: Configurable limits to protect your account from spam detection
- **Cloud Deployment**: Ready for deployment to Render and other cloud platforms

## Prerequisites

- Python 3.8 or higher
- Telegram Premium subscription (required for posting stories via user account)
- Telegram API credentials (API ID and API Hash)

## Quick Start (Local)

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note down your **API ID** and **API Hash**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Option A: Use environment variables (recommended)
```bash
export API_ID=12345678
export API_HASH="your_api_hash_here"
export PHONE_NUMBER="+1234567890"
export WATCH_GROUP="your_group_username"
```

Option B: Edit `config.py` directly
```python
API_ID = 12345678
API_HASH = "your_api_hash_here"
PHONE_NUMBER = "+1234567890"
WATCH_GROUP = "your_group_username_or_id"
```

### 4. Run the Bot

```bash
python bot.py
```

On first run, you'll need to:
1. Enter the verification code sent to your Telegram
2. Enter your 2FA password if enabled

## Cloud Deployment

### Deploy to Render

📖 **See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions**

Quick steps:
1. Generate a string session: `python generate_session.py`
2. Push code to GitHub
3. Create a Web Service on Render
4. Set environment variables (API_ID, API_HASH, STRING_SESSION, WATCH_GROUP, etc.)
5. Deploy!

### Other Platforms

The bot can be deployed to any platform that supports Python:
- Heroku (using Procfile)
- Railway
- DigitalOcean App Platform
- AWS Lambda (with modifications)
- Your own VPS

## Setup Instructions

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note down your **API ID** and **API Hash**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit `config.py` and set your credentials:

```python
# Telegram API Credentials
API_ID = 12345678  # Your API ID (integer)
API_HASH = "your_api_hash_here"  # Your API hash
PHONE_NUMBER = "+1234567890"  # Your phone number with country code

# Group to monitor
WATCH_GROUP = "your_group_username"  # or use numeric chat ID like -1001234567890
```

### 4. Run the Bot

```bash
python bot.py
```

On first run, you'll need to:
1. Enter the verification code sent to your Telegram
2. Enter your 2FA password if enabled

## Configuration Options

### Rate Limiting (Account Safety)

These settings control how many stories can be posted and are **critical for account safety**:

| Setting | Description | Default |
|---------|-------------|---------|
| `MIN_STORY_DELAY` | Minimum seconds between stories | 300 (5 min) |
| `MAX_STORIES_PER_HOUR` | Maximum stories per hour | 5 |
| `MAX_STORIES_PER_DAY` | Maximum stories per day | 30 |
| `COOLDOWN_HOURS` | Cooldown after daily limit | 1 |

**See [ACCOUNT_SAFETY.md](ACCOUNT_SAFETY.md) for recommended configurations**

### `config.py` Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `API_ID` | Your Telegram API ID | Required |
| `API_HASH` | Your Telegram API hash | Required |
| `PHONE_NUMBER` | Your phone number with country code | Required |
| `WATCH_GROUP` | Group username or chat ID to monitor | Required |
| `MIN_CAPTION_GAP` | Min captions before repeat | 3 |
| `CUSTOM_VIEWER_LIST` | Initial whitelist (usernames/user IDs) | [] |
| `CAPTIONS` | List of 200 captions for rotation | See config.py |
| `STRING_SESSION` | String session for authentication (optional) | "" |

### Viewer Whitelist

The whitelist controls who can view your stories:

1. **Initial whitelist**: Add users to `CUSTOM_VIEWER_LIST` in `config.py`
   - Format: `["username1", "username2", 123456789]`

2. **Auto-whitelist**: Any user who sends you a DM is automatically added

The whitelist is stored in `state.json` and persists across restarts.

## File Structure

```
.
├── bot.py              # Main entry point, event handlers, story poster
├── composer.py         # Image processing and caption overlay
├── config.py           # All user-configurable settings
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── state.json          # Persistent state (auto-created)
├── userbot.log         # Log file (auto-created)
└── userbot_session.session  # Telegram session (auto-created)
```

## State File (`state.json`)

This file stores:
- `caption_history`: Recently used caption indices
- `viewer_whitelist`: List of whitelisted user IDs
- `last_caption_index`: Last caption used

**Note**: Do not edit this file manually while the bot is running.

## Image Processing

The bot processes images as follows:
1. Downloads the image from the group message
2. Resizes and center-crops to 1080×1920 (9:16 story aspect ratio)
3. Adds a dark gradient bar at the bottom (35% height)
4. Burns the caption text centered in the gradient area
5. Applies a drop shadow for readability
6. Saves as high-quality JPEG (95% quality)

## Logging

All actions are logged to:
- Console (stdout)
- `userbot.log` file

Log levels can be adjusted in `config.py`:
- `DEBUG`: Detailed information
- `INFO`: General operation (default)
- `WARNING`: Warnings only
- `ERROR`: Errors only

## Account Safety

⚠️ **IMPORTANT**: This bot operates using your real Telegram account. Read [ACCOUNT_SAFETY.md](ACCOUNT_SAFETY.md) for comprehensive safety guidelines.

### Key Safety Features

- ✅ **Rate limiting** with automatic cooldowns
- ✅ **Persistent state** survives restarts
- ✅ **Whitelist-only viewing** for privacy
- ✅ **Graceful handling** of rate limits
- ✅ **Environment variable support** for secure deployments

### Tips to Avoid Bans

1. **Use a dedicated account**: Don't use your primary personal account
2. **Start conservative**: Begin with low rate limits and increase gradually
3. **Monitor logs**: Check for rate limit messages regularly
4. **Respect limits**: Don't modify or bypass rate limiting
5. **Age the account**: Let the account exist for 2+ weeks before use
6. **Legitimate usage**: Use the bot for legitimate purposes only

### Important Notes

- **Telegram Premium required**: Stories can only be posted by Premium users
- **MTProto only**: Uses Telethon (MTProto), not the Bot API
- **Session persistence**: Your session is saved to `userbot_session.session` or as STRING_SESSION - keep this secure
- **Privacy**: The bot only listens to the specified group and private messages
- **Cloud deployment**: Use STRING_SESSION for persistent deployments

## Troubleshooting

### "Story not posted due to rate limit"

This is **normal and protective**. The bot is preventing spam-like behavior. Wait for the cooldown period or adjust rate limits in config.py.

### "Could not resolve user ID"

The bot needs to have the user in its contacts/dialogs to resolve them. Have the user send you a DM first.

### "Failed to post story"

- Verify you have Telegram Premium
- Check your API credentials
- Ensure the session is valid (delete `userbot_session.session` and re-authenerate if needed)
- Check for rate limiting messages in logs

### Images not being processed

- Verify `WATCH_GROUP` is set correctly (check the exact username or chat ID)
- Ensure the bot account has access to the group
- Check logs for error messages
- Verify rate limits aren't being hit

### Font issues

The bot tries multiple font paths. If none work, it falls back to a default font. To use a specific font, install it:
```bash
# Ubuntu/Debian
sudo apt-get install fonts-dejavu

# Or add your font to the system fonts directory
```

### Deployment Issues

- **Render builds failing**: Check environment variables are set correctly
- **Session lost on redeploy**: Use STRING_SESSION instead of session file
- **Rate limits not persisting**: Ensure persistent disk is configured on Render

## Documentation

- 📖 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- 🛡️ [ACCOUNT_SAFETY.md](ACCOUNT_SAFETY.md) - Comprehensive safety guidelines
- ⚙️ [.env.example](.env.example) - Environment variable template

## License

This project is provided as-is for educational purposes. Use at your own risk and in compliance with Telegram's Terms of Service.

## Support

For issues or questions:
1. Check the logs in `userbot.log` or Render dashboard
2. Read [ACCOUNT_SAFETY.md](ACCOUNT_SAFETY.md) for rate limiting issues
3. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for deployment issues
4. Verify your configuration and dependencies
