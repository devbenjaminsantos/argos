# Argos — Bot Fiscal de Preços

O **Argos** é um bot de monitoramento de preços que acompanha produtos em lojas on-line e avisa o usuário quando identifica uma queda relevante ou quando o valor desejado é atingido.

O foco inicial do projeto são anúncios do **Mercado Livre** e da **Shopee**.

## Objetivo

Facilitar o acompanhamento de preços sem exigir que o usuário visite repetidamente as páginas dos produtos. O sistema mantém um histórico dos valores encontrados, aplica regras configuráveis e envia notificações no momento adequado.

## MVP

O fluxo de cadastro de um produto será:

1. Informar a URL do produto.
2. Definir um nome ou apelido para identificá-lo.
3. Informar o preço-alvo.
4. Escolher o canal de notificação.

Inicialmente, cada usuário poderá monitorar até **3 produtos**.

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

### Organização do projeto

```text
argos/
├── api/
│   ├── routes/
│   └── dependencies/
├── domain/
│   ├── products/
│   ├── prices/
│   └── notifications/
├── application/
│   ├── services/
│   └── use_cases/
├── infrastructure/
│   ├── database/
│   ├── scrapers/
│   ├── scheduler/
│   └── telegram/
├── models/
├── repositories/
├── tests/
└── main.py
```

### Responsabilidades das camadas

- **`api/`**: expõe as rotas HTTP e reúne as dependências necessárias para executar os casos de uso.
- **`domain/`**: contém as regras centrais do negócio, organizadas pelos domínios de produtos, preços e notificações. Essa camada não deve depender de frameworks, banco de dados ou serviços externos.
- **`application/`**: coordena os fluxos da aplicação. Seus serviços e casos de uso combinam as regras do domínio para cadastrar produtos, verificar preços, registrar o histórico e disparar alertas.
- **`infrastructure/`**: concentra implementações ligadas ao mundo externo, como persistência, scrapers das lojas, tarefas agendadas e integração com o Telegram.
- **`models/`**: reúne os modelos usados para persistência, validação ou transferência de dados, mantendo clara a diferença entre esses formatos e as entidades do domínio.
- **`repositories/`**: define os contratos de acesso aos dados. As implementações concretas ficam na infraestrutura, permitindo trocar SQLite por PostgreSQL sem alterar as regras de negócio.
- **`tests/`**: contém testes unitários, de integração e de ponta a ponta.
- **`main.py`**: é o ponto de entrada e de composição da aplicação.

### Direção das dependências

```text
API ──→ Aplicação ──→ Domínio
          ↑
Infraestrutura implementa os contratos usados pela aplicação
```

O domínio permanece no centro e não conhece detalhes de HTTP, banco de dados, scraping, agendamento ou Telegram. A infraestrutura pode ser substituída sem reescrever as regras principais. Por exemplo, cada loja terá seu próprio adaptador em `infrastructure/scrapers/`, mas todos deverão entregar os dados em um formato esperado pela aplicação.

Essa separação simplifica o desenvolvimento e a implantação inicial, além de preparar alguns caminhos naturais de evolução:

- o agendador e os scrapers podem se tornar workers independentes;
- notificações podem ser movidas para um serviço próprio;
- novos marketplaces podem ser adicionados por meio de adaptadores;
- SQLite pode ser substituído por PostgreSQL;
- API, extensão e aplicativo Android podem reutilizar os mesmos casos de uso por meio do back-end.

## Stack tecnológica

### MVP — Extensão para Chrome

- **TypeScript**
- **IndexedDB** para armazenamento local

### Back-end local ou em nuvem

- **Python**
- **FastAPI** ou **Django**
- **SQLite** para ambientes locais e protótipos
- **PostgreSQL** para produção e maior escala

### Aplicativo Android

- **Kotlin**
- **Jetpack Compose**

## Funcionalidades futuras

- gráfico do histórico de preços;
- exportação do histórico em PDF e CSV;
- exibição do menor preço já encontrado;
- sugestão de um bom momento para compra;
- cálculo da redução em reais e em percentual;
- comparação com outros anúncios do mesmo produto;
- aumento do limite de produtos monitorados;
- suporte a outras lojas e marketplaces.

## Roadmap sugerido

### Fase 1 — MVP

- cadastrar, editar e remover produtos;
- monitorar até 3 URLs;
- definir preço-alvo e intervalo de verificação;
- coletar e armazenar o histórico de preços;
- detectar quedas relevantes;
- evitar notificações duplicadas;
- enviar notificações pelo canal escolhido.

### Fase 2 — Histórico e inteligência

- apresentar gráficos de variação;
- destacar o menor preço em 30 e 90 dias;
- calcular a queda absoluta e percentual;
- exportar dados em PDF e CSV;
- sugerir o melhor momento para compra.

### Fase 3 — Expansão

- disponibilizar um back-end local ou em nuvem;
- sincronizar dados entre dispositivos;
- lançar o aplicativo Android;
- comparar anúncios equivalentes;
- adicionar novas lojas e canais de notificação.

## Observações

A coleta de preços deve considerar mudanças no HTML das lojas, páginas que exigem autenticação, variações de produto, promoções temporárias, frete e mecanismos de proteção contra automação. A implementação também deverá respeitar os termos de uso e as políticas de acesso de cada marketplace.

## Status

Projeto em fase de planejamento e definição do MVP.
