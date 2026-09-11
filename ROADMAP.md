# Roadmap do Argos

Este documento registra o avanço do projeto e divide as próximas versões em entregas pequenas, testáveis e fáceis de revisar.

## Como atualizar

- `[ ]` ainda não iniciado;
- `[x]` concluído e validado;
- manter apenas uma etapa marcada como **próxima**;
- concluir testes e revisão antes de iniciar o bloco seguinte;
- não implementar vários blocos da versão atual na mesma alteração.

## Estado atual

**Versão implementada:** V1 — Extensão Chrome; fundação, segurança HTTP e inbox durável da V2 em andamento

**Próximo item:** V2.8 — Integrar `/ajuda` ao worker sem ampliar outros comandos

**Última atualização:** 11/09/2026

> **Validação adiada da V1:** a extensão foi construída e validada automaticamente, mas o teste de aceitação no Chrome será feito posteriormente em um computador Windows. O ambiente atual utiliza Safari. Essa pendência não bloqueia o planejamento da V2.

### Leitura da V2 em 10/09/2026

| Bloco | Estado comprovado | Falta |
| --- | --- | --- |
| Runtime e migrações | Logins mínimos separados, TLS `verify-full`, readiness com consulta e Alembic administrativo validados | Revisar privilégios padrão do provedor para objetos criados fora de `argos_migrator` |
| Webhook e inbox | Autenticação, limites, persistência, deduplicação, concorrência e recuperação validados; webhook real persistiu e concluiu o primeiro update | Restringir explicitamente os comandos aceitos |
| Identidade e `/start` | Fluxo real mensagem → inbox → identidade → resposta concluído em produção | Ampliar comandos em incrementos posteriores |
| Bot Telegram | `@argos_teste_bot`, token, identidade e webhook validados sem expor segredos | Validar rotação em etapa operacional posterior |
| Domínio do monitoramento | Regras da V1 disponíveis como referência | Usuários, produtos, preços, conversas, coleta e notificações da V2 |

---

## V1 — Extensão Chrome

- [x] Configurar TypeScript, Manifest V3, build e testes.
- [x] Criar interface dedicada ao Mercado Livre.
- [x] Cadastrar produtos a partir da página aberta.
- [x] Limitar o monitoramento a três produtos.
- [x] Armazenar produtos e histórico no IndexedDB.
- [x] Extrair título, identificador e preço do Mercado Livre.
- [x] Configurar preço-alvo e queda percentual relevante.
- [x] Configurar verificações a cada 12 ou 24 horas.
- [x] Executar coleta periódica pelo service worker.
- [x] Enviar notificações locais pelo Chrome.
- [x] Impedir notificações equivalentes duplicadas.
- [x] Validar URLs e origens das mensagens.
- [x] Aplicar controles contra XSS e requisições arbitrárias.
- [x] Documentar segurança e limitações da extensão.
- [x] Validar tipos, testes, build, dependências e manifesto.
- [ ] Executar teste de aceitação no Chrome para Windows — **adiado até haver acesso ao ambiente**.

**Resultado:** a V1 funciona localmente, sem conta, servidor, endpoint remoto ou segredos distribuídos no pacote.

---

## V2 — MVP Telegram em cloud

A V2 entregará o primeiro Argos cloud utilizável. O Telegram será interface, identidade inicial e canal de notificação. OIDC, extensão cloud, modo local e Android ficam fora desta versão.

Decisões relacionadas:

- [`ADR 0001 — Desenvolvimento local e execução em nuvem`](docs/decisions/0001-local-vs-cloud.md);
- [`ADR 0003 — FastAPI e identidades da V2`](docs/decisions/0003-backend-stack-and-auth.md);
- [`ADR 0004 — Telegram como V2`](docs/decisions/0004-telegram-mvp.md);
- [`ADR 0006 — Plataforma fracionada sem grandes nuvens`](docs/decisions/0006-fractionated-platform.md).

### V2.1 — Recorte e contratos do MVP Telegram — CONCLUÍDA

- [x] Escolher FastAPI e uma arquitetura cloud portátil; a infraestrutura vigente está no ADR 0006.
- [x] Escolher Telegram como interface e canal do MVP.
- [x] Limitar o MVP a conversas privadas e Mercado Livre.
- [x] Identificar o proprietário por `telegram_user_id`, nunca por `username`.
- [x] Definir os contratos de repositório, coletor e notificador em [`docs/V2_CONTRACTS.md`](docs/V2_CONTRACTS.md).
- [x] Definir comandos, estados da conversa e respostas de erro em [`docs/V2_TELEGRAM_CONVERSATION.md`](docs/V2_TELEGRAM_CONVERSATION.md).
- [x] Atualizar o modelo de ameaças para Telegram, webhook, SSRF e banco cloud em [`docs/V2_SECURITY.md`](docs/V2_SECURITY.md).

**Critério de conclusão:** recorte e contratos documentados, sem servidor funcional.

### V2.2 — FastAPI local e contêiner — CONCLUÍDA

- [x] Criar o monólito modular Python em [`backend/`](backend/).
- [x] Criar `GET /health` e tratamento centralizado de erros.
- [x] Configurar testes e variáveis sem segredos no repositório.
- [x] Criar a definição reproduzível da imagem com Python fixado, dependências travadas e usuário sem privilégios.
- [x] Validar build, execução sem privilégios e `/health` dentro do contêiner.

**Critério de conclusão:** API e testes passam localmente e a imagem inicia com `/health` funcional.

### V2.3 — Escolha da infraestrutura cloud — CONCLUÍDA

- [x] Definir API, PostgreSQL e job como responsabilidades independentes.
- [x] Escolher Render, Supabase e GitHub Actions como candidatos iniciais do piloto.
- [x] Registrar que grandes nuvens não serão destinos contratados; nesta etapa não foram provisionados API ou job cloud (o PostgreSQL foi provisionado posteriormente em V2.7).

**Critério de conclusão:** arquitetura, limites de custo e restrições de provedor documentados, sem API ou job cloud provisionados nesta etapa.

### V2.4 — Bot de teste e segredos — CONCLUÍDA

- [x] Criar e configurar o bot exclusivo de desenvolvimento `@argos_teste_bot` no BotFather, limitado a conversas privadas e com somente `/start` anunciado.
- [x] Guardar e validar `ARGOS_TELEGRAM_WEBHOOK_SECRET` somente no secret store do Render; o endpoint público rejeita segredo ausente ou inválido com `401`.
- [x] Guardar `ARGOS_TELEGRAM_BOT_TOKEN` somente no secret store do Render e registrar o webhook do bot após criar sua identidade.
- [x] Confirmar a identidade `@argos_teste_bot` com a Bot API durante a inicialização segura.
- [x] Mascarar o token na configuração e no adaptador, substituir erros de transporte por códigos seguros e testar que a credencial não aparece nas exceções ou representações.
- [x] Confirmar após a configuração real que logs do Render e do executor não contêm token.

> O plano Free não oferece shell neste serviço. A aplicação configura o webhook de forma idempotente na inicialização quando recebe a URL e o username esperados: valida `getMe`, recusa outra identidade, consulta `getWebhookInfo` e chama `setWebhook` somente quando necessário.

> Em 11/09/2026, o bot `@argos_teste_bot` foi criado e configurado. O token ainda deve ser armazenado diretamente no Render antes de confirmar a identidade pela Bot API; não enviar ou versionar a credencial.

**Critério de conclusão:** a API consulta a identidade do bot sem expor credenciais.

### V2.5 — Webhook seguro — CONCLUÍDA

- [x] Criar `POST /webhooks/telegram`.
- [x] Validar `X-Telegram-Bot-Api-Secret-Token` em tempo constante.
- [x] Limitar o corpo antes do parsing e aceitar somente updates de mensagem de texto.
- [x] Restringir a persistência a `/start`; texto e comandos desconhecidos recebem `200` sem entrar na inbox nem provocar retries do Telegram.
- [x] Recusar grupos e aceitar apenas conversas privadas.
- [x] Responder rapidamente sem executar scraping no request.
- [x] Testar segredo ausente, inválido, payload excessivo e conteúdo malformado.
- [x] Persistir e deduplicar o update antes de responder `200`; ausência da inbox ou falha SQL retorna `503` para permitir nova entrega.
- [x] Validar em produção uma entrega autenticada real e confirmar no PostgreSQL uma inbox concluída em uma tentativa, sem dead letter, além da identidade persistida.

**Critério de conclusão:** somente updates autenticados e válidos são aceitos.

### V2.6 — Domínio e regras

- [ ] Implementar usuário Telegram, produto, observação e entrega de notificação.
- [ ] Armazenar dinheiro em unidade segura e portar regras da V1.
- [ ] Aplicar limite de três produtos por usuário.
- [ ] Definir estados de coleta e da conversa.
- [ ] Criar testes sem dependência de FastAPI, Telegram ou banco.

**Critério de conclusão:** regras funcionam isoladamente e mantêm paridade com a V1.

### V2.7 — Supabase PostgreSQL e isolamento

- [x] Adotar `psycopg` e remover dependências nativas de banco anteriores.
- [x] Configurar SQLAlchemy e migrações versionadas com Alembic.
- [x] Criar a migração inicial de `processed_telegram_updates` e validar `upgrade`/`downgrade` em PostgreSQL 17 efêmero.
- [x] Criar o projeto Supabase Argos em `sa-east-1` com estimativa de US$ 0/mês, sem add-ons solicitados.
- [x] Aplicar a revisão Alembic `20260821_01` e confirmar `alembic_version` no PostgreSQL remoto.
- [x] Desabilitar a Data API no Dashboard do Supabase (RLS será definido quando a estrutura estiver pronta).
- [x] Exigir `sslmode=verify-full` e `sslrootcert` existente na configuração de produção.
- [x] Validar o handshake remoto do endpoint direto com a CA Supabase Root 2021; `psycopg` alcançou a etapa de autenticação e um hostname incorreto foi rejeitado, sem expor senha.
- [x] Separar a configuração `ARGOS_DATABASE_URL` (runtime) de `ARGOS_MIGRATION_DATABASE_URL` (migrações) e exigir a segunda em produção.
- [x] Criar os grupos PostgreSQL `argos_runtime` e `argos_migrator` sem `LOGIN` ou senha; o runtime recebeu somente `SELECT`, `INSERT` e `UPDATE` na inbox, e os grants das roles padrão foram revogados nas tabelas existentes.
- [x] Conceder `USAGE`/`CREATE` no schema `public` e ownership das tabelas atuais ao grupo `argos_migrator`, em operações administrativas separadas e validadas.
- [ ] Revisar os privilégios padrão do provedor para novas tabelas, sequências e funções no schema `public`; a inspeção atual ainda mostra grants amplos quando o owner é `postgres` ou `supabase_admin`.
- [x] Criar o projeto Render `Argos` (`prj-dagnkh67bikc73bvd220`), seu ambiente `Production` (`evm-dagnkh67bikc73bvd22g`) e associar somente o serviço `argos-api` (`srv-dagnegm7bikc73bulvig`).
- [x] Corrigir e confirmar o serviço web Docker do Argos no Render, com `devbenjaminsantos/argos`, diretório `backend`, health check `/health` e deploy `live` do commit `9a9eb20`.
- [x] Configurar e validar o segredo mínimo do webhook no secret store do provedor de execução.
- [x] Criar `argos_runtime_login` sem privilégios próprios, vinculá-lo somente ao grupo `argos_runtime` e validar seus atributos e privilégios efetivos no PostgreSQL remoto.
- [x] Configurar `ARGOS_DATABASE_URL` no Render pelo session pooler IPv4, com `sslmode=verify-full`, CA Supabase Root 2021 e pool limitado; `/health/ready` executou `SELECT 1` e o PostgreSQL confirmou a sessão de `argos_runtime_login`.
- [x] Criar `argos_migrator_login` sem privilégios próprios e vinculá-lo somente ao grupo `argos_migrator`.
- [x] Configurar `argos_migrator_login` somente no GitHub Actions, assumir `argos_migrator` e validar DDL transacional reversível mais `alembic upgrade head` pelo workflow manual.
- [x] Criar a inbox de updates Telegram com deduplicação, disponibilidade, tentativas e leases.
- [x] Criar a identidade Telegram com ownership por `telegram_user_id`, destino separado por `chat_id`, upsert monotônico e grants mínimos.
- [ ] Criar conversas, produtos, preços e notificações.
- [x] Implementar o repositório da inbox e seus índices operacionais.
- [ ] Implementar os repositórios restantes e índices de propriedade.
- [ ] Testar que um `telegram_user_id` nunca acessa dados de outro.

**Critério de conclusão:** migrações são reproduzíveis, schema público não está exposto indevidamente, credenciais não são versionadas e isolamento é comprovado.

### V2.8 — Usuário, deduplicação e conversa — EM ANDAMENTO

- [x] Definir a inbox durável com payload, estados, tentativas, disponibilidade, lease, conclusão, erro e índices de recuperação; a migração recusa substituir tabelas que contenham dados.
- [x] Implementar o caso de uso isolado de `/start`, com validação do comando e identidade, upsert do proprietário e resposta em texto simples.
- [x] Implementar `/ajuda` como caso de uso isolado, listando somente comandos disponíveis; integração ao worker fica no próximo incremento.
- [ ] Implementar `/cancelar` em incremento posterior.
- [x] Integrar `/start` ao núcleo do worker com claim, conclusão, retry apenas para falha transitória confirmada, dead letter para falha permanente ou resultado incerto e recuperação por lease para exceção inesperada.
- [x] Persistir usuário por `telegram_user_id` e destino por `chat_id`; a revisão `20260910_03` e o repositório foram validados com concorrência em PostgreSQL 17 e aplicados em produção.
- [x] Implementar a persistência recuperável e a deduplicação por `update_id`, com claims concorrentes, leases, retry e ligação ao webhook validados em PostgreSQL 17 no GitHub Actions.
- [x] Validar em produção a recuperação após reinício: a nova instância retomou um lease sintético expirado, incrementou a tentativa, liberou o lease e encerrou o comando inválido sem chamar a Bot API; o registro de teste foi removido.
- [x] Manter retry transitório confirmado e resultado incerto cobertos por adaptadores determinísticos; não provocar falhas artificiais contra a Bot API real enquanto não houver staging isolado ou injeção de falhas segura.
- [ ] Implementar rate limit e máquina de estados persistente.

**Critério de conclusão:** updates repetidos não duplicam ações e conversas sobrevivem a reinícios.

#### Curso de ação atual

1. [x] Criar a tabela e o repositório de identidade Telegram, mantendo `telegram_user_id` como proprietário e `chat_id` somente como destino; validar upsert concorrente e grants mínimos.
2. [x] Implementar o caso de uso isolado de `/start`, que cria ou atualiza a identidade e produz a resposta definida sem depender de FastAPI, PostgreSQL ou da Bot API.
3. [x] Criar o núcleo do worker que reivindica a inbox com lease, executa `/start` e conclui ou reagenda o update sem manter transação aberta durante chamadas externas.
4. [x] Implementar o adaptador da Bot API com host fixo, texto simples, timeout, limite de resposta e classificação segura de falhas, sem configurar credenciais reais.
5. [x] Criar o comando one-shot do worker e validar PostgreSQL → claim → `/start` → usuário → saída falsa → conclusão.
6. [x] Integrar um runner recuperável ao processo HTTP do piloto gratuito, despertado após a persistência e pelo polling de recuperação, sem manter trabalho apenas em memória; o job de coleta permanece separado.
7. [x] Criar o bot de desenvolvimento, armazenar `ARGOS_TELEGRAM_BOT_TOKEN` no Render, confirmar sua identidade, registrar o webhook e executar a aceitação ponta a ponta.

O frontend pode continuar sendo desenhado em paralelo. Ele não bloqueia essa sequência e deve depender dos contratos de aplicação, sem acessar diretamente tabelas ou detalhes da Bot API.

### V2.9 — Cadastro de produtos pelo Telegram

- [ ] Implementar `/adicionar`, `/produtos` e `/remover`.
- [ ] Coletar URL, apelido, preço-alvo e intervalo em passos separados.
- [ ] Validar entrada e permitir confirmação antes de salvar.
- [ ] Escopar todas as operações ao usuário Telegram.

**Critério de conclusão:** dois usuários gerenciam listas isoladas com limite individual de três produtos.

### V2.10 — Segurança de URLs e SSRF

- [ ] Aceitar apenas HTTPS e hosts explicitamente suportados.
- [ ] Rejeitar credenciais, portas alternativas e URLs malformadas.
- [ ] Resolver DNS e bloquear destinos privados, locais ou reservados.
- [ ] Validar cada redirecionamento e limitar tamanho e duração da resposta.
- [ ] Criar testes com URLs maliciosas.

**Critério de conclusão:** o coletor não funciona como proxy genérico nem alcança rede interna.

### V2.11 — Coleta manual do Mercado Livre

- [ ] Portar o adaptador do Mercado Livre para o back-end.
- [ ] Implementar `/verificar` para um produto cadastrado.
- [ ] Registrar sucesso e falhas explícitas, nunca preço zero.
- [ ] Criar fixtures e testes do extrator.

**Critério de conclusão:** uma verificação manual registra preço e responde pelo Telegram.

### V2.12 — Histórico, job e alertas

- [ ] Comparar preço atual, último preço válido e preço-alvo.
- [ ] Criar comando de job separado da API.
- [ ] Agendar o comando de coleta externamente, inicialmente com GitHub Actions, em UTC.
- [ ] Impedir coletas concorrentes e aplicar retentativas limitadas.
- [ ] Enviar alerta pelo Telegram, reservar entregas e tratar resultado externo incerto.

**Critério de conclusão:** uma queda reserva uma entrega de alerta de forma idempotente e o job recupera trabalho após reinícios.

### V2.13 — Fechamento do MVP

- [ ] Configurar métricas, logs sem dados sensíveis e prontidão.
- [ ] Revisar permissões, backup, rollback e quotas do Render e Supabase.
- [ ] Testar cold start, falhas do Telegram, bloqueio da loja e banco indisponível.
- [ ] Executar teste de aceitação com dois usuários.

**Critério de conclusão:** o usuário cadastra um link e recebe um alerta real sem acessar código ou infraestrutura cloud.

---

## V3 — Plataforma cloud e integração da extensão

- [ ] Escolher provedor OIDC e implementar Authorization Code com PKCE.
- [ ] Identificar contas por `issuer` + `subject` e vincular identidade Telegram.
- [ ] Criar API pública de produtos e histórico escopada ao usuário autenticado.
- [ ] Integrar a extensão Chrome com o modo cloud.
- [ ] Sincronizar sem duplicar produtos ou corromper o modo local da V1.
- [ ] Adicionar canais de notificação além do Telegram.

**Critério de conclusão:** uma conta cloud acessa os mesmos produtos pelo Telegram e pela extensão.

---

## V4 — Back-end local/autohospedado

- [ ] Definir sistemas operacionais e banco suportados.
- [ ] Criar instalação, atualização e serviço em segundo plano.
- [ ] Proteger API por loopback e credencial por instalação.
- [ ] Implementar backup, diagnóstico e desinstalação.
- [ ] Criar testes de instalação nos sistemas suportados.

**Critério de conclusão:** usuário instala e remove o Argos sem configurar Python, banco ou scheduler.

---

## V5 — Android

- [ ] Criar aplicativo com Kotlin e Jetpack Compose.
- [ ] Integrar autenticação e API cloud.
- [ ] Gerenciar produtos, histórico e notificações.

---

## Fora das versões atuais

- [ ] Comparação automática entre anúncios equivalentes.
- [ ] Recomendação de melhor momento de compra.
- [ ] Relatórios em PDF e CSV.
- [ ] Gráficos avançados de histórico.
- [ ] Suporte à Shopee e a outras lojas.
- [ ] Extração de componentes para microsserviços, somente se houver necessidade comprovada.
