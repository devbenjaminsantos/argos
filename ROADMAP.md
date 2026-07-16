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
**Próxima etapa:** V2.1 — Decisões e contratos do back-end  
**Última atualização:** 16/07/2026

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

## V2 — Back-end cloud na Azure

A V2 será desenvolvida e testada localmente, mas seu produto final rodará na Azure. O modo local/autohospedado foi separado e movido para a V3.

### V2.1 — Decisões e contratos do back-end — PRÓXIMA

- [x] Avaliar execução local versus execução em nuvem.
- [x] Confirmar desenvolvimento local com execução programada em nuvem.
- [x] Escolher a Azure como provedora do piloto.
- [x] Separar o modo local/autohospedado e adiá-lo para a V3.
- [ ] Escolher FastAPI ou Django e registrar a decisão.
- [ ] Confirmar PostgreSQL desde o início, localmente e na Azure.
- [ ] Definir se o piloto será de usuário único ou terá autenticação desde o início.
- [ ] Definir os limites entre domínio, aplicação e infraestrutura.
- [ ] Definir os contratos de `ProductRepository`, `PriceRepository`, `PriceCollector` e `Notifier`.
- [ ] Definir o formato inicial da API e dos erros.
- [ ] Atualizar o modelo de ameaças para incluir API, SSRF e banco de dados.

**Critério de conclusão:** decisões registradas em documentação, sem implementação funcional do servidor.

Decisões relacionadas:

- [`ADR 0001 — Desenvolvimento local e execução em nuvem`](docs/decisions/0001-local-vs-cloud.md);
- [`ADR 0002 — Azure como plataforma da V2`](docs/decisions/0002-azure-platform.md).

### V2.2 — Fundação executável da API

- [ ] Criar a estrutura modular do back-end.
- [ ] Configurar ambiente e variáveis sem armazenar segredos no repositório.
- [ ] Criar uma imagem Docker reproduzível.
- [ ] Criar endpoint de saúde, como `GET /health`.
- [ ] Configurar tratamento centralizado de erros.
- [ ] Adicionar testes do processo de inicialização e do endpoint de saúde.
- [ ] Publicar somente o endpoint de saúde em um Azure Container App de desenvolvimento.

**Critério de conclusão:** o mesmo contêiner inicia localmente e na Azure, e o teste de saúde passa nos dois ambientes.

### V2.3 — Domínio e regras de preço

- [ ] Implementar entidades de produto, observação de preço e entrega de notificação.
- [ ] Armazenar valores monetários em centavos inteiros ou tipo decimal seguro.
- [ ] Portar as regras de preço-alvo e queda relevante da extensão.
- [ ] Definir os estados de coleta e suas transições.
- [ ] Criar testes de paridade com as regras da V1.

**Critério de conclusão:** regras de negócio funcionam sem depender de HTTP, banco ou scraper.

### V2.4 — Persistência com PostgreSQL

- [ ] Escolher e configurar a ferramenta de migração.
- [ ] Executar PostgreSQL localmente para desenvolvimento e testes de integração.
- [ ] Provisionar Azure Database for PostgreSQL no ambiente de desenvolvimento.
- [ ] Criar tabelas de produtos, observações e notificações.
- [ ] Implementar os repositórios definidos na V2.1.
- [ ] Garantir unicidade de produto e deduplicação de notificações.
- [ ] Criar testes de integração do banco.

**Critério de conclusão:** as mesmas migrações e integrações funcionam no PostgreSQL local e na Azure, e os dados sobrevivem ao reinício da API.

### V2.5 — API de produtos

- [ ] Criar endpoint para cadastrar produto.
- [ ] Criar endpoint para listar produtos.
- [ ] Criar endpoint para consultar um produto.
- [ ] Criar endpoint para atualizar regras de monitoramento.
- [ ] Criar endpoint para remover produto.
- [ ] Aplicar o limite inicial de três produtos.
- [ ] Validar payloads e padronizar respostas de erro.

**Critério de conclusão:** CRUD coberto por testes de API, ainda sem coleta automática.

### V2.6 — Segurança de URLs e SSRF

- [ ] Aceitar apenas HTTPS e lojas explicitamente suportadas.
- [ ] Rejeitar credenciais, portas não permitidas e URLs malformadas.
- [ ] Resolver DNS e bloquear destinos privados, locais ou reservados.
- [ ] Validar novamente cada redirecionamento.
- [ ] Limitar tamanho, duração e quantidade de respostas.
- [ ] Impedir que clientes escolham endpoints internos do coletor.
- [ ] Criar testes com URLs maliciosas e redirecionamentos.

**Critério de conclusão:** o coletor não funciona como proxy genérico nem alcança a rede interna.

### V2.7 — Coletor do Mercado Livre

- [ ] Portar o adaptador do Mercado Livre para o back-end.
- [ ] Criar uma operação manual de coleta para um produto cadastrado.
- [ ] Registrar sucesso ou falha sem transformar erro em preço zero.
- [ ] Detectar produto indisponível, bloqueio e preço ausente.
- [ ] Criar fixtures de páginas e testes do extrator.

**Critério de conclusão:** uma coleta manual registra uma observação válida no PostgreSQL.

### V2.8 — Histórico e comparação

- [ ] Criar endpoint para consultar o histórico de um produto.
- [ ] Comparar o preço atual com a última observação válida.
- [ ] Calcular queda absoluta e percentual.
- [ ] Calcular o menor preço observado no período disponível.
- [ ] Não afirmar histórico de 30 ou 90 dias sem dados suficientes.

**Critério de conclusão:** API retorna histórico e comparações com testes determinísticos.

### V2.9 — Agendador e retentativas

- [ ] Criar um comando de job separado da inicialização da API.
- [ ] Executar verificações vencidas com Azure Container Apps Jobs.
- [ ] Configurar execução cron em UTC.
- [ ] Evitar duas coletas simultâneas do mesmo produto.
- [ ] Implementar retentativa com espera progressiva para falhas transitórias.
- [ ] Aplicar limites por loja.
- [ ] Recuperar tarefas interrompidas após reinício.
- [ ] Testar relógio, concorrência e recuperação.

**Critério de conclusão:** o job agendado na Azure coleta produtos vencidos uma única vez e falhas não geram loops agressivos.

### V2.10 — Notificações remotas

- [ ] Definir o primeiro canal remoto.
- [ ] Manter tokens e credenciais somente no servidor.
- [ ] Criar contrato de notificador independente do canal.
- [ ] Implementar deduplicação persistente.
- [ ] Registrar tentativas, falhas e entregas.
- [ ] Testar o canal com um adaptador falso antes da integração real.

**Critério de conclusão:** um alerta gera uma única entrega rastreável, sem expor credenciais ao cliente.

### V2.11 — Integração com a extensão

- [ ] Definir autenticação entre extensão e API.
- [ ] Criar o modo cloud da extensão separado do armazenamento local da V1.
- [ ] Sincronizar produtos cloud sem duplicar cadastros.
- [ ] Exibir estado de sincronização e falhas.
- [ ] Tratar indisponibilidade e cold start da API sem corromper o estado local.

**Critério de conclusão:** a extensão cadastra e consulta produtos pela API em um ambiente de teste.

### V2.12 — Operação e proteção de custos na Azure

- [ ] Configurar logs estruturados e métricas básicas.
- [ ] Criar verificações de prontidão e saúde.
- [ ] Configurar orçamento, alertas de custo e limites de escala.
- [ ] Revisar consumo de Container Apps, PostgreSQL, registry, logs e tráfego.
- [ ] Documentar backup, restauração, implantação e rollback.
- [ ] Executar testes de carga compatíveis com o escopo inicial.

**Critério de conclusão:** o ambiente Azure pode ser operado, restaurado e limitado dentro do orçamento definido para o piloto.

---

## V3 — Back-end local/autohospedado

O modo local será tratado como um produto separado. Desenvolvimento local da V2 não significa que essa edição esteja pronta para distribuição.

- [ ] Definir sistemas operacionais suportados.
- [ ] Escolher SQLite ou PostgreSQL empacotado para a edição local.
- [ ] Criar instalação e atualização reproduzíveis.
- [ ] Executar API e scheduler como serviço em segundo plano.
- [ ] Resolver portas, certificados e comunicação com a extensão.
- [ ] Armazenar segredos com mecanismos próprios do sistema operacional.
- [ ] Criar backup, restauração e diagnóstico local.
- [ ] Documentar firewall, permissões e desinstalação.
- [ ] Criar testes de instalação no Windows, macOS e Linux suportados.

**Critério de conclusão:** um usuário consegue instalar, atualizar, executar e remover o Argos local sem configurar manualmente Python, banco ou scheduler.

---

## V4 — Android

- [ ] Aplicativo Android com Kotlin e Jetpack Compose.
- [ ] Autenticação e comunicação com a API cloud.
- [ ] Cadastro e gerenciamento de produtos.
- [ ] Histórico e notificações no dispositivo.

---

## Fora das versões atuais

- [ ] Comparação automática entre anúncios equivalentes.
- [ ] Recomendação de melhor momento de compra.
- [ ] Relatórios em PDF e CSV.
- [ ] Gráficos avançados de histórico.
- [ ] Suporte à Shopee e a outras lojas.
- [ ] Extração de componentes para microsserviços, somente se houver necessidade comprovada.
