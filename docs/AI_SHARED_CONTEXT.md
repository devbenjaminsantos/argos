# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook retorna `503` para um update válido de propósito. Ainda não há inbox durável, deduplicação efetiva, comandos Telegram, envio de mensagens, domínio V2, repositórios, coletor Python ou job executável.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. O projeto Supabase Argos existe em `sa-east-1` (`mkpziasjjfnwvtvuorig`), está saudável e tem a revisão Alembic `20260821_01` aplicada. A revisão cria `processed_telegram_updates`; ela não basta para retomar processamento após uma queda entre reserva e conclusão.
- A última validação executou `backend/.venv/bin/python -m pytest` a partir de `backend/` (27 testes passando) e `git diff --check`. A execução a partir da raiz ainda falha em seis testes que assumem o diretório de trabalho `backend/`; isso é uma pendência de ergonomia da suíte, separada desta correção.
- O último commit é `240e16e` (2026-09-09), que registrou as roles PostgreSQL e suas operações administrativas; há ajustes de documentação locais posteriores ainda não commitados. Revise `git status` antes de editar documentação ou criar o próximo commit.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime exige `sslmode=verify-full` e `sslrootcert` apontando para um arquivo existente. Em 09/09/2026, o endpoint direto do Supabase passou por handshake TLS com a CA Supabase Root 2021, rejeitou um hostname incorreto e `psycopg` alcançou a autenticação usando senha inválida descartável; a credencial `LOGIN` mínima do runtime e a rede do provedor de execução continuam pendentes. A configuração de produção agora exige `ARGOS_MIGRATION_DATABASE_URL` separado para o Alembic.
- Em 09/09/2026 foram criados no Supabase os grupos `argos_runtime` e `argos_migrator`, ambos `NOLOGIN`, sem senha, superusuário, criação de banco/roles, replicação ou bypass de RLS. `argos_runtime` tem somente `SELECT`, `INSERT` e `UPDATE` em `public.processed_telegram_updates`; `DELETE`, `alembic_version` e os grants das roles padrão ficaram fora do acesso. Em operações separadas, `argos_migrator` recebeu `USAGE`/`CREATE` em `public` e ownership de `alembic_version` e `processed_telegram_updates`; ainda falta uma identidade `LOGIN` para usar esse grupo.
- A inspeção dos privilégios padrão mostrou grants amplos de `postgres` e `supabase_admin` para `anon`, `authenticated` e `service_role` em objetos futuros de `public` (tabelas, sequências e funções). Não alterá-los sem avaliar as dependências gerenciadas; até a revisão, novas migrações devem usar a identidade de migração e conceder DML explicitamente ao runtime.
- Supabase Auth e Data API não fazem parte da V2. O usuário informou em 09/09/2026 que desabilitou a Data API no Dashboard e decidiu adiar RLS até a estrutura de dados e as políticas estarem prontas; a sessão não consegue inspecionar diretamente esse toggle.
- A consulta inicial ao Render em 09/09/2026 encontrou somente a workspace `My Workspace` e o serviço `runbase-system`, ligado a `devbenjaminsantos/runbase-system`; esse serviço não pertence ao Argos e não deve ser alterado.
- A API Argos foi validada por HTTP local temporário em 09/09/2026: `/health` retornou `200`, segredo incorreto no webhook retornou `401` e update privado válido retornou `503` intencional. Esse smoke test não representa uma implantação Render nem testa banco a partir do provedor.
- Após a tentativa solicitada pelo usuário, foi criado no Render o serviço `argos-api` (`srv-dagnegm7bikc73bulvig`) na mesma workspace, com plano Free, Docker e auto deploy desligado. O primeiro deploy falhou porque o conector criou `rootDir` vazio e procurou `./Dockerfile` na raiz; o Argos usa `backend/Dockerfile`. O serviço não recebeu secrets nem tráfego. Corrigir pelo Dashboard com Dockerfile/contexto `backend` e health check `/health` antes de qualquer deploy.
- Em 09/09/2026, o serviço `argos-api` foi associado ao projeto Render `Argos` (`prj-dagnkh67bikc73bvd220`), no ambiente `Production` (`evm-dagnkh67bikc73bvd22g`). O serviço `runbase-system` permaneceu fora desse projeto; nenhuma credencial ou configuração de deploy foi alterada nessa operação.

## Documentação recente

- A revisão está registrada em `docs/REPOSITORY_REVIEW_2026-09-08.md`.
- O README, roadmap, backend README, ADRs 0001–0005 e `AZURE_FOUNDATION.md` foram ajustados para remover orientações incompatíveis. `docs/decisions/0006-fractionated-platform.md` foi criado como decisão vigente.
- A consolidação inicial foi versionada em `f9c0ca6`; a validação TLS e a separação de credenciais foram versionadas em `dd5dab4` e `d1a7c8f`.
- A criação das roles e a ownership inicial foram versionadas em `240e16e`.
- As operações administrativas de roles estão versionadas em `ops/supabase/20260909_argos_roles.sql`, `20260909_argos_migrator_schema.sql` e `20260909_argos_migrator_ownership.sql`; elas não substituem as migrações Alembic.

## Pendências conhecidas

### Confirmadas

- V1 não possui teste de aceitação em Chrome real.
- V2 não processa updates válidos nem persiste usuários, produtos, conversas, observações ou entregas.
- Não há API cloud funcional, bot Telegram, credencial `LOGIN` mínima ou conexão da aplicação ao Supabase configurados no provedor de execução; o endpoint e o handshake TLS foram verificados a partir do ambiente atual. Os grupos PostgreSQL existem no projeto, mas ainda não estão associados a uma identidade de execução.
- O serviço `argos-api` existe no Render, mas ainda não tem um deploy funcional; a configuração de source/health e as credenciais de runtime/migração continuam pendentes.
- As ACLs das duas tabelas atuais estão restritas, mas os privilégios padrão futuros de `public` ainda precisam de revisão manual antes de ampliar o schema ou reativar qualquer API de dados.
- O advisor de segurança do Supabase aponta RLS desabilitado em `public.alembic_version` e `public.processed_telegram_updates`. A Data API foi desabilitada manualmente; RLS fica adiado até a estrutura e as políticas estarem prontas. Não aplicar RLS sem decidir as políticas: isso pode bloquear o runtime.
- Não há configuração versionada de deploy Render nem workflow GitHub Actions.

### A verificar antes do piloto

- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, credencial mínima, pool de conexões, latência e limites dos planos. O handshake direto com TLS `verify-full` e a CA do projeto já foi validado a partir do ambiente atual.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Corrigir a configuração do serviço `argos-api` no Render (Dockerfile/contexto `backend` e health check `/health`), associar uma identidade `LOGIN` ao grupo `argos_runtime`, guardar a URL/CA no secret store e validar a conexão a partir desse serviço.
2. Criar uma identidade `LOGIN` de migração, associá-la a `argos_migrator` e validar uma migração estrutural em ambiente controlado.
3. Antes de aceitar updates Telegram, definir e implementar inbox recuperável, transações, leases e deduplicação com testes em PostgreSQL real.
4. Depois configurar o bot e o deploy da API em incrementos separados.
5. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
