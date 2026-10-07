-- =============================================================================
-- Real-Time Financial Fraud Intelligence Platform
-- Supabase / PostgreSQL Production Schema
-- =============================================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. ACCOUNTS TABLE
-- Stores aggregated account-level risk scores and human-readable explanations
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.accounts (
    account_id VARCHAR(64) PRIMARY KEY,
    account_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (account_risk_score >= 0 AND account_risk_score <= 100),
    explanation TEXT NOT NULL DEFAULT 'Normal account activity',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_accounts_risk_score ON public.accounts (account_risk_score DESC);

-- -----------------------------------------------------------------------------
-- 2. TRANSACTIONS TABLE
-- Stores real-time scored transactions, explanations, and recommended actions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.transactions (
    transaction_id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) NOT NULL REFERENCES public.accounts(account_id) ON DELETE CASCADE,
    device_id VARCHAR(64) NOT NULL,
    merchant_id VARCHAR(64) NOT NULL,
    location VARCHAR(128) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (risk_score >= 0 AND risk_score <= 100),
    explanation TEXT NOT NULL,
    action VARCHAR(64) NOT NULL CHECK (
        action IN ('Approve', 'OTP Verification', 'Temporary Hold', 'Block and Investigate')
    )
);

CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON public.transactions (account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_device_id ON public.transactions (device_id);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant_id ON public.transactions (merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON public.transactions (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_risk_score ON public.transactions (risk_score DESC);

-- -----------------------------------------------------------------------------
-- 3. FRAUD RINGS TABLE
-- Stores detected graph clusters, ring risk scores, patterns, and member accounts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.fraud_rings (
    ring_id VARCHAR(64) PRIMARY KEY,
    ring_risk_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (ring_risk_score >= 0 AND ring_risk_score <= 100),
    pattern_detected TEXT NOT NULL,
    accounts_involved JSONB NOT NULL DEFAULT '[]'::jsonb,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fraud_rings_risk_score ON public.fraud_rings (ring_risk_score DESC);

-- -----------------------------------------------------------------------------
-- Row Level Security (RLS) & Realtime Publication for Supabase
-- -----------------------------------------------------------------------------
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fraud_rings ENABLE ROW LEVEL SECURITY;

-- Allow service role / authenticated hackathon access
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'transactions' AND policyname = 'Allow full access to transactions'
    ) THEN
        CREATE POLICY "Allow full access to transactions" ON public.transactions FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'accounts' AND policyname = 'Allow full access to accounts'
    ) THEN
        CREATE POLICY "Allow full access to accounts" ON public.accounts FOR ALL USING (true) WITH CHECK (true);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'fraud_rings' AND policyname = 'Allow full access to fraud_rings'
    ) THEN
        CREATE POLICY "Allow full access to fraud_rings" ON public.fraud_rings FOR ALL USING (true) WITH CHECK (true);
    END IF;
END
$$;

-- Enable Supabase Realtime on tables
ALTER PUBLICATION supabase_realtime ADD TABLE public.transactions;
ALTER PUBLICATION supabase_realtime ADD TABLE public.accounts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.fraud_rings;
