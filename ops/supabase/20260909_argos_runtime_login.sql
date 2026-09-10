-- Identidade de login usada exclusivamente pela API Argos.
-- A senha inicial é gerada dentro do PostgreSQL e nunca sai do banco. Ela será
-- rotacionada diretamente para o secret store ao configurar a conexão Render.

DO $$
DECLARE
    initial_password text := encode(gen_random_bytes(48), 'base64');
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'argos_runtime_login'
    ) THEN
        EXECUTE format(
            'CREATE ROLE argos_runtime_login LOGIN INHERIT '
            'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS '
            'PASSWORD %L',
            initial_password
        );
    END IF;
END
$$;

-- A identidade não recebe grants diretamente. Seus privilégios de objetos
-- vêm apenas do grupo NOLOGIN argos_runtime.
REVOKE ALL PRIVILEGES
    ON TABLE public.alembic_version, public.processed_telegram_updates
    FROM argos_runtime_login;

GRANT argos_runtime TO argos_runtime_login;
