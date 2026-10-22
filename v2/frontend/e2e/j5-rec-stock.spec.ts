/**
 * J#5-REC — compromisso confirma, não fatura, vincula na tela (SKU ≠ EAN/I.V.*) e chega ao estoque.
 */
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { loginAs } from "./helpers/orderCreate";

const SHOT_DIR = path.resolve(
  process.cwd(),
  "..",
  "..",
  "docs",
  "v2",
  "etapa-j5-rec",
  "screenshots",
);

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

async function shot(page: import("@playwright/test").Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SHOT_DIR, name), fullPage: true });
}

test("J5-REC compromisso vinculado chega ao estoque", async ({ page }) => {
  test.setTimeout(180_000);
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.setViewportSize({ width: 1366, height: 900 });
  await loginAs(page);

  const tag = Date.now().toString(36);
  const catalogSku = `CAT-REC-${tag}`;
  expect(catalogSku).not.toMatch(/^I\.V\./i);
  expect(/^\d{8,14}$/.test(catalogSku)).toBeFalsy();

  let r = await api(page, "POST", "/api/suppliers", {
    name: `Sup REC ${tag}`,
    country_code: "IT",
  });
  expectOk(r.status);
  const supplier = r.body as Json & { id: number };

  r = await api(page, "POST", "/api/orders", {
    code: `ORD-REC-${tag}`,
    supplier_id: supplier.id,
    currency: "EUR",
  });
  expectOk(r.status);
  let order = r.body as Json & { id: number; version: number; items?: Json[] };

  r = await api(page, "POST", `/api/orders/${order.id}/items`, {
    expected_version: order.version,
    line_kind: "COMMITMENT",
    external_code: "I.V. 2",
    description: "racchette compromisso",
    quantity: "10",
    unit_price: "100",
    unit: "PZ",
  });
  expectOk(r.status);
  order = r.body as typeof order;

  r = await api(page, "POST", `/api/orders/${order.id}/confirm`, {
    expected_version: order.version,
  });
  expectOk(r.status);
  order = r.body as typeof order;
  const item = (order.items ?? [])[0] as Json & { id: number };
  expect(item.line_kind).toBe("COMMITMENT");
  expect(item.product_id).toBeNull();

  const blockedInv = await api(page, "POST", `/api/orders/${order.id}/invoices`, {
    invoice_number: `F-REC-BLOCK-${tag}`,
    invoice_type: "FINAL",
  });
  expect(blockedInv.status).toBeGreaterThanOrEqual(400);
  expect(JSON.stringify(blockedInv.body)).toMatch(/faturável|COMMITMENT|compromisso/i);

  await page.goto(`/orders/${order.id}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("cockpit-alert-COMMITMENT_UNBOUND")).toBeVisible();
  await shot(page, "01-cockpit-compromisso.png");

  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("close-blocked-commitment")).toBeVisible();
  await page.getByTestId(`bind-product-${item.id}`).click();
  await expect(page.getByTestId("bind-product-modal")).toBeVisible();
  await page.getByTestId("bind-product-sku").fill(catalogSku);
  await page.getByTestId("bind-product-new-desc").fill(`Raquete rec ${tag}`);
  await page.getByTestId("bind-product-create-btn").click();
  await expect(page.getByTestId("bind-product-match")).toContainText(catalogSku, { timeout: 15_000 });
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId(`bind-product-${item.id}`)).toHaveCount(0, { timeout: 15_000 });
  await expect(page.getByTestId("close-blocked-commitment")).toHaveCount(0);
  await shot(page, "02-comercial-vinculado.png");

  r = await api(page, "GET", `/api/orders/${order.id}`);
  expectOk(r.status);
  order = r.body as typeof order;
  const bound = (order.items ?? [])[0] as Json & { id: number; product_id: number; sku_snapshot: string };
  expect(bound.line_kind).toBe("PRODUCT");
  expect(bound.external_code).toBe("I.V. 2");
  expect(bound.sku_snapshot).toBe(catalogSku);
  expect(bound.sku_snapshot).not.toBe("I.V. 2");
  const productId = bound.product_id;
  const orderItemId = bound.id;

  await page.goto(`/orders/${order.id}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("cockpit-alert-COMMITMENT_UNBOUND")).toHaveCount(0);

  async function issuedInvoice() {
    let invR = await api(page, "POST", `/api/orders/${order.id}/invoices`, {
      invoice_number: `F-REC-${tag}`,
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
          unit_price_gross: "100",
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
      form.append("file", new Blob(["%PDF-1.4 rec"], { type: "application/pdf" }), "rec.pdf");
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

  const inv = await issuedInvoice();

  r = await api(page, "POST", "/api/logistics-providers", {
    legal_name: `Carrier REC ${tag}`,
    provider_type: "TRANSPORTADOR",
    active: true,
  });
  expectOk(r.status);
  const provider = r.body as Json & { id: number };

  r = await api(page, "POST", "/api/shipments", {
    modal: "SEA",
    logistics_provider_id: provider.id,
  });
  expectOk(r.status);
  let sh = r.body as Json & { id: number; version: number; items: Json[] };
  r = await api(page, "POST", `/api/shipments/${sh.id}/items`, {
    expected_version: sh.version,
    order_item_id: orderItemId,
    quantity: "10",
  });
  expectOk(r.status);
  sh = r.body as typeof sh;
  const shpItemId = (sh.items[0] as Json).id as number;
  const invItemId = (inv.items[0] as Json).id as number;

  await page.goto("/customs");
  await page.getByTestId("customs-new-link").click();
  await page.getByTestId("customs-external-ref").fill(`DUIMP-REC-${tag}`);
  await page.getByTestId("customs-create-submit").click();
  await page.waitForURL(/\/customs\/\d+/);
  const processId = Number(page.url().match(/\/customs\/(\d+)/)?.[1]);
  expect(processId).toBeGreaterThan(0);

  await page.goto(`/customs/${processId}`);
  await expect(page.getByTestId("customs-detail-page")).toBeVisible();
  await page.getByTestId("customs-link-invoice-id").fill(String(inv.id));
  await page.getByTestId("customs-link-invoice").click();
  await expect(page.getByTestId("customs-invoice-list")).toContainText(String(inv.id));
  await page.getByTestId("customs-link-shipment-id").fill(String(sh.id));
  await page.getByTestId("customs-link-shipment").click();
  await expect(page.getByTestId("customs-shipment-list")).toContainText(String(sh.id));

  await page.getByTestId("customs-alloc-inv-item").fill(String(invItemId));
  await page.getByTestId("customs-alloc-inv-qty").fill("10");
  await page.getByTestId("customs-alloc-inv").click();
  await page.getByTestId("customs-alloc-shp-item").fill(String(shpItemId));
  await page.getByTestId("customs-alloc-shp-qty").fill("10");
  await page.getByTestId("customs-alloc-shp").click();

  await page.getByTestId("customs-submit").click();
  await expect(page.getByTestId("status-badge")).toHaveAttribute("data-status", "SUBMITTED");

  await page.getByTestId("customs-nationalization-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("nationalization-create").click();
  await page.getByTestId(`nationalization-proposed-s-${shpItemId}`).fill("10");
  await page.getByTestId("nationalization-add-items").click();
  const natConfirm = page.locator('[data-testid^="nationalization-confirm-"]').first();
  await expect(natConfirm).toBeVisible();
  await natConfirm.click();
  await expect(page.getByTestId("nationalization-list")).toContainText("Confirmada");

  await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("receipt-residual-table")).toBeVisible();
  await page.getByTestId("receipt-location").selectOption("DOMESTIC-MAIN");
  await page.locator('[data-testid^="receipt-proposed-"]').first().fill("10");
  await page.getByTestId("receipt-receive").click();
  await expect(page.getByTestId("receipt-list")).toContainText("Confirmado");
  await shot(page, "03-recebimento.png");

  await page.goto(`/inventory/sku/${productId}`);
  await expect(page.getByTestId("sku-position-page")).toBeVisible();
  await expect(page.getByTestId("sku-bucket-available_qty")).toContainText("10");
  await expect(page.getByTestId("sku-position-page")).toContainText(catalogSku);
  await expect(page.getByTestId("sku-position-page")).not.toContainText("I.V. 2");
  await shot(page, "04-posicao-estoque.png");
});
