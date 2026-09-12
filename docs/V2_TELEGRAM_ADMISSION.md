# Admissão de comandos Telegram

## Estado

Política e contrato de aplicação implementados em 12/09/2026. O adaptador PostgreSQL e a migração `20260912_05` estão implementados e aguardam validação em PostgreSQL real. A ligação ao webhook ainda está pendente. O rate limit ainda não está ativo em produção.

## Política inicial do piloto

- Admitir até 10 comandos suportados por `telegram_user_id` em uma janela móvel de 60 segundos; valores poderão entrar pela configuração na composição.
- Contar somente primeiras admissões na janela `(recebimento - 60 segundos, recebimento]`; comandos repetidos e rejeitados não consomem quota.
- Aplicar a política antes de criar trabalho, inclusive para usuários que ainda não enviaram `/start`, sem exigir uma identidade cadastrada.
- Usar uma decisão durável por `update_id`: `admitted`, `duplicate` ou `rate_limited`. `duplicate` descreve uma repetição da decisão original, que permanece inalterada.
- Confirmar excedentes com HTTP `200`, sem execução, entrada na inbox ou resposta pela Bot API. Isso evita novas entregas do mesmo comando e mensagens adicionais durante abuso.
- Falha de persistência deve produzir `503`; nunca confirmar uma decisão que não foi gravada.

O filtro de segredo, formato, conversa privada e lista fechada precede a admissão. Comandos desconhecidos continuam sendo confirmados sem persistência. A proteção global de capacidade e os limites de operações de coleta são requisitos separados, ainda pendentes.

## Critérios do adaptador PostgreSQL

Deduplicação, avaliação da quota e inserção na inbox devem ocorrer em uma única transação, com serialização por proprietário. A implementação deve usar tempo consistente, não permitir que timestamps obsoletos contornem o limite e preservar decisões após reinício. Não criar um contador em memória ou fazer uma consulta de contagem sem bloquear concorrência.

Testar em PostgreSQL real: dez admissões e rejeição da décima primeira; liberação na fronteira de 60 segundos; isolamento entre proprietários; concorrência sem ultrapassar dez admissões; repetição de admitidos e excedentes; recuperação após reinício; rollback sem quota ou decisão parcial quando a inbox falha. A retenção das decisões deve acompanhar a política de deduplicação da inbox; não apagar registros sem definir essa política.

## Implementação da persistência

`telegram_admission_owners` serializa operações por proprietário e mantém um horário monotônico. `telegram_admissions` guarda somente proprietário, update, horário e decisão; somente admissões guardam payload na inbox. O adaptador bloqueia o proprietário, reserva o update globalmente, conta admissões na janela e grava decisão e inbox na mesma transação. Updates já presentes na inbox antes da ativação retornam duplicata sem consumir quota.

A migração concede somente SELECT/INSERT/UPDATE ao runtime e revoga acesso das roles públicas. O downgrade recusa remover tabelas que contenham decisões ou proprietários. A revisão ainda não foi aplicada em produção.
