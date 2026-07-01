# pipeline_simple.py
from dagster import asset, define_asset_job, ScheduleDefinition, Definitions, MaterializeResult
from pathlib import Path
import subprocess
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent

@asset
def scrape_data():
    """Scrape Telegram data"""
    result = subprocess.run(["python", "src/scraper.py"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Scraping failed: {result.stderr}")
    return MaterializeResult(metadata={"status": "success"})

@asset(deps=[scrape_data])
def load_to_postgres():
    """Load data to PostgreSQL"""
    result = subprocess.run(["python", "src/load_to_postgres.py"], cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Loading failed: {result.stderr}")
    return MaterializeResult(metadata={"status": "success"})

@asset(deps=[load_to_postgres])
def run_dbt():
    """Run dbt transformations"""
    result = subprocess.run(["dbt", "run"], cwd=PROJECT_ROOT / "medical-warehouse", capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"dbt failed: {result.stderr}")
    return MaterializeResult(metadata={"status": "success"})

telegram_pipeline = define_asset_job("telegram_pipeline", selection=["scrape_data", "load_to_postgres", "run_dbt"])

daily_schedule = ScheduleDefinition(
    name="daily_pipeline",
    job_name="telegram_pipeline",
    cron_schedule="0 10 * * *",
)

defs = Definitions(
    assets=[scrape_data, load_to_postgres, run_dbt],
    jobs=[telegram_pipeline],
    schedules=[daily_schedule],
)