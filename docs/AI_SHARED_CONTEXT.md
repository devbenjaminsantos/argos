# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook retorna `503` para um update válido de propósito. Ainda não há inbox durável, deduplicação efetiva, comandos Telegram, envio de mensagens, domínio V2, repositórios, coletor Python ou job executável.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. O projeto Supabase Argos existe em `sa-east-1` (`mkpziasjjfnwvtvuorig`), está saudável e tem a revisão Alembic `20260821_01` aplicada. A revisão cria `processed_telegram_updates`; ela não basta para retomar processamento após uma queda entre reserva e conclusão.
- A última validação executou `backend/.venv/bin/python -m pytest` a partir de `backend/` (27 testes passando) e `git diff --check`. A execução a partir da raiz ainda falha em seis testes que assumem o diretório de trabalho `backend/`; isso é uma pendência de ergonomia da suíte, separada desta correção.
- O último commit é `d1a7c8f` (2026-09-09), que separou as URLs de runtime e migração e reforçou a validação TLS/CA. Revise `git status` antes de editar documentação ou criar o próximo commit.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime exige `sslmode=verify-full` e `sslrootcert` apontando para um arquivo existente. Em 09/09/2026, o endpoint direto do Supabase passou por handshake TLS com a CA Supabase Root 2021, rejeitou um hostname incorreto e `psycopg` alcançou a autenticação usando senha inválida descartável; a credencial `LOGIN` mínima do runtime e a rede do provedor de execução continuam pendentes. A configuração de produção agora exige `ARGOS_MIGRATION_DATABASE_URL` separado para o Alembic.
- Em 09/09/2026 foram criados no Supabase os grupos `argos_runtime` e `argos_migrator`, ambos `NOLOGIN`, sem senha, superusuário, criação de banco/roles, replicação ou bypass de RLS. `argos_runtime` tem somente `SELECT`, `INSERT` e `UPDATE` em `public.processed_telegram_updates`; `DELETE`, `alembic_version` e os grants das roles padrão ficaram fora do acesso. Em operações separadas, `argos_migrator` recebeu `USAGE`/`CREATE` em `public` e ownership de `alembic_version` e `processed_telegram_updates`; ainda falta uma identidade `LOGIN` para usar esse grupo.
- Supabase Auth e Data API não fazem parte da V2. O usuário informou em 09/09/2026 que desabilitou a Data API no Dashboard e decidiu adiar RLS até a estrutura de dados e as políticas estarem prontas; a sessão não consegue inspecionar diretamente esse toggle.

## Documentação recente

- A revisão está registrada em `docs/REPOSITORY_REVIEW_2026-09-08.md`.
- O README, roadmap, backend README, ADRs 0001–0005 e `AZURE_FOUNDATION.md` foram ajustados para remover orientações incompatíveis. `docs/decisions/0006-fractionated-platform.md` foi criado como decisão vigente.
- A consolidação inicial foi versionada em `f9c0ca6`; a validação TLS e a separação de credenciais foram versionadas em `dd5dab4` e `d1a7c8f`.
- As operações administrativas de roles estão versionadas em `ops/supabase/20260909_argos_roles.sql`, `20260909_argos_migrator_schema.sql` e `20260909_argos_migrator_ownership.sql`; elas não substituem as migrações Alembic.

## Pendências conhecidas

### Confirmadas

- V1 não possui teste de aceitação em Chrome real.
- V2 não processa updates válidos nem persiste usuários, produtos, conversas, observações ou entregas.
- Não há API cloud, bot Telegram, credencial `LOGIN` mínima ou conexão da aplicação ao Supabase configurados no provedor de execução; o endpoint e o handshake TLS foram verificados a partir do ambiente atual. Os grupos PostgreSQL existem no projeto, mas ainda não estão associados a uma identidade de execução.
- O advisor de segurança do Supabase aponta RLS desabilitado em `public.alembic_version` e `public.processed_telegram_updates`. A Data API foi desabilitada manualmente; RLS fica adiado até a estrutura e as políticas estarem prontas. Não aplicar RLS sem decidir as políticas: isso pode bloquear o runtime.
- Não há configuração versionada de deploy Render nem workflow GitHub Actions.

### A verificar antes do piloto

- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, credencial mínima, pool de conexões, latência e limites dos planos. O handshake direto com TLS `verify-full` e a CA do projeto já foi validado a partir do ambiente atual.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Confirmar o serviço Argos no provedor de execução, associar uma identidade `LOGIN` ao grupo `argos_runtime`, guardar a URL/CA no secret store e validar a conexão a partir desse serviço.
2. Criar uma identidade `LOGIN` de migração, associá-la a `argos_migrator` e validar uma migração estrutural em ambiente controlado.
3. Antes de aceitar updates Telegram, definir e implementar inbox recuperável, transações, leases e deduplicação com testes em PostgreSQL real.
4. Depois configurar o bot e o deploy da API em incrementos separados.
5. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
