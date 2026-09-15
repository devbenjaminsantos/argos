# Revisão de continuidade — 15/09/2026

Comparação local de código, testes e documentação. Não houve nova consulta aos provedores nesta revisão: referências de produção abaixo usam evidências registradas nas validações anteriores. Checkboxes não substituem código ou aceitação.

## Resultado

A trilha runtime → TLS/conexão → migrador separado → inbox/deduplicação → bot inicial foi entregue e tem evidências registradas. Cadastro, listagem, cancelamento durável e remoção lógica estão implementados; remoção confirmada pela consulta anterior com histórico preservado. A V2.9 permanece aberta pela aceitação manual com dois proprietários e limite individual. Não é necessário bloquear toda preparação técnica enquanto a segunda conta é obtida.

| Achado | Evidência | Ação |
| --- | --- | --- |
| Mensagem `/start` anuncia cadastro/consulta futuros | application/use_cases/start.py, texto de boas-vindas | Atualizar para comandos disponíveis e manter coleta/alertas indisponíveis; validar testes focados e CI antes do deploy |
| Início de `/adicionar` anuncia cadastro completo futuro | application/use_cases/begin_registration.py, replies.started | Corrigir instrução sem modificar prazo ou transação |
| Contexto/roadmap conservam frases históricas como atuais | AI_SHARED_CONTEXT.md e sequência V2.8 | Identificar snapshots históricos e priorizar resumo atual; não inferir falta de implementação por relato antigo |
| Readiness já existe, mas checkbox de fechamento agrupa tudo como pendente | main/API health, backend README e V2.13 | Separar prontidão/correlação existentes de métricas e exercícios operacionais ainda pendentes |
| URL aceita sintaticamente não comprova SSRF seguro | domain/mercado_livre_url.py não faz rede; diretório scrapers contém scaffolding | Preparar política de fetch/DNS/redirecionamentos antes do coletor; não marcar V2.10 concluída |
| Isolamento manual ainda não comprovado | roteiro de duas contas e critério V2.9 | Executar quando houver segunda conta; não substituir pelo CI |

## Pendências que continuam válidas

- Aceitação com duas contas: listas próprias, mesma chave entre proprietários, código alheio recusado, limite individual e remoção sem afetar a outra conta.
- Menu BotFather: confirmação do conjunto de comandos disponíveis ainda pendente.
- Casos manuais de entrada inválida, repetição e cancelamento em etapas intermediárias continuam registrados no roadmap. Código/CI existentes não encerram automaticamente essas pendências. A antiga resposta de confirmação indisponível foi substituída e já não é requisito do fluxo atual.
- Privilégios padrão gerenciados do provedor requerem revisão antes de criar objetos com identidades do provedor ou reativar Data API. Objetos do Argos usam migrador e grants explícitos. Respeitar decisão de Data API desativada e RLS adiado; não alterar indiscriminadamente defaults gerenciados.
- Backup/restauração, rotação, rollback, cold start e falhas externas reais ainda precisam de exercícios documentados. `/health/ready` não comprova disponibilidade futura ou saúde de toda dependência.
- Aceitação Chrome da V1 permanece pendente; independente do piloto Telegram.
- Coletor, observações de preços, job e alertas ainda não implementados. Frontend/OIDC pertencem às trilhas futuras, sem acesso direto ao banco.

## Trabalho possível sem segunda conta

1. Corrigir as mensagens públicas desatualizadas de `/start` e `/adicionar`, em incremento pequeno com CI e posterior deploy manual.
2. Preparar o contrato de fetch seguro: hosts explicitamente permitidos, resolução validada e conexão ao destino validado, bloqueio de redes privadas/reservadas, revalidação de cada redirect e limites de tempo/tamanho. A allowlist sintática atual de subdomínios do Mercado Livre não deve ser adotada automaticamente como política de rede.
3. Implementar e testar a proteção SSRF com DNS/HTTP falsos, sem consultar anúncios reais ou inserir coleta em produção. Validar IPv4/IPv6, DNS rebinding, redirects e respostas excessivas antes do extrator.
4. Preparar runbooks de backup/restauração e rollback; exercícios reais em incremento próprio, com escopo e recursos definidos.

Prioridade imediata: mensagens públicas. Segunda conta permanece uma pendência paralela; não encerrar V2.9 ou habilitar coleta enquanto os respectivos critérios estiverem abertos.
