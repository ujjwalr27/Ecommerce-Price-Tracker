from sqlalchemy import create_engine, Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
import os
import hashlib
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('database')

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///price_tracker.db")
logger.info(f"Using database: {DATABASE_URL}")

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    
    url = Column(String, primary_key=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    price_histories = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product(url='{self.url}')>"


class PriceHistory(Base):
    __tablename__ = "price_histories"
    
    id = Column(String, primary_key=True)
    product_url = Column(String, ForeignKey("products.url"))
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    main_image_url = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="price_histories")
    
    def __repr__(self):
        return f"<PriceHistory(product_url='{self.product_url}', price={self.price}, timestamp='{self.timestamp}')>"



try:
    engine = create_engine(DATABASE_URL)
    logger.info(f"Database engine created successfully")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
except Exception as e:
    logger.error(f"Error connecting to database: {e}")
    logger.info("Falling back to SQLite")
    DATABASE_URL = "sqlite:///price_tracker.db"
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)


class Database:
    
    def __init__(self):
        self.session = Session()
    
    def add_product(self, url):
      
        url_str = str(url)
        product = Product(url=url_str)
        self.session.merge(product)
        self.session.commit()
        return product
    
    def add_price(self, data: dict):
      
        url_str = str(data['url'])
        
     
        unique_id = hashlib.md5(f"{url_str}_{data['timestamp'].isoformat()}".encode()).hexdigest()
        
        
        self.add_product(url_str)
        
        price_entry = PriceHistory(
            id=unique_id,
            product_url=url_str,
            name=data["name"],
            price=data["price"],
            currency=data["currency"],
            main_image_url=str(data["main_image_url"]) if data.get("main_image_url") else None,
            timestamp=data["timestamp"]
        )
        self.session.add(price_entry)
        self.session.commit()
        return price_entry
    
    def get_all_products(self):
        return self.session.query(Product).all()
    
    def get_price_history(self, url, limit=None):
        
        url_str = str(url)
        
        query = (
            self.session.query(PriceHistory)
            .filter(PriceHistory.product_url == url_str)
            .order_by(PriceHistory.timestamp.asc())
        )
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    def get_latest_price(self, url):
      
        url_str = str(url)
        
        return (
            self.session.query(PriceHistory)
            .filter(PriceHistory.product_url == url_str)
            .order_by(PriceHistory.timestamp.desc())
            .first()
        )
    
    def delete_product(self, url):
      
        url_str = str(url)
        
        product = self.session.query(Product).filter(Product.url == url_str).first()
        if product:
            self.session.delete(product)
            self.session.commit()
            return True
        return False
    
    def close(self):
        self.session.close() 