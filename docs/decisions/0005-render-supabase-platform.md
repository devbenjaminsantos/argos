# ADR 0005 — Render e Supabase como plataforma primária da V2

**Status:** aceita
**Data:** 21/08/2026

## Contexto

A tentativa de criar um App Service Plan F1 na assinatura Azure foi recusada porque a quota disponível é zero. Azure Container Apps possui franquia gratuita, mas pode gerar cobrança quando ela é excedida, contrariando a restrição atual de custo estritamente zero.

O back-end já foi construído como monólito modular, empacotado em contêiner e separado por portas e adaptadores. Portanto, a plataforma pode mudar sem alterar o domínio ou os casos de uso.

## Decisão

A infraestrutura primária da V2 será:

- Render Free para executar a API FastAPI em contêiner;
- Supabase Free para PostgreSQL persistente;
- um agendador externo, inicialmente GitHub Actions, para iniciar o comando de coleta em intervalos definidos;
- Telegram Bot API como entrada e canal de notificação;
- Oracle Cloud Always Free como alternativa futura para uma execução mais contínua;
- Azure preservada apenas como opção futura, sem novos recursos enquanto a restrição de custo zero estiver ativa.

```text
Telegram ──→ Render/FastAPI ──→ Supabase/PostgreSQL
                                      ↑
GitHub Actions ──→ job de coleta ─────┘
                         │
                         └──→ Mercado Livre / Telegram
```

## Proteção de custo

- manter o serviço Render no tipo `Free`;
- não cadastrar método de pagamento no workspace Render durante o piloto;
- manter o projeto Supabase em uma organização `Free`;
- não ativar add-ons, instâncias, discos ou recursos pagos;
- aceitar suspensão, cold start ou restrição do serviço ao atingir uma quota, em vez de permitir cobrança;
- revisar novamente os termos e limites no momento do provisionamento.

## Portabilidade

Permanecem independentes do provedor:

- entidades e regras do domínio;
- casos de uso e contratos em `application/ports`;
- adaptadores do Mercado Livre e do Telegram;
- comando do job e sua idempotência;
- imagem Docker e configuração por variáveis de ambiente.

Ficam específicos da infraestrutura:

- implementação PostgreSQL dos repositórios;
- injeção de segredos no Render e no GitHub Actions;
- conexão TLS e credencial de privilégio mínimo do Supabase;
- configuração de deploy, health check e agendamento.

Uma migração futura para Oracle ou Azure deverá trocar principalmente esses adaptadores e arquivos de implantação, sem reescrever as regras do Argos.

## Consequências

- PostgreSQL substitui Azure SQL Database como banco da V2;
- o ODBC Driver 18 deixou de ser requisito e foi removido da imagem ao introduzir `psycopg`;
- identidade gerenciada da Azure é substituída por credencial PostgreSQL armazenada somente como segredo;
- o filesystem do Render não será usado para dados persistentes;
- o webhook deve tolerar cold start e repetição de updates;
- o job não dependerá de um loop em memória dentro da API;
- os ADRs 0002 e a parte de persistência cloud do ADR 0003 são substituídos por esta decisão.

## Alternativa futura

Oracle Cloud Always Free permanece como contingência para o caso de cold start, limites de execução ou bloqueios de scraping tornarem o Render inadequado. Essa migração não será iniciada durante o MVP sem necessidade comprovada.

## Referências operacionais

- [Render — serviços gratuitos e limites](https://render.com/docs/free)
- [Supabase — controle de custos e comportamento do plano Free](https://supabase.com/docs/guides/platform/cost-control)
- [Oracle Cloud — recursos Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
