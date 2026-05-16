-- Paste this entire file into Supabase → SQL Editor → Run

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS technicians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    skills TEXT[] NOT NULL DEFAULT '{}',
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    rate_min INTEGER NOT NULL,
    rating DOUBLE PRECISION NOT NULL CHECK (rating >= 1.0 AND rating <= 5.0),
    available BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_type TEXT NOT NULL,
    customer_lat DOUBLE PRECISION NOT NULL,
    customer_lng DOUBLE PRECISION NOT NULL,
    urgency INTEGER NOT NULL CHECK (urgency >= 1 AND urgency <= 5),
    customer_budget INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_tech_id UUID REFERENCES technicians(id),
    agreed_price INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS negotiation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    round INTEGER NOT NULL,
    customer_offer INTEGER NOT NULL,
    tech_offer INTEGER NOT NULL,
    customer_message TEXT NOT NULL,
    tech_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_negotiation_logs_job_id ON negotiation_logs(job_id);

-- Allow API access with anon / service_role keys (development)
ALTER TABLE technicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE negotiation_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "api_all_technicians" ON technicians;
CREATE POLICY "api_all_technicians" ON technicians FOR ALL TO anon, authenticated
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "api_all_jobs" ON jobs;
CREATE POLICY "api_all_jobs" ON jobs FOR ALL TO anon, authenticated
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "api_all_negotiation_logs" ON negotiation_logs;
CREATE POLICY "api_all_negotiation_logs" ON negotiation_logs FOR ALL TO anon, authenticated
    USING (true) WITH CHECK (true);
