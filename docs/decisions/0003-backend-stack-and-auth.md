# ADR 0003 — FastAPI, Azure SQL e identidades

**Status:** aceita  
**Data:** 16/07/2026

## Contexto

A V2 será um bot Telegram multiusuário executado em Azure Container Apps. Cada produto, observação, regra e notificação pertence a um usuário e não pode ser exposto a outro. A API OIDC para extensão e Android foi movida para a V3.

O projeto busca uma API pequena, modular e adequada a processos orientados a I/O, além de uma persistência integrada ao ambiente Azure.

## Decisões

### FastAPI

FastAPI foi escolhido no lugar de Django porque a V2 é centrada em API e não depende inicialmente de painel administrativo, templates ou ORM acoplado ao framework.

O framework deverá permanecer na camada de entrada. Entidades, regras, contratos de repositório e coletores não podem depender de FastAPI.

### Azure SQL Database

Azure SQL Database foi escolhido como persistência cloud. A aplicação usará uma abstração de repositórios e uma camada de mapeamento para evitar SQL espalhado pelos casos de uso.

Direção técnica inicial:

- SQLAlchemy para mapeamento e unidades de trabalho;
- migrações versionadas;
- Microsoft ODBC Driver 18 e `pyodbc` dentro da imagem Linux;
- valores monetários armazenados em tipo decimal fixo ou unidade inteira bem definida;
- identidade gerenciada do Azure Container App para autenticação sem senha no banco;
- credenciais locais separadas apenas para desenvolvimento, quando necessárias.

O SQL Server adiciona uma dependência nativa: o driver ODBC precisa ser instalado e validado na imagem. Isso será tratado no primeiro bloco de persistência.

### Identidade do usuário na V2 Telegram

Na V2, o Telegram será a interface e a fonte da identidade inicial. O bot aceitará somente conversas privadas.

Regras obrigatórias:

- o proprietário será identificado pelo `telegram_user_id`, nunca por `username`;
- o `chat_id` será armazenado separadamente como destino das mensagens;
- o webhook exigirá `X-Telegram-Bot-Api-Secret-Token` válido;
- updates serão deduplicados por `update_id`;
- cada agregado persistido terá proprietário explícito;
- todas as consultas e comandos serão escopados ao usuário Telegram;
- o limite de três produtos será aplicado por usuário;
- testes tentarão acessar, alterar e remover dados pertencentes a outro usuário.

### Autenticação na V3

OIDC/OAuth 2.0 permanece aprovado para a plataforma cloud da V3. Extensão e Android usarão Authorization Code com PKCE, e o usuário interno será identificado por `issuer` + `subject`. A V3 também definirá como vincular uma conta OIDC à identidade Telegram existente.

## Identidades diferentes

O sistema terá duas categorias de identidade:

1. **identidade humana:** na V2 vem do Telegram; na V3 também poderá vir do OIDC;
2. **identidade da carga:** permite que API e job acessem Azure SQL e outros recursos sem senha.

Uma identidade gerenciada representa o serviço e não deve ser confundida com o usuário final.

## V4 local

A edição local não precisará de contas de usuário no escopo inicial. Mesmo assim, uma API HTTP local não pode ficar aberta apenas porque o sistema operacional protege downloads.

A direção da V4 será:

- escutar somente no loopback por padrão;
- usar uma credencial aleatória por instalação ou um canal IPC equivalente;
- restringir CORS e origens permitidas;
- armazenar a credencial usando o mecanismo seguro do sistema operacional;
- não expor portas na rede local sem ação explícita do usuário.

SmartScreen, Gatekeeper e mecanismos semelhantes ajudam a verificar ou restringir software baixado, mas não autorizam requisições feitas depois que o processo está instalado e em execução.

## Consequências

- o schema será multiusuário desde a primeira migração;
- operações de repositório receberão o contexto do proprietário;
- a imagem Docker incluirá dependências ODBC;
- o pipeline deverá testar migrações e consultas contra SQL Server/Azure SQL;
- API e job usarão identidade gerenciada com privilégio mínimo;
- a escolha do provedor OIDC permanece pendente para a V3;
- isolamento por `telegram_user_id` entra desde a primeira migração da V2;
- a vinculação entre Telegram e OIDC deverá preservar a propriedade dos dados existentes.
