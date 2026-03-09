"""
WhatsApp Bot with Intelligent Follow-ups
Tracks lead engagement and sends appropriate follow-up messages based on behavior.

Flow:
1. Send pitch message to lead
2. Track: message sent time, read status, reply status, online status
3. Based on behavior, send appropriate follow-up:
   - Stage 0: Online but message not opened → Filter check message
   - Stage 1: Read but no reply (20-28h) → Value gap message
   - Stage 2: Still silent → Risk concern message  
   - Stage 3: Final follow-up → Dormant
"""

import os
import sys
import json
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
from zoneinfo import ZoneInfo

from aiohttp import web
import pytz

# Configure logging
def setup_logging():
    """Set up logging to both console and file."""
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Log file path
    is_render = os.path.exists("/opt/render")
    if is_render:
        log_file = "/opt/render/project/data/whatsapp_bot.log"
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


import config
logger = setup_logging()


# =============================================================================
# ENUMS
# =============================================================================
class FollowUpStage(int, Enum):
    """Follow-up stages for leads."""
    NONE = 0           # Just sent pitch, no follow-up needed yet
    STAGE_0 = 1        # Online but message not opened
    STAGE_1 = 2        # Read message, went silent (value gap)
    STAGE_2 = 3        # Still silent after Stage 1 (risk concern)
    STAGE_3 = 4        # Final follow-up
    DORMANT = 5        # No more automatic messages


class LeadStatus(str, Enum):
    """Lead status in the system."""
    ACTIVE = "active"
    REPLIED = "replied"
    CONVERTED = "converted"
    DORMANT = "dormant"


# =============================================================================
# SUPABASE CLIENT
# =============================================================================
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.error("Supabase credentials not configured!")
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
# LEAD MANAGEMENT
# =============================================================================
class LeadManager:
    """Manages leads in Supabase with tracking of all engagement metrics."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        if not self.supabase:
            raise RuntimeError("Supabase not configured. Lead tracking requires Supabase.")
        
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create leads table if it doesn't exist."""
        try:
            # Try to create table (will fail gracefully if exists)
            self.supabase.execute_raw("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    phone_number VARCHAR(50) UNIQUE NOT NULL,
                    first_name VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'active',
                    followup_stage INTEGER DEFAULT 0,
                    pitch_sent_at TIMESTAMP WITH TIME ZONE,
                    message_read_at TIMESTAMP WITH TIME ZONE,
                    replied_at TIMESTAMP WITH TIME ZONE,
                    converted_at TIMESTAMP WITH TIME ZONE,
                    last_followup_at TIMESTAMP WITH TIME ZONE,
                    next_followup_at TIMESTAMP WITH TIME ZONE,
                    online_status VARCHAR(50) DEFAULT 'offline',
                    last_seen_at TIMESTAMP WITH TIME ZONE,
                    is_online BOOLEAN DEFAULT FALSE,
                    they_replied BOOLEAN DEFAULT FALSE,
                    converted BOOLEAN DEFAULT FALSE,
                    amount_mentioned VARCHAR(50),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            logger.info("Leads table ready")
        except Exception as e:
            logger.warning(f"Table creation note: {e}")
    
    def create_lead(self, phone_number: str, first_name: str = None) -> Dict[str, Any]:
        """Create a new lead or return existing one."""
        try:
            # Check if lead exists
            existing = self.supabase.table("leads").select("*").eq("phone_number", phone_number).execute()
            
            if existing.data:
                logger.info(f"Lead {phone_number} already exists")
                return existing.data[0]
            
            # Create new lead
            lead_data = {
                "phone_number": phone_number,
                "first_name": first_name or "there",
                "status": LeadStatus.ACTIVE.value,
                "followup_stage": FollowUpStage.NONE.value,
                "pitch_sent_at": datetime.now(pytz.UTC).isoformat(),
                "they_replied": False,
                "converted": False,
            }
            
            result = self.supabase.table("leads").insert(lead_data).execute()
            logger.info(f"Created new lead: {phone_number}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating lead: {e}")
            return None
    
    def get_lead(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get lead by phone number."""
        try:
            result = self.supabase.table("leads").select("*").eq("phone_number", phone_number).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting lead: {e}")
            return None
    
    def update_lead(self, phone_number: str, data: Dict[str, Any]) -> bool:
        """Update lead data."""
        try:
            data["updated_at"] = datetime.now(pytz.UTC).isoformat()
            self.supabase.table("leads").update(data).eq("phone_number", phone_number).execute()
            logger.info(f"Updated lead {phone_number}: {list(data.keys())}")
            return True
        except Exception as e:
            logger.error(f"Error updating lead: {e}")
            return False
    
    def mark_message_read(self, phone_number: str, amount_mentioned: str = None) -> bool:
        """Mark that the lead has read a message."""
        lead = self.get_lead(phone_number)
        if not lead:
            return False
        
        update_data = {
            "message_read_at": datetime.now(pytz.UTC).isoformat(),
            "is_online": False,  # They were online to read it
        }
        
        if amount_mentioned:
            update_data["amount_mentioned"] = amount_mentioned
        
        return self.update_lead(phone_number, update_data)
    
    def mark_online(self, phone_number: str) -> bool:
        """Mark lead as online."""
        return self.update_lead(phone_number, {
            "is_online": True,
            "online_status": "online",
            "last_seen_at": datetime.now(pytz.UTC).isoformat(),
        })
    
    def mark_offline(self, phone_number: str) -> bool:
        """Mark lead as offline."""
        lead = self.get_lead(phone_number)
        if lead and lead.get("is_online"):
            return self.update_lead(phone_number, {
                "is_online": False,
                "online_status": "offline",
            })
        return True
    
    def mark_replied(self, phone_number: str) -> bool:
        """Mark that lead has replied. Stop all follow-ups."""
        return self.update_lead(phone_number, {
            "they_replied": True,
            "replied_at": datetime.now(pytz.UTC).isoformat(),
            "status": LeadStatus.REPLIED.value,
            "next_followup_at": None,  # Cancel scheduled follow-ups
        })
    
    def mark_converted(self, phone_number: str) -> bool:
        """Mark lead as converted. Stop all follow-ups permanently."""
        return self.update_lead(phone_number, {
            "converted": True,
            "converted_at": datetime.now(pytz.UTC).isoformat(),
            "status": LeadStatus.CONVERTED.value,
            "next_followup_at": None,
        })
    
    def advance_followup_stage(self, phone_number: str) -> int:
        """Advance to next follow-up stage. Returns new stage."""
        lead = self.get_lead(phone_number)
        if not lead:
            return -1
        
        current_stage = lead.get("followup_stage", 0)
        
        # Stop if already replied or converted
        if lead.get("they_replied") or lead.get("converted"):
            return current_stage
        
        # Advance stage
        new_stage = current_stage + 1
        
        # Cap at max stages
        if new_stage > config.MAX_FOLLOWUP_STAGES:
            # Mark as dormant
            self.update_lead(phone_number, {
                "followup_stage": FollowUpStage.DORMANT.value,
                "status": LeadStatus.DORMANT.value,
                "next_followup_at": None,
            })
            return FollowUpStage.DORMANT.value
        
        # Update stage and schedule next follow-up
        next_followup = self._calculate_next_followup_time()
        
        self.update_lead(phone_number, {
            "followup_stage": new_stage,
            "last_followup_at": datetime.now(pytz.UTC).isoformat(),
            "next_followup_at": next_followup.isoformat(),
        })
        
        logger.info(f"Lead {phone_number} advanced to stage {new_stage}")
        return new_stage
    
    def _calculate_next_followup_time(self) -> datetime:
        """Calculate random follow-up time between 20-28 hours from now."""
        hours_to_add = random.randint(config.FOLLOWUP_MIN_HOURS, config.FOLLOWUP_MAX_HOURS)
        next_time = datetime.now(pytz.UTC) + timedelta(hours=hours_to_add)
        
        # Check if it falls in quiet hours (12am-7am US time)
        next_time = self._adjust_for_quiet_hours(next_time)
        
        return next_time
    
    def _adjust_for_quiet_hours(self, dt: datetime) -> datetime:
        """Adjust datetime to avoid quiet hours (12am-7am US time)."""
        us_tz = ZoneInfo("America/New_York")
        
        # Convert to US time
        us_time = dt.astimezone(us_tz)
        hour = us_time.hour
        
        # If in quiet hours, move to 7am US time
        if config.QUIET_HOURS_START <= hour < config.QUIET_HOURS_END:
            # Move to 7am the same day (or next day if already past 7am)
            target_date = us_time.date()
            if hour >= config.QUIET_HOURS_END:
                target_date = target_date + timedelta(days=1)
            
            # Set to 7am US time
            new_us_time = us_time.replace(
                year=target_date.year,
                month=target_date.month,
                day=target_date.day,
                hour=config.QUIET_HOURS_END,
                minute=0,
                second=0,
            )
            
            # Convert back to UTC
            return new_us_time.astimezone(pytz.UTC)
        
        return dt
    
    def get_pending_followups(self) -> list:
        """Get leads that need follow-up messages now."""
        try:
            now = datetime.now(pytz.UTC).isoformat()
            
            result = self.supabase.table("leads").select("*").execute()
            pending = []
            
            for lead in result.data:
                # Skip if replied, converted, or dormant
                if lead.get("they_replied") or lead.get("converted"):
                    continue
                
                if lead.get("status") == LeadStatus.DORMANT.value:
                    continue
                
                # Check if it's time for follow-up
                next_followup = lead.get("next_followup_at")
                if next_followup:
                    next_dt = datetime.fromisoformat(next_followup.replace("Z", "+00:00"))
                    now_dt = datetime.now(pytz.UTC)
                    
                    if now_dt >= next_dt:
                        pending.append(lead)
            
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending follow-ups: {e}")
            return []


# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================
class MessageTemplates:
    """Follow-up message templates."""
    
    @staticmethod
    def get_stage0_message(first_name: str) -> str:
        """Stage 0: Online but message not opened."""
        return config.STAGE0_MESSAGE.format(first_name=first_name)
    
    @staticmethod
    def get_stage1_message(first_name: str, amount_seen: str = None) -> str:
        """Stage 1: Read message, went silent."""
        if amount_seen and "50" in amount_seen:
            return config.STAGE1B_MESSAGE.format(first_name=first_name)
        return config.STAGE1A_MESSAGE.format(first_name=first_name)
    
    @staticmethod
    def get_stage2_message(first_name: str) -> str:
        """Stage 2: Still silent (uses same as stage 1 but more urgent)."""
        # Could be different based on what was sent before
        return config.STAGE1B_MESSAGE.format(first_name=first_name)
    
    @staticmethod
    def get_stage3_message(first_name: str) -> str:
        """Stage 3: Final follow-up."""
        return config.STAGE3_MESSAGE.format(first_name=first_name)
    
    @staticmethod
    def get_pitch_message(first_name: str) -> str:
        """Initial pitch message."""
        return config.PITCH_MESSAGE.format(first_name=first_name)


# =============================================================================
# WHATSAPP MESSENGER
# =============================================================================
class WhatsAppMessenger:
    """Handles sending WhatsApp messages via Twilio or Meta API."""
    
    def __init__(self):
        self.twilio_client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client if configured."""
        if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.warning(f"Twilio not available: {e}")
    
    async def send_message(self, to: str, message: str) -> bool:
        """Send a WhatsApp message."""
        formatted_to = self._format_phone_number(to)
        
        try:
            if self.twilio_client:
                return await self._send_via_twilio(formatted_to, message)
            else:
                # Fallback: log the message (for testing)
                logger.info(f"[WOULD SEND] To {formatted_to}: {message[:50]}...")
                return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp."""
        # Remove any spaces/dashes
        phone = phone.strip().replace(" ", "").replace("-", "")
        
        # Add country code if missing (assume US +1)
        if not phone.startswith("+"):
            if len(phone) == 10:
                phone = "+1" + phone
            else:
                phone = "+" + phone
        
        return f"whatsapp:{phone}"
    
    async def _send_via_twilio(self, to: str, message: str) -> bool:
        """Send message via Twilio."""
        try:
            # Twilio is sync, run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.twilio_client.messages.create(
                    from_=config.TWILIO_PHONE_NUMBER,
                    body=message,
                    to=to
                )
            )
            logger.info(f"Message sent via Twilio to {to}")
            return True
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            return False
    
    async def send_followup(self, lead: Dict[str, Any]) -> bool:
        """Send appropriate follow-up based on stage."""
        first_name = lead.get("first_name", "there")
        stage = lead.get("followup_stage", 0)
        amount_seen = lead.get("amount_mentioned")
        
        # Get message based on stage
        if stage == FollowUpStage.STAGE_0.value:
            message = MessageTemplates.get_stage0_message(first_name)
        elif stage == FollowUpStage.STAGE_1.value:
            message = MessageTemplates.get_stage1_message(first_name, amount_seen)
        elif stage == FollowUpStage.STAGE_2.value:
            message = MessageTemplates.get_stage2_message(first_name)
        elif stage == FollowUpStage.STAGE_3.value:
            message = MessageTemplates.get_stage3_message(first_name)
        else:
            logger.warning(f"Unknown stage {stage} for lead {lead.get('phone_number')}")
            return False
        
        phone = lead.get("phone_number")
        return await self.send_message(phone, message)


# =============================================================================
# FOLLOW-UP SCHEDULER
# =============================================================================
class FollowUpScheduler:
    """Schedules and processes follow-up messages."""
    
    def __init__(self):
        self.lead_manager = LeadManager()
        self.messenger = WhatsAppMessenger()
        self.check_interval = 60  # Check every minute
    
    async def start(self):
        """Start the follow-up scheduler."""
        logger.info("Starting follow-up scheduler...")
        
        while True:
            try:
                await self.process_followups()
            except Exception as e:
                logger.error(f"Error in follow-up scheduler: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def process_followups(self):
        """Process pending follow-ups."""
        pending = self.lead_manager.get_pending_followups()
        
        for lead in pending:
            phone = lead.get("phone_number")
            logger.info(f"Processing follow-up for {phone} at stage {lead.get('followup_stage')}")
            
            # Send the follow-up message
            success = await self.messenger.send_followup(lead)
            
            if success:
                # Advance to next stage
                new_stage = self.lead_manager.advance_followup_stage(phone)
                logger.info(f"Follow-up sent to {phone}, advanced to stage {new_stage}")
            else:
                logger.error(f"Failed to send follow-up to {phone}")


# =============================================================================
# INCOMING MESSAGE HANDLER
# =============================================================================
class WhatsAppWebhookHandler:
    """Handles incoming WhatsApp messages and status updates."""
    
    def __init__(self):
        self.lead_manager = LeadManager()
        self.messenger = WhatsAppMessenger()
    
    async def handle_incoming_message(self, data: Dict[str, Any]) -> Optional[str]:
        """Handle incoming WhatsApp message."""
        # Extract message data based on Twilio or Meta format
        phone = self._extract_phone(data)
        message_text = self._extract_message(data)
        
        if not phone:
            logger.warning("Could not extract phone from message")
            return None
        
        # Get or create lead
        lead = self.lead_manager.get_lead(phone)
        if not lead:
            # Extract name if available
            first_name = self._extract_name(data) or "there"
            lead = self.lead_manager.create_lead(phone, first_name)
        
        # Mark as replied (stop follow-ups)
        self.lead_manager.mark_replied(phone)
        
        logger.info(f"Lead {phone} replied: {message_text[:50]}...")
        
        # Check for conversion keywords
        if self._is_conversion(message_text):
            self.lead_manager.mark_converted(phone)
        
        # Process the message (could integrate with AI/automation here)
        response = await self._generate_response(message_text, lead)
        
        if response:
            await self.messenger.send_message(phone, response)
        
        return phone
    
    async def handle_status_update(self, data: Dict[str, Any]) -> None:
        """Handle WhatsApp status updates (read receipts, online status)."""
        phone = self._extract_phone(data)
        status = self._extract_status(data)
        
        if not phone:
            return
        
        if status == "read":
            # Extract if a specific amount was mentioned
            amount = self._extract_amount_from_context(phone)
            self.lead_manager.mark_message_read(phone, amount)
            logger.info(f"Lead {phone} read message")
        
        elif status == "delivered":
            logger.debug(f"Message delivered to {phone}")
        
        elif status == "sent":
            logger.debug(f"Message sent to {phone}")
    
    async def handle_presence(self, data: Dict[str, Any]) -> None:
        """Handle presence/online status updates."""
        phone = self._extract_phone(data)
        is_online = self._extract_online_status(data)
        
        if not phone:
            return
        
        if is_online:
            self.lead_manager.mark_online(phone)
            logger.info(f"Lead {phone} is online")
        else:
            self.lead_manager.mark_offline(phone)
    
    def _extract_phone(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from message data."""
        # Twilio format
        if "From" in data:
            return data["From"].replace("whatsapp:", "")
        
        # Meta API format
        if "entry" in data:
            try:
                changes = data["entry"][0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    if messages:
                        return messages[0].get("from")
            except (IndexError, KeyError):
                pass
        
        return None
    
    def _extract_message(self, data: Dict[str, Any]) -> str:
        """Extract message text."""
        # Twilio format
        if "Body" in data:
            return data["Body"]
        
        # Meta API format
        if "entry" in data:
            try:
                changes = data["entry"][0].get("changes", [])
                if changes:
                    value = changes[0].get("value", {})
                    messages = value.get("messages", [])
                    if messages:
                        return messages[0].get("text", {}).get("body", "")
            except (IndexError, KeyError):
                pass
        
        return ""
    
    def _extract_name(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract sender name."""
        # Twilio format
        if "ProfileName" in data:
            return data["ProfileName"]
        
        # Could be extracted from contacts API
        return None
    
    def _extract_status(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract message status."""
        # Twilio format
        if "MessageStatus" in data:
            return data["MessageStatus"]
        
        # Meta API has read receipts in a different format
        return None
    
    def _extract_online_status(self, data: Dict[str, Any]) -> bool:
        """Extract online status."""
        # Presence updates would come from WhatsApp Business API
        return data.get("presence", False)
    
    def _extract_amount_from_context(self, phone: str) -> Optional[str]:
        """Extract what amount the lead saw before going silent."""
        lead = self.lead_manager.get_lead(phone)
        if lead:
            return lead.get("amount_mentioned")
        return None
    
    def _is_conversion(self, message: str) -> bool:
        """Check if message indicates conversion."""
        conversion_keywords = [
            "i'm in", "im in", "count me in", "sign me up",
            "yes", "interested", "let's do it", "let's go",
            "deposit", "pay", "send details", "ready to start"
        ]
        return any(kw in message.lower() for kw in conversion_keywords)
    
    async def _generate_response(self, message: str, lead: Dict) -> Optional[str]:
        """Generate automated response to lead."""
        # This could integrate with AI or be custom logic
        # For now, just acknowledge
        return None  # Let human handle responses


# =============================================================================
# HTTP HANDLERS
# =============================================================================
webhook_handler = WhatsAppWebhookHandler()


async def webhook(request):
    """Handle incoming WhatsApp webhooks."""
    try:
        data = await request.json()
        
        # Check if it's a status update or message
        if "MessageStatus" in data or data.get("SmsStatus"):
            # Status callback (Twilio)
            await webhook_handler.handle_status_update(data)
        
        elif "entry" in data:
            # Meta WhatsApp API format
            changes = data.get("entry", [{}])[0].get("changes", [{}])
            if changes:
                value = changes[0].get("value", {})
                
                # Check for messages
                if value.get("messages"):
                    await webhook_handler.handle_incoming_message(data)
                
                # Check for status updates (read receipts)
                if value.get("statuses"):
                    await webhook_handler.handle_status_update(data)
        
        elif "Body" in data:
            # Incoming message (Twilio format)
            await webhook_handler.handle_incoming_message(data)
        
        return web.Response(text="OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(text="Error", status=500)


async def health_check(request):
    """Health check endpoint."""
    return web.Response(text="OK", status=200)


# =============================================================================
# MAIN APPLICATION
# =============================================================================
async def create_app():
    """Create the aiohttp application."""
    app = web.Application()
    
    # Webhook endpoint
    app.router.add_post("/webhook", webhook)
    app.router.add_get("/webhook", health_check)
    app.router.add_get("/health", health_check)
    
    return app


async def start_followup_scheduler():
    """Start the background follow-up scheduler."""
    scheduler = FollowUpScheduler()
    await scheduler.start()


async def main():
    """Main entry point."""
    # Get port from environment
    port = int(os.environ.get("PORT", 8000))
    
    # Start follow-up scheduler in background
    scheduler_task = asyncio.create_task(start_followup_scheduler())
    
    # Start HTTP server
    app = await create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logger.info(f"WhatsApp bot running on port {port}")
    logger.info("Endpoints:")
    logger.info(f"  POST /webhook - WhatsApp webhook")
    logger.info(f"  GET  /health  - Health check")
    
    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
