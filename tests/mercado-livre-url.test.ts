import { describe, expect, it } from "vitest";
import {
  getMercadoLivreProductId,
  normalizeMercadoLivreProductUrl,
  UnsafeProductUrlError,
} from "../src/security/mercado-livre-url";

describe("normalizeMercadoLivreProductUrl", () => {
  it("aceita páginas HTTPS de produto e remove rastreamento", () => {
    const result = normalizeMercadoLivreProductUrl(
      "https://www.mercadolivre.com.br/produto/p/MLB123456?variation=1&utm_source=test#reviews",
    );

    expect(result).toBe(
      "https://www.mercadolivre.com.br/produto/p/MLB123456?variation=1",
    );
    expect(getMercadoLivreProductId(result)).toBe("MLB123456");
  });

  it.each([
    "http://www.mercadolivre.com.br/produto/p/MLB123456",
    "https://mercadolivre.com.br.evil.example/produto/p/MLB123456",
    "https://user:password@www.mercadolivre.com.br/produto/p/MLB123456",
    "https://www.mercadolivre.com.br:8443/produto/p/MLB123456",
    "https://www.mercadolivre.com.br/ofertas",
    "javascript:alert(1)",
  ])("rejeita uma URL fora da lista segura: %s", (url) => {
    expect(() => normalizeMercadoLivreProductUrl(url)).toThrow(UnsafeProductUrlError);
  });
});

