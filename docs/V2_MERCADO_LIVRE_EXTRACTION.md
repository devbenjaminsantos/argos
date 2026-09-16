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

Leitura inerte implementada em `html_page.py`: o transporte preserva o charset do único `Content-Type` HTML 200 e o parser aceita somente UTF-8/UTF8 ou charset ausente, sempre com decodificação estrita. Charset diferente e bytes inválidos falham explicitamente. Scripts e estilos não entram no texto visível; entidades são decodificadas; somente os primeiros 2.000 caracteres visíveis alimentam a detecção de bloqueio. Captcha ou frase de verificação humana interrompe o fluxo antes do JSON-LD, inclusive quando há preço presente. O conteúdo não é executado nem exposto no `repr`. 112 testes relacionados passaram localmente. Meta/DOM e composição pública do adaptador são posteriores.

Coleta persistida, `/verificar`, observações e job continuam pendentes. A aceitação funcional entre duas contas da V2.9 foi concluída por relato do usuário; não houve consulta administrativa final. A V2.10 tem seus controles isolados implementados e testados, mas ainda não autoriza tráfego de coleta pelo bot.
