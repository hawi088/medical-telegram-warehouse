"""
YOLO Object Detection for Telegram Images
Task 3: Data Enrichment with Object Detection

This script:
1. Scans for images downloaded in Task 1
2. Runs YOLOv8 detection on each image
3. Records detected objects with confidence scores
4. Saves results to CSV
5. Categorizes images based on detected objects
"""

import os
import cv2
import glob
import json
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from ultralytics import YOLO
from dotenv import load_dotenv
import logging

# Load environment
load_dotenv()

# Configuration
IMAGES_PATH = os.getenv('IMAGES_PATH', './data/raw/images')
OUTPUT_PATH = './data/processed/yolo_detections'
os.makedirs(OUTPUT_PATH, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/yolo_detection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# YOLO class mappings (COCO dataset)
YOLO_CLASSES = {
    0: 'person',
    1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
    5: 'bus', 6: 'train', 7: 'truck', 8: 'boat',
    9: 'traffic light', 10: 'fire hydrant', 11: 'stop sign',
    12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat',
    16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow',
    20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe',
    24: 'backpack', 25: 'umbrella', 26: 'handbag', 27: 'tie',
    28: 'suitcase', 29: 'frisbee', 30: 'skis', 31: 'snowboard',
    32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove',
    36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle',
    40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife',
    44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple',
    48: 'sandwich', 49: 'orange', 50: 'broccoli', 51: 'carrot',
    52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake',
    56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed',
    60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop',
    64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone',
    68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
    72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase',
    76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
}

# Product-related objects (detected in medical/pharma images)
PRODUCT_CLASSES = [39, 40, 41, 42, 43, 44, 45, 56, 58]  # bottle, cup, fork, knife, spoon, bowl, chair, potted plant
PERSON_CLASS = 0  # person


class YOLODetector:
    """YOLO object detector for Telegram images"""
    
    def __init__(self, model_name='yolov8n.pt'):
        """Initialize YOLO model"""
        logger.info(f"Loading YOLO model: {model_name}")
        self.model = YOLO(model_name)
        self.model_name = model_name
        logger.info("YOLO model loaded successfully")
    
    def detect_image(self, image_path, confidence_threshold=0.3):
        """
        Run detection on a single image
        
        Args:
            image_path: Path to image file
            confidence_threshold: Minimum confidence for detection
            
        Returns:
            List of detections with class, confidence, bbox
        """
        try:
            # Run inference
            results = self.model(image_path, conf=confidence_threshold, verbose=False)
            
            detections = []
            for result in results:
                if result.boxes is not None:
                    for box in result.boxes:
                        # Get class and confidence
                        cls_id = int(box.cls[0].item())
                        confidence = float(box.conf[0].item())
                        
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        detections.append({
                            'class_id': cls_id,
                            'class_name': YOLO_CLASSES.get(cls_id, f'class_{cls_id}'),
                            'confidence': confidence,
                            'bbox': [x1, y1, x2, y2]
                        })
            
            return detections
        except Exception as e:
            logger.error(f"Error detecting on {image_path}: {e}")
            return []
    
    def classify_image(self, detections):
        """
        Classify image based on detected objects
        
        Args:
            detections: List of detections
            
        Returns:
            category: 'promotional', 'product_display', 'lifestyle', 'other'
            confidence_score: Confidence in classification
        """
        # Extract class IDs
        class_ids = [d['class_id'] for d in detections]
        has_person = PERSON_CLASS in class_ids
        has_product = any(cls in PRODUCT_CLASSES for cls in class_ids)
        
        # Count detections by type
        person_count = class_ids.count(PERSON_CLASS)
        product_count = sum(1 for cls in class_ids if cls in PRODUCT_CLASSES)
        
        # Categorize
        if has_person and has_product:
            category = 'promotional'
            confidence = min(0.9, 0.5 + (person_count * 0.1) + (product_count * 0.1))
        elif has_product and not has_person:
            category = 'product_display'
            confidence = min(0.8, 0.6 + (product_count * 0.1))
        elif has_person and not has_product:
            category = 'lifestyle'
            confidence = min(0.7, 0.5 + (person_count * 0.1))
        else:
            category = 'other'
            confidence = 0.3
        
        return category, round(confidence, 3)
    
    def process_image(self, image_path):
        """
        Process a single image: detect and classify
        
        Args:
            image_path: Path to image
            
        Returns:
            dict with detection results and classification
        """
        # Get message_id from filename
        filename = os.path.basename(image_path)
        message_id = int(filename.split('.')[0]) if filename.split('.')[0].isdigit() else None
        
        # Run detection
        detections = self.detect_image(image_path)
        
        # Classify image
        category, confidence = self.classify_image(detections)
        
        result = {
            'image_path': image_path,
            'message_id': message_id,
            'category': category,
            'category_confidence': confidence,
            'detections': detections,
            'num_detections': len(detections),
            'has_person': any(d['class_id'] == PERSON_CLASS for d in detections),
            'has_product': any(d['class_id'] in PRODUCT_CLASSES for d in detections),
            'detected_objects': [d['class_name'] for d in detections]
        }
        
        return result


def find_images():
    """Find all images from Task 1"""
    # Search for images in the images directory
    image_paths = []
    
    # Supported image extensions
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    
    for ext in extensions:
        search_path = os.path.join(IMAGES_PATH, '**', ext)
        image_paths.extend(glob.glob(search_path, recursive=True))
    
    logger.info(f"Found {len(image_paths)} images")
    return image_paths


def save_results(results, output_file='yolo_detections.csv'):
    """Save detection results to CSV"""
    rows = []
    
    for result in results:
        for detection in result['detections']:
            rows.append({
                'message_id': result['message_id'],
                'image_path': result['image_path'],
                'category': result['category'],
                'category_confidence': result['category_confidence'],
                'class_id': detection['class_id'],
                'class_name': detection['class_name'],
                'confidence': detection['confidence'],
                'bbox_x1': detection['bbox'][0],
                'bbox_y1': detection['bbox'][1],
                'bbox_x2': detection['bbox'][2],
                'bbox_y2': detection['bbox'][3],
                'has_person': result['has_person'],
                'has_product': result['has_product']
            })
    
    # Save to CSV
    df = pd.DataFrame(rows)
    output_path = os.path.join(OUTPUT_PATH, output_file)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(rows)} detections to {output_path}")
    
    # Also save summary
    summary_path = os.path.join(OUTPUT_PATH, 'yolo_summary.csv')
    summary_data = []
    for result in results:
        summary_data.append({
            'message_id': result['message_id'],
            'image_path': result['image_path'],
            'category': result['category'],
            'category_confidence': result['category_confidence'],
            'num_detections': result['num_detections'],
            'has_person': result['has_person'],
            'has_product': result['has_product'],
            'detected_objects': ', '.join(result['detected_objects'][:5])
        })
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv(summary_path, index=False)
    logger.info(f" Saved {len(summary_data)} image summaries to {summary_path}")
    
    return df


def analyze_results(df):
    """Basic analysis of detection results"""

    logger.info("YOLO DETECTION ANALYSIS")

    
    # Category distribution
    category_counts = df.groupby('category').size()
    logger.info(f"\n Category Distribution:")
    for category, count in category_counts.items():
        logger.info(f"  {category}: {count} images")
    
    # Most detected objects
    if 'class_name' in df.columns:
        object_counts = df['class_name'].value_counts().head(10)
        logger.info(f"\n Top 10 Detected Objects:")
        for obj, count in object_counts.items():
            logger.info(f"  {obj}: {count} times")
    
    # Images with people vs products
    if 'has_person' in df.columns:
        person_count = df['has_person'].sum()
        product_count = df['has_product'].sum()
        total = len(df)
        
        logger.info(f"\n Images with People: {person_count}/{total} ({person_count/total*100:.1f}%)")
        logger.info(f" Images with Products: {product_count}/{total} ({product_count/total*100:.1f}%)")
    
    return category_counts


def main():
    """Main function"""
   
    logger.info(" YOLO OBJECT DETECTION FOR TELEGRAM IMAGES")
   
    
    # Initialize detector
    detector = YOLODetector()
    
    # Find images
    images = find_images()
    
    if not images:
        logger.warning("No images found. Please run Task 1 first.")
        return
    
    # Process images
    logger.info(f"\n Processing {len(images)} images...")
    results = []
    
    for image_path in tqdm(images, desc="Processing images"):
        result = detector.process_image(image_path)
        results.append(result)
    
    # Save results
    df = save_results(results)
    
    # Analyze results
    analyze_results(df)
    
    logger.info("\n YOLO detection completed successfully!")
    logger.info(f" Results saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()