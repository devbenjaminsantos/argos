# Back-end do Argos

Este diretório contém o monólito modular Python da V2. Ele é separado da extensão Chrome para que os dois produtos possam evoluir e ser testados sem misturar toolchains ou dependências.

## Estrutura

```text
backend/
├── src/argos/
│   ├── api/
│   │   ├── dependencies/
│   │   └── routes/
│   ├── application/
│   │   ├── ports/
│   │   ├── services/
│   │   └── use_cases/
│   ├── domain/
│   │   ├── notifications/
│   │   ├── prices/
│   │   └── products/
│   └── infrastructure/
│       ├── database/
│       ├── scheduler/
│       ├── scrapers/
│       │   └── mercado_livre/
│       └── telegram/
├── tests/
└── pyproject.toml
```

## Limites dos módulos

- `domain`: entidades, valores e regras de negócio; não importa FastAPI, SQLAlchemy, Telegram ou qualquer provedor cloud;
- `application`: casos de uso e portas descritas em [`../docs/V2_CONTRACTS.md`](../docs/V2_CONTRACTS.md); depende apenas do domínio;
- `api`: entrada HTTP, validação de transporte e composição de respostas; chama casos de uso;
- `infrastructure`: implementações de banco, coleta, scheduler e Telegram para as portas da aplicação;
- a raiz do pacote será o ponto de composição das implementações, sem mover regras de negócio para a inicialização.

A direção permitida é:

```text
api ──────────────► application ──► domain
infrastructure ───► application ──► domain
        composição conecta portas e adaptadores
```

Importações no sentido contrário são proibidas. Em particular, o domínio não conhece DTOs HTTP, modelos ORM nem payloads do Telegram.

## Decisões estruturais

Os modelos ficam dentro dos respectivos módulos de domínio, em vez de um diretório global `models`. Contratos de repositório ficam em `application/ports`, e suas implementações ficam em `infrastructure/database`. Isso evita que modelos de banco se tornem acidentalmente o modelo de negócio.

## API local

A aplicação é criada por uma factory e expõe `GET /health` e a fronteira inicial `POST /webhooks/telegram`. A documentação interativa permanece desabilitada por padrão e os erros usam um envelope seguro com identificador de correlação.

O webhook:

- compara `X-Telegram-Bot-Api-Secret-Token` em tempo constante;
- limita o corpo antes de interpretar JSON;
- aceita somente mensagens de texto em chats privados;
- não registra corpo, token ou segredo nos erros;
- responde `503` para um update válido enquanto ainda não existir persistência e deduplicação, permitindo que o Telegram tente entregá-lo novamente.

O limite padrão do corpo é 64 KiB e pode ser reduzido com `ARGOS_TELEGRAM_WEBHOOK_MAX_BODY_BYTES`. O segredo deve existir somente em `ARGOS_TELEGRAM_WEBHOOK_SECRET` fora do Git.

## PostgreSQL e migrações

A persistência usa SQLAlchemy 2, Alembic e `psycopg`. A URL deve usar `postgresql+psycopg`; em produção a configuração exige `sslmode=verify-full` e um `sslrootcert` apontando para a CA do projeto. O arquivo da CA deve ser baixado no Dashboard do Supabase e montado no runtime; no Render, um Secret File fica disponível em `/etc/secrets/<nome>`. A credencial mínima permanece somente no secret store. O handshake do endpoint direto foi validado com a CA em 09/09/2026, um hostname incorreto foi rejeitado e `psycopg` alcançou a autenticação; ainda falta configurar e testar a credencial do processo no provedor de execução. Consulte as instruções oficiais de [conexão SSL](https://supabase.com/docs/guides/database/psql#connecting-with-ssl) e [Secret Files do Render](https://render.com/docs/configure-environment-variables#secret-files).

Depois de definir `ARGOS_DATABASE_URL` fora do Git, execute a partir de `backend/`. Essa é a identidade do runtime. Em produção, defina também `ARGOS_MIGRATION_DATABASE_URL` com uma identidade separada e de uso pontual; o Alembic exige essa variável e não reutiliza a credencial do runtime.

No projeto Supabase do Argos, as operações [`ops/supabase/20260909_argos_roles.sql`](../ops/supabase/20260909_argos_roles.sql), [`ops/supabase/20260909_argos_migrator_schema.sql`](../ops/supabase/20260909_argos_migrator_schema.sql) e [`ops/supabase/20260909_argos_migrator_ownership.sql`](../ops/supabase/20260909_argos_migrator_ownership.sql) criaram os grupos `argos_runtime` e `argos_migrator` sem `LOGIN` e sem senha, concederam DDL ao migrador e transferiram a ownership das tabelas atuais. O runtime recebeu somente `SELECT`, `INSERT` e `UPDATE` em `processed_telegram_updates`; não use `postgres`, `service_role` ou `argos_migrator` como credencial da API. Ainda falta criar uma identidade `LOGIN` de cada carga e validar uma migração estrutural com a identidade de migração. Os privilégios padrão do provedor para objetos criados por `postgres` ou `supabase_admin` no schema `public` continuam amplos; até essa revisão, novas migrações devem usar a identidade de migração e grants explícitos.

```bash
.venv/bin/alembic upgrade head
```

Para reverter a última migração durante desenvolvimento:

```bash
.venv/bin/alembic downgrade -1
```

As migrações não são executadas automaticamente ao iniciar a API. O deploy deverá aplicá-las explicitamente uma única vez antes de liberar uma versão que dependa do novo schema.

Crie o ambiente e instale também as dependências de desenvolvimento:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

O arquivo `.env.example` contém apenas configuração não sensível e nomes de variáveis. Copie-o para `.env`, preencha segredos localmente e exporte as variáveis antes de iniciar. O `.env` real é ignorado pelo Git.

Execute a partir de `backend/`:

```bash
python -m uvicorn argos.main:app --app-dir src --host 127.0.0.1 --port 8000
```

Para executar os testes:

```bash
.venv/bin/python -m pytest
```

## Contêiner

A imagem usa Python 3.14 sobre Debian 12, inclui o driver binário `psycopg`, os arquivos versionados do Alembic e executa a API com um usuário sem privilégios. Dependências de runtime são resolvidas pelo arquivo `requirements.runtime.lock`; dependências de teste não entram na imagem.

Construa a partir deste diretório:

```bash
docker build --platform linux/amd64 --tag argos-backend:dev .
```

Valide as migrações incluídas sem conectar ao banco:

```bash
docker run --rm \
  --env ARGOS_MIGRATION_DATABASE_URL=postgresql+psycopg://argos-migration:local@localhost/argos?sslmode=require \
  argos-backend:dev \
  alembic upgrade head --sql
```

Inicie a API localmente:

```bash
docker run --rm --publish 8000:8000 argos-backend:dev
```

O contêiner não contém `.env`, tokens, testes ou ferramentas de desenvolvimento. Segredos serão injetados pelas variáveis secretas do Render e, para o job, pelos secrets do GitHub Actions.
