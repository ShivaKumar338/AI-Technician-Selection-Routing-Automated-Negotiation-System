-- Run this in Supabase → SQL Editor → Run
-- Drops the old status check constraint so new stage names work

ALTER TABLE whatsapp_negotiations
  DROP CONSTRAINT IF EXISTS whatsapp_negotiations_status_check;
