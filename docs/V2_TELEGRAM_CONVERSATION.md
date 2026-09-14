# Conversa do bot Telegram na V2

Este documento define os comandos, estados e respostas do MVP Telegram. O bot atende somente conversas privadas e usa português do Brasil na V2.

## Regras gerais

- somente mensagens de texto em conversas privadas são processadas;
- `telegram_user_id` identifica o proprietário dos dados;
- `chat_id` indica apenas onde a resposta será enviada;
- comandos são comparados sem diferenciar maiúsculas de minúsculas;
- espaços no início e no fim são removidos antes da validação;
- cada mensagem avança no máximo uma etapa da conversa;
- `/cancelar` interrompe qualquer fluxo incompleto;
- outro comando conhecido pode substituir o fluxo atual após cancelar seu rascunho;
- mensagens repetidas com o mesmo `update_id` não repetem ações;
- textos recebidos do usuário ou da loja são enviados como texto simples, sem interpretação de HTML ou Markdown;
- o webhook apenas valida e aceita o update; coleta de página e outras tarefas lentas ocorrem fora da requisição.

O bot não solicita senha, código de autenticação, dados de pagamento ou token. Respostas nunca incluem stack trace, segredo, query SQL, HTML coletado ou detalhes internos da infraestrutura cloud.

## Comandos do MVP

| Comando | Disponibilidade | Resultado |
| --- | --- | --- |
| `/start` | sempre | cria ou atualiza o usuário e apresenta o resumo inicial |
| `/ajuda` | sempre | lista os comandos e explica o fluxo de cadastro |
| `/cancelar` | durante ou fora de um fluxo | apaga o rascunho atual sem alterar produtos existentes |
| `/adicionar` | estado ocioso | inicia o cadastro de um produto |
| `/produtos` | estado ocioso | lista os produtos ativos do proprietário |
| `/remover` | estado ocioso | inicia a seleção de um produto para remoção |
| `/verificar` | estado ocioso | inicia uma coleta manual de um produto cadastrado |

Comandos com sufixo de nome do bot, como `/ajuda@argos_bot`, só serão aceitos se o sufixo corresponder ao bot configurado. Como grupos são recusados, esse formato existe apenas para compatibilidade com o protocolo do Telegram.

## Fluxo de cadastro

O cadastro usa um rascunho persistido e só cria o produto depois da confirmação final.

```text
OCIOSO
  │ /adicionar
  ▼
AGUARDANDO_URL
  │ URL válida do Mercado Livre
  ▼
AGUARDANDO_APELIDO
  │ apelido válido
  ▼
AGUARDANDO_PRECO_ALVO
  │ preço válido
  ▼
AGUARDANDO_INTERVALO
  │ 12 ou 24 horas
  ▼
AGUARDANDO_CONFIRMACAO
  ├── confirmar ──► produto criado ──► OCIOSO
  └── corrigir  ──► AGUARDANDO_URL
```

Em qualquer estado, `/cancelar` retorna para `OCIOSO` e remove somente o rascunho.

### `AGUARDANDO_URL`

Entrada esperada: uma URL HTTPS de anúncio do Mercado Livre.

Validações imediatas:

- protocolo HTTPS;
- ausência de usuário, senha e porta alternativa;
- host explicitamente permitido;
- caminho com identificador de produto reconhecido;
- tamanho máximo definido pela camada de entrada.

A validação completa de DNS, IP e redirecionamentos ocorre antes da primeira coleta. Salvar um rascunho não autoriza uma requisição de rede.

### `AGUARDANDO_APELIDO`

Entrada esperada: nome curto usado pelo próprio usuário para reconhecer o produto.

- espaços repetidos são normalizados;
- texto vazio é recusado;
- caracteres de controle são recusados;
- o tamanho máximo inicial é de 60 caracteres;
- o texto é sempre tratado como conteúdo, nunca como HTML.

### `AGUARDANDO_PRECO_ALVO`

Formatos aceitos:

- `2500`;
- `2500,90`;
- `R$ 2.500,90`.

O valor é normalizado para centavos inteiros. Valores iguais ou menores que zero, com mais de duas casas decimais ou fora do limite monetário da aplicação são recusados. A resposta de confirmação sempre apresenta o valor normalizado em BRL.

### `AGUARDANDO_INTERVALO`

Entradas aceitas: `12` ou `24`, representando horas. Texto adicional e valores diferentes são recusados na V2.

### `AGUARDANDO_CONFIRMACAO`

Entradas aceitas:

- `confirmar`: cria o produto se o limite e a unicidade ainda forem válidos;
- `corrigir`: reinicia o rascunho a partir da URL;
- `/cancelar`: descarta o rascunho.

A confirmação revalida todas as regras dentro da transação. Isso evita ultrapassar o limite de três produtos caso duas conversas sejam processadas concorrentemente.

## Fluxo de remoção

```text
OCIOSO
  │ /remover
  ▼
AGUARDANDO_PRODUTO_PARA_REMOVER
  │ seleção válida
  ▼
AGUARDANDO_CONFIRMACAO_DE_REMOCAO
  ├── remover   ──► produto desativado ──► OCIOSO
  └── /cancelar ──► OCIOSO
```

O bot apresenta uma lista numerada de produtos do proprietário. A seleção usa o número temporário apresentado, mas o servidor resolve e persiste o UUID correspondente no rascunho. Antes de remover, o caso de uso consulta novamente o produto com `owner_id` e UUID.

A remoção é lógica: o produto deixa de ser monitorado, mas o histórico permanece disponível para evolução futura.

## Fluxo de verificação manual

```text
OCIOSO
  │ /verificar
  ▼
AGUARDANDO_PRODUTO_PARA_VERIFICAR
  │ seleção válida
  ▼
VERIFICACAO_SOLICITADA ──► OCIOSO
```

O bot confirma que a verificação foi solicitada e retorna imediatamente ao estado ocioso. A coleta é executada fora do processamento do webhook. Repetir o mesmo update não cria uma segunda solicitação, e uma nova solicitação para um produto já em execução é recusada de maneira segura.

## Estados persistidos

```text
IDLE
AWAITING_URL
AWAITING_ALIAS
AWAITING_TARGET_PRICE
AWAITING_INTERVAL
AWAITING_ADD_CONFIRMATION
AWAITING_REMOVE_SELECTION
AWAITING_REMOVE_CONFIRMATION
AWAITING_CHECK_SELECTION
```

Cada estado contém:

- `owner_id`;
- nome do estado;
- dados parciais estritamente necessários;
- `created_at` e `updated_at` em UTC;
- versão para controle de concorrência;
- expiração do rascunho.

Um rascunho expirado é descartado e o usuário recebe orientação para executar `/adicionar` novamente. O estado nunca armazena token do bot, cabeçalhos do webhook, HTML da loja ou credenciais.

## Respostas de sucesso

### `/start`

```text
Olá! Eu sou o Argos.

Posso acompanhar até 3 produtos do Mercado Livre e avisar quando o preço atingir seu objetivo.

Use /adicionar para cadastrar um produto ou /ajuda para ver os comandos.
```

### Produto criado

```text
Produto adicionado.

Nome: {apelido}
Preço-alvo: {preço em BRL}
Verificação: a cada {12|24} horas
```

### Verificação solicitada

```text
Verificação de {apelido} solicitada. Avisarei quando o resultado estiver disponível.
```

Esses textos são modelos de conteúdo, não contratos byte a byte. Testes devem verificar código de resposta e dados essenciais, evitando falhas por ajustes editoriais pequenos.

## Modelo de erros

Erros possuem um código interno estável e uma mensagem pública segura.

```text
ConversationError
├── code: identificador estável
├── public_message: texto seguro em PT-BR
├── retryable: bool
└── correlation_id: identificador opcional sem dado sensível
```

| Código | Quando ocorre | Resposta pública |
| --- | --- | --- |
| `private_chat_required` | update veio de grupo, canal ou chat incompatível | Este bot funciona somente em conversa privada. |
| `unsupported_update` | update não contém mensagem de texto suportada | Não consigo processar esse tipo de mensagem. Use /ajuda. |
| `unknown_command` | comando não pertence à lista fechada | Comando não reconhecido. Use /ajuda. |
| `conversation_expired` | rascunho ultrapassou sua validade | Esse cadastro expirou. Use /adicionar para começar novamente. |
| `invalid_url` | URL não corresponde ao formato permitido | Envie uma URL válida de produto do Mercado Livre. |
| `unsafe_destination` | DNS, IP ou redirecionamento foi bloqueado | Não foi possível usar essa URL com segurança. |
| `invalid_alias` | apelido vazio, longo ou com caracteres proibidos | Use um nome de até 80 caracteres. |
| `invalid_target_price` | preço não pôde ser normalizado | Informe um preço válido, por exemplo: R$ 1.299,90. |
| `invalid_interval` | intervalo diferente de 12 ou 24 | Escolha 12 ou 24 horas. |
| `confirmation_required` | confirmação não reconhecida | Responda confirmar, corrigir ou use /cancelar. |
| `product_limit_reached` | proprietário já possui três produtos ativos | Você já monitora o limite de 3 produtos. Remova um antes de adicionar outro. |
| `duplicate_product` | mesmo anúncio já está ativo para o proprietário | Esse produto já está na sua lista. |
| `product_not_found` | seleção não pertence ao usuário ou não existe | Produto não encontrado na sua lista. |
| `check_already_running` | produto já possui coleta reservada | Esse produto já está sendo verificado. |
| `rate_limited` | usuário excedeu o limite operacional | Muitas solicitações em pouco tempo. Tente novamente mais tarde. |
| `temporary_failure` | banco, Telegram ou serviço temporariamente indisponível | Não consegui concluir agora. Tente novamente mais tarde. |

Um recurso de outro usuário e um recurso inexistente produzem sempre `product_not_found`. A resposta não revela se o UUID existe para outro proprietário.

## Falhas de coleta comunicadas depois do webhook

| Código interno | Mensagem ao usuário |
| --- | --- |
| `product_not_found_at_store` | O anúncio não está mais disponível. |
| `price_not_found` | Encontrei o anúncio, mas não consegui identificar um preço confiável. |
| `access_blocked` | O Mercado Livre bloqueou temporariamente a verificação. Tentarei novamente depois. |
| `temporary_collection_failure` | Não foi possível verificar o preço agora. Tentarei novamente depois. |

Nenhuma dessas falhas registra preço zero ou dispara alerta de queda.

## Concorrência e idempotência

Para cada update aceito:

1. reivindicar atomicamente o `update_id`;
2. identificar o proprietário pelo `telegram_user_id`;
3. carregar o estado por proprietário;
4. validar a entrada e executar uma única transição;
5. persistir estado e alterações com controle de versão;
6. reservar a resposta ou tarefa de saída;
7. marcar o update como concluído.

Se houver conflito de versão, o caso de uso recarrega o estado uma única vez. Persistindo o conflito, responde com `temporary_failure`, sem executar novamente efeitos que já tenham sido confirmados.

## Fora do escopo desta conversa

- menus inline e botões interativos;
- comandos administrativos;
- grupos e canais;
- alteração parcial de produto já salvo;
- comparação entre anúncios;
- suporte à Shopee;
- localização em outros idiomas;
- autenticação OIDC.

## Persistência implementada em preparação

O repositório oferece `begin` para iniciar cadastro sem sobrescrever rascunho ativo (um expirado pode ser substituído), e `advance` para atualizar somente a versão ativa lida pelo chamador. A expiração inicial é preservada ao avançar; a aplicação escolhe sua duração ao iniciar. A versão UUID é renovada na criação e em cada avanço, impedindo sobrescrita concorrente e atualização após cancelamento/recriação. A revisão `20260913_06` adiciona a coluna; aplicada em produção pelo workflow `34788321746`, commit `75b31bf`. O grafo de transições vive no domínio. Este preparo não libera `/adicionar` nem valida URL, apelido ou dinheiro: os casos de uso das etapas ainda deverão validar dados e coordenar a idempotência por update com os efeitos persistidos.

Validação: CI `34787786771`, commit `5099b39`, aprovado em PostgreSQL real. Cobre preservação de ativo, substituição de expirado, rejeição na expiração, avanço concorrente e snapshot anterior ao cancelamento/recriação no mesmo timestamp. A suíte local antes da adição da coluna UUID concluiu 104 testes, com 29 integrações ignoradas; a validação final do esquema e do adaptador versionado vem do CI.

Verificação independente em produção: revisão `20260913_06`, coluna `version` UUID NOT NULL com default `gen_random_uuid()`, ownership de `argos_migrator`, DML do runtime preservado e nenhuma leitura por `anon`, `authenticated` ou `service_role`. A migração não implanta o código do repositório no Render nem libera `/adicionar`.

## Início de cadastro idempotente — contrato preparado

`BeginTelegramRegistration` valida `/adicionar`, identidade, update, horário e lease e delega à porta `TelegramRegistrationRepository.begin_for_update`. A política inicial exige `/start` prévio, inicia rascunho de 15 minutos e preserva uma operação já ativa, orientando `/cancelar` antes de outro cadastro.

O futuro adaptador deve conferir lease vigente e identidade/comando contra o payload da inbox, serializar update e proprietário e gravar rascunho e resposta na mesma transação. Reprocessamento devolve a resposta persistida, mesmo após expiração ou cancelamento, sem recriar rascunho nem renovar prazo. Também deve persistir respostas de operação já ativa ou acesso ainda não registrado. Não usar operações independentes do repositório atual, pois elas abririam uma janela entre efeito e resultado.

Este incremento implementa apenas aplicação e contrato. Persistência de resultados, migração, composição no worker e liberação no webhook ainda estão pendentes. Testar no PostgreSQL: chamadas repetidas e concorrentes, recriação do pool, recuperação após efeito persistido, lease perdido, identidade divergente, rollback após falha ao guardar a resposta e preservação do rascunho ativo. Reutilizar o resultado não garante envio único pela Bot API; o tratamento de resultado externo incerto permanece necessário.

## Adaptador de início idempotente

`PostgreSQLTelegramRegistrationRepository` e a migração `20260913_07` estão implementados, ainda sem aplicação em produção ou integração ao worker. A tabela `telegram_registration_results` referencia o update da inbox e guarda proprietário, chat, resposta e horário. Runtime recebe somente SELECT/INSERT, sem UPDATE/DELETE; roles públicas ficam sem acesso. O downgrade recusa remover resultados existentes.

A transação bloqueia o update, verifica lease contra o relógio PostgreSQL e identidade/comando contra seu payload, reutiliza um resultado existente ou bloqueia o usuário para decidir entre iniciar cadastro, preservar ativo e exigir `/start`. Rascunho e resposta são gravados juntos. O resultado persistido não faz envio externo. A retenção da inbox deverá preservar resultados; a FK impede removê-la sem uma política explícita.

Validação final do adaptador: CI `34788802511`, commit `af907fb`, aprovado em PostgreSQL real. Reprocessamento com novo lease preservou a resposta após remover o rascunho, sem recriá-lo; falha SQL ao guardar a resposta reverteu a criação; concorrência preservou uma operação ativa; lease expirado e identidade divergente foram recusados; runtime sem UPDATE/DELETE e downgrade com dados recusado. A migração foi aplicada em produção; o comando continua pendente.

Aplicação em produção de `20260913_07`: workflow `34789307934`, commit `a924821`, concluído com sucesso. Consulta independente confirmou revisão, tabela de resultados vazia sob ownership de `argos_migrator`, runtime com SELECT/INSERT sem UPDATE/DELETE e roles públicas sem leitura. A integração ao worker e webhook continua pendente.

## Início integrado no piloto (13/09/2026)

O webhook e o worker aceitam `/adicionar` para iniciar um rascunho de teste com duração de 15 minutos, após `/start`. Rascunho e resposta são persistidos na mesma transação sob o lease da inbox. Uma operação ativa é preservada; o mesmo update reutiliza a resposta original, inclusive após recuperação do worker. `/cancelar` permite remover esse rascunho.

A ajuda e a resposta de início esclarecem que o recebimento da URL e o cadastro completo ainda serão liberados. Texto livre continua confirmado sem persistência. A integração foi implantada manualmente no deploy `dep-dajk7sh594qs73ch8spg` (commit `9a23c79`). O usuário confirmou a sequência de ajuda, início, operação ativa, cancelamento e novo início; consulta independente confirmou cinco comandos concluídos em uma tentativa, dois inícios persistidos, uma resposta de operação ativa e um único rascunho vazio com duração de 15 minutos. Isso não conclui o cadastro de produtos da V2.9.

## Contrato preparado para receber URL (14/09/2026)

`ReceiveTelegramRegistrationURL` entrega texto original, URL normalizada (ou ausência quando inválida), proprietário, update e lease à porta transacional. O adaptador PostgreSQL foi implementado e confere o payload e o lease, serializa o proprietário, reutiliza resultados anteriores e grava avanço e resposta juntos na tabela existente telegram_registration_results; não exige migração. A aprovação dos testes PostgreSQL no CI deve preceder a integração pública. URL válida só avança awaiting_url para awaiting_alias; falhas e outros estados preservam o rascunho. A expiração original não é renovada.

O validador aceita HTTPS, domínio mercadolivre.com.br e subdomínios, porta padrão ou 443 e caminhos de anúncio MLB ou catálogo /p/MLB ou produto /up/MLBU. Rejeita credenciais, hosts externos, encurtadores e caracteres ambíguos; remove fragmento e parâmetros de tracking, preservando parâmetros funcionais. A validação não comprova existência do anúncio e não substitui DNS seguro e política de SSRF na futura coleta. O webhook continua sem receber URLs neste incremento.

## Recebimento integrado (aguarda deploy)

Texto privado não vazio que não começa por / passa pela mesma admissão de comandos, com quota compartilhada e deduplicação por update. Comandos desconhecidos e texto vazio continuam confirmados sem persistência. O worker envia o texto à operação transacional da URL: sem rascunho ativo orienta iniciar; entrada inválida preserva o rascunho; URL válida avança para awaiting_alias e informa que apelido ainda não está disponível; texto posterior preserva essa etapa. A ajuda e /adicionar agora orientam o envio da URL. Testes integrados HTTP → admissão → worker → PostgreSQL → saída falsa cobrem entrada inválida, válida, repetição e quota. Deploy manual e aceitação real permanecem pendentes.

### Correção do formato /up/MLBU

A aceitação manual revelou rejeição do link de produto fornecido pelo usuário em /caneca-personalizada-hello-kitty/up/MLBU1977786059. O validador agora contempla /up/MLBU seguido de dígitos, com slug opcional; fragmentos de recomendação são removidos. Host, HTTPS, porta e credenciais continuam sob as mesmas restrições. Teste de regressão sintático e fluxo HTTP/worker/PostgreSQL preparados. Não altera o schema nem confirma existência ou coleta do produto. Novo deploy manual e reenvio como nova mensagem são necessários; resultados de updates antigos permanecem imutáveis.

## Aceitação da URL e contrato do apelido

Em 14/09/2026, o usuário confirmou registro do link /up/MLBU. Deploy manual dep-dajuqnqd0e5s73dqpkp0 no commit 162c26c ficou live. Consulta independente confirmou awaiting_alias com URL sem fragmento, expiração original de 15 minutos e update completed em uma tentativa. Aceitação manual de nova URL após avanço e cancelamento nessa sequência ainda não foi confirmada.

O contrato do apelido está preparado, sem integração pública: 1 a 60 caracteres após NFC e normalização de espaços; controles e links são rejeitados. Avanço awaiting_alias → awaiting_target_price deve preservar URL e expiração, renovar versão e persistir resposta na mesma transação. Inputs inválidos também têm resultado durável. O adaptador PostgreSQL do apelido foi implementado usando a tabela existente de resultados, sem migração. Preserva URL e demais dados, expires_at e identidade, grava nova versão e resposta atomicamente. Testes PostgreSQL preparados para replay, concorrência, cancelamento, expiração, lease e rollback; CI `34849755660` aprovado no commit `406ae1f`, com PostgreSQL 17. O roteamento por estado ainda será implementado e deve decidir o passo dentro da transação após verificar resultado persistido; o bot continua informando que o apelido é uma próxima etapa.

## Texto por estado integrado (aguarda deploy)

O worker usa ReceiveTelegramRegistrationText e uma única transação PostgreSQL. Resultado persistido por update é consultado antes da seleção do passo: awaiting_url valida URL; awaiting_alias valida apelido e avança para awaiting_target_price. Outros estados recebem resposta de etapa indisponível, sem alteração. URL e apelido preservam expiração e dados anteriores. Ajuda e resposta da URL agora pedem apelido; preço-alvo continua pendente. Quota compartilhada e webhook permanecem iguais. CI e aceitação real devem preceder o próximo passo.

## Aceitação do apelido (14/09/2026)

Deploy manual dep-dajvn4ojo6nc73ffi1k0 no commit ebb7dcc confirmado live. Usuário confirmou funcionamento; consulta independente encontrou quatro updates completed em uma tentativa, resultados de início, URL e apelido, e um rascunho awaiting_target_price com URL/apelido e duração original de 15 minutos. A consulta não exibiu identificadores ou conteúdo pessoal.

Apelido inválido, etapa indisponível e cancelamento após apelido continuam pendentes de aceitação manual: não aparecem na janela verificada e o rascunho permanece. Essa evidência confirma o caminho principal, sem concluir todos os testes reais propostos. Próximo incremento: contrato e validação monetária do preço-alvo em centavos; entrada ainda não liberada.

## Preço-alvo: contrato preparado

Validação isolada aceita valores BRL inteiros, decimal com vírgula de uma ou duas casas e agrupamento de milhares por ponto, com prefixo R$ opcional. Exemplos: 2500, 2500,90 e R$ 2.500,90. Conversão usa somente inteiros, sem arredondamento. Limite inicial do piloto: de 1 a 999999999 centavos (R$ 0,01 a R$ 9.999.999,99). Ponto decimal, sinais, notação científica, mais de duas casas e agrupamento irregular são recusados.

A porta transacional deve reutilizar resposta por update antes de avaliar estado, conferir lease e payload, preservar URL/apelido e expires_at e gravar target_price_cents como inteiro, nova versão e resposta formatada em BRL juntos ao avançar awaiting_target_price → awaiting_interval. Respostas inválidas também devem ser duráveis. Adaptador PostgreSQL do preço-alvo implementado usando resultados existentes, sem migração. Reconverte o texto da inbox, confere centavos, preserva URL/apelido/expiração e grava avanço/resposta juntos. Testes PostgreSQL preparados; CI 34852857248 aprovado no commit f6f2c63, com PostgreSQL 17. Integração ao worker ainda pendente; preço-alvo não foi liberado no bot.

## Preço-alvo integrado (aguarda deploy)

A seleção do texto na mesma transação contempla awaiting_target_price. O valor é validado exatamente em centavos, armazenado como inteiro em target_price_cents, e a resposta persistida confirma BRL. URL, apelido e expires_at permanecem; estado avança para awaiting_interval com nova versão. Resultado por update continua consultado antes do estado, incluindo respostas negativas. Ajuda e resposta do apelido pedem preço-alvo; intervalo continua indisponível. Integração ao worker validada no CI 34854438746, commit 15a602d; deploy e aceitação real pendentes.

## Aceitação do preço e contrato do intervalo

Em 14/09/2026, deploy manual dep-dak0ihuq1p3s739quj90 (9dbe42c) confirmado live. Entrada 150 aceita como R$ 150,00; consulta independente confirmou 15000 centavos numéricos, awaiting_interval, URL/apelido e duração original preservados, update completed em uma tentativa. Cenários inválido, etapa indisponível e cancelamento após preço não foram confirmados no relato atual.

Contrato do intervalo preparado isoladamente: texto 12 ou 24, com espaços externos tolerados; sem unidades, decimais ou outros valores. Persistência futura deve gravar interval_hours e resposta juntos, nova versão, dados e expiração preservados ao avançar para awaiting_confirmation. Confirmação e criação do produto continuarão indisponíveis nesse passo; não iniciar coleta. Nenhuma mudança pública neste incremento.

## Persistência do intervalo preparada

PostgreSQLTelegramRegistrationIntervalRepository implementado, sem migração: usa resultados existentes, reconfirma horas contra texto da inbox, exige lease válido e escopo do proprietário, e grava interval_hours como inteiro e resposta juntos ao avançar para awaiting_confirmation com nova versão. Preserva URL, apelido, preço, demais dados e expiração original. Replay reutiliza resposta antes de avaliar o estado; respostas negativas são duráveis. Testes PostgreSQL preparados para 12/24, concorrência, expiração, cancelamento, recuperação e rollback; CI 34859065182 aprovado no commit 0e7f6d8, com PostgreSQL 17. Integração ao worker ainda pendente; não cria produto nem inicia coleta.

## Intervalo integrado (aguarda deploy)

A seleção transacional do texto contempla awaiting_interval e grava interval_hours e resposta juntos, avançando para awaiting_confirmation sem renovar a expiração ou modificar dados anteriores. Resposta do preço pede 12 ou 24; ajuda lista intervalo. A confirmação e criação do produto ainda não estão disponíveis: confirmar recebe resposta durável de etapa indisponível e preserva o rascunho. Replay é consultado antes de selecionar estado. Testes de 12/24, inválido, replay e worker na confirmação preparados; CI e aceitação real pendentes.

CI da integração 34860141613 aprovado no commit 4d3a42d. Execução anterior 34859916708 falhou em dois testes por JSON literal interpretado como bind SQLAlchemy; preparação corrigida para JSON parametrizado, sem alteração da lógica de produção. Deploy e aceitação real pendentes.

## Aceitação do intervalo e preparação da confirmação

Deploy dep-dak0vj7qj5pc73fdvaug, commit dabb28b, confirmado live. Usuário confirmou funcionamento; consulta independente encontrou oito updates completed em uma tentativa, rejeição de intervalo inválido, intervalo aceito e zero rascunhos após cancelamento. A resposta de confirmação indisponível não apareceu na janela consultada e permanece pendente de aceitação manual.

Validação isolada de ProductRegistration revalida URL, apelido, centavos inteiros e intervalo 12/24; dados incompletos ou incompatíveis são recusados. Decisões confirmar/corrigir toleram espaços externos e caixa, sem aceitar texto adicional. Isso não cria produto nem autoriza coleta. Próximo contrato deve tratar lease, proprietário, estado/versão/expiração, limite de três, unicidade, criação e consumo do rascunho junto com resposta durável. Schema e integração ainda pendentes.

## Schema e contrato da confirmação preparados

20260914_08 cria monitored_products com UUID, proprietário Telegram, slot 1..3, chave Mercado Livre, URL, apelido, centavos, intervalo e criação. Unique proprietário/slot garante até três linhas por usuário no banco; proprietário/chave evita duplicatas mesmo com variações de query ou slug. A futura confirmação deve extrair a chave MLB/MLBU do caminho validado, reservar slot sob bloqueio do usuário e tratar violações como conflito durável. Modelo não equivale a coleta implementada.

Runtime recebe SELECT/INSERT, sem UPDATE/DELETE; roles públicas sem acesso. Migração deve rodar somente no executor administrativo; downgrade recusa tabela populada. Contrato exige criação, consumo de rascunho e resposta juntos; corrigir limpa dados com nova versão mantendo expires_at. Migração em produção, adaptador e bot ainda pendentes. CI preparado para constraints, grants, isolamento de proprietários e downgrade protegido.

Schema validado no CI 34863238232, commit 9e7e02c. Execuções anteriores falharam nas limpezas de usuários por nova FK; fixtures corrigidas incluindo monitored_products. Migração de produção continua pendente.

## Migração de produtos confirmada em produção

Em 14/09/2026, workflow administrativo 34864818265 (commit 8d8bb33) concluiu com sucesso. Consulta independente confirmou revisão 20260914_08, monitored_products vazia, ownership argos_migrator, runtime SELECT/INSERT sem UPDATE/DELETE/TRUNCATE e nenhuma leitura por anon/authenticated/service_role. Constraints de proprietário/slot, proprietário/chave, FK e validações presentes. Adaptador de confirmação/correção e integração pública continuam pendentes; não houve criação de produtos nesta validação.

## Confirmação/correção transacionais implementadas (sem integração pública)

O adaptador confere lease e payload e reutiliza resultado por update antes de avaliar rascunho. Em awaiting_confirmation ativo, confirmar revalida dados, deriva chave MLB/MLBU ignorando slug/query e reserva slot 1..3 sob bloqueio do usuário; criação, remoção do rascunho e resposta são atômicos. Limite e duplicata preservam rascunho com resposta durável. corrigir limpa dados e reinicia awaiting_url com nova versão, mantendo expires_at. Não envia mensagens nem inicia coleta.

Testes PostgreSQL preparados para concorrência no último slot, duplicata por chave, resposta rejeitada com rollback, expiração, lease e replay após reinício/cancelamento. CI 34865501539 aprovado no commit 3b9270d, com PostgreSQL 17. Integração ao texto e resumo apresentado ao usuário antes de confirmar ainda pendentes; o bot continua sem criar produtos.

## Cadastro confirmado integrado (aguarda deploy)

Após intervalo válido, resposta durável mostra URL, apelido, preço BRL e horas, pedindo confirmar/corrigir. Texto em awaiting_confirmation chama o adaptador de confirmação na mesma conexão e transação; não abre transação independente. Resultado por update precede seleção do estado. Confirmar cadastra e consome rascunho; corrigir limpa dados com nova versão e expiração original. Respostas esclarecem que coleta e alertas seguem indisponíveis. Ajuda atualizada; consulta e remoção continuam pendentes. CI e aceitação real do cadastro/correção pendentes.

Integração aprovada no CI 34865934346, commit c2495c7, incluindo fluxo HTTP até worker/PostgreSQL para confirmar e corrigir, resumo, deduplicação e preservação de expires_at. Deploy e aceitação real pendentes.

## Aceitação real do cadastro confirmado — 14/09/2026

O usuário confirmou o fluxo. Consulta independente, somente agregada, encontrou dois resumos, uma correção, um produto cadastrado e duas respostas sem cadastro ativo. O update de criação está completed em uma tentativa; os 70 registros da inbox estão completed, sem pending, processing ou dead_letter. Dados estruturais do produto atendem slots, preço positivo e intervalo 12/24. Não foram expostos IDs, URLs, apelidos ou payloads.

O produto e os resultados de confirmação foram gravados antes do redeploy atual dep-dak2oje743jc73fojcig (af6068d), live desde 17:19 UTC. Entre c2495c7, aprovado no CI 34865934346, e af6068d houve somente alterações documentais. Existe um novo rascunho awaiting_interval iniciado às 17:22 UTC, depois da criação do produto às 16:18 UTC; foi preservado. Não confundir esse novo cadastro com falha de consumo do anterior.

Próximo incremento: `/produtos`, com leitura por proprietário, lista vazia e apresentação dos dados persistidos. Remoção, coleta de preços e alertas continuam pendentes.

## `/produtos` implementado — aguarda CI e deploy

Comando privado admitido com a mesma deduplicação e quota dos demais. Exibe somente produtos do proprietário Telegram, ordenados por slot, com apelido, preço-alvo BRL e intervalo; a resposta informa que coleta e alertas permanecem indisponíveis. Lista vazia orienta `/adicionar`; usuário não registrado recebe orientação `/start`. Não altera rascunhos.

A consulta verifica lease e identidade contra a inbox e grava snapshot em telegram_registration_results na mesma transação. Reprocessamento retorna a resposta original, mesmo após alteração da lista. Usa grants existentes, sem migração. Testes locais e CI devem preceder deploy manual; aceitação real ainda pendente. No BotFather, incluir `/produtos` no menu após validação do deploy.

CI 34876514072 aprovado no commit f9dd144, incluindo PostgreSQL real; 41 testes locais focados passaram. Deploy e aceitação manual de `/produtos` continuam pendentes.

## Aceitação da listagem própria — 14/09/2026

Usuário confirmou funcionamento após deploy manual dep-dak3bv2d0e5s738i1m5g, commit b9be394, live. Consulta agregada independente encontrou uma resposta de lista própria, update completed em uma tentativa e 72 updates completed, sem pending, processing ou dead_letter. Permanecem um produto e um rascunho awaiting_interval expirado; nenhum deles foi alterado pela validação. Sem exposição de IDs ou conteúdo pessoal.

Lista vazia com outro usuário e repetição não apareceram nessa consulta: permanecem pendências de aceitação manual, embora cobertas no CI. Próximo incremento: definir contrato de remoção por proprietário, com confirmação vinculada ao produto selecionado; runtime ainda não possui DELETE em monitored_products.
