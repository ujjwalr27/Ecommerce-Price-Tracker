#!/usr/bin/env python
import os
import sys
import logging
import signal
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
import argparse

# Add parent directory to path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.tasks.check_prices import check_all_products

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../../scheduler.log'))
    ]
)
logger = logging.getLogger('scheduler')

def start_scheduler(hours_interval=None, email=None, daily_report=False):
    """
    Start the price checking scheduler
    
    Args:
        hours_interval: Hours between price checks
        email: Email address to send reports to
        daily_report: Whether to send daily reports instead of on every check
    """
    try:
        # Get interval from environment or parameter
        interval_hours = hours_interval or float(os.getenv("SCRAPE_INTERVAL_HOURS", "1"))
        
        logger.info(f"Starting scheduler with {interval_hours} hour interval")
        
        if email:
            if daily_report:
                logger.info(f"Will send daily report to {email}")
            else:
                logger.info(f"Will send report after every price check to {email}")
        
        # Create scheduler
        scheduler = BackgroundScheduler()
        
        # Schedule price check job
        def check_job():
            logger.info("Running scheduled price check")
            # Only send email if not using daily reports or if it's the first run
            send_to_email = email if (not daily_report or not hasattr(check_job, 'has_run')) else None
            check_all_products(recipient_email=send_to_email)
            check_job.has_run = True
        
        # Schedule daily report job if needed
        def send_daily_report():
            if email and daily_report:
                logger.info(f"Sending daily report to {email}")
                check_all_products(recipient_email=email)
        
        # Add price check job
        scheduler.add_job(
            check_job,
            IntervalTrigger(hours=interval_hours),
            id='price_check_job',
            name='Check prices and update database',
            replace_existing=True
        )
        
        # Add daily report job if needed
        if email and daily_report:
            scheduler.add_job(
                send_daily_report,
                IntervalTrigger(days=1, start_date=datetime.now().replace(hour=8, minute=0, second=0)),
                id='daily_report_job',
                name='Send daily price report',
                replace_existing=True
            )
        
        # Start scheduler
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Keep the script running
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping scheduler")
            scheduler.shutdown()
            
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return False
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the price tracker scheduler")
    parser.add_argument("--interval", type=float, help="Interval in hours between price checks")
    parser.add_argument("--email", help="Email address to send reports to")
    parser.add_argument("--daily-report", action="store_true", help="Send a daily report instead of after every check")
    
    args = parser.parse_args()
    
    start_scheduler(
        hours_interval=args.interval,
        email=args.email,
        daily_report=args.daily_report
    ) 