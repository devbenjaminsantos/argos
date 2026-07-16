import { describe, expect, it } from "vitest";
import { evaluatePriceAlert } from "../src/domain/price-rules";
import type { Product } from "../src/domain/product";

const product: Product = {
  id: "product-1",
  store: "mercado-livre",
  externalId: "MLB123",
  url: "https://www.mercadolivre.com.br/item/p/MLB123",
  name: "Produto",
  targetPriceCents: 80_000,
  alertDropPercent: 10,
  checkIntervalHours: 24,
  createdAt: "2026-07-16T00:00:00.000Z",
  updatedAt: "2026-07-16T00:00:00.000Z",
  lastCheckedAt: "2026-07-16T00:00:00.000Z",
  nextCheckAt: "2026-07-17T00:00:00.000Z",
  lastPriceCents: 100_000,
};

describe("evaluatePriceAlert", () => {
  it("prioriza o alerta de preço-alvo", () => {
    const alert = evaluatePriceAlert(product, 79_900);
    expect(alert?.reason).toBe("target_reached");
  });

  it("detecta uma queda percentual relevante", () => {
    const alert = evaluatePriceAlert(product, 90_000);
    expect(alert?.reason).toBe("relevant_drop");
    expect(alert?.dropPercent).toBe(10);
  });

  it("não alerta para queda abaixo do limite", () => {
    expect(evaluatePriceAlert(product, 95_000)).toBeNull();
  });

  it("não trata preço inválido como queda", () => {
    expect(evaluatePriceAlert(product, 0)).toBeNull();
  });
});

