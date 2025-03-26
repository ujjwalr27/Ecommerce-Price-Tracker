#!/usr/bin/env python
import os
import sys
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('add_product')

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.models.database import Database
from app.scrapers.scraper_factory import ScraperFactory


def add_product(url: str, silent: bool = False) -> bool:
    """
    Add a new product to track
    
    Args:
        url: Product URL to add
        silent: If True, suppress info output
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not url.startswith(("http://", "https://")):
            logger.error("Invalid URL. Make sure it starts with http:// or https://")
            return False
            
        # Get database connection
        db = Database()
        
        # Check if product already exists
        existing_products = [p.url for p in db.get_all_products()]
        if url in existing_products:
            if not silent:
                logger.info(f"Product already exists: {url}")
            db.close()
            return True
            
        # Add product to database
        db.add_product(url)
        
        # Try to scrape initial data
        scraper = ScraperFactory.get_scraper(url)
        product_data = scraper.scrape()
        
        # Add initial price data
        db.add_price(product_data)
        
        if not silent:
            logger.info(f"Added product: {product_data['name']} - Current price: {product_data['currency']} {product_data['price']}")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding product {url}: {e}")
        return False


def list_products():
    """List all tracked products"""
    db = Database()
    products = db.get_all_products()
    
    if not products:
        logger.info("No products are being tracked.")
        db.close()
        return
    
    logger.info(f"Tracking {len(products)} products:")
    
    for product in products:
        latest = db.get_latest_price(product.url)
        if latest:
            logger.info(f" - {latest.name} ({product.url}): {latest.currency} {latest.price:.2f}")
        else:
            logger.info(f" - {product.url}: No price data yet")
    
    db.close()


def remove_product(url: str) -> bool:
    """
    Remove a product from tracking
    
    Args:
        url: Product URL to remove
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db = Database()
        result = db.delete_product(url)
        db.close()
        
        if result:
            logger.info(f"Removed product: {url}")
        else:
            logger.error(f"Product not found: {url}")
            
        return result
    except Exception as e:
        logger.error(f"Error removing product {url}: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage products for price tracking")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add product command
    add_parser = subparsers.add_parser("add", help="Add a product to track")
    add_parser.add_argument("url", help="URL of the product to track")
    
    # List products command
    list_parser = subparsers.add_parser("list", help="List all tracked products")
    
    # Remove product command
    remove_parser = subparsers.add_parser("remove", help="Remove a product from tracking")
    remove_parser.add_argument("url", help="URL of the product to remove")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "add" and args.url:
        add_product(args.url)
    elif args.command == "list":
        list_products()
    elif args.command == "remove" and args.url:
        remove_product(args.url)
    else:
        parser.print_help() 