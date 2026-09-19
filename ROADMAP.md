# Roadmap do Argos

Plano ativo reorganizado em **19/09/2026**, confrontado com o código local. Evidências antigas de CI, deploy e aceite foram preservadas no [histórico anterior](docs/history/ROADMAP_BEFORE_2026-09-19.md); não representam nova verificação de produção.

## Como acompanhar

- `[x]` entrega concluída com a evidência correspondente; não implica aceite de toda a versão.
- `[ ]` entrega pendente, parcial ou aguardando validação — o texto identifica qual caso.
- Implementar um incremento pequeno, validar e revisar antes do seguinte.
- Um item compartilhado tem uma lista canônica; outras versões apontam para ela.
- Não encerrar uma etapa sem cumprir seu critério de saída. Não repetir entregas concluídas quando forem ampliadas numa versão futura.

**Próximo item:** executar o aceite Chrome de C1 e registrar os resultados em [aceitação contextual](docs/CONTEXTUAL_CAPTURE_ACCEPTANCE.md). Depende de ambiente Chrome real; não foi realizado.

## Agora, depois e dependências

| Horizonte | Trabalho | Limite para avançar |
| --- | --- | --- |
| Agora: consolidar V1/V2 | Aceite C1/V1, CI da extensão, pendências de cadastro, diagnóstico de bloqueio e operação | Não habilitar fontes presumidas nem anunciar preço real sem coleta bem-sucedida |
| Agora: preparação independente | Fixtures de extração, contratos e testes de migração/fila, diagnóstico de capacidade pública | Preparação não marca C2–C6 como entregues; integrações seguem os gates |
| V2: fechar piloto público | Executor periódico, histórico comparável e alertas Telegram simples (V2.12), aceite operacional (V2.13) | Depende de fonte pública viável em V2.11; o 403 atual impede concluir esse aceite |
| V3: contexto do proprietário | C2–C6: identidade Argos, modelo contextual, trabalhos duráveis, conector e alertas condicionais | C1 aceito e migrações incrementais; frontend somente pela API |
| Expansões da V3 | C7 fontes oficiais, C8 busca limitada, C9 novas lojas | Capacidade comprovada por fonte/loja; não bloqueiam a V3 Mercado Livre |
| Futuro sem data | V4 autohospedado e V5 Android | API e operação estáveis; escopos próprios abaixo |

Se a coleta pública continuar inviável, registrar a limitação e priorizar C1–C6 para observação de páginas abertas; V2.12/V2.13 permanecem pendentes, sem declarar o piloto público concluído. Não é necessário implementar duas filas: se C4 vier primeiro, seu executor e entregas atenderão V2.12, com o aceite público ainda separado.

A hospedagem permanece fracionada conforme [ADR 0006](docs/decisions/0006-fractionated-platform.md): API, PostgreSQL e execução separados, monólito modular portátil e sem contratação direta de grandes nuvens. Não há mudança de provedor nesta revisão.

## O que será retomado nas versões futuras

| Base atual | Evolução futura | O que preservar |
| --- | --- | --- |
| V1: IndexedDB, alarmes e notificações locais | C5: modo conectado; V4: instalação de backend | Modo local utilizável e sem conta obrigatória |
| V2.6–V2.9: proprietário Telegram | C2: UUID Argos, Telegram como identidade vinculada | Dados, comandos e isolamento durante migração aditiva |
| V2.7/V2.11: produto e observação de sucesso/falha | C3: oferta, monitoramento, tentativa e observação separados | Histórico, centavos, idempotência e desconhecidos explícitos |
| V2.8: inbox, leases e respostas recuperáveis | C4: fila de coleta e intenções de entrega | Inbox continua recebendo comandos; envio externo pode ficar incerto |
| V2.10/V2.11: transporte seguro e extrator ML | C3/C7/C9: capacidades e adaptadores por loja | SSRF, limites e identidade da oferta; não compartilhar sessão |
| V2.12: alvo/queda pública e Telegram | C4/C6: entregas por canal e comparação contextual | Regras existentes somente para condições compatíveis |
| V2.13: métricas, permissões e recuperação | C5/C9/V4/V5: novos canais, lojas e distribuição | Repetir aceitação de segurança/isolamento em cada ampliação |

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

**Escopo implementado (aceite manual pendente):** a V1 opera localmente, sem conta, servidor, endpoint remoto ou segredos distribuídos no pacote.

---

## V2 — Piloto Telegram público — parcial

A V2 já possui cadastro completo, remoção e verificação manual no código. Ainda não é um monitor cloud com coleta periódica e alertas aceitos. A implantação histórica de `/verificar` retornou falhas de coleta; não houve aceite de preço real. Detalhes e recibos estão no histórico arquivado.

### V2.1–V2.5 — Fundação, infraestrutura e webhook — implementados

- [x] Definir contratos, monólito FastAPI, imagem Docker e hospedagem fracionada.
- [x] Configurar bot de teste, segredo do webhook e validação de identidade sem expor credenciais.
- [x] Validar mensagens privadas, limites HTTP e persistência/deduplicação antes do `200`.
- [x] Admitir comandos suportados e texto privado não vazio para a conversa; descartar comandos desconhecidos sem criar inbox.

### V2.6 — Domínio e regras — parcial

- [x] Implementar identidade Telegram, produtos, observações e estados persistentes da conversa.
- [x] Usar centavos inteiros, limite de três produtos e comparação com preço-alvo.
- [x] Testar regras isoladas de framework e banco.

**Restante:** queda percentual e entrega de alertas em V2.12. Modelo contextual em C3, sem duplicar sua implementação aqui.

### V2.7 — PostgreSQL e isolamento — parcial

- [x] Implementar migrações, repositórios de inbox, identidade, conversa, produtos, resultados e observações com índices/constraints e testes de isolamento.
- [x] Separar runtime/migrador, exigir TLS verificado e validar readiness por consulta ao banco.
- [ ] Revisar privilégios padrão para objetos criados fora do migrador, preservando dependências gerenciadas.

**Restante:** tabelas de trabalhos/entregas em V2.12/C4; migração de propriedade em C2. Recibos de migrações existentes no histórico; não reaplicar operações administrativas por esta lista.

### V2.8 — Inbox e conversa — implementadas; menu pendente

- [x] Implementar `/start`, `/ajuda`, `/cancelar`, máquina de estados com expiração, rate limit e respostas duráveis.
- [x] Implementar claim/lease, deduplicação, recuperação e distinção entre falha transitória, permanente e envio incerto.
- [ ] Confirmar menu do BotFather conforme comandos implantados, incluindo `/cancelar` e `/verificar`.

**Retomada:** o worker atual executa a coleta manual fora do request HTTP, mas ainda no processamento do comando; desacoplar em C4.

### V2.9 — Cadastro, listagem e remoção — implementados; regressões manuais pendentes

- [x] Integrar URL → apelido → alvo → intervalo → confirmação, listagem própria, cancelamento e remoção lógica confirmada.
- [x] Testar concorrência, replay e isolamento no PostgreSQL; registrar aceite relatado de duas contas e limite individual de três produtos.
- [ ] Completar matriz manual de URL repetida após avanço, apelido/preço inválidos, etapa indisponível e cancelamento após cada passo.
- [ ] Completar evidência das sequências de dois cancelamentos, repetição de `/produtos` e início/cancelamento com filtros de ativos, sem refazer os aceites já registrados.

**Saída:** regressões restantes registradas; cadastro/listagem/remoção e limite entre contas já possuem aceite. Referência: [aceitação com duas contas](docs/V2_TELEGRAM_TWO_USERS_ACCEPTANCE.md).

### V2.10 — Transporte seguro — implementado

- [x] Validar URL, DNS completo, IP público fixado, TLS/SNI, redirects, prazo, tamanho e framing HTTP.
- [x] Compor transporte com coletor Mercado Livre e testar ataques/falhas em ambiente controlado.

**Retomada:** manter essas garantias em cada adaptador futuro. Testes controlados não comprovam acesso comercial à loja.

### V2.11 — Verificação manual — implementada; aceite real bloqueado

- [x] Implementar extração JSON-LD/meta/DOM, centavos, identidade final e falhas explícitas sem preço zero.
- [x] Integrar `/verificar <UUID>` com escopo do proprietário, histórico idempotente e checkpoint recuperável da resposta.
- [x] Registrar implantação histórica de `c830c6c` e migração `20260916_10`; tentativas reais falharam em coleta.
- [x] Classificar 403/429 como `access_blocked` e abertura de transporte como `transport_failed` (`d829a10`, testes locais e CI registrados).
- [ ] Confirmar implantação dessa classificação e mensagem de bloqueio no bot real.
- [ ] Validar UUID inválido e de outro proprietário no bot real; implementação possui testes automatizados.
- [ ] Obter preço real por fonte viável, persistir e responder pelo Telegram; registrar origem e limitações.

**Saída:** preço real observado e isolamento aceitos. Persistência de uma falha não conclui o aceite. Investigar viabilidade C7 se necessário, sem presumir autorização de API nem contratar provedor automaticamente.

### V2.12 — Histórico, executor periódico e alertas públicos — não implementados

**Pode ser preparado agora; aceite depende de V2.11.** Entregar primeiro contrato/testes, depois persistência/executor e por último agendamento/entrega. Se C4 for implementado antes, reutilizá-lo.

- [ ] Comparar último preço válido, preço-alvo e queda percentual apenas para identidade/condições compatíveis; explicitar limitações do histórico legado.
- [ ] Criar trabalho persistido e comando executor separado da API, com lease, prazo, quota e retentativas limitadas.
- [ ] Persistir observação e intenção de alerta atomicamente, com entrega Telegram independente e resultado externo incerto explícito.
- [ ] Configurar agendamento externo em UTC, inicialmente candidato GitHub Actions; validar recuperação, concorrência e cancelamento de monitoramento removido.
- [ ] Aceitar alerta público real e recuperação após interrupção, sem duplicar observação lógica.

**Retomada:** C4 amplia para tarefa contextual e outros canais; C6 amplia comparabilidade e elegibilidade. Não antecipar frontend, pareamento ou busca para fechar este bloco público.

### V2.13 — Operação e fechamento — parcial

- [x] Implementar readiness PostgreSQL e correlação de erros sem credenciais/payloads.
- [ ] Incluir extensão no CI: job com Node 24, `npm ci`, tipos, 29 testes Vitest e build preparado e reproduzido localmente em 19/09/2026; concluir após execução remota aprovada.
- [ ] Completar indicadores de atrasos/falhas, cobertura de logs e quotas operacionais.
- [ ] Validar permissões, backup/restauração, rollback e rotação de segredos em procedimento controlado.
- [ ] Testar cold start, Telegram indisponível, loja bloqueada e banco indisponível; usar staging/injeção segura para falhas de envio.
- [ ] Concluir aceite de cadastro → coleta periódica → alerta real com dois proprietários.

**Saída:** piloto utilizável sem operar infraestrutura manualmente; aceites de cadastro não substituem o aceite de alerta.

## V3 — Conta Argos e observação contextual — futura

Lista canônica: **C2–C6 abaixo**, precedida do aceite C1. Autenticação estabelecida, identidade externa vinculada à conta Argos, API escopada, pareamento e extensão conectada substituem a antiga lista genérica da V3. O modo local permanece disponível. Novos canais além de Telegram/frontend não têm compromisso de versão.

**Saída:** uma conta usa Telegram, frontend e conector Mercado Livre com isolamento, revogação e alertas comparáveis aceitos. Migrações, implantação e aceite real fazem parte da entrega; estrutura de diretórios não comprova conclusão.

## Evolução contextual — ADR 0007

Decisão: [arquitetura contextual](docs/decisions/0007-contextual-multistore.md). Esta seção é a fonte de progresso do plano; o ADR registra as decisões, não uma segunda lista de execução.

C1 é a prova local atual; C2–C6 formam a V3 contextual; C7–C9 são expansões posteriores. A sequência de integração do ADR permanece: C1 → C2 → C3 → C4 → C5 → C6. Preparação isolada e manutenção da V2 podem avançar enquanto um aceite externo está pendente; isso não encerra o gate nem autoriza liberar a etapa dependente. Cada checkbox exige evidência correspondente, e código, implantação e aceite são estados distintos.

### C1 — Observação local da página aberta

**Horizonte: agora — implementação local pronta; aceite depende de Chrome real.**

- [x] Registrar as decisões no ADR 0007.
- [x] Implementar ação explícita de observação local no popup, sem enviar dados ao backend ou alterar o monitoramento V1.
- [x] Extrair preço DOM em BRL, recusar valores inválidos/conflitantes e manter elegibilidade, vendedor, variante, frete e contexto desconhecidos quando não comprovados.
- [x] Cobrir extração, moeda, ambiguidade, bloqueio e ausência de conteúdo sensível com testes sintéticos.
- [x] Validar TypeScript, 29 testes Vitest (12 novos), build e `git diff --check` em 18/09/2026.
- [ ] Executar todos os casos de [aceitação em Chrome real](docs/CONTEXTUAL_CAPTURE_ACCEPTANCE.md), incluindo outra conta/perfil, mudança de variante e regressão da V1.
- [ ] Registrar evidência do aceite e corrigir divergências encontradas em anúncios reais.

**Saída:** leitura contextual local aceita em Chrome real, sem exportação de sessão ou efeitos no monitoramento existente.

### C2 — Identidade Argos e migração aditiva

**Horizonte: V3, após C1.** Evolui a identidade Telegram de V2.6–V2.9 por migração aditiva; não reimplementa os comandos.

- [ ] Criar `argos_user_id` UUID e vínculo único com a identidade Telegram existente; preservar `chat_id` como destino.
- [ ] Preencher contas e vínculos para os usuários existentes por migração aditiva.
- [ ] Migrar propriedade de produtos, observações, trabalhos e resultados sem remover prematuramente as relações antigas.
- [ ] Obter o proprietário da autenticação, nunca de identificador livre no payload.
- [ ] Escopar repositórios e relações ao proprietário, com constraints contra vínculos cruzados.
- [ ] Validar upgrade, preservação de registros e compatibilidade dos comandos em PostgreSQL real.
- [ ] Testar dois proprietários, inclusive tentativa de acesso por identificador alheio e preservação dos limites individuais.
- [ ] Preparar implantação e recuperação da migração; confirmar o resultado antes de retirar a compatibilidade antiga.

**Saída:** identidade interna em uso, dados preservados e Telegram funcional com isolamento comprovado.

### C3 — Oferta, monitoramento e observação contextual

**Horizonte: V3, após C2.** Evolui produtos e histórico de V2.7/V2.11. Migrar também falhas legadas para tentativas, preservando vínculos e idempotência.

- [ ] Separar produto/variante, oferta, monitoramento, observação e tentativa de coleta.
- [ ] Identificar oferta por loja/anúncio e vendedor/variante quando disponíveis; manter desconhecidos explícitos.
- [ ] Migrar registros existentes como Mercado Livre, preservando histórico e método de extração sem inventar contexto ou condições.
- [ ] Registrar preço inteiro, moeda, disponibilidade, condições de pagamento/cupom/assinatura/quantidade e frete separado.
- [ ] Registrar elegibilidade e evidência, horários observado/recebido, validade comercial e geração contextual quando aplicáveis.
- [ ] Separar origem, contexto de acesso, método de extração e personalização.
- [ ] Separar prazo de atualização da validade da oferta e deixar claro que o alvo inicial exclui frete.
- [ ] Registrar falhas como tentativas sem preço; preservar observações válidas sem sobrescrita normal.
- [ ] Declarar capacidades por adaptador e manter históricos privados por proprietário, sem equivalência automática entre lojas.
- [ ] Testar migração, dados desconhecidos, propriedade e ausência de conversão de falha em preço zero.

**Saída:** modelo contextual persistido e validado, compatível com os registros anteriores.

### C4 — Trabalhos e entregas duráveis

**Horizonte: V3, após C3.** Reaproveita as garantias da inbox e o executor/entregas de V2.12, caso já concluídos. Inbox de comandos e fila de coletas têm responsabilidades diferentes. Entrega frontend e teste com conector real só encerram após C5; usar adaptadores de teste antes disso.

- [ ] Fazer `/verificar` persistir trabalho e intenção de confirmação antes de responder que a coleta foi agendada.
- [ ] Separar execução da coleta do processamento de comandos, com tentativa, lease e prazo.
- [ ] Selecionar fontes conforme a tarefa; coleta pública não espera o navegador e não se apresenta como personalizada.
- [ ] Definir cancelamento ao remover monitoramento, quotas de trabalhos pendentes e recusa de resultados tardios.
- [ ] Recusar resultados de leases substituídos e revalidar autorização ao aceitar o resultado.
- [ ] Aplicar idempotência por resultado lógico; mesma chave com conteúdo divergente deve falhar.
- [ ] Gravar observação e intenção de notificar na mesma transação.
- [ ] Manter entregas Telegram e frontend independentes, com retentativas limitadas e tratamento explícito de envio incerto.
- [ ] Testar concorrência, interrupção, retomada, timeout, resultado divergente e conector offline em PostgreSQL real.
- [ ] Validar implantação do executor separado, recuperação após reinício e indicadores de trabalho atrasado/falhas sem dados sensíveis.

**Saída:** comando agenda trabalho durável e entrega posterior recuperável, sem promessa de exatamente uma entrega externa.

### C5 — Pareamento e fluxo completo do conector

**Horizonte: V3, após a base C2–C4 e aceite C1.** Entregar em incrementos: autenticação/API → pareamento/chaves → protocolo/geração → revogação/privacidade → integração Chrome. Cada incremento deve ser revisável separadamente.

- [ ] Integrar autenticação estabelecida no frontend; acesso a dados somente pela API Argos, sem mecanismo próprio de senhas.
- [ ] Implementar pareamento com código descartável, expiração, confirmação na conta autorizada e auditoria.
- [ ] Criar `connector_id` e chave por instalação, protegida do acesso de content scripts.
- [ ] Implementar contexto por usuário/conector/loja/geração, com invalidação por desconexão ou troca de conta.
- [ ] Tratar contexto desconhecido explicitamente quando não houver evidência confiável, sem coletar a identidade real da loja.
- [ ] Implementar aquisição de tarefas com operação permitida, oferta, geração, prazo, tentativa e nonce.
- [ ] Restringir tarefas e resultados por schema, URL, loja, tamanho e volume; não aceitar scripts, seletores executáveis ou HTTP arbitrário.
- [ ] Assinar resultados vinculando tarefa, tentativa, geração, nonce e conteúdo; assinatura não comprova veracidade comercial.
- [ ] Revalidar vínculo, proprietário, loja, oferta, lease e revogação na transação de aceitação.
- [ ] Permitir visualizar e revogar conectores, impedindo novas aquisições e submissões após revogação.
- [ ] Exibir conectividade, última observação e intervenção necessária, distinguindo navegador offline de login necessário.
- [ ] Integrar observação de página aberta ao backend preservando o modo local da V1.
- [ ] Implementar retenção e exclusão solicitada de dados personalizados; append-only não bloqueia exclusão por privacidade.
- [ ] Testar replay, pareamento expirado/reutilizado, revogação concorrente, troca de contexto, tarefas maliciosas e acesso entre proprietários.
- [ ] Validar mensagens no contexto privilegiado por schema estrito, incluindo conteúdo oculto, preços iguais com condições distintas e cupom fora do anúncio principal.
- [ ] Inspecionar payloads/logs e comprovar ausência de HTML integral, cookies, tokens e identificadores reais de sessão.
- [ ] Validar em Chrome real que Telegram, frontend e extensão vinculados acessam apenas os dados da mesma conta.

**Saída:** fluxo Mercado Livre completo e revogável, com isolamento, privacidade e regressão V1 comprovados.

### C6 — Comparação e alertas condicionais

**Horizonte: V3, após C3–C5.** Evolui as regras públicas de V2.12; não reaplica porcentagens entre observações incompatíveis.

- [ ] Comparar apenas oferta, variante, moeda, quantidade e condições compatíveis.
- [ ] Impedir falso alerta por mudança de vendedor, condição do produto, pagamento ou geração contextual.
- [ ] Aplicar condições aceitas pelo usuário e evidência de elegibilidade antes de disparar alertas condicionais.
- [ ] Exibir preço observado, condições, frete desconhecido e idade da observação sem prometer preço final garantido.
- [ ] Manter preço público e observação de sessão identificáveis e independentes.
- [ ] Testar Pix, cupom incerto, assinatura, quantidade, frete desconhecido, oferta expirada e observação desatualizada.
- [ ] Validar alertas e entregas por canal com duas contas, incluindo falhas e recuperação.

**Saída:** alertas baseados em evidência comparável, sem misturar contextos ou usuários.

### C7 — Fontes oficiais comprovadas

**Horizonte: expansão da V3.** A investigação de viabilidade pode ser antecipada se a coleta pública continuar bloqueada; integração exige capacidade comprovada e modelo compatível. Não é requisito para liberar o conector Mercado Livre.

- [ ] Comprovar acesso autorizado à API oficial do Mercado Livre, campos, identidade da oferta, contexto de preço e limites.
- [ ] Registrar a capacidade real e a decisão de habilitar ou manter a fonte indisponível; ausência de acesso não autoriza simular suporte.
- [ ] Integrar somente a capacidade comprovada, mantendo credenciais no executor e fora da extensão.
- [ ] Aplicar seleção por capacidade e classificar falhas, sem depender de cascata obrigatória pelo navegador.
- [ ] Validar preço/identidade, permissões, quotas, falha da API e apresentação correta da origem/contexto.
- [ ] Manter provedor pago desabilitado; qualquer avaliação exige métricas de bloqueio e aprovação de teto mensal antes de ativação.

**Saída:** fontes habilitadas com evidência de viabilidade e comportamento verificável; capacidades indisponíveis documentadas.

### C8 — Busca limitada de oportunidades

**Horizonte: expansão posterior, após C5/C6 e capacidade de busca comprovada.** Página de produto aberta não implica suporte a navegação autônoma. Não bloqueia o MVP contextual.

- [ ] Criar intenção privada por loja, consulta/categoria, orçamento, filtros, frequência, validade e limite de candidatos.
- [ ] Distribuir tarefas somente ao conector do proprietário, com limites de páginas, execução e cancelamento.
- [ ] Receber candidatos normalizados, sem explorar histórico de compras, carrinho ou conta de forma irrestrita.
- [ ] Deduplicar e pontuar com evidências acessíveis ao proprietário e observações compatíveis.
- [ ] Informar falta de histórico suficiente sem fabricar preço de referência ou desconto.
- [ ] Permitir consultar/excluir intenções e respectivos dados personalizados conforme retenção definida.
- [ ] Testar expiração, limites, cancelamento, conector offline e duas contas buscando a mesma categoria com resultados independentes.

**Saída:** descoberta delimitada, auditável e privada, sem ações de compra.

### C9 — Novas lojas em incrementos independentes

**Horizonte: expansão posterior, após o fluxo Mercado Livre aceito.** Amazon e Shopee são entregas independentes; não exigem C8 quando suportarem apenas observação de página aberta.

- [ ] Amazon Brasil: comprovar capacidades, acesso e requisitos antes de implementar o adaptador.
- [ ] Amazon Brasil: implementar URL, identidade da oferta, extração e condições das capacidades aprovadas.
- [ ] Amazon Brasil: aprovar fixtures, teste real controlado, duas contas e regressão Mercado Livre antes da liberação.
- [ ] Shopee Brasil: comprovar capacidades, acesso e requisitos antes de implementar o adaptador.
- [ ] Shopee Brasil: implementar URL, identidade da oferta, extração e condições das capacidades aprovadas.
- [ ] Shopee Brasil: aprovar fixtures, teste real controlado, duas contas e regressão das lojas existentes antes da liberação.
- [ ] Atualizar matriz de capacidades, permissões da extensão e documentação de produto para cada loja liberada.

**Saída:** cada loja habilitada individualmente com evidências, sem generalizar suporte a capacidades não verificadas.

---

## V4 — Back-end local/autohospedado — futuro sem data

Retoma instalação, configuração, execução e backup hoje operados na cloud; depende de API estável. Não é requisito para preservar a extensão V1 local.

- [ ] Definir sistemas operacionais e banco suportados.
- [ ] Criar instalação, atualização e serviço em segundo plano.
- [ ] Proteger API por loopback e credencial por instalação.
- [ ] Implementar backup, diagnóstico e desinstalação.
- [ ] Criar testes de instalação nos sistemas suportados.

**Critério de conclusão:** usuário instala e remove o Argos sem configurar Python, banco ou scheduler.

---

## V5 — Android — futuro sem data

Reutiliza autenticação/API de C5 e histórico/entregas de C3–C6. Não depende da distribuição autohospedada V4.

- [ ] Criar aplicativo com Kotlin e Jetpack Compose.
- [ ] Integrar autenticação e API cloud.
- [ ] Gerenciar produtos, histórico e notificações.

---

## Fora das versões atuais

- [ ] Comparação automática entre anúncios equivalentes.
- [ ] Recomendação de melhor momento de compra.
- [ ] Relatórios em PDF e CSV.
- [ ] Gráficos avançados de histórico.
Amazon e Shopee são acompanhadas exclusivamente em C9. Outras lojas continuam sem compromisso de versão.
- [ ] Extração de componentes para microsserviços, somente se houver necessidade comprovada.
