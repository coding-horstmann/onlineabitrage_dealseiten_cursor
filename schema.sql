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

-- Index für schnelle Abfragen
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status);
CREATE INDEX IF NOT EXISTS idx_deals_timestamp ON deals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deals_profit ON deals(profit DESC);

-- Kommentare für Dokumentation
COMMENT ON TABLE logs IS 'Log-Einträge für Feed-Verarbeitungsaktivitäten';
COMMENT ON TABLE deals IS 'Gefundene profitable Arbitrage-Deals';

