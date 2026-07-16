// @vitest-environment jsdom

import { describe, expect, it } from "vitest";
import {
  extractMercadoLivreProduct,
  ProductExtractionError,
} from "../src/stores/mercado-livre/extractor";

const PRODUCT_URL = "https://www.mercadolivre.com.br/notebook/p/MLB123456";

describe("extractMercadoLivreProduct", () => {
  it("prioriza o preço estruturado do produto", () => {
    const document = parse(`
      <html>
        <head>
          <meta property="og:title" content="Notebook seguro" />
          <script type="application/ld+json">
            {"@type":"Product","offers":{"@type":"Offer","price":"3499.90"}}
          </script>
        </head>
      </html>
    `);

    expect(extractMercadoLivreProduct(document, PRODUCT_URL)).toMatchObject({
      externalId: "MLB123456",
      title: "Notebook seguro",
      priceCents: 349_990,
      source: "json-ld",
    });
  });

  it("extrai reais e centavos do preço visível sem inserir HTML na interface", () => {
    const document = parse(`
      <html><body>
        <h1 class="ui-pdp-title"><img src=x onerror="globalThis.compromised=true">Notebook</h1>
        <div class="ui-pdp-price__second-line">
          <span class="andes-money-amount">
            <span class="andes-money-amount__fraction">2.199</span>
            <span class="andes-money-amount__cents">90</span>
          </span>
        </div>
      </body></html>
    `);

    const result = extractMercadoLivreProduct(document, PRODUCT_URL);
    expect(result.priceCents).toBe(219_990);
    expect(result.title).toBe("Notebook");
    expect((globalThis as { compromised?: boolean }).compromised).not.toBe(true);
  });

  it("classifica uma página de bloqueio sem gerar preço zero", () => {
    const document = parse("<html><head><title>Captcha</title></head><body></body></html>");

    expect(() => extractMercadoLivreProduct(document, PRODUCT_URL)).toThrowError(
      expect.objectContaining<Partial<ProductExtractionError>>({ code: "access_blocked" }),
    );
  });
});

function parse(html: string): Document {
  return new DOMParser().parseFromString(html, "text/html");
}

