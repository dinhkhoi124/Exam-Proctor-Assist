BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by UUID,
    ADD COLUMN IF NOT EXISTS delete_reason TEXT,
    ADD COLUMN IF NOT EXISTS purged_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS locked_by UUID;

ALTER TABLE chat_logs
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by UUID;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'chat_logs'
          AND column_name = 'created_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE chat_logs
            ALTER COLUMN created_at TYPE TIMESTAMPTZ
            USING created_at AT TIME ZONE 'Asia/Ho_Chi_Minh';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'feedback_logs'
          AND column_name = 'created_at'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE feedback_logs
            ALTER COLUMN created_at TYPE TIMESTAMPTZ
            USING created_at AT TIME ZONE 'Asia/Ho_Chi_Minh';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'last_active'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE users
            ALTER COLUMN last_active TYPE TIMESTAMPTZ
            USING last_active AT TIME ZONE 'Asia/Ho_Chi_Minh';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'token_expiry'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE users
            ALTER COLUMN token_expiry TYPE TIMESTAMPTZ
            USING token_expiry AT TIME ZONE 'Asia/Ho_Chi_Minh';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'users'
          AND column_name = 'verification_expiry'
          AND data_type = 'timestamp without time zone'
    ) THEN
        ALTER TABLE users
            ALTER COLUMN verification_expiry TYPE TIMESTAMPTZ
            USING verification_expiry AT TIME ZONE 'Asia/Ho_Chi_Minh';
    END IF;
END
$$;

ALTER TABLE chat_logs ALTER COLUMN created_at SET DEFAULT now();

ALTER TABLE chat_logs DROP CONSTRAINT IF EXISTS fk_user;
ALTER TABLE chat_logs
    ADD CONSTRAINT fk_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_user_id_fkey;
ALTER TABLE chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

ALTER TABLE user_activity_logs DROP CONSTRAINT IF EXISTS user_activity_logs_user_id_fkey;
ALTER TABLE user_activity_logs
    ADD CONSTRAINT user_activity_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

ALTER TABLE user_sessions DROP CONSTRAINT IF EXISTS user_sessions_user_id_fkey;
ALTER TABLE user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_deleted_by_fkey'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_deleted_by_fkey
            FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_locked_by_fkey'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_locked_by_fkey
            FOREIGN KEY (locked_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chat_logs_deleted_by_fkey'
    ) THEN
        ALTER TABLE chat_logs
            ADD CONSTRAINT chat_logs_deleted_by_fkey
            FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_users_active_deleted
    ON users (is_deleted, is_active);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at
    ON users (deleted_at)
    WHERE is_deleted = true AND purged_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_chat_logs_user_active_created
    ON chat_logs (user_id, created_at DESC)
    WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_chat_logs_session_active
    ON chat_logs (session_id)
    WHERE is_deleted = false;
CREATE INDEX IF NOT EXISTS idx_chat_logs_deleted_at
    ON chat_logs (deleted_at)
    WHERE is_deleted = true;

INSERT INTO schema_migrations(version)
VALUES ('001_admin_retention_vn_timezone')
ON CONFLICT (version) DO NOTHING;

COMMIT;
