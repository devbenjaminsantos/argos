-- Identidade de login reservada ao executor administrativo de migrações.
-- A senha inicial é gerada dentro do PostgreSQL e nunca sai do banco. Ela deve
-- ser rotacionada diretamente para o secret store do executor escolhido.

DO $$
DECLARE
    initial_password text := encode(gen_random_bytes(48), 'base64');
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'argos_migrator_login'
    ) THEN
        EXECUTE format(
            'CREATE ROLE argos_migrator_login LOGIN INHERIT '
            'NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS '
            'PASSWORD %L',
            initial_password
        );
    END IF;
END
$$;

-- O login não recebe grants de objetos diretamente. Para operações que
-- dependem de ownership, o executor deve assumir explicitamente argos_migrator.
REVOKE ALL PRIVILEGES
    ON TABLE public.alembic_version, public.processed_telegram_updates
    FROM argos_migrator_login;

GRANT argos_migrator TO argos_migrator_login;
