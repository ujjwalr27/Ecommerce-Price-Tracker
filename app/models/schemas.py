from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional


class ProductData(BaseModel):
    url: HttpUrl = Field(..., description="Product page URL")
    name: str = Field(..., description="Product name")
    price: float = Field(..., description="Current price")
    currency: str = Field("USD", description="Currency (e.g., USD)")
    main_image_url: Optional[HttpUrl] = Field(None, description="Product image URL")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Scrape timestamp")


class PriceAlert(BaseModel):
    product_name: str
    product_url: HttpUrl
    old_price: float
    new_price: float
    drop_percentage: float
    currency: str = "USD"
    image_url: Optional[HttpUrl] = None 