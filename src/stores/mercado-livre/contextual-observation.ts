import { getMercadoLivreProductId, normalizeMercadoLivreProductUrl } from "../../security/mercado-livre-url";

/** Local evidence only: never establishes eligibility or authenticates a shop session. */
export interface ContextualObservation {
  store: "mercado-livre";
  externalId: string;
  observedAt: string;
  priceCents: number;
  currency: "BRL";
  origin: "browser";
  extractionMethod: "visible-dom";
  accessContext: "unknown";
  personalization: "unknown";
  eligibility: "unknown";
  sellerId: null;
  variantId: null;
  shippingCents: null;
  validUntil: null;
  conditions: { payment: "pix" | "unknown"; coupon: "mentioned" | "unknown"; membership: "mentioned" | "unknown"; quantity: null };
}

export function observeMercadoLivrePage(document: Document, rawUrl: string): ContextualObservation {
  const url = normalizeMercadoLivreProductUrl(rawUrl);
  const externalId = getMercadoLivreProductId(url);
  if (!externalId) throw new Error("Oferta não identificada.");
  if (/captcha|verifique se você é humano/i.test(document.title + (document.body?.textContent || "").slice(0, 2000))) {
    throw new Error("A loja exige intervenção no navegador.");
  }
  const containers = [...document.querySelectorAll<HTMLElement>(".ui-pdp-price__second-line .andes-money-amount")]
    .filter((element) => !element.closest('[hidden], [aria-hidden="true"], s, del')
      && ![element, ...ancestors(element)].some((node) => {
        const style = document.defaultView?.getComputedStyle(node);
        return style?.display === "none" || style?.visibility === "hidden";
      }));
  const prices = containers.map((element) => {
    const symbol = element.querySelector(".andes-money-amount__currency-symbol")?.textContent?.trim();
    if (symbol !== "R$") throw new Error("Moeda da oferta não confirmada.");
    const fraction = element.querySelector(".andes-money-amount__fraction")?.textContent?.trim() || "";
    const cents = element.querySelector(".andes-money-amount__cents")?.textContent?.trim() ?? "00";
    if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)$/.test(fraction) || !/^\d{2}$/.test(cents)) {
      throw new Error("Preço visível inválido.");
    }
    const value = Number(fraction.replaceAll(".", "")) * 100 + Number(cents);
    if (!Number.isSafeInteger(value) || value <= 0 || value > 999999999) throw new Error("Preço visível inválido.");
    return value;
  });
  const priceCents = prices[0];
  if (priceCents === undefined) throw new Error("Preço visível não identificado. Abra a página do produto.");
  if (new Set(prices).size !== 1) throw new Error("Há preços diferentes na oferta; selecione uma variante antes de observar.");
  const text = containers.map((element) => element.closest(".ui-pdp-price")?.textContent || element.parentElement?.textContent || "").join(" ").slice(0, 4000);
  return {
    store: "mercado-livre", externalId, observedAt: new Date().toISOString(), priceCents, currency: "BRL",
    origin: "browser", extractionMethod: "visible-dom", accessContext: "unknown", personalization: "unknown",
    eligibility: "unknown", sellerId: null, variantId: null, shippingCents: null, validUntil: null,
    conditions: { payment: /(?:^|[^a-z])pix\b/i.test(text) ? "pix" : "unknown", coupon: /\bcupom\b/i.test(text) ? "mentioned" : "unknown", membership: /\bmeli\+|assinatura/i.test(text) ? "mentioned" : "unknown", quantity: null },
  };
}

function ancestors(element: HTMLElement): HTMLElement[] {
  const result: HTMLElement[] = [];
  for (let parent = element.parentElement; parent; parent = parent.parentElement) result.push(parent);
  return result;
}
