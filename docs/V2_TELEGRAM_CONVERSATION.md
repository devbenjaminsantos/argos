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

O bot não solicita senha, código de autenticação, dados de pagamento ou token. Respostas nunca incluem stack trace, segredo, query SQL, HTML coletado ou detalhes internos da Azure.

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
- o tamanho máximo inicial é de 80 caracteres;
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
