/**
 * I5-1 E2E — ImportProcess via UI (criação não via API).
 * Seed invoices/shipments via fetch autenticado no browser; processo por cliques.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-j5/screenshots");

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

test("I5-1 customs UI journey", async ({ page }) => {
  test.setTimeout(180_000);
  fs.mkdirSync(shotDir, { recursive: true });

  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  const tag = Date.now().toString(36);

  let r = await api(page, "POST", "/api/suppliers", { name: `Sup ${tag}`, country_code: "IT" });
  expectOk(r.status);
  const supplier = r.body;
  r = await api(page, "POST", "/api/products", { sku: `SKU-${tag}`, description: "P" });
  expectOk(r.status);
  const product = r.body;
  r = await api(page, "POST", "/api/orders", {
    code: `ORD-${tag}`,
    supplier_id: supplier.id,
    currency: "EUR",
  });
  expectOk(r.status);
  let order = r.body as Json & { items?: Json[]; version: number; id: number };
  r = await api(page, "POST", `/api/orders/${order.id}/items`, {
    expected_version: order.version,
    product_id: product.id,
    quantity: "20",
    unit_price: "10",
  });
  expectOk(r.status);
  order = r.body as typeof order;
  r = await api(page, "POST", `/api/orders/${order.id}/confirm`, { expected_version: order.version });
  expectOk(r.status);
  order = r.body as typeof order;
  const orderItemId = (order.items as Json[])[0].id;

  async function issuedInvoice(number: string) {
    let invR = await api(page, "POST", `/api/orders/${order.id}/invoices`, {
      invoice_number: number,
      invoice_type: "FINAL",
    });
    expectOk(invR.status);
    let inv = invR.body as Json & { id: number; version: number; items: Json[] };
    invR = await api(page, "PUT", `/api/invoices/${inv.id}/items`, {
      expected_version: inv.version,
      items: [
        {
          order_item_id: orderItemId,
          quantity: "10",
          unit_price_gross: "10",
          discount_type: "PERCENT",
          discount_percent: "0",
        },
      ],
    });
    expectOk(invR.status);
    inv = invR.body as typeof inv;
    const today = new Date().toISOString().slice(0, 10);
    invR = await api(page, "PUT", `/api/invoices/${inv.id}/terms`, {
      expected_version: inv.version,
      mode: "PERCENT",
      terms: [{ due_date: today, percent: "100" }],
    });
    expectOk(invR.status);
    inv = invR.body as typeof inv;

    const docStatus = await page.evaluate(async (invoiceId) => {
      const form = new FormData();
      form.append("file", new Blob(["%PDF-1.4 x"], { type: "application/pdf" }), "f.pdf");
      form.append("entity_type", "invoice");
      form.append("entity_id", String(invoiceId));
      form.append("role", "official");
      const res = await fetch("/api/documents", { method: "POST", credentials: "include", body: form });
      return res.status;
    }, inv.id);
    expect(docStatus).toBe(200);

    invR = await api(page, "GET", `/api/invoices/${inv.id}`);
    expectOk(invR.status);
    inv = invR.body as typeof inv;
    invR = await api(page, "POST", `/api/invoices/${inv.id}/issue`, {
      expected_version: inv.version,
    });
    expectOk(invR.status);
    return invR.body as typeof inv;
  }

  const inv1 = await issuedInvoice(`E2E-${tag}-1`);
  const inv2 = await issuedInvoice(`E2E-${tag}-2`);

  r = await api(page, "POST", "/api/logistics-providers", {
    legal_name: `Carrier ${tag}`,
    provider_type: "TRANSPORTADOR",
    active: true,
  });
  expectOk(r.status);
  const provider = r.body;

  async function shipment(qty: string) {
    let shR = await api(page, "POST", "/api/shipments", {
      modal: "SEA",
      logistics_provider_id: provider.id,
    });
    expectOk(shR.status);
    let sh = shR.body as Json & { id: number; version: number; items: Json[] };
    shR = await api(page, "POST", `/api/shipments/${sh.id}/items`, {
      expected_version: sh.version,
      order_item_id: orderItemId,
      quantity: qty,
    });
    expectOk(shR.status);
    return shR.body as typeof sh;
  }

  const sh1 = await shipment("4");
  const sh2 = await shipment("4");

  await page.setViewportSize({ width: 1366, height: 900 });
  await page.goto("/customs");
  await page.getByTestId("customs-new-link").click();
  await page.getByTestId("customs-external-ref").fill(`DUIMP-${tag}`);
  await page.getByTestId("customs-create-submit").click();
  await page.waitForURL(/\/customs\/\d+/);
  await page.screenshot({ path: path.join(shotDir, "i5-1-detail-created-1366.png"), fullPage: true });

  await page.getByTestId("customs-link-invoice-id").fill(String(inv1.id));
  await page.getByTestId("customs-link-invoice").click();
  await expect(page.getByTestId("customs-invoice-list")).toContainText(String(inv1.id));

  await page.getByTestId("customs-link-invoice-id").fill(String(inv2.id));
  await page.getByTestId("customs-link-invoice").click();
  await expect(page.getByTestId("customs-invoice-list")).toContainText(String(inv2.id));

  await page.getByTestId("customs-link-shipment-id").fill(String(sh1.id));
  await page.getByTestId("customs-link-shipment").click();
  await expect(page.getByTestId("customs-shipment-list")).toContainText(String(sh1.id));

  await page.getByTestId("customs-link-shipment-id").fill(String(sh2.id));
  await page.getByTestId("customs-link-shipment").click();
  await expect(page.getByTestId("customs-shipment-list")).toContainText(String(sh2.id));

  await page.getByTestId("customs-alloc-inv-item").fill(String((inv1.items[0] as Json).id));
  await page.getByTestId("customs-alloc-inv-qty").fill("3");
  await page.getByTestId("customs-alloc-inv").click();
  await expect(page.getByTestId("customs-inv-residuals")).toContainText("3");

  await page.getByTestId("customs-alloc-shp-item").fill(String((sh1.items[0] as Json).id));
  await page.getByTestId("customs-alloc-shp-qty").fill("2");
  await page.getByTestId("customs-alloc-shp").click();
  await expect(page.getByTestId("customs-shp-residuals")).toContainText("2");

  await page.reload();
  await expect(page.getByTestId("customs-invoice-list")).toContainText(String(inv1.id));
  await expect(page.getByTestId("customs-shipment-list")).toContainText(String(sh2.id));

  await page.getByTestId("customs-submit").click();
  await expect(page.getByTestId("status-badge")).toHaveAttribute("data-status", "SUBMITTED");
  await expect(page.getByTestId("customs-link-invoice")).toHaveCount(0);

  await page.goto("/customs");
  await expect(page.getByTestId("customs-list-page")).toBeVisible();
  await page.screenshot({ path: path.join(shotDir, "i5-1-list-submitted-1366.png"), fullPage: true });
});
