-- Run in Supabase → SQL Editor → Run
-- Adds customer info fields to jobs table

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_name TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_phone TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS customer_address TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS visit_date DATE;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS visit_time TEXT;
