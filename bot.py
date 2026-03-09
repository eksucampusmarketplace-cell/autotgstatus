"""
Telegram Premium Userbot - Main Entry Point
Listens for images in a specified group and posts them as Telegram Stories
with rotating captions and privacy controls.
"""

import os
import sys
import json
import asyncio
import logging
import random
from typing import List, Set, Union
from datetime import datetime, timedelta
from aiohttp import web

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.stories import SendStoryRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    InputPrivacyValueAllowUsers,
    InputUser,
    InputPeerUser,
    InputMediaUploadedPhoto,
)
from telethon.tl.types import MessageMediaPhoto, User
from telethon.tl.types import InputPrivacyValueDisallowAll

import config
from composer import ImageComposer


# =============================================================================
# LOGGING SETUP
# =============================================================================
def setup_logging():
    """Set up logging to both console and file."""
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Determine log file path
    if os.path.exists("/opt/render"):
        log_file = "/opt/render/project/data/userbot.log"
        # Ensure the data directory exists
        os.makedirs("/opt/render/project/data", exist_ok=True)
    else:
        log_file = config.LOG_FILE

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


logger = setup_logging()


# =============================================================================
# RATE LIMITER
# =============================================================================
class RateLimiter:
    """Enforces rate limits to protect account from spam detection."""

    def __init__(self, state_manager):
        self.state_manager = state_manager

    def can_post_story(self) -> tuple[bool, str]:
        """
        Check if a story can be posted based on rate limits.
        Returns (can_post, reason_message)
        """
        now = datetime.now()
        state = self.state_manager.state

        # Initialize rate limit tracking if needed
        if "story_timestamps" not in state:
            state["story_timestamps"] = []

        timestamps = state["story_timestamps"]

        # Check cooldown period after hitting daily limit
        if "daily_limit_hit_at" in state:
            limit_hit_time = datetime.fromisoformat(state["daily_limit_hit_at"])
            cooldown_end = limit_hit_time + timedelta(hours=config.COOLDOWN_HOURS)
            if now < cooldown_end:
                remaining = (cooldown_end - now).total_seconds() / 60
                return False, f"Cooldown active. Wait {remaining:.0f} minutes."
            else:
                # Cooldown over, clear the limit
                del state["daily_limit_hit_at"]

        # Clean up old timestamps (older than 24 hours)
        one_day_ago = now - timedelta(days=1)
        timestamps = [ts for ts in timestamps if datetime.fromisoformat(ts) > one_day_ago]
        state["story_timestamps"] = timestamps

        # Check daily limit
        if len(timestamps) >= config.MAX_STORIES_PER_DAY:
            state["daily_limit_hit_at"] = now.isoformat()
            self.state_manager._save_state()
            return False, f"Daily limit reached ({config.MAX_STORIES_PER_DAY} stories)"

        # Check hourly limit
        one_hour_ago = now - timedelta(hours=1)
        recent_hour = [ts for ts in timestamps if datetime.fromisoformat(ts) > one_hour_ago]
        if len(recent_hour) >= config.MAX_STORIES_PER_HOUR:
            return False, f"Hourly limit reached ({config.MAX_STORIES_PER_HOUR} stories)"

        # Check minimum delay between stories
        if timestamps:
            last_post = datetime.fromisoformat(timestamps[-1])
            time_since_last = (now - last_post).total_seconds()
            if time_since_last < config.MIN_STORY_DELAY:
                remaining = config.MIN_STORY_DELAY - time_since_last
                return False, f"Wait {remaining:.0f} seconds before posting again"

        return True, "Ready to post"

    def record_story_posted(self):
        """Record that a story was posted."""
        now = datetime.now().isoformat()
        state = self.state_manager.state

        if "story_timestamps" not in state:
            state["story_timestamps"] = []

        state["story_timestamps"].append(now)
        self.state_manager._save_state()
        logger.info(f"Story recorded. Total today: {len(state['story_timestamps'])}")


# =============================================================================
# SUPABASE CLIENT (Optional)
# =============================================================================
_supabase_client = None

def get_supabase_client():
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        return None
    
    try:
        from supabase import create_client
        _supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


# =============================================================================
# STATE MANAGEMENT
# =============================================================================
class StateManager:
    """Manages persistent state including caption history and viewer whitelist.
    
    Uses Supabase for whitelist persistence if configured, otherwise uses local JSON file.
    """

    def __init__(self, state_file: str = config.STATE_FILE):
        # Determine if we're on Render (check for the persistent data directory)
        is_render = os.path.exists("/opt/render")

        # Use persistent disk path for Render deployment
        if is_render:
            self.state_file = "/opt/render/project/data/state.json"
        else:
            self.state_file = state_file
        
        # Initialize Supabase client
        self.supabase = get_supabase_client()
        self.use_supabase = self.supabase is not None
        
        if self.use_supabase:
            logger.info("Using Supabase for whitelist persistence")
        else:
            logger.info("Using local JSON file for whitelist persistence")
        
        self.state = self._load_state()
        self._ensure_defaults()
        
        # Sync whitelist from Supabase on startup
        self._sync_whitelist_from_supabase()

    def _load_state(self) -> dict:
        """Load state from JSON file or return defaults."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load state file: {e}")
        return {}

    def _save_state(self):
        """Save current state to JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_file) if os.path.dirname(self.state_file) else ".", exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save state file: {e}")

    def _ensure_defaults(self):
        """Ensure state has all required fields with defaults."""
        if "caption_history" not in self.state:
            self.state["caption_history"] = []
        if "viewer_whitelist" not in self.state:
            # Initialize with custom list from config
            self.state["viewer_whitelist"] = [
                str(uid) for uid in config.CUSTOM_VIEWER_LIST
            ]
        if "last_caption_index" not in self.state:
            self.state["last_caption_index"] = None
        self._save_state()

    def _sync_whitelist_from_supabase(self):
        """Sync whitelist from Supabase to local state on startup."""
        if not self.use_supabase:
            return
        
        try:
            response = self.supabase.table("whitelist").select("user_id").execute()
            if response.data:
                supabase_ids = [str(item["user_id"]) for item in response.data]
                local_whitelist = self.state.get("viewer_whitelist", [])
                
                # Merge Supabase IDs with local whitelist (avoid duplicates)
                merged = list(set(local_whitelist + supabase_ids))
                self.state["viewer_whitelist"] = merged
                self._save_state()
                logger.info(f"Synced {len(supabase_ids)} users from Supabase whitelist")
        except Exception as e:
            logger.error(f"Failed to sync whitelist from Supabase: {e}")

    def _save_whitelist_to_supabase(self, user_id: str):
        """Save a user to Supabase whitelist."""
        if not self.use_supabase:
            return True
        
        try:
            # Check if already exists
            response = self.supabase.table("whitelist").select("id").eq("user_id", user_id).execute()
            if response.data:
                return True  # Already exists
            
            # Insert new record
            self.supabase.table("whitelist").insert({"user_id": user_id}).execute()
            logger.info(f"Saved user {user_id} to Supabase whitelist")
            return True
        except Exception as e:
            logger.error(f"Failed to save to Supabase: {e}")
            return False

    def _remove_whitelist_from_supabase(self, user_id: str):
        """Remove a user from Supabase whitelist."""
        if not self.use_supabase:
            return True
        
        try:
            self.supabase.table("whitelist").delete().eq("user_id", user_id).execute()
            logger.info(f"Removed user {user_id} from Supabase whitelist")
            return True
        except Exception as e:
            logger.error(f"Failed to remove from Supabase: {e}")
            return False

    def _clear_whitelist_in_supabase(self):
        """Clear all users from Supabase whitelist."""
        if not self.use_supabase:
            return True
        
        try:
            self.supabase.table("whitelist").delete().neq("id", 0).execute()
            logger.info("Cleared all users from Supabase whitelist")
            return True
        except Exception as e:
            logger.error(f"Failed to clear Supabase whitelist: {e}")
            return False

    def get_caption_history(self) -> List[int]:
        """Get list of recently used caption indices."""
        return self.state.get("caption_history", [])

    def add_caption_to_history(self, caption_index: int):
        """Add a caption index to history and maintain size limit."""
        history = self.state.get("caption_history", [])
        history.append(caption_index)
        # Keep only the last MIN_CAPTION_GAP entries to track recent usage
        max_history = config.MIN_CAPTION_GAP
        if len(history) > max_history:
            history = history[-max_history:]
        self.state["caption_history"] = history
        self.state["last_caption_index"] = caption_index
        self._save_state()

    def get_viewer_whitelist(self) -> List[str]:
        """Get list of whitelisted viewer IDs/usernames."""
        return self.state.get("viewer_whitelist", [])

    def add_viewer_to_whitelist(self, user_id: Union[int, str]):
        """Add a user to the viewer whitelist."""
        user_id_str = str(user_id)
        whitelist = self.state.get("viewer_whitelist", [])
        if user_id_str not in whitelist:
            whitelist.append(user_id_str)
            self.state["viewer_whitelist"] = whitelist
            self._save_state()
            
            # Also save to Supabase if configured
            if self.use_supabase:
                self._save_whitelist_to_supabase(user_id_str)
            
            logger.info(f"Added user {user_id} to viewer whitelist")
            return True
        return False

    def remove_viewer_from_whitelist(self, user_id: Union[int, str]):
        """Remove a user from the viewer whitelist."""
        user_id_str = str(user_id)
        whitelist = self.state.get("viewer_whitelist", [])
        if user_id_str in whitelist:
            whitelist.remove(user_id_str)
            self.state["viewer_whitelist"] = whitelist
            self._save_state()
            
            # Also remove from Supabase if configured
            if self.use_supabase:
                self._remove_whitelist_from_supabase(user_id_str)
            
            logger.info(f"Removed user {user_id} from viewer whitelist")
            return True
        return False

    def clear_viewer_whitelist(self):
        """Clear all viewers from the whitelist."""
        self.state["viewer_whitelist"] = []
        self._save_state()
        
        # Also clear in Supabase if configured
        if self.use_supabase:
            self._clear_whitelist_in_supabase()
        
        logger.info("Cleared all viewers from whitelist")


# =============================================================================
# CAPTION ROTATOR
# =============================================================================
class CaptionRotator:
    """Handles random caption rotation with minimum gap enforcement."""

    def __init__(self, captions: List[str], state_manager: StateManager):
        self.captions = captions
        self.state_manager = state_manager
        self.min_gap = config.MIN_CAPTION_GAP

    def get_next_caption(self) -> str:
        """
        Get the next caption randomly, ensuring no repeats until MIN_CAPTION_GAP
        other captions have been used.
        """
        history = self.state_manager.get_caption_history()
        all_indices = set(range(len(self.captions)))
        excluded_indices = set(history[-self.min_gap:]) if history else set()

        available_indices = list(all_indices - excluded_indices)

        if not available_indices:
            # Fallback: if all excluded, just pick randomly
            available_indices = list(all_indices)

        chosen_index = random.choice(available_indices)
        self.state_manager.add_caption_to_history(chosen_index)

        return self.captions[chosen_index]


# =============================================================================
# TELEGRAM USERBOT
# =============================================================================
class TelegramStoryBot:
    """Main bot class handling Telegram interactions and story posting."""

    def __init__(self):
        # Determine if we're on Render (check for the persistent data directory)
        is_render = os.path.exists("/opt/render")

        # Set persistent session file path
        if is_render:
            session_file = "/opt/render/project/data/userbot_session.session"
            # Ensure data directory exists
            os.makedirs("/opt/render/project/data", exist_ok=True)
        else:
            session_file = config.SESSION_FILE

        # Handle string session vs file session
        # For Render deployment, prefer string session for persistence
        if config.STRING_SESSION:
            # Use string session (can be copy-pasted)
            self.client = TelegramClient(
                StringSession(config.STRING_SESSION),
                config.API_ID,
                config.API_HASH,
            )
        else:
            # Use session file (legacy)
            self.client = TelegramClient(
                session_file,
                config.API_ID,
                config.API_HASH,
            )

        self.state_manager = StateManager()
        self.rate_limiter = RateLimiter(self.state_manager)
        self.caption_rotator = CaptionRotator(config.CAPTIONS, self.state_manager)
        self.composer = ImageComposer(
            story_width=config.STORY_WIDTH,
            story_height=config.STORY_HEIGHT,
            caption_font_size=config.CAPTION_FONT_SIZE,
            caption_text_color=config.CAPTION_TEXT_COLOR,
            gradient_opacity_start=config.GRADIENT_OPACITY_START,
            gradient_height_ratio=config.GRADIENT_HEIGHT_RATIO,
        )
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up event handlers for the bot."""

        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            """Handle all new messages - for whitelist, group, and channel monitoring."""
            # Check if this is a private message (DM) for whitelist
            if event.is_private:
                await self._handle_private_message(event)
                return

            # Check if this is the watched group
            if await self._is_watched_group(event):
                await self._handle_group_message(event)

            # Check if this is the watched channel
            if await self._is_watched_channel(event):
                await self._handle_channel_message(event)

    async def _handle_private_message(self, event):
        """Handle private messages - commands to manage whitelist and get status."""
        sender = await event.get_sender()
        if not isinstance(sender, User):
            return

        user_id = sender.id
        username = sender.username or "N/A"
        message_text = event.message.message.strip()

        # Check if user is authorized to manage whitelist (owner only)
        is_owner = user_id == config.OWNER_USER_ID
        
        # Parse command
        if message_text.startswith("/"):
            # It's a command
            command_parts = message_text.split(maxsplit=1)
            command = command_parts[0].lower()
            args = command_parts[1] if len(command_parts) > 1 else ""
            
            if command in ["/start", "/help"]:
                await self._send_help(event, is_owner)
            elif command == "/viewers" or command == "/list":
                await self._send_viewer_list(event)
            elif command == "/status":
                await self._send_status(event)
            elif is_owner:
                # Owner-only commands
                if command == "/add" and args:
                    await self._add_viewer(event, args)
                elif command == "/remove" and args:
                    await self._remove_viewer(event, args)
                elif command == "/clear":
                    await self._clear_viewers(event)
                elif command == "/test":
                    await self._test_story(event)
                else:
                    await event.reply("Unknown command. Use /help for available commands.")
            else:
                # Unknown command from non-owner
                await event.reply("Unknown command. Use /help for available commands.")
        else:
            # Auto-add sender to whitelist when they message
            # No messages are sent to users - only owner can message manually
            username = sender.username or "N/A"
            added = self.state_manager.add_viewer_to_whitelist(user_id)
            
            if added:
                logger.info(f"Auto-added user {user_id} (@{username}) to whitelist from DM")
                # Update existing stories to include the new user
                try:
                    await self.update_all_stories_for_new_user(user_id)
                except Exception as e:
                    logger.warning(f"Could not update existing stories for new user: {e}")
            else:
                logger.debug(f"User {user_id} (@{username}) already in whitelist")

    async def _send_help(self, event, is_owner: bool):
        """Send help message with available commands."""
        help_text = """📖 *Available Commands*

• /start - Show this help message
• /viewers - List all viewers who can see stories  
• /status - Show bot status and settings
"""
        if is_owner:
            help_text += """
👑 *Owner Commands*
• /add @username - Add viewer by username
• /add <user_id> - Add viewer by user ID
• /remove @username - Remove viewer by username
• /remove <user_id> - Remove viewer by user ID
• /clear - Remove all viewers
• /test - Post a test story
"""
        await event.reply(help_text)

    async def _send_viewer_list(self, event):
        """Send list of current viewers with resolved usernames."""
        viewers = self.state_manager.get_viewer_whitelist()
        if not viewers:
            await event.reply("No viewers in the list yet.")
            return
        
        text = f"👀 *Current Viewers* ({len(viewers)}):\n\n"
        
        # Resolve each viewer to get their username/info
        for i, viewer in enumerate(viewers, 1):
            try:
                # Try to resolve the user
                if isinstance(viewer, int) or (
                    isinstance(viewer, str) and viewer.lstrip("-").isdigit()
                ):
                    user_id = int(viewer)
                    entity = await self.client.get_entity(user_id)
                    if isinstance(entity, User):
                        username = f"@{entity.username}" if entity.username else f"ID:{entity.id}"
                        name = entity.first_name or "Unknown"
                        if entity.last_name:
                            name += f" {entity.last_name}"
                        text += f"{i}. {name} (`{username}`)\n"
                    else:
                        text += f"{i}. `{viewer}`\n"
                else:
                    # It's a username string
                    username = viewer.lstrip("@")
                    entity = await self.client.get_entity(username)
                    if isinstance(entity, User):
                        name = entity.first_name or "Unknown"
                        if entity.last_name:
                            name += f" {entity.last_name}"
                        text += f"{i}. {name} (`@{entity.username}`)\n"
                    else:
                        text += f"{i}. `@{viewer}`\n"
            except Exception as e:
                # If resolution fails, just show the raw value
                text += f"{i}. `{viewer}` (unresolved)\n"
        
        await event.reply(text)

    async def _send_status(self, event):
        """Send bot status information."""
        viewers = self.state_manager.get_viewer_whitelist()
        
        text = f"""📊 *Bot Status*

• Watch Group: `{config.WATCH_GROUP}`
• Watch Channel: `{config.WATCH_CHANNEL or 'Disabled'}`
• Viewers: {len(viewers)}
• Captions: {len(config.CAPTIONS)}
• Min Story Delay: {config.MIN_STORY_DELAY}s
• Max Stories/Day: {config.MAX_STORIES_PER_DAY}
"""
        await event.reply(text)

    async def _add_viewer(self, event, user_input: str):
        """Add a viewer by username or user ID."""
        user_input = user_input.strip().lstrip("@")
        
        # Try to resolve the user
        try:
            # Check if it's a numeric ID
            if user_input.lstrip("-").isdigit():
                user_id = int(user_input)
                entity = await self.client.get_entity(user_id)
            else:
                # It's a username
                entity = await self.client.get_entity(f"@{user_input}")
            
            if isinstance(entity, User):
                added = self.state_manager.add_viewer_to_whitelist(entity.id)
                if added:
                    username = f"@{entity.username}" if entity.username else f"ID:{entity.id}"
                    await event.reply(f"✅ Added {username} to viewers!")
                    # Update existing stories to include the new user
                    try:
                        await self.update_all_stories_for_new_user(entity.id)
                    except Exception as e:
                        logger.warning(f"Could not update existing stories for new user: {e}")
                else:
                    username = f"@{entity.username}" if entity.username else f"ID:{entity.id}"
                    await event.reply(f"ℹ️ {username} is already in the viewer list.")
            else:
                await event.reply("❌ Could not resolve user.")
        except Exception as e:
            logger.error(f"Error adding viewer: {e}")
            await event.reply(f"❌ Error: {e}")

    async def _remove_viewer(self, event, user_input: str):
        """Remove a viewer by username or user ID."""
        user_input = user_input.strip().lstrip("@")
        
        # Try to resolve the user first
        try:
            if user_input.lstrip("-").isdigit():
                user_id = int(user_input)
            else:
                entity = await self.client.get_entity(f"@{user_input}")
                if isinstance(entity, User):
                    user_id = entity.id
                else:
                    await event.reply("❌ Could not resolve user.")
                    return
        except:
            # If resolution fails, try as direct ID
            try:
                user_id = int(user_input)
            except:
                await event.reply("❌ Invalid username or ID.")
                return
        
        # Remove from whitelist
        removed = self.state_manager.remove_viewer_from_whitelist(user_id)
        if removed:
            await event.reply(f"✅ Removed user {user_id} from viewers!")
        else:
            await event.reply(f"ℹ️ User {user_id} was not in the viewer list.")

    async def _clear_viewers(self, event):
        """Clear all viewers."""
        self.state_manager.clear_viewer_whitelist()
        await event.reply("✅ All viewers have been removed.")

    async def _test_story(self, event):
        """Post a test story."""
        await event.reply("🧪 Posting test story...")
        
        # Check rate limits
        can_post, reason = self.rate_limiter.can_post_story()
        if not can_post:
            await event.reply(f"⏳ Cannot test: {reason}")
            return
        
        try:
            # Create a simple test image
            test_image = self.composer.create_test_image("TEST STORY")
            
            # Post the story
            await self._post_story(test_image)
            self.rate_limiter.record_story_posted()
            await event.reply("✅ Test story posted!")
        except Exception as e:
            await event.reply(f"❌ Error posting test: {e}")

    async def _is_watched_group(self, event) -> bool:
        """Check if the message is from the watched group."""
        try:
            chat = await event.get_chat()
            watch_group = config.WATCH_GROUP

            # Don't try to match if it's the placeholder value
            if watch_group == "your_group_username_or_id" or not watch_group:
                logger.warning(f"WATCH_GROUP not configured! Set it to your actual group username/ID in config.py or env var")
                return False

            # Handle numeric chat ID
            if isinstance(watch_group, int) or (
                isinstance(watch_group, str) and watch_group.lstrip("-").isdigit()
            ):
                watch_group_id = int(watch_group)
                
                # Also check if this could be a channel/supergroup ID
                # Supergroups have format -100{channel_id}
                # Check if -100{channel_id} matches the chat ID
                if hasattr(chat, "id"):
                    # Direct match
                    if chat.id == watch_group_id:
                        logger.info(f"Matched group by ID: {chat.id}")
                        return True
                    
                    # Check for supergroup format: -100{10-digit-channel-id}
                    # The user might have set WATCH_GROUP=-1003825876206
                    # But the actual channel ID in the dialog is 3825876206 (positive)
                    # So extract the channel part and compare with positive ID too
                    watch_str = str(watch_group_id)
                    if watch_str.startswith("-100") and len(watch_str) == 14:
                        # Extract the channel part (last 10 digits)
                        channel_part = watch_str[4:]  # Remove -100 prefix
                        # Check if chat.id matches the resolved supergroup ID
                        expected_id = -1000000000000 - int(channel_part)
                        if chat.id == expected_id:
                            logger.info(f"Matched supergroup by resolved ID: {chat.id}")
                            return True
                        # Also check if it matches the raw channel ID (positive)
                        if chat.id == int(channel_part):
                            logger.info(f"Matched channel by raw ID: {chat.id}")
                            return True
                return False

            # Handle username
            if hasattr(chat, "username") and chat.username:
                is_match = chat.username.lower() == watch_group.lower().lstrip("@")
                if is_match:
                    logger.info(f"Matched group by username: @{chat.username}")
                else:
                    # Debug info when not matching
                    logger.debug(f"Group username @{chat.username} != {watch_group}")
                return is_match

            # Handle title
            if hasattr(chat, "title"):
                is_match = chat.title == watch_group
                if is_match:
                    logger.info(f"Matched group by title: {chat.title}")
                else:
                    logger.debug(f"Group title '{chat.title}' != '{watch_group}'")
                return is_match

        except Exception as e:
            logger.error(f"Error checking watched group: {e}")

        return False

    async def _handle_group_message(self, event):
        """Handle messages from the watched group."""
        chat = await event.get_chat()
        chat_info = f"@{chat.username}" if hasattr(chat, 'username') and chat.username else chat.title if hasattr(chat, 'title') else f"ID:{chat.id}"
        
        # Only process image messages
        if not event.message.media:
            logger.debug(f"Ignoring non-media message from {chat_info}")
            return

        if not isinstance(event.message.media, MessageMediaPhoto):
            logger.debug(f"Ignoring non-photo media from {chat_info}")
            return

        logger.info(f"New image detected in watched group {chat_info} (msg_id: {event.message.id})")

        # Check rate limits first
        can_post, reason = self.rate_limiter.can_post_story()
        if not can_post:
            logger.info(f"Story not posted due to rate limit: {reason}")
            return

        try:
            # Download the image
            image_bytes = await event.message.download_media(bytes)
            if not image_bytes:
                logger.error("Failed to download image")
                return

            # Get next caption
            caption = self.caption_rotator.get_next_caption()
            logger.info(f"Selected caption: {caption}")

            # Compose the story image
            story_image = self.composer.process_image_from_bytes(image_bytes, caption)

            # Post the story
            await self._post_story(story_image)

            # Record the story post for rate limiting
            self.rate_limiter.record_story_posted()

        except Exception as e:
            logger.error(f"Error processing group message: {e}", exc_info=True)

    async def _is_watched_channel(self, event) -> bool:
        """Check if the message is from the watched channel."""
        try:
            chat = await event.get_chat()
            watch_channel = config.WATCH_CHANNEL

            if not watch_channel:
                logger.debug("WATCH_CHANNEL not configured")
                return False

            # Handle numeric chat ID
            if isinstance(watch_channel, int) or (
                isinstance(watch_channel, str) and watch_channel.lstrip("-").isdigit()
            ):
                watch_channel_id = int(watch_channel)
                is_match = hasattr(chat, "id") and chat.id == watch_channel_id
                if is_match:
                    logger.info(f"Matched channel by ID: {chat.id}")
                return is_match

            # Handle username
            if hasattr(chat, "username") and chat.username:
                is_match = chat.username.lower() == watch_channel.lower().lstrip("@")
                if is_match:
                    logger.info(f"Matched channel by username: @{chat.username}")
                return is_match

            # Handle title
            if hasattr(chat, "title"):
                is_match = chat.title == watch_channel
                if is_match:
                    logger.info(f"Matched channel by title: {chat.title}")
                return is_match

        except Exception as e:
            logger.error(f"Error checking watched channel: {e}")

        return False

    async def _handle_channel_message(self, event):
        """Handle messages from the watched channel."""
        # Only process image messages
        if not event.message.media:
            logger.debug("Ignoring non-media message in channel")
            return

        if not isinstance(event.message.media, MessageMediaPhoto):
            logger.debug("Ignoring non-photo media message in channel")
            return

        logger.info(f"New image detected in watched channel (msg_id: {event.message.id})")

        # Check rate limits first
        can_post, reason = self.rate_limiter.can_post_story()
        if not can_post:
            logger.info(f"Story not posted due to rate limit: {reason}")
            return

        try:
            # Download the image
            image_bytes = await event.message.download_media(bytes)
            if not image_bytes:
                logger.error("Failed to download image from channel")
                return

            # Get next caption
            caption = self.caption_rotator.get_next_caption()
            logger.info(f"Selected caption: {caption}")

            # Compose the story image
            story_image = self.composer.process_image_from_bytes(image_bytes, caption)

            # Post the story
            await self._post_story(story_image)

            # Record the story post for rate limiting
            self.rate_limiter.record_story_posted()

        except Exception as e:
            logger.error(f"Error processing channel message: {e}", exc_info=True)

    async def _resolve_whitelist_users(self) -> List[InputUser]:
        """Resolve whitelisted user IDs/usernames to InputUser objects."""
        whitelist = self.state_manager.get_viewer_whitelist()
        input_users = []

        for entry in whitelist:
            try:
                # Try as integer ID first
                if isinstance(entry, int) or (
                    isinstance(entry, str) and entry.lstrip("-").isdigit()
                ):
                    user_id = int(entry)
                    # Get user entity
                    try:
                        entity = await self.client.get_entity(user_id)
                        if isinstance(entity, User):
                            input_users.append(
                                InputUser(user_id=entity.id, access_hash=entity.access_hash)
                            )
                            logger.debug(f"Resolved user ID {user_id}")
                    except Exception as e:
                        logger.warning(f"Could not resolve user ID {user_id}: {e}")
                else:
                    # Try as username
                    username = entry.lstrip("@")
                    try:
                        entity = await self.client.get_entity(username)
                        if isinstance(entity, User):
                            input_users.append(
                                InputUser(user_id=entity.id, access_hash=entity.access_hash)
                            )
                            logger.debug(f"Resolved username @{username}")
                    except Exception as e:
                        logger.warning(f"Could not resolve username @{username}: {e}")
            except Exception as e:
                logger.error(f"Error resolving whitelist entry '{entry}': {e}")

        return input_users

    async def _post_story(self, image_bytes: bytes):
        """Post the composed image as a Telegram Story with privacy settings."""
        try:
            # Get the current user (self) as peer for the story
            me = await self.client.get_me()
            peer = InputPeerUser(user_id=me.id, access_hash=me.access_hash)

            # Resolve whitelist users
            allowed_users = await self._resolve_whitelist_users()

            if not allowed_users:
                logger.warning("No valid users in whitelist - story will be posted with default privacy")

            # Create privacy rule
            privacy_rules = [InputPrivacyValueAllowUsers(users=allowed_users)] if allowed_users else []

            # Upload the image with proper file name for extension detection
            file = await self.client.upload_file(image_bytes, file_name="photo.jpg")

            # Post the story (with required peer parameter)
            result = await self.client(
                SendStoryRequest(
                    peer=peer,
                    media=InputMediaUploadedPhoto(file=file),
                    privacy_rules=privacy_rules,
                    noforwards=False,
                )
            )

            logger.info("Story posted successfully!")

        except Exception as e:
            logger.error(f"Failed to post story: {e}", exc_info=True)

    async def _update_story_privacy(self, story_id: int, new_user_id: int):
        """Update an existing story's privacy to include a new user."""
        try:
            from telethon.tl.functions.stories import EditStoryRequest
            
            me = await self.client.get_me()
            peer = InputPeerUser(user_id=me.id, access_hash=me.access_hash)
            
            # Resolve the new user
            entity = await self.client.get_entity(new_user_id)
            if not isinstance(entity, User):
                logger.warning(f"Cannot update story privacy - could not resolve user {new_user_id}")
                return False
            
            input_user = InputUser(user_id=entity.id, access_hash=entity.access_hash)
            
            # Get current whitelist and add the new user
            allowed_users = await self._resolve_whitelist_users()
            
            # Make sure the new user is included
            if input_user not in allowed_users:
                allowed_users.append(input_user)
            
            # Create privacy rule
            privacy_rules = [InputPrivacyValueAllowUsers(users=allowed_users)] if allowed_users else []
            
            # Try to update the story - note: this may not work for all story types
            try:
                await self.client(
                    EditStoryRequest(
                        peer=peer,
                        id=story_id,
                        privacy_rules=privacy_rules,
                    )
                )
                logger.info(f"Updated story {story_id} privacy for user {new_user_id}")
                return True
            except Exception as e:
                logger.warning(f"Could not update story {story_id} privacy: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating story privacy: {e}")
            return False

    async def update_all_stories_for_new_user(self, new_user_id: int):
        """Update all existing stories to include a new user in their privacy settings."""
        try:
            from telethon.tl.functions.stories import GetUserStoriesRequest
            
            me = await self.client.get_me()
            
            # Get all stories from the user
            stories_result = await self.client(
                GetUserStoriesRequest(peer=InputPeerUser(user_id=me.id, access_hash=me.access_hash))
            )
            
            story_count = 0
            success_count = 0
            
            # Update each story (limit to recent stories to avoid rate limits)
            max_stories_to_update = 10
            for story in stories_result.stories[:max_stories_to_update]:
                story_count += 1
                if await self._update_story_privacy(story.id, new_user_id):
                    success_count += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            logger.info(f"Updated {success_count}/{story_count} stories for new user {new_user_id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error updating stories for new user: {e}")
            return False

    async def start(self):
        """Start the bot."""
        logger.info("Starting Telegram Story Userbot...")
        logger.info(f"Session type: {'string session' if config.STRING_SESSION else 'file session'}")
        logger.info(f"Watch group: {config.WATCH_GROUP}")
        logger.info(f"Watch channel: {config.WATCH_CHANNEL if config.WATCH_CHANNEL else '(disabled)'}")
        logger.info(f"Viewer whitelist count: {len(self.state_manager.get_viewer_whitelist())}")
        logger.info(f"Available captions: {len(config.CAPTIONS)}")
        logger.info(f"Min caption gap: {config.MIN_CAPTION_GAP}")

        # Log rate limiting settings
        logger.info("=" * 60)
        logger.info("RATE LIMITING SETTINGS (Account Safety)")
        logger.info("=" * 60)
        logger.info(f"Min delay between stories: {config.MIN_STORY_DELAY}s")
        logger.info(f"Max stories per hour: {config.MAX_STORIES_PER_HOUR}")
        logger.info(f"Max stories per day: {config.MAX_STORIES_PER_DAY}")
        logger.info(f"Cooldown after daily limit: {config.COOLDOWN_HOURS} hours")
        logger.info("=" * 60)

        await self.client.start()

        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username}) - ID: {me.id}")
        logger.info("Bot is running and listening for messages...")

        # Keep the bot running
        await self.client.run_until_disconnected()

    async def stop(self):
        """Stop the bot."""
        logger.info("Stopping bot...")
        await self.client.disconnect()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

# Global reference to the bot for health check
_bot_instance = None


async def health_check(request):
    """Health check endpoint for Render web service."""
    global _bot_instance
    if _bot_instance and _bot_instance.client.is_connected():
        return web.Response(text="OK - Bot is running", status=200)
    return web.Response(text="Bot is not connected", status=503)


async def start_http_server():
    """Start the HTTP server for health checks."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Get port from environment (Render sets this)
    port = int(os.environ.get("PORT", 8000))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"HTTP health check server running on port {port}")


async def main():
    """Main entry point."""
    global _bot_instance
    
    # Start HTTP server for health checks
    await start_http_server()
    
    bot = TelegramStoryBot()
    _bot_instance = bot

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
