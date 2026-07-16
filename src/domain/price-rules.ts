import type { Product } from "./product";

export type AlertReason = "target_reached" | "relevant_drop";

export interface PriceAlert {
  reason: AlertReason;
  previousPriceCents: number | null;
  currentPriceCents: number;
  dropPercent: number | null;
  deduplicationKey: string;
}

export function evaluatePriceAlert(
  product: Product,
  currentPriceCents: number,
): PriceAlert | null {
  if (!Number.isSafeInteger(currentPriceCents) || currentPriceCents <= 0) {
    return null;
  }

  if (currentPriceCents <= product.targetPriceCents) {
    return createAlert("target_reached", product, currentPriceCents, null);
  }

  if (product.lastPriceCents === null || currentPriceCents >= product.lastPriceCents) {
    return null;
  }

  const dropPercent =
    ((product.lastPriceCents - currentPriceCents) / product.lastPriceCents) * 100;

  if (dropPercent < product.alertDropPercent) {
    return null;
  }

  return createAlert("relevant_drop", product, currentPriceCents, dropPercent);
}

function createAlert(
  reason: AlertReason,
  product: Product,
  currentPriceCents: number,
  dropPercent: number | null,
): PriceAlert {
  return {
    reason,
    previousPriceCents: product.lastPriceCents,
    currentPriceCents,
    dropPercent,
    deduplicationKey: `${product.id}:${reason}:${currentPriceCents}`,
  };
}

