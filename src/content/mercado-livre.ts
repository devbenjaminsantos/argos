import { extractMercadoLivreProduct } from "../stores/mercado-livre/extractor";
import type { ExtensionRequest, ExtractionResponse } from "../shared/messages";

chrome.runtime.onMessage.addListener(
  (message: unknown, sender, sendResponse: (response: ExtractionResponse) => void) => {
    if (sender.id !== chrome.runtime.id) return false;
    if (!isExtractionRequest(message)) return false;

    try {
      sendResponse({ ok: true, data: extractMercadoLivreProduct(document, location.href) });
    } catch (error) {
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : "Não foi possível ler esta página.",
      });
    }
    return false;
  },
);

function isExtractionRequest(message: unknown): message is Extract<ExtensionRequest, { type: "EXTRACT_CURRENT_PAGE" }> {
  return (
    typeof message === "object" &&
    message !== null &&
    "type" in message &&
    message.type === "EXTRACT_CURRENT_PAGE"
  );
}

