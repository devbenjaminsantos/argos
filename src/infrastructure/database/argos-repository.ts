import { MAX_PRODUCTS, type NewProductInput, type PriceObservation, type Product } from "../../domain/product";

const DATABASE_NAME = "argos";
const DATABASE_VERSION = 1;
const PRODUCTS = "products";
const OBSERVATIONS = "priceObservations";
const NOTIFICATIONS = "notificationDeliveries";

interface NotificationDelivery {
  deduplicationKey: string;
  productId: string;
  sentAt: string;
}

export async function listProducts(): Promise<Product[]> {
  const db = await openDatabase();
  return requestToPromise(db.transaction(PRODUCTS).objectStore(PRODUCTS).getAll());
}

export async function getProduct(productId: string): Promise<Product | null> {
  const db = await openDatabase();
  const result = await requestToPromise<Product | undefined>(
    db.transaction(PRODUCTS).objectStore(PRODUCTS).get(productId),
  );
  return result ?? null;
}

export async function addProduct(input: NewProductInput): Promise<Product> {
  const db = await openDatabase();
  const transaction = db.transaction([PRODUCTS, OBSERVATIONS], "readwrite");
  const products = transaction.objectStore(PRODUCTS);
  const count = await requestToPromise(products.count());

  if (count >= MAX_PRODUCTS) {
    transaction.abort();
    throw new Error(`O limite de ${MAX_PRODUCTS} produtos foi atingido.`);
  }

  const existing = await requestToPromise<Product[]>(
    products.index("byUrl").getAll(input.initialExtraction.url),
  );
  if (existing.length > 0) {
    transaction.abort();
    throw new Error("Este produto já está sendo monitorado.");
  }

  const now = new Date();
  const product: Product = {
    id: crypto.randomUUID(),
    store: "mercado-livre",
    externalId: input.initialExtraction.externalId,
    url: input.initialExtraction.url,
    name: input.name.trim().slice(0, 80),
    targetPriceCents: input.targetPriceCents,
    alertDropPercent: input.alertDropPercent,
    checkIntervalHours: input.checkIntervalHours,
    createdAt: now.toISOString(),
    updatedAt: now.toISOString(),
    lastCheckedAt: now.toISOString(),
    nextCheckAt: addHours(now, input.checkIntervalHours).toISOString(),
    lastPriceCents: input.initialExtraction.priceCents,
  };

  products.add(product);
  transaction.objectStore(OBSERVATIONS).add({
    id: crypto.randomUUID(),
    productId: product.id,
    status: "success",
    priceCents: input.initialExtraction.priceCents,
    capturedAt: now.toISOString(),
    source: input.initialExtraction.source,
    detail: "Coleta realizada durante o cadastro.",
  } satisfies PriceObservation);

  await transactionDone(transaction);
  return product;
}

export async function removeProduct(productId: string): Promise<void> {
  const db = await openDatabase();
  const transaction = db.transaction([PRODUCTS, OBSERVATIONS, NOTIFICATIONS], "readwrite");
  transaction.objectStore(PRODUCTS).delete(productId);
  await deleteByIndex(transaction.objectStore(OBSERVATIONS).index("byProduct"), productId);
  await deleteByIndex(transaction.objectStore(NOTIFICATIONS).index("byProduct"), productId);
  await transactionDone(transaction);
}

export async function saveObservation(
  product: Product,
  observation: PriceObservation,
): Promise<Product> {
  const db = await openDatabase();
  const transaction = db.transaction([PRODUCTS, OBSERVATIONS], "readwrite");
  const checkedAt = new Date(observation.capturedAt);
  const updated: Product = {
    ...product,
    updatedAt: observation.capturedAt,
    lastCheckedAt: observation.capturedAt,
    nextCheckAt: addHours(checkedAt, product.checkIntervalHours).toISOString(),
    lastPriceCents:
      observation.status === "success" && observation.priceCents !== null
        ? observation.priceCents
        : product.lastPriceCents,
  };

  transaction.objectStore(OBSERVATIONS).add(observation);
  transaction.objectStore(PRODUCTS).put(updated);
  await transactionDone(transaction);
  return updated;
}

export async function hasNotification(deduplicationKey: string): Promise<boolean> {
  const db = await openDatabase();
  const result = await requestToPromise(
    db.transaction(NOTIFICATIONS).objectStore(NOTIFICATIONS).getKey(deduplicationKey),
  );
  return result !== undefined;
}

export async function recordNotification(delivery: NotificationDelivery): Promise<void> {
  const db = await openDatabase();
  const transaction = db.transaction(NOTIFICATIONS, "readwrite");
  transaction.objectStore(NOTIFICATIONS).add(delivery);
  await transactionDone(transaction);
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = () => {
      const db = request.result;
      const products = db.createObjectStore(PRODUCTS, { keyPath: "id" });
      products.createIndex("byUrl", "url", { unique: true });

      const observations = db.createObjectStore(OBSERVATIONS, { keyPath: "id" });
      observations.createIndex("byProduct", "productId");
      observations.createIndex("byCapturedAt", "capturedAt");

      const notifications = db.createObjectStore(NOTIFICATIONS, {
        keyPath: "deduplicationKey",
      });
      notifications.createIndex("byProduct", "productId");
    };
  });
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error ?? new Error("Transação cancelada."));
  });
}

async function deleteByIndex(index: IDBIndex, key: IDBValidKey): Promise<void> {
  const keys = await requestToPromise(index.getAllKeys(key));
  for (const primaryKey of keys) index.objectStore.delete(primaryKey);
}

function addHours(date: Date, hours: number): Date {
  return new Date(date.getTime() + hours * 60 * 60 * 1_000);
}

