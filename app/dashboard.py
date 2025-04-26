import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px
import datetime
from urllib.parse import urlparse
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.scraper_factory import ScraperFactory
from models.database import Database
from models.schemas import ProductData
from services.notification_service import EmailReportService

st.set_page_config(
    page_title="Price Tracker Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4CAF50;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f5f5f5;
        border-radius: 5px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .price-current {
        font-size: 2rem;
        font-weight: bold;
        color: #4CAF50;
    }
    .price-old {
        text-decoration: line-through;
        color: #999;
    }
    .price-drop {
        color: #4CAF50;
        font-weight: bold;
    }
    .price-increase {
        color: #F44336;
        font-weight: bold;
    }
    .card-container {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
    }
</style>
""", unsafe_allow_html=True)


def format_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    path = parsed.path
    return f"{domain}{path[:30] + '...' if len(path) > 30 else path}"


def fetch_all_products():
    db = Database()
    products = db.get_all_products()
    results = []
    
    logger = logging.getLogger('dashboard')
    logger.info(f"Found {len(products)} products in database")
    
    for product in products:
        try:
            history = db.get_price_history(product.url)
            
            if history and len(history) > 0:
                latest = history[-1]
                results.append({
                    "url": product.url,
                    "name": latest.name,
                    "latest_price": latest.price,
                    "currency": latest.currency,
                    "image_url": latest.main_image_url,
                    "history_count": len(history),
                    "added_at": product.added_at
                })
            else:
                
                try:
                    logger.info(f"No price history for {product.url}, attempting to fetch initial data")
                    scraper = ScraperFactory.get_scraper(product.url)
                    product_data = scraper.scrape()
                    db.add_price(product_data)
                    
                    results.append({
                        "url": product.url,
                        "name": product_data["name"],
                        "latest_price": product_data["price"],
                        "currency": product_data["currency"],
                        "image_url": product_data.get("main_image_url"),
                        "history_count": 1,
                        "added_at": product.added_at
                    })
                    logger.info(f"Successfully fetched initial data for {product.url}")
                except Exception as e:
                    logger.error(f"Failed to scrape product data for {product.url}: {e}")
                  
                    name = "Unknown Product"
                    if history and len(history) > 0:
                        name = history[0].name
                        
                    results.append({
                        "url": product.url,
                        "name": name,
                        "latest_price": 0.0,
                        "currency": "USD",
                        "image_url": None,
                        "history_count": 0 if not history else len(history),
                        "added_at": product.added_at,
                        "error": str(e)
                    })
        except Exception as e:
            logger.error(f"Error processing product {product.url}: {e}")
           
            results.append({
                "url": product.url,
                "name": "Error Loading Product",
                "latest_price": 0.0,
                "currency": "USD",
                "image_url": None,
                "history_count": 0,
                "added_at": product.added_at,
                "error": str(e)
            })
    
    logger.info(f"Returning {len(results)} products for display")
    db.close()
    return results


def fetch_price_history(url):
    db = Database()
    history = db.get_price_history(url)
    db.close()
    
    if not history:
        return pd.DataFrame()
    
    df = pd.DataFrame([
        {
            "timestamp": h.timestamp,
            "price": h.price,
            "currency": h.currency,
            "name": h.name
        } for h in history
    ])
    
    return df


def add_new_product(url):
    logger = logging.getLogger('dashboard')
    logger.info(f"Attempting to add product: {url}")
    
    try:
       
        if not url.startswith(("http://", "https://")):
            return False, "Invalid URL. Make sure it starts with http:// or https://"
        
        
        db = Database()
        existing_products = [p.url for p in db.get_all_products()]
        
        if url in existing_products:
            db.close()
            logger.info(f"Product already being tracked: {url}")
            
           
            try:
                scraper = ScraperFactory.get_scraper(url)
                product_data = scraper.scrape()
                db.add_price(product_data)
                logger.info(f"Refreshed data for existing product: {product_data['name']}")
                return True, f"Product already exists. Updated price: {product_data['currency']} {product_data['price']}"
            except Exception as e:
                logger.error(f"Failed to refresh data: {e}")
                return False, "This product is already being tracked."
        
        logger.info(f"Creating scraper for URL: {url}")
        scraper = ScraperFactory.get_scraper(url)
        
        logger.info(f"Scraping data from URL: {url}")
        product_data = scraper.scrape()
        
        logger.info(f"Adding product to database: {url}")
        db.add_product(url)
        
        logger.info(f"Adding initial price data: {product_data['price']} {product_data['currency']}")
        db.add_price(product_data)
        db.close()
        
        logger.info(f"Successfully added product: {product_data['name']}")
        return True, f"Successfully added {product_data['name']}"
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}")
        return False, f"Error adding product: {str(e)}"


def send_price_report(email_address):
    logger = logging.getLogger('dashboard')
    
    try:
        if not email_address or not '@' in email_address:
            return False, "Please enter a valid email address"
        
        logger.info(f"Sending price report to {email_address}")
        report_service = EmailReportService()
        success = report_service.send_price_report(email_address)
        
        if success:
            logger.info(f"Successfully sent price report to {email_address}")
            return True, f"Price report successfully sent to {email_address}"
        else:
            logger.error(f"Failed to send price report to {email_address}")
            return False, "Failed to send price report. Please check your email configuration."
    except Exception as e:
        logger.error(f"Error sending price report: {e}")
        return False, f"Error sending price report: {str(e)}"


def remove_product(url):
    logger = logging.getLogger('dashboard')
    logger.info(f"Attempting to remove product: {url}")
    
    try:
        db = Database()
        result = db.delete_product(url)
        db.close()
        
        if result:
            logger.info(f"Successfully removed product: {url}")
            return True, f"Product removed successfully"
        else:
            logger.error(f"Product not found: {url}")
            return False, "Product not found in the database"
    except Exception as e:
        logger.error(f"Error removing product: {e}")
        return False, f"Error removing product: {str(e)}"


def main():
    st.markdown('<h1 class="main-header">Price Tracker Dashboard</h1>', unsafe_allow_html=True)
    
    logger = logging.getLogger('dashboard')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    
    st.sidebar.markdown('<h2 class="subheader">Add New Product</h2>', unsafe_allow_html=True)
    with st.sidebar.form("add_product_form"):
        new_url = st.text_input("Product URL")
        submit_button = st.form_submit_button("Add Product")
        
        if submit_button and new_url:
            success, message = add_new_product(new_url)
            if success:
                st.sidebar.success(message)
                
                st.rerun()
            else:
                st.sidebar.error(message)
    
   
    st.sidebar.markdown('<h2 class="subheader">Send Price Report</h2>', unsafe_allow_html=True)
    with st.sidebar.form("send_report_form"):
        email = st.text_input("Email Address", placeholder="your@email.com")
        email_submit = st.form_submit_button("Send Price Report")
        
        if email_submit:
            success, message = send_price_report(email)
            if success:
                st.sidebar.success(message)
            else:
                st.sidebar.error(message)
    
    
    st.sidebar.markdown('<h2 class="subheader">Remove Product</h2>', unsafe_allow_html=True)
    with st.sidebar.form("remove_product_form"):
        product_url = st.text_input("Product URL", placeholder="https://www.example.com/product")
        remove_submit = st.form_submit_button("Remove Product")
        
        if remove_submit and product_url:
            success, message = remove_product(product_url)
            if success:
                st.sidebar.success(message)
                st.rerun()
            else:
                st.sidebar.error(message)
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    try:
        products = fetch_all_products()
        logger.info(f"Fetched {len(products)} products for display")
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        st.error(f"Error fetching products: {e}")
        products = []
    
    if not products:
        st.info("No products are being tracked yet. Add a product URL in the sidebar to get started.")
        return
    
    st.markdown(f"<h2 class='subheader'>Tracking {len(products)} Products</h2>", unsafe_allow_html=True)
    
    
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0
    
    if 'show_analysis_tab' in st.session_state and st.session_state['show_analysis_tab']:
        st.session_state['active_tab'] = 1
        st.session_state['show_analysis_tab'] = False
    
    col1, col2 = st.columns(2)
    
    if col1.button("All Products", key="tab_all_products", 
                  type="primary" if st.session_state['active_tab'] == 0 else "secondary"):
        st.session_state['active_tab'] = 0
        st.rerun()
        
    if col2.button("Individual Analysis", key="tab_analysis", 
                  type="primary" if st.session_state['active_tab'] == 1 else "secondary"):
        st.session_state['active_tab'] = 1
        st.rerun()
    
    if st.session_state['active_tab'] == 0:
        if not products:
            st.info("No products are being tracked yet. Add a product URL in the sidebar to get started.")
        else:
            for i in range(0, len(products), 3):
                cols = st.columns(3)
                for j in range(min(3, len(products) - i)):
                    product = products[i + j]
                    with cols[j]:
                        with st.container():
                            st.markdown(f"""
                            <div class="metric-card">
                                <h3>{product['name'][:40] + '...' if len(product['name']) > 40 else product['name']}</h3>
                                <p>{format_url(product['url'])}</p>
                            """, unsafe_allow_html=True)
                            
                            if product.get('latest_price') and product.get('latest_price') > 0:
                                st.markdown(f"""
                                <div class="price-current">{product['currency']} {product['latest_price']:.2f}</div>
                                <p>Price points: {product['history_count']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="color: #ff0000;">Error fetching price</div>
                                <p>Last update failed</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if product.get('image_url'):
                                try:
                                    st.image(product['image_url'], width=150)
                                except Exception as e:
                                    logger.error(f"Error displaying image: {e}")
                                    st.markdown("*Image unavailable*")
                            
                            if not product.get('latest_price') or product.get('latest_price') <= 0:
                                if st.button(f"Retry", key=f"retry_{i+j}"):
                                    try:
                                        scraper = ScraperFactory.get_scraper(product['url'])
                                        product_data = scraper.scrape()
                                        db = Database()
                                        db.add_price(product_data)
                                        db.close()
                                        st.success(f"Updated price: {product_data['currency']} {product_data['price']}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"Analyze", key=f"analyze_{i+j}"):
                                    st.session_state['selected_product'] = product['url']
                                    st.session_state['active_tab'] = 1
                                    st.rerun()
                            with col2:
                                if st.button(f"Remove", key=f"remove_{i+j}", type="secondary"):
                                    success, message = remove_product(product['url'])
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
    else:
       
        if 'selected_product' not in st.session_state:
            st.session_state['selected_product'] = products[0]['url'] if products else None
        
        if st.session_state['selected_product']:
            product_options = {p['url']: p['name'] for p in products}
            selected_url = st.selectbox(
                "Select Product", 
                options=list(product_options.keys()),
                format_func=lambda x: product_options[x],
                index=list(product_options.keys()).index(st.session_state['selected_product'])
            )
            
            if selected_url != st.session_state['selected_product']:
                st.session_state['selected_product'] = selected_url
                st.rerun()
            
            try:
                df = fetch_price_history(selected_url)
                
                if df.empty:
                    st.warning("No price history available for this product yet.")
                    
                    try:
                        scraper = ScraperFactory.get_scraper(selected_url)
                        product_data = scraper.scrape()
                        
                        st.subheader("Current Price")
                        selected_product = next((p for p in products if p['url'] == selected_url), None)
                        st.metric("Price", f"{product_data['currency']} {product_data['price']:.2f}")
                        
                        if product_data.get('main_image_url'):
                            st.image(product_data['main_image_url'], width=200)
                        
                        db = Database()
                        db.add_price(product_data)
                        db.close()
                        
                        st.success("Updated with current price data!")
                        st.button("Refresh View", on_click=lambda: st.rerun())
                    except Exception as e:
                        logger.error(f"Error fetching current price: {e}")
                        st.error(f"Couldn't fetch current price: {e}")
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])

                    selected_product = next((p for p in products if p['url'] == selected_url), None)
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"<h2>{selected_product['name']}</h2>", unsafe_allow_html=True)
                        st.markdown(f"<a href='{selected_url}' target='_blank'>{selected_url}</a>", unsafe_allow_html=True)
                        
                        first_price = df['price'].iloc[0]
                        latest_price = df['price'].iloc[-1]
                        price_change = latest_price - first_price
                        price_change_pct = (price_change / first_price) * 100 if first_price > 0 else 0
                        
                        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                        metrics_col1.metric("Current Price", f"{selected_product['currency']} {latest_price:.2f}")
                        metrics_col2.metric(
                            "Change Since First Tracked", 
                            f"{selected_product['currency']} {price_change:.2f}",
                            f"{price_change_pct:.1f}%",
                            delta_color="inverse"  
                        )
                        metrics_col3.metric("Price Points", len(df))
                        
                        if st.button("Remove Product", type="secondary"):
                            success, message = remove_product(selected_url)
                            if success:
                                st.success(message)
                               
                                st.session_state['active_tab'] = 0
                                st.session_state.pop('selected_product', None)
                                st.rerun()
                            else:
                                st.error(message)
                    
                    with col2:
                        if selected_product.get('image_url'):
                            try:
                                st.image(selected_product['image_url'], width=200)
                            except Exception as e:
                                logger.error(f"Error displaying product image: {e}")
                    
                    st.subheader("Price History")
                    
                    try:
                        fig = px.line(
                            df, 
                            x='timestamp', 
                            y='price',
                            title="Price History",
                            labels={"timestamp": "Date", "price": f"Price ({selected_product['currency']})"}
                        )
                        fig.update_layout(
                            height=400,
                            hovermode="x unified",
                            xaxis=dict(title="Date", tickformat="%d %b %Y"),
                            yaxis=dict(title=f"Price ({selected_product['currency']})")
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error creating price chart: {e}")
                        st.error(f"Could not create price chart: {e}")
                        
                        st.write("Price History Data:")
                        st.write(df)
                    
                    st.subheader("Price History Data")
                    
                    display_df = df.copy()
                    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
                    display_df = display_df.rename(columns={
                        'timestamp': 'Date/Time',
                        'price': 'Price',
                        'currency': 'Currency'
                    }).drop(columns=['name'] if 'name' in display_df.columns else [])
                    
                    st.dataframe(display_df.sort_values('Date/Time', ascending=False))
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "Download Price History",
                        csv,
                        f"price_history_{urlparse(selected_url).netloc}_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        key="download-csv"
                    )
            except Exception as e:
                logger.error(f"Error analyzing product: {e}")
                st.error(f"Error analyzing product: {e}")
        else:
            st.info("No products available for analysis. Add a product first.")


if __name__ == "__main__":
    main() 