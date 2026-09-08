# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook retorna `503` para um update válido de propósito. Ainda não há inbox durável, deduplicação efetiva, comandos Telegram, envio de mensagens, domínio V2, repositórios, coletor Python ou job executável.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. A única migração (`20260821_01`) cria `processed_telegram_updates`; ela não basta para retomar processamento após uma queda entre reserva e conclusão.
- A última validação registrada executou `npm run check`, `npm test` (17 testes), `npm run build` e `backend/.venv/bin/python -m pytest` (25 testes). Como não houve mudança de código desde então, esses resultados servem como referência, não como validação da próxima alteração.
- O último commit é `2aa0960` (2026-08-21). Há mudanças documentais não commitadas no working tree; revise `git status` antes de editar documentação.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime deverá exigir TLS com validação de certificado e hostname (`verify-full` e CA adequada). O código atual aceita também `sslmode=require`; isso é uma pendência antes do piloto remoto.
- Supabase Auth e Data API não fazem parte da V2. Se a Data API não for necessária, ela deve permanecer desabilitada.

## Trabalho documental em andamento

- A revisão está registrada em `docs/REPOSITORY_REVIEW_2026-09-08.md`.
- O README, roadmap, backend README, ADRs 0001–0005 e `AZURE_FOUNDATION.md` foram ajustados para remover orientações incompatíveis. `docs/decisions/0006-fractionated-platform.md` foi criado como decisão vigente.
- Essas mudanças são somente documentação e ainda não foram commitadas. Elas devem ser revisadas e preservadas ao iniciar a próxima tarefa.

## Pendências conhecidas

### Confirmadas

- V1 não possui teste de aceitação em Chrome real.
- V2 não processa updates válidos nem persiste usuários, produtos, conversas, observações ou entregas.
- Não há infraestrutura cloud, bot Telegram ou conexão Supabase provisionados/verificados no repositório.
- Não há configuração versionada de deploy Render nem workflow GitHub Actions.

### A verificar antes do piloto

- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, pool de conexões, TLS `verify-full`, latência e limites dos planos.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Revisar e versionar a consolidação documental atual.
2. Antes de aceitar updates Telegram, definir e implementar inbox recuperável, transações, leases e deduplicação com testes em PostgreSQL real.
3. Provisionar o piloto Supabase e validar conexão remota com TLS completo e credenciais mínimas; depois configurar o bot e o deploy da API em incrementos separados.
4. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
