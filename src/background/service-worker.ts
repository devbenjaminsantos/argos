import { validateNewProductInput } from "../application/product-input";
import { monitorProduct } from "../application/monitor-product";
import {
  addProduct,
  listProducts,
  removeProduct,
} from "../infrastructure/database/argos-repository";
import { isExtensionRequest, type ExtensionResponse } from "../shared/messages";

const MONITORING_ALARM = "argos-monitoring";

chrome.runtime.onInstalled.addListener(() => {
  void ensureMonitoringAlarm();
});

chrome.runtime.onStartup.addListener(() => {
  void ensureMonitoringAlarm();
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === MONITORING_ALARM) void checkDueProducts();
});

chrome.runtime.onMessage.addListener(
  (message: unknown, sender, sendResponse: (response: ExtensionResponse) => void) => {
    if (sender.id !== chrome.runtime.id || !isExtensionRequest(message)) return false;
    if (message.type === "EXTRACT_CURRENT_PAGE" || message.type === "PARSE_MERCADO_LIVRE_HTML") {
      return false;
    }

    if (sender.tab) {
      sendResponse({ ok: false, error: "Origem da solicitação não autorizada." });
      return false;
    }

    void handleRequest(message)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((error: unknown) =>
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : "Não foi possível concluir a operação.",
        }),
      );
    return true;
  },
);

async function handleRequest(message: Exclude<ReturnTypeMessage, { type: "EXTRACT_CURRENT_PAGE" | "PARSE_MERCADO_LIVRE_HTML" }>) {
  switch (message.type) {
    case "LIST_PRODUCTS":
      return listProducts();
    case "ADD_PRODUCT":
      return addProduct(validateNewProductInput(message.payload));
    case "REMOVE_PRODUCT":
      await removeProduct(message.payload.productId);
      return null;
    case "CHECK_PRODUCT_NOW":
      return monitorProduct(message.payload.productId);
  }
}

type ReturnTypeMessage = Parameters<typeof isExtensionRequest>[0] extends never
  ? never
  : import("../shared/messages").ExtensionRequest;

async function ensureMonitoringAlarm(): Promise<void> {
  if (!(await chrome.alarms.get(MONITORING_ALARM))) {
    await chrome.alarms.create(MONITORING_ALARM, { periodInMinutes: 30 });
  }
}

async function checkDueProducts(): Promise<void> {
  const now = Date.now();
  const products = await listProducts();
  for (const product of products) {
    if (Date.parse(product.nextCheckAt) <= now) await monitorProduct(product.id);
  }
}
