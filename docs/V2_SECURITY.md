# Modelo de ameaças da V2 Telegram

Este documento define as fronteiras de confiança, ameaças e controles obrigatórios do Argos na V2. Ele complementa os controles da extensão descritos em [`SECURITY.md`](SECURITY.md).

## Escopo

A V2 inclui:

- bot do Telegram em conversas privadas;
- webhook público em FastAPI;
- API executada no Render Free e job iniciado por agendador externo;
- coleta de páginas do Mercado Livre;
- persistência PostgreSQL no Supabase Free;
- envio de respostas e alertas pela Telegram Bot API.

OIDC, API pública para extensão, Android, grupos do Telegram e painel administrativo estão fora do escopo.

## Ativos protegidos

- token do bot e segredo do webhook;
- identidade numérica e `chat_id` dos usuários;
- produtos, regras e históricos de cada proprietário;
- integridade das observações de preço;
- estado das conversas e updates processados;
- credenciais de conexão e segredos da carga;
- disponibilidade e quotas dos recursos Render, Supabase e do agendador;
- rede interna, endpoint de metadados e serviços acessíveis pelo coletor.

## Atores e conteúdo não confiável

São tratados como não confiáveis:

- toda requisição recebida da internet, mesmo no caminho correto do webhook;
- corpo, cabeçalhos e identificadores de um update antes da validação;
- nome, `username`, texto e URL enviados pelo usuário;
- HTML, JSON, cabeçalhos, certificados e redirecionamentos retornados pela loja;
- DNS e cada endereço resolvido para um host externo;
- mensagens de erro de Telegram, PostgreSQL, Render, Supabase e do agendador;
- valores vindos de variáveis de ambiente antes da validação de configuração.

O segredo correto do webhook autentica a entrega, mas não transforma o conteúdo do update em dado confiável.

## Fronteiras de confiança

```text
Usuário
  │
  ▼
Telegram ── HTTPS + segredo ──► Webhook público
                                      │
                                      ▼
                              Casos de uso do Argos
                                │              │
                      conexão TLS restrita     │ HTTPS controlado
                                ▼              ▼
                      Supabase/PostgreSQL  Mercado Livre
                                ▲
                                │
                      job agendado externamente

Argos ── HTTPS + token do bot ──► Telegram Bot API
```

Cada seta é uma fronteira: entrada, identidade, autorização, tamanho, tempo e formato precisam ser verificados dos dois lados relevantes.

## Webhook público

### Ameaças

- descoberta e chamada direta do endpoint;
- falsificação ou repetição de updates;
- comparação insegura do segredo;
- payload excessivo, JSON malformado ou tipos inesperados;
- uso de grupos para misturar identidades e destinos;
- execução de scraping durante a requisição;
- vazamento de token, segredo ou stack trace em logs e respostas;
- negação de serviço e aumento involuntário de custo.

### Controles obrigatórios

- aceitar somente `POST /webhooks/telegram` por HTTPS;
- comparar `X-Telegram-Bot-Api-Secret-Token` em tempo constante;
- manter segredo do webhook separado do token do bot;
- rejeitar o corpo antes do parsing quando ultrapassar o limite configurado;
- validar o schema com lista fechada de tipos e campos usados;
- aceitar somente mensagens de texto em chats privados;
- identificar o proprietário por `telegram_user_id`, nunca por `username`;
- reivindicar `update_id` atomicamente antes de executar efeitos;
- persistir ou reservar o trabalho antes de responder com sucesso;
- responder rapidamente e executar coleta fora do ciclo do webhook;
- aplicar rate limit por proprietário e proteção global de capacidade;
- retornar mensagens genéricas e um identificador de correlação não sensível;
- desabilitar documentação interativa da API em produção ou protegê-la explicitamente;
- não habilitar CORS, pois o Telegram não depende de navegador para chamar o webhook.

O caminho do webhook não é considerado segredo. Trocar a URL sem validar o cabeçalho não constitui autenticação.

### Testes mínimos

- segredo ausente, vazio, incorreto e com prefixo/sufixo;
- corpo vazio, inválido, acima do limite e com campos de tipos errados;
- grupo, canal, mensagem editada e update não suportado;
- mesmo `update_id` entregue duas vezes e simultaneamente;
- duas mensagens concorrentes do mesmo proprietário;
- resposta pública sem stack trace ou valor de configuração.

## Identidade e isolamento entre usuários

### Ameaças

- usar `username`, que pode mudar, ser ausente ou pertencer depois a outra pessoa;
- consultar um produto por UUID e verificar o proprietário apenas após carregar os dados;
- confundir `chat_id` com identidade ou autorização;
- revelar que um produto pertence a outro usuário por mensagens diferentes;
- ultrapassar o limite de três produtos por condição de corrida.

### Controles obrigatórios

- chave de propriedade baseada em `telegram_user_id` positivo;
- `chat_id` armazenado e atualizado separadamente como destino;
- `owner_id` explícito em produtos, conversas, observações, tentativas e notificações;
- toda consulta de recurso usa `owner_id` e identificador na mesma operação;
- recurso alheio e recurso inexistente retornam o mesmo erro público;
- limite de produtos e unicidade garantidos dentro da transação;
- testes negativos com pelo menos dois proprietários.

## SSRF e coleta de páginas

### Ameaças

- acesso a loopback, rede privada, link-local ou endpoints de metadados cloud;
- host permitido usado para redirecionar a um destino proibido;
- DNS rebinding entre validação e conexão;
- URLs com credenciais, portas alternativas, caracteres ambíguos ou host semelhante;
- respostas grandes, lentas, comprimidas de forma abusiva ou com redirecionamentos em ciclo;
- envio de cookies, tokens ou cabeçalhos internos para a loja;
- transformação do coletor em proxy genérico.

### Controles obrigatórios

- aceitar somente HTTPS e hosts exatos pertencentes à lista de lojas suportadas;
- normalizar e analisar a URL com biblioteca própria para URLs, nunca com comparação textual parcial;
- rejeitar credenciais embutidas, fragmentos, porta diferente de 443 e host inválido;
- validar o formato de anúncio e o identificador `MLB` antes da rede;
- resolver todos os endereços IPv4 e IPv6 e rejeitar qualquer destino não público;
- bloquear loopback, privado, link-local, multicast, não especificado, reservado e faixas especiais, incluindo endpoints de metadados;
- garantir que a conexão use um endereço previamente validado, evitando uma segunda resolução não controlada;
- seguir redirecionamentos manualmente, com limite baixo, repetindo toda a validação a cada salto;
- impedir redirecionamento para outra loja ou para um identificador incompatível;
- limitar tempo de conexão, tempo total, bytes recebidos e bytes após descompressão;
- usar apenas `GET`, sem corpo, cookies, autenticação do usuário, proxy escolhido pelo usuário ou cabeçalhos arbitrários;
- não expor endpoint que aceite uma URL e devolva o conteúdo remoto;
- registrar somente código de falha e host normalizado, sem HTML da resposta.

Se a biblioteca HTTP não permitir fixar de maneira segura o endereço validado preservando TLS/SNI e host, a coleta cloud permanece bloqueada até existir um adaptador ou controle de saída adequado.

### Testes mínimos

- `localhost`, IPv4 e IPv6 literais, formatos numéricos alternativos e nomes com ponto final;
- endereços privados, loopback, link-local e de metadados;
- credenciais na URL e portas alternativas;
- subdomínio malicioso semelhante ao host permitido;
- DNS com respostas públicas e privadas misturadas;
- redirecionamento permitido para destino proibido;
- cadeia longa, ciclo, timeout, resposta acima do limite e expansão após compressão.

## Conteúdo remoto e injeção

### Ameaças

- scripts ou marcação maliciosa presentes no anúncio;
- JSON estruturado adulterado;
- SQL injection por apelido, URL ou conteúdo da loja;
- injeção de HTML/Markdown em mensagens do Telegram;
- conteúdo remoto inserido em logs de forma a forjar registros.

### Controles obrigatórios

- nunca executar JavaScript recebido da loja no coletor padrão;
- interpretar JSON com parser, nunca `eval`;
- tratar todo texto extraído como conteúdo simples;
- usar queries parametrizadas e mapeamento explícito;
- escapar corretamente o modo de formatação do Telegram ou enviar texto sem modo de parse;
- normalizar quebras e remover caracteres de controle antes de logs;
- aplicar limites de tamanho a título, apelido, URL e detalhes persistidos;
- nunca converter falha de parser em preço zero.

## Supabase PostgreSQL

### Ameaças

- credencial de banco dentro da imagem ou do repositório;
- identidade de runtime com permissão de administração ou migração;
- consulta sem escopo do proprietário;
- conexão sem criptografia ou validação adequada do certificado;
- dados sensíveis em logs, backups ou ambientes de teste;
- concorrência causando alertas, updates ou produtos duplicados.

### Controles obrigatórios

- connection string existe apenas nos secrets do Render e do agendador;
- migrações usam uma credencial separada da credencial de runtime, quando o provedor permitir;
- privilégios mínimos por credencial e ambiente;
- conexão PostgreSQL exige TLS e validação de certificado;
- chaves administrativas do Supabase nunca são expostas ao cliente ou usadas como identidade humana;
- acesso de rede limitado aos recursos necessários, conforme capacidade e custo do ambiente;
- queries parametrizadas e repositórios sempre escopados ao proprietário;
- constraints e índices únicos para integridade e deduplicação;
- transações curtas, controle de versão e leases para trabalho concorrente;
- ambientes de desenvolvimento e produção separados;
- política de backup, retenção e restauração validada antes do piloto real.

Segredos locais eventualmente usados no desenvolvimento ficam em arquivo ignorado ou secret store, nunca em configuração versionada.

## Telegram Bot API e notificações

### Ameaças

- exposição do token do bot;
- envio ao `chat_id` errado;
- notificação duplicada por retentativa ou concorrência;
- indisponibilidade e rate limit do provedor;
- resposta externa completa registrada em log.

### Controles obrigatórios

- token mantido somente como secret e nunca incluído em URL registrada;
- destino obtido do usuário proprietário persistido, não do conteúdo do produto;
- reserva atômica da chave de deduplicação antes do envio;
- timeout e retentativa limitada apenas para falhas transitórias;
- tratamento explícito de bloqueio do bot e destino inválido;
- logs contêm código interno, correlação e status, sem token ou corpo completo;
- rotação do token e do segredo do webhook documentada e testável.

## Disponibilidade, abuso e custo

### Ameaças

- muitas mensagens, verificações manuais ou URLs lentas;
- job concorrente com ele mesmo;
- retentativas sem limite;
- crescimento descontrolado de logs, histórico ou réplicas;
- cold start fazendo o Telegram repetir updates.

### Controles obrigatórios

- limite de três produtos por proprietário;
- rate limit por usuário, host e operação;
- uma coleta ativa por produto e concorrência global configurável;
- leases com expiração para recuperação após falha;
- retentativa com espera progressiva, jitter e número máximo de tentativas;
- limites de réplicas, CPU, memória, execução de jobs e retenção de logs;
- quotas e restrições do plano Free verificadas antes do agendamento recorrente;
- métricas para rejeições, duração, falhas, deduplicação e consumo;
- procedimento para desativar jobs e webhook sem perder dados.

## Contêiner e cadeia de dependências

- executar como usuário sem privilégios;
- manter imagem mínima e versões de dependências fixadas;
- separar dependências de desenvolvimento das de runtime;
- não incluir `.env`, repositório Git, testes ou tokens na imagem final;
- verificar vulnerabilidades conhecidas antes do deploy;
- usar processo de produção, nunca servidor com reload;
- aplicar atualizações de segurança por imagem reproduzível e rollback conhecido.

## Logs e privacidade

Podem ser registrados:

- identificador de correlação;
- código interno do evento ou falha;
- duração, quantidade e status operacional;
- identificadores internos pseudonimizados quando necessários.

Não podem ser registrados:

- token do bot, segredo do webhook ou cabeçalho de autorização;
- connection string, token de identidade ou conteúdo de `.env`;
- corpo completo de updates;
- HTML ou resposta completa da loja;
- texto livre do usuário;
- query contendo valores sensíveis.

O `telegram_user_id` e o `chat_id` são dados pessoais e não devem ser usados como identificadores públicos de correlação.

## Riscos residuais aceitos no MVP

- o segredo do webhook é compartilhado entre Telegram e uma implantação do bot;
- a identidade humana depende da integridade da plataforma Telegram;
- o marketplace pode retornar preço de variante, Pix ou promoção diferente da intenção do usuário;
- a loja pode bloquear automação ou mudar o HTML sem aviso;
- escala mínima zero pode introduzir cold start e novas entregas do mesmo update;
- a V2 não oferece exclusão e portabilidade completas por interface, que deverão existir antes de uso público amplo.

Esses riscos exigem deduplicação, transparência sobre o preço observado, testes com páginas reais e operação inicial limitada a um piloto.

## Portões de segurança por etapa

- **V2.2:** configuração validada, imagem sem segredos, processo não privilegiado e `/health` sem detalhes internos;
- **V2.3:** plataforma Free, proteção de custo e contingência documentadas;
- **V2.4:** token e segredo separados, armazenados como secrets e ausentes dos logs;
- **V2.5:** autenticação do webhook, schema fechado, limite de corpo e deduplicação testados;
- **V2.7:** TLS, credenciais mínimas, migrações separadas e isolamento entre usuários testados;
- **V2.10:** suíte negativa de SSRF aprovada antes de qualquer URL gerar tráfego;
- **V2.13:** backup, restauração, rotação, rollback e desligamento operacional exercitados.
