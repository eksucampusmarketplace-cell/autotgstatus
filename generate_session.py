#!/usr/bin/env python3
"""
String Session Generator
========================
This script helps generate a string session that you can copy-paste 
into your config.py file instead of using a session file.

Usage:
    python generate_session.py

Then paste the generated string session into config.py:
    STRING_SESSION = "1AAAA..."
"""

import asyncio
import config


async def generate_session():
    """Generate a string session for the bot."""
    print("=" * 60)
    print("String Session Generator")
    print("=" * 60)
    print()
    
    # Create client with a temporary session name
    client = TelegramClient("temp_session", config.API_ID, config.API_HASH)
    
    await client.start(phone=config.PHONE_NUMBER)
    
    # Generate the string session
    session_string = client.session.save()
    
    print()
    print("=" * 60)
    print("YOUR STRING SESSION:")
    print("=" * 60)
    print()
    print(session_string)
    print()
    print("=" * 60)
    print()
    print("Copy the string above and paste it into config.py:")
    print()
    print(f'    STRING_SESSION = "{session_string}"')
    print()
    print("Then delete or comment out SESSION_FILE if using string session only.")
    print()
    
    await client.disconnect()


if __name__ == "__main__":
    from telethon import TelegramClient
    asyncio.run(generate_session())
