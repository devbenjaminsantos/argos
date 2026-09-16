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

Coleta persistida, `/verificar`, observações e job continuam pendentes. A aceitação funcional entre duas contas da V2.9 foi concluída por relato do usuário; não houve consulta administrativa final. A V2.10 tem seus controles isolados implementados e testados, mas ainda não autoriza tráfego de coleta pelo bot.
