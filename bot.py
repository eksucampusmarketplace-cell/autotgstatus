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

from telethon import TelegramClient, events
from telethon.tl.functions.stories import SendStoryRequest
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

    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE)
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
# STATE MANAGEMENT
# =============================================================================
class StateManager:
    """Manages persistent state including caption history and viewer whitelist."""

    def __init__(self, state_file: str = config.STATE_FILE):
        # Use persistent disk path for Render deployment
        if os.path.exists("/opt/render/project/data"):
            self.state_file = "/opt/render/project/data/state.json"
        else:
            self.state_file = state_file
        self.state = self._load_state()
        self._ensure_defaults()

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
            logger.info(f"Added user {user_id} to viewer whitelist")
            return True
        return False


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
        # Handle string session vs file session
        # For Render deployment, prefer string session for persistence
        if config.STRING_SESSION:
            # Use string session (can be copy-pasted)
            self.client = TelegramClient(
                config.STRING_SESSION,
                config.API_ID,
                config.API_HASH,
            )
        else:
            # Use session file (legacy) with persistent path for Render
            session_file = config.SESSION_FILE
            if os.path.exists("/opt/render/project/data"):
                session_file = "/opt/render/project/data/userbot_session.session"
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
            """Handle all new messages - for whitelist and group monitoring."""
            # Check if this is a private message (DM) for whitelist
            if event.is_private:
                await self._handle_private_message(event)
                return

            # Check if this is the watched group
            if await self._is_watched_group(event):
                await self._handle_group_message(event)

    async def _handle_private_message(self, event):
        """Handle private messages - add sender to whitelist and send welcome message."""
        sender = await event.get_sender()
        if isinstance(sender, User):
            user_id = sender.id
            username = sender.username or "N/A"
            first_name = sender.first_name or "User"

            added = self.state_manager.add_viewer_to_whitelist(user_id)
            if added:
                logger.info(f"New DM from user {user_id} (@{username}) - added to whitelist")
                
                # Send welcome message to new user
                if config.NEW_USER_MESSAGE:
                    try:
                        # Replace {name} placeholder with user's first name
                        welcome_msg = config.NEW_USER_MESSAGE.replace("{name}", first_name)
                        await event.respond(welcome_msg)
                        logger.info(f"Sent welcome message to user {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to send welcome message: {e}")
            else:
                logger.debug(f"DM from known user {user_id} (@{username})")

    async def _is_watched_group(self, event) -> bool:
        """Check if the message is from the watched group."""
        try:
            chat = await event.get_chat()
            watch_group = config.WATCH_GROUP

            # Handle numeric chat ID
            if isinstance(watch_group, int) or (
                isinstance(watch_group, str) and watch_group.lstrip("-").isdigit()
            ):
                watch_group_id = int(watch_group)
                return hasattr(chat, "id") and chat.id == watch_group_id

            # Handle username
            if hasattr(chat, "username") and chat.username:
                return chat.username.lower() == watch_group.lower().lstrip("@")

            # Handle title
            if hasattr(chat, "title"):
                return chat.title == watch_group

        except Exception as e:
            logger.error(f"Error checking watched group: {e}")

        return False

    async def _handle_group_message(self, event):
        """Handle messages from the watched group."""
        # Only process image messages
        if not event.message.media:
            logger.debug("Ignoring non-media message")
            return

        if not isinstance(event.message.media, MessageMediaPhoto):
            logger.debug("Ignoring non-photo media message")
            return

        logger.info(f"New image detected in watched group (msg_id: {event.message.id})")

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
            # Resolve whitelist users
            allowed_users = await self._resolve_whitelist_users()

            if not allowed_users:
                logger.warning("No valid users in whitelist - story will be posted with default privacy")

            # Create privacy rule
            privacy_rules = [InputPrivacyValueAllowUsers(users=allowed_users)] if allowed_users else []

            # Upload the image
            file = await self.client.upload_file(image_bytes)

            # Post the story
            result = await self.client(
                SendStoryRequest(
                    media=InputMediaUploadedPhoto(file=file),
                    privacy_rules=privacy_rules,
                    noforwards=False,
                )
            )

            logger.info(f"Story posted successfully! Story ID: {result.id}")

        except Exception as e:
            logger.error(f"Failed to post story: {e}", exc_info=True)

    async def start(self):
        """Start the bot."""
        logger.info("Starting Telegram Story Userbot...")
        logger.info(f"Session type: {'string session' if config.STRING_SESSION else 'file session'}")
        logger.info(f"Watch group: {config.WATCH_GROUP}")
        logger.info(f"Viewer whitelist count: {len(self.state_manager.get_viewer_whitelist())}")
        logger.info(f"Available captions: {len(config.CAPTIONS)}")
        logger.info(f"Min caption gap: {config.MIN_CAPTION_GAP}")
        logger.info(f"New user message: {'enabled' if config.NEW_USER_MESSAGE else 'disabled'}")

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
async def main():
    """Main entry point."""
    bot = TelegramStoryBot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
