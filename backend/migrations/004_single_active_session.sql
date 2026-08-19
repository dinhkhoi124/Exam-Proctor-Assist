BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS session_version BIGINT;

UPDATE users
SET session_version = 0
WHERE session_version IS NULL;

ALTER TABLE users
    ALTER COLUMN session_version SET DEFAULT 0,
    ALTER COLUMN session_version SET NOT NULL;

INSERT INTO schema_migrations(version)
VALUES ('004_single_active_session')
ON CONFLICT (version) DO NOTHING;

COMMIT;
