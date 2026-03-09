"""
Configuration file for Telegram Premium Userbot.
All user-configurable settings are defined here.

Environment variables are checked first, then defaults are used.
This makes deployment easier on platforms like Render.
"""

import os

# =============================================================================
# TELEGRAM API CREDENTIALS
# Get these from https://my.telegram.org/apps
# =============================================================================
API_ID = int(os.getenv("API_ID", 12345678))  # Your Telegram API ID (integer)
API_HASH = os.getenv("API_HASH", "your_api_hash_here")  # Your Telegram API hash (string)
STRING_SESSION = os.getenv("STRING_SESSION", "")  # String session for authentication
PHONE_NUMBER = os.getenv("PHONE_NUMBER", "+1234567890")  # Your phone number with country code

# =============================================================================
# SESSION CONFIGURATION
# Option 1: Use string session (copy-paste the session string) - set via STRING_SESSION env var
# Option 2: Use session file (legacy, requires running auth once)
# =============================================================================
# Generate a string session by running:
# python -c "from telethon.sync import TelegramClient; c = TelegramClient('session_name', API_ID, API_HASH); c.start(phone='+1234567890'); print(c.session.save())"
# Then set the output as STRING_SESSION environment variable

# If STRING_SESSION is empty/not set, will use SESSION_FILE instead
SESSION_FILE = "userbot_session.session"

# =============================================================================
# GROUP MONITORING
# Define which group to watch for new images
# Can be: group username (e.g., "mytradinggroup") or numeric chat ID (e.g., -1001234567890)
# =============================================================================
WATCH_GROUP = os.getenv("WATCH_GROUP", "your_group_username_or_id")

# =============================================================================
# CHANNEL MONITORING (Optional)
# Define which channel to watch for new images
# If set, the bot will monitor this channel for images to post as stories
# Can be: channel username (e.g., "mychannel") or numeric chat ID (e.g., 1234567890)
# =============================================================================
WATCH_CHANNEL = os.getenv("WATCH_CHANNEL", "")  # Empty = disabled

# =============================================================================
# CAPTION ROTATION SETTINGS
# =============================================================================
MIN_CAPTION_GAP = int(os.getenv("MIN_CAPTION_GAP", 3))  # Minimum number of other captions before a caption can repeat

# =============================================================================
# RATE LIMITING SETTINGS (IMPORTANT FOR ACCOUNT SAFETY)
# =============================================================================
# Time to wait between posting stories (seconds)
MIN_STORY_DELAY = int(os.getenv("MIN_STORY_DELAY", 300))  # 5 minutes default

# Maximum stories per time period to avoid spam detection
MAX_STORIES_PER_HOUR = int(os.getenv("MAX_STORIES_PER_HOUR", 5))
MAX_STORIES_PER_DAY = int(os.getenv("MAX_STORIES_PER_DAY", 30))

# Cooldown period after hitting daily limit (hours)
COOLDOWN_HOURS = int(os.getenv("COOLDOWN_HOURS", 1))

# Maximum number of existing stories to update when adding a new viewer
# Higher = new viewers can see more old stories, but may hit rate limits
MAX_STORIES_TO_UPDATE = int(os.getenv("MAX_STORIES_TO_UPDATE", 20))

# =============================================================================
# OWNER USER ID
# Your Telegram user ID - only you can use owner commands (/add, /remove, /test)
# Find your ID via @userinfobot on Telegram
# =============================================================================
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", 0))  # Set your actual user ID

# =============================================================================
# VIEWER WHITELIST SETTINGS
# Pre-populate with usernames or numeric user IDs who can view stories
# Format: ["username1", "username2", 123456789, "username3"]
# =============================================================================
CUSTOM_VIEWER_LIST = []

# =============================================================================
# SUPABASE CONFIGURATION (Optional)
# Use Supabase to persist whitelist across restarts and deployments
# Set SUPABASE_URL and SUPABASE_KEY to enable cloud storage
# If not set, whitelist will be stored locally in state.json
# =============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "")  # Your Supabase project URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Your Supabase anon/service key

# =============================================================================
# WELCOME MESSAGE FOR NEW USERS
# DISABLED - No automatic messages are sent to users
# Only the owner can message users manually
# =============================================================================
NEW_USER_MESSAGE = None  # Disabled - owner only messaging

# =============================================================================
# IMAGE COMPOSITION SETTINGS
# =============================================================================
STORY_WIDTH = 1080
STORY_HEIGHT = 1920
CAPTION_FONT_SIZE = 48
CAPTION_TEXT_COLOR = "#FFFFFF"  # White with black shadow (best for any background)
GRADIENT_OPACITY_START = 170  # Alpha value for gradient (0-255)
GRADIENT_HEIGHT_RATIO = 0.35  # Gradient covers bottom 35% of image

# =============================================================================
# LOGGING SETTINGS
# =============================================================================
LOG_FILE = "userbot.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR

# =============================================================================
# STATE FILE
# =============================================================================
STATE_FILE = "state.json"

# =============================================================================
# CAPTIONS LIST (200 captions for rotation)
# =============================================================================
CAPTIONS = [
    # Results & Wins (1-20)
    "Members eating big in here 🍽️",
    "Another day, another bag secured 💰",
    "We don't miss, we eat 🔥",
    "The profits are speaking for themselves 📈",
    "Winning is the only language we speak 🏆",
    "Bag secured. Next. 💼",
    "They said it couldn't be done. Check the chart 📊",
    "Green all day, every day 🟢",
    "This is what discipline looks like 💎",
    "Results don't lie, people do 📈",
    "We came, we saw, we profited 💸",
    "Another one hits 🎯",
    "The market bowed today 👑",
    "Members feasting as usual 🍾",
    "In the green while they sleep 😴",
    "Woke up profitable 🌅",
    "The charts don't lie 📉📈",
    "Consistency is the real flex 💪",
    "Small group, big wins 🏅",
    "We eat first, then we eat again 🍽️🍽️",

    # Options Trading (21-40)
    "Options trading so sweet 🍯",
    "Calls printing like crazy 🖨️",
    "Puts hitting perfectly ✅",
    "We read the market like a book 📖",
    "Options are just math with attitude 🧮",
    "Theta who? We win anyway ⏳",
    "IV crush can't stop us 💥",
    "Premium collected, no stress 😎",
    "Strike price hit like clockwork ⏰",
    "Expiry day smiling at us 🗓️",
    "Weeklies printing again 💵",
    "We don't guess options, we read them 👁️",
    "Greeks working in our favour today 📐",
    "The flow told us first 🌊",
    "Dark pool activity? We saw it coming 🕳️",
    "Smart money followed us this time 🧠",
    "Options flow = free money signals 💹",
    "Monthlies looking lovely 🗓️✅",
    "Volatility is our best friend 📊",
    "We trade options, options don't trade us 👊",

    # Community & Group (41-60)
    "Trade with us, eat with us 🤝",
    "The group that wins together stays together 🏆",
    "Not a group, a movement 🌍",
    "Built different in here 🏗️",
    "Only winners allowed in this room 🚪",
    "This community prints 🖨️",
    "We don't gatekeep, we elevate 🚀",
    "Real traders, real results 💯",
    "The inner circle is eating 🥩",
    "Exclusive for a reason 🔐",
    "You're in the right room 🏠",
    "The best decision you made was joining 💡",
    "Loyalty + discipline = this group 🤝",
    "We move as one 🎯",
    "The family that trades together 👨‍👩‍👧‍👦",
    "Not for everyone. Just the serious ones 🔒",
    "Where real traders come to grow 🌱",
    "This is what a real signal group looks like 📡",
    "Community over competition 🤲",
    "Inside here is a different world 🌐",

    # Calls & Signals (61-80)
    "Signal dropped. Members already in ✅",
    "Called it before the move 📣",
    "Entry perfect, exit cleaner 🎯",
    "We were in before the pump 🚀",
    "The call was free, the profit wasn't 💸",
    "Sent the alert, members moved fast ⚡",
    "In at the bottom, out at the top 📈",
    "Signal accuracy speaking for itself 🎙️",
    "Another clean entry, another clean exit 🏁",
    "Read the setup, trusted the process 🧩",
    "Textbook trade executed perfectly 📚",
    "Alert sent. Money made. Simple. 💰",
    "We don't chase, we wait and win 🐆",
    "Patience + signal = profit 🧘",
    "The setup was there, we took it 🎣",
    "Risk managed, profit secured 🔐",
    "Low risk, high reward — every time 📊",
    "We called the reversal perfectly 🔄",
    "Pre-market call, post-market profit 🌄",
    "The chart pattern played out exactly 🗺️",

    # Mindset & Motivation (81-100)
    "Discipline is the real edge 🧠",
    "Consistency beats luck every time ♟️",
    "The market rewards the patient 🕰️",
    "Losses are lessons, wins are paychecks 📝",
    "Risk management is self-management 🛡️",
    "Trade the plan, not the emotion 📋",
    "Your mindset is your most valuable asset 💡",
    "Slow and steady builds the account 🐢",
    "One good trade can change your week 🗓️",
    "We don't FOMO, we prepare 🔭",
    "Fear is for those without a strategy 😤",
    "The best traders are the most patient 🧘",
    "Think long term, trade short term 🔮",
    "Capital protection first, profits second 🛡️",
    "Every loss is tuition 🎓",
    "The market is always right — so we adapt 🌊",
    "No emotion, just execution 🤖",
    "Size your risk, not your greed ⚖️",
    "The chart tells the truth if you listen 👂",
    "Mastery over the market starts with self 🪞",

    # Market Commentary (101-120)
    "Market opened and we were already positioned 📍",
    "Bulls running today, we ran with them 🐂",
    "Bears tried it. We shorted them too 🐻",
    "Volatility? We trade that too 🌪️",
    "Red market, green portfolio 🟢",
    "While the market panicked, we planned 🧩",
    "Sector rotation caught early ♻️",
    "The macro told us the micro 🔭",
    "News came out. We already knew 📰",
    "CPI day and we were ready 📅",
    "Fed meeting? Already positioned 🏦",
    "Earnings play hit perfectly 💹",
    "Gap up called the night before 🌙",
    "Pre-market movers spotted early 🌅",
    "The volume told the story 📢",
    "Institutional money tipped us off 🏛️",
    "Smart money doesn't hide from us 👁️",
    "We trade the trend, not against it 🌊",
    "Breakout confirmed, members in ✅",
    "Support held exactly where we said 📏",

    # Lifestyle & Flex (121-140)
    "Trading funded the lifestyle 🏖️",
    "Charts in the morning, freedom in the evening 🌇",
    "Work smarter, not harder 🧠",
    "Financial freedom is the goal 🗺️",
    "The laptop is the office 💻",
    "Location independent, profit dependent 🌍",
    "Trading pays for what the job can't 💳",
    "9 to 5 is not the only way 🕐",
    "Building wealth one trade at a time 🧱",
    "This is what we work towards every day 🌟",
    "The grind is quiet, the results are loud 🔇📢",
    "Less talking, more executing 🤐",
    "The account growing while you read this 📈",
    "Every pip counts 💰",
    "Small account. Big ambitions. Bigger results 🎯",
    "From zero to consistent 🔁",
    "The journey is the reward 🛤️",
    "Trading is a skill. We teach it here 🎓",
    "Financial literacy is power 📚",
    "Generational wealth starts with one decision 🌳",

    # FOMO Triggers (141-150)
    "You missed this one. Don't miss the next 👀",
    "Members already up. You still watching? ⏳",
    "The train is moving. Get on 🚂",
    "While you wait, we ate 🍽️",
    "Another one closed green without you 💚",
    "Join before the next signal drops 📡",
    "The next call could change everything 🔮",
    "Don't watch from the outside 🪟",
    "Opportunity doesn't wait 🏃",
    "The early ones always eat best 🍗",

    # Crypto & Forex (151-160)
    "Crypto doesn't sleep and neither does profit 🌙",
    "BTC said go, we went 🟠",
    "Altseason hitting different in here 🎭",
    "Forex pairs moving beautifully 💱",
    "Pips stacking up nicely 📐",
    "The dollar strong, our positions stronger 💪",
    "Crypto signal hit to the pip 🎯",
    "DeFi gains looking lovely 🌐",
    "Spot and futures — we do both ⚔️",
    "The blockchain doesn't lie 🔗",

    # Short & Punchy (161-180)
    "In. Profit. Out. 💨",
    "Called it. ✅",
    "Again. 🔁",
    "Consistent. 📊",
    "Members winning. 🏆",
    "Green day. 🟢",
    "We don't miss. 🎯",
    "Another hit. 💥",
    "Told you. 😏",
    "Printing. 🖨️",
    "Clean. 🧼",
    "Easy. 😌",
    "Locked in. 🔐",
    "Running. 🏃",
    "Up only. 📈",
    "Secured. 💼",
    "Accurate. 🎯",
    "Blessed. 🙏",
    "Focused. 🧘",
    "Winning. 🏅",

    # Weekend / Time-based (181-190)
    "Weekend profits hit different 🌴",
    "Monday market open, we're ready 📋",
    "Friday closed green — as always ✅",
    "Pre-market prepared, post-market paid 🌄",
    "End of week looking beautiful 🌅",
    "Quarterly targets crushed 📆",
    "Month not even over and we're up 📅",
    "Mid-week check — all green 🟢",
    "Sunday prep = Monday profit 🗓️",
    "Closing the week in profit, opening the next the same way 🔄",

    # Trust & Credibility (191-200)
    "Track record speaks louder than promises 📜",
    "No hype, just results 🚫📣",
    "Verified wins, real members 🪪",
    "Transparency is our policy 🔍",
    "We show the losses too — that's honesty 🤝",
    "Screenshots don't pay bills, discipline does 📱",
    "Built on trust, sustained by results 🏗️",
    "No fake signals, no fake gurus 🚫",
    "Real calls from real traders 💯",
    "The proof is in the portfolio 📂",
]
