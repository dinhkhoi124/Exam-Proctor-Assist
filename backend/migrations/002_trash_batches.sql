BEGIN;

ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by UUID,
    ADD COLUMN IF NOT EXISTS deletion_batch_id UUID;

ALTER TABLE chat_logs
    ADD COLUMN IF NOT EXISTS deletion_batch_id UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chat_sessions_deleted_by_fkey'
    ) THEN
        ALTER TABLE chat_sessions
            ADD CONSTRAINT chat_sessions_deleted_by_fkey
            FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;
    END IF;
END
$$;

UPDATE chat_sessions
SET deleted_at = COALESCE(deleted_at, updated_at, created_at, now()),
    deletion_batch_id = COALESCE(deletion_batch_id, gen_random_uuid())
WHERE is_deleted = true;

UPDATE chat_logs AS log
SET is_deleted = true,
    deleted_at = COALESCE(log.deleted_at, session.deleted_at),
    deletion_batch_id = COALESCE(log.deletion_batch_id, session.deletion_batch_id)
FROM chat_sessions AS session
WHERE log.session_id = session.id
  AND session.is_deleted = true
  AND log.is_deleted = false;

UPDATE chat_logs
SET deletion_batch_id = gen_random_uuid()
WHERE is_deleted = true
  AND deletion_batch_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_chat_logs_deletion_batch
    ON chat_logs (deletion_batch_id)
    WHERE is_deleted = true;
CREATE INDEX IF NOT EXISTS idx_chat_sessions_deletion_batch
    ON chat_sessions (deletion_batch_id)
    WHERE is_deleted = true;
CREATE INDEX IF NOT EXISTS idx_chat_sessions_deleted_at
    ON chat_sessions (deleted_at)
    WHERE is_deleted = true;

INSERT INTO schema_migrations(version)
VALUES ('002_trash_batches')
ON CONFLICT (version) DO NOTHING;

COMMIT;
