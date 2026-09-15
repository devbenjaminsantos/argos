# Preparação da extração Mercado Livre

## Estado e origem

O extrator Python ainda não está implementado. O transporte isolado retorna `FetchedHTML(html: bytes, final_url: str)` após validar destino, redirects e limites. Esta preparação foi baseada em `src/stores/mercado-livre/extractor.ts` e `tests/mercado-livre-extractor.test.ts`; não houve acesso a anúncios reais.

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

Próximo incremento: implementar somente JSON-LD e conversão monetária com Decimal, usando fixtures e casos de valores inválidos, moeda e estrutura ambígua. Definir explicitamente arredondamento, limite monetário e ofertas múltiplas antes de portar esses comportamentos; não copiar permissividade numérica da V1 automaticamente. Meta e DOM serão incrementos posteriores. Charset/decodificação e limites do parser também precisam de decisão antes da composição com transporte.

Coleta persistida, `/verificar`, observações e job continuam pendentes. A aceitação manual entre duas contas da V2.9 permanece aberta. A V2.10 não deve ser declarada encerrada apenas por estas fixtures.
