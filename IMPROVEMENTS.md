# Bot Improvements & Fixes

This document describes the recent improvements made to the Telegram Story Userbot to address common issues and improve reliability.

## Issues Fixed

### 1. New Users Not Added to Old Stories
**Problem:** When a user messaged the bot (DM), they were added to the whitelist, but they could only see stories posted AFTER they were added, not the existing ones.

**Solution:** Enhanced the `update_all_stories_for_new_user()` method to automatically update existing stories' privacy settings when a new user is added.

**How it works:**
- When a user sends a DM (non-command message), they are auto-added to the whitelist
- The bot then attempts to update the last N existing stories (configurable via `MAX_STORIES_TO_UPDATE`)
- Each story's privacy settings are updated to include the new user
- This ensures new viewers can see recently posted stories, not just new ones

**Configuration:**
```python
MAX_STORIES_TO_UPDATE = 20  # Update last 20 stories for new users
```

**Notes:**
- Story updates have rate limits, so we add a small delay between updates
- If Telegram rejects the privacy update, the bot logs a warning but continues
- Only the most recent stories are updated to avoid hitting rate limits

---

### 2. Image+Text Posts Not Being Detected
**Problem:** When posting an image with text/caption in the watched group, the bot wasn't detecting the text and was using random captions instead.

**Solution:** Improved caption detection in `_handle_group_message()` to check multiple sources for text.

**How it works:**
The bot now checks for captions in this priority order:
1. `message.text` - For newer Telegram API versions
2. `message.message` - Legacy field for message content
3. `message.caption` - For forwarded photos or album captions

**Example scenarios now handled:**
- ✅ Image with text attached (caption)
- ✅ Image with message body text
- ✅ Forwarded image with original caption
- ✅ Album images with captions
- ✅ Plain image without text (falls back to rotating captions)

**Logging:**
The bot now logs which caption source it used:
```
Using custom caption from message: "Your text here"
```
or
```
Selected rotating caption: "Members eating big in here"
```

---

### 3. Bot Dies and Doesn't Restart
**Problem:** If the bot crashed due to network issues, API errors, or other exceptions, it would stop completely and not restart.

**Solution:** Added an auto-restart wrapper script (`start_bot.sh`) and improved error handling.

**Features:**

#### Auto-Restart Wrapper Script
- Automatically restarts the bot if it crashes
- Exits cleanly on intentional shutdown (Ctrl+C)
- Logs all restart attempts with timestamps
- 10-second cooldown between restarts

**Usage:**
```bash
# Direct execution
bash start_bot.sh

# Or via Procfile (Heroku/Render)
worker: bash start_bot.sh
```

#### Improved Error Handling
1. **Connection Retries:** The bot now retries connection up to 5 times with 5-second delays
2. **Exception Handling:** Unhandled exceptions in the main loop are caught, logged, and re-raised to trigger the wrapper script
3. **Graceful Shutdown:** Keyboard interrupts are handled cleanly without restart

**Exit Codes:**
- `0` - Clean shutdown (no restart)
- `130` - Keyboard interrupt (no restart)
- Other - Error (triggers restart after 10 seconds)

**Deployment:**
Both `Procfile` and `render.yaml` have been updated to use the wrapper:
```yaml
# render.yaml
startCommand: bash start_bot.sh

# Procfile
worker: bash start_bot.sh
```

---

## Additional Improvements

### Better Logging
- Connection attempts are logged with retry counts
- Caption source is logged when posting from groups
- Story update successes/failures are tracked
- All errors include full stack traces (`exc_info=True`)

### State Management
- `_post_story()` now returns the result object (for future enhancements)
- Story IDs are tracked for potential future features

---

## Testing Checklist

After deploying these improvements, verify:

- [ ] **New user story access:**
  1. Have a new user DM the bot (send any message)
  2. Check logs for "Auto-added user" message
  3. Verify the user can see the last ~20 stories (configurable)

- [ ] **Image+text detection:**
  1. Post an image with text in the watched group
  2. Check logs for "Using custom caption from message: ..."
  3. Verify the story shows your text instead of random caption

- [ ] **Auto-restart:**
  1. Stop the bot (or simulate a crash)
  2. Wait 10 seconds
  3. Verify bot automatically restarts and reconnects
  4. Check logs for restart attempts

- [ ] **Clean shutdown:**
  1. Press Ctrl+C to stop the bot
  2. Verify it exits completely without restarting

---

## Troubleshooting

### "Could not update story privacy" Warning
This is normal and expected for some scenarios:
- Stories older than 24 hours cannot have privacy changed
- Rate limits may prevent some updates
- Some story types don't support privacy updates

**Action:** No action needed - this is a warning, not an error. The user can still see all new stories going forward.

### Bot Keeps Restarting
If the bot restarts repeatedly, check logs for the root cause:
- Network connectivity issues
- Invalid API credentials
- Telegram blocking/restricting the account
- Rate limit violations

**Action:**
1. Check logs in `userbot.log` or Render dashboard
2. Review ACCOUNT_SAFETY.md for rate limit settings
3. Verify environment variables are correct

### Image Text Still Not Detected
If the bot still uses random captions for image+text posts:

**Check:**
1. Is the text actually attached to the image (not a separate message)?
2. Is the message from the correct WATCH_GROUP?
3. Check logs to see what's being detected

**Debug:** Set `LOG_LEVEL=DEBUG` in config to see detailed message parsing info.

---

## Configuration Review

After these improvements, review these settings in `config.py`:

```python
# How many old stories to update for new users
MAX_STORIES_TO_UPDATE = 20  # Higher = more stories visible, but slower

# Rate limits to prevent bans
MIN_STORY_DELAY = 300  # Seconds between stories
MAX_STORIES_PER_HOUR = 5
MAX_STORIES_PER_DAY = 30
COOLDOWN_HOURS = 1  # Rest period after daily limit

# Deployment settings (use string session for cloud)
STRING_SESSION = ""  # Generate with: python generate_session.py
```

---

## Monitoring

### Health Check Endpoint
The bot now includes a health check endpoint for monitoring:
- `GET /` or `GET /health` - Returns "OK" if bot is connected, 503 otherwise

**Useful for:**
- Render health checks
- Uptime monitoring services
- Simple status checks

### Key Logs to Monitor
```
✅ "Bot is running and listening for messages..." - Bot started successfully
✅ "Auto-added user..." - New user added to whitelist
✅ "Updated X/Y stories for new user..." - Old stories updated
✅ "Using custom caption from message..." - Text detected from image
⚠️ "Could not update story privacy..." - Story update failed (expected sometimes)
❌ "Bot disconnected unexpectedly" - Crash detected (auto-restart will trigger)
```

---

## Summary

These improvements address the three main issues:
1. ✅ **Whitelist persistence** - New users see old stories
2. ✅ **Caption detection** - Image+text posts work correctly
3. ✅ **Bot reliability** - Auto-restart on crashes

The bot is now more robust and handles edge cases better while maintaining account safety through rate limiting.
