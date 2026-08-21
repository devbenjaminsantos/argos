# ADR 0004 — Telegram como V2

**Status:** aceita  
**Data:** 19/08/2026

> **Refinamento:** o recorte Telegram permanece aceito. Render, Supabase e agendamento externo substituem os serviços Azure citados originalmente, conforme o [`ADR 0005`](0005-render-supabase-platform.md).

## Contexto

Integrar imediatamente OIDC, extensão cloud e múltiplos clientes aumentaria o tempo até a primeira versão utilizável. O Telegram já oferece interface conversacional, entrega de mensagens e uma identidade numérica estável para o piloto.

## Decisão

A V2 será o MVP Telegram do Argos:

- conversa privada como única interface;
- `telegram_user_id` como identidade do proprietário;
- `chat_id` como destino de respostas e alertas;
- Mercado Livre como única loja;
- até três produtos por usuário;
- cadastro por etapas, coleta manual e periódica;
- alertas enviados pelo próprio bot;
- FastAPI com infraestrutura cloud definida separadamente no ADR 0005.

OIDC e integração cloud da extensão passam para a V3. O modo local passa para a V4 e Android para a V5.

## Segurança

- token do bot armazenado somente como secret da plataforma de execução;
- webhook protegido por secret próprio;
- updates deduplicados por `update_id`;
- grupos recusados;
- `username` nunca usado como chave de propriedade;
- scraping fora do ciclo de resposta do webhook;
- validação contra SSRF antes de ativar URLs fornecidas pelos usuários.

## Consequências

- o schema nasce multiusuário, mas sem OIDC na V2;
- a futura conta OIDC deverá ser vinculada à identidade Telegram sem transferências implícitas;
- Telegram é um adaptador de entrada e saída, não uma dependência do domínio;
- API, banco, coleta e regras continuarão reutilizáveis por extensão, Android e modo local.
