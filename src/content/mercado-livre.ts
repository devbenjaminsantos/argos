import { extractMercadoLivreProduct } from "../stores/mercado-livre/extractor";
import { isExtensionRequest, type ExtensionRequest, type ExtractionResponse } from "../shared/messages";
import { observeMercadoLivrePage, type ContextualObservation } from "../stores/mercado-livre/contextual-observation";
import type { ExtensionResponse } from "../shared/messages";

chrome.runtime.onMessage.addListener(
  (message: unknown, sender, sendResponse: (response: ExtractionResponse | ExtensionResponse<ContextualObservation>) => void) => {
    if (sender.id !== chrome.runtime.id) return false;
    if (!isExtensionRequest(message)) return false;
    if (message.type === "OBSERVE_CURRENT_PAGE") {
      if (sender.url !== chrome.runtime.getURL("popup/popup.html")) return false;
      try {
        sendResponse({ ok: true, data: observeMercadoLivrePage(document, location.href) });
      } catch (error) {
        sendResponse({ ok: false, error: error instanceof Error ? error.message : "Não foi possível observar a oferta." });
      }
      return false;
    }
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
  return isExtensionRequest(message) && message.type === "EXTRACT_CURRENT_PAGE";
}
