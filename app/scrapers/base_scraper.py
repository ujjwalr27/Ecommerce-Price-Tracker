import os
import requests
import random
import time
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import ValidationError
import logging

from app.models.schemas import ProductData


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('scraper')


load_dotenv()

class BaseScraper(ABC):
    
   
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    DEFAULT_HEADERS = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0"
    }
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
      
        user_agent = random.choice(self.USER_AGENTS)
        
        self.headers = dict(self.DEFAULT_HEADERS)
        self.headers["User-Agent"] = user_agent
        
       
        if headers:
            self.headers.update(headers)
    
    def _fetch_page(self) -> str:
        max_retries = 3
        retry_delay = 2  
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {self.url} (Attempt {attempt+1}/{max_retries})")
                
                
                if attempt > 0:
                    self.headers["Referer"] = "https://www.google.com/"
                
                session = requests.Session()
                response = session.get(
                    self.url, 
                    headers=self.headers, 
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                
               
                if "captcha" in response.text.lower() or "robot check" in response.text.lower():
                    logger.warning(f"Captcha detected on attempt {attempt+1}")
                    if attempt < max_retries - 1:
                       
                        self.headers["User-Agent"] = random.choice(self.USER_AGENTS)
                        time.sleep(retry_delay * (attempt + 1))  
                        continue
                    else:
                        raise requests.RequestException("Captcha detected, could not bypass")
                
                return response.text
            except requests.RequestException as e:
                logger.error(f"Failed to fetch {self.url} on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1)) 
                else:
                    raise
    
    @abstractmethod
    def _extract_data(self, html: str) -> Dict[str, Any]:
        pass
    
    def scrape(self) -> Dict[str, Any]:
        """Main scraping method"""
        logger.info(f"Scraping {self.url}")
        html = self._fetch_page()
        raw_data = self._extract_data(html)
        

        raw_data["url"] = self.url
        if "timestamp" not in raw_data:
            raw_data["timestamp"] = datetime.utcnow()
            
        try:
            product_data = ProductData(**raw_data)
            return product_data.dict()
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise 