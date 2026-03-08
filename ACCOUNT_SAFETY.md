# Account Safety Guide for Telegram Userbot

This guide explains how to use your Telegram userbot safely and minimize the risk of account bans.

## Understanding Telegram's Anti-Spam System

Telegram uses sophisticated algorithms to detect spam and abusive behavior. Using MTProto (the official API) at high rates or in spam-like patterns can trigger these protections.

### Risk Factors

1. **High rate of operations**: Too many API calls in a short time
2. **Regular patterns**: Posting at consistent intervals
3. **Mass content distribution**: Broadcasting to many users
4. **Automated behavior**: Obvious non-human activity patterns
5. **Reports from users**: Community flagging content

## Safety Features Built Into This Bot

### 1. Rate Limiting

The bot enforces strict rate limits:

```python
MIN_STORY_DELAY = 300      # 5 minutes between stories
MAX_STORIES_PER_HOUR = 5   # Maximum 5 stories per hour
MAX_STORIES_PER_DAY = 30    # Maximum 30 stories per day
COOLDOWN_HOURS = 1          # 1 hour cooldown after daily limit
```

**How it works:**
- Stories are automatically skipped if limits are exceeded
- Cooldown periods prevent continuous operation
- All limits persist across restarts

### 2. Privacy Controls

Stories are only visible to whitelisted users:
- Reduces distribution scale
- Lower risk of being reported
- More private, less spam-like

### 3. Graceful Degradation

The bot won't crash or retry when rate limited:
- Logs the reason for skipping
- Waits for cooldown to expire
- Continues monitoring without forced actions

## Recommended Safety Practices

### 1. Account Preparation

**Use a Dedicated Account**
```
✓ DO: Create a separate account for the bot
✓ DO: Use a phone number you can afford to lose
✓ DO: Keep Premium subscription active
✗ DON'T: Use your primary personal account
✗ DON'T: Use a phone number tied to important services
```

**Age the Account**
```
✓ DO: Let the account exist for 2+ weeks before bot use
✓ DO: Add some normal activity (join groups, send messages)
✓ DO: Complete the profile (bio, avatar)
✗ DON'T: Use a brand new account immediately
```

### 2. Warm-Up Strategy

**Week 1 - Testing Phase**
```python
MIN_STORY_DELAY = 600        # 10 minutes
MAX_STORIES_PER_HOUR = 2
MAX_STORIES_PER_DAY = 10
```
- Monitor logs carefully
- Test with a small whitelist
- Stop if any warnings appear

**Week 2 - Ramp Up**
```python
MIN_STORY_DELAY = 450        # 7.5 minutes
MAX_STORIES_PER_HOUR = 3
MAX_STORIES_PER_DAY = 20
```
- Gradually increase limits
- Monitor for rate limit hits
- Continue only if no warnings

**Week 3+ - Normal Operation**
```python
MIN_STORY_DELAY = 300        # 5 minutes
MAX_STORIES_PER_HOUR = 5
MAX_STORIES_PER_DAY = 30
```
- Only if previous weeks were problem-free
- Continue monitoring
- Reduce limits if issues occur

### 3. Operational Safety

**Avoid Spam Patterns**
```
✓ DO: Post irregularly (the bot mirrors group activity)
✓ DO: Take breaks (bot respects group downtime)
✓ DO: Vary captions (200 captions rotate automatically)
✗ DON'T: Post at exact intervals every time
✗ DON'T: Run 24/7 from day one
✗ DON'T: Post identical content repeatedly
```

**Monitor Group Activity**
```
✓ DO: Check your WATCH_GROUP posting frequency
✓ DO: Adjust bot limits based on group activity
✓ DO: Consider pausing bot during high-volume periods
✗ DON'T: Let bot mirror spammy groups
✗ DON'T: Ignore sudden group activity spikes
```

### 4. Whitelist Management

**Start Small**
```
✓ DO: Begin with 1-5 trusted users
✓ DO: Add users who DM you naturally
✓ DO: VET users before whitelisting
✗ DON'T: Pre-fill with large lists
✗ DON'T: Auto-whitelist everyone
```

**Keep Quality High**
```
✓ DO: Remove users who report issues
✓ DO: Monitor for abuse from viewers
✓ DO: Keep whitelist engaged and relevant
✗ DON'T: Ignore user feedback
✗ DON'T Let untrusted users access
```

## Warning Signs to Watch For

### Telegram Warnings

If you receive any Telegram warnings:
1. **Stop the bot immediately**
2. **Reduce rate limits significantly**
3. **Wait 24-48 hours before resuming**
4. **Consider if the use case is worth the risk**

### Rate Limit Logs

Normal operation:
```
INFO: Story posted successfully! Story ID: 12345
INFO: Story recorded. Total today: 3
```

Protective behavior (good!):
```
INFO: Story not posted due to rate limit: Hourly limit reached (5 stories)
INFO: Story not posted due to rate limit: Wait 180 seconds before posting again
```

### Red Flags

Watch for these in logs:
```
✗ FloodWaitError (Telegram rate limiting)
✗ PeerFloodError (too many operations)
✗ Spam ban errors
✗ CAPTCHA requests
```

If you see these:
1. **Stop the bot**
2. **Wait 24+ hours**
3. **Reduce all rate limits by 50%**
4. **Resume with extreme caution**

## Configuration for Different Risk Levels

### Ultra Conservative (Lowest Risk)

```python
MIN_STORY_DELAY = 900        # 15 minutes
MAX_STORIES_PER_HOUR = 2
MAX_STORIES_PER_DAY = 10
COOLDOWN_HOURS = 2
```
- Best for: New accounts, testing, sensitive use cases
- Stories per day: ~10
- Recommended for: First 2 weeks of operation

### Conservative (Low Risk)

```python
MIN_STORY_DELAY = 600        # 10 minutes
MAX_STORIES_PER_HOUR = 3
MAX_STORIES_PER_DAY = 15
COOLDOWN_HOURS = 2
```
- Best for: Aged accounts, careful operation
- Stories per day: ~15
- Recommended for: Weeks 3-4 of operation

### Standard (Moderate Risk)

```python
MIN_STORY_DELAY = 300        # 5 minutes
MAX_STORIES_PER_HOUR = 5
MAX_STORIES_PER_DAY = 30
COOLDOWN_HOURS = 1
```
- Best for: Established accounts, normal operation
- Stories per day: ~30
- **Default configuration**
- Recommended for: Weeks 5+ of operation

### Aggressive (Higher Risk)

```python
MIN_STORY_DELAY = 180        # 3 minutes
MAX_STORIES_PER_HOUR = 8
MAX_STORIES_PER_DAY = 50
COOLDOWN_HOURS = 1
```
- Best for: High-volume needs, tolerant accounts
- Stories per day: ~50
- **Not recommended for new accounts**
- Use at your own risk

## What to Do If Banned

### If You Receive a Warning

1. Stop all bot activity immediately
2. Read the warning carefully
3. Adjust behavior as suggested
4. Wait 48+ hours before resuming
5. Reduce rate limits by 50%

### If Your Account is Restricted

1. Don't panic - restrictions are often temporary
2. Check Telegram's appeals process
3. Wait out the restriction period
4. Reduce bot usage significantly
5. Consider using a different account

### If Your Account is Permanently Banned

1. Accept the decision
2. Don't attempt to circumvent the ban
3. Create a new account if needed
4. Review what went wrong
5. Adjust practices for the new account

## Compliance Checklist

Before running the bot, ensure you can answer YES to:

- [ ] I have Telegram Premium subscription
- [ ] I have legitimate API credentials from my.telegram.org
- [ ] I'm using a dedicated account, not my primary
- [ ] I understand the Terms of Service
- [ ] I'm using this for legitimate purposes only
- [ ] I've configured rate limits appropriately
- [ ] I'm whitelisting only trusted users
- [ ] I'm monitoring logs regularly
- [ ] I understand the risks involved
- [ ] I'm ready to stop if I receive warnings

## Final Recommendations

1. **Start conservative**: You can always increase limits later
2. **Monitor constantly**: Check logs daily for the first week
3. **Listen to warnings**: Telegram's warnings are serious
4. **Prioritize safety**: Over 30 stories/day isn't worth the risk
5. **Have a backup**: Keep a spare account ready

---

**Remember**: No safety measure is 100% effective. Use this bot at your own risk and always comply with Telegram's Terms of Service.

When in doubt, be more conservative with your rate limits.
