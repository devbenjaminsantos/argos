# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook retorna `503` para um update válido de propósito. Ainda não há inbox durável, deduplicação efetiva, comandos Telegram, envio de mensagens, domínio V2, repositórios, coletor Python ou job executável.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. O projeto Supabase Argos existe em `sa-east-1` (`mkpziasjjfnwvtvuorig`), está saudável e tem a revisão Alembic `20260821_01` aplicada. A revisão cria `processed_telegram_updates`; ela não basta para retomar processamento após uma queda entre reserva e conclusão.
- A última validação automatizada registrada executou `backend/.venv/bin/python -m pytest` a partir de `backend/` (27 testes passando). A execução a partir da raiz ainda falha em seis testes que assumem o diretório de trabalho `backend/`; isso é uma pendência de ergonomia da suíte. A releitura remota de 09/09/2026 consultou catálogos PostgreSQL, serviço/deploy Render e HTTP público; não repetiu a suíte nem alterou infraestrutura.
- O último commit é `9e33b85` (2026-09-09), que configurou a API no Render; há ajustes de documentação locais posteriores ainda não commitados. Revise `git status` antes de editar documentação ou criar o próximo commit.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime exige `sslmode=verify-full` e `sslrootcert` apontando para um arquivo existente. Em 09/09/2026, o endpoint direto do Supabase passou por handshake TLS com a CA Supabase Root 2021, rejeitou um hostname incorreto e `psycopg` alcançou a autenticação usando senha inválida descartável; a injeção segura da credencial de `argos_runtime_login` e a validação da rede do provedor de execução continuam pendentes. A configuração de produção agora exige `ARGOS_MIGRATION_DATABASE_URL` separado para o Alembic.
- A releitura de `pg_roles`, `pg_auth_members` e privilégios efetivos em 09/09/2026 confirmou `argos_runtime` e `argos_migrator`, ambos `NOLOGIN`, sem superusuário, criação de banco/roles, replicação ou bypass de RLS. A identidade `argos_runtime_login`, criada pela operação remota `20260909185425`, possui `LOGIN` e senha SCRAM-SHA-256, não recebe grants diretamente e herda somente `argos_runtime`, sem `ADMIN OPTION`: `USAGE` em `public` e `SELECT`/`INSERT`/`UPDATE` em `processed_telegram_updates`, sem `CREATE` no schema, `DELETE`, `TRUNCATE`, `REFERENCES` ou `TRIGGER` nessa tabela e sem leitura de `alembic_version`. Como as demais roles do projeto, ela herda `CONNECT` e `TEMPORARY` concedidos a `PUBLIC` no banco; remover `TEMPORARY` exigiria alterar o padrão global do projeto e não foi feito nesta operação isolada. Sua senha inicial foi gerada dentro do PostgreSQL e deverá ser rotacionada diretamente para o secret store durante a configuração do Render. O migrator possui `USAGE`/`CREATE` em `public` e é proprietário das duas tabelas. A revisão Alembic remota continua `20260821_01`.
- Os grupos já possuem associação administrativa: `postgres` é membro de ambos e pode fazer login. Não há outro membro direto nem login dedicado de privilégio mínimo para o Argos. Não confundir os grupos existentes com credenciais de autenticação da aplicação; não reutilizar `postgres` como runtime. Senhas e hashes não foram consultados.
- A inspeção dos privilégios padrão mostrou grants amplos de `postgres` e `supabase_admin` para `anon`, `authenticated` e `service_role` em objetos futuros de `public` (tabelas, sequências e funções). Não alterá-los sem avaliar as dependências gerenciadas; até a revisão, novas migrações devem usar a identidade de migração e conceder DML explicitamente ao runtime.
- Supabase Auth e Data API não fazem parte da V2. O usuário informou em 09/09/2026 que desabilitou a Data API no Dashboard e decidiu adiar RLS até a estrutura de dados e as políticas estarem prontas; a sessão não consegue inspecionar diretamente esse toggle.
- A consulta inicial ao Render em 09/09/2026 encontrou a workspace `My Workspace` e o serviço `runbase-system`, ligado a `devbenjaminsantos/runbase-system`; esse serviço não pertence ao Argos e não deve ser alterado.
- O serviço `argos-api` (`srv-dagnegm7bikc73bulvig`) está no projeto Render `Argos` (`prj-dagnkh67bikc73bvd220`), ambiente `Production` (`evm-dagnkh67bikc73bvd22g`), plano Free, região Oregon, com `rootDir=backend`, Dockerfile `Dockerfile` e health check `/health`. A consulta remota de 09/09/2026 confirmou serviço não suspenso, auto-deploy desabilitado e deploy `dep-dagpm1dbedkc739o1ikg` em estado `live`, no commit `9e33b85`. O serviço `runbase-system` permanece fora do escopo.
- Em 09/09/2026, `/health` respondeu `200` publicamente; rota inexistente, documentação desabilitada e método inválido responderam `404`, `404` e `405` com envelope seguro e ID de correlação. Os 27 testes locais passaram no mesmo commit implantado.
- `ARGOS_TELEGRAM_WEBHOOK_SECRET` já foi configurado no secret store do Render. Na releitura de 09/09/2026, `/health` retornou `200` e o webhook sem segredo retornou `401`. No código implantado, segredo não configurado retornaria `503`; o `401` comprova que a autenticação está configurada no runtime, sem revelar o valor. O código ainda retorna `503` para update válido até existir inbox durável e deduplicação efetiva.
- A conferência complementar de 09/09/2026 autenticou a CLI Render v2.7.0 pelo navegador e confirmou o serviço/projeto/ambiente. Como essa versão não lista segredos, foram consultados os endpoints de leitura da API Render com a credencial da CLI, exibindo somente nomes e presença. O serviço tem apenas `ARGOS_TELEGRAM_WEBHOOK_SECRET` (não vazio) nas variáveis configuradas, nenhum secret file e o ambiente `Production` não lista env groups. `ARGOS_TELEGRAM_BOT_TOKEN`, `ARGOS_DATABASE_URL`, `ARGOS_MIGRATION_DATABASE_URL` e arquivo CA não estão configurados nesses recursos do Render. Nenhum segredo foi exibido ou gravado no repositório, e nenhuma configuração remota foi alterada.
- A existência do bot e o registro `setWebhook` não foram consultados no Telegram; continuam sem confirmação atual. `/health` não consulta PostgreSQL, e `main.py` ainda não compõe um engine/repositório; saúde HTTP não comprova conexão API → banco. O login da CLI fica em arquivo temporário fora do Git e pode expirar ou desaparecer; reautenticar quando necessário.

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
- A API cloud está ativa e o segredo do webhook está em uso. O login mínimo `argos_runtime_login` e os grupos PostgreSQL já existem; falta criar somente o login dedicado de migração. A associação administrativa dos grupos com `postgres` permanece para operações do provedor.
- Faltam no Render as variáveis do token do bot, conexão de runtime e conexão de migração, além do arquivo CA, conforme leitura autenticada de 09/09/2026. A credencial de migração deverá ficar no executor administrativo escolhido; sua ausência no serviço HTTP não exige colocá-la nesse runtime.
- As ACLs das duas tabelas atuais estão restritas, mas os privilégios padrão futuros de `public` ainda precisam de revisão manual antes de ampliar o schema ou reativar qualquer API de dados.
- Os advisors de segurança e desempenho do Supabase não retornaram lints após a criação do login. A Data API foi desabilitada manualmente; RLS fica adiado até a estrutura e as políticas estarem prontas. Não aplicar RLS sem decidir as políticas: isso pode bloquear o runtime.
- Não há configuração versionada de deploy Render nem workflow GitHub Actions.

### A verificar antes do piloto

- Ao configurar o que falta, preservar `ARGOS_TELEGRAM_WEBHOOK_SECRET` já existente. Confirmar identidade do bot e estado do webhook pela Bot API quando houver acesso ao token; existência do segredo de webhook não comprova existência do bot.
- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, credencial mínima, pool de conexões, latência e limites dos planos. O handshake direto com TLS `verify-full` e a CA do projeto já foi validado a partir do ambiente atual.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Seguir V2.7 do roadmap: rotacionar a senha de `argos_runtime_login` diretamente para o secret store, configurar URL/CA com `sslmode=verify-full` e validar uma consulta ao Supabase a partir do serviço Render.
2. Criar uma identidade `LOGIN` dedicada de migração, associá-la ao grupo `argos_migrator` existente e validar uma migração estrutural em ambiente controlado.
3. Conferir se o bot de teste e `ARGOS_TELEGRAM_BOT_TOKEN` já existem; configurar somente o que faltar e confirmar a identidade do bot sem expor o token.
4. Antes de registrar o webhook do bot para receber mensagens, definir e implementar inbox recuperável, transações, leases e deduplicação com testes em PostgreSQL real.
5. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
