"""Task definitions for the price tracker."""
import os
import sys
import logging
from datetime import datetime
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.models.database import Database
from app.scrapers.scraper_factory import ScraperFactory
from app.services.price_analysis import PriceAnalyzer
from app.services.notification_service import EmailNotifier
from app.models.schemas import PriceAlert

logger = logging.getLogger('tasks')


def scrape_product(url: str) -> bool:
   
    try:
        logger.info(f"Scraping price for {url}")
        
        scraper = ScraperFactory.get_scraper(url)
        
        product_data = scraper.scrape()
        
        db = Database()
        db.add_price(product_data)
        db.close()
        
        logger.info(f"Successfully scraped {product_data['name']}: {product_data['currency']} {product_data['price']}")
        return True
    
    except Exception as e:
        logger.error(f"Error scraping product {url}: {e}")
        return False


def scrape_all_products() -> int:
    
    logger.info("Starting to scrape all products")
    
    db = Database()
    products = db.get_all_products()
    db.close()
    
    if not products:
        logger.info("No products to scrape")
        return 0
    
    success_count = 0
    
    for product in products:
        if scrape_product(product.url):
            success_count += 1
    
    logger.info(f"Completed scraping: {success_count}/{len(products)} successful")
    return success_count


def analyze_prices() -> List[PriceAlert]:
  
    logger.info("Analyzing prices for all products")
    
    analyzer = PriceAnalyzer()
    alerts = analyzer.analyze_all_products()
    analyzer.close()
    
    logger.info(f"Found {len(alerts)} products with significant price drops")
    return alerts


def send_alerts(alerts: List[PriceAlert]) -> int:
   
    if not alerts:
        logger.info("No alerts to send")
        return 0
    
    logger.info(f"Sending {len(alerts)} price drop alerts")
    
    email_notifier = EmailNotifier()
    sent_count = email_notifier.send_batch_alerts(alerts)
    
    logger.info(f"Sent {sent_count}/{len(alerts)} email alerts")
    return sent_count


def process_all() -> dict:
    
    start_time = datetime.now()
    logger.info("Starting full processing pipeline")
    
    scraped_count = scrape_all_products()
    
    alerts = analyze_prices()
    
    sent_count = send_alerts(alerts)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    stats = {
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration,
        "products_scraped": scraped_count,
        "price_drops_detected": len(alerts),
        "alerts_sent": sent_count
    }
    
    logger.info(f"Full processing completed in {duration:.1f} seconds")
    return stats 