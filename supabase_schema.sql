-- =============================================================================
-- WhatsApp Bot Lead Tracking Schema
-- Run this SQL in your Supabase SQL Editor to set up the database
-- =============================================================================

-- Create leads table for tracking prospect engagement
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    followup_stage INTEGER DEFAULT 0,
    pitch_sent_at TIMESTAMP WITH TIME ZONE,
    message_read_at TIMESTAMP WITH TIME ZONE,
    replied_at TIMESTAMP WITH TIME ZONE,
    converted_at TIMESTAMP WITH TIME ZONE,
    last_followup_at TIMESTAMP WITH TIME ZONE,
    next_followup_at TIMESTAMP WITH TIME ZONE,
    online_status VARCHAR(50) DEFAULT 'offline',
    last_seen_at TIMESTAMP WITH TIME ZONE,
    is_online BOOLEAN DEFAULT FALSE,
    they_replied BOOLEAN DEFAULT FALSE,
    converted BOOLEAN DEFAULT FALSE,
    amount_mentioned VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone_number);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_next_followup ON leads(next_followup_at);

-- Enable Row Level Security (optional)
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Create policy for service role access (for your bot)
CREATE POLICY "Service role full access" ON leads
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Insert a test lead (optional)
-- INSERT INTO leads (phone_number, first_name, status, followup_stage)
-- VALUES ('+1234567890', 'John', 'active', 0);
