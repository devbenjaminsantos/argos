-- Operação administrativa do Argos; não é uma migração Alembic.
-- Executar depois de 20260909_argos_roles.sql com o papel administrativo
-- disponível no provedor.

-- O Supabase recomenda esta associação para que postgres possa inspecionar e
-- operar objetos criados pelo papel customizado.
GRANT argos_migrator TO postgres;
GRANT USAGE, CREATE ON SCHEMA public TO argos_migrator;
