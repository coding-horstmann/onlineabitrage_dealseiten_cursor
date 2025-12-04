-- ArbiBot Database Schema für Supabase PostgreSQL

-- Tabelle für Logs (Feed-Verarbeitung)
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'Success', 'Error', 'Processing'
    products_found INTEGER DEFAULT 0,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabelle für profitable Deals
CREATE TABLE IF NOT EXISTS deals (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source VARCHAR(255) NOT NULL,
    product_name TEXT NOT NULL,
    product_url TEXT,
    rss_price DECIMAL(10, 2) NOT NULL,
    ebay_price DECIMAL(10, 2) NOT NULL,
    profit DECIMAL(10, 2) NOT NULL,
    ebay_fees DECIMAL(10, 2) DEFAULT 0,
    rss_item_title TEXT,
    rss_item_link TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabelle für eBay-Abfragen (zum Nachvollziehen)
CREATE TABLE IF NOT EXISTS ebay_queries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    log_id INTEGER,
    source VARCHAR(255) NOT NULL,
    product_name TEXT NOT NULL,
    rss_price DECIMAL(10, 2),
    ebay_price DECIMAL(10, 2),
    ebay_items_found INTEGER DEFAULT 0,
    profit DECIMAL(10, 2),
    query_successful BOOLEAN DEFAULT false,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_ebay_queries_log_id ON ebay_queries(log_id);
CREATE INDEX IF NOT EXISTS idx_ebay_queries_source ON ebay_queries(source);
CREATE INDEX IF NOT EXISTS idx_ebay_queries_timestamp ON ebay_queries(timestamp DESC);

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status);
CREATE INDEX IF NOT EXISTS idx_deals_timestamp ON deals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deals_profit ON deals(profit DESC);

-- Kommentare für Dokumentation
COMMENT ON TABLE logs IS 'Log-Einträge für Feed-Verarbeitungsaktivitäten';
COMMENT ON TABLE deals IS 'Gefundene profitable Arbitrage-Deals';

