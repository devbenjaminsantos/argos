# Preparação da extração Mercado Livre

## Estado e origem

A extração JSON-LD isolada está implementada; o extrator HTML completo ainda não. O transporte isolado retorna `FetchedHTML(html: bytes, final_url: str)` após validar destino, redirects e limites. Esta preparação foi baseada em `src/stores/mercado-livre/extractor.ts` e `tests/mercado-livre-extractor.test.ts`; não houve acesso a anúncios reais.

As seis fixtures em `backend/tests/fixtures/mercado_livre/` são sintéticas, mínimas e sem dados de usuários. `manifest.json` registra URL final e resultado esperado para a futura suíte Python. Não comprovam compatibilidade com o HTML atual da loja.

## Contrato previsto

O adaptador recebe HTML limitado e URL final validada, sem executar scripts, carregar imagens ou seguir URLs encontradas no documento. Identidade do produto vem da URL final; canonical, links e dados estruturados não autorizam novas requisições. Título é texto, limitado a 180 caracteres, priorizando `h1.ui-pdp-title`, `og:title` e `title`; fallback: `Produto do Mercado Livre`.

Preço deve ser inteiro positivo em centavos, sem cálculo por ponto flutuante. Resultado previsto: loja `mercado-livre`, ID externo, URL final, título, `price_cents` e fonte. Falha nunca produz preço zero e não deve incluir HTML ou URL completa na mensagem de erro.

| Fonte | Comportamento a portar |
| --- | --- |
| JSON-LD | Prioridade sobre meta/DOM; somente Product, inclusive arrays e @graph; offers.price ou lowPrice. JSON inválido permite tentar a fonte seguinte. |
| Meta | itemprop=price, product:price:amount, og:price:amount, nessa ordem. |
| DOM visível | Apenas contêineres de preço principal usados pela V1; fração e centavos separados. Não capturar preços de recomendações ou parcelas. |

Bloqueio identificado por captcha/título ou frases de verificação humana tem prioridade, mesmo se existir preço. Sem preço válido, classificar `product_unavailable` quando houver as frases de indisponibilidade usadas pela V1; caso contrário, `price_not_found`.

## Fixtures e sequência

- `json_ld_priority.html`: JSON-LD vence um meta com preço diferente.
- `malformed_json_meta.html`: JSON inválido permite fallback para meta.
- `visible_price.html`: 2.199,90 e título com markup não executável.
- `access_blocked.html`: bloqueio prevalece sobre preço presente.
- `unavailable.html`: indisponibilidade sem preço.
- `missing_price.html`: preço zero inválido, erro explícito.

Extração JSON-LD isolada implementada em infrastructure/scrapers/mercado_livre/json_ld.py: Product/arrays/@graph, offers.price/lowPrice, Decimal e centavos exatos positivos até 999999999, sem arredondamento; strings decimais com ponto, sem formato local/expoente. Moeda ausente aceita no contexto ML Brasil; moeda explícita diferente de BRL falha. Preços válidos conflitantes falham ambiguous_price, iguais concordam. Scripts inválidos/valores inválidos permitem fonte posterior; limites de 32 scripts, 2 MiB de texto e profundidade 32. 32 testes locais passaram; CI 35007318534 aprovado em 5cacc60.

Leitura inerte implementada em `html_page.py`: o transporte preserva o charset do único `Content-Type` HTML 200 e o parser aceita somente UTF-8/UTF8 ou charset ausente, sempre com decodificação estrita. Charset diferente e bytes inválidos falham explicitamente. Scripts e estilos não entram no texto visível; entidades são decodificadas; somente os primeiros 2.000 caracteres visíveis alimentam a detecção de bloqueio. Captcha ou frase de verificação humana interrompe o fluxo antes do JSON-LD, inclusive quando há preço presente. O conteúdo não é executado nem exposto no `repr`. 112 testes relacionados passaram localmente; CI 35100500881 aprovado em 8b3a21c. Meta/DOM e composição pública do adaptador são posteriores.

Título e metadados foram portados sem DOM executável. O título prioriza `h1.ui-pdp-title`, `og:title` e `<title>`, normaliza espaços, limita a 180 caracteres e usa fallback estável. O preço mantém JSON-LD como primeira fonte; JSON inválido ou sem preço permite tentar, em ordem, `itemprop=price`, `product:price:amount` e `og:price:amount`. Apenas o primeiro elemento de cada seletor é considerado, como em `querySelector`; valor inválido avança ao próximo seletor. Resultados intermediários omitem conteúdo não confiável do `repr`. Quarenta e nove testes focados e a suíte completa local passaram; CI 35102552967 aprovado em 2510fed. Preço visível e resultado final do adaptador permanecem no próximo incremento.

Preço visível portado somente de `.ui-pdp-price__second-line` e `.ui-pdp-price__main-container`, exigindo descendente `.andes-money-amount`. Fração e centavos são lidos como texto e convertidos em inteiros com limite monetário; preços fora desses contêineres, zero, conteúdo inválido e excesso são ignorados. O resultado final contém loja, ID externo derivado exclusivamente da URL final validada, URL final, título, preço em centavos e fonte. Sem preço, diferencia `product_unavailable` de `price_not_found`; bloqueio permanece prioritário. As seis fixtures do manifesto, 65 testes focados e a suíte completa local passaram; CI 35103344973 aprovado em 31fe398. O adaptador ainda não compõe rede e extração numa porta pública e não está ligado ao bot.

Composição interna preparada em `MercadoLivreCollector`: a aplicação define `ProductCollector`, `CollectedProduct` e `ProductCollectionError`; a infraestrutura injeta `fetch_html_once` e `extract_product`. Cada chamada executa uma única tentativa, sem fallback de transporte ou retry. Falhas de política, página e preço estruturado são convertidas em códigos simples validados; URL, HTML e detalhes de rede não entram na exceção. Resultado injetado inválido continua sendo erro de programação. Oitenta e dois testes focados e a suíte completa local passaram; CI 35107292418 aprovado em 5b7fede. Ainda não existe caso de uso de verificação, persistência de observação ou comando Telegram.

Caso de uso interno `VerifyProduct` preparado sem entrada Telegram: recebe `telegram_user_id` e UUID do produto, usa uma porta que exige busca ativa escopada aos dois valores, executa uma coleta e recusa identidade externa diferente da chave cadastrada. O resultado omite URL e contém alias/título, preço atual, preço-alvo, fonte e decisão `target_reached`. Produto ausente ou alheio retorna o mesmo `product_not_found`; códigos do coletor são traduzidos para erros públicos seguros. Trinta e cinco testes focados e a suíte completa local passaram; CI 35108277106 aprovado em df57d45. A porta de leitura ainda não tem adaptador PostgreSQL e nenhuma observação é persistida.

Leitura PostgreSQL implementada em `PostgreSQLProductVerificationTargets`: um único SELECT exige simultaneamente UUID, `telegram_user_id` e `removed_at IS NULL`, retornando somente chave, URL, alias e meta necessários ao caso de uso. Produto removido, inexistente ou alheio resulta em `None`; não há fallback por chave/URL. O adaptador utiliza o SELECT já concedido ao runtime, sem ampliar UPDATE/DELETE/TRUNCATE. Vinte e três testes locais focados e oito integrações PostgreSQL foram aprovados; CI 35122262352 em efff34c. Observações ainda não são persistidas.

Migração `20260916_10` e contrato `PriceObservation` preparados para histórico append-only. O UUID da observação é a chave idempotente. Sucesso exige preço entre 1 e 999999999 e fonte conhecida, sem erro; falha exige preço/fonte nulos e código sanitizado. A meta de preço é preservada como snapshot. Uma FK composta por produto/proprietário impede registros cruzados. Data API roles e PUBLIC não leem a tabela; `argos_runtime` recebe somente SELECT/INSERT. Downgrade recusa apagar histórico existente. Doze testes de contrato passaram localmente e 12 integrações PostgreSQL foram aprovadas no CI 35123926472, commit 7c34163.

`PostgreSQLPriceObservationRepository` grava com `INSERT ... ON CONFLICT DO NOTHING` dentro de uma transação. Em colisão, compara todos os campos da linha vencedora: repetição idêntica retorna sem duplicar; reutilização divergente do UUID lança `PriceObservationConflictError` e preserva a linha original. Quatro integrações cobrem replay sequencial, divergência e as duas formas concorrentes; foram aprovadas no CI 35130500915, commit ca9b179.

`VerifyProduct` recebe `observation_id` e `observed_at` do executor para preservar a chave entre retries. Depois de localizar um alvo ativo do proprietário, grava sucesso com preço/fonte ou falha sem preço para erros de coleta e identidade final divergente. Entrada inválida e produto ausente não criam histórico. Nenhum resultado de sucesso ou erro público de coleta é entregue antes da persistência; falha do repositório interrompe a operação. Vinte e um testes do caso de uso e duas integrações do caminho completo com os adaptadores PostgreSQL foram aprovados no CI 35132196464, commit a7fbcdf. `/verificar` ainda não está ligado ao Telegram.

O contrato Telegram aceita somente `/verificar <UUID canônico completo>`, com espaços ou tabulação no mesmo texto e sem argumentos extras. O UUID da observação é derivado de forma determinística do `update_id`, permitindo que o executor preserve a chave em recuperação. A resposta de sucesso usa apenas apelido, preços e comparação com a meta; omite título remoto e fonte técnica. Falhas usam uma allowlist de mensagens, sem propagar detalhes internos. Dezenove testes e a suíte completa foram aprovados no CI 35132873065, commit 5576eca. Admissão HTTP, worker e `/ajuda` ainda não reconhecem o comando: antes disso, falta recuperar observação/resultado durável sem refazer coleta após uma interrupção.

Coleta persistida, `/verificar`, observações e job continuam pendentes. A aceitação funcional entre duas contas da V2.9 foi concluída por relato do usuário; não houve consulta administrativa final. A V2.10 tem seus controles isolados implementados e testados, mas ainda não autoriza tráfego de coleta pelo bot.
