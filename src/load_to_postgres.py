"""
Load scraped Telegram data to PostgreSQL
Task 2: Data Modeling and Transformation
"""

import os
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import glob
from datetime import datetime

# Load .env from the correct location (project root)
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to project root
project_root = os.path.dirname(script_dir)
env_path = os.path.join(project_root, '.env')

# Load .env
load_dotenv(dotenv_path=env_path)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'telegram_warehouse'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def create_raw_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS raw.telegram_messages (
            id SERIAL PRIMARY KEY,
            message_id INTEGER,
            channel_name VARCHAR(255),
            channel_username VARCHAR(255),
            message_date TIMESTAMP,
            message_text TEXT,
            views INTEGER,
            forwards INTEGER,
            has_media BOOLEAN,
            media_type VARCHAR(50),
            image_path TEXT,
            image_downloaded BOOLEAN,
            reply_to INTEGER,
            raw_data TEXT,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print(" Raw table created/verified")

def load_json_files():
    # Look for data in project root
    data_path = os.path.join(project_root, 'data/raw/telegram_messages/**/*.json')
    files = glob.glob(data_path, recursive=True)
    
    print(f" Found {len(files)} JSON files")
    
    all_messages = []
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                messages = json.load(f)
                all_messages.extend(messages)
                print(f"  Loaded {len(messages)} from {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  Error: {e}")
    
    print(f" Total messages: {len(all_messages)}")
    return all_messages

def insert_messages(messages):
    if not messages:
        print(" No messages to insert")
        return
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("TRUNCATE raw.telegram_messages RESTART IDENTITY")
    
    insert_data = []
    for msg in messages:
        insert_data.append((
            msg.get('message_id'),
            msg.get('channel_name'),
            msg.get('channel_username'),
            msg.get('message_date'),
            msg.get('message_text', ''),
            msg.get('views', 0),
            msg.get('forwards', 0),
            msg.get('has_media', False),
            msg.get('media_type'),
            msg.get('image_path'),
            msg.get('image_downloaded', False),
            msg.get('reply_to'),
            msg.get('raw_data', '')
        ))
    
    execute_values(
        cur,
        """
        INSERT INTO raw.telegram_messages (
            message_id, channel_name, channel_username,
            message_date, message_text, views, forwards,
            has_media, media_type, image_path, image_downloaded,
            reply_to, raw_data
        )
        VALUES %s
        """,
        insert_data
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(insert_data)} messages into raw.telegram_messages")

def main():
    
    create_raw_table()
    messages = load_json_files()
    insert_messages(messages)
    print("\n Data loading complete!")

if __name__ == "__main__":
    main()