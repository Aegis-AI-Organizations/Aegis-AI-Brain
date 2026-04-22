-- Step 2: PostgreSQL Migration for Billing System

-- 1. Update Companies table
ALTER TABLE companies ADD COLUMN org_size VARCHAR(50);
ALTER TABLE companies ADD COLUMN org_type VARCHAR(100);
ALTER TABLE companies ADD COLUMN token_balance BIGINT DEFAULT 0 NOT NULL;

-- 2. Create Token Ledger table
CREATE TABLE token_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index for performance on ledger lookups
CREATE INDEX idx_token_ledger_company_id ON token_ledger(company_id);
