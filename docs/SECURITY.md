# Segurança da V1 Chrome

Este documento descreve as fronteiras de confiança da extensão Argos, os controles adotados e os riscos que permanecem na V1.

## Fronteiras de confiança

São considerados não confiáveis:

- URLs e parâmetros vindos de páginas;
- todo HTML e texto recebido do Mercado Livre;
- preços e metadados presentes no DOM;
- mensagens originadas em content scripts;
- respostas de rede e redirecionamentos.

O popup, o service worker e o documento offscreen pertencem ao pacote da extensão, mas ainda validam as mensagens antes de executar uma operação.

## Controles adotados

### URLs e requisições

- somente o protocolo HTTPS é aceito;
- o domínio deve ser `mercadolivre.com.br` ou um subdomínio direto/indireto dele;
- credenciais embutidas e portas diferentes de 443 são rejeitadas;
- o caminho precisa corresponder a um identificador de produto `MLB`;
- URLs de redirecionamento são validadas novamente;
- redirecionamentos para outro produto são rejeitados quando existe um identificador conhecido;
- cookies e credenciais do usuário não são enviados pela coleta em segundo plano;
- o HTML recebido possui limite de 3 MB.

Essas regras evitam que o coletor funcione como um cliente genérico para URLs arbitrárias. Na futura versão com back-end, a mesma validação deverá ser complementada por resolução segura de DNS, bloqueio de endereços privados e proteção específica contra SSRF.

### XSS e conteúdo remoto

- scripts encontrados no HTML não são executados;
- dados estruturados são processados com `JSON.parse`, nunca com `eval`;
- a interface usa `textContent` e criação explícita de elementos;
- nenhum HTML coletado é atribuído a `innerHTML`;
- o Manifest V3 não carrega código JavaScript remoto.

### Mensagens e armazenamento

- o service worker valida o formato de todas as solicitações;
- operações de criação, remoção e coleta manual são recusadas quando chegam de uma aba/content script;
- a página não pode escolher uma URL arbitrária para o service worker buscar;
- preços são armazenados como centavos inteiros;
- falhas de coleta nunca são convertidas em preço zero;
- notificações equivalentes são deduplicadas por produto, motivo e preço.

## Segredos e endpoints

A V1 não utiliza endpoint remoto, autenticação ou token de Telegram. Nenhum segredo deve ser adicionado ao código, ao manifesto ou ao armazenamento da extensão. Canais remotos deverão ser implementados por um back-end que mantenha as credenciais fora do pacote distribuído.

## Riscos residuais

- o marketplace pode alterar HTML, dados estruturados ou comportamento de renderização;
- uma página pode apresentar preço de Pix, cupom, variante ou condição diferente da esperada;
- proteções contra automação podem bloquear a coleta agendada;
- o Chrome pode atrasar verificações e não executa coletas com o dispositivo desligado;
- uma página comprometida pode fornecer dados falsos ao extrator, embora não obtenha acesso direto ao IndexedDB da extensão;
- o histórico local pode ser perdido ao remover a extensão ou apagar seus dados.

Esses riscos devem ser tratados com testes manuais em páginas reais, telemetria local de status, versionamento dos adaptadores e, posteriormente, coletores controlados no back-end.

## Controles planejados para a V2 Telegram

O modelo de ameaças detalhado e os testes obrigatórios da V2 estão documentados em [`V2_SECURITY.md`](V2_SECURITY.md).

- webhook autenticado por `X-Telegram-Bot-Api-Secret-Token`;
- aceitação somente de conversas privadas;
- identidade do proprietário baseada em `telegram_user_id`, nunca em `username`;
- `chat_id` tratado apenas como destino de mensagens;
- deduplicação persistente por `update_id`;
- rate limit por usuário e lista fechada de comandos;
- propriedade explícita de produtos, históricos e notificações;
- consultas sempre escopadas ao usuário Telegram;
- testes negativos de acesso entre usuários;
- conexão TLS com Supabase PostgreSQL usando credencial de runtime armazenada somente como segredo;
- permissões mínimas e separadas entre identidade humana e credencial da carga;
- proteção contra SSRF antes de ativar coletas cloud;
- quotas do plano Free verificadas antes de jobs recorrentes.

## Controles planejados para a V3 cloud

- autenticação federada OIDC/OAuth 2.0;
- Authorization Code com PKCE para extensão e aplicativo móvel;
- identidade interna baseada em `issuer` e `subject`;
- vinculação explícita e auditável entre conta OIDC e identidade Telegram;
- autorização dentro da aplicação, além da autenticação na borda.
