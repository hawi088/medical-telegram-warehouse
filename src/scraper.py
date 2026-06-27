"""
Telegram Medical Products Scraper
Task 1: Data Scraping and Collection (Extract & Load)

This script scrapes messages and images from Telegram channels
related to Ethiopian medical and pharmaceutical products.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any
import re

from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
from telethon.errors import FloodWaitError, RPCError
from dotenv import load_dotenv
from tqdm import tqdm
from loguru import logger

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE = os.getenv('TELEGRAM_PHONE', '')
RAW_DATA_PATH = os.getenv('RAW_DATA_PATH', './data/raw')
IMAGES_PATH = os.getenv('IMAGES_PATH', './data/raw/images')
LOGS_PATH = os.getenv('LOGS_PATH', './logs')

# ============================================================================
# Telegram channels to scrape - VERIFIED USERNAMES
# ============================================================================
CHANNELS = [
    # Medical Information channels
    'tenamereja',              # Medical Information- ጤና መረጃ
    'HakimApps_Guideline',     # Hakimed: Medical Resources
    
    # Pharmacy channels
    'lobelia4cosmetics',       # Lobelia pharmacy and cosmetics
    'EPSA_Ethiopia',           # Ethiopian Pharmaceutical Students Association
    'epsaethiopia2012',        # Ethiopian Pharmaceutical Supply Service - EPSS
    
    # Health channels
    'healthinovation',         # Health info & vacancy news (HIVN)
    'ClinicalPharmGuideline',  # Clinical Practice guidelines
    
    # Medical channels
    'tikvahethiopia',          # TIKVAH-ETHIOPIA
    'medinethiopiainsider',    # Med In Ethiopia
]

# Create directories
os.makedirs(RAW_DATA_PATH, exist_ok=True)
os.makedirs(IMAGES_PATH, exist_ok=True)
os.makedirs(LOGS_PATH, exist_ok=True)

# Configure logging
logger.remove()
logger.add(
    f"{LOGS_PATH}/scraper_{{time:YYYY-MM-DD}}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO"
)
logger.add(
    f"{LOGS_PATH}/scraper_errors_{{time:YYYY-MM-DD}}.log",
    rotation="1 day",
    retention="30 days",
    level="ERROR"
)
logger.add(lambda msg: print(msg, end=""), level="INFO")


class TelegramScraper:
    """
    Telegram scraper for medical products channels
    """
    
    def __init__(self, api_id: int, api_hash: str, phone: str):
        """
        Initialize the Telegram scraper
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number for authentication
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client = None
        self.session_name = 'telegram_session'
        
        # Track scraped channels
        self.scraped_channels = {}
        
    async def connect(self):
        """
        Connect to Telegram API
        """
        try:
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash
            )
            await self.client.start(phone=self.phone)
            logger.info("✅ Connected to Telegram API")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """
        Disconnect from Telegram API
        """
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram API")
    
    async def get_channel_entity(self, channel_name: str):
        """
        Get channel entity by username or name
        
        Args:
            channel_name: Channel username or name
            
        Returns:
            Channel entity or None if not found
        """
        try:
            # Try with @ prefix
            entity = await self.client.get_entity(f"@{channel_name}")
            logger.info(f"Found channel: {entity.title}")
            return entity
        except ValueError:
            try:
                # Try searching for the channel
                dialogs = await self.client.get_dialogs()
                for dialog in dialogs:
                    if dialog.is_channel:
                        if channel_name.lower() in dialog.name.lower():
                            logger.info(f"Found channel by name: {dialog.name}")
                            return dialog.entity
            except Exception as e:
                logger.error(f"Error finding channel: {e}")
                return None
        except Exception as e:
            logger.error(f"Error finding channel: {e}")
            return None
    
    async def scrape_channel(
        self, 
        channel_name: str, 
        limit: int = 1000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Scrape messages from a Telegram channel
        """
        logger.info(f"🔄 Scraping channel: {channel_name}")
        
        # Get channel entity
        entity = await self.get_channel_entity(channel_name)
        if not entity:
            logger.error(f"Channel '{channel_name}' not found")
            return []
        
        messages_data = []
        images_downloaded = 0
        
        try:
            # Scrape messages - SIMPLIFIED (no offset_date, no reverse)
            async for message in self.client.iter_messages(
                entity,
                limit=limit
            ):
                # Apply date filters - handle timezone-aware comparison
                if start_date:
                    # Make message.date timezone-aware if needed
                    msg_date = message.date
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    if msg_date < start_date:
                        continue
                
                if end_date:
                    msg_date = message.date
                    if msg_date.tzinfo is None:
                        msg_date = msg_date.replace(tzinfo=timezone.utc)
                    if msg_date > end_date:
                        continue
                
                # Extract message data
                message_dict = self._extract_message_data(
                    message, 
                    channel_name,
                    entity.title
                )
                messages_data.append(message_dict)
                
                # Download image if present
                if message.media and isinstance(message.media, MessageMediaPhoto):
                    image_path = await self._download_image(
                        message,
                        channel_name,
                        entity.title
                    )
                    if image_path:
                        messages_data[-1]['image_path'] = image_path
                        messages_data[-1]['image_downloaded'] = True
                        images_downloaded += 1
                
                # Log progress
                if len(messages_data) % 100 == 0:
                    logger.info(f"  Scraped {len(messages_data)} messages")
            
        except FloodWaitError as e:
            logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
        except RPCError as e:
            logger.error(f"RPC Error: {e}")
        except Exception as e:
            logger.error(f"Error scraping {channel_name}: {e}")
        
        logger.info(f"✅ Scraped {len(messages_data)} messages from {channel_name}")
        logger.info(f"  📸 Downloaded {images_downloaded} images")
        
        return messages_data
    
    def _extract_message_data(
        self, 
        message, 
        channel_username: str,
        channel_title: str
    ) -> Dict:
        """
        Extract structured data from a Telegram message
        """
        data = {
            'message_id': message.id,
            'channel_name': channel_title,
            'channel_username': channel_username,
            'message_date': message.date.isoformat() if message.date else None,
            'message_text': message.text or '',
            'views': message.views if hasattr(message, 'views') else 0,
            'forwards': message.forwards if hasattr(message, 'forwards') else 0,
            'has_media': bool(message.media),
            'media_type': None,
            'image_path': None,
            'image_downloaded': False,
            'reply_to': message.reply_to_msg_id if message.reply_to_msg_id else None,
            'raw_data': str(message)
        }
        
        # Determine media type
        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                data['media_type'] = 'photo'
            else:
                data['media_type'] = 'other'
        
        return data
    
    async def _download_image(
        self,
        message,
        channel_name: str,
        channel_title: str
    ) -> Optional[str]:
        """
        Download image from a message
        """
        try:
            # Create channel directory
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', channel_title)
            channel_dir = os.path.join(IMAGES_PATH, safe_name)
            os.makedirs(channel_dir, exist_ok=True)
            
            # Create filename
            filename = f"{message.id}.jpg"
            filepath = os.path.join(channel_dir, filename)
            
            # Check if image already exists
            if os.path.exists(filepath):
                logger.debug(f"Image already exists: {filepath}")
                return filepath
            
            # Download image
            path = await message.download_media(file=filepath)
            
            if path:
                logger.debug(f"Downloaded image: {path}")
                return path
            else:
                logger.warning(f"Failed to download image for message {message.id}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    async def scrape_all_channels(
        self,
        limit: int = 1000,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[Dict]]:
        """
        Scrape all configured channels
        """
        results = {}
        
        for channel in CHANNELS:
            try:
                messages = await self.scrape_channel(
                    channel,
                    limit=limit,
                    start_date=start_date,
                    end_date=end_date
                )
                results[channel] = messages
                
                # Save data after each channel
                self._save_channel_data(channel, messages)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to scrape {channel}: {e}")
                results[channel] = []
        
        return results
    
    def _save_channel_data(self, channel_name: str, messages: List[Dict]):
        """
        Save scraped data for a channel
        """
        if not messages:
            logger.warning(f"No data to save for {channel_name}")
            return
        
        # Create date-based directory structure
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(RAW_DATA_PATH, 'telegram_messages', today)
        os.makedirs(date_dir, exist_ok=True)
        
        # Save as JSON
        filename = f"{channel_name}.json"
        filepath = os.path.join(date_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Saved {len(messages)} messages to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save data for {channel_name}: {e}")
    
    async def scrape_recent_messages(
        self,
        days_back: int = 90,
        limit_per_channel: int = 1000
    ):
        """
        Scrape recent messages from all channels
        """
        # Make dates timezone-aware
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"📅 Scraping messages from {start_date.date()} to {end_date.date()}")
        
        results = await self.scrape_all_channels(
            limit=limit_per_channel,
            start_date=start_date,
            end_date=end_date
        )
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("📊 SCRAPING SUMMARY")
        logger.info("="*60)
        for channel, messages in results.items():
            logger.info(f"{channel}: {len(messages)} messages")
        
        return results


async def main():
    """
    Main function to run the scraper
    """

    logger.info("="*60)
    logger.info("🏥 TELEGRAM MEDICAL PRODUCTS SCRAPER")
    logger.info("="*60)
    
    # Check credentials
    if not API_ID or not API_HASH:
        logger.error("❌ API credentials not found. Please check .env file")
        return
    
    # Initialize scraper
    scraper = TelegramScraper(API_ID, API_HASH, PHONE)
    
    # Connect to Telegram
    if not await scraper.connect():
        logger.error("❌ Failed to connect to Telegram")
        return
    
    try:
        # Scrape recent messages
        results = await scraper.scrape_recent_messages(
            days_back=90,
            limit_per_channel=1000
        )
        
        logger.info("\n✅ Scraping completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
    
    finally:
        await scraper.disconnect()


if __name__ == "__main__":
    asyncio.run(main())