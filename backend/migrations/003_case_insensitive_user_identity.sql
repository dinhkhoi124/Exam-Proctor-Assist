BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM users
        GROUP BY lower(btrim(email))
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Cannot apply migration 003: duplicate emails exist when compared case-insensitively';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM users
        GROUP BY lower(btrim(username))
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION
            'Cannot apply migration 003: duplicate usernames exist when compared case-insensitively';
    END IF;
END
$$;

UPDATE users
SET email = lower(btrim(email)),
    username = btrim(username)
WHERE email IS DISTINCT FROM lower(btrim(email))
   OR username IS DISTINCT FROM btrim(username);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_case_insensitive
    ON users (lower(email));

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_case_insensitive
    ON users (lower(username));

INSERT INTO schema_migrations(version)
VALUES ('003_case_insensitive_user_identity')
ON CONFLICT (version) DO NOTHING;

COMMIT;
