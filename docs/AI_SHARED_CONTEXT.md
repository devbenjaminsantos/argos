# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

O primeiro fluxo real do Telegram está validado: `@argos_teste_bot` recebeu `/start`, o webhook persistiu o update, o runner registrou a identidade, enviou a resposta esperada e concluiu a inbox em uma tentativa. O bot permanece limitado a conversas privadas e anuncia somente `/start`. A fronteira persiste apenas esse comando; texto ou comandos desconhecidos são confirmados sem persistência para evitar retries do Telegram. No piloto gratuito, o runner acompanha o ciclo de vida do processo HTTP, acorda depois da persistência e usa polling, inbox e leases para recuperação; o job de coleta permanece separado. O frontend ainda em desenho pode evoluir em paralelo e não deve acessar diretamente o banco ou a Bot API.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook persiste cada update autenticado e válido na inbox antes de responder `200`; updates repetidos recebem `200` sem nova linha. Ausência da inbox ou falha SQL retorna `503`. O `/start`, worker one-shot e adaptador de envio existem, mas ainda não foram executados contra um bot real. Também faltam os demais comandos, domínio V2 e coletor Python.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. O projeto Supabase Argos existe em `sa-east-1` (`mkpziasjjfnwvtvuorig`), está saudável e tem a revisão Alembic `20260910_03` aplicada. `telegram_update_inbox` preserva o payload e modela disponibilidade, tentativas, lease, conclusão e dead letter. `telegram_users` separa propriedade e destino. Os repositórios tratam deduplicação, concorrência e atualização monotônica do destino.
- A execução GitHub Actions `34510894628`, no commit `9a9eb20`, aplicou as migrations em PostgreSQL 17 descartável e concluiu os 40 testes. A integração cobre o caminho HTTP até a linha persistida, update repetido, inserção e claim concorrentes, lease expirado, rejeição de conclusão obsoleta e retry agendado.
- O commit `9a9eb20` (2026-09-10) ligou o webhook à inbox. O deploy Render `dep-daheu5ifngtc7397e490` ficou `live` com essa revisão.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime exige `sslmode=verify-full` e `sslrootcert` apontando para um arquivo existente. A CA pública Supabase Root 2021 está versionada e copiada para `/app/certs/prod-ca-2021.crt`; seu fingerprint SHA-256 foi conferido antes da inclusão. Em 10/09/2026, o endpoint direto falhou a partir do Render porque oferece apenas IPv6 no plano atual. A conexão foi movida para o session pooler IPv4, porta 5432, mantendo `verify-full`, e `/health/ready` executou `SELECT 1` com sucesso. A configuração de produção exige `ARGOS_MIGRATION_DATABASE_URL` separado para o Alembic.
- A releitura de `pg_roles`, `pg_auth_members` e privilégios efetivos confirmou `argos_runtime` e `argos_migrator`, ambos `NOLOGIN`, sem atributos administrativos. `argos_runtime_login`, criado pela operação `20260909185425`, não recebe grants diretamente e herda somente o DML de `argos_runtime`; sua senha SCRAM-SHA-256 já foi rotacionada diretamente para o Render. `argos_migrator_login`, criado pela operação `20260910121420`, também não recebe grants ou ownership diretamente e pertence somente a `argos_migrator`, sem `ADMIN OPTION`; ele pode assumir o grupo proprietário e herda `USAGE`/`CREATE` em `public` e os direitos das tabelas atuais. Sua senha inicial permanece desconhecida fora do PostgreSQL até ser rotacionada para o executor administrativo.
- `postgres` continua membro administrativo dos dois grupos para operar objetos pelo provedor. Não reutilizar `postgres`, `service_role` ou o migrador como runtime HTTP. `ARGOS_MIGRATION_DATABASE_URL` está somente no secret store do GitHub Actions; não foi adicionada ao serviço `argos-api`.
- A inspeção dos privilégios padrão mostrou grants amplos de `postgres` e `supabase_admin` para `anon`, `authenticated` e `service_role` em objetos futuros de `public` (tabelas, sequências e funções). Não alterá-los sem avaliar as dependências gerenciadas; até a revisão, novas migrações devem usar a identidade de migração e conceder DML explicitamente ao runtime.
- Supabase Auth e Data API não fazem parte da V2. O usuário informou em 09/09/2026 que desabilitou a Data API no Dashboard e decidiu adiar RLS até a estrutura de dados e as políticas estarem prontas; a sessão não consegue inspecionar diretamente esse toggle.
- A consulta inicial ao Render em 09/09/2026 encontrou a workspace `My Workspace` e o serviço `runbase-system`, ligado a `devbenjaminsantos/runbase-system`; esse serviço não pertence ao Argos e não deve ser alterado.
- O serviço `argos-api` (`srv-dagnegm7bikc73bulvig`) está no projeto Render `Argos` (`prj-dagnkh67bikc73bvd220`), ambiente `Production` (`evm-dagnkh67bikc73bvd22g`), plano Free, região Oregon, com `rootDir=backend`, Dockerfile `Dockerfile` e health check de liveness em `/health`. O deploy `dep-daheu5ifngtc7397e490` do commit `9a9eb20` ficou `live` em 10/09/2026. O serviço `runbase-system` permanece fora do escopo.
- Em 09/09/2026, `/health` respondeu `200` publicamente; rota inexistente, documentação desabilitada e método inválido responderam `404`, `404` e `405` com envelope seguro e ID de correlação. Os 27 testes locais passaram no mesmo commit implantado.
- `ARGOS_TELEGRAM_WEBHOOK_SECRET` já foi configurado no secret store do Render. Após o deploy de `9a9eb20`, `/health` e `/health/ready` retornaram `200`, e o webhook sem segredo retornou `401`. Isso comprova liveness, consulta ao banco e autenticação configurada sem revelar o segredo. A persistência autenticada em produção ainda requer validação manual com o segredo existente; o caminho completo foi comprovado no PostgreSQL real do CI.
- `ARGOS_DATABASE_URL` e `ARGOS_TELEGRAM_WEBHOOK_SECRET` estão no secret store do serviço. A senha de `argos_runtime_login` foi rotacionada em memória e sincronizada com o Render sem ser exibida, gravada localmente ou incluída no histórico de migrações. `ARGOS_TELEGRAM_BOT_TOKEN` ainda está ausente do runtime HTTP. `ARGOS_MIGRATION_DATABASE_URL` também está ausente e deve permanecer fora desse serviço.
- O bot de teste `@argos_teste_bot` foi criado e configurado no BotFather em 11/09/2026. Seu token não foi compartilhado nem versionado; ele ainda deve ser inserido diretamente no secret store do Render antes de chamar a Bot API ou registrar o webhook.
- O plano Free do serviço não disponibiliza shell. Para manter os segredos somente no Render, a aplicação possui configuração idempotente de startup: valida `getMe` contra `argos_teste_bot`, consulta `getWebhookInfo` e registra somente updates de `message` quando a URL ainda não corresponde ao endpoint esperado.
- `/health/ready` retornou `200` pelo endpoint público e o catálogo PostgreSQL confirmou uma sessão de `argos_runtime_login` via Supavisor. `pg_stat_ssl.ssl=false` descreve a conexão interna Supavisor → PostgreSQL e não o trecho cliente Render → pooler, no qual o `psycopg` exige CA e hostname por `verify-full`. `/health` permanece uma verificação de liveness sem consulta ao banco.
- O GitHub Actions é o executor administrativo inicial. O workflow manual `Migrate production database` possui somente `contents: read`, concorrência única e timeout de dez minutos. A execução `34491082455` aplicou `20260910_02` em 10/09/2026. Uma consulta independente confirmou a remoção da tabela legada vazia, a presença da inbox vazia sob ownership de `argos_migrator` e somente `SELECT`/`INSERT`/`UPDATE` para `argos_runtime_login`.
- A execução administrativa `34528124844` aplicou `20260910_03`. Uma consulta independente confirmou `telegram_users` vazia, sob ownership de `argos_migrator`; `argos_runtime_login` possui somente `SELECT`/`INSERT`/`UPDATE`, sem `DELETE`, e `anon`/`authenticated` não possuem leitura. O CI `34527506778` concluiu 44 testes, incluindo upsert concorrente e proteção contra destino obsoleto.
- O commit `c25488e` implementou `/start` como caso de uso de aplicação independente de FastAPI, SQLAlchemy e Bot API. Ele valida comando, identidade e timestamp UTC, atualiza o destino e produz a resposta em texto simples. O CI `34528613256` concluiu 49 testes.
- O commit `ed29274` implementou o núcleo do worker. Ele processa uma entrega por vez, não mantém transação durante o envio, conclui somente depois da porta de saída, reagenda apenas falhas transitórias com resultado conhecido, envia falhas permanentes ou ambíguas para dead letter e deixa exceções inesperadas para recuperação após o lease. O CI `34532088167` concluiu 57 testes.
- O commit `e194d46` implementou o adaptador da Bot API com host fixo, texto simples, timeout, limite de resposta, `retry_after` limitado e erros sem token. O CI `34533252572` foi aprovado.
- O commit `dfb8525` criou `argos-telegram-worker`, um comando one-shot que compõe banco, inbox, identidade, `/start` e saída. O CI `34533540182` concluiu com sucesso o fluxo usando PostgreSQL real e somente a saída Telegram falsa.
- O commit `ba63204` integrou o runner recuperável ao lifespan da API. Ele fica desativado sem token, acorda após o webhook persistir, drena a fila fora do event loop e encerra de forma controlada. Uma única consulta confirmou o CI `34593684038` como concluído com sucesso.
- Os advisors após a migration não apontaram falhas de segurança. O advisor de desempenho informou que os dois índices parciais da inbox ainda não foram usados, resultado esperado enquanto o worker não existe; não removê-los antes de validar o padrão real de claims.

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
- A API cloud está ativa e o segredo do webhook está em uso. Os logins mínimos `argos_runtime_login` e `argos_migrator_login`, assim como seus grupos PostgreSQL, já existem. A associação administrativa dos grupos com `postgres` permanece para operações do provedor.
- Falta no Render somente o token do bot entre as credenciais previstas para o runtime HTTP. A credencial de migração está no GitHub Actions e deve permanecer fora desse serviço.
- As ACLs das duas tabelas atuais estão restritas, mas os privilégios padrão futuros de `public` ainda precisam de revisão manual antes de ampliar o schema ou reativar qualquer API de dados.
- Os advisors de segurança e desempenho do Supabase não retornaram lints após a criação do login. A Data API foi desabilitada manualmente; RLS fica adiado até a estrutura e as políticas estarem prontas. Não aplicar RLS sem decidir as políticas: isso pode bloquear o runtime.
- Não há Blueprint versionado do Render. Os workflows de teste e migração administrativa estão versionados no GitHub Actions.

### A verificar antes do piloto

- Em 11/09/2026, a aceitação real de `/start` confirmou uma inbox `completed`, `attempt_count=1`, zero dead letter e uma identidade persistida. A consulta exibiu somente contagens, estado e tempos, sem IDs Telegram ou payload.
- Em 11/09/2026, o deploy `dep-dai3gte1egvs73daiamg` validou recuperação após reinício. Um registro sintético com lease ativo foi persistido antes do redeploy; após a nova instância ficar `live`, o lease foi expirado e o runner o recuperou, elevou `attempt_count` de 1 para 2, liberou o lease e encerrou o comando inválido em `dead_letter` sem envio externo. O registro sintético foi removido e não houve acesso a IDs ou payloads reais.
- Ao configurar o que falta, preservar `ARGOS_TELEGRAM_WEBHOOK_SECRET` já existente. Confirmar identidade do bot e estado do webhook pela Bot API quando houver acesso ao token; existência do segredo de webhook não comprova existência do bot.
- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, credencial mínima, pool de conexões, latência e limites dos planos. O handshake direto com TLS `verify-full` e a CA do projeto já foi validado a partir do ambiente atual.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Integrar o caso de uso isolado de `/ajuda` ao worker e então liberá-lo na lista fechada do webhook.
2. Implementar `/cancelar` em incremento posterior.
3. Reservar testes de falha da Bot API real para staging isolado ou para uma injeção de falhas que não possa enviar mensagens duplicadas.
4. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
