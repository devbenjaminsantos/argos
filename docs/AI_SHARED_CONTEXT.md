# Contexto operacional compartilhado

## Objetivo atual

Preparar a V2 do Argos para um piloto Telegram com API, PostgreSQL e execução de coletas separados, preservando a V1 local da extensão Chrome.

## Estado atual

- A V1 implementa monitoramento local de até três produtos do Mercado Livre: IndexedDB, alarmes aproximados de 12/24 horas, extração, preço-alvo, queda percentual e notificações Chrome. A aceitação manual no Chrome ainda não foi executada.
- A V2 possui uma fundação FastAPI em `backend/`: `GET /health`, middleware de correlação, tratamento seguro de erros e `POST /webhooks/telegram` com segredo em tempo constante, corpo limitado e somente mensagens privadas de texto.
- O webhook retorna `503` para um update válido de propósito. Ainda não há inbox durável, deduplicação efetiva, comandos Telegram, envio de mensagens, domínio V2, repositórios, coletor Python ou job executável.
- PostgreSQL usa SQLAlchemy, Alembic e psycopg. O projeto Supabase Argos existe em `sa-east-1` (`mkpziasjjfnwvtvuorig`), está saudável e tem a revisão Alembic `20260821_01` aplicada. A revisão cria `processed_telegram_updates`; ela não basta para retomar processamento após uma queda entre reserva e conclusão.
- A última validação executou `backend/.venv/bin/python -m pytest` a partir de `backend/` (25 testes passando) e `git diff --check`. A execução a partir da raiz ainda falha em seis testes que assumem o diretório de trabalho `backend/`; isso é uma pendência de ergonomia da suíte, separada desta correção.
- O último commit é `f9c0ca6` (2026-09-08), que versionou o guia de agentes e a consolidação documental. Há uma atualização posterior deste contexto ainda não commitada; revise `git status` antes de editar documentação.

## Decisões atuais

- O ADR 0006 define a plataforma fracionada: Render é candidato inicial para a API, Supabase para PostgreSQL, GitHub Actions para disparar o job e Telegram para entrada/notificações. Grandes nuvens não são destinos contratados do projeto.
- API e job usam o mesmo monólito modular, em processos distintos. Estado, trabalho pendente, leases e entregas devem ficar no PostgreSQL; não no processo nem no filesystem da API.
- Para um banco remoto, o runtime exige `sslmode=verify-full`, com validação de certificado e hostname. A validação da CA apropriada, da credencial mínima e da conectividade real ainda é uma pendência antes do piloto remoto.
- Supabase Auth e Data API não fazem parte da V2. O usuário informou em 09/09/2026 que desabilitou a Data API no Dashboard e decidiu adiar RLS até a estrutura de dados e as políticas estarem prontas; a sessão não consegue inspecionar diretamente esse toggle.

## Documentação recente

- A revisão está registrada em `docs/REPOSITORY_REVIEW_2026-09-08.md`.
- O README, roadmap, backend README, ADRs 0001–0005 e `AZURE_FOUNDATION.md` foram ajustados para remover orientações incompatíveis. `docs/decisions/0006-fractionated-platform.md` foi criado como decisão vigente.
- A consolidação foi versionada no commit `f9c0ca6`.

## Pendências conhecidas

### Confirmadas

- V1 não possui teste de aceitação em Chrome real.
- V2 não processa updates válidos nem persiste usuários, produtos, conversas, observações ou entregas.
- Não há API cloud, bot Telegram ou conexão da aplicação ao Supabase provisionados/verificados no repositório.
- O advisor de segurança do Supabase aponta RLS desabilitado em `public.alembic_version` e `public.processed_telegram_updates`. A Data API foi desabilitada manualmente; RLS fica adiado até a estrutura e as políticas estarem prontas. Não aplicar RLS sem decidir as políticas: isso pode bloquear o runtime.
- Não há configuração versionada de deploy Render nem workflow GitHub Actions.

### A verificar antes do piloto

- Conectividade de Render e do executor com o endpoint PostgreSQL escolhido, pool de conexões, TLS `verify-full`, latência e limites dos planos.
- Recuperação de um update ou envio de alerta quando o processo cai depois de um efeito externo; “exatamente uma entrega” não é garantível sem política explícita para resultado incerto.

### Melhorias futuras, não bloqueantes agora

- Shopee, regras de queda absoluta e menor preço em 30/90 dias não estão implementadas.
- OIDC, extensão conectada à cloud, modo local distribuível e Android pertencem às versões futuras.

## Próximos passos prováveis

1. Configurar e validar conexão remota com CA, TLS completo e credenciais mínimas.
2. Antes de aceitar updates Telegram, definir e implementar inbox recuperável, transações, leases e deduplicação com testes em PostgreSQL real.
3. Depois configurar o bot e o deploy da API em incrementos separados.
4. Executar a aceitação manual da V1 no Chrome quando houver ambiente disponível.
