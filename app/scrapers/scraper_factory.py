import logging
from urllib.parse import urlparse
import importlib
import os
from typing import Dict, Type

from .base_scraper import BaseScraper
from .generic_scraper import GenericScraper

logger = logging.getLogger('scraper.factory')

class ScraperFactory:
    
    _registry: Dict[str, Type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, domain, scraper_class: Type[BaseScraper]):
        if isinstance(domain, list):
            for single_domain in domain:
                cls._registry[single_domain] = scraper_class
                logger.info(f"Registered scraper for domain: {single_domain}")
        else:
            cls._registry[domain] = scraper_class
            logger.info(f"Registered scraper for domain: {domain}")
    
    @classmethod
    def get_scraper(cls, url: str) -> BaseScraper:
        domain = urlparse(url).netloc
        
        for registered_domain, scraper_class in cls._registry.items():
            if isinstance(registered_domain, list):
                if any(reg_domain in domain for reg_domain in registered_domain):
                    logger.info(f"Using {scraper_class.__name__} for {domain}")
                    return scraper_class(url)
            elif registered_domain in domain:
                logger.info(f"Using {scraper_class.__name__} for {domain}")
                return scraper_class(url)
        
        logger.info(f"Using GenericScraper for {domain}")
        return GenericScraper(url)



def discover_scrapers():
    scrapers_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename in os.listdir(scrapers_dir):
        if filename.endswith('_scraper.py') and filename != 'base_scraper.py' and filename != 'generic_scraper.py':
            module_name = filename[:-3]  
            
            try:
                module_path = f"app.scrapers.{module_name}"
                try:
                    module = importlib.import_module(f".{module_name}", package="app.scrapers")
                except ImportError:
                    module = importlib.import_module(module_path)
                
                if hasattr(module, 'DOMAIN') and hasattr(module, 'Scraper'):
                    ScraperFactory.register(module.DOMAIN, module.Scraper)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to load scraper from {filename}: {e}")



discover_scrapers() 