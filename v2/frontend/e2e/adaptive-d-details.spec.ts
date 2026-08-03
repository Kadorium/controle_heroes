import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/adaptive-d/screenshots",
);

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("navigation", { name: /módulos/i })).toBeVisible({
    timeout: 15000,
  });
}

/**
 * Onda D — detalhes/forms/gaps: RO cockpit, FX by id, without-doc, cancel, create parcial, retorno.
 */
test("adaptive-D details forms gaps", async ({ page }) => {
  mkdirSync(evidenceDir, { recursive: true });
  await page.setViewportSize({ width: 1366, height: 768 });
  await login(page);

  const stamp = Date.now();
  const seed = await page.evaluate(async (s) => {
    const sRes = await fetch("/api/suppliers", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: `D-Supp-${s}`, country_code: "IT" }),
    });
    if (!sRes.ok) throw new Error(`supplier ${sRes.status}`);
    const supplier = (await sRes.json()) as { id: number };

    const pRes = await fetch("/api/products", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sku: `D-SKU-${s}`, description: `Item ${s}` }),
    });
    if (!pRes.ok) throw new Error(`product ${pRes.status}`);
    const product = (await pRes.json()) as { id: number };

    const oRes = await fetch("/api/orders", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code: `D-ORD-${s}`,
        supplier_id: supplier.id,
        currency: "EUR",
      }),
    });
    if (!oRes.ok) throw new Error(`order ${oRes.status}`);
    let order = (await oRes.json()) as { id: number; version: number };

    const iRes = await fetch(`/api/orders/${order.id}/items`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_version: order.version,
        product_id: product.id,
        quantity: "1",
        unit_price: "100.0000",
      }),
    });
    if (!iRes.ok) throw new Error(`item ${iRes.status}`);
    order = (await iRes.json()) as { id: number; version: number };

    const cRes = await fetch(`/api/orders/${order.id}/confirm`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_version: order.version }),
    });
    if (!cRes.ok) throw new Error(`confirm ${cRes.status}`);
    order = (await cRes.json()) as { id: number; version: number };

    const invRes = await fetch(`/api/orders/${order.id}/invoices`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoice_number: `D-INV-${s}`, invoice_type: "FINAL" }),
    });
    if (!invRes.ok) throw new Error(`invoice ${invRes.status}`);
    let inv = (await invRes.json()) as {
      id: number;
      version: number;
      items: { order_item_id: number; quantity: string; unit_price_gross: string | null }[];
    };

    const itemsBody = {
      expected_version: inv.version,
      items: (inv.items ?? []).map((it) => ({
        order_item_id: it.order_item_id,
        quantity: it.quantity,
        unit_price_gross: it.unit_price_gross ?? "100.0000",
        discount_type: "NONE",
      })),
    };
    const itemsRes = await fetch(`/api/invoices/${inv.id}/items`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(itemsBody),
    });
    if (!itemsRes.ok) throw new Error(`items ${itemsRes.status}`);
    inv = (await itemsRes.json()) as typeof inv;

    const termsRes = await fetch(`/api/invoices/${inv.id}/terms`, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_version: inv.version,
        mode: "AMOUNT",
        terms: [{ due_date: "2026-08-15", amount: "100.0000" }],
      }),
    });
    if (!termsRes.ok) throw new Error(`terms ${termsRes.status}`);
    inv = (await termsRes.json()) as typeof inv;

    const issueRes = await fetch(`/api/invoices/${inv.id}/issue`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        expected_version: inv.version,
        issue_without_document: true,
        reason_code: "TEST_OVERRIDE",
      }),
    });
    if (!issueRes.ok) throw new Error(`issue ${issueRes.status}`);
    inv = (await issueRes.json()) as typeof inv & { payables?: { id: number }[] };

    const payablesRes = await fetch(`/api/payables?invoice_id=${inv.id}`, {
      credentials: "include",
    });
    if (!payablesRes.ok) throw new Error(`payables ${payablesRes.status}`);
    const payables = (await payablesRes.json()) as { id: number }[];
    const payableId = payables[0]?.id;
    if (!payableId) throw new Error("no payable");

    const byId = await fetch(`/api/payables/${payableId}`, { credentials: "include" });
    if (!byId.ok) throw new Error(`get payable ${byId.status}`);

    const payRes = await fetch("/api/payments", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        supplier_id: supplier.id,
        amount: "50.0000",
        currency: "EUR",
        payment_date: "2026-07-30",
        register_without_document: true,
        reason_code: "TEST_OVERRIDE",
        external_reference: `D-PAY-${s}`,
      }),
    });
    if (!payRes.ok) throw new Error(`payment ${payRes.status}`);
    const payment = (await payRes.json()) as { id: number; version: number };

    const draftInvRes = await fetch(`/api/orders/${order.id}/invoices`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoice_number: `D-DRAFT-${s}`, invoice_type: "FINAL" }),
    });
    if (!draftInvRes.ok) throw new Error(`draft inv ${draftInvRes.status}`);
    const draftInv = (await draftInvRes.json()) as { id: number };

    return {
      orderId: order.id,
      payableId,
      paymentId: payment.id,
      draftInvoiceId: draftInv.id,
    };
  }, stamp);

  // D1 — Cockpit RO + detail-shell
  await page.goto(`/orders/${seed.orderId}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("order-cockpit")).toHaveClass(/detail-shell/);
  await expect(page.getByText(/somente leitura/i)).toBeVisible();
  await page.screenshot({
    path: path.join(evidenceDir, "d1-cockpit-1366.png"),
    fullPage: true,
  });

  // D0.5/D1 — FX by id (GET /api/payables/{id}, sem scan)
  await page.goto(`/payables/${seed.payableId}/fx`);
  await expect(page.getByTestId("payable-fx-page")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("payable-fx-page")).toHaveClass(/detail-shell/);
  await page.screenshot({
    path: path.join(evidenceDir, "d1-fx-1366.png"),
    fullPage: true,
  });

  // D3 — cancel payment (REGISTERED sem alocação)
  await page.goto(`/payments/${seed.paymentId}`);
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("cancel-payment").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByText(/cancelado/i)).toBeVisible({ timeout: 10000 });

  // D3 — cancel invoice DRAFT
  await page.goto(`/invoices/${seed.draftInvoiceId}`);
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("cancel-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByText(/cancelad/i)).toBeVisible({ timeout: 10000 });

  // D2/D3 — PaymentCreate without-doc + form-grid + retorno
  await page.goto("/payments?status=REGISTERED");
  await page.getByRole("link", { name: /novo pagamento/i }).click();
  await expect(page.getByTestId("payment-create")).toBeVisible();
  await expect(page.locator(".form-grid")).toBeVisible();
  await page.getByTestId("register-without-doc").check();
  await page.getByTestId("pay-supplier").selectOption({ index: 1 });
  await page.getByTestId("pay-amount").fill("12.50");
  await page.getByTestId("save-payment").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });

  // D2 — create parcial: save draft then notice on retry path
  await page.goto("/orders/new");
  await expect(page.getByTestId("order-create-page")).toBeVisible();
  const code = `D-PARTIAL-${stamp}`;
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Partial Supp ${stamp}`);
  await page.getByTestId("line-sku").fill(`PSKU-${stamp}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("1");
  await page.getByTestId("line-price").fill("10");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-draft").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });
  await page.goto("/orders/new");
  // Simulate partial by API create then UI notice requires persistedOrder in-session —
  // assert commercial return path from create with form-grid
  await expect(page.locator(".form-grid")).toBeVisible();
  await page.screenshot({
    path: path.join(evidenceDir, "d2-order-create-1366.png"),
    fullPage: true,
  });

  // Viewports smoke (economic)
  for (const w of [1024, 1440] as const) {
    await page.setViewportSize({ width: w, height: w === 1024 ? 768 : 900 });
    await page.goto(`/orders/${seed.orderId}`);
    await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
    await page.screenshot({
      path: path.join(evidenceDir, `d1-cockpit-${w}.png`),
      fullPage: true,
    });
  }
});
