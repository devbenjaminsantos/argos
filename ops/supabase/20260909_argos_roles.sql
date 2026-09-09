-- Papéis de grupo do Argos.
-- Este arquivo é uma operação administrativa, não uma migração Alembic.
-- Não adicionar senhas ou criar papéis LOGIN aqui.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argos_runtime') THEN
        CREATE ROLE argos_runtime
            NOLOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argos_migrator') THEN
        CREATE ROLE argos_migrator
            NOLOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOREPLICATION
            NOBYPASSRLS;
    END IF;
END
$$;

-- O papel de migração foi criado sem login. A concessão de DDL e a
-- transferência de ownership estão nos arquivos de operação seguintes, para
-- que cada mudança possa ser validada separadamente no projeto gerenciado.

-- O runtime só precisa operar a inbox; exclusão e o marcador do Alembic
-- continuam fora do escopo da aplicação.
GRANT SELECT, INSERT, UPDATE
    ON TABLE public.processed_telegram_updates
    TO argos_runtime;

-- A Data API está desabilitada e as políticas RLS serão definidas depois que
-- a estrutura de dados estiver pronta. Até lá, as roles padrão não recebem
-- acesso às tabelas do Argos.
REVOKE ALL PRIVILEGES
    ON TABLE public.alembic_version, public.processed_telegram_updates
    FROM PUBLIC, anon, authenticated, service_role;

-- O schema public ainda mantém USAGE público no projeto gerenciado. O runtime
-- recebe apenas os grants DML explícitos acima; novas tabelas deverão receber
-- grants do runtime em cada migração até que os privilégios padrão possam ser
-- ajustados com o papel administrativo adequado.
