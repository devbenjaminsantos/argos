# ADR 0007 — Ofertas multiloja e observações por contexto

Status: aceita como direção; implementação incremental, não concluída.
Data: 18/09/2026.

## Decisão

Preservar o monólito modular, PostgreSQL e hospedagem fracionada do ADR 0006. A sessão de cada loja permanece no navegador; o backend recebe somente ofertas normalizadas. Não contratar grandes nuvens diretamente. Preservar a V1 local e os comandos Telegram durante a evolução.

## Identidade

Introduzir `argos_user_id` UUID por migração aditiva, preenchendo vínculos para os usuários Telegram existentes antes de alterar relações. `telegram_user_id` passa a identidade de canal; `chat_id` é destino. Autorização deriva da identidade autenticada, nunca do owner enviado no payload. Relações privadas terão escopo do proprietário e constraints compostas contra vínculos cruzados.

Cada instalação tem `connector_id` e chave própria. Pareamento exige autenticação, código descartável com expiração e confirmação na conta autorizada. Contexto é usuário + conector + loja + geração; desconexão/troca de conta invalida tarefas antigas. Se não houver evidência confiável da sessão, marcar desconhecida e pedir confirmação; não coletar identidade real da conta da loja.

## Modelo

Separar produto/variante, oferta (loja, anúncio, vendedor e variante), monitoramento do proprietário, observação, tentativa de coleta e futura intenção de busca. Campos desconhecidos são explícitos. Não fazer equivalência automática entre lojas nem compartilhar observações privadas entre usuários.

Observações registram preço inteiro, moeda, disponibilidade, condições de pagamento/cupom/assinatura/quantidade, frete separado, elegibilidade e evidência, horários observado/recebido, validade comercial quando declarada e geração contextual. Prazo de atualização não equivale a validade comercial.

Manter dimensões independentes: origem (browser/API/HTML/provider), contexto (público/sessão/desconhecido), método (DOM/JSON-LD/meta/estrutura) e personalização (identificada/não identificada/desconhecida). Login não prova personalização; assinatura não prova veracidade comercial. Comparar apenas ofertas e condições compatíveis. Alvo inicial exclui frete; condições não confirmadas não devem produzir alerta que prometa preço elegível.

## Execução

Adaptadores por loja declaram capacidades, sem obrigatoriedade de todas as fontes. Coleta pública é independente do conector. Resultado público nunca substitui silenciosamente resultado de sessão. API oficial exige prova de acesso e campos antes de integração; provedor pago desabilitado até aprovação de orçamento.

`/verificar` deverá persistir trabalho e intenção de confirmação antes de responder agendamento. Executor ou conector adquire tentativa com lease e prazo. Resultado com lease substituído é recusado; mesma chave/conteúdo é idempotente, conteúdo divergente é conflito. Observação e intenção de notificar são transacionais, com entregas independentes por canal e política explícita para envio incerto. Falha gera tentativa sem preço. Append-only permite exclusão por privacidade.

## Fronteira da extensão

Começar com ação explícita sobre página aberta. Content scripts não acessam chaves, cookies ou dados de sessão para exportação. Mensagens só contêm campos permitidos. Tarefas não contêm scripts, seletores executáveis ou opções arbitrárias de HTTP. Validar destinos e limites dos dois lados. Assinatura vincula conteúdo, nonce, tarefa, tentativa e geração; revalidar revogação e autorização na transação de aceitação. Disponibilidade do conector não comprova autenticação na loja.

## Evolução e aceite

Acompanhar execução e validação exclusivamente nos checkboxes C1–C9 de [ROADMAP.md](../../ROADMAP.md#evolução-contextual--adr-0007). A lista abaixo registra a sequência da decisão, sem duplicar status.

1. Prova local de página aberta, sem backend, seguida de aceite Chrome real.
2. Identidade aditiva e preservação do Telegram.
3. Modelo contextual e separação de tentativas.
4. Trabalhos e entregas duráveis.
5. Pareamento, revogação e fluxo completo do conector.
6. Comparação e alertas condicionais.
7. Fontes oficiais comprovadas.
8. Busca delimitada por consulta/categoria, orçamento, candidatos, frequência e validade.
9. Amazon Brasil e Shopee Brasil em incrementos independentes.

Aceite inclui migração sem perda, dois proprietários, troca de contexto, replay, revogação concorrente, lease obsoleto, resultado divergente, recuperação após interrupção, conector offline, página/tarefa maliciosa e inspeção de payloads sem segredos. Cada loja exige fixtures e teste real controlado. Não prometer exatamente uma entrega externa sob qualquer falha.

## Estado implementado neste incremento

Botão de observação local na extensão, com preço DOM em BRL, rejeição de preços conflitantes e indicação conservadora de condições desconhecidas. Não persiste, envia dados ou dispara alertas. Identidade de vendedor/variante e autenticação não são inferidas. Esta prova não implementa ainda pareamento, geração de contexto, migração de proprietário, fila de coleta ou novas lojas. O aceite real está em `docs/CONTEXTUAL_CAPTURE_ACCEPTANCE.md`.
