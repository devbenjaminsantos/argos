# ADR 0003 — FastAPI, Azure SQL e autenticação

**Status:** aceita  
**Data:** 16/07/2026

## Contexto

A V2 será uma API cloud multiusuário executada em Azure Container Apps. Cada produto, observação, regra e notificação pertence a um usuário e não pode ser exposto a outro.

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

### Autenticação por usuário

A API cloud exigirá autenticação federada compatível com OIDC/OAuth 2.0. O provedor de identidade ainda será escolhido.

Regras obrigatórias:

- clientes públicos, como extensão e Android, usarão Authorization Code com PKCE;
- a aplicação não armazenará senha do usuário;
- o usuário interno será identificado pela combinação estável `issuer` + `subject`, nunca apenas pelo e-mail;
- cada agregado persistido terá proprietário explícito;
- todas as consultas e comandos serão escopados ao usuário autenticado;
- o limite de três produtos será aplicado por usuário;
- autenticação na borda não substituirá autorização dentro da aplicação;
- testes tentarão acessar, alterar e remover dados pertencentes a outro usuário.

Azure Container Apps possui autenticação integrada com Microsoft Entra ID, Google e outros provedores OIDC. Essa opção será comparada com validação de tokens dentro do FastAPI antes da implementação.

## Identidades diferentes

O sistema terá duas categorias de identidade:

1. **identidade humana:** autentica o usuário da extensão ou do aplicativo;
2. **identidade da carga:** permite que API e job acessem Azure SQL e outros recursos sem senha.

Uma identidade gerenciada representa o serviço e não deve ser confundida com o usuário final.

## V3 local

A edição local não precisará de contas de usuário no escopo inicial. Mesmo assim, uma API HTTP local não pode ficar aberta apenas porque o sistema operacional protege downloads.

A direção da V3 será:

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
- a escolha do provedor OIDC permanece uma decisão pendente;
- autenticação e isolamento de dados entram antes da integração cloud da extensão.

