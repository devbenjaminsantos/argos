# ADR 0006 — Plataforma fracionada sem grandes nuvens

**Status:** aceita  
**Data:** 08/09/2026

## Contexto

O Argos precisa manter o monitoramento ativo fora da máquina do usuário, sem transformar o MVP em uma arquitetura de microsserviços. A revisão do repositório identificou documentação residual de Azure e Oracle e confirmou que o código atual já usa FastAPI, PostgreSQL, SQLAlchemy, Alembic e psycopg.

O projeto não contratará Azure, AWS, Google Cloud, Oracle Cloud ou outro grande provedor de nuvem para hospedar partes do Argos. A escolha deve manter API, banco e execução periódica desacoplados por responsabilidade e substituíveis por configuração, sem pressupor que os provedores especializados não usem infraestrutura dessas empresas internamente.

## Decisão

Para o piloto da V2:

- Render é o candidato inicial para hospedar a API FastAPI;
- Supabase é o candidato inicial para PostgreSQL persistente;
- GitHub Actions é o candidato inicial para disparar o comando de coleta;
- Telegram Bot API é a interface e o canal de notificações;
- API e job pertencem ao mesmo monólito modular, mas são processos distintos;
- PostgreSQL concentra estado, inbox de updates, leases e entregas; nenhum dado durável fica no filesystem da API;
- substituições de provedor serão avaliadas por responsabilidade e não podem reintroduzir grandes nuvens como destino contratado.

```text
Telegram ──HTTPS──> API FastAPI / Render
                            │
                            └──TLS──> PostgreSQL / Supabase
                                          ▲
GitHub Actions ──> comando de job Python ──┘
                            │
                            └──HTTPS──> Mercado Livre / Telegram
```

## Requisitos operacionais

- credenciais de runtime, migração e Telegram ficam somente em secret stores dos respectivos serviços;
- o runtime usa PostgreSQL por TLS com verificação de certificado e hostname;
- migrações são aplicadas explicitamente, com credencial distinta e mínima quando disponível;
- o job seleciona trabalho vencido no banco, usa leases e tolera atraso, duplicação ou ausência de um disparo;
- o webhook só confirma update depois de persistir o trabalho necessário para recuperá-lo;
- a API não mantém estado durável em memória ou em disco local;
- backup, restauração, quotas, cold start, latência entre API e banco e limites de conexão devem ser validados antes do piloto real.

## Consequências

Render Free é adequado somente como piloto: pode dormir, reiniciar e impor limites a tráfego de saída. GitHub Actions é um disparador aproximado, não uma fila ou garantia de execução. Esses limites precisam ser absorvidos pela persistência e pelo job, sem depender de loops em memória.

O backend acessará o PostgreSQL diretamente; Supabase Auth e Data API não fazem parte da V2. Se a Data API não for necessária, ela deve permanecer desabilitada. Caso alguma tabela seja exposta futuramente, permissões e RLS serão definidos para o modelo de identidade daquele cliente, sem usar `telegram_user_id` como se fosse `auth.uid()`.

Este ADR substitui o ADR 0005 como decisão de plataforma. Os ADRs 0002 e a parte de infraestrutura do ADR 0003 permanecem somente como histórico.

## Referências

- [Render — serviços gratuitos e limites](https://render.com/docs/free)
- [Supabase — conexões PostgreSQL](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase — segurança da Data API](https://supabase.com/docs/guides/api/securing-your-api)
- [GitHub Actions — agendamento](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
