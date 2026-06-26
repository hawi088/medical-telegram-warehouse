# src/find_channels.py
"""
Find and verify Telegram channel usernames
"""

import asyncio
import os
from telethon import TelegramClient
from telethon.errors import UsernameInvalidError, UsernameNotOccupiedError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE = os.getenv('TELEGRAM_PHONE', '')

# Channels to try with different formats
CHANNELS_TO_TRY = [
    # Possible formats for each channel
    ('doctors_online_et', 'doctorsonlineet', 'doctors_online', 'doctorsonline'),
    ('medicalinfoethiopia', 'medical_info_ethiopia', 'medical_ethiopia'),
    ('hakimed_et', 'hakimed', 'hakimed_ethiopia'),
    ('lobelia4cosmetics', 'lobeliacosmetics', 'lobelia_cosmetics'),
    ('med_in_ethiopia', 'medethiopia', 'med_ethiopia'),
    ('efda_et', 'efda', 'efdaethiopia'),
    ('pharmacist_rayid', 'rayidpharmacist', 'rayid'),
    ('rayapharma_et', 'rayapharma', 'raya_pharma'),
]

async def search_channels():
    """Search for channels"""
    client = TelegramClient('search_session', API_ID, API_HASH)
    
    
    print("SEARCHING FOR TELEGRAM CHANNELS")

    
    try:
        await client.start(phone=PHONE)
        print("\n Connected to Telegram\n")
        
        found_channels = []
        
        # First, try to search using the search API
        print(" Searching for channels via search...")
    
        
        search_terms = ['medical', 'pharmacy', 'drug', 'health', 'clinic', 'pharma', 'medicine', 'ethiopia']
        
        for term in search_terms:
            print(f"\nSearching for: {term}")
            try:
                # Search for channels
                dialogs = await client.get_dialogs()
                for dialog in dialogs:
                    if dialog.is_channel and term.lower() in dialog.name.lower():
                        print(f"   Found: {dialog.name}")
                        if dialog.entity.username:
                            print(f"     Username: @{dialog.entity.username}")
                        print(f"     ID: {dialog.id}")
                        found_channels.append({
                            'name': dialog.name,
                            'username': dialog.entity.username,
                            'id': dialog.id
                        })
            except Exception as e:
                print(f"  Error: {e}")
        
    
        print("SUMMARY")

        
        print(f"\n Found {len(found_channels)} channels")
        print("\nChannel list:")
        for ch in found_channels:
            print(f"  - {ch['name']} (@{ch['username']})")
        

       
        print("""
From the search results, update your CHANNELS list with:
- The exact username (without @)
- Example: if found as '@lobeliacosmetics', use 'lobeliacosmetics'
""")
        
    except Exception as e:
        print(f" Error: {e}")
    
    finally:
        await client.disconnect()
        print("\nDisconnected")

if __name__ == "__main__":
    asyncio.run(search_channels())