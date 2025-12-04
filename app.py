"""
ArbiBot - Online Arbitrage Bot via RSS Feeds
Flask Application für Vercel Serverless
"""

import os
import feedparser
import google.generativeai as genai
from flask import Flask, render_template_string, request, Response
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
from datetime import datetime, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '').strip()

# Ensure SUPABASE_URL has https:// protocol
if SUPABASE_URL and not SUPABASE_URL.startswith('http'):
    SUPABASE_URL = f'https://{SUPABASE_URL}'
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
EBAY_APP_ID = os.getenv('EBAY_APP_ID')
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
ALERT_EMAIL = os.getenv('ALERT_EMAIL', GMAIL_USER)
BASIC_AUTH_USER = os.getenv('BASIC_AUTH_USER', 'admin')
BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD', 'changeme')
CRON_SECRET = os.getenv('CRON_SECRET', 'change-this-secret-token')

# Initialize Supabase (lazy initialization)
supabase: Client = None
supabase_error = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        # Remove trailing slash if present and ensure proper format
        supabase_url_clean = SUPABASE_URL.rstrip('/')
        # Initialize Supabase client
        supabase = create_client(supabase_url_clean, SUPABASE_KEY)
        logging.info("Supabase initialized successfully")
    except Exception as e:
        supabase_error = str(e)
        logging.error(f"Failed to initialize Supabase: {e}")
        import traceback
        logging.error(traceback.format_exc())
else:
    if not SUPABASE_URL:
        supabase_error = "SUPABASE_URL is not set"
    elif not SUPABASE_KEY:
        supabase_error = "SUPABASE_KEY is not set"

# Initialize Gemini AI (lazy initialization)
gemini_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
    except Exception as e:
        logging.error(f"Failed to initialize Gemini: {e}")

# RSS Feed Sources
RSS_SOURCES = [
    'https://www.mydealz.de/rss/hot',
    'https://www.dealdoktor.de/feed/',
    'https://schnaeppchenfuchs.com/rss'
]

# HTML Template for Dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArbiBot Dashboard</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 12px 24px;
            background: white;
            border: none;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            color: #666;
            transition: all 0.3s;
        }
        .tab.active {
            background: white;
            color: #667eea;
            box-shadow: 0 -2px 5px rgba(0,0,0,0.1);
        }
        .tab-content {
            display: none;
            background: white;
            padding: 30px;
            border-radius: 0 10px 10px 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .tab-content.active {
            display: block;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .status-success { color: #28a745; font-weight: 600; }
        .status-error { color: #dc3545; font-weight: 600; }
        .status-processing { color: #ffc107; font-weight: 600; }
        .profit-positive { color: #28a745; font-weight: 600; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 20px;
        }
        .refresh-btn:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ArbiBot Dashboard</h1>
            <p>Online Arbitrage Monitoring System</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('logs')">Live Logs</button>
            <button class="tab" onclick="showTab('winners')">Winners</button>
        </div>
        
        <div id="logs" class="tab-content active">
            <button class="refresh-btn" onclick="location.reload()">🔄 Aktualisieren</button>
            <table>
                <thead>
                    <tr>
                        <th>Zeitstempel</th>
                        <th>Quelle</th>
                        <th>Status</th>
                        <th>Gefundene Produkte</th>
                        <th>Nachricht</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr onclick="showEbayQueries({{ log.id }}, '{{ log.source }}')" style="cursor: pointer;" title="Klicken für eBay-Abfragen">
                        <td>{{ log.timestamp }}</td>
                        <td>{{ log.source }}</td>
                        <td><span class="status-{{ log.status.lower() }}">{{ log.status }}</span></td>
                        <td>{{ log.products_found }}</td>
                        <td>{{ log.message or '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div id="winners" class="tab-content">
            <button class="refresh-btn" onclick="location.reload()">🔄 Aktualisieren</button>
            <table>
                <thead>
                    <tr>
                        <th>Zeitstempel</th>
                        <th>Quelle</th>
                        <th>Produkt</th>
                        <th>RSS Preis</th>
                        <th>eBay Preis</th>
                        <th>Gewinn</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
                    {% for deal in deals %}
                    <tr>
                        <td>{{ deal.timestamp }}</td>
                        <td>{{ deal.source }}</td>
                        <td>{{ deal.product_name }}</td>
                        <td>{{ "%.2f"|format(deal.rss_price) }} €</td>
                        <td>{{ "%.2f"|format(deal.ebay_price) }} €</td>
                        <td><span class="profit-positive">{{ "%.2f"|format(deal.profit) }} €</span></td>
                        <td><a href="{{ deal.product_url }}" target="_blank">🔗 Link</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <div id="ebayModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; overflow-y: auto;">
        <div style="background: white; margin: 50px auto; padding: 30px; border-radius: 10px; max-width: 900px; max-height: 80vh; overflow-y: auto;">
            <h2>eBay-Abfragen für: <span id="modalSource"></span></h2>
            <button onclick="closeEbayModal()" style="float: right; background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">✕ Schließen</button>
            <div id="ebayQueriesContent" style="margin-top: 20px;"></div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            // Add active class to clicked tab
            event.target.classList.add('active');
        }
        
        function showEbayQueries(logId, source) {
            document.getElementById('modalSource').textContent = source;
            document.getElementById('ebayModal').style.display = 'block';
            document.getElementById('ebayQueriesContent').innerHTML = '<p>Lade eBay-Abfragen...</p>';
            
            fetch(`/api/ebay-queries/${logId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.queries && data.queries.length > 0) {
                        let html = '<table style="width: 100%; margin-top: 20px;"><thead><tr><th>Produkt</th><th>RSS Preis</th><th>eBay Preis</th><th>Gewinn</th><th>eBay Items</th><th>Status</th></tr></thead><tbody>';
                        data.queries.forEach(q => {
                            html += `<tr>
                                <td>${q.product_name || '-'}</td>
                                <td>${q.rss_price ? q.rss_price.toFixed(2) + ' €' : '-'}</td>
                                <td>${q.ebay_price ? q.ebay_price.toFixed(2) + ' €' : '-'}</td>
                                <td>${q.profit ? q.profit.toFixed(2) + ' €' : '-'}</td>
                                <td>${q.ebay_items_found || 0}</td>
                                <td>${q.query_successful ? '<span style="color: green;">✓ Erfolg</span>' : '<span style="color: red;">✗ Fehler</span>'}</td>
                            </tr>`;
                        });
                        html += '</tbody></table>';
                        document.getElementById('ebayQueriesContent').innerHTML = html;
                    } else {
                        document.getElementById('ebayQueriesContent').innerHTML = '<p>Keine eBay-Abfragen für diesen Log-Eintrag gefunden.</p>';
                    }
                })
                .catch(error => {
                    document.getElementById('ebayQueriesContent').innerHTML = '<p style="color: red;">Fehler beim Laden der eBay-Abfragen: ' + error + '</p>';
                });
        }
        
        function closeEbayModal() {
            document.getElementById('ebayModal').style.display = 'none';
        }
        
        // Close modal on outside click
        document.getElementById('ebayModal')?.addEventListener('click', function(e) {
            if (e.target === this) {
                closeEbayModal();
            }
        });
    </script>
</body>
</html>
"""


def check_auth(username, password):
    """Check if username and password are correct"""
    return username == BASIC_AUTH_USER and password == BASIC_AUTH_PASSWORD


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    """Decorator for routes that require authentication"""
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated


def extract_product_info_with_gemini(item_title, item_description, retry_count=0):
    """Extract product name and price using Gemini AI with rate limiting"""
    try:
        if not gemini_model:
            return item_title, 0.0
        
        # Combine title and description
        full_text = f"{item_title}\n{item_description[:1000]}"
        
        prompt = f"""Du bist ein Experte für die Extraktion von Produktinformationen aus deutschen Deal-Seiten.

Analysiere folgenden RSS-Feed-Eintrag und extrahiere den Produktnamen und Preis:

{full_text}

WICHTIG: 
- Suche nach Preisen in verschiedenen Formaten: "19,99€", "19.99€", "19,99 €", "19.99 EUR", "19,99 Euro", "ab 19,99€", "statt 29,99€ jetzt 19,99€"
- Wenn mehrere Preise vorhanden sind, nimm den niedrigsten/aktuellen Preis
- Ignoriere Versandkosten
- Wenn kein Preis gefunden wird, gib PREIS: 0 zurück

Antworte NUR in diesem exakten Format (eine Zeile pro Feld):
PRODUKT: [Produktname]
PREIS: [Zahl ohne Währungssymbol, Punkt als Dezimaltrennzeichen]

Beispiel:
PRODUKT: Samsung Galaxy S23
PREIS: 599.99"""
        
        try:
            response = gemini_model.generate_content(prompt)
            text = response.text
        except Exception as api_error:
            error_str = str(api_error)
            # Check for quota/rate limit errors
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                if retry_count < 3:
                    # Extract retry delay if available
                    wait_time = 30  # Default 30 seconds
                    if "retry in" in error_str.lower():
                        try:
                            import re
                            match = re.search(r'retry in (\d+)', error_str.lower())
                            if match:
                                wait_time = int(match.group(1)) + 5  # Add 5 seconds buffer
                        except:
                            pass
                    
                    logging.warning(f"Gemini quota exceeded, waiting {wait_time}s before retry {retry_count + 1}/3")
                    time.sleep(wait_time)
                    return extract_product_info_with_gemini(item_title, item_description, retry_count + 1)
                else:
                    logging.error(f"Gemini quota exceeded after 3 retries. Skipping extraction.")
                    return item_title, 0.0
            else:
                raise  # Re-raise if it's not a quota error
        
        # Parse response
        product_name = item_title
        price = 0.0
        
        # Try multiple parsing strategies
        for line in text.split('\n'):
            line = line.strip()
            if 'PRODUKT:' in line.upper():
                product_name = line.split(':', 1)[1].strip() if ':' in line else line.replace('PRODUKT', '').strip()
            elif 'PREIS:' in line.upper():
                try:
                    price_part = line.split(':', 1)[1].strip() if ':' in line else line.replace('PREIS', '').strip()
                    # Remove currency symbols and clean
                    price_part = price_part.replace('€', '').replace('EUR', '').replace('Euro', '').replace('€', '').strip()
                    # Replace comma with dot for decimal
                    price_part = price_part.replace(',', '.')
                    # Remove any non-numeric characters except dot
                    import re
                    price_part = re.sub(r'[^\d.]', '', price_part)
                    if price_part:
                        price = float(price_part)
                except Exception as e:
                    logging.debug(f"Price parsing failed for '{line}': {e}")
                    price = 0.0
        
        # Fallback: Try to find price directly in text using regex
        if price == 0.0:
            import re
            # Look for common price patterns
            price_patterns = [
                r'(\d{1,3}(?:[.,]\d{2})?)\s*€',
                r'€\s*(\d{1,3}(?:[.,]\d{2})?)',
                r'(\d{1,3}[.,]\d{2})\s*(?:EUR|Euro)',
                r'Preis[:\s]+(\d{1,3}(?:[.,]\d{2})?)',
                r'(\d{1,3}[.,]\d{2})\s*Euro',
            ]
            for pattern in price_patterns:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    try:
                        price_str = matches[0].replace(',', '.')
                        price = float(price_str)
                        logging.debug(f"Found price via regex: {price}€")
                        break
                    except:
                        continue
        
        logging.debug(f"Gemini extraction: '{item_title[:50]}' -> Product: '{product_name[:50]}', Price: {price}€")
        return product_name, price
    except Exception as e:
        logging.error(f"Gemini extraction error for '{item_title[:50]}': {e}")
        return item_title, 0.0


def get_ebay_market_price(product_name, log_id=None, rss_price=None, source=None):
    """Get average market price from eBay Browse API"""
    try:
        if not EBAY_APP_ID:
            logging.warning("EBAY_APP_ID not set, skipping eBay query")
            return None
        
        # Use eBay Finding API (simpler, but deprecated)
        finding_url = "https://svcs.ebay.de/services/search/FindingService/v1"
        finding_params = {
            "OPERATION-NAME": "findCompletedItems",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": EBAY_APP_ID,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "keywords": product_name[:100],  # Limit length
            "itemFilter(0).name": "Condition",
            "itemFilter(0).value": "New",
            "itemFilter(1).name": "SoldItemsOnly",
            "itemFilter(1).value": "true",
            "paginationInput.entriesPerPage": "20"
        }
        
        response = requests.get(finding_url, params=finding_params, timeout=10)
        items_found = 0
        ebay_price_result = None
        error_msg = None
        
        if response.status_code == 200:
            data = response.json()
            prices = []
            
            try:
                items = data.get('findCompletedItemsResponse', [{}])[0].get('searchResult', [{}])[0].get('item', [])
                items_found = len(items)
                for item in items:
                    selling_status = item.get('sellingStatus', [{}])[0]
                    current_price = selling_status.get('currentPrice', [{}])[0]
                    price_value = float(current_price.get('__value__', 0))
                    if price_value > 0:
                        prices.append(price_value)
            except Exception as e:
                error_msg = str(e)
                logging.debug(f"Error parsing eBay response: {e}")
                pass
            
            if prices:
                avg_price = sum(prices) / len(prices)
                # eBay fees: ~10% for most categories
                fees = avg_price * 0.10
                net_price = avg_price - fees
                ebay_price_result = net_price
                logging.debug(f"eBay query for '{product_name[:50]}': {len(prices)} items, avg={avg_price:.2f}€, net={net_price:.2f}€")
            else:
                logging.debug(f"eBay query for '{product_name[:50]}': No prices found")
        else:
            error_msg = f"HTTP {response.status_code}"
            logging.warning(f"eBay API returned status {response.status_code} for '{product_name[:50]}'")
        
        # Save eBay query to database for tracking
        if log_id and supabase:
            try:
                profit = (ebay_price_result - rss_price) if (ebay_price_result and rss_price) else None
                query_entry = {
                    "log_id": log_id,
                    "source": source or "",
                    "product_name": product_name[:500],
                    "rss_price": float(rss_price) if rss_price else None,
                    "ebay_price": float(ebay_price_result) if ebay_price_result else None,
                    "ebay_items_found": items_found,
                    "profit": float(profit) if profit else None,
                    "query_successful": ebay_price_result is not None,
                    "error_message": error_msg
                }
                supabase.table('ebay_queries').insert(query_entry).execute()
            except Exception as e:
                logging.error(f"Failed to save eBay query: {e}")
        
        return ebay_price_result
    except Exception as e:
        error_msg = str(e)
        logging.error(f"eBay API error for '{product_name[:50] if product_name else 'unknown'}': {e}")
        
        # Save error to database
        if log_id and supabase:
            try:
                query_entry = {
                    "log_id": log_id,
                    "source": source or "",
                    "product_name": product_name[:500] if product_name else "",
                    "rss_price": float(rss_price) if rss_price else None,
                    "ebay_price": None,
                    "ebay_items_found": 0,
                    "profit": None,
                    "query_successful": False,
                    "error_message": error_msg
                }
                supabase.table('ebay_queries').insert(query_entry).execute()
            except:
                pass
        
        return None


def send_email_alert(deal):
    """Send email alert via Gmail SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f"🎯 ArbiBot: Profitabler Deal gefunden! (+{deal['profit']:.2f}€)"
        
        body = f"""
        Neuer profitabler Deal gefunden!
        
        Produkt: {deal['product_name']}
        Quelle: {deal['source']}
        RSS Preis: {deal['rss_price']:.2f} €
        eBay Preis (netto): {deal['ebay_price']:.2f} €
        Gewinn: {deal['profit']:.2f} €
        
        Link: {deal['product_url']}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Email alert sent for deal: {deal['product_name']}")
    except Exception as e:
        logging.error(f"Email sending error: {e}")


def process_rss_feeds():
    """Main function to process RSS feeds and find arbitrage opportunities"""
    if not supabase:
        raise Exception("Supabase not initialized. Check SUPABASE_URL and SUPABASE_KEY.")
    
    if not gemini_model:
        raise Exception("Gemini not initialized. Check GEMINI_API_KEY.")
    
    current_hour = datetime.now().hour
    
    # Check if within allowed time window (8:00 - 20:00)
    if current_hour < 8 or current_hour >= 20:
        logging.info(f"Skipping cron job - outside time window (current hour: {current_hour})")
        return {"status": "skipped", "message": "Outside time window"}
    
    total_products_found = 0
    total_deals_found = 0
    
    for source_url in RSS_SOURCES:
        # Statistics for this feed
        feed_products = 0
        gemini_extractions = 0
        gemini_with_price = 0
        ebay_queries = 0
        ebay_found = 0
        profitable_deals = 0
        
        try:
            # Create log entry
            log_entry = {
                "source": source_url,
                "status": "Processing",
                "products_found": 0,
                "message": "Feed wird verarbeitet..."
            }
            supabase.table('logs').insert(log_entry).execute()
            
            # Parse RSS feed
            feed = feedparser.parse(source_url)
            
            if feed.bozo:
                raise Exception(f"Feed parsing error: {feed.bozo_exception}")
            
            feed_products = len(feed.entries)
            total_products_found += feed_products
            
            # Get log ID for eBay queries tracking
            latest_log = supabase.table('logs').select('id').eq('source', source_url).order('timestamp', desc=True).limit(1).execute()
            current_log_id = latest_log.data[0]['id'] if latest_log.data else None
            
            # Process each entry with rate limiting (limit to first 20 to avoid timeout)
            max_entries = 20  # Limit to avoid timeout
            for idx, entry in enumerate(feed.entries[:max_entries]):
                try:
                    # Rate limiting: wait between Gemini API calls to avoid quota issues
                    if idx > 0:
                        time.sleep(2)  # Wait 2 seconds between requests (reduced from 1s due to quota)
                    
                    # Extract product info with Gemini
                    product_name, rss_price = extract_product_info_with_gemini(
                        entry.get('title', ''),
                        entry.get('description', '')
                    )
                    gemini_extractions += 1
                    
                    if rss_price <= 0:
                        continue
                    
                    gemini_with_price += 1
                    
                    # Get eBay market price (with tracking)
                    ebay_price = get_ebay_market_price(product_name, log_id=current_log_id, rss_price=rss_price, source=source_url)
                    ebay_queries += 1
                    
                    if ebay_price is None or ebay_price <= 0:
                        continue
                    
                    ebay_found += 1
                    
                    # Calculate profit
                    profit = ebay_price - rss_price
                    
                    # Check if profit > 15€
                    if profit > 15:
                        deal = {
                            "source": source_url,
                            "product_name": product_name,
                            "product_url": entry.get('link', ''),
                            "rss_price": float(rss_price),
                            "ebay_price": float(ebay_price),
                            "profit": float(profit),
                            "ebay_fees": float(ebay_price * 0.10),
                            "rss_item_title": entry.get('title', ''),
                            "rss_item_link": entry.get('link', '')
                        }
                        
                        # Save to database
                        supabase.table('deals').insert(deal).execute()
                        profitable_deals += 1
                        total_deals_found += 1
                        
                        # Send email alert
                        send_email_alert(deal)
                        
                except Exception as e:
                    logging.error(f"Error processing entry: {e}")
                    continue
            
            # Create detailed message
            message_parts = [
                f"Feed-Einträge: {feed_products}",
                f"Gemini-Extraktionen: {gemini_extractions}",
                f"Mit Preis gefunden: {gemini_with_price}",
                f"eBay-Abfragen: {ebay_queries}",
                f"eBay-Preise gefunden: {ebay_found}",
                f"Profitabel (>15€): {profitable_deals}"
            ]
            detailed_message = " | ".join(message_parts)
            
            # Update log entry (get latest log ID first)
            latest_log = supabase.table('logs').select('id').eq('source', source_url).order('timestamp', desc=True).limit(1).execute()
            if latest_log.data:
                log_id = latest_log.data[0]['id']
                supabase.table('logs').update({
                    "status": "Success",
                    "products_found": feed_products,
                    "message": detailed_message
                }).eq('id', log_id).execute()
            
        except Exception as e:
            logging.error(f"Error processing feed {source_url}: {e}")
            # Update log entry with error (get latest log ID first)
            latest_log = supabase.table('logs').select('id').eq('source', source_url).order('timestamp', desc=True).limit(1).execute()
            if latest_log.data:
                log_id = latest_log.data[0]['id']
                error_message = f"Fehler: {str(e)} | Feed-Einträge: {feed_products}"
                supabase.table('logs').update({
                    "status": "Error",
                    "products_found": feed_products,
                    "message": error_message
                }).eq('id', log_id).execute()
    
    return {
        "status": "success",
        "products_found": total_products_found,
        "deals_found": total_deals_found
    }


@app.route('/')
@requires_auth
def dashboard():
    """Dashboard route with Live Logs and Winners views"""
    try:
        if not supabase:
            return "Error: Supabase not initialized. Check SUPABASE_URL and SUPABASE_KEY.", 500
        
        # Get logs (last 100 entries)
        logs_response = supabase.table('logs').select('*').order('timestamp', desc=True).limit(100).execute()
        logs = logs_response.data if hasattr(logs_response, 'data') and logs_response.data else []
        
        # Format timestamp for display
        for log in logs:
            if log.get('timestamp'):
                try:
                    dt = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                    log['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        # Get deals (last 100 entries)
        deals_response = supabase.table('deals').select('*').order('timestamp', desc=True).limit(100).execute()
        deals = deals_response.data if hasattr(deals_response, 'data') and deals_response.data else []
        
        # Format timestamp for display
        for deal in deals:
            if deal.get('timestamp'):
                try:
                    dt = datetime.fromisoformat(deal['timestamp'].replace('Z', '+00:00'))
                    deal['timestamp'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
        
        return render_template_string(DASHBOARD_TEMPLATE, logs=logs, deals=deals)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500


@app.route('/api/cron', methods=['GET', 'POST'])
def cron_job():
    """Cron job endpoint - can be called by external cron services"""
    try:
        # Security check: Verify secret token
        provided_secret = request.headers.get('X-Cron-Secret') or request.args.get('secret')
        if provided_secret != CRON_SECRET:
            return {
                "status": "error",
                "message": "Unauthorized - Invalid secret token"
            }, 401
        
        # Allow manual override of time window with ?force=true parameter
        force_run = request.args.get('force', '').lower() == 'true'
        
        if force_run:
            # Override time window check for manual testing
            logging.info("Manual cron execution forced (time window check bypassed)")
            result = process_rss_feeds(force_time_window=True)
        else:
            result = process_rss_feeds()
        
        return {
            "status": "success",
            "result": result
        }, 200
    except Exception as e:
        logging.error(f"Cron job error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return {"status": "ok"}, 200


@app.route('/api/ebay-queries/<int:log_id>', methods=['GET'])
@requires_auth
def get_ebay_queries(log_id):
    """Get eBay queries for a specific log entry"""
    try:
        if not supabase:
            return {"error": "Supabase not initialized"}, 500
        
        try:
            queries_response = supabase.table('ebay_queries').select('*').eq('log_id', log_id).order('timestamp', desc=True).execute()
            queries = queries_response.data if hasattr(queries_response, 'data') and queries_response.data else []
        except Exception as table_error:
            # Table might not exist yet - return empty list
            logging.warning(f"ebay_queries table might not exist: {table_error}")
            queries = []
        
        return {
            "log_id": log_id,
            "queries": queries,
            "count": len(queries)
        }, 200
    except Exception as e:
        logging.error(f"Error fetching eBay queries for log_id {log_id}: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {
            "error": str(e),
            "log_id": log_id,
            "queries": []
        }, 500


@app.route('/debug', methods=['GET'])
@requires_auth
def debug():
    """Debug endpoint to check environment variables (without exposing secrets)"""
    debug_info = {
        "supabase_initialized": supabase is not None,
        "supabase_error": supabase_error if 'supabase_error' in globals() else None,
        "supabase_url_set": bool(SUPABASE_URL),
        "supabase_url_preview": SUPABASE_URL[:20] + "..." if SUPABASE_URL else None,
        "supabase_key_set": bool(SUPABASE_KEY),
        "supabase_key_preview": SUPABASE_KEY[:10] + "..." if SUPABASE_KEY else None,
        "gemini_initialized": gemini_model is not None,
        "gemini_key_set": bool(GEMINI_API_KEY),
        "gemini_key_preview": GEMINI_API_KEY[:10] + "..." if GEMINI_API_KEY else None,
        "ebay_app_id_set": bool(EBAY_APP_ID),
        "gmail_user_set": bool(GMAIL_USER),
        "gmail_password_set": bool(GMAIL_PASSWORD),
        "cron_secret_set": bool(CRON_SECRET),
    }
    return debug_info, 200


@app.route('/test-gemini', methods=['GET'])
@requires_auth
def test_gemini():
    """Test endpoint to verify Gemini API is working"""
    try:
        if not gemini_model:
            return {
                "error": "Gemini not initialized",
                "gemini_key_set": bool(GEMINI_API_KEY),
                "gemini_key_preview": GEMINI_API_KEY[:10] + "..." if GEMINI_API_KEY else None
            }, 500
        
        # Simple test query
        test_prompt = "Extrahiere aus folgendem Text den Preis: 'Samsung Galaxy S23 für 599,99€'"
        response = gemini_model.generate_content(test_prompt)
        
        return {
            "status": "success",
            "gemini_working": True,
            "test_response": response.text[:200],
            "gemini_model": "gemini-2.0-flash-exp"
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "gemini_working": False,
            "error": str(e),
            "gemini_key_set": bool(GEMINI_API_KEY)
        }, 500


if __name__ == '__main__':
    app.run(debug=True)

