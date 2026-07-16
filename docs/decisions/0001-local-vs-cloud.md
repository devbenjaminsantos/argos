# ADR 0001 — Desenvolvimento local e execução em nuvem

**Status:** aceita  
**Data:** 16/07/2026

## Contexto

A V2 adicionará um back-end responsável por persistência, coleta agendada e notificações remotas. Diferentemente da extensão, esse monitoramento deve continuar funcionando quando o navegador e o computador do usuário estiverem desligados.

“Local ou cloud” envolve duas decisões diferentes:

1. onde o sistema será desenvolvido e testado;
2. onde as coletas programadas serão executadas.

## Alternativas

### Somente local

Vantagens:

- custo de infraestrutura praticamente nulo;
- depuração e acesso ao banco mais simples;
- menor quantidade de configuração inicial.

Desvantagens:

- o monitor para quando o computador desliga ou perde conexão;
- notificações e coletas dependem da máquina do desenvolvedor;
- não representa o comportamento final esperado do produto.

**Conclusão:** adequado para desenvolvimento, testes e uso opcional autohospedado, mas não como execução principal do bot.

### Serviço cloud continuamente ativo

Vantagens:

- API e scheduler permanecem disponíveis;
- modelo operacional simples no início;
- facilita notificações e integrações recebidas em tempo real.

Desvantagens:

- cobra recursos mesmo durante períodos sem trabalho;
- mistura API HTTP e agendamento no mesmo processo;
- reinícios ou múltiplas réplicas exigem controle para impedir coletas duplicadas.

**Conclusão:** funciona, mas manter um processo 24/7 é desnecessário para verificações a cada 12 ou 24 horas.

### API cloud e job programado

Neste modelo, a API pode dormir ou escalar para zero. Um job executado, por exemplo, a cada 30 minutos consulta o banco, seleciona produtos vencidos, realiza as coletas e encerra.

Vantagens:

- continua funcionando sem depender do computador do usuário;
- reduz consumo quando não há trabalho;
- separa requisições HTTP da rotina de coleta;
- permite evoluir o job para um worker posteriormente.

Desvantagens:

- exige um provedor com jobs programados ou um agendador externo;
- horários são aproximados e precisam tolerar atraso;
- a execução deve ser idempotente e possuir trava ou lease no banco;
- a API e o job precisam compartilhar uma base persistente.

**Conclusão:** é a alternativa recomendada para o piloto da V2.

## Decisão

- desenvolver e executar testes localmente;
- empacotar o back-end como um contêiner reproduzível;
- implantar cedo um ambiente piloto na nuvem;
- utilizar uma API e um comando de job no mesmo monólito modular;
- executar o job periodicamente, em vez de manter um worker ocioso 24/7;
- utilizar banco persistente externo ao filesystem do contêiner;
- manter a implantação independente do provedor escolhido.
- entregar a execução cloud na V2;
- adiar a edição local/autohospedada, com instalação própria, para a V3.

Fluxo proposto:

```text
Extensão/cliente ──→ API cloud ──→ banco persistente
                                      ↑
Agendador cloud ──→ job de coleta ────┘
                         │
                         └──→ Mercado Livre / notificações
```

## Persistência — decisão posteriormente refinada

Arquivos locais de contêineres cloud normalmente são efêmeros. Portanto, um arquivo SQLite dentro do contêiner não deve ser considerado armazenamento de produção.

Inicialmente foram consideradas duas opções:

1. SQLite no desenvolvimento local e PostgreSQL antes do primeiro deploy;
2. PostgreSQL desde o início, localmente por contêiner e gerenciado na nuvem.

Após a escolha da Azure, o projeto decidiu usar Azure SQL Database, e não PostgreSQL, na V2. A decisão posterior e prevalente está no [`ADR 0003`](0003-backend-stack-and-auth.md). SQLite permanece como alternativa a ser reavaliada para a edição local/autohospedada da V3.

## Avaliação inicial de provedores

| Alternativa | Adequação ao piloto | Principal cuidado |
|---|---|---|
| [Azure Container Apps](https://azure.microsoft.com/en-us/pricing/details/container-apps/) | Alta — selecionada | Jobs agendados e escala para zero atendem ao piloto; franquias, banco, logs e tráfego precisam de limites de custo. |
| [Railway](https://docs.railway.com/guides/cron-workers-queues) | Alta | Serviço, PostgreSQL e cron no mesmo projeto; há [cobrança baseada em plano e uso](https://docs.railway.com/pricing/plans). |
| [Render](https://render.com/docs/free) | Média | Boa experiência de deploy, mas o serviço gratuito dorme e o filesystem é efêmero. |
| [Google Cloud Run](https://docs.cloud.google.com/run/docs/configuring/min-instances) | Média/alta | Escala para zero e suporta execução em contêiner, mas exige mais configuração de IAM, billing e agendamento. Instâncias mínimas geram cobrança. |
| [Fly.io](https://fly.io/docs/about/pricing/) | Média | Máquinas pequenas têm custo baixo, porém a operação e a persistência exigem mais decisões. |

A Azure foi escolhida para o piloto. A decisão específica está registrada no [`ADR 0002`](0002-azure-platform.md).

## Impactos arquiteturais

- o scheduler não deve existir apenas como um loop em memória;
- produtos vencidos devem ser selecionados pelo banco;
- cada execução precisa ser idempotente;
- duas execuções concorrentes não podem coletar o mesmo produto;
- segredos devem vir do ambiente cloud, nunca do repositório;
- timeouts, retentativas e limites por loja devem existir antes de ativar o job;
- a API precisa funcionar localmente sem depender de serviços exclusivos de um fornecedor.

## Decisões resultantes

- [x] Aprovar desenvolvimento local e execução cloud.
- [x] Escolher a Azure para a V2.
- [x] Adiar a edição local/autohospedada para a V3.
- [x] Escolher FastAPI.
- [x] Escolher Azure SQL Database.
- [ ] Definir orçamento mensal máximo e alertas de custo.
- [x] Incluir autenticação e isolamento multiusuário desde a V2.
