# Guia para agentes

## Objetivo

Argos monitora preços de produtos e avisa o usuário quando o preço-alvo ou uma queda percentual relevante é atingida. A V1 é uma extensão Chrome local para Mercado Livre. A V2 evolui o produto para um bot Telegram com backend Python, persistência PostgreSQL e coleta remota.

## Regra de início e colaboração

Em toda tarefa, leia primeiro este arquivo, depois `docs/AI_SHARED_CONTEXT.md` e, por fim, os arquivos de código ligados à tarefa. O contexto compartilhado orienta a investigação, mas não substitui a inspeção do código: código, testes, configuração e histórico Git são a fonte de verdade do que está implementado.

Antes de uma alteração significativa, confira `git status` e as mudanças em andamento. Não sobrescreva trabalho existente. Para trabalho paralelo, divida módulos ou use branches/worktrees; os arquivos de contexto não resolvem conflitos de escrita.

Atualize `docs/AI_SHARED_CONTEXT.md` ao concluir uma mudança relevante, descoberta recorrente, decisão que afete sessões futuras ou alteração do próximo passo. Mantenha-o curto e atual. Decisões estruturais duradouras pertencem a um ADR em `docs/decisions/` e, quando útil, a este arquivo. Corrija o contexto se ele divergir do código.

## Arquitetura e diretórios

```text
src/                         Extensão Chrome Manifest V3 (V1)
  application/               Casos de uso da extensão
  background/                Service worker e alarmes
  content/                   Extração da página aberta
  domain/                    Produtos, observações e regras de preço
  infrastructure/database/   IndexedDB
  offscreen/                 Parser de HTML para coletas em segundo plano
  security/                  Normalização e validação de URL
  stores/mercado-livre/      Adaptador de loja
  popup/                     Interface da extensão
tests/                       Testes Vitest da extensão

backend/                     Backend Python da V2
  src/argos/domain/          Regras e entidades sem dependências de framework
  src/argos/application/     Casos de uso e portas
  src/argos/api/             FastAPI, schemas e middleware HTTP
  src/argos/infrastructure/  PostgreSQL, Telegram, scrapers e scheduler
  migrations/                Migrações Alembic
  tests/                     Testes pytest
docs/                        Segurança, contratos, roadmap e ADRs
```

A direção permitida no backend é `api -> application -> domain` e `infrastructure -> application -> domain`; a composição conecta portas e adaptadores. O domínio não importa FastAPI, SQLAlchemy, Telegram ou modelos ORM.

## Stack e convenções

- V1: TypeScript estrito, Manifest V3, IndexedDB, esbuild e Vitest. Valores monetários usam centavos inteiros; falha de coleta nunca é preço zero.
- V2: Python 3.12–3.14, FastAPI, SQLAlchemy, Alembic, psycopg e PostgreSQL. Configuração entra por `ARGOS_*`; segredos usam ambiente/secret store, nunca Git.
- Preserve adaptadores por loja. Mercado Livre é a única loja implementada.
- Prefira nomes claros, tipos explícitos e mudanças pequenas, isoladas e testáveis. Não transforme o backend em microsserviços antes de necessidade comprovada.
- Atualize documentação de produto quando uma mudança alterar comportamento público. Mantenha HTML de fallback e traduções sincronizados somente se houver `data-i18n` envolvido.

## Comandos

Na raiz, para a extensão:

```bash
npm install
npm run check
npm test
npm run build
```

Em `backend/`, para desenvolvimento e testes:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
python -m uvicorn argos.main:app --app-dir src --host 127.0.0.1 --port 8000
.venv/bin/alembic upgrade head
```

Não há comando de lint separado; `npm run check` é a verificação estática da extensão. A imagem do backend é construída de `backend/` com `docker build --platform linux/amd64 --tag argos-backend:dev .`.

## Segurança e restrições

- V1 aceita somente URLs HTTPS de produto do Mercado Livre, sem credenciais ou portas alternativas; preserve a normalização, revalidação de redirecionamento, limite de resposta e `credentials: "omit"`.
- Conteúdo de lojas e content scripts é não confiável. Não execute HTML remoto, não use `innerHTML` para conteúdo coletado e valide mensagens entre contextos da extensão.
- V2 aceita somente conversas privadas no Telegram. Use `telegram_user_id` como proprietário e `chat_id` apenas como destino; nunca autorize por `username`.
- Webhook e coleta devem ser idempotentes. Faça persistência durável antes de confirmar efeitos externos e mantenha todas as consultas escopadas ao proprietário.
- Qualquer coletor cloud deve aplicar a política de SSRF em `docs/V2_SECURITY.md`: allowlist de hosts, DNS seguro, bloqueio de rede privada, redirecionamentos validados e limites de tempo/tamanho.
- O projeto não contratará Azure, AWS, Google Cloud, Oracle Cloud ou outro grande provedor para hospedar o Argos. A decisão vigente é o ADR 0006: API, PostgreSQL e job são responsabilidades separadas.

## Limites operacionais

- Testes automatizados não substituem uma validação manual no Chrome quando a mudança afetar APIs ou ciclo de vida da extensão.
- Não deduza funcionalidades da V2 pela estrutura de diretórios; consulte `docs/AI_SHARED_CONTEXT.md` e inspecione o código antes de modificar comandos, repositórios, coleta ou notificações.
- Migrações não executam automaticamente no boot da API. O runtime não deve usar filesystem local como armazenamento persistente.
