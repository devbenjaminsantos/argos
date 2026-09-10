# Roadmap do Argos

Este documento registra o avanço do projeto e divide as próximas versões em entregas pequenas, testáveis e fáceis de revisar.

## Como atualizar

- `[ ]` ainda não iniciado;
- `[x]` concluído e validado;
- manter apenas uma etapa marcada como **próxima**;
- concluir testes e revisão antes de iniciar o bloco seguinte;
- não implementar vários blocos da versão atual na mesma alteração.

## Estado atual

**Versão implementada:** V1 — Extensão Chrome

**Próximo item:** V2.7 — Configurar credencial mínima e validar o runtime

**Última atualização:** 09/09/2026

> **Validação adiada da V1:** a extensão foi construída e validada automaticamente, mas o teste de aceitação no Chrome será feito posteriormente em um computador Windows. O ambiente atual utiliza Safari. Essa pendência não bloqueia o planejamento da V2.

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

### V2.4 — Bot de teste e segredos

- [ ] Criar um bot exclusivo de desenvolvimento no BotFather.
- [x] Guardar e validar `ARGOS_TELEGRAM_WEBHOOK_SECRET` somente no secret store do Render; o endpoint público rejeita segredo ausente ou inválido com `401`.
- [ ] Guardar `ARGOS_TELEGRAM_BOT_TOKEN` somente no secret store do Render e registrar o webhook do bot após criar sua identidade.
- [ ] Confirmar a identidade do bot com a Bot API.
- [ ] Garantir que tokens nunca apareçam em código, erros ou logs.

**Critério de conclusão:** a API consulta a identidade do bot sem expor credenciais.

### V2.5 — Webhook seguro

- [x] Criar `POST /webhooks/telegram`.
- [x] Validar `X-Telegram-Bot-Api-Secret-Token` em tempo constante.
- [x] Limitar o corpo antes do parsing e aceitar somente updates de mensagem de texto.
- [ ] Restringir os comandos aceitos.
- [x] Recusar grupos e aceitar apenas conversas privadas.
- [x] Responder rapidamente sem executar scraping no request.
- [x] Testar segredo ausente, inválido, payload excessivo e conteúdo malformado.
- [ ] Persistir e deduplicar o update antes de responder com sucesso; até lá, retornar `503` para updates válidos.

**Critério de conclusão:** somente updates autenticados e válidos são aceitos.

### V2.6 — Domínio e regras

- [ ] Implementar usuário Telegram, produto, observação e entrega de notificação.
- [ ] Armazenar dinheiro em unidade segura e portar regras da V1.
- [ ] Aplicar limite de três produtos por usuário.
- [ ] Definir estados de coleta e da conversa.
- [ ] Criar testes sem dependência de FastAPI, Telegram ou banco.

**Critério de conclusão:** regras funcionam isoladamente e mantêm paridade com a V1.

### V2.7 — Supabase PostgreSQL e isolamento — PRÓXIMA

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
- [x] Corrigir e confirmar o serviço web Docker do Argos no Render, com `devbenjaminsantos/argos`, diretório `backend`, health check `/health` e deploy `live` do commit `9e33b85`.
- [x] Configurar e validar o segredo mínimo do webhook no secret store do provedor de execução.
- [x] Criar `argos_runtime_login` sem privilégios próprios, vinculá-lo somente ao grupo `argos_runtime` e validar seus atributos e privilégios efetivos no PostgreSQL remoto.
- [ ] Criar uma identidade `LOGIN` de migração, vinculá-la ao grupo `argos_migrator` e validar uma migração estrutural em ambiente controlado.
- [ ] Criar usuários, updates processados, conversas, produtos, preços e notificações.
- [ ] Implementar repositórios e índices de propriedade.
- [ ] Testar que um `telegram_user_id` nunca acessa dados de outro.

**Critério de conclusão:** migrações são reproduzíveis, schema público não está exposto indevidamente, credenciais não são versionadas e isolamento é comprovado.

### V2.8 — Usuário, deduplicação e conversa

- [ ] Implementar `/start`, `/ajuda` e `/cancelar`.
- [ ] Persistir usuário por `telegram_user_id` e destino por `chat_id`.
- [ ] Persistir inbox recuperável e deduplicar updates por `update_id`.
- [ ] Implementar rate limit e máquina de estados persistente.

**Critério de conclusão:** updates repetidos não duplicam ações e conversas sobrevivem a reinícios.

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
