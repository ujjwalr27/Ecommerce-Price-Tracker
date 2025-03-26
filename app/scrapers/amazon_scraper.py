import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Tuple

from .base_scraper import BaseScraper

# Domain identifier for the scraper factory
DOMAIN = ["amazon.com", "amazon.in"]

logger = logging.getLogger('scraper.amazon')

class Scraper(BaseScraper):
    """Amazon-specific scraper implementation"""
    
    def _extract_price(self, soup: BeautifulSoup) -> Tuple[float, str]:
        """Extract price from Amazon product page"""
        # Try different price selectors specific to Amazon
        price_selectors = [
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price .a-offscreen",
            "#price_inside_buybox",
            ".apexPriceToPay .a-offscreen",
            ".priceToPay .a-offscreen",
            "#apex_desktop .a-offscreen",
            "#corePriceDisplay_desktop_feature_div .a-offscreen",
            ".a-price-whole",
            "span.a-price-whole",
            "span.a-size-medium.a-color-price",
            "span.a-color-price"
        ]
        
        logger.info(f"Attempting to extract price from Amazon page with {len(price_selectors)} selectors")
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                logger.info(f"Found price element with selector '{selector}': '{price_text}'")
                
                # Detect currency
                currency_match = re.search(r'[$€£¥₹]', price_text)
                currency = currency_match.group(0) if currency_match else '$'
                
                # Extract numeric value from price text
                price_text = re.sub(r'[$€£¥₹,]', '', price_text)
                price_text = re.sub(r'[^\d.]', '', price_text)
                
                try:
                    price = float(price_text)
                    
                    # Determine currency code
                    currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
                    currency_code = currency_map.get(currency, 'USD')
                    
                    # Check URL for country-specific currency if no symbol found
                    if currency == '$' and hasattr(self, 'url'):
                        domain = self.url.split('/')[2].lower()
                        if '.in' in domain:
                            currency_code = 'INR'
                        elif '.co.uk' in domain:
                            currency_code = 'GBP'
                        elif any(x in domain for x in ['.de', '.fr', '.it', '.es']):
                            currency_code = 'EUR'
                    
                    logger.info(f"Successfully extracted price: {price} {currency_code}")
                    return price, currency_code
                except ValueError as e:
                    logger.warning(f"Failed to convert price text '{price_text}' to float: {e}")
        
        # Try special Amazon format with separate whole and fraction parts
        logger.info("Trying to extract price from whole+fraction parts")
        try:
            whole_elements = soup.select("span.a-price-whole")
            fraction_elements = soup.select("span.a-price-fraction")
            
            if whole_elements and fraction_elements:
                whole_part = whole_elements[0].get_text().strip().replace(",", "")
                fraction_part = fraction_elements[0].get_text().strip()
                price_text = f"{whole_part}.{fraction_part}"
                logger.info(f"Found whole+fraction parts: {whole_part}.{fraction_part}")
                
                # Determine currency from the page
                currency_code = "USD"
                symbol_elements = soup.select("span.a-price-symbol")
                if symbol_elements:
                    currency_symbol = symbol_elements[0].get_text().strip()
                    currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY', '₹': 'INR'}
                    currency_code = currency_map.get(currency_symbol, 'USD')
                    logger.info(f"Found currency symbol: {currency_symbol}")
                # Otherwise try to guess from URL
                elif hasattr(self, 'url'):
                    domain = self.url.split('/')[2].lower()
                    if '.in' in domain:
                        currency_code = 'INR'
                        logger.info("Set currency to INR based on domain")
                
                price = float(price_text)
                logger.info(f"Successfully extracted price using whole+fraction method: {price} {currency_code}")
                return price, currency_code
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning(f"Failed to extract price using whole+fraction method: {e}")
        
        # As a last resort, look for any price-like text in the page
        logger.info("Trying to find any price-like text on the page")
        try:
            # Look for text that contains ₹ (Rupee symbol) followed by numbers
            if hasattr(self, 'url') and '.in' in self.url:
                rupee_patterns = [
                    re.compile(r'₹\s*([\d,]+(\.\d+)?)'),
                    re.compile(r'₹([\d,]+(\.\d+)?)')
                ]
                
                for pattern in rupee_patterns:
                    price_matches = pattern.findall(str(soup))
                    if price_matches:
                        price_text = price_matches[0][0].replace(',', '')
                        price = float(price_text)
                        logger.info(f"Found price using regex pattern: ₹{price_text}")
                        return price, 'INR'
        except Exception as e:
            logger.warning(f"Failed to extract price using regex: {e}")
        
        # Check for "Buy New" section which often contains price
        try:
            buy_new_elements = soup.select("#buyNewSection .a-color-price")
            if buy_new_elements:
                price_text = buy_new_elements[0].get_text().strip()
                logger.info(f"Found price in Buy New section: {price_text}")
                
                # Extract numeric value
                price_text = re.sub(r'[$€£¥₹,]', '', price_text)
                price_text = re.sub(r'[^\d.]', '', price_text)
                price = float(price_text)
                
                # Determine currency (default to INR for amazon.in)
                currency_code = 'USD'
                if hasattr(self, 'url'):
                    domain = self.url.split('/')[2].lower()
                    if '.in' in domain:
                        currency_code = 'INR'
                
                return price, currency_code
        except Exception as e:
            logger.warning(f"Failed to extract price from Buy New section: {e}")
        
        logger.error("Could not extract price from Amazon page using any method")
        raise ValueError("Could not extract price from Amazon page")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from Amazon page"""
        title_elem = soup.select_one("#productTitle")
        if title_elem:
            return title_elem.get_text().strip()
        
        # Fallback to page title
        title_tag = soup.title
        if title_tag:
            # Amazon titles often contain " : Amazon.com"
            return title_tag.get_text().split(" : ")[0].strip()
        
        raise ValueError("Could not extract product title from Amazon page")
    
    def _extract_image_url(self, soup: BeautifulSoup) -> str:
        """Extract product image URL from Amazon page"""
        # Try main product image
        img_elem = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
        if img_elem and img_elem.has_attr('src'):
            return img_elem['src']
        elif img_elem and img_elem.has_attr('data-a-dynamic-image'):
            # Amazon sometimes stores image URLs in a data attribute as JSON
            import json
            try:
                images = json.loads(img_elem['data-a-dynamic-image'])
                if images:
                    # Get the first image URL (key)
                    return list(images.keys())[0]
            except (json.JSONDecodeError, IndexError):
                pass
        
        # Try other image selectors
        for selector in ["#main-image", "#imgTagWrapperId img"]:
            img_elem = soup.select_one(selector)
            if img_elem and img_elem.has_attr('src'):
                return img_elem['src']
        
        # Return None if no image found
        return None
    
    def _extract_data(self, html: str) -> Dict[str, Any]:
        """Extract product data from Amazon HTML"""
        soup = BeautifulSoup(html, 'lxml')
        
        # Extract product details
        try:
            price, currency = self._extract_price(soup)
        except ValueError:
            # As a last-ditch effort, try to extract price from the raw HTML
            logger.info("Attempting to extract price from raw HTML")
            price = None
            currency = 'INR' if '.in' in self.url else 'USD'  # Default based on domain
            
            # Look for price patterns in the raw HTML
            # Amazon often has pricing data in JSON inside the HTML
            # For Amazon India
            if '.in' in self.url:
                price_patterns = [
                    r'"priceAmount":\s*(\d+(?:\.\d+)?)',
                    r'"formattedPrice":\s*"₹\s*(\d+(?:,\d+)*(?:\.\d+)?)"',
                    r'"buyingPrice":\s*"₹\s*(\d+(?:,\d+)*(?:\.\d+)?)"',
                    r'id="priceblock_ourprice"[^>]*>₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
                    r'class="a-price-whole">(\d+(?:,\d+)*)</span><span class="a-price-fraction">(\d+)',
                    r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, html)
                    if matches:
                        if isinstance(matches[0], tuple) and len(matches[0]) == 2:
                            # Handle whole and fraction parts
                            price_str = f"{matches[0][0].replace(',', '')}.{matches[0][1]}"
                        else:
                            price_str = str(matches[0]).replace(',', '')
                        
                        try:
                            price = float(price_str)
                            logger.info(f"Extracted price {price} from raw HTML using pattern: {pattern}")
                            break
                        except (ValueError, TypeError):
                            continue
            
            if price is None:
                raise ValueError("Could not extract price from page after trying all methods")
        
        title = self._extract_title(soup)
        image_url = self._extract_image_url(soup)
        
        return {
            "name": title,
            "price": price,
            "currency": currency,
            "main_image_url": image_url
        } 