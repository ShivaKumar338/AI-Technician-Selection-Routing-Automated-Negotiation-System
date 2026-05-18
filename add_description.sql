-- Run this in Supabase → SQL Editor → Run
-- Adds the description column to jobs table

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT;
