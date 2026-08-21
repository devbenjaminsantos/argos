# Contratos da V2 Telegram

Este documento define as portas internas do monólito modular da V2. Ele descreve responsabilidades e dados trocados, sem escolher FastAPI, SQLAlchemy, PostgreSQL ou a biblioteca do Telegram como dependências do domínio.

## Princípios

- casos de uso dependem de contratos, não de implementações de infraestrutura;
- `telegram_user_id` identifica o proprietário e deve estar presente em toda operação que acessa dados do usuário;
- `chat_id` é apenas o destino de mensagens e não concede acesso a produtos;
- valores monetários usam centavos inteiros e código de moeda explícito;
- datas e horas usam UTC e valores conscientes de fuso;
- ausência de preço e falha de coleta são resultados distintos de um preço igual a zero;
- deduplicação e aquisição de trabalho precisam ser atômicas no banco;
- contratos não expõem modelos de FastAPI, Telegram, SQLAlchemy ou respostas HTTP.

## Tipos compartilhados

Os nomes abaixo expressam o formato lógico dos dados. A representação em Python será criada na V2.2.

### Identidade do proprietário

```text
OwnerId
└── telegram_user_id: int64 positivo
```

O `username` pode ser armazenado apenas como dado de apresentação. Ele nunca participa de chaves, filtros de propriedade ou autorização.

### Produto monitorado

```text
MonitoredProduct
├── id: UUID
├── owner_id: OwnerId
├── chat_id: int64
├── store: "mercado_livre"
├── canonical_url: HTTPS URL validada
├── external_id: identificador MLB
├── alias: string
├── target_price_minor: int64 positivo
├── relevant_drop_basis_points: int entre 1 e 10000
├── check_interval_hours: 12 | 24
├── next_check_at: datetime UTC
├── active: bool
└── version: int
```

Percentuais usam pontos-base: `1000` representa 10%. A URL só pode chegar a este modelo depois da validação de formato; a ativação para coleta cloud ainda depende da validação contra SSRF.

### Resultado da coleta

```text
CollectedOffer
├── store: "mercado_livre"
├── external_id: identificador MLB confirmado
├── title: string
├── canonical_url: HTTPS URL final validada
├── price_minor: int64 positivo
├── currency: "BRL"
└── observed_at: datetime UTC
```

Falhas são classificadas separadamente:

- `UnsupportedUrl`: loja ou formato não suportado;
- `UnsafeDestination`: destino bloqueado pela política contra SSRF;
- `ProductNotFound`: anúncio removido ou inexistente;
- `PriceNotFound`: página recebida, mas sem preço confiável;
- `AccessBlocked`: bloqueio ou desafio imposto pela loja;
- `TemporaryCollectionFailure`: timeout, rede ou resposta temporariamente inválida.

Somente `CollectedOffer` gera uma observação de preço válida.

## Repositórios

As implementações devem garantir o escopo pelo proprietário dentro da própria consulta. Buscar um produto apenas pelo seu UUID e filtrar o proprietário depois não é permitido.

### `UserRepository`

- `upsert_telegram_user(owner_id, chat_id, display_data) -> User`
- `get_by_owner(owner_id) -> User | None`
- `update_chat_destination(owner_id, chat_id) -> User`

### `ProductRepository`

- `count_active(owner_id) -> int`
- `add(owner_id, product) -> MonitoredProduct`
- `get(owner_id, product_id) -> MonitoredProduct | None`
- `list(owner_id, active_only=True) -> list[MonitoredProduct]`
- `update(owner_id, product, expected_version) -> MonitoredProduct`
- `deactivate(owner_id, product_id) -> bool`
- `claim_due(now, limit, lease_until) -> list[MonitoredProduct]`

`add` deve aplicar no banco o limite de três produtos ativos por proprietário. `claim_due` deve impedir que API e job processem o mesmo produto simultaneamente.

### `PriceObservationRepository`

- `add(owner_id, product_id, observation) -> PriceObservation`
- `latest_valid(owner_id, product_id) -> PriceObservation | None`
- `lowest_valid_since(owner_id, product_id, since) -> PriceObservation | None`
- `list_recent(owner_id, product_id, limit) -> list[PriceObservation]`

Observações inválidas não são criadas. Falhas de coleta pertencem ao registro de tentativas, não ao histórico de preços.

### `CollectionAttemptRepository`

- `record_started(owner_id, product_id, started_at) -> CollectionAttempt`
- `record_succeeded(attempt_id, observed_at) -> None`
- `record_failed(attempt_id, failure_code, safe_detail) -> None`

`safe_detail` não pode conter página HTML, tokens, cabeçalhos, dados de conexão ou respostas completas da loja.

### `ProcessedUpdateRepository`

- `try_claim(update_id, received_at) -> bool`
- `mark_completed(update_id, completed_at) -> None`
- `mark_failed(update_id, failure_code) -> None`

`try_claim` é atômico. Ele retorna `false` quando o `update_id` já existe, permitindo responder ao Telegram sem repetir a ação.

### `ConversationRepository`

- `get(owner_id) -> ConversationState | None`
- `save(owner_id, state, expected_version) -> ConversationState`
- `clear(owner_id) -> None`

O estado é persistido para sobreviver a reinícios e usa versão para impedir duas mensagens concorrentes de avançarem a conversa de maneira incompatível.

### `NotificationDeliveryRepository`

- `try_reserve(deduplication_key, owner_id, product_id, reason, price_minor) -> Delivery | None`
- `mark_sent(delivery_id, provider_message_id, sent_at) -> None`
- `mark_failed(delivery_id, failure_code, retry_after) -> None`

A chave de deduplicação deve representar produto, regra disparada e preço observado. A reserva acontece antes do envio para evitar notificações duplicadas por jobs concorrentes.

## Coletor de loja

### `StoreCollector`

- `store -> StoreId`
- `supports(url) -> bool`
- `collect(source, policy) -> CollectedOffer`

O coletor recebe somente uma origem já validada sintaticamente. A infraestrutura HTTP aplica a política de rede antes da conexão e novamente em cada redirecionamento.

```text
CollectionPolicy
├── allowed_hosts
├── maximum_redirects
├── connect_timeout
├── total_timeout
└── maximum_response_bytes
```

O contrato não permite ao usuário fornecer cabeçalhos, método HTTP, corpo, proxy ou opções de rede.

## Notificador

### `Notifier`

- `send(destination, message) -> NotificationReceipt`

```text
NotificationDestination
├── channel: "telegram"
└── chat_id: int64

NotificationMessage
├── kind: resposta | alerta_de_preco | erro_de_coleta
├── text: string limitada
└── correlation_id: string sem dado sensível

NotificationReceipt
├── provider_message_id: string
└── accepted_at: datetime UTC
```

O adaptador Telegram é responsável por escapar ou desativar modos de formatação, limitar o tamanho da mensagem, aplicar timeout e traduzir erros externos para códigos internos seguros.

## Unidade de trabalho

Casos de uso que alteram mais de um repositório usam uma unidade de trabalho:

- `commit() -> None`
- `rollback() -> None`

Transações obrigatórias incluem:

- criar um produto e aplicar o limite por usuário;
- reivindicar e concluir um update do Telegram;
- registrar preço, avaliar regras e reservar uma notificação;
- reivindicar produtos vencidos para execução pelo job.

Chamadas de rede não permanecem dentro de uma transação aberta. Primeiro o sistema reserva o trabalho; depois coleta ou envia; por fim persiste o resultado em uma transação curta.

## Direção das dependências

```text
FastAPI / Job / Telegram
          │
          ▼
     Casos de uso
          │
          ▼
Domínio + contratos (portas)
          ▲
          │
PostgreSQL / HTTP / Bot API
      (adaptadores)
```

## Decisões adiadas

Ficam para as etapas de implementação:

- classes e assinaturas Python definitivas;
- ORM, schemas e migrações;
- biblioteca cliente do Telegram;
- biblioteca HTTP do coletor;
- política de retentativas e tempos exatos;
- formato final das chaves de deduplicação e leases.

Essas escolhas não podem enfraquecer o isolamento por proprietário, a atomicidade ou a política de rede estabelecidos aqui.
