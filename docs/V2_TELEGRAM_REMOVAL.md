# Contrato de remoção de produtos no Telegram

Estado em 14/09/2026: contrato definido; `/remover` ainda não implementado ou admitido no webhook. Não alterar o menu ou anunciar disponibilidade antes de CI, migração administrativa e deploy. Este contrato detalha a remoção lógica prevista em V2_TELEGRAM_CONVERSATION.md.

## Fluxo público planejado

1. `/remover` exige acesso registrado e nenhuma operação ativa. Sem produtos ativos, responde com lista vazia sem abrir rascunho. Operação ativa é preservada; orientar `/cancelar`.
2. Apresentar até três produtos próprios com slot, apelido, preço-alvo e intervalo. Persistir o mapa slot → UUID da lista apresentada no rascunho `awaiting_product_to_remove`; duração total de 15 minutos.
3. Aceitar somente um número de slot entre 1 e 3. Resolver pelo mapa persistido e conferir novamente proprietário, UUID e atividade. Seleção inválida preserva mapa/estado/expiração; produto indisponível encerra a operação e orienta um novo `/remover`.
4. Seleção válida avança para `awaiting_removal_confirmation`, persiste UUID/slot e nova versão, mantendo a expiração original. Mostrar os dados do produto e a instrução de confirmação `remover <código>` ou `/cancelar`.
5. O código identifica exclusivamente essa proposta: usar a versão UUID completa em hexadecimal (32 caracteres), sem permitir abreviação. Não representa credencial nem concede acesso; proprietário, payload, estado e lease continuam obrigatórios. Uma mensagem antiga não pode confirmar outra proposta. Código incorreto, ausente ou de outra operação preserva o rascunho e não remove nada. Uma futura interface com botão pode transportar a mesma identidade, em incremento separado.
6. Confirmação válida desativa somente o UUID selecionado do proprietário, consome o rascunho e persiste a resposta na mesma transação. Não consultar o slot para escolher novamente o produto. Informar remoção do produto e liberação da vaga; não anunciar coleta/alertas.
7. `/cancelar` encerra somente a operação, sem alterar produtos. `/produtos` e `/ajuda` podem ser usados durante o fluxo e não mudam o rascunho. Expiração impede seleção/confirmação; não renovar prazo por entrada inválida ou replay.

Não aceitar `remover` sem código, `confirmar` de cadastro ou texto adicional como autorização de remoção. UUID interno do produto não precisa aparecer na mensagem. O código da proposta não deve aparecer em logs.

## Persistência, autorização e concorrência

Reutilizar inbox e telegram_registration_results como registro imutável de resposta por update; o nome histórico da tabela não limita seu uso ao cadastro. Nenhum novo armazenamento local ou serviço é necessário.

Cada início, seleção, confirmação e cancelamento deve validar o lease vigente e o payload privado da inbox, incluindo proprietário, destino e texto. Bloquear na ordem inbox → usuário → rascunho → produto. Consultar resultado por update antes de avaliar o estado atual: se existir, retornar exatamente a resposta original. Identidade divergente ou lease perdido aborta a operação; erro SQL reverte todos os efeitos. Conferir novamente o relógio do banco antes de terminar a transação.

Todas as mutações conversacionais precisam usar o bloqueio do usuário nessa mesma ordem. Criar/iniciar outra operação não substitui uma ativa. Seleção e confirmação verificam versão e expiração; a confirmação também exige o código da proposta. Destino nunca substitui telegram_user_id como autorização.

Na confirmação, usar filtro de UUID + telegram_user_id + produto ativo. Produto já desativado/ausente encerra a proposta com resposta durável sem tocar outro registro. Desativação, consumo da versão do rascunho e inserção do resultado são atômicos. Confirmações concorrentes do mesmo update retornam um resultado; outro update com a mesma confirmação após consumo recebe ausência de operação e não produz nova mutação.

Enviar pela Bot API somente depois do commit. Manter a política existente: reagendar apenas falha transitória com resultado conhecido; envio ambíguo vai para dead letter. Uma interrupção depois do commit reutiliza a resposta; não prometer exatamente uma entrega externa.

## Remoção lógica e migração futura

Preservar a linha do produto com `removed_at` nullable, atribuído pelo relógio PostgreSQL. Ativo significa removed_at IS NULL. Produtos atuais devem permanecer ativos ao aplicar a migração.

Substituir as unicidades owner/slot e owner/product_key por índices únicos parciais para produtos ativos. Assim o proprietário mantém no máximo três slots ativos e pode cadastrar novamente uma chave removida com novo UUID; registros históricos não ocupam vagas. Desativação não modifica alias, URL, preço ou intervalo.

Atualizar simultaneamente todas as consultas de ativos: `/produtos`, confirmação de cadastro (duplicata e slots), início/seleção/confirmação de remoção e, futuramente, coletor. Testar que o histórico não aparece na lista nem bloqueia novas inclusões. Evitar deploy de código antigo depois da migração quando já houver produtos removidos: ele não filtra atividade e pode apresentar histórico ou contar vagas incorretamente.

Runtime mantém SELECT/INSERT e recebe somente UPDATE da coluna removed_at; sem UPDATE geral, DELETE ou TRUNCATE em monitored_products. Migração e ownership continuam em argos_migrator, executada fora do HTTP. Não alterar Data API/RLS ou grants públicos neste incremento. Downgrade deve recusar registros removidos ou duplicatas históricas incompatíveis com as constraints anteriores; nunca apagar histórico para viabilizá-lo.

## Pré-requisito identificado no código atual

Na inspeção anterior a este incremento, CancelTelegramConversation e cancel_for_owner excluíam rascunho sem lease, registro por update ou bloqueio de usuário. Se o processo cair após cancelar, reprocessar o mesmo update pode cancelar uma operação iniciada depois; a resposta também muda. Corrigir isso antes de integrar `/remover`: cancelamento deve validar a inbox, bloquear usuário/rascunho e persistir resposta e consumo juntos. Replay retorna a resposta anterior sem alcançar o novo rascunho. A proteção beneficia também `/adicionar`.

## Critérios de aceitação

- Dois proprietários com slots iguais: seleção/código de outro proprietário nunca autorizam acesso ou mutação.
- Lista inicial vazia e acesso não registrado: resposta durável sem rascunho; operação ativa preservada.
- Seleção inválida, código errado e expiração: nenhuma desativação, sem renovação de prazo.
- Remoção concorrente com cadastro: slot liberado pode ser reutilizado; proposta antiga continua vinculada ao UUID original e nunca atinge o substituto.
- Nova proposta para outro produto: confirmação com código antigo é recusada mesmo com update diferente.
- Replay com novo lease, pool reiniciado ou lista alterada: resposta original; nenhuma nova transição/desativação.
- Falha ao inserir resposta: rollback da desativação e do consumo do rascunho.
- Cancelar, iniciar outro fluxo e recuperar cancelamento antigo: nova operação permanece intacta.
- Remoção lógica libera slot/chave, mantém histórico e omite produto removido da listagem.
- Constraints, grants de coluna e downgrade protegido verificados em PostgreSQL descartável; runtime não pode alterar preço/alias nem apagar linhas.
- Fluxo HTTP → inbox → worker → banco com saída Telegram falsa no CI; depois, aceitação manual no bot. Testes não desativam produtos reais.

## Ordem de implementação

1. Tornar `/cancelar` transacional e durável por update, com teste de recuperação que preserve operação nova.
2. Preparar modelo, migração e filtros de produtos ativos com testes PostgreSQL de grants/constraints/downgrade; revisar compatibilidade de deploy antes da aplicação administrativa.
3. Implementar início/seleção e confirmação isolados, com código de proposta e respostas duráveis.
4. Integrar webhook/worker/ajuda, validar CI, aplicar migração pelo executor administrativo e realizar deploy manual; validar no bot antes de atualizar menu.

O contrato não conclui implementação, CI de remoção, migração, deploy ou aceitação manual. Coleta e alertas permanecem pendentes.

Cancelamento durável implementado no runtime em 14/09/2026, ainda aguardando CI/deploy/aceitação. Usa o repositório dedicado PostgreSQLTelegramCancellationRepository; cancel_for_owner permanece como operação de baixo nível fora da composição do worker. Sem migração ou novos grants.

Cancelamento durável aprovado no CI 34880965589, commit a3e0cfa, com PostgreSQL real. Suíte local aprovada (PostgreSQL pulado localmente); deploy e aceitação no bot permanecem pendentes.

Em 14/09/2026, usuário aprovou o processo após deploy dep-dak3rcbl550s73buab9g, 7970d42, live. Consulta agregada independente confirmou um cancelamento durável completed em uma tentativa, 85 updates completed sem outros estados, um produto e um rascunho presentes. Não houve exposição de IDs/payload nem alteração de dados durante a validação. A sequência completa com dois cancelamentos não foi comprovada nessa consulta; permanece pendência de evidência manual. Recuperação após interrupção está comprovada no CI. Próximo incremento: preparar modelo e migração de remoção lógica, sem aplicar em produção durante a preparação.

## Modelo e migração preparados — 14/09/2026

Revisão 20260914_09 adiciona removed_at nullable, troca unicidades por índices únicos parciais de ativos e concede UPDATE somente nessa coluna ao runtime. Modelo e filtros de `/produtos` e confirmação de cadastro atualizados. Downgrade online recusa qualquer produto removido e preserva ativos; downgrade offline recusado por exigir inspeção dos dados.

Testes PostgreSQL preparados para execução real como argos_runtime, bloqueio de alteração de alias/preço e DELETE/TRUNCATE, reutilização de slot/chave, histórico omitido, cadastro com chave removida e upgrade/downgrade com ativo preservado. CI ainda pendente; nada aplicado em produção, que permanece em 20260914_08. O próximo deploy depende da migração administrativa 09. Ainda não há comando de remoção ou desativação automática.

Preparação aprovada no CI 34884132074, commit e6afd27, com PostgreSQL real, incluindo upgrade/downgrade preservando ativo, histórico protegido, grants de coluna e filtros de listagem/cadastro. Suíte local aprovada com integrações PostgreSQL puladas. Próximo passo operacional: aplicar 20260914_09 pelo executor administrativo, verificar revisão/grants/índices e somente então realizar deploy manual. Migração e deploy não executados nesta preparação.

## Migração aplicada em produção — 14/09/2026

Workflow administrativo 34885202890, commit 2bcc050, concluiu com sucesso. Consulta independente confirmou revisão 20260914_09, ownership argos_migrator, um produto preservado/ativo e zero removidos. Índices únicos de proprietário/slot e proprietário/chave têm predicado removed_at IS NULL. Login runtime possui SELECT/INSERT e UPDATE somente removed_at; sem UPDATE geral, alias/preço, DELETE/TRUNCATE ou leitura por roles públicas. Não foram expostos IDs/conteúdo pessoal.

Próximo passo: deploy manual da versão com filtros de ativos, seguido de validação de `/produtos` e início/cancelamento de cadastro. A migração não disponibiliza `/remover` nem inicia coleta.
