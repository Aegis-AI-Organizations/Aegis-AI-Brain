-- Store first-login onboarding invitations as one-time hashed tokens.

CREATE TABLE IF NOT EXISTS onboarding_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_onboarding_invitations_user_id
    ON onboarding_invitations(user_id);

CREATE INDEX IF NOT EXISTS idx_onboarding_invitations_expires_at
    ON onboarding_invitations(expires_at);
