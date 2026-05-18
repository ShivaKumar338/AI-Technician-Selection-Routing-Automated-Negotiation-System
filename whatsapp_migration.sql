-- WhatsApp Negotiation Migration v2
-- Run this in Supabase → SQL Editor → Run

-- 1. Add phone_number to technicians
ALTER TABLE technicians ADD COLUMN IF NOT EXISTS phone_number TEXT;

-- 2. Add description to jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT;

-- 3. Assign 2 repeating demo numbers to all existing technicians
WITH numbered AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM technicians
)
UPDATE technicians t
SET phone_number = CASE
    WHEN numbered.rn % 2 = 0 THEN '8520929979'
    ELSE '9603831929'
END
FROM numbered WHERE t.id = numbered.id;

-- 4. WhatsApp negotiation sessions table
CREATE TABLE IF NOT EXISTS whatsapp_negotiations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    technician_id UUID NOT NULL REFERENCES technicians(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'initiated',
    current_round INTEGER NOT NULL DEFAULT 0,
    floor_price INTEGER,
    ceiling_price INTEGER,
    agreed_price INTEGER,
    outcome TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. WhatsApp message log (also used as live chat feed)
CREATE TABLE IF NOT EXISTS whatsapp_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    negotiation_id UUID REFERENCES whatsapp_negotiations(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL DEFAULT 0,
    sender TEXT NOT NULL CHECK (sender IN ('ai','technician','system')),
    message TEXT NOT NULL,
    our_offer INTEGER,
    their_offer INTEGER,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wa_negotiations_job_id ON whatsapp_negotiations(job_id);
CREATE INDEX IF NOT EXISTS idx_wa_negotiations_status ON whatsapp_negotiations(status);
CREATE INDEX IF NOT EXISTS idx_wa_messages_negotiation_id ON whatsapp_messages(negotiation_id);
CREATE INDEX IF NOT EXISTS idx_wa_messages_job_id ON whatsapp_messages(job_id);

ALTER TABLE whatsapp_negotiations ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "api_all_wa_negotiations" ON whatsapp_negotiations;
CREATE POLICY "api_all_wa_negotiations" ON whatsapp_negotiations
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "api_all_wa_messages" ON whatsapp_messages;
CREATE POLICY "api_all_wa_messages" ON whatsapp_messages
    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
