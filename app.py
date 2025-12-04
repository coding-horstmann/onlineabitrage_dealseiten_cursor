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

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
EBAY_APP_ID = os.getenv('EBAY_APP_ID')
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')
ALERT_EMAIL = os.getenv('ALERT_EMAIL', GMAIL_USER)
BASIC_AUTH_USER = os.getenv('BASIC_AUTH_USER', 'admin')
BASIC_AUTH_PASSWORD = os.getenv('BASIC_AUTH_PASSWORD', 'changeme')
CRON_SECRET = os.getenv('CRON_SECRET', 'change-this-secret-token')

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# RSS Feed Sources
RSS_SOURCES = [
    'https://www.mydealz.de/rss/hot',
    'https://www.dealdoktor.de/feed/',
    'https://www.schnaeppchenfuchs.de/feed'
]

# HTML Template for Dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArbiBot Dashboard</title>
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
                    <tr>
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


def extract_product_info_with_gemini(item_title, item_description):
    """Extract product name and price using Gemini AI"""
    try:
        prompt = f"""
        Extrahiere aus folgendem RSS-Feed-Eintrag die Produktinformationen:
        
        Titel: {item_title}
        Beschreibung: {item_description[:500]}
        
        Bitte gib mir im folgenden Format zurück:
        PRODUKT: [Produktname]
        PREIS: [Preis in Euro als Zahl ohne Währungssymbol]
        
        Wenn kein Preis gefunden wird, gib PREIS: 0 zurück.
        """
        
        response = gemini_model.generate_content(prompt)
        text = response.text
        
        # Parse response
        product_name = item_title
        price = 0.0
        
        for line in text.split('\n'):
            if 'PRODUKT:' in line:
                product_name = line.split('PRODUKT:')[1].strip()
            elif 'PREIS:' in line:
                try:
                    price_str = line.split('PREIS:')[1].strip().replace('€', '').replace(',', '.').strip()
                    price = float(price_str)
                except:
                    price = 0.0
        
        return product_name, price
    except Exception as e:
        logging.error(f"Gemini extraction error: {e}")
        return item_title, 0.0


def get_ebay_market_price(product_name):
    """Get average market price from eBay Browse API"""
    try:
        # eBay Browse API endpoint
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        
        headers = {
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
            "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=<eBayPartnerNetworkId>"
        }
        
        params = {
            "q": product_name,
            "limit": 20,
            "filter": "conditions:{NEW|NEW_OTHER|NEW_WITH_DEFECT}"
        }
        
        # Note: eBay API requires OAuth token, simplified here
        # In production, you need to implement OAuth flow
        # For now, using a simplified approach
        
        # Alternative: Use eBay Finding API (simpler, but deprecated)
        finding_url = "https://svcs.ebay.de/services/search/FindingService/v1"
        finding_params = {
            "OPERATION-NAME": "findCompletedItems",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": EBAY_APP_ID,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "keywords": product_name,
            "itemFilter(0).name": "Condition",
            "itemFilter(0).value": "New",
            "itemFilter(1).name": "SoldItemsOnly",
            "itemFilter(1).value": "true",
            "paginationInput.entriesPerPage": "20"
        }
        
        response = requests.get(finding_url, params=finding_params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            prices = []
            
            try:
                items = data.get('findCompletedItemsResponse', [{}])[0].get('searchResult', [{}])[0].get('item', [])
                for item in items:
                    selling_status = item.get('sellingStatus', [{}])[0]
                    current_price = selling_status.get('currentPrice', [{}])[0]
                    price_value = float(current_price.get('__value__', 0))
                    if price_value > 0:
                        prices.append(price_value)
            except:
                pass
            
            if prices:
                avg_price = sum(prices) / len(prices)
                # eBay fees: ~10% for most categories
                fees = avg_price * 0.10
                net_price = avg_price - fees
                return net_price
        
        return None
    except Exception as e:
        logging.error(f"eBay API error: {e}")
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
    current_hour = datetime.now().hour
    
    # Check if within allowed time window (8:00 - 20:00)
    if current_hour < 8 or current_hour >= 20:
        logging.info(f"Skipping cron job - outside time window (current hour: {current_hour})")
        return {"status": "skipped", "message": "Outside time window"}
    
    products_found = 0
    deals_found = 0
    
    for source_url in RSS_SOURCES:
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
            
            products_found = len(feed.entries)
            
            # Process each entry
            for entry in feed.entries:
                try:
                    # Extract product info with Gemini
                    product_name, rss_price = extract_product_info_with_gemini(
                        entry.get('title', ''),
                        entry.get('description', '')
                    )
                    
                    if rss_price <= 0:
                        continue
                    
                    # Get eBay market price
                    ebay_price = get_ebay_market_price(product_name)
                    
                    if ebay_price is None or ebay_price <= 0:
                        continue
                    
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
                        deals_found += 1
                        
                        # Send email alert
                        send_email_alert(deal)
                        
                except Exception as e:
                    logging.error(f"Error processing entry: {e}")
                    continue
            
            # Update log entry (get latest log ID first)
            latest_log = supabase.table('logs').select('id').eq('source', source_url).order('timestamp', desc=True).limit(1).execute()
            if latest_log.data:
                log_id = latest_log.data[0]['id']
                supabase.table('logs').update({
                    "status": "Success",
                    "products_found": products_found,
                    "message": f"{deals_found} profitable Deals gefunden"
                }).eq('id', log_id).execute()
            
        except Exception as e:
            logging.error(f"Error processing feed {source_url}: {e}")
            # Update log entry with error (get latest log ID first)
            latest_log = supabase.table('logs').select('id').eq('source', source_url).order('timestamp', desc=True).limit(1).execute()
            if latest_log.data:
                log_id = latest_log.data[0]['id']
                supabase.table('logs').update({
                    "status": "Error",
                    "message": str(e)
                }).eq('id', log_id).execute()
    
    return {
        "status": "success",
        "products_found": products_found,
        "deals_found": deals_found
    }


@app.route('/')
@requires_auth
def dashboard():
    """Dashboard route with Live Logs and Winners views"""
    try:
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


if __name__ == '__main__':
    app.run(debug=True)

