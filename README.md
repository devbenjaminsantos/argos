# Argos — Bot Fiscal de Preços

O **Argos** é um bot de monitoramento de preços que acompanha produtos em lojas on-line e avisa o usuário quando identifica uma queda relevante ou quando o valor desejado é atingido.

O foco inicial do projeto são anúncios do **Mercado Livre** e da **Shopee**.

## Versões do projeto

- **V1 — Chrome (concluída):** extensão local dedicada inicialmente ao Mercado Livre.
- **V2 — MVP Telegram:** cadastro, monitoramento e alertas pelo Telegram, executados na Azure.
- **V3 — Plataforma cloud:** autenticação OIDC, API de clientes e integração cloud da extensão.
- **V4 — Back-end local:** edição autohospedada e distribuível para execução na máquina do usuário.
- **V5 — Android:** aplicativo móvel integrado ao back-end cloud.

O progresso detalhado e a próxima entrega estão registrados em [`ROADMAP.md`](ROADMAP.md).

## Objetivo

Facilitar o acompanhamento de preços sem exigir que o usuário visite repetidamente as páginas dos produtos. O sistema mantém um histórico dos valores encontrados, aplica regras configuráveis e envia notificações no momento adequado.

## MVP

O fluxo de cadastro na V1 será:

1. Abrir a página do produto no Mercado Livre.
2. Abrir a extensão para extrair a URL, o título e o preço atual.
3. Definir um nome ou apelido para identificá-lo.
4. Informar o preço-alvo.
5. Definir a queda percentual relevante e o intervalo de verificação.
6. Receber notificações locais pelo Chrome.

Inicialmente, cada usuário poderá monitorar até **3 produtos**.

### Escopo da V1 Chrome

- Mercado Livre como primeira loja suportada;
- coleta inicial diretamente da página aberta pelo usuário;
- coleta periódica em segundo plano enquanto o Chrome estiver disponível;
- intervalos configuráveis de 12 ou 24 horas;
- histórico local no IndexedDB;
- alerta ao atingir o preço-alvo ou uma queda percentual relevante;
- deduplicação de alertas equivalentes;
- nenhum servidor, endpoint remoto, conta ou segredo armazenado na extensão.

## Como funciona

```text
URL do produto
      ↓
Visita periódica à página
      ↓
Extração do preço atual
      ↓
Registro do valor, data e hora
      ↓
Comparação com o histórico e o preço-alvo
      ↓
Notificação, caso alguma regra seja atendida
```

Em cada verificação, o sistema:

- visita a página do produto;
- extrai o preço atual;
- registra o valor com data e hora;
- compara o preço com o valor anterior e com o preço-alvo;
- verifica se o preço é o menor dos últimos 30 ou 90 dias;
- envia uma notificação quando identifica uma queda relevante;
- impede o envio de notificações duplicadas.

## Regras de monitoramento

O usuário poderá configurar regras como:

- período entre verificações, por exemplo, a cada 12 ou 24 horas;
- queda mínima em percentual, por exemplo, 10%;
- queda mínima em valor absoluto, por exemplo, R$ 120,00;
- notificação ao atingir ou ficar abaixo do preço-alvo;
- notificação ao alcançar o menor preço dos últimos 30 ou 90 dias;
- controle de notificações duplicadas;
- limite inicial de 3 produtos monitorados.

Exemplo de notificação:

> O preço era R$ 800,00 e agora é R$ 680,00. Houve uma queda de R$ 120,00 (15%).

## Arquitetura

O Argos será inicialmente desenvolvido como um **monólito modular**. Os domínios de monitoramento, adaptadores de lojas, histórico de preços e notificações permanecerão desacoplados internamente. Assim, partes do sistema poderão ser extraídas no futuro para workers ou microsserviços, se necessário, sem introduzir a complexidade de uma arquitetura distribuída no MVP.

### Organização da V1 Chrome

```text
argos/
├── src/
│   ├── application/
│   ├── background/
│   ├── content/
│   ├── domain/
│   ├── infrastructure/
│   │   └── database/
│   ├── offscreen/
│   ├── popup/
│   ├── security/
│   ├── shared/
│   └── stores/
│       └── mercado-livre/
├── tests/
├── scripts/
└── package.json
```

### Responsabilidades das camadas

- **`domain/`**: contém produtos, observações de preço e regras de alerta, sem depender das APIs do Chrome.
- **`application/`**: valida entradas e coordena os casos de uso de cadastro e monitoramento.
- **`stores/`**: contém um adaptador por loja. A V1 possui apenas o adaptador `mercado-livre/`.
- **`infrastructure/`**: implementa a persistência local com IndexedDB.
- **`background/`**: recebe operações autorizadas, executa coletas agendadas e envia notificações.
- **`content/`**: extrai dados da página que o usuário abriu.
- **`offscreen/`**: interpreta o HTML estático obtido durante as verificações agendadas, pois o service worker não possui DOM.
- **`popup/`**: apresenta a aba e os controles específicos de cada loja.
- **`security/`**: concentra validação e normalização das URLs permitidas.
- **`shared/`**: define o protocolo de mensagens entre os contextos da extensão.
- **`tests/`**: contém testes unitários, de integração e de ponta a ponta.

### Direção das dependências

```text
Popup/Background ──→ Aplicação ──→ Domínio
                           ↑
   IndexedDB e adaptadores implementam as integrações
```

O domínio permanece no centro e não conhece IndexedDB, páginas HTML ou APIs do Chrome. Cada loja possui seu próprio adaptador, mas todas devem entregar um produto extraído no contrato esperado pela aplicação.

Essa separação simplifica o desenvolvimento e a implantação inicial, além de preparar alguns caminhos naturais de evolução:

- o agendador e os coletores podem se tornar workers independentes;
- notificações podem ser movidas para um serviço próprio;
- novos marketplaces podem ser adicionados por meio de adaptadores;
- Azure SQL Database atende à persistência do back-end cloud sem alterar o domínio;
- API, extensão e aplicativo Android podem reutilizar os mesmos contratos por meio do back-end.

## Stack tecnológica

### MVP — Extensão para Chrome

- **TypeScript**
- **IndexedDB** para armazenamento local
- **Manifest V3**
- **esbuild** para empacotamento
- **Vitest** para testes

### V2 — MVP Telegram na Azure

- **Python**
- **FastAPI**
- **Azure SQL Database**
- **SQLAlchemy** e ferramenta de migração — implementação ainda pendente
- **Microsoft ODBC Driver 18 for SQL Server**
- **Docker**
- **Azure Container Apps**
- **Azure Container Apps Jobs**
- identidade do usuário baseada no `telegram_user_id`
- Telegram Bot API com webhook autenticado
- identidade gerenciada para acesso da aplicação ao banco sem senha

### V3 — Plataforma cloud e extensão

- autenticação federada **OIDC/OAuth 2.0**;
- integração da extensão Chrome com a API;
- vinculação da identidade Telegram à conta cloud.

### V4 — Back-end local/autohospedado

- mesma base Python e arquitetura modular da V2;
- banco local ainda a decidir;
- instalação, atualização e serviço em segundo plano multiplataforma.

### V5 — Aplicativo Android

- **Kotlin**
- **Jetpack Compose**

## Executando a V1 Chrome

Requisitos: Node.js e npm.

```bash
npm install
npm run check
npm test
npm run build
```

Depois do build:

1. Acesse `chrome://extensions`.
2. Ative o **Modo do desenvolvedor**.
3. Selecione **Carregar sem compactação**.
4. Escolha a pasta `dist/` gerada pelo projeto.
5. Abra ou recarregue uma página de produto do Mercado Livre.
6. Clique no ícone do Argos.

## Segurança da extensão

A V1 não possui back-end nem expõe endpoints. Entre os controles adotados estão:

- permissão de host limitada a `https://*.mercadolivre.com.br/*`;
- aceitação somente de páginas HTTPS de produto, sem credenciais ou portas alternativas;
- remoção de parâmetros comuns de rastreamento;
- validação das mensagens e de sua origem;
- bloqueio de operações de banco solicitadas por content scripts;
- limite de tamanho para páginas coletadas;
- `credentials: "omit"` nas coletas em segundo plano;
- renderização da interface com `textContent`, sem inserir HTML coletado;
- nenhum código remoto, token ou chave de API no pacote.

O modelo de ameaças e as limitações conhecidas estão documentados em [`docs/SECURITY.md`](docs/SECURITY.md).

## Funcionalidades futuras

- gráfico do histórico de preços;
- exportação do histórico em PDF e CSV;
- exibição do menor preço já encontrado;
- sugestão de um bom momento para compra;
- cálculo da redução em reais e em percentual;
- comparação com outros anúncios do mesmo produto;
- aumento do limite de produtos monitorados;
- suporte a outras lojas e marketplaces.

## Observações

A coleta de preços deve considerar mudanças no HTML das lojas, páginas que exigem autenticação, variações de produto, promoções temporárias, frete e mecanismos de proteção contra automação. A implementação também deverá respeitar os termos de uso e as políticas de acesso de cada marketplace.

## Status

V1 Chrome concluída, com suporte inicial ao Mercado Livre. Melhorias e regressões do adaptador continuam sendo tratadas conforme surgirem novos formatos de página.

> **Teste de aceitação pendente:** a extensão ainda será testada manualmente no Chrome para Windows. O desenvolvimento atual está sendo realizado em um ambiente com Safari, que não executa diretamente o pacote Manifest V3 preparado para o Chrome.
