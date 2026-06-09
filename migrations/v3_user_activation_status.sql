-- Add explicit user activation lifecycle for deferred onboarding.

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_activation_status') THEN
        CREATE TYPE user_activation_status AS ENUM ('active', 'pending_activation');
    END IF;
END $$;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS activation_status user_activation_status NOT NULL DEFAULT 'active';
