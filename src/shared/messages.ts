import type { ExtractedProduct, NewProductInput, Product } from "../domain/product";

export type ExtensionRequest =
  | { type: "EXTRACT_CURRENT_PAGE" }
  | { type: "LIST_PRODUCTS" }
  | { type: "ADD_PRODUCT"; payload: NewProductInput }
  | { type: "REMOVE_PRODUCT"; payload: { productId: string } }
  | { type: "CHECK_PRODUCT_NOW"; payload: { productId: string } }
  | { type: "PARSE_MERCADO_LIVRE_HTML"; payload: { html: string; url: string } };

export type ExtensionResponse<T = unknown> =
  | { ok: true; data: T }
  | { ok: false; error: string; code?: string };

export type ExtractionResponse = ExtensionResponse<ExtractedProduct>;
export type ProductListResponse = ExtensionResponse<Product[]>;

export function isExtensionRequest(value: unknown): value is ExtensionRequest {
  if (!isRecord(value) || typeof value.type !== "string") return false;

  switch (value.type) {
    case "EXTRACT_CURRENT_PAGE":
    case "LIST_PRODUCTS":
      return true;
    case "ADD_PRODUCT":
      return isNewProductInput(value.payload);
    case "REMOVE_PRODUCT":
    case "CHECK_PRODUCT_NOW":
      return isRecord(value.payload) && typeof value.payload.productId === "string";
    case "PARSE_MERCADO_LIVRE_HTML":
      return (
        isRecord(value.payload) &&
        typeof value.payload.html === "string" &&
        typeof value.payload.url === "string"
      );
    default:
      return false;
  }
}

function isNewProductInput(value: unknown): value is NewProductInput {
  if (!isRecord(value) || !isRecord(value.initialExtraction)) return false;
  return (
    typeof value.url === "string" &&
    typeof value.name === "string" &&
    typeof value.targetPriceCents === "number" &&
    typeof value.alertDropPercent === "number" &&
    (value.checkIntervalHours === 12 || value.checkIntervalHours === 24) &&
    value.initialExtraction.store === "mercado-livre" &&
    typeof value.initialExtraction.url === "string" &&
    typeof value.initialExtraction.title === "string" &&
    typeof value.initialExtraction.priceCents === "number"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
