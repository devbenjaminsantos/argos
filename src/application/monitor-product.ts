import { evaluatePriceAlert } from "../domain/price-rules";
import type { CollectionStatus, PriceObservation, Product } from "../domain/product";
import {
  getProduct,
  hasNotification,
  recordNotification,
  saveObservation,
} from "../infrastructure/database/argos-repository";
import {
  getMercadoLivreProductId,
  normalizeMercadoLivreProductUrl,
} from "../security/mercado-livre-url";
import type { ExtensionRequest, ExtractionResponse } from "../shared/messages";

const MAXIMUM_HTML_SIZE = 3_000_000;

export async function monitorProduct(productId: string): Promise<Product> {
  const product = await getProduct(productId);
  if (!product) throw new Error("Produto não encontrado.");

  const capturedAt = new Date().toISOString();

  try {
    const extracted = await collectProduct(product);
    const observation: PriceObservation = {
      id: crypto.randomUUID(),
      productId: product.id,
      status: "success",
      priceCents: extracted.priceCents,
      capturedAt,
      source: extracted.source,
      detail: null,
    };

    const alert = evaluatePriceAlert(product, extracted.priceCents);
    const updated = await saveObservation(product, observation);

    if (alert && !(await hasNotification(alert.deduplicationKey))) {
      await sendPriceNotification(product, alert);
      await recordNotification({
        deduplicationKey: alert.deduplicationKey,
        productId: product.id,
        sentAt: capturedAt,
      });
    }

    return updated;
  } catch (error) {
    const observation: PriceObservation = {
      id: crypto.randomUUID(),
      productId: product.id,
      status: statusFromError(error),
      priceCents: null,
      capturedAt,
      source: "unknown",
      detail: safeErrorMessage(error),
    };
    return saveObservation(product, observation);
  }
}

async function collectProduct(product: Product) {
  const safeUrl = normalizeMercadoLivreProductUrl(product.url);
  const response = await fetch(safeUrl, {
    method: "GET",
    credentials: "omit",
    redirect: "follow",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new CollectionError(
      response.status === 403 || response.status === 429 ? "access_blocked" : "network_error",
      `A loja respondeu com o status ${response.status}.`,
    );
  }

  const responseUrl = normalizeMercadoLivreProductUrl(response.url);
  if (
    product.externalId !== null &&
    getMercadoLivreProductId(responseUrl) !== product.externalId
  ) {
    throw new CollectionError("invalid_response", "A loja redirecionou para outro produto.");
  }
  const contentLength = Number(response.headers.get("content-length") || "0");
  if (contentLength > MAXIMUM_HTML_SIZE) {
    throw new CollectionError("invalid_response", "A resposta excedeu o limite permitido.");
  }

  const html = await response.text();
  if (html.length > MAXIMUM_HTML_SIZE) {
    throw new CollectionError("invalid_response", "A resposta excedeu o limite permitido.");
  }

  await ensureOffscreenDocument();
  const request: ExtensionRequest = {
    type: "PARSE_MERCADO_LIVRE_HTML",
    payload: { html, url: responseUrl },
  };
  const result = (await chrome.runtime.sendMessage(request)) as ExtractionResponse;
  if (!result?.ok) {
    throw new CollectionError(
      isCollectionStatus(result?.code) ? result.code : "price_not_found",
      result?.error || "Falha ao interpretar a página.",
    );
  }
  return result.data;
}

let creatingOffscreenDocument: Promise<void> | null = null;

async function ensureOffscreenDocument(): Promise<void> {
  if (await chrome.offscreen.hasDocument()) return;
  if (!creatingOffscreenDocument) {
    creatingOffscreenDocument = chrome.offscreen
      .createDocument({
        url: "offscreen/offscreen.html",
        reasons: [chrome.offscreen.Reason.DOM_SCRAPING],
        justification: "Interpretar com segurança o HTML estático da página monitorada.",
      })
      .finally(() => {
        creatingOffscreenDocument = null;
      });
  }
  await creatingOffscreenDocument;
}

async function sendPriceNotification(
  product: Product,
  alert: ReturnType<typeof evaluatePriceAlert> & {},
): Promise<void> {
  const current = formatCurrency(alert.currentPriceCents);
  const message =
    alert.reason === "target_reached"
      ? `O preço chegou a ${current}, atingindo seu alvo.`
      : `O preço caiu ${alert.dropPercent?.toFixed(1)}% e agora está em ${current}.`;

  await chrome.notifications.create({
    type: "basic",
    iconUrl: chrome.runtime.getURL("icons/icon128.png"),
    title: product.name,
    message,
    contextMessage: "Argos · Mercado Livre",
  });
}

function formatCurrency(cents: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100);
}

function statusFromError(error: unknown): CollectionStatus {
  return error instanceof CollectionError ? error.status : "network_error";
}

function safeErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message.slice(0, 240);
  return "Falha inesperada durante a coleta.";
}

function isCollectionStatus(value: unknown): value is CollectionStatus {
  return (
    value === "success" ||
    value === "price_not_found" ||
    value === "product_unavailable" ||
    value === "access_blocked" ||
    value === "network_error" ||
    value === "invalid_response"
  );
}

class CollectionError extends Error {
  constructor(public readonly status: CollectionStatus, message: string) {
    super(message);
    this.name = "CollectionError";
  }
}
