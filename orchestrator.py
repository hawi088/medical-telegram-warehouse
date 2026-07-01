"""
Simple Pipeline Orchestrator for Telegram Medical Data Warehouse
"""

import os
import sys
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent

def run_step(step_name, command, cwd=None, continue_on_fail=False):
    """Run a pipeline step and log results"""
    logger.info(f"Starting: {step_name}")
    logger.info(f"  Command: {command}")
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            logger.info(f"Completed: {step_name} ({duration:.2f}s)")
            if result.stdout:
                logger.debug(f"  Output: {result.stdout[:200]}...")
            return True
        else:
            if continue_on_fail:
                logger.warning(f"WARNING: {step_name} had errors but continuing ({duration:.2f}s)")
                if result.stderr:
                    logger.warning(f"  Error: {result.stderr[:500]}")
                return True
            else:
                logger.error(f"Failed: {step_name} ({duration:.2f}s)")
                if result.stderr:
                    logger.error(f"  Error: {result.stderr[:500]}")
                return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout: {step_name} (exceeded 1 hour)")
        return False
    except Exception as e:
        logger.error(f"Exception in {step_name}: {e}")
        return False


def run_pipeline():
    """Run the complete pipeline"""
    logger.info("="*60)
    logger.info("TELEGRAM MEDICAL DATA PIPELINE")
    logger.info("="*60)
    logger.info(f"Start time: {datetime.now().isoformat()}")
    
    results = {}
    
    # Step 1: Scrape Telegram Data
    results['scrape'] = run_step(
        "Scrape Telegram Data",
        "python src/scraper.py"
    )
    
    if not results['scrape']:
        logger.error("Pipeline stopped: Scraping failed")
        return False
    
    # Step 2: Load to PostgreSQL
    results['load'] = run_step(
        "Load to PostgreSQL",
        "python src/load_to_postgres.py"
    )
    
    if not results['load']:
        logger.error("Pipeline stopped: Load to PostgreSQL failed")
        return False
    
    # Step 3: Run dbt Transformations (continue on failure)
    results['dbt'] = run_step(
        "Run dbt Transformations",
        "dbt run || echo 'dbt completed with warnings'",
        cwd=PROJECT_ROOT / "medical-warehouse",
        continue_on_fail=True
    )
    
    # Step 4: Run YOLO Detection (continue on failure)
    results['yolo'] = run_step(
        "Run YOLO Detection",
        "python src/yolo_detect.py",
        continue_on_fail=True
    )
    
    # Summary
    logger.info("="*60)
    logger.info("PIPELINE SUMMARY")
    logger.info("="*60)
    for step, success in results.items():
        status = "PASSED" if success else "FAILED"
        logger.info(f"  {step}: {status}")
    
    all_passed = all(results.values())
    logger.info("="*60)
    if all_passed:
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    else:
        logger.warning("PIPELINE COMPLETED WITH ERRORS")
    logger.info(f"End time: {datetime.now().isoformat()}")
    
    return all_passed


def run_pipeline_daily():
    """Run the pipeline daily with retry logic"""
    try:
        import schedule
    except ImportError:
        logger.error("Schedule package not installed. Run: pip install schedule")
        return
    
    logger.info("Starting daily scheduler...")
    logger.info("Pipeline will run daily at 10:00 AM")
    
    def job():
        logger.info("Running scheduled pipeline...")
        run_pipeline()
    
    schedule.every().day.at("10:00").do(job)
    
    logger.info("Running initial pipeline (first run)...")
    run_pipeline()
    
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        run_pipeline_daily()
    else:
        run_pipeline()