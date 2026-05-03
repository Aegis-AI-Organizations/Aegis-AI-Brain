-- Migration: v3_agent_management
-- Description: Create agents table to track persistent probes/agents state.

CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'IDLE',
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_agents_company_id ON agents(company_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
