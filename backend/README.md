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

- `domain`: entidades, valores e regras de negócio; não importa FastAPI, SQLAlchemy, Telegram ou Azure;
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

A aplicação é criada por uma factory e expõe inicialmente apenas `GET /health`. A documentação interativa permanece desabilitada por padrão e os erros usam um envelope seguro com identificador de correlação.

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

A imagem usa Python 3.14 sobre Debian 12, instala o Microsoft ODBC Driver 18 e executa a API com um usuário sem privilégios. Dependências de runtime são resolvidas pelo arquivo `requirements.runtime.lock`; dependências de teste não entram na imagem.

Construa a partir deste diretório:

```bash
docker build --platform linux/amd64 --tag argos-backend:dev .
```

Valide o driver incluído:

```bash
docker run --rm --entrypoint odbcinst argos-backend:dev -q -d
```

Inicie a API localmente:

```bash
docker run --rm --publish 8000:8000 argos-backend:dev
```

O contêiner não contém `.env`, tokens, testes ou ferramentas de desenvolvimento. Segredos serão injetados por referências seguras do Azure Container Apps nas etapas posteriores.
