// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { observeMercadoLivrePage } from "../src/stores/mercado-livre/contextual-observation";
import { isExtensionRequest } from "../src/shared/messages";
const url = "https://www.mercadolivre.com.br/item/p/MLB123456?token=secret";
function price(amount = "180", cents = "00", symbol = "R$") {
  return `<span class="andes-money-amount"><span class="andes-money-amount__currency-symbol">${symbol}</span><span class="andes-money-amount__fraction">${amount}</span><span class="andes-money-amount__cents">${cents}</span></span>`;
}
function page(content: string) {
  return new DOMParser().parseFromString(`<div class="ui-pdp-price"><div class="ui-pdp-price__second-line">${content}</div></div>`, "text/html");
}
describe("local contextual observation", () => {
  it("keeps the observation command in the shared message contract", () => {
    expect(isExtensionRequest({ type: "OBSERVE_CURRENT_PAGE" })).toBe(true);
    expect(isExtensionRequest({ type: "OBSERVE_UNKNOWN_PAGE" })).toBe(false);
  });

  it("accepts a catalog MLBU page without exporting its URL", () => {
    const result = observeMercadoLivrePage(
      page(price()),
      "https://www.mercadolivre.com.br/caneca/up/MLBU1977786059?tracking=private",
    );
    expect(result.externalId).toBe("MLBU1977786059");
    expect(JSON.stringify(result)).not.toContain("mercadolivre.com.br");
  });
  it("keeps eligibility unknown despite Pix and coupon mentions and never exports page/session data", () => {
    const doc = page(price() + "Pix cupom");
    doc.body.insertAdjacentHTML("beforeend", '<script>window.token="secret"</script><input value="private">');
    const result = observeMercadoLivrePage(doc, url);
    expect(result).toMatchObject({ priceCents: 18000, eligibility: "unknown", accessContext: "unknown", personalization: "unknown", shippingCents: null, variantId: null, conditions: { payment: "pix", coupon: "mentioned" } });
    expect(JSON.stringify(result)).not.toMatch(/secret|private|<script|https:/);
  });
  it("does not use JSON-LD as evidence of the displayed price", () => {
    const doc = page(price());
    doc.head.innerHTML = '<script type="application/ld+json">{"@type":"Product","offers":{"price":1}}</script>';
    expect(observeMercadoLivrePage(doc, url).priceCents).toBe(18000);
  });
  it("rejects conflicting visible offers", () => {
    expect(() => observeMercadoLivrePage(page(price() + price("200")), url)).toThrow("preços diferentes");
  });
  it("ignores explicitly hidden offers and crossed-out prices", () => {
    expect(observeMercadoLivrePage(page(price() + `<del>${price("300")}</del><span hidden>${price("400")}</span>`), url).priceCents).toBe(18000);
  });
  it.each([price("0"), price("1", "999"), price("12x"), price("100", "00", "US$")])("fails closed for invalid money %s", (html) => {
    expect(() => observeMercadoLivrePage(page(html), url)).toThrow();
  });
  it("rejects unsupported URL, missing price and challenge", () => {
    expect(() => observeMercadoLivrePage(page(price()), "https://evil.example/p/MLB123456")).toThrow();
    expect(() => observeMercadoLivrePage(page(""), url)).toThrow();
    const doc = page(price()); doc.title = "Captcha";
    expect(() => observeMercadoLivrePage(doc, url)).toThrow("intervenção");
  });
});
