-- Operação administrativa do Argos; não é uma migração Alembic.
-- Executar depois de 20260909_argos_migrator_schema.sql.

ALTER TABLE public.alembic_version OWNER TO argos_migrator;
ALTER TABLE public.processed_telegram_updates OWNER TO argos_migrator;
