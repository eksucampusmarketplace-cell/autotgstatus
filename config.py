# =============================================================================
# WHATSAPP BOT CONFIGURATION
# =============================================================================
# WhatsApp Business API (Twilio) credentials
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+1234567890

# Or use WhatsApp API directly (Meta)
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID/messages
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token

# =============================================================================
# FOLLOW-UP SETTINGS
# =============================================================================
# Randomize follow-up timing between 20-28 hours (avoid automation detection)
FOLLOWUP_MIN_HOURS=20
FOLLOWUP_MAX_HOURS=28

# Quiet hours: Never send between 12am-7am US time
QUIET_HOURS_START=0  # 12am
QUIET_HOURS_END=7    # 7am
QUIET_HOURS_TZ=America/New_York  # US Eastern Time

# Maximum follow-up stages before marking dormant
MAX_FOLLOWUP_STAGES=3

# =============================================================================
# SUPABASE CONFIGURATION (Required for lead tracking)
# =============================================================================
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_key

# =============================================================================
# DEFAULT MESSAGES (Without dashes)
# =============================================================================
# Stage 0: Online but message not opened
STAGE0_MESSAGE="Hey {first_name}, just making sure you're not getting my messages filtered. This week is moving fast. 🔱"

# Stage 1a: Read message, went silent (no specific amount mentioned)
STAGE1A_MESSAGE="I'm only taking 10 traders this week for the $500 to $10k flip. I keep the circle small so I can personally ensure everyone hits their targets. 🥂\n\nIt's a $50 commitment deposit to secure your seat. This isn't a fee for me, it's to filter out the window shoppers and find the people actually ready to work. Once you're in, you get the exact 9:30 AM entry alerts and the full strategy. 📈\n\nI have 2 spots left. You want to lock in, or should I pass?"

# Stage 1b: Saw the $50 and went silent
STAGE1B_MESSAGE="I noticed the silence, {first_name}. Usually that means the risk management part is the concern. 🥂\n\nThe $50 isn't the risk. The real risk is watching this week move without you in it. The people already inside locked in because they understood that. Just let me know either way."

# Stage 2: Still silent after Stage 1
# Uses either STAGE1A or STAGE1B based on what was sent before

# Stage 3: Final follow-up
STAGE3_MESSAGE="Last time reaching out, {first_name}. The spots filled fast this week. If timing wasn't right, no hard feelings — I'll be running the next circle soon. Just reply when you're ready and I'll see what I can do. 🔱"

# =============================================================================
# PITCH MESSAGE (Initial outreach)
# =============================================================================
PITCH_MESSAGE="Hey {first_name}! 👋\n\nI noticed you checked out our trading community. Here's the deal:\n\nWe help traders go from $500 to $10k using a proven strategy with 9:30 AM entry alerts. Small group, personal attention.\n\nWhat's your trading experience been like? And what's your main goal this month?"

# =============================================================================
# LOGGING
# =============================================================================
LOG_FILE="whatsapp_bot.log"
LOG_LEVEL=INFO
