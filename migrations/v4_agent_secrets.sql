-- Migration: v4_agent_secrets
-- Description: Add token_hash to agents table for secure authentication.

ALTER TABLE agents ADD COLUMN token_hash TEXT;

-- Existing agents will have NULL token_hash, which is fine (they won't be able to authenticate until re-registered or manually updated).
