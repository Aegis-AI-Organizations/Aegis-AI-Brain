-- Step 2: PostgreSQL Migration for Billing System

-- 1. Update Companies table
ALTER TABLE companies ADD COLUMN IF NOT EXISTS org_size VARCHAR(50);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS org_type VARCHAR(100);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS token_balance BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS deployment_token VARCHAR(255) UNIQUE;

-- 2. Create Token Ledger table
CREATE TABLE IF NOT EXISTS token_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index for performance on ledger lookups
CREATE INDEX IF NOT EXISTS idx_token_ledger_company_id ON token_ledger(company_id);

-- 3. Create Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    company_id UUID,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id VARCHAR(100),
    details JSONB,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Index for performance on audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_company_id ON audit_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);

-- 4. Update user_role enum
-- Note: In PostgreSQL, you cannot ADD VALUE IF NOT EXISTS within a transaction in older versions, 
-- but here we assume it's safe to run or handled by the migration tool.
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'billing_aegis') THEN
        ALTER TYPE user_role ADD VALUE 'billing_aegis';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'technicien') THEN
        ALTER TYPE user_role ADD VALUE 'technicien';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'support') THEN
        ALTER TYPE user_role ADD VALUE 'support';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'commercial') THEN
        ALTER TYPE user_role ADD VALUE 'commercial';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'billing_client') THEN
        ALTER TYPE user_role ADD VALUE 'billing_client';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role' AND e.enumlabel = 'operateur') THEN
        ALTER TYPE user_role ADD VALUE 'operateur';
    END IF;
END $$;
