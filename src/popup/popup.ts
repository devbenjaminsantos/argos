import { MAX_PRODUCTS, type CheckIntervalHours, type ExtractedProduct, type Product } from "../domain/product";
import type { ExtensionRequest, ExtensionResponse, ExtractionResponse, ProductListResponse } from "../shared/messages";

const elements = {
  count: requireElement<HTMLElement>("product-count"),
  status: requireElement<HTMLElement>("status"),
  captureSection: requireElement<HTMLElement>("capture-section"),
  capturedTitle: requireElement<HTMLElement>("captured-title"),
  capturedPrice: requireElement<HTMLElement>("captured-price"),
  form: requireElement<HTMLFormElement>("product-form"),
  name: requireElement<HTMLInputElement>("name"),
  targetPrice: requireElement<HTMLInputElement>("target-price"),
  dropPercent: requireElement<HTMLInputElement>("drop-percent"),
  interval: requireElement<HTMLSelectElement>("interval"),
  productList: requireElement<HTMLElement>("product-list"),
};

let currentExtraction: ExtractedProduct | null = null;

elements.form.addEventListener("submit", (event) => void submitProduct(event));
void initialize();

async function initialize(): Promise<void> {
  await refreshProducts();
  await inspectActivePage();
}

async function inspectActivePage(): Promise<void> {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) throw new Error("Abra uma página de produto do Mercado Livre.");

    const request: ExtensionRequest = { type: "EXTRACT_CURRENT_PAGE" };
    const response = (await chrome.tabs.sendMessage(tab.id, request)) as ExtractionResponse;
    if (!response?.ok) throw new Error(response?.error || "Não foi possível ler esta página.");

    currentExtraction = response.data;
    elements.capturedTitle.textContent = response.data.title;
    elements.capturedPrice.textContent = formatCurrency(response.data.priceCents);
    elements.name.value = response.data.title.slice(0, 80);
    elements.captureSection.hidden = false;
  } catch {
    elements.captureSection.hidden = true;
    showStatus("Abra um produto do Mercado Livre para adicioná-lo ao Argos.", "info");
  }
}

async function submitProduct(event: SubmitEvent): Promise<void> {
  event.preventDefault();
  if (!currentExtraction) return;

  const submitButton = elements.form.querySelector<HTMLButtonElement>('button[type="submit"]');
  if (submitButton) submitButton.disabled = true;

  try {
    const targetPriceCents = parseBrazilianCurrency(elements.targetPrice.value);
    const alertDropPercent = Number(elements.dropPercent.value);
    const checkIntervalHours = Number(elements.interval.value) as CheckIntervalHours;
    const request: ExtensionRequest = {
      type: "ADD_PRODUCT",
      payload: {
        url: currentExtraction.url,
        name: elements.name.value,
        targetPriceCents,
        alertDropPercent,
        checkIntervalHours,
        initialExtraction: currentExtraction,
      },
    };

    const response = (await chrome.runtime.sendMessage(request)) as ExtensionResponse<Product>;
    if (!response.ok) throw new Error(response.error);

    showStatus("Produto adicionado ao monitoramento.", "success");
    elements.captureSection.hidden = true;
    await refreshProducts();
  } catch (error) {
    showStatus(error instanceof Error ? error.message : "Não foi possível adicionar o produto.", "error");
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

async function refreshProducts(): Promise<void> {
  const request: ExtensionRequest = { type: "LIST_PRODUCTS" };
  const response = (await chrome.runtime.sendMessage(request)) as ProductListResponse;
  if (!response.ok) {
    showStatus(response.error, "error");
    return;
  }

  elements.count.textContent = `${response.data.length}/${MAX_PRODUCTS}`;
  renderProducts(response.data);
}

function renderProducts(products: Product[]): void {
  elements.productList.replaceChildren();
  if (products.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Nenhum produto monitorado ainda.";
    elements.productList.append(empty);
    return;
  }

  for (const product of products) {
    const card = document.createElement("article");
    card.className = "product-card";

    const name = document.createElement("strong");
    name.textContent = product.name;

    const interval = document.createElement("span");
    interval.className = "label";
    interval.textContent = `${product.checkIntervalHours}h`;

    const prices = document.createElement("div");
    prices.className = "product-prices";
    prices.append(
      priceLabel("Atual", product.lastPriceCents),
      priceLabel("Alvo", product.targetPriceCents),
    );

    const actions = document.createElement("div");
    actions.className = "product-actions";
    actions.append(
      actionButton("Verificar agora", "secondary-button", () => checkNow(product.id)),
      actionButton("Remover", "danger-button", () => remove(product.id)),
    );

    card.append(name, interval, prices, actions);
    elements.productList.append(card);
  }
}

function priceLabel(label: string, cents: number | null): HTMLElement {
  const span = document.createElement("span");
  const bold = document.createElement("b");
  bold.textContent = cents === null ? "—" : formatCurrency(cents);
  span.append(`${label}: `, bold);
  return span;
}

function actionButton(label: string, className: string, action: () => Promise<void>): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", () => {
    button.disabled = true;
    void action().finally(() => {
      button.disabled = false;
    });
  });
  return button;
}

async function checkNow(productId: string): Promise<void> {
  showStatus("Verificando o produto…", "info");
  const request: ExtensionRequest = { type: "CHECK_PRODUCT_NOW", payload: { productId } };
  const response = (await chrome.runtime.sendMessage(request)) as ExtensionResponse<Product>;
  if (!response.ok) {
    showStatus(response.error, "error");
    return;
  }
  showStatus("Verificação concluída.", "success");
  await refreshProducts();
}

async function remove(productId: string): Promise<void> {
  const request: ExtensionRequest = { type: "REMOVE_PRODUCT", payload: { productId } };
  const response = (await chrome.runtime.sendMessage(request)) as ExtensionResponse<null>;
  if (!response.ok) {
    showStatus(response.error, "error");
    return;
  }
  showStatus("Produto removido.", "success");
  await refreshProducts();
}

function parseBrazilianCurrency(value: string): number {
  const normalized = value.trim().replace(/\s|R\$/gi, "").replace(/\./g, "").replace(",", ".");
  const cents = Math.round(Number(normalized) * 100);
  if (!Number.isSafeInteger(cents) || cents <= 0) throw new Error("Informe um preço-alvo válido.");
  return cents;
}

function formatCurrency(cents: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100);
}

function showStatus(message: string, type: "info" | "success" | "error"): void {
  elements.status.textContent = message;
  elements.status.className = `status visible ${type}`;
}

function requireElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Elemento ausente: ${id}`);
  return element as T;
}

