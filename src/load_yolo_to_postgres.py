"""
Load YOLO detection results to PostgreSQL
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'telegram_warehouse'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

def load_yolo_results():
    """Load YOLO results to PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Create staging table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging.yolo_detections (
            id SERIAL PRIMARY KEY,
            message_id INTEGER,
            image_path TEXT,
            category VARCHAR(50),
            category_confidence FLOAT,
            class_id INTEGER,
            class_name VARCHAR(50),
            confidence FLOAT,
            has_person BOOLEAN,
            has_product BOOLEAN,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # Load CSV data
    csv_path = './data/processed/yolo_detections/yolo_detections.csv'
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f" Loaded {len(df)} detections from CSV")
        
        # Clear existing
        cur.execute("TRUNCATE staging.yolo_detections")
        
        # Insert data
        data = df[['message_id', 'image_path', 'category', 'category_confidence', 
                    'class_id', 'class_name', 'confidence', 'has_person', 'has_product']].values.tolist()
        
        execute_values(
            cur,
            """
            INSERT INTO staging.yolo_detections (
                message_id, image_path, category, category_confidence,
                class_id, class_name, confidence, has_person, has_product
            )
            VALUES %s
            """,
            data
        )
        
        conn.commit()
        print(f"Inserted {len(data)} rows into staging.yolo_detections")
    else:
        print(f" CSV file not found: {csv_path}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    load_yolo_results()