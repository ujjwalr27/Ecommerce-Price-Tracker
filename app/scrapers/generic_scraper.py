from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any, Optional, Tuple

from .base_scraper import BaseScraper

logger = logging.getLogger('scraper.generic')

class GenericScraper(BaseScraper):
    """Generic scraper that attempts to extract product data from various e-commerce sites"""
    
    # Common price selectors across various e-commerce sites
    PRICE_SELECTORS = [
        ".price", 
        ".product-price", 
        ".offer-price", 
        ".price-current", 
        ".actual-price", 
        "#priceblock_ourprice", 
        "#priceblock_dealprice", 
        ".a-price",
        ".a-price-whole",
        ".a-price .a-offscreen",
        ".priceToPay .a-offscreen",
        ".apexPriceToPay .a-offscreen",
        "#price_inside_buybox",
        "span.a-price-whole",
        "span.a-size-medium.a-color-price",
        "[data-testid='product-price']",
        ".product-price-value",
        ".current-price"
    ]
    
    # Common title selectors
    TITLE_SELECTORS = [
        "h1.product-title", 
        "h1.product-name", 
        "h1.product_title", 
        "#productTitle", 
        ".product-name", 
        ".product-title",
        "[data-testid='product-title']",
        ".title"
    ]
    
    # Common image selectors
    IMAGE_SELECTORS = [
        ".product-image img", 
        ".product-main-image img", 
        "#main-image", 
        "#product-image",
        ".gallery-image",
        "[data-testid='product-image']",
        ".main-product-image"
    ]
    
    def _extract_price(self, soup: BeautifulSoup) -> Tuple[float, str]:
        """Extract price from soup using multiple selectors"""
        for selector in self.PRICE_SELECTORS:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                logger.debug(f"Found price element with text: {price_text}")
                
                # Detect currency symbol
                currency_match = re.search(r'[$€£¥₹]', price_text)
                currency = currency_match.group(0) if currency_match else 'USD'
                
                # If no currency symbol found but URL contains country indicators, set default currency
                if not currency_match and hasattr(self, 'url'):
                    if '.in/' in self.url.lower():
                        currency = '₹'
                    elif '.uk/' in self.url.lower():
                        currency = '£'
                    elif any(x in self.url.lower() for x in ['.de/', '.fr/', '.it/', '.es/']):
                        currency = '€'
                
                # Map currency symbol to currency code
                currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
                currency_code = currency_map.get(currency, 'USD')
                
                try:
                    # Handle case of duplicated price - if the price appears twice in the string
                    # First, clean the string of all non-price characters
                    price_text = re.sub(r'[$€£¥₹]', '', price_text)
                    price_text = re.sub(r'[^\d.,]', '', price_text)
                    
                    # Check if it's a duplicate pattern by looking for repeating digit groups
                    if len(price_text) > 0:
                        # If the price appears twice consecutively, take only the first instance
                        # For example: "37490.0037490.00" -> "37490.00"
                        half_length = len(price_text) // 2
                        if half_length > 0 and price_text[:half_length] == price_text[half_length:]:
                            price_text = price_text[:half_length]
                        elif len(price_text) > 8:  # If it's a long string, likely contains duplicates
                            # Try to find a sensible price pattern
                            match = re.search(r'([\d,]+\.?\d*)', price_text)
                            if match:
                                price_text = match.group(1)
                    
                    # Replace commas and convert to float
                    price = float(price_text.replace(',', ''))
                    
                    # Log successful price extraction
                    logger.info(f"Successfully extracted price: {price} {currency_code}")
                    return price, currency_code
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not convert price text to float: {price_text}, Error: {e}")
        
        # If no price found with regular selectors, try special Amazon format with separate whole and fraction parts
        try:
            if soup.select_one("span.a-price-whole") and soup.select_one("span.a-price-fraction"):
                whole_part = soup.select_one("span.a-price-whole").get_text().strip().replace(",", "")
                fraction_part = soup.select_one("span.a-price-fraction").get_text().strip()
                price_text = f"{whole_part}.{fraction_part}"
                
                # Determine currency from the page
                # First check symbol attribute
                currency_code = "USD"
                if soup.select_one("span.a-price-symbol"):
                    currency_symbol = soup.select_one("span.a-price-symbol").get_text().strip()
                    currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
                    currency_code = currency_map.get(currency_symbol, 'USD')
                # Otherwise try to guess from URL
                elif hasattr(self, 'url'):
                    if '.in/' in self.url.lower():
                        currency_code = 'INR'
                
                price = float(price_text)
                logger.info(f"Extracted price using whole+fraction method: {price} {currency_code}")
                return price, currency_code
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to extract price using whole+fraction method: {e}")
        
        raise ValueError("Could not extract price from page")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from soup"""
        for selector in self.TITLE_SELECTORS:
            title_elem = soup.select_one(selector)
            if title_elem:
                return title_elem.get_text().strip()
        
        # Fallback to page title if specific title not found
        title_tag = soup.title
        if title_tag:
            return title_tag.get_text().strip()
            
        raise ValueError("Could not extract product title from page")
    
    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image URL from soup"""
        for selector in self.IMAGE_SELECTORS:
            img_elem = soup.select_one(selector)
            if img_elem and img_elem.has_attr('src'):
                return img_elem['src']
            elif img_elem and img_elem.has_attr('data-src'):
                return img_elem['data-src']
        
        # Return None if image not found, as it's optional
        return None
    
    def _extract_data(self, html: str) -> Dict[str, Any]:
        """Extract product data from HTML"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract product details
        price, currency = self._extract_price(soup)
        title = self._extract_title(soup)
        image_url = self._extract_image_url(soup)
        
        return {
            "name": title,
            "price": price,
            "currency": currency,
            "main_image_url": image_url
        } 