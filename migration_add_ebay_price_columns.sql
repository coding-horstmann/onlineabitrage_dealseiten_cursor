-- Migration: Add new eBay price columns to existing ebay_queries table
-- Run this in Supabase SQL Editor if the table already exists

-- Add new columns for three price types
ALTER TABLE ebay_queries 
ADD COLUMN IF NOT EXISTS ebay_sold_price DECIMAL(10, 2),
ADD COLUMN IF NOT EXISTS ebay_offer_price DECIMAL(10, 2),
ADD COLUMN IF NOT EXISTS ebay_median_price DECIMAL(10, 2),
ADD COLUMN IF NOT EXISTS ebay_sold_items_found INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ebay_offer_items_found INTEGER DEFAULT 0;

-- Copy existing ebay_price to ebay_sold_price for backward compatibility
UPDATE ebay_queries 
SET ebay_sold_price = ebay_price 
WHERE ebay_sold_price IS NULL AND ebay_price IS NOT NULL;

-- Copy ebay_sold_price to ebay_median_price (they are the same)
UPDATE ebay_queries 
SET ebay_median_price = ebay_sold_price 
WHERE ebay_median_price IS NULL AND ebay_sold_price IS NOT NULL;

