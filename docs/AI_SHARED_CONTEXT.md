# Contexto operacional compartilhado

## Direção e próximo passo — 19/09/2026

O [roadmap](../ROADMAP.md) é a fonte única de progresso. Foi reorganizado entre consolidação V1/V2 agora, V3 contextual C2–C6, expansões C7–C9 e V4/V5 sem data. Preserva IDs e checkboxes, distingue implementação de aceite e mostra quais componentes serão evoluídos. Detalhes antigos estão no [histórico do roadmap](history/ROADMAP_BEFORE_2026-09-19.md) e no [contexto histórico](history/AI_SHARED_CONTEXT_BEFORE_2026-09-19.md); seus “próximos passos” estão superados.

**Próximo item:** aceite de C1 em Chrome real, conforme `docs/CONTEXTUAL_CAPTURE_ACCEPTANCE.md`. Não executado. Enquanto o ambiente não estiver disponível, CI da extensão, regressões e preparação isolada de contratos podem avançar; isso não encerra C1 nem libera integrações dependentes. Trabalhar em incrementos pequenos e revisáveis.

## Estado confirmado no código

- V1: Mercado Livre local, até três produtos, IndexedDB, alarmes, alvo/queda percentual e notificações. Aceite Chrome ainda pendente.
- C1: botão explícito de observação DOM sem persistência, backend ou alertas; condições/elegibilidade/contexto desconhecidos quando não comprovados. Validação registrada em 18/09: tipos, 29 testes Vitest e build. C2–C9 ainda não entregues.
- V2: FastAPI, webhook privado autenticado, admissão/rate limit, inbox durável, worker com leases, conversas persistentes, cadastro/listagem/cancelamento/remoção e `/verificar <UUID>` implementados. Texto privado não vazio é admitido para a conversa; comandos desconhecidos são descartados.
- Proprietário atual é `telegram_user_id`; `chat_id` é destino. UUID Argos será introduzido aditivamente em C2. Cadastro/listagem/remoção e limites têm testes PostgreSQL e aceites relatados entre duas contas, com regressões manuais restantes no roadmap.
- Coletor público compõe transporte SSRF seguro e extração JSON-LD/meta/DOM. `/verificar` grava sucesso/falha idempotente e checkpoint da resposta. A coleta ainda ocupa o worker de comandos; não há fila contextual, outbox geral, coleta periódica ou alertas cloud aceitos.
- O modelo atual reúne sucesso e falha em observações; C3 separará tentativas. Método de extração não comprova sessão ou personalização. Reutilizar garantias existentes sem confundi-las com o modelo contextual pronto.
- O workflow local agora possui job independente da extensão com Node 24, instalação pelo lockfile, tipos, 29 testes Vitest e build, sem alterar o job PostgreSQL do backend. `npm ci`, tipos, testes e build foram reproduzidos localmente em 19/09, e o YAML foi validado; a execução remota ainda não ocorreu. Manter a pendência V2.13 aberta até o CI aprovar o commit.

## Limites operacionais e evidência histórica

- Plataforma fracionada do ADR 0006: API Render, PostgreSQL Supabase e execução separada; GitHub Actions é candidato de agendamento e executor administrativo de migrações. Sem contratação direta de grandes nuvens. Monólito modular mantido.
- Runtime e migrador separados; TLS `verify-full`, CA e pool limitado. Migrações não executam no boot. Data API/Auth não fazem parte da V2; frontend futuro acessa somente API Argos. Revisão dos privilégios padrão de objetos criados fora do migrador segue pendente.
- Histórico de 17/09: `/verificar` implantado em `c830c6c`, banco em `20260916_10`, tentativas sem preço. Reprodução encontrou HTTP 403. `d829a10` classifica 403/429 e falhas de abertura; 596 testes locais e CI `35232666792` registrados. Confirmar implantação/mensagem antes de declarar diagnóstico aceito. Não houve nova consulta cloud nesta revisão documental.
- Coleta pública bloqueada não implica conector bloqueado. Se necessário priorizar C1–C6, mantendo V2.12/V2.13 pendentes até aceite público real. Não criar duas filas: executor/entregas V2.12 e C4 devem evoluir a mesma base.
- Sessão da loja permanece no navegador. Assinatura comprova origem/integridade, não preço comercial. Consentimento, geração, revogação e exclusão pertencem a C5. APIs oficiais, busca e lojas adicionais dependem de viabilidade comprovada.

Na reorganização inicial foram alterados somente documentos. Depois dela, o job da extensão foi preparado localmente; a validação local deve ser registrada separadamente e não substitui a execução remota do CI.
