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

O `main.py`, as dependências de runtime e o endpoint `/health` serão adicionados na próxima entrega da V2.2.
