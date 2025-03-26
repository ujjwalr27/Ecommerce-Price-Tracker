import logging
from urllib.parse import urlparse
import importlib
import os
from typing import Dict, Type

from .base_scraper import BaseScraper
from .generic_scraper import GenericScraper

logger = logging.getLogger('scraper.factory')

class ScraperFactory:
    """Factory class that creates appropriate scrapers for different websites"""
    
    # Registry of domain-specific scrapers
    _registry: Dict[str, Type[BaseScraper]] = {}
    
    @classmethod
    def register(cls, domain, scraper_class: Type[BaseScraper]):
        """Register a scraper class for a specific domain"""
        # Handle both string domains and lists of domains
        if isinstance(domain, list):
            for single_domain in domain:
                cls._registry[single_domain] = scraper_class
                logger.info(f"Registered scraper for domain: {single_domain}")
        else:
            cls._registry[domain] = scraper_class
            logger.info(f"Registered scraper for domain: {domain}")
    
    @classmethod
    def get_scraper(cls, url: str) -> BaseScraper:
        """Get appropriate scraper instance for the given URL"""
        # Extract domain from URL
        domain = urlparse(url).netloc
        
        # Check if we have a specific scraper for this domain
        for registered_domain, scraper_class in cls._registry.items():
            # Check if registered_domain is a list or a single string
            if isinstance(registered_domain, list):
                if any(reg_domain in domain for reg_domain in registered_domain):
                    logger.info(f"Using {scraper_class.__name__} for {domain}")
                    return scraper_class(url)
            elif registered_domain in domain:
                logger.info(f"Using {scraper_class.__name__} for {domain}")
                return scraper_class(url)
        
        # Fall back to generic scraper
        logger.info(f"Using GenericScraper for {domain}")
        return GenericScraper(url)


# Auto-discover and register domain-specific scrapers
def discover_scrapers():
    """Discover and register domain-specific scrapers"""
    scrapers_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename in os.listdir(scrapers_dir):
        if filename.endswith('_scraper.py') and filename != 'base_scraper.py' and filename != 'generic_scraper.py':
            module_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the module
                module_path = f"app.scrapers.{module_name}"
                # Try relative import first
                try:
                    module = importlib.import_module(f".{module_name}", package="app.scrapers")
                except ImportError:
                    # Fall back to absolute import
                    module = importlib.import_module(module_path)
                
                # Look for a DOMAIN constant and Scraper class
                if hasattr(module, 'DOMAIN') and hasattr(module, 'Scraper'):
                    ScraperFactory.register(module.DOMAIN, module.Scraper)
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to load scraper from {filename}: {e}")


# Register scrapers on import
discover_scrapers() 