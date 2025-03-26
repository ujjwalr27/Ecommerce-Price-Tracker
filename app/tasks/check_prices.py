#!/usr/bin/env python
import os
import sys
import logging
import argparse
from datetime import datetime

# Add parent directory to path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.database import Database
from app.scrapers.scraper_factory import ScraperFactory
from app.services.price_analysis import PriceAnalyzer
from app.services.notification_service import EmailReportService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), '../../price_checker.log'))
    ]
)
logger = logging.getLogger('price_checker')


def check_product(url: str) -> bool:
    """
    Check a single product for price updates
    
    Args:
        url: Product URL to check
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Checking price for {url}")
        
        # Get the appropriate scraper for this URL
        scraper = ScraperFactory.get_scraper(url)
        
        # Scrape the product data
        product_data = scraper.scrape()
        
        # Store the data in the database
        db = Database()
        db.add_price(product_data)
        
        logger.info(f"Successfully updated price for {product_data['name']}: {product_data['currency']} {product_data['price']}")
        
        db.close()
        return True
    except Exception as e:
        logger.error(f"Error checking price for {url}: {e}")
        return False


def check_all_products(recipient_email=None):
    """Check all tracked products for price updates and send report to specified email"""
    logger.info("Starting price check for all products")
    
    # Get all tracked products
    db = Database()
    products = db.get_all_products()
    db.close()
    
    if not products:
        logger.info("No products to check")
        return
    
    logger.info(f"Found {len(products)} products to check")
    success_count = 0
    
    # Check each product
    for product in products:
        if check_product(product.url):
            success_count += 1
    
    logger.info(f"Completed price checks: {success_count}/{len(products)} successful")
    
    # Analyze prices and send report if email specified
    if recipient_email:
        logger.info(f"Sending price report to {recipient_email}")
        report_service = EmailReportService()
        if report_service.send_price_report(recipient_email):
            logger.info(f"Price report sent successfully to {recipient_email}")
        else:
            logger.error(f"Failed to send price report to {recipient_email}")
    else:
        # For backward compatibility, still analyze prices
        analyzer = PriceAnalyzer()
        alerts = analyzer.analyze_all_products()
        analyzer.close()
        
        if alerts:
            logger.info(f"Detected {len(alerts)} price drops")
        else:
            logger.info("No significant price drops detected")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check product prices and send reports")
    parser.add_argument("--url", help="Check a specific product URL")
    parser.add_argument("--check-all", action="store_true", help="Check all tracked products")
    parser.add_argument("--email", help="Email address to send the price report to")
    
    args = parser.parse_args()
    
    if args.url:
        check_product(args.url)
    elif args.check_all or not args.url:
        check_all_products(recipient_email=args.email)
    else:
        parser.print_help() 