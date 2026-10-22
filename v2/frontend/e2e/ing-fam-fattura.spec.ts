/**
 * ING-FAM — Fattura PDF na tela do pedido confirmado.
 * SKU interno ≠ código de barras. Prepare fresco; não misturar com cat-pim.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { loginAs } from "./helpers/orderCreate";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const fatturaPdf = path.resolve(
  __dirname,
  "../../tests/fixtures/ingestion/corpus_202/Fattura_202.pdf",
);
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-ing-fam/screenshots");

type Json = Record<string, unknown>;

async function api(
  page: import("@playwright/test").Page,
  method: string,
  pathName: string,
  body?: unknown,
): Promise<{ status: number; body: Json }> {
  return page.evaluate(
    async ({ method, pathName, body }) => {
      const opts: RequestInit = { method, credentials: "include" };
      if (body !== undefined) {
        opts.headers = { "Content-Type": "application/json" };
        opts.body = JSON.stringify(body);
      }
      const r = await fetch(pathName, opts);
      const text = await r.text();
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        /* raw */
      }
      return { status: r.status, body: parsed as Json };
    },
    { method, pathName, body },
  );
}

function expectOk(status: number) {
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThan(300);
}

const EANS: { ean: string; desc: string }[] = [
  { ean: "8057628950936", desc: "WASH BAG REBEL - PURPLE" },
  { ean: "8057628953104", desc: "WASH BAG FIERCE" },
  { ean: "8057628954194", desc: "WASH BAG SHOW - LIGHT BLUE" },
  { ean: "8057628953814", desc: "WASH BAG STARLIGHT - RED" },
  { ean: "8057628955191", desc: "THUNDER ARION" },
  { ean: "8057628955207", desc: "GRAVITY ARION" },
  { ean: "8057628955214", desc: "WASH BAG ARION" },
];

test("Fattura PDF na comercial cria fatura em rascunho", async ({ page }) => {
  test.skip(!fs.existsSync(fatturaPdf), "Fattura_202.pdf missing");
  test.setTimeout(180_000);
  fs.mkdirSync(shotDir, { recursive: true });
  await page.setViewportSize({ width: 1366, height: 900 });
  await loginAs(page);

  const tag = Date.now().toString(36);
  let r = await api(page, "POST", "/api/suppliers", {
    name: `Heroe's Srl FAM ${tag}`,
    country_code: "IT",
  });
  expectOk(r.status);
  const supplierId = (r.body as Json & { id: number }).id;

  const productIds: number[] = [];
  const catalogSkus: string[] = [];
  for (let i = 0; i < EANS.length; i++) {
    const sku = `CAT-F-${tag}-${i + 1}`;
    expect(sku).not.toMatch(/^\d{8,14}$/);
    r = await api(page, "POST", "/api/products", {
      sku,
      description: EANS[i].desc,
    });
    expectOk(r.status);
    const product = r.body as Json & { id: number };
    r = await api(page, "PATCH", `/api/products/${product.id}`, { ean: EANS[i].ean });
    expectOk(r.status);
    productIds.push(product.id);
    catalogSkus.push(sku);
  }

  r = await api(page, "POST", "/api/orders", {
    code: `ORD-FAM-${tag}`,
    supplier_id: supplierId,
    currency: "EUR",
  });
  expectOk(r.status);
  let order = r.body as Json & { id: number; version: number };
  for (const pid of productIds) {
    r = await api(page, "POST", `/api/orders/${order.id}/items`, {
      expected_version: order.version,
      product_id: pid,
      quantity: "1000",
      unit_price: "10",
      unit: "PZ",
    });
    expectOk(r.status);
    order = r.body as typeof order;
  }
  r = await api(page, "POST", `/api/orders/${order.id}/confirm`, {
    expected_version: order.version,
  });
  expectOk(r.status);

  await page.goto(`/orders/${order.id}/commercial`);
  await expect(page.getByTestId("order-invoices")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("order-fattura-pdf-panel")).toBeVisible();
  await page.getByTestId("order-fattura-upload").setInputFiles(fatturaPdf);
  await expect(page.getByTestId("order-fattura-ready")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("order-fattura-number")).toContainText("202");
  await expect(page.getByTestId("order-fattura-lines")).toContainText("Código de barras");
  await expect(page.getByTestId("order-fattura-import")).toBeEnabled();
  await page.screenshot({ path: path.join(shotDir, "01-fattura-na-comercial.png"), fullPage: true });
  await page.getByTestId("order-fattura-import").click();
  await expect(page.getByTestId("invoice-items-table")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("body")).toContainText("202");
  const table = page.getByTestId("invoice-items-table");
  await expect(table).toContainText(catalogSkus[0]);
  await expect(table).not.toContainText("8057628955191");
  const divergence = page.getByTestId("invoice-price-divergence");
  await expect(divergence).toBeVisible();
  await expect(divergence).toContainText(/código de barras/i);
  await expect(divergence).not.toContainText("SKU 8057628955191");
  await expect(divergence).not.toContainText("IR doc");
  await expect(divergence).not.toContainText("policy=");
  await page.screenshot({ path: path.join(shotDir, "02-fatura-rascunho.png"), fullPage: true });
});
