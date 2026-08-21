# Fundação Azure da V2

Este documento registra a preparação operacional da assinatura Azure usada pelo Argos. Nenhum token, identificador de usuário ou credencial deve ser salvo no repositório.

## Azure CLI no macOS Monterey

A Azure CLI atual via Homebrew exige uma versão mais recente do macOS. Neste ambiente, a CLI é executada pela imagem oficial da Microsoft, com versão fixada:

```text
mcr.microsoft.com/azure-cli:2.88.0-azurelinux3.0
```

A sessão autenticada fica no volume local `argos-azure-cli-config`, fora do repositório. O login usa código de dispositivo e MFA:

```bash
docker run --rm --interactive --tty \
  --mount source=argos-azure-cli-config,target=/root/.azure \
  mcr.microsoft.com/azure-cli:2.88.0-azurelinux3.0 \
  az login --use-device-code
```

Não montar a pasta do projeto em `/root/.azure` e não copiar o conteúdo desse volume para arquivos versionados.

## Recursos e nomenclatura

Estado validado em 21/08/2026:

- assinatura ativa e inicialmente sem recursos;
- oferta identificada pela API como Pay-As-You-Go, com `spendingLimit` desativado;
- custo acumulado no mês: `0,00 BRL` no momento da consulta;
- provedor `Microsoft.App` registrado;
- provedor `Microsoft.Web` registrado;
- extensão `containerapp` 1.3.0b4 instalada no volume local da CLI;
- resource group `rg-argos-dev-brazilsouth` criado em `brazilsouth`;
- tags: `project=argos`, `environment=dev` e `managed-by=azure-cli`.

O registro do provedor e o resource group não executam carga do Argos. Container Apps Environment, aplicação, registry e banco ainda não foram criados.

### Avaliação do App Service Free F1

O App Service Linux F1 tem preço publicado de zero e cotas rígidas. Quando uma aplicação excede CPU ou banda no tier Free, ela é interrompida até a renovação da cota, em vez de migrar automaticamente para um tier pago.

Foi tentada a criação de `asp-argos-api-dev-brazilsouth` no SKU F1. A Azure recusou a operação antes do provisionamento porque a assinatura possui limite de zero instâncias para App Service. A consulta confirmou `F1 VMs: 0/0` e `Total Regional VMs: 0/0` em Brazil South; regiões alternativas consultadas também apresentaram limite total zero.

Consequências:

- nenhum App Service Plan ou Web App foi criado;
- não solicitar aumento de quota automaticamente;
- não substituir F1 por um SKU pago;
- continuar a API localmente até o usuário avaliar a quota no portal.

## Direção de custo próximo de zero

A assinatura não possui um bloqueio automático de cobrança. Franquias gratuitas reduzem o custo, mas não substituem orçamento, alertas e limites técnicos.

### Restrição temporária: custo estritamente zero

Até uma revisão explícita do usuário, a regra operacional é mais restritiva que a simples existência de franquia:

- não criar um recurso que possa gerar cobrança depois de consumir a franquia gratuita;
- não considerar orçamento ou alerta como bloqueio de cobrança;
- não provisionar Container Apps Environment, Container App, Container Apps Job, Log Analytics ou Azure Container Registry;
- não usar `az containerapp up`, pois o comando pode criar automaticamente registry e workspace de logs;
- não criar Azure SQL até confirmar no próprio fluxo de provisionamento que a Free Offer está aplicada e que o comportamento ao atingir o limite é pausar até o mês seguinte;
- permitir somente operações sem cobrança, como registro de provedor, resource group e consultas de inventário/custo;
- manter toda implementação possível no Docker local enquanto essa restrição estiver ativa.

O resource group existente pode permanecer: ele organiza recursos e não possui cobrança própria. Nenhuma carga de aplicação está ativa na Azure.

Direção proposta para o piloto:

- Azure Container Apps no plano Consumption;
- API com escala mínima zero e máxima um;
- alocação inicial de `0.25` vCPU e `0.5Gi` de memória;
- imagem hospedada fora do Azure Container Registry, evitando o custo fixo diário do ACR;
- Azure SQL Database Free Offer, caso a oferta apareça no provisionamento;
- comportamento do banco configurado para pausar até o mês seguinte quando a franquia terminar, nunca continuar com cobrança automática;
- sem Log Analytics inicialmente, até confirmar a alternativa mínima necessária para diagnóstico;
- orçamento mensal e alertas como proteção adicional, sabendo que orçamento não interrompe recursos.

No momento da decisão, a franquia mensal publicada do Container Apps inclui 180.000 vCPU-segundos, 360.000 GiB-segundos e dois milhões de requisições por assinatura. A oferta gratuita do Azure SQL inclui 100.000 vCore-segundos, 32 GB de dados e 32 GB de backup por banco a cada mês. Essas franquias devem ser reconfirmadas antes do provisionamento porque podem mudar.

## Ordem de provisionamento após a revisão de gastos

1. Definir orçamento mensal e contatos dos alertas.
2. Configurar orçamento e alertas na assinatura.
3. Confirmar quais recursos podem ser criados e quais continuam proibidos.
4. Criar o Container Apps Environment sem Log Analytics inicialmente, se houver autorização explícita para um serviço baseado em franquia.
5. Publicar apenas o `/health`, com escala mínima zero e máxima um.
6. Validar cold start, logs e custo observado antes de adicionar Telegram, jobs ou Azure SQL.

Cada bloco deve ser consultado após a criação e registrado no [`ROADMAP.md`](../ROADMAP.md) antes do próximo provisionamento.
