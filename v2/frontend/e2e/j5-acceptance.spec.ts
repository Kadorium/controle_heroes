/**
 * I5-6 — Aceite final J#5 (Customs + Inventory).
 * Viewport 1366; login admin; UI preferencial; API para prereqs determinísticos.
 * Screenshots: docs/v2/etapa-j5/screenshots/j5-*.png
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

async function shot(page: import("@playwright/test").Page, name: string) {
  await page.screenshot({ path: path.join(shotDir, name), fullPage: true });
}

test("J#5 I5-6 comprehensive acceptance", async ({ page }) => {
  test.setTimeout(300_000);
  fs.mkdirSync(shotDir, { recursive: true });

  await page.setViewportSize({ width: 1366, height: 900 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  const tag = Date.now().toString(36);
  const payeeName = `Bechtrans-${tag}`;

  // --- Deterministic prereqs via API (catalog + ISSUED invoices + shipments) ---
  let r = await api(page, "POST", "/api/suppliers", {
    name: `Sup J5 ${tag}`,
    country_code: "IT",
  });
  expectOk(r.status);
  const supplier = r.body;

  r = await api(page, "POST", "/api/products", {
    sku: `SKU-J5-${tag}`,
    description: `Produto J5 ${tag}`,
  });
  expectOk(r.status);
  const product = r.body as Json & { id: number };

  r = await api(page, "POST", "/api/orders", {
    code: `ORD-J5-${tag}`,
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

  r = await api(page, "POST", `/api/orders/${order.id}/confirm`, {
    expected_version: order.version,
  });
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
      form.append("file", new Blob(["%PDF-1.4 j5"], { type: "application/pdf" }), "j5.pdf");
      form.append("entity_type", "invoice");
      form.append("entity_id", String(invoiceId));
      form.append("role", "official");
      const res = await fetch("/api/documents", {
        method: "POST",
        credentials: "include",
        body: form,
      });
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

  const inv1 = await issuedInvoice(`J5-${tag}-1`);
  const inv2 = await issuedInvoice(`J5-${tag}-2`);

  r = await api(page, "POST", "/api/logistics-providers", {
    legal_name: `Carrier J5 ${tag}`,
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

  const sh1 = await shipment("6");
  const sh2 = await shipment("4");

  // --- 1) Create process via UI ---
  await page.goto("/customs");
  await page.getByTestId("customs-new-link").click();
  await page.getByTestId("customs-external-ref").fill(`DUIMP-J5-${tag}`);
  await page.getByTestId("customs-create-submit").click();
  await page.waitForURL(/\/customs\/\d+/);
  const processUrl = page.url();
  const processId = Number(processUrl.match(/\/customs\/(\d+)/)?.[1]);
  expect(processId).toBeGreaterThan(0);

  await page.goto("/customs");
  await expect(page.getByTestId("customs-list-page")).toBeVisible();
  await expect(page.getByTestId("customs-table")).toContainText(`DUIMP-J5-${tag}`);
  await shot(page, "j5-01-process-list.png");

  // --- 2) Multi invoice + shipment links ---
  await page.goto(`/customs/${processId}`);
  await expect(page.getByTestId("customs-detail-page")).toBeVisible();

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

  await page.getByTestId("customs-section-invoices").scrollIntoViewIfNeeded();
  await shot(page, "j5-02-process-links.png");

  // --- 3) Partial allocations ---
  const invItemId = (inv1.items[0] as Json).id as number;
  const shpItemId = (sh1.items[0] as Json).id as number;

  await page.getByTestId("customs-alloc-inv-item").fill(String(invItemId));
  await page.getByTestId("customs-alloc-inv-qty").fill("4");
  await page.getByTestId("customs-alloc-inv").click();
  await expect(page.getByTestId("customs-inv-residuals")).toContainText("4");

  await page.getByTestId("customs-alloc-shp-item").fill(String(shpItemId));
  await page.getByTestId("customs-alloc-shp-qty").fill("3");
  await page.getByTestId("customs-alloc-shp").click();
  await expect(page.getByTestId("customs-shp-residuals")).toContainText("3");

  await page.getByTestId("customs-section-allocs-inv").scrollIntoViewIfNeeded();
  await shot(page, "j5-03-item-allocations.png");

  // --- 4) Submit ---
  await page.getByTestId("customs-submit").click();
  await expect(page.getByTestId("status-badge")).toHaveAttribute("data-status", "SUBMITTED");
  await shot(page, "j5-04-process-submitted.png");

  // --- 5) Doganale v1 ---
  await page.getByTestId("customs-doganale-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("doganale-create-version").click();
  await expect(page.getByTestId("doganale-history")).toContainText("v1");
  await page.getByTestId("doganale-ncm").fill("84713012");
  await page.getByTestId("doganale-desc").fill(`Notebook J5 ${tag}`);
  await page.getByTestId("doganale-qty").fill("10");
  await page.getByTestId("doganale-price").fill("100");
  await page.getByTestId("doganale-save-lines").click();
  await page.getByTestId("doganale-activate").click();
  await expect(page.getByTestId("doganale-current")).toContainText("v1 (ACTIVE)");
  await shot(page, "j5-05-doganale-v1.png");

  // --- 6) Doganale v2 + history ---
  await page.getByTestId("doganale-supersede").click();
  await expect(page.getByTestId("doganale-history")).toContainText("v2");
  await page.getByTestId("doganale-desc").fill(`Notebook retificado J5 ${tag}`);
  await page.getByTestId("doganale-qty").fill("9");
  await page.getByTestId("doganale-save-lines").click();
  await page.getByTestId("doganale-activate").click();
  await expect(page.getByTestId("doganale-current")).toContainText("v2 (ACTIVE)");
  await expect(page.getByTestId("doganale-history")).toContainText("SUPERSEDED");
  await shot(page, "j5-06-doganale-v2-history.png");

  // --- 7) Divergence ---
  await page.getByTestId("doganale-div-msg").fill(`Divergência qty J5 ${tag}`);
  await page.getByTestId("doganale-add-divergence").click();
  await expect(page.getByTestId("doganale-divergences")).toContainText("Divergência qty");
  await shot(page, "j5-07-doganale-divergence.png");

  // --- 8) Funding request (Bechtrans-like payee) ---
  await page.getByTestId("customs-numerario-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("numerario-payee-name").fill(payeeName);
  await page.getByTestId("numerario-bank").fill("Banco Bechtrans");
  await page.getByTestId("numerario-declared").fill("1500.00");
  await page.getByTestId("numerario-create").click();
  await expect(page.getByTestId("numerario-list")).toContainText(payeeName);
  await shot(page, "j5-08-funding-request.png");

  // --- 9) Funding composition (bases / tax / expense) ---
  await page.getByTestId("numerario-basis").fill("1000");
  await page.getByTestId("numerario-tax").fill("300");
  await page.getByTestId("numerario-expense").fill("200");
  await page.getByTestId("numerario-save-lines").click();
  await expect(page.getByTestId("numerario-totals")).toContainText("1.500,00");
  await shot(page, "j5-09-funding-composition.png");

  await page.getByTestId("numerario-confirm").click();
  await expect(page.getByTestId("numerario-confirmed-totals")).toBeVisible();
  await expect(page.getByTestId("numerario-payable-links")).toBeVisible();

  // --- 10) Customs payable on AP ---
  await page.goto("/payables");
  await expect(page.getByTestId("ap-queue-page")).toBeVisible();
  await expect(page.getByTestId("ap-table")).toContainText(payeeName);
  await expect(page.getByTestId("ap-origin-customs").first()).toBeVisible();
  // multi-currency KPIs must not show a single EUR total mixing BRL
  const openKpis = page.locator('[data-testid^="kpi-open-balance-"]');
  await expect(openKpis.first()).toBeVisible();
  const kpiTexts = await openKpis.allTextContents();
  expect(kpiTexts.join(" ")).not.toMatch(/EUR\s*1[.,]900/);
  const customsRow = page.locator('[data-testid^="ap-row-"]').filter({ hasText: payeeName }).first();
  await customsRow.click();
  await expect(page.getByText(/Numerário \(Customs\)/i)).toBeVisible();
  await expect(page.getByTestId("ap-customs-settlement-notice")).toBeVisible();
  await expect(page.getByTestId("ap-g02-new-payment")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Abrir fatura" })).toHaveCount(0);
  await shot(page, "j5-10-customs-payable-ap.png");

  // --- 11) Bonded receipt ---
  await page.goto(`/customs/${processId}`);
  await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("receipt-type").fill("BONDED_IN");
  await page.getByTestId("receipt-location").fill("BONDED-MAIN");
  await page.getByTestId("receipt-create").click();
  await expect(page.getByTestId("receipt-list")).toContainText(/Entrada entreposto|BONDED/i);

  await page.getByTestId("receipt-product-id").fill(String(product.id));
  await page.getByTestId("receipt-qty").fill("5");
  await page.getByTestId("receipt-add-lines").click();

  const receiptConfirm = page.locator('[data-testid^="receipt-confirm-"]').first();
  await expect(receiptConfirm).toBeVisible();
  await receiptConfirm.click();
  await expect(page.getByTestId("receipt-list")).toContainText("Confirmado");
  await shot(page, "j5-11-bonded-receipt.png");

  // --- 12) Partial nationalization ---
  await page.getByTestId("customs-nationalization-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("nationalization-create").click();
  await page.getByTestId("nationalization-product-id").fill(String(product.id));
  await page.getByTestId("nationalization-qty").fill("2");
  await page.getByTestId("nationalization-shipment-item").fill(String(shpItemId));
  await page.getByTestId("nationalization-invoice-item").fill(String(invItemId));
  await page.getByTestId("nationalization-add-items").click();
  await expect(page.getByTestId("nationalization-list")).toContainText(`SKU ${product.id}`);

  const natConfirm = page.locator('[data-testid^="nationalization-confirm-"]').first();
  await expect(natConfirm).toBeVisible();
  await natConfirm.click();
  await expect(page.getByTestId("nationalization-list")).toContainText("Confirmada");
  await shot(page, "j5-12-partial-nationalization.png");

  // --- 12b) RECLASS bonded → domestic (SC-10 conservação) ---
  const natMeta = await page.evaluate(async (pid) => {
    const res = await fetch(`/api/import-processes/${pid}/nationalizations`, {
      credentials: "include",
    });
    const list = await res.json();
    const confirmed = list.find((n: { status: string }) => n.status === "CONFIRMED");
    return {
      natId: confirmed?.id ?? null,
      itemId: confirmed?.items?.[0]?.id ?? null,
    };
  }, processId);
  expect(natMeta.natId).toBeTruthy();
  expect(natMeta.itemId).toBeTruthy();

  await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("receipt-type").fill("RECLASS");
  await page.getByTestId("receipt-location").fill("DOMESTIC-MAIN");
  await page.getByTestId("receipt-nat-id").fill(String(natMeta.natId));
  await page.getByTestId("receipt-create").click();
  await expect(page.getByTestId("receipt-list")).toContainText(/Reclass|Rascunho|DOMESTIC/i);

  await page.getByTestId("receipt-product-id").fill(String(product.id));
  await page.getByTestId("receipt-qty").fill("2");
  await page.getByTestId("receipt-nat-item-id").fill(String(natMeta.itemId));
  await page.getByTestId("receipt-add-lines").click();
  const reclassConfirm = page.locator('[data-testid^="receipt-confirm-"]').first();
  await expect(reclassConfirm).toBeVisible();
  await reclassConfirm.click();
  await expect(page.getByTestId("receipt-list")).toContainText("Confirmado");

  // --- 13) SKU position after conservation ---
  await page.goto(`/inventory/sku/${product.id}`);
  await expect(page.getByTestId("sku-position-page")).toBeVisible();
  await expect(page.getByTestId("sku-buckets")).toBeVisible();
  await expect(page.getByTestId("sku-bucket-bonded_qty")).toContainText("3");
  await expect(page.getByTestId("sku-bucket-available_qty")).toContainText("2");
  await expect(page.getByTestId("sku-bucket-cleared_not_received_qty")).toContainText("0");
  await expect(page.getByTestId("sku-bucket-in_clearance_qty")).toContainText("Não disponível");
  await expect(page.getByTestId("sku-dimension-note")).toBeVisible();
  await shot(page, "j5-13-sku-position.png");

  // --- 14) Inventory movements ---
  await page.goto(`/inventory/movements?product_id=${product.id}`);
  await expect(page.getByTestId("inventory-movements-page")).toBeVisible();
  await expect(page.getByTestId("movements-product-filter")).toHaveValue(String(product.id));
  await expect(page.getByTestId("movements-list")).toBeVisible();
  await expect(page.getByTestId("movements-list")).toContainText(/Entrada entreposto|Reclassificação/);
  await expect(page.getByTestId("movements-list")).toContainText(/BONDED-MAIN|Entreposto/i);
  await expect(page.getByTestId("movements-list")).toContainText(/DOMESTIC-MAIN|Doméstic/i);
  await shot(page, "j5-14-inventory-movements.png");

  // --- 15) Documents + audit ---
  await page.goto(`/customs/${processId}`);
  await page.getByTestId("customs-section-docs").scrollIntoViewIfNeeded();
  await page.getByTestId("customs-doc-upload").setInputFiles({
    name: `duimp-${tag}.pdf`,
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 j5-acceptance"),
  });
  await expect(page.getByTestId("customs-docs")).toContainText(`duimp-${tag}.pdf`);

  await page.getByTestId("customs-section-audit").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("customs-audit-table")).toBeVisible();
  await expect(page.getByTestId("customs-audit-table")).toContainText(/./);
  await shot(page, "j5-15-documents-audit.png");
});
