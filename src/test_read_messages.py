# src/test_read_messages.py
"""
Test if we can read messages from joined channels
"""

import asyncio
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE = os.getenv('TELEGRAM_PHONE', '')

# Use a channel you've definitely joined
CHANNEL = 'lobelia4cosmetics'

async def test_read():
    client = TelegramClient('test_session', API_ID, API_HASH)
    
    try:
        await client.start(phone=PHONE)
        print("✅ Connected to Telegram\n")
        
        # Get the channel
        entity = await client.get_entity(f"@{CHANNEL}")
        print(f"📢 Channel: {entity.title}")
        print(f"   ID: {entity.id}")
        print(f"   Type: {type(entity).__name__}")
        
        # Try to get messages
        print("\n📨 Fetching messages...")
        messages = []
        
        # Try using different methods
        try:
            print("Method 1: iter_messages with limit")
            async for msg in client.iter_messages(entity, limit=10):
                messages.append(msg)
                print(f"  - {msg.id}: {msg.text[:50] if msg.text else '[No text]'}...")
        except Exception as e1:
            print(f"Method 1 failed: {e1}")
            
            try:
                print("Method 2: get_messages")
                msgs = await client.get_messages(entity, limit=10)
                for msg in msgs:
                    messages.append(msg)
                    print(f"  - {msg.id}: {msg.text[:50] if msg.text else '[No text]'}...")
            except Exception as e2:
                print(f"Method 2 failed: {e2}")
        
        print(f"\n📊 Results: Found {len(messages)} messages")
        
        if len(messages) == 0:
            print("\n⚠️ No messages found! Possible reasons:")
            print("  1. You're not a member of this channel")
            print("  2. The channel is private and you need to be added")
            print("  3. The channel is empty")
            print("  4. API permissions issue")
            print("  5. You're using the wrong account")
            
            # Check if you're a member
            try:
                print("\nChecking membership status...")
                # Try to get the channel full info
                full_channel = await client.get_entity(entity)
                print(f"Channel: {full_channel.title}")
                print(f"Is member: {getattr(full_channel, 'participants_count', 'Unknown')}")
            except Exception as e3:
                print(f"Could not verify membership: {e3}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.disconnect()
        print("\nDisconnected")

if __name__ == "__main__":
    asyncio.run(test_read())