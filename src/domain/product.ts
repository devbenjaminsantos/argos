export const MAX_PRODUCTS = 3;

export type StoreId = "mercado-livre";
export type CheckIntervalHours = 12 | 24;

export interface Product {
  id: string;
  store: StoreId;
  externalId: string | null;
  url: string;
  name: string;
  targetPriceCents: number;
  alertDropPercent: number;
  checkIntervalHours: CheckIntervalHours;
  createdAt: string;
  updatedAt: string;
  lastCheckedAt: string | null;
  nextCheckAt: string;
  lastPriceCents: number | null;
}

export type CollectionStatus =
  | "success"
  | "price_not_found"
  | "product_unavailable"
  | "access_blocked"
  | "network_error"
  | "invalid_response";

export interface PriceObservation {
  id: string;
  productId: string;
  status: CollectionStatus;
  priceCents: number | null;
  capturedAt: string;
  source: "json-ld" | "meta" | "visible-dom" | "unknown";
  detail: string | null;
}

export interface ExtractedProduct {
  store: StoreId;
  externalId: string | null;
  url: string;
  title: string;
  priceCents: number;
  source: PriceObservation["source"];
}

export interface NewProductInput {
  url: string;
  name: string;
  targetPriceCents: number;
  alertDropPercent: number;
  checkIntervalHours: CheckIntervalHours;
  initialExtraction: ExtractedProduct;
}

