# ADR 0002 — Azure como plataforma da V2

**Status:** aceita  
**Data:** 16/07/2026

## Contexto

O Argos precisa executar coletas mesmo quando o navegador e o computador do usuário estiverem desligados. O projeto possui acesso a uma conta Azure com free tier e busca minimizar custos durante o piloto.

## Decisão

A V2 será implantada na Azure com a seguinte direção:

- Azure Container Apps para a API;
- escala mínima de zero no ambiente de desenvolvimento, quando compatível com o comportamento esperado;
- Azure Container Apps Jobs para coletas programadas;
- Azure SQL Database para persistência;
- uma única imagem e um único monólito modular, com comandos separados para API e job;
- desenvolvimento e testes executados localmente antes do deploy;
- orçamento, alertas e limites de escala configurados antes de ativar coletas recorrentes.

```text
Extensão ──→ Azure Container App ──→ Azure SQL Database
                                          ↑
Cron ──→ Azure Container Apps Job ────────┘
                    │
                    └──→ lojas e notificações
```

## Por que não usar uma VM na V2

Uma Azure Virtual Machine permitiria executar Docker de maneira semelhante a uma instância EC2. Entretanto, ela também exigiria manutenção do sistema operacional, proteção de SSH, proxy, certificados, atualizações, reinício de processos e cuidados adicionais com disco e backup.

Container Apps e Jobs atendem melhor ao padrão de carga do Argos: uma API pequena e coletas periódicas que podem encerrar depois de concluídas.

Uma VM poderá ser reavaliada se o coletor passar a exigir navegador headless persistente, sessões longas ou controle de rede indisponível no plano gerenciado.

## Limite da decisão

Esta decisão escolhe a plataforma cloud da V2. Ela não transforma o ambiente local de desenvolvimento em uma edição distribuível.

A edição local/autohospedada foi movida para a V3 porque exige decisões próprias sobre:

- instalação multiplataforma;
- execução como serviço em segundo plano;
- banco empacotado;
- portas, firewall e certificados;
- armazenamento local de segredos;
- atualização, backup, diagnóstico e desinstalação.

## Custos e validade

O free tier será usado como ambiente de piloto, não como garantia de custo zero permanente. Antes do deploy recorrente, o projeto deverá:

- confirmar elegibilidade e região de cada recurso;
- configurar orçamento e alertas;
- limitar réplicas, CPU, memória, logs e retenção;
- revisar custos de Azure SQL, Container Registry e tráfego;
- documentar o comportamento após o fim das franquias promocionais.

## Consequências

- Azure SQL Database passa a ser a persistência da V2;
- o job deve ser idempotente e protegido contra concorrência;
- o domínio não pode depender de SDKs da Azure;
- API e job devem executar com a mesma imagem;
- configuração e segredos devem entrar por variáveis ou referências seguras;
- infraestrutura Azure deve ser criada em blocos pequenos e revisáveis.
