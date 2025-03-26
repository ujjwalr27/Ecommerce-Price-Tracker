import os
import smtplib
import logging
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Optional, Dict
from dotenv import load_dotenv

from app.models.schemas import PriceAlert
from app.models.database import Database

# Load environment variables
load_dotenv()
logger = logging.getLogger('notification')

class EmailReportService:
    """Service for sending price reports via email"""
    
    def __init__(self, gmail_user: Optional[str] = None, gmail_password: Optional[str] = None):
        """
        Initialize notification service
        
        Args:
            gmail_user: Gmail address (falls back to GMAIL_USER env var)
            gmail_password: Gmail app password (falls back to GMAIL_APP_PASSWORD env var)
        """
        self.gmail_user = gmail_user or os.getenv("GMAIL_USER")
        self.gmail_password = gmail_password or os.getenv("GMAIL_APP_PASSWORD")
        
        if not self.gmail_user or not self.gmail_password:
            logger.warning("Gmail credentials not configured. Email notifications will not work.")
    
    def send_price_report(self, recipient_email: str) -> bool:
        """
        Send a comprehensive price report for all tracked products
        
        Args:
            recipient_email: Email address to send the report to
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.gmail_user or not self.gmail_password:
            logger.error("Gmail credentials not configured. Cannot send price report.")
            return False
        
        try:
            # Fetch all product data from database
            db = Database()
            products = db.get_all_products()
            
            if not products:
                logger.info("No products to include in report.")
                db.close()
                return False
            
            # Create email content
            subject = f"Price Tracker Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Start building HTML content
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .price-down {{ color: green; font-weight: bold; }}
                    .price-up {{ color: red; }}
                    .product-row {{ margin-bottom: 30px; }}
                    .price-history {{ margin-top: 10px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Price Tracker Report</h1>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                <div class="container">
                    <h2>Currently Tracked Products</h2>
                    <table>
                        <tr>
                            <th>Product</th>
                            <th>Current Price</th>
                            <th>Lowest Price</th>
                            <th>Highest Price</th>
                            <th>Price Change</th>
                            <th>Last Updated</th>
                        </tr>
            """
            
            # Add each product to the report
            for product in products:
                history = db.get_price_history(product.url)
                
                if not history:
                    continue
                
                latest = history[-1]
                first = history[0]
                
                # Calculate price stats
                lowest = min(history, key=lambda x: x.price)
                highest = max(history, key=lambda x: x.price)
                
                # Calculate price change
                price_change = latest.price - first.price
                price_change_pct = (price_change / first.price) * 100 if first.price > 0 else 0
                
                # Determine price change direction
                price_class = "price-down" if price_change < 0 else "price-up" if price_change > 0 else ""
                price_symbol = "↓" if price_change < 0 else "↑" if price_change > 0 else "-"
                
                # Format the price change as a string
                if price_change != 0:
                    price_change_str = f"{price_symbol} {abs(price_change):.2f} ({abs(price_change_pct):.1f}%)"
                else:
                    price_change_str = "No change"
                
                # Add row for this product
                html_content += f"""
                    <tr>
                        <td><a href="{product.url}">{latest.name}</a></td>
                        <td>{latest.currency} {latest.price:.2f}</td>
                        <td>{lowest.currency} {lowest.price:.2f}</td>
                        <td>{highest.currency} {highest.price:.2f}</td>
                        <td class="{price_class}">{price_change_str}</td>
                        <td>{latest.timestamp.strftime('%Y-%m-%d %H:%M')}</td>
                    </tr>
                """
            
            # Close the table and add footer
            html_content += """
                    </table>
                    <p>This report shows the current status of all products you're tracking.</p>
                    <p>Visit your price tracker dashboard for more detailed information and charts.</p>
                    <p><small>To stop receiving these reports, update your notification settings.</small></p>
                </div>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.gmail_user
            msg['To'] = recipient_email
            
            # Attach HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(msg)
            
            logger.info(f"Price report sent successfully to {recipient_email}")
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send price report: {e}")
            return False


class EmailNotifier:
    """Legacy notifier class - kept for backward compatibility"""
    
    def __init__(self):
        self.report_service = EmailReportService()
    
    def send_alert(self, alert: PriceAlert, recipient_email: str) -> bool:
        """Forward to report service"""
        return self.report_service.send_price_report(recipient_email)
    
    def send_batch_alerts(self, alerts: List[PriceAlert], recipient_email: Optional[str] = None) -> int:
        """Send a comprehensive report instead of individual alerts"""
        recipient = recipient_email or os.getenv("GMAIL_USER")
        if not recipient:
            logger.error("No recipient email specified")
            return 0
            
        if self.report_service.send_price_report(recipient):
            return 1
        return 0


# Optional Discord notifier implementation
try:
    import aiohttp
    import asyncio
    import json
    
    class DiscordNotifier:
        """Service for sending notifications to Discord webhook"""
        
        def __init__(self, webhook_url: Optional[str] = None):
            self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
            
            if not self.webhook_url:
                logger.error("Discord webhook URL not configured. Please set DISCORD_WEBHOOK_URL in .env")
        
        async def _send_webhook(self, payload: dict) -> bool:
            """Send a payload to Discord webhook"""
            if not self.webhook_url:
                return False
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        return 200 <= response.status < 300
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")
                return False
        
        async def send_price_drop_alert(self, alert: PriceAlert) -> bool:
            """Send a price drop alert to Discord"""
            if not self.webhook_url:
                logger.error("Cannot send Discord notification: webhook URL not configured")
                return False
            
            # Create Discord embed message
            embed = {
                "title": f"Price Drop: {alert.product_name}",
                "description": f"Price dropped from {alert.currency} {alert.old_price:.2f} to {alert.currency} {alert.new_price:.2f} ({alert.drop_percentage:.1f}% drop)",
                "url": alert.product_url,
                "color": 0x4CAF50,  # Green color
                "fields": [
                    {
                        "name": "Old Price",
                        "value": f"{alert.currency} {alert.old_price:.2f}",
                        "inline": True
                    },
                    {
                        "name": "New Price",
                        "value": f"{alert.currency} {alert.new_price:.2f}",
                        "inline": True
                    },
                    {
                        "name": "Discount",
                        "value": f"{alert.drop_percentage:.1f}%",
                        "inline": True
                    }
                ]
            }
            
            # Add image if available
            if alert.image_url:
                embed["thumbnail"] = {"url": alert.image_url}
            
            payload = {
                "embeds": [embed],
                "username": "Price Tracker"
            }
            
            return await self._send_webhook(payload)
        
        async def send_batch_alerts(self, alerts: List[PriceAlert]) -> int:
            """Send multiple price drop alerts to Discord, returns count of successful sends"""
            successful = 0
            for alert in alerts:
                if await self.send_price_drop_alert(alert):
                    successful += 1
            
            return successful
    
except ImportError:
    logger.warning("aiohttp not installed, Discord notifications will not be available") 