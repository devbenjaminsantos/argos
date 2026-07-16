import { describe, expect, it } from "vitest";
import { validateNewProductInput } from "../src/application/product-input";
import type { NewProductInput } from "../src/domain/product";

const validInput: NewProductInput = {
  url: "https://www.mercadolivre.com.br/item/p/MLB123456",
  name: "Notebook",
  targetPriceCents: 300_000,
  alertDropPercent: 10,
  checkIntervalHours: 24,
  initialExtraction: {
    store: "mercado-livre",
    externalId: "MLB123456",
    url: "https://www.mercadolivre.com.br/item/p/MLB123456",
    title: "Notebook",
    priceCents: 350_000,
    source: "json-ld",
  },
};

describe("validateNewProductInput", () => {
  it("aceita e normaliza uma entrada válida", () => {
    expect(validateNewProductInput(validInput).name).toBe("Notebook");
  });

  it("rejeita divergência entre a URL e a extração", () => {
    expect(() =>
      validateNewProductInput({
        ...validInput,
        url: "https://www.mercadolivre.com.br/outro/p/MLB999999",
      }),
    ).toThrow("não corresponde");
  });

  it("rejeita valores e limites inválidos", () => {
    expect(() => validateNewProductInput({ ...validInput, targetPriceCents: 0 })).toThrow(
      "preço-alvo",
    );
    expect(() => validateNewProductInput({ ...validInput, alertDropPercent: 101 })).toThrow(
      "entre 1% e 100%",
    );
  });
});

