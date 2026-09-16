# Aceitação do Telegram com dois usuários

Estado em 15/09/2026: cadastro, listagem e remoção implementados. Cadastro e listagem isolados aceitos por relato do usuário; operações e limite individual ainda pendentes. Usar duas contas Telegram distintas em conversas privadas com o bot de teste; dois dispositivos da mesma conta não representam dois proprietários.

Executar com dados de teste e respeitar a quota de dez entradas por minuto por proprietário. Não publicar IDs, payloads, URLs pessoais ou códigos de proposta nos registros de validação. A coleta e os alertas permanecem indisponíveis.

| Passo | Conta A | Conta B | Resultado esperado |
| --- | --- | --- | --- |
| Acesso | `/start` | `/start` e `/produtos` | B vê sua própria lista; vazia se ainda não cadastrou |
| Cadastro | Cadastrar um produto com apelido `Teste A` | Cadastrar o mesmo anúncio com apelido `Teste B` | Chave igual permitida entre proprietários |
| Consulta | `/produtos` | `/produtos` | Cada conta vê somente seu apelido e preço-alvo |
| Operação ativa | `/remover`, selecionar o produto | `/adicionar`, manter rascunho ativo | Operações independentes |
| Código de outra proposta | Manter proposta aberta | Enviar o código de A em B | Nenhuma remoção autorizada em B; rascunhos independentes |
| Cancelamento | `/cancelar` | Continuar ou `/cancelar` | Cancelar A não encerra operação de B |
| Limite | Cadastrar até três ativos e tentar um quarto anúncio distinto | Consultar ou cadastrar em suas próprias vagas | Limite individual; tentativa de A não consome vaga de B |
| Remoção | Remover um produto com o código correto | `/produtos` | B permanece intacto; A deixa de listar removido |
| Reutilização | Recadastrar o anúncio removido | `/produtos` | A reutiliza vaga/chave; histórico preservado; B intacto |
| Repetição | Repetir `/produtos` | Repetir `/produtos` | Listas estáveis, sem efeitos adicionais |

O envio do código de A enquanto B está cadastrando não comprova sozinho a proteção entre duas propostas de remoção. Para esse caso, abrir `/remover` e selecionar produto nas duas contas; enviar o código de A na proposta de B. B deve recusar o código e preservar o produto/proposta. Depois cancelar as propostas para limpar os testes.

## Evidência já disponível

Testes PostgreSQL verificam produto com mesma chave em proprietários distintos, listagem filtrada, abertura de remoção omitindo produtos alheios e rejeição de claim com proprietário divergente na seleção/confirmacão. Há cobertura de limite, concorrência, histórico, slot reutilizado, replay e rollback. CI de integração 34978574492 aprovou o fluxo HTTP com saída Telegram falsa; isso não substitui a aceitação com duas contas reais.

## Registro de conclusão

Registrar quais passos foram executados e seus resultados. Marcar o critério da V2.9 somente depois de comprovar listas isoladas e limite individual. Consulta administrativa de confirmação deve retornar somente agregados: quantidade de proprietários com produtos, limite máximo de ativos por proprietário, contagens de produtos ativos/removidos e estados da inbox. Não gerar mensagens ou remover produtos reais por ferramentas para simular aceitação.

Menu do BotFather continua com confirmação pendente; sincronizar somente os comandos disponíveis: start, ajuda, adicionar, produtos, remover e cancelar. Aceitação Chrome da V1 e testes reais de falhas da Bot API permanecem pendências separadas.

## Retomada da validação

- [x] Segunda conta disponível, conforme relato do usuário.
- [x] Usuário relatou envio de `/start` pela conta B.
- [ ] Confirmar explicitamente a resposta de `/start` da conta B.
- [x] Confirmar lista inicial de B vazia com `/produtos`, enquanto A lista seu produto; relato do usuário.
- [x] Cadastrar o mesmo anúncio em A/B, com apelidos e configurações distintos, e comprovar listas isoladas; relato do usuário.
- [ ] Executar operações independentes, cancelamento e código entre duas propostas de remoção.
- [ ] Comprovar limite individual, remoção, reutilização e repetição conforme tabela.

Não há confirmação administrativa nova nesta retomada. A extração foi pausada para priorizar este aceite; cadastro/listagem foram aceitos por relato; demais resultados continuam pendentes.

Aceite manual relatado pelo usuário: A cadastrou produto e /produtos exibiu o item; B inicialmente sem produtos recebeu lista vazia. Depois, mesmo anúncio cadastrado nas duas contas: A com apelido relógio, alvo R$ 50 e intervalo 12 h; B com relógio de mesa, alvo R$ 400 e intervalo 24 h. Cada conta continuou exibindo somente seus produtos/configurações. Isolamento de cadastro/listagem aceito por relato, sem nova consulta administrativa. Operações independentes, cancelamento, códigos de remoção e limite individual ainda pendentes.
