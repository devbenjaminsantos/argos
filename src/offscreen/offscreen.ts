import { normalizeMercadoLivreProductUrl } from "../security/mercado-livre-url";
import type { ExtensionRequest, ExtractionResponse } from "../shared/messages";
import {
  extractMercadoLivreProduct,
  ProductExtractionError,
} from "../stores/mercado-livre/extractor";

chrome.runtime.onMessage.addListener(
  (message: unknown, sender, sendResponse: (response: ExtractionResponse) => void) => {
    if (sender.id !== chrome.runtime.id || sender.tab) return false;
    if (!isParseRequest(message)) return false;

    try {
      const url = normalizeMercadoLivreProductUrl(message.payload.url);
      const document = new DOMParser().parseFromString(message.payload.html, "text/html");
      sendResponse({ ok: true, data: extractMercadoLivreProduct(document, url) });
    } catch (error) {
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : "Não foi possível interpretar a página.",
        ...(error instanceof ProductExtractionError ? { code: error.code } : {}),
      });
    }
    return false;
  },
);

function isParseRequest(
  message: unknown,
): message is Extract<ExtensionRequest, { type: "PARSE_MERCADO_LIVRE_HTML" }> {
  return (
    typeof message === "object" &&
    message !== null &&
    "type" in message &&
    message.type === "PARSE_MERCADO_LIVRE_HTML" &&
    "payload" in message &&
    typeof message.payload === "object" &&
    message.payload !== null &&
    "html" in message.payload &&
    typeof message.payload.html === "string" &&
    message.payload.html.length <= 3_000_000 &&
    "url" in message.payload &&
    typeof message.payload.url === "string"
  );
}
