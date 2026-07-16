import type { ExtractedProduct, PriceObservation } from "../../domain/product";
import {
  getMercadoLivreProductId,
  normalizeMercadoLivreProductUrl,
} from "../../security/mercado-livre-url";

export class ProductExtractionError extends Error {
  constructor(
    public readonly code: "price_not_found" | "product_unavailable" | "access_blocked",
    message: string,
  ) {
    super(message);
    this.name = "ProductExtractionError";
  }
}

export function extractMercadoLivreProduct(
  document: Document,
  rawUrl: string,
): ExtractedProduct {
  const url = normalizeMercadoLivreProductUrl(rawUrl);

  if (looksBlocked(document)) {
    throw new ProductExtractionError(
      "access_blocked",
      "O Mercado Livre bloqueou ou interrompeu a coleta.",
    );
  }

  const title = extractTitle(document);
  const price = extractJsonLdPrice(document) ?? extractMetaPrice(document) ?? extractVisiblePrice(document);

  if (price === null) {
    if (looksUnavailable(document)) {
      throw new ProductExtractionError("product_unavailable", "O produto parece indisponível.");
    }
    throw new ProductExtractionError(
      "price_not_found",
      "Não foi possível identificar um preço válido nesta página.",
    );
  }

  return {
    store: "mercado-livre",
    externalId: getMercadoLivreProductId(url),
    url,
    title,
    priceCents: price.priceCents,
    source: price.source,
  };
}

function extractTitle(document: Document): string {
  const candidates = [
    document.querySelector<HTMLHeadingElement>("h1.ui-pdp-title")?.textContent,
    document.querySelector<HTMLMetaElement>('meta[property="og:title"]')?.content,
    document.title,
  ];

  const title = candidates.find((value) => value?.trim())?.trim();
  return title?.slice(0, 180) || "Produto do Mercado Livre";
}

function extractJsonLdPrice(
  document: Document,
): { priceCents: number; source: PriceObservation["source"] } | null {
  const scripts = document.querySelectorAll<HTMLScriptElement>('script[type="application/ld+json"]');

  for (const script of scripts) {
    try {
      const value: unknown = JSON.parse(script.textContent || "null");
      const price = findProductPrice(value);
      const priceCents = toPriceCents(price);
      if (priceCents !== null) return { priceCents, source: "json-ld" };
    } catch {
      // Dados estruturados inválidos não devem impedir os próximos extratores.
    }
  }

  return null;
}

function findProductPrice(value: unknown): unknown {
  if (Array.isArray(value)) {
    for (const item of value) {
      const result = findProductPrice(item);
      if (result !== null && result !== undefined) return result;
    }
    return null;
  }

  if (!isRecord(value)) return null;

  if ("@graph" in value) {
    const graphResult = findProductPrice(value["@graph"]);
    if (graphResult !== null && graphResult !== undefined) return graphResult;
  }

  const type = value["@type"];
  const isProduct = type === "Product" || (Array.isArray(type) && type.includes("Product"));
  if (isProduct) {
    const offers = value.offers;
    if (Array.isArray(offers)) {
      const offer = offers.find(isRecord);
      return offer?.price ?? offer?.lowPrice ?? null;
    }
    if (isRecord(offers)) return offers.price ?? offers.lowPrice ?? null;
  }

  return null;
}

function extractMetaPrice(
  document: Document,
): { priceCents: number; source: PriceObservation["source"] } | null {
  const selectors = [
    'meta[itemprop="price"]',
    'meta[property="product:price:amount"]',
    'meta[property="og:price:amount"]',
  ];

  for (const selector of selectors) {
    const content = document.querySelector<HTMLMetaElement>(selector)?.content;
    const priceCents = toPriceCents(content);
    if (priceCents !== null) return { priceCents, source: "meta" };
  }

  return null;
}

function extractVisiblePrice(
  document: Document,
): { priceCents: number; source: PriceObservation["source"] } | null {
  const containers = document.querySelectorAll<HTMLElement>(
    ".ui-pdp-price__second-line .andes-money-amount, .ui-pdp-price__main-container .andes-money-amount",
  );

  for (const container of containers) {
    const fraction = container.querySelector<HTMLElement>(".andes-money-amount__fraction")?.textContent;
    const cents = container.querySelector<HTMLElement>(".andes-money-amount__cents")?.textContent;
    if (!fraction) continue;

    const integerPart = Number(fraction.replace(/\D/g, ""));
    const centsPart = cents ? Number(cents.replace(/\D/g, "").padEnd(2, "0").slice(0, 2)) : 0;
    const priceCents = integerPart * 100 + centsPart;
    if (Number.isSafeInteger(priceCents) && priceCents > 0) {
      return { priceCents, source: "visible-dom" };
    }
  }

  return null;
}

function toPriceCents(value: unknown): number | null {
  if (typeof value === "number") return decimalToCents(value);
  if (typeof value !== "string") return null;

  let normalized = value.trim().replace(/\s|R\$/gi, "");
  if (!normalized) return null;

  if (normalized.includes(",")) {
    normalized = normalized.replace(/\./g, "").replace(",", ".");
  } else if (/^\d{1,3}(\.\d{3})+$/.test(normalized)) {
    normalized = normalized.replace(/\./g, "");
  }

  return decimalToCents(Number(normalized));
}

function decimalToCents(value: number): number | null {
  const cents = Math.round(value * 100);
  return Number.isSafeInteger(cents) && cents > 0 ? cents : null;
}

function looksUnavailable(document: Document): boolean {
  const text = document.body?.textContent?.toLowerCase() || "";
  return text.includes("produto indisponível") || text.includes("anúncio finalizado");
}

function looksBlocked(document: Document): boolean {
  const title = document.title.toLowerCase();
  const text = document.body?.textContent?.toLowerCase().slice(0, 2_000) || "";
  return (
    title.includes("captcha") ||
    text.includes("não conseguimos confirmar que você é humano") ||
    text.includes("verifique se você é humano")
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

