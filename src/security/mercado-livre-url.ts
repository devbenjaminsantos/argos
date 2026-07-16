const ALLOWED_ROOT_DOMAIN = "mercadolivre.com.br";
const PRODUCT_PATH_PATTERNS = [/\/MLB-\d+/i, /\/p\/MLB\d+/i];
const TRACKING_PARAMETERS = [
  "matt_tool",
  "matt_word",
  "matt_source",
  "matt_campaign",
  "matt_ad_group",
  "matt_match_type",
  "matt_network",
  "matt_device",
  "matt_creative",
  "matt_keyword",
  "gclid",
  "fbclid",
];

export class UnsafeProductUrlError extends Error {
  constructor(message = "A URL não é uma página de produto válida do Mercado Livre.") {
    super(message);
    this.name = "UnsafeProductUrlError";
  }
}

export function normalizeMercadoLivreProductUrl(rawUrl: string): string {
  let url: URL;

  try {
    url = new URL(rawUrl);
  } catch {
    throw new UnsafeProductUrlError();
  }

  const hostname = url.hostname.toLowerCase();
  const allowedHost =
    hostname === ALLOWED_ROOT_DOMAIN || hostname.endsWith(`.${ALLOWED_ROOT_DOMAIN}`);

  if (
    url.protocol !== "https:" ||
    !allowedHost ||
    (url.port !== "" && url.port !== "443") ||
    url.username !== "" ||
    url.password !== "" ||
    !PRODUCT_PATH_PATTERNS.some((pattern) => pattern.test(url.pathname))
  ) {
    throw new UnsafeProductUrlError();
  }

  url.hash = "";
  for (const key of [...url.searchParams.keys()]) {
    if (key.toLowerCase().startsWith("utm_") || TRACKING_PARAMETERS.includes(key.toLowerCase())) {
      url.searchParams.delete(key);
    }
  }

  return url.toString();
}

export function getMercadoLivreProductId(url: string): string | null {
  const match = url.match(/(?:\/MLB-|\/p\/MLB)(\d+)/i);
  return match ? `MLB${match[1]}` : null;
}

