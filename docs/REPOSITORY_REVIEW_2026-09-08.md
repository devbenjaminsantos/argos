# Análise do repositório e curso de ação

Data: 08/09/2026. Escopo: código e documentação versionados, testes locais e documentação oficial dos provedores. Não houve consulta a contas cloud, provisionamento ou alteração de código da aplicação. As ações documentais recomendadas nesta análise foram registradas depois no [ADR 0006](decisions/0006-fractionated-platform.md) e nos documentos indicados por ele.

## Conclusão

O Argos possui uma extensão implementada e uma fundação de backend. Ainda não possui um MVP Telegram funcional. A direção PostgreSQL + FastAPI já aparece no código; as maiores divergências estão na apresentação de funcionalidades, no histórico de decisões cloud e nas garantias operacionais ainda não implementadas.

A orientação desta revisão é distribuir a hospedagem por responsabilidade: API em um provedor, PostgreSQL em outro e execução periódica separada. Azure, AWS, Google Cloud e Oracle Cloud ficam fora das opções de contratação direta do projeto, inclusive como contingência. Isso substitui a intenção anterior de voltar à Azure ou migrar para Oracle.

Interpretação adotada: a restrição diz respeito aos serviços contratados e operados pelo Argos. Provedores especializados podem usar infraestrutura de grandes nuvens internamente; esta proposta não certifica independência física dessas empresas.

## Estado comprovado

| Parte | Estado no código | Limite da evidência |
|---|---|---|
| Extensão | Cadastro Mercado Livre, três produtos, IndexedDB, alarmes, coleta manual/periódica e notificações | Aceitação no Chrome ainda pendente; não há suíte E2E versionada |
| Regras V1 | Preço-alvo e queda percentual sobre o último preço | Sem regra de queda absoluta ou mínimo de 30/90 dias |
| API | `/health`, erros padronizados, correlação e validação do webhook | `/health` só testa vida HTTP; não conecta ao banco |
| Telegram | Segredo em tempo constante, corpo limitado, mensagem privada de texto | Update válido recebe `503`; nenhum comando ou envio implementado |
| Banco | SQLAlchemy, psycopg, Alembic e tabela `processed_telegram_updates` | Sem repositório conectado ao webhook; sem usuários, produtos ou conversas |
| Arquitetura Python | Diretórios de domínio, portas e adaptadores preparados | Muitos contêm apenas `__init__.py`; estrutura não equivale a implementação |
| Implantação | Dockerfile com runtime não privilegiado e dependências travadas | Sem configuração Render ou workflows GitHub versionados; deploy externo não verificado |
| Job | Intenção documentada | Sem comando executável, scheduler, coletor Python ou notificador |

Validação executada nesta revisão: `npm run check`, `npm test` (**17 passaram**), `npm run build` e `backend/.venv/bin/python -m pytest`, a partir de `backend/` (**25 passaram**). Os testes atuais de migração verificam metadados e SQL offline. Não foi repetido aqui o teste histórico em PostgreSQL real nem o build Docker. Não foram validados Chrome, entrega Telegram, credenciais, backups ou implantação remota.

## Divergências e riscos, por prioridade

### Alta — decisões cloud contraditórias

- `docs/decisions/0003-backend-stack-and-auth.md` permanece com status aceita e consequências envolvendo ODBC, SQL Server e identidade gerenciada, apesar da ressalva inicial.
- `docs/decisions/0005-render-supabase-platform.md` ainda mantém Azure e Oracle como opções futuras, contrariando a orientação atual.
- `docs/AZURE_FOUNDATION.md` parece um procedimento operacional ativo e inclui uma ordem de provisionamento obsoleta.
- `ROADMAP.md`, V2.2/V2.3, mistura realizações históricas em Azure/ODBC com critérios atuais. O Dockerfile já usa psycopg.

**Ação:** preservar ADRs históricos claramente marcados como substituídos, retirar procedimentos Azure da navegação operacional e registrar uma decisão vigente que exclua grandes nuvens como destino direto. Atualizar as consequências ainda válidas do ADR 0003 e o roadmap sem apagar o histórico.

### Alta — persistência não equivale a processamento durável

`backend/src/argos/api/routes/telegram.py` termina em `503`. Isso é coerente com a pendência documentada e evita confirmar trabalho que seria perdido. A tabela em `infrastructure/database/models.py` contém ID, status e datas, mas não dados suficientes para reconstruir o comando, lease de processamento ou política de retomada.

`docs/V2_CONTRACTS.md` propõe responder sem repetir a ação quando o ID já existe. Se o processo cair depois de reservar e antes de concluir, essa regra sozinha pode abandonar trabalho. Uma tabela de deduplicação não constitui uma fila recuperável.

**Ação:** definir uma inbox persistente com dados mínimos normalizados, estados recuperáveis, tentativas e lease; ou concluir comandos locais e registrar seu resultado na mesma transação. Qualquer coleta assíncrona precisa de trabalho durável e de um consumidor definido. Responder sucesso somente após commit. Testar duplicação concorrente e interrupção entre etapas.

### Alta — segurança planejada apresentada como garantia mais forte que o código

`docs/V2_SECURITY.md` exige TLS e validação de certificado; `infrastructure/database/config.py` aceita `sslmode=require`, que não garante por si só verificação do hostname. A validação só é chamada ao criar o engine; iniciar a API e obter `/health` não comprova essa configuração. Para conexões entre provedores, adotar `verify-full` com CA configurada e testar certificado/hostname incorretos. [Referência PostgreSQL](https://www.postgresql.org/docs/current/libpq-ssl.html).

O documento também fala em schema fechado, mas `api/schemas.py` usa `extra="ignore"` e inteiros sem modo estrito. Isso pode ser uma escolha de compatibilidade com Telegram; documentar como subconjunto validado com campos extras ignorados, e testar tipos e limites dos identificadores.

Isolamento entre usuários, rate limit e SSRF no backend são requisitos futuros, não controles já implementados.

### Média — README superestima escopo e cobertura

- Abertura inclui Shopee; código e escopo V2 suportam somente Mercado Livre.
- “Como funciona” anuncia mínimo em 30/90 dias; “Regras” inclui queda absoluta. `src/domain/price-rules.ts` implementa somente alvo e queda percentual.
- `tests/` é descrito como incluindo integração e E2E; os quatro arquivos atuais cobrem regras, entradas, URLs e extração com DOM simulado.
- “V1 concluída” deve virar “implementada, com aceitação no Chrome pendente”.
- `docs/V2_CONTRACTS.md` promete representação Python na V2.2, marcada concluída; os contratos ainda são especificação textual.

**Ação:** separar explicitamente disponível, planejado e validado. Levar funcionalidades ausentes para backlog; não implementá-las apenas para satisfazer texto antigo.

### Média — limitações da V1 merecem registro e teste

Em `src/application/monitor-product.ts`, consultar deduplicação, enviar notificação e registrar entrega são operações separadas. Coleta manual e alarme podem sobrepor execuções; queda após envio e antes do registro permite repetição. A garantia é deduplicação no fluxo normal, não entrega única sob concorrência/falha.

O mesmo arquivo segue redirects automaticamente e valida apenas a URL final. O limite é conferido após `response.text()` quando não há tamanho declarado confiável; portanto não é limite rígido de bytes durante download, nem validação prévia de cada salto. Não portar esse transporte diretamente para o backend.

**Ação:** testar concorrência e falha de entrega na extensão, separar falha de notificação de falha de coleta e explicitar os limites em `docs/SECURITY.md`. Implementar transporte Python conforme o modelo SSRF já especificado.

## Arquitetura proposta

```text
Telegram ──HTTPS──> API FastAPI / Render
                            │
                            └──TLS──> PostgreSQL / Supabase
                                          ▲
GitHub Actions ──> comando de job Python ──┘
                            │
                            └──HTTPS──> Mercado Livre / Telegram

Extensão V1 ──> IndexedDB local (independente)
```

Manter um monólito modular Python com entradas separadas para API e job, mesma versão de código e dependências. A separação de provedores não exige microsserviços. PostgreSQL concentra estado, trabalho pendente, leases e entregas; o filesystem da API não guarda dados duráveis.

| Responsabilidade | Direção | Condição de uso |
|---|---|---|
| API/webhook | Render como candidato inicial | Free apenas para piloto que aceite cold start; medir resposta real do Telegram |
| Dados | Supabase como PostgreSQL gerenciado | SQLAlchemy/Alembic por conexão SQL, sem necessidade de Supabase Auth na V2 |
| Coletas periódicas | GitHub Actions executando o comando do job | Agenda aproximada; seleção de vencidos e recuperação ficam no banco |
| Respostas conversacionais | API para comandos curtos e persistidos | Não esperar o cron de coleta para responder `/start`; efeitos de rede após commit |
| Coleta manual assíncrona | Trabalho persistido e executor a definir no incremento correspondente | Se exigir baixa latência, acrescentar worker em provedor especializado; não depender só de tarefa em memória |
| Identidade e notificações | Telegram | Usuário por `telegram_user_id`, destino por `chat_id`; OIDC somente na V3 |

O Render Free dorme após 15 minutos sem tráfego e pode levar aproximadamente um minuto para voltar. Também pode suspender serviços com volume incomum de tráfego iniciado para bancos/APIs externos. Por isso, Render + banco externo deve ser validado como piloto, não anunciado como disponibilidade contínua garantida. [Limites oficiais](https://render.com/docs/free).

O cron do GitHub pode atrasar ou perder execuções; em repositório público, pode ser desativado após 60 dias sem atividade. Usar `next_check_at`, recuperação de atrasados, disparo manual e indicador de última execução bem-sucedida. Conferir minutos e orçamento da conta antes de ativar. [Agendamento oficial](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Para Supabase, testar a conectividade a partir da API e do executor: conexão direta depende de IPv6 no Free; session pooler é alternativa para rede IPv4. Não selecionar transaction pooler sem configurar a compatibilidade de prepared statements. Limitar pools somados de API e job e manter transações curtas. [Conexões oficiais](https://supabase.com/docs/guides/database/connecting-to-postgres).

Como somente o backend acessará SQL, desabilitar a Data API se não for utilizada e revisar grants/schema. Se houver tabelas expostas, configurar RLS e permissões adequadas. Não presumir que Alembic ativa essas proteções nem que identidade Telegram corresponde a `auth.uid()`. Credenciais de migração e runtime devem ser distintas. [Segurança da Data API](https://supabase.com/docs/guides/api/securing-your-api).

Escolher regiões próximas, medir latência entre API e banco, definir backup restaurável e orçamento por serviço. A troca de hospedagem deve preservar PostgreSQL e interfaces; o provedor substituto será avaliado por necessidade, sem reintroduzir Azure/AWS/GCP/Oracle. A gratuidade permanece uma restrição registrada no projeto, não uma promessa de operação contínua sem custos.

## Curso de ação em incrementos

Esta é uma proposta de sequência; não marca funcionalidades como concluídas nem altera o roadmap vigente nesta revisão.

| Ordem | Entrega isolada | Aceitação |
|---|---|---|
| 1 — próxima | Consolidar README, roadmap, ADRs e status dos controles | Uma única direção vigente; histórico sinalizado; nenhuma funcionalidade ausente descrita como disponível |
| 2 | Refinar contrato de inbox, retomada e entregas | Definir consumidor, commit antes de ACK, lease expirado e tratamento de resultado de envio incerto |
| 3 | Implementar persistência mínima de updates e usuários | Testes em PostgreSQL real: repetição, concorrência, rollback e retomada após falha |
| 4 | Entregar `/start`, `/ajuda`, `/cancelar` e resposta Telegram | Comandos funcionando localmente, estado durável e segredos ausentes dos logs |
| 5 | Criar CI e piloto mínimo Render + Supabase | Checks automatizados; TLS verificado desde o runtime; migração separada; deploy reproduzível; webhook testado após cold start |
| 6 | Implementar domínio e cadastro por etapas | Dinheiro em centavos, três produtos sob concorrência, confirmação e isolamento com dois usuários |
| 7 | Entregar transporte seguro, extrator e coleta manual | SSRF negativo, fixtures de parser e preço real sem transformar falha em zero; validar acesso à loja desde o executor escolhido |
| 8 | Entregar job, agenda, histórico e alertas | Trabalho vencido recuperável, leases, retentativas limitadas, registro de envio e atraso observável |
| 9 | Fechar piloto e aceitação V1 | Chrome real; dois usuários no Telegram; restauração de backup, indisponibilidade e rotação exercitadas |

Separar o atual V2.7 em incrementos menores: conexão/provisionamento, repositórios, entidades e isolamento são entregas diferentes. Levar proteção SSRF antes da primeira coleta de URL, inclusive durante cadastro. A aceitação da extensão pode ocorrer assim que houver Chrome disponível, sem depender da V2.

Não prometer “exatamente um alerta” sob qualquer falha: uma interrupção depois de o provedor aceitar o envio, mas antes de registrar o resultado, deixa entrega incerta. Definir política explícita para esse estado e testar o compromisso entre possível repetição e possível perda; reserva única no banco resolve concorrência local, mas não torna o envio externo transacional.

## Organização documental sugerida

- `README.md`: produto disponível, como executar, limitações e links.
- `ROADMAP.md`: entregas verificáveis, evidências e uma próxima etapa.
- `docs/decisions/`: decisões vigentes e históricas com status inequívoco.
- Documento operacional de implantação: provedores, regiões, conexão, migrações, segredos, backup e rollback; substituir a função operacional de `AZURE_FOUNDATION.md`.
- Contratos e segurança: requisitos acompanhados de estado — planejado, implementado ou validado — e referência ao código/teste.

Não criar uma segunda lista permanente de progresso neste relatório. Após a consolidação, o roadmap volta a ser a fonte de andamento; esta análise permanece como registro datado.
