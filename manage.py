"""
WhatsApp Bot Management CLI
Use this to manually interact with leads and test the bot.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from whatsapp_bot import LeadManager, WhatsAppMessenger, WhatsAppWebhookHandler


async def list_leads():
    """List all leads."""
    manager = LeadManager()
    supabase = manager.supabase
    
    result = supabase.table("leads").select("*").order("created_at", desc=True).execute()
    
    print("\n" + "=" * 80)
    print("LEADS LIST")
    print("=" * 80)
    
    if not result.data:
        print("No leads found.")
        return
    
    for lead in result.data:
        print(f"\n📱 {lead['phone_number']}")
        print(f"   Name: {lead['first_name']}")
        print(f"   Status: {lead['status']}")
        print(f"   Stage: {lead['followup_stage']}")
        print(f"   Replied: {'✅' if lead['they_replied'] else '❌'}")
        print(f"   Converted: {'✅' if lead['converted'] else '❌'}")
        
        if lead['pitch_sent_at']:
            print(f"   Pitch sent: {lead['pitch_sent_at'][:19]}")
        if lead['message_read_at']:
            print(f"   Read at: {lead['message_read_at'][:19]}")
        if lead['replied_at']:
            print(f"   Replied at: {lead['replied_at'][:19]}")
        if lead['next_followup_at']:
            print(f"   Next follow-up: {lead['next_followup_at'][:19]}")
    
    print("\n" + "=" * 80)
    print(f"Total leads: {len(result.data)}")
    print("=" * 80)


async def add_lead(phone: str, first_name: str = None):
    """Add a new lead."""
    manager = LeadManager()
    
    name = first_name or input(f"Enter first name for {phone}: ").strip()
    
    lead = manager.create_lead(phone, name)
    
    if lead:
        print(f"✅ Added lead: {phone} ({name})")
    else:
        print(f"❌ Failed to add lead: {phone}")


async def send_pitch(phone: str):
    """Send pitch message to a lead."""
    manager = LeadManager()
    messenger = WhatsAppMessenger()
    
    lead = manager.get_lead(phone)
    if not lead:
        print(f"❌ Lead not found: {phone}")
        return
    
    first_name = lead.get("first_name", "there")
    message = config.PITCH_MESSAGE.format(first_name=first_name)
    
    success = await messenger.send_message(phone, message)
    
    if success:
        manager.update_lead(phone, {
            "pitch_sent_at": datetime.now(pytz.UTC).isoformat()
        })
        print(f"✅ Pitch sent to {phone}")
    else:
        print(f"❌ Failed to send pitch to {phone}")


async def send_manual_message(phone: str, message: str):
    """Send a manual message to a lead."""
    messenger = WhatsAppMessenger()
    
    success = await messenger.send_message(phone, message)
    
    if success:
        print(f"✅ Message sent to {phone}")
    else:
        print(f"❌ Failed to send message to {phone}")


async def mark_replied(phone: str):
    """Mark a lead as having replied."""
    manager = LeadManager()
    
    success = manager.mark_replied(phone)
    
    if success:
        print(f"✅ Marked {phone} as replied")
    else:
        print(f"❌ Failed to mark {phone}")


async def mark_converted(phone: str):
    """Mark a lead as converted."""
    manager = LeadManager()
    
    success = manager.mark_converted(phone)
    
    if success:
        print(f"✅ Marked {phone} as converted")
    else:
        print(f"❌ Failed to mark {phone}")


async def test_followup(phone: str):
    """Test sending a follow-up to a lead."""
    manager = LeadManager()
    messenger = WhatsAppMessenger()
    
    lead = manager.get_lead(phone)
    if not lead:
        print(f"❌ Lead not found: {phone}")
        return
    
    success = await messenger.send_followup(lead)
    
    if success:
        print(f"✅ Test follow-up sent to {phone}")
    else:
        print(f"❌ Failed to send test follow-up to {phone}")


def print_help():
    """Print help message."""
    print("""
WhatsApp Bot Management CLI

Commands:
  list                           List all leads
  add <phone> [name]              Add a new lead
  pitch <phone>                  Send pitch message to lead
  send <phone> <message>         Send manual message to lead
  replied <phone>                Mark lead as replied
  converted <phone>             Mark lead as converted
  test-followup <phone>          Test follow-up message
  help                           Show this help

Examples:
  python manage.py list
  python manage.py add +1234567890 John
  python manage.py send +1234567890 "Hey John, checking in!"
""")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        await list_leads()
    
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: python manage.py add <phone> [name]")
            return
        phone = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else None
        await add_lead(phone, name)
    
    elif command == "pitch":
        if len(sys.argv) < 3:
            print("Usage: python manage.py pitch <phone>")
            return
        await send_pitch(sys.argv[2])
    
    elif command == "send":
        if len(sys.argv) < 4:
            print("Usage: python manage.py send <phone> <message>")
            return
        phone = sys.argv[2]
        message = " ".join(sys.argv[3:])
        await send_manual_message(phone, message)
    
    elif command == "replied":
        if len(sys.argv) < 3:
            print("Usage: python manage.py replied <phone>")
            return
        await mark_replied(sys.argv[2])
    
    elif command == "converted":
        if len(sys.argv) < 3:
            print("Usage: python manage.py converted <phone>")
            return
        await mark_converted(sys.argv[2])
    
    elif command == "test-followup":
        if len(sys.argv) < 3:
            print("Usage: python manage.py test-followup <phone>")
            return
        await test_followup(sys.argv[2])
    
    elif command == "help":
        print_help()
    
    else:
        print(f"Unknown command: {command}")
        print_help()


if __name__ == "__main__":
    from datetime import datetime
    import pytz
    
    asyncio.run(main())
