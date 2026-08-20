# Roadmap do Argos

Este documento registra o avanço do projeto e divide as próximas versões em entregas pequenas, testáveis e fáceis de revisar.

## Como atualizar

- `[ ]` ainda não iniciado;
- `[x]` concluído e validado;
- manter apenas uma etapa marcada como **próxima**;
- concluir testes e revisão antes de iniciar o bloco seguinte;
- não implementar vários blocos da versão atual na mesma alteração.

## Estado atual

**Versão concluída:** V1 — Extensão Chrome

**Próximo item:** V2.3 — Criar a fundação Azure com proteção de custo

**Última atualização:** 20/08/2026

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

## V2 — MVP Telegram na Azure

A V2 entregará o primeiro Argos cloud utilizável. O Telegram será interface, identidade inicial e canal de notificação. OIDC, extensão cloud, modo local e Android ficam fora desta versão.

Decisões relacionadas:

- [`ADR 0001 — Desenvolvimento local e execução em nuvem`](docs/decisions/0001-local-vs-cloud.md);
- [`ADR 0002 — Azure como plataforma`](docs/decisions/0002-azure-platform.md);
- [`ADR 0003 — FastAPI, Azure SQL e identidades`](docs/decisions/0003-backend-stack-and-auth.md);
- [`ADR 0004 — Telegram como V2`](docs/decisions/0004-telegram-mvp.md).

### V2.1 — Recorte e contratos do MVP Telegram — CONCLUÍDA

- [x] Escolher FastAPI, Azure Container Apps e Azure SQL Database.
- [x] Escolher Telegram como interface e canal do MVP.
- [x] Limitar o MVP a conversas privadas e Mercado Livre.
- [x] Identificar o proprietário por `telegram_user_id`, nunca por `username`.
- [x] Definir os contratos de repositório, coletor e notificador em [`docs/V2_CONTRACTS.md`](docs/V2_CONTRACTS.md).
- [x] Definir comandos, estados da conversa e respostas de erro em [`docs/V2_TELEGRAM_CONVERSATION.md`](docs/V2_TELEGRAM_CONVERSATION.md).
- [x] Atualizar o modelo de ameaças para Telegram, webhook, SSRF e Azure SQL em [`docs/V2_SECURITY.md`](docs/V2_SECURITY.md).

**Critério de conclusão:** recorte e contratos documentados, sem servidor funcional.

### V2.2 — FastAPI local e contêiner — CONCLUÍDA

- [x] Criar o monólito modular Python em [`backend/`](backend/).
- [x] Criar `GET /health` e tratamento centralizado de erros.
- [x] Configurar testes e variáveis sem segredos no repositório.
- [x] Criar a definição reproduzível da imagem com Python fixado, dependências travadas, usuário sem privilégios e ODBC Driver 18.
- [x] Validar build, presença do ODBC Driver 18, execução sem privilégios e `/health` dentro do contêiner.

**Critério de conclusão:** API e testes passam localmente e a imagem inicia com `/health` funcional.

### V2.3 — Fundação Azure — PRÓXIMA

- [ ] Criar resource group e Container Apps Environment de desenvolvimento.
- [ ] Configurar orçamento, alertas e limites de escala antes dos recursos recorrentes.
- [ ] Publicar somente `/health` em um Container App com escala mínima zero.
- [ ] Validar logs, cold start e implantação.

**Critério de conclusão:** o mesmo contêiner responde a `/health` localmente e na Azure.

### V2.4 — Bot de teste e segredos

- [ ] Criar um bot exclusivo de desenvolvimento no BotFather.
- [ ] Guardar token e segredo do webhook somente nos secrets da Azure.
- [ ] Confirmar a identidade do bot com a Bot API.
- [ ] Garantir que tokens nunca apareçam em código, erros ou logs.

**Critério de conclusão:** a API consulta a identidade do bot sem expor credenciais.

### V2.5 — Webhook seguro

- [ ] Criar `POST /webhooks/telegram`.
- [ ] Validar `X-Telegram-Bot-Api-Secret-Token` em tempo constante.
- [ ] Limitar corpo, tipos de update e comandos aceitos.
- [ ] Recusar grupos e aceitar apenas conversas privadas.
- [ ] Responder rapidamente sem executar scraping no request.
- [ ] Testar segredo ausente, inválido e payload malformado.

**Critério de conclusão:** somente updates autenticados e válidos são aceitos.

### V2.6 — Domínio e regras

- [ ] Implementar usuário Telegram, produto, observação e entrega de notificação.
- [ ] Armazenar dinheiro em unidade segura e portar regras da V1.
- [ ] Aplicar limite de três produtos por usuário.
- [ ] Definir estados de coleta e da conversa.
- [ ] Criar testes sem dependência de FastAPI, Telegram ou banco.

**Critério de conclusão:** regras funcionam isoladamente e mantêm paridade com a V1.

### V2.7 — Azure SQL e isolamento

- [ ] Configurar migrações e estratégia de testes com SQL Server.
- [ ] Provisionar Azure SQL Database com proteção de custo.
- [ ] Configurar identidade gerenciada para acesso sem senha.
- [ ] Criar usuários, updates processados, conversas, produtos, preços e notificações.
- [ ] Implementar repositórios e índices de propriedade.
- [ ] Testar que um `telegram_user_id` nunca acessa dados de outro.

**Critério de conclusão:** migrações são reproduzíveis, acesso cloud não usa senha e isolamento é comprovado.

### V2.8 — Usuário, deduplicação e conversa

- [ ] Implementar `/start`, `/ajuda` e `/cancelar`.
- [ ] Persistir usuário por `telegram_user_id` e destino por `chat_id`.
- [ ] Deduplicar updates por `update_id`.
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
- [ ] Agendar produtos vencidos com Container Apps Jobs em UTC.
- [ ] Impedir coletas concorrentes e aplicar retentativas limitadas.
- [ ] Enviar alerta pelo Telegram e deduplicar entregas.

**Critério de conclusão:** uma queda gera exatamente um alerta e o job continua após reinícios.

### V2.13 — Fechamento do MVP

- [ ] Configurar métricas, logs sem dados sensíveis e prontidão.
- [ ] Revisar permissões, backup, rollback e consumo da Azure.
- [ ] Testar cold start, falhas do Telegram, bloqueio da loja e banco indisponível.
- [ ] Executar teste de aceitação com dois usuários.

**Critério de conclusão:** o usuário cadastra um link e recebe um alerta real sem acessar código ou Azure.

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
