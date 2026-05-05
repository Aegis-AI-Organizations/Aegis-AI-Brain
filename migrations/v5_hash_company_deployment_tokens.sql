-- Migration: v5_hash_company_deployment_tokens
-- Description: Store only hashes of agent deployment tokens.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

UPDATE companies
SET deployment_token = encode(digest(deployment_token, 'sha256'), 'hex')
WHERE deployment_token IS NOT NULL
  AND deployment_token LIKE 'ag_%';

COMMENT ON COLUMN companies.deployment_token IS
    'SHA-256 hash of the raw ag_ deployment token. The raw token is returned only once during onboarding.';
