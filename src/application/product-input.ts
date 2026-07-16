import type { NewProductInput } from "../domain/product";
import { normalizeMercadoLivreProductUrl } from "../security/mercado-livre-url";

export function validateNewProductInput(input: NewProductInput): NewProductInput {
  const normalizedUrl = normalizeMercadoLivreProductUrl(input.url);
  const normalizedExtractionUrl = normalizeMercadoLivreProductUrl(input.initialExtraction.url);
  const name = input.name.trim();

  if (normalizedUrl !== normalizedExtractionUrl) {
    throw new Error("A página extraída não corresponde à URL informada.");
  }
  if (name.length < 1 || name.length > 80) {
    throw new Error("O apelido deve ter entre 1 e 80 caracteres.");
  }
  if (!Number.isSafeInteger(input.targetPriceCents) || input.targetPriceCents <= 0) {
    throw new Error("Informe um preço-alvo válido.");
  }
  if (
    !Number.isFinite(input.alertDropPercent) ||
    input.alertDropPercent < 1 ||
    input.alertDropPercent > 100
  ) {
    throw new Error("A queda relevante deve estar entre 1% e 100%.");
  }
  if (input.checkIntervalHours !== 12 && input.checkIntervalHours !== 24) {
    throw new Error("O intervalo deve ser de 12 ou 24 horas.");
  }
  if (
    !Number.isSafeInteger(input.initialExtraction.priceCents) ||
    input.initialExtraction.priceCents <= 0
  ) {
    throw new Error("A página não forneceu um preço válido.");
  }

  return {
    ...input,
    url: normalizedUrl,
    name,
    initialExtraction: {
      ...input.initialExtraction,
      url: normalizedExtractionUrl,
      title: input.initialExtraction.title.trim().slice(0, 180),
    },
  };
}

