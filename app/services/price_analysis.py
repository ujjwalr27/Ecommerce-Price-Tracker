import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re

from app.models.database import Database
from app.models.schemas import PriceAlert

load_dotenv()
logger = logging.getLogger('price_analysis')

try:
    threshold_value = os.getenv("PRICE_DROP_THRESHOLD", "5")
    numeric_part = re.search(r'^\d+\.?\d*', threshold_value)
    if numeric_part:
        PRICE_DROP_THRESHOLD = float(numeric_part.group(0))
    else:
        PRICE_DROP_THRESHOLD = 5.0
    logger.info(f"Using price drop threshold of {PRICE_DROP_THRESHOLD}%")
except Exception as e:
    logger.warning(f"Error parsing PRICE_DROP_THRESHOLD: {e}. Using default value of 5%")
    PRICE_DROP_THRESHOLD = 5.0


class PriceAnalyzer:
    
    def __init__(self, threshold: Optional[float] = None):
      
        self.db = Database()
        self.threshold = threshold or PRICE_DROP_THRESHOLD
        logger.info(f"Price analyzer initialized with {self.threshold}% threshold")
    
    def analyze_product(self, url: str) -> Optional[PriceAlert]:
       
        history = self.db.get_price_history(url)
        
        if not history or len(history) < 2:
            logger.info(f"Not enough price history for {url} to analyze")
            return None
        
        latest = history[-1]
        
        previous = history[-2]
        prev_drop_pct = self._calculate_drop_percentage(previous.price, latest.price)
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        last_30_days = [record for record in history if record.timestamp >= thirty_days_ago]
        
        if last_30_days:
            highest_price = max(last_30_days, key=lambda x: x.price)
            highest_drop_pct = self._calculate_drop_percentage(highest_price.price, latest.price)
        else:
            highest_drop_pct = 0
        
        drop_pct = max(prev_drop_pct, highest_drop_pct)
        reference_price = previous.price if prev_drop_pct >= highest_drop_pct else highest_price.price
        
        if drop_pct >= self.threshold:
            logger.info(f"Price drop detected for {latest.name}: {drop_pct:.1f}% (from {reference_price} to {latest.price})")
            
            alert = PriceAlert(
                product_name=latest.name,
                product_url=url,
                old_price=reference_price,
                new_price=latest.price,
                drop_percentage=drop_pct,
                currency=latest.currency,
                image_url=latest.main_image_url
            )
            
            return alert
        
        logger.debug(f"No significant price drop for {url} (latest: {latest.price}, previous: {previous.price}, drop: {prev_drop_pct:.1f}%)")
        return None
    
    def _calculate_drop_percentage(self, old_price: float, new_price: float) -> float:
        
        if old_price <= 0 or new_price >= old_price:
            return 0
        
        drop_amount = old_price - new_price
        percentage = (drop_amount / old_price) * 100
        return percentage
    
    def analyze_all_products(self) -> List[PriceAlert]:
        
        products = self.db.get_all_products()
        alerts = []
        
        for product in products:
            alert = self.analyze_product(product.url)
            if alert:
                alerts.append(alert)
        
        return alerts
    
    def close(self):
        self.db.close() 