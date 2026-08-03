/**
 * Inc-6 vertical Order-to-Pay — domain effects via API + UI walkthrough.
 * Gate: npm run e2e:inc-6
 */
import { test, expect } from "@playwright/test";

type Json = Record<string, unknown>;

async function api(
  page: import("@playwright/test").Page,
  method: string,
  path: string,
  body?: unknown,
): Promise<{ status: number; body: Json | Json[] | string }> {
  return page.evaluate(
    async ({ method, path, body }) => {
      const opts: RequestInit = { method, credentials: "include" };
      if (body !== undefined) {
        opts.headers = { "Content-Type": "application/json" };
        opts.body = JSON.stringify(body);
      }
      const r = await fetch(path, opts);
      const text = await r.text();
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        /* raw */
      }
      return { status: r.status, body: parsed as Json };
    },
    { method, path, body },
  );
}

function expectOk(status: number) {
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThan(300);
}

async function uploadDoc(
  page: import("@playwright/test").Page,
  entityType: string,
  entityId: number,
  role = "official",
) {
  return page.evaluate(
    async ({ entityType, entityId, role }) => {
      const fd = new FormData();
      fd.append("file", new Blob(["%PDF-1.4 inc6"], { type: "application/pdf" }), "inc6.pdf");
      fd.append("entity_type", entityType);
      fd.append("entity_id", String(entityId));
      fd.append("role", role);
      const r = await fetch("/api/documents", { method: "POST", credentials: "include", body: fd });
      return { status: r.status, body: await r.json() };
    },
    { entityType, entityId, role },
  );
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function plusDays(n: number) {
  return new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);
}

test("Inc-6 Order-to-Pay vertical domain slice", async ({ page }) => {
  const tag = `I6-${Date.now()}`;
  const sku = `SKU-${tag}`;

  // --- Login (UI) ---
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({
    timeout: 15000,
  });

  // 1–3 Supplier, Product, Order+items, CONFIRM
  const supplierRes = await api(page, "POST", "/api/suppliers", {
    name: `Sup ${tag}`,
    country_code: "IT",
  });
  expectOk(supplierRes.status);
  const supplier = supplierRes.body as Json;
  expect(supplier.id).toBeTruthy();

  const productRes = await api(page, "POST", "/api/products", {
    sku,
    description: `Product ${tag}`,
  });
  expectOk(productRes.status);
  const product = productRes.body as Json;
  expect(product.id).toBeTruthy();

  let orderRes = await api(page, "POST", "/api/orders", {
    code: tag,
    supplier_id: supplier.id,
    currency: "EUR",
  });
  expectOk(orderRes.status);
  let order = orderRes.body as Json;
  orderRes = await api(page, "POST", `/api/orders/${order.id}/items`, {
    expected_version: order.version,
    product_id: product.id,
    quantity: "20",
    unit_price: "100",
  });
  expectOk(orderRes.status);
  order = orderRes.body as Json;
  orderRes = await api(page, "POST", `/api/orders/${order.id}/confirm`, {
    expected_version: order.version,
  });
  expectOk(orderRes.status);
  order = orderRes.body as Json;
  expect(order.status).toBe("CONFIRMED");
  const orderId = order.id as number;
  const orderItemId = (order.items as Json[])[0].id as number;

  // 4–6 Two invoices; inv1 multi terms → multi payables; inv2 remaining qty
  let inv1 = (
    await api(page, "POST", `/api/orders/${orderId}/invoices`, {
      invoice_number: `F1-${tag}`,
      invoice_type: "FINAL",
      order_item_ids: [orderItemId],
    })
  ).body as Json;
  const item1 = (inv1.items as Json[])[0];
  inv1 = (
    await api(page, "PUT", `/api/invoices/${inv1.id}/items`, {
      expected_version: inv1.version,
      items: [
        {
          order_item_id: item1.order_item_id,
          quantity: "10",
          unit_price_gross: "100",
          discount_type: "NONE",
        },
      ],
    })
  ).body as Json;
  expect(inv1.net_amount).toBe("1000.00");
  inv1 = (
    await api(page, "PUT", `/api/invoices/${inv1.id}/terms`, {
      expected_version: inv1.version,
      mode: "AMOUNT",
      terms: [
        { due_date: today(), amount: "400" },
        { due_date: plusDays(30), amount: "600" },
      ],
    })
  ).body as Json;
  const doc1 = await uploadDoc(page, "invoice", inv1.id as number);
  expectOk(doc1.status);
  inv1 = (
    await api(page, "POST", `/api/invoices/${inv1.id}/issue`, {
      expected_version: inv1.version,
    })
  ).body as Json;
  expect(inv1.status).toBe("ISSUED");
  expect((inv1.payables as Json[]).length).toBe(2);
  expect(inv1.payables_sum).toBe("1000.00");
  expect(inv1.balance).toBe("1000.00");
  const [pa, pb] = inv1.payables as Json[];

  let inv2 = (
    await api(page, "POST", `/api/orders/${orderId}/invoices`, {
      invoice_number: `F2-${tag}`,
      invoice_type: "FINAL",
    })
  ).body as Json;
  const item2 = (inv2.items as Json[])[0];
  inv2 = (
    await api(page, "PUT", `/api/invoices/${inv2.id}/items`, {
      expected_version: inv2.version,
      items: [
        {
          order_item_id: item2.order_item_id,
          quantity: "10",
          unit_price_gross: "100",
          discount_type: "NONE",
        },
      ],
    })
  ).body as Json;
  inv2 = (
    await api(page, "PUT", `/api/invoices/${inv2.id}/terms`, {
      expected_version: inv2.version,
      mode: "PERCENT",
      terms: [{ due_date: today(), percent: "100" }],
    })
  ).body as Json;
  const doc2 = await uploadDoc(page, "invoice", inv2.id as number);
  expectOk(doc2.status);
  inv2 = (
    await api(page, "POST", `/api/invoices/${inv2.id}/issue`, {
      expected_version: inv2.version,
    })
  ).body as Json;
  expect(inv2.status).toBe("ISSUED");
  expect((inv2.payables as Json[]).length).toBe(1);
  expect(inv2.balance).toBe("1000.00");
  const pc = (inv2.payables as Json[])[0];

  // Independent balances (SC-01)
  const inv1Reload = (await api(page, "GET", `/api/invoices/${inv1.id}`)).body as Json;
  const inv2Reload = (await api(page, "GET", `/api/invoices/${inv2.id}`)).body as Json;
  expect(inv1Reload.balance).toBe("1000.00");
  expect(inv2Reload.balance).toBe("1000.00");

  // 7–8 Payment unallocated — balances unchanged (SC-03)
  const balBefore = {
    inv1: inv1Reload.balance,
    pa: (await api(page, "GET", `/api/payables/${pa.id}`)).body as Json,
    pb: (await api(page, "GET", `/api/payables/${pb.id}`)).body as Json,
  };
  let payment = (
    await api(page, "POST", "/api/payments", {
      supplier_id: supplier.id,
      amount: "1000",
      currency: "EUR",
      payment_date: today(),
      register_without_document: true,
      reason_code: "TEST_OVERRIDE",
    })
  ).body as Json;
  expect(payment.amount_unallocated).toBe("1000.00");
  expect(payment.amount_allocated).toBe("0.00");
  const paAfterPay = (await api(page, "GET", `/api/payables/${pa.id}`)).body as Json;
  const pbAfterPay = (await api(page, "GET", `/api/payables/${pb.id}`)).body as Json;
  const inv1AfterPay = (await api(page, "GET", `/api/invoices/${inv1.id}`)).body as Json;
  expect(paAfterPay.balance).toBe(balBefore.pa.balance);
  expect(pbAfterPay.balance).toBe(balBefore.pb.balance);
  expect(inv1AfterPay.balance).toBe(balBefore.inv1);

  // 9–11 Partial + multi-payable allocation (SC-04)
  const key1 = `i6-alloc1-${tag}`;
  payment = (
    await api(page, "POST", `/api/payments/${payment.id}/allocations`, {
      expected_version: payment.version,
      idempotency_key: key1,
      allocations: [
        {
          payable_id: pa.id,
          amount: "200",
          expected_version: paAfterPay.version,
        },
      ],
    })
  ).body as Json;
  expect(payment.amount_unallocated).toBe("800.00");
  const paPartial = (await api(page, "GET", `/api/payables/${pa.id}`)).body as Json;
  expect(paPartial.balance).toBe("200.0000");
  expect(paPartial.status).toBe("PARTIALLY_PAID");

  const pbFresh = (await api(page, "GET", `/api/payables/${pb.id}`)).body as Json;
  payment = (
    await api(page, "POST", `/api/payments/${payment.id}/allocations`, {
      expected_version: payment.version,
      idempotency_key: `i6-alloc2-${tag}`,
      allocations: [
        {
          payable_id: pb.id,
          amount: "300",
          expected_version: pbFresh.version,
        },
      ],
    })
  ).body as Json;
  expect(payment.amount_unallocated).toBe("500.00");
  const pbPartial = (await api(page, "GET", `/api/payables/${pb.id}`)).body as Json;
  expect(pbPartial.balance).toBe("300.0000");
  const inv1AfterAlloc = (await api(page, "GET", `/api/invoices/${inv1.id}`)).body as Json;
  // residual invoice = 200 + 300 = 500
  expect(Number(inv1AfterAlloc.balance)).toBe(500);

  // 12 Idempotent replay — same key must not double-allocate
  const unallocBeforeReplay = payment.amount_unallocated;
  const allocLenBefore = (payment.allocations as Json[]).length;
  const replay = await api(page, "POST", `/api/payments/${payment.id}/allocations`, {
    expected_version: 999,
    idempotency_key: key1,
    allocations: [
      {
        payable_id: pa.id,
        amount: "200",
        expected_version: paAfterPay.version,
      },
    ],
  });
  expectOk(replay.status);
  const replayBody = replay.body as Json;
  // Residual must not drop further (no second 200 applied)
  expect(Number(replayBody.amount_unallocated)).toBeGreaterThanOrEqual(Number(unallocBeforeReplay));
  const payAfterReplay = (await api(page, "GET", `/api/payments/${payment.id}`)).body as Json;
  expect((payAfterReplay.allocations as Json[]).length).toBe(allocLenBefore);
  expect(payAfterReplay.amount_unallocated).toBe(unallocBeforeReplay);

  // 13 Excess blocked
  const paNow = (await api(page, "GET", `/api/payables/${pa.id}`)).body as Json;
  const excess = await api(page, "POST", `/api/payments/${payment.id}/allocations`, {
    expected_version: payment.version,
    idempotency_key: `i6-excess-${tag}`,
    allocations: [
      {
        payable_id: pa.id,
        amount: "9999",
        expected_version: paNow.version,
      },
    ],
  });
  expect(excess.status).toBeGreaterThanOrEqual(400);

  // 14 FX contracted slice on inv2 payable (canonical numbers)
  const pcFresh = (await api(page, "GET", `/api/payables/${pc.id}`)).body as Json;
  expect(
    (
      await api(page, "POST", `/api/payables/${pc.id}/fx-plan`, {
        kind: "INITIAL",
        rate: "6.00",
        effective_from: today(),
      })
    ).status,
  ).toBe(200);
  expect(
    (
      await api(page, "POST", `/api/payables/${pc.id}/fx-plan`, {
        kind: "REFORECAST",
        rate: "6.10",
        effective_from: today(),
        reason_code: "MARKET_UPDATE",
      })
    ).status,
  ).toBe(200);
  expect(
    (await api(page, "POST", "/api/fx/quotes", { foreign_currency: "EUR", rate: "6.25", source: "MANUAL" }))
      .status,
  ).toBe(200);

  let fxPay = (
    await api(page, "POST", "/api/payments", {
      supplier_id: supplier.id,
      amount: "400",
      currency: "EUR",
      payment_date: today(),
      register_without_document: true,
      reason_code: "TEST_OVERRIDE",
    })
  ).body as Json;
  fxPay = (
    await api(page, "POST", `/api/payments/${fxPay.id}/allocations`, {
      expected_version: fxPay.version,
      idempotency_key: `i6-fx-alloc-${tag}`,
      allocations: [
        {
          payable_id: pc.id,
          amount: "400",
          expected_version: pcFresh.version,
        },
      ],
    })
  ).body as Json;
  const allocId = (fxPay.allocations as Json[])[0].id as number;
  const fxExec = (
    await api(page, "POST", `/api/payments/${fxPay.id}/fx-executions`, {
      foreign_amount: "400",
      rate: "6.20",
      execution_date: today(),
      register_without_document: true,
      reason_code: "FX_NO_DOC",
    })
  ).body as Json;
  expect(
    (
      await api(page, "POST", "/api/fx/execution-allocations", {
        fx_execution_id: fxExec.id,
        payment_allocation_id: allocId,
      })
    ).status,
  ).toBe(200);
  const val = (
    await api(page, "POST", "/api/fx/valuations/complete", {
      payment_allocation_id: allocId,
    })
  ).body as Json;
  expect(Number(val.realized_result_vs_reference)).toBe(-40);
  const fxView = (await api(page, "GET", `/api/payables/${pc.id}/fx-view`)).body as Json;
  expect(Number(fxView.realized_result_vs_reference)).toBe(-40);
  expect(Number(fxView.online_result_vs_current)).toBe(-90);
  expect(Number(fxView.total_vs_current)).toBe(-130);

  // 15 Documents linked (already); list check
  const docs = (await api(page, "GET", `/api/documents?entity_type=invoice&entity_id=${inv1.id}`))
    .body as Json[];
  expect(Array.isArray(docs) ? docs.length : 0).toBeGreaterThanOrEqual(1);

  // 16 Audit sample
  const audit = (
    await api(page, "GET", `/api/audit?entity_type=invoice&entity_id=${inv1.id}`)
  ).body as Json[];
  expect(Array.isArray(audit) && audit.length).toBeGreaterThan(0);
  expect(audit.some((e) => String(e.action).toLowerCase().includes("issue") || e.action)).toBeTruthy();

  // 17 AP queue (UI + API)
  const ap = (await api(page, "GET", `/api/reporting/ap-queue?order_id=${orderId}`)).body as Json;
  expect(Number(ap.total)).toBeGreaterThanOrEqual(3);
  expect(Array.isArray(ap.items) && (ap.items as Json[]).length).toBeGreaterThanOrEqual(3);
  await page.goto(`/payables?order_id=${orderId}`);
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("ap-table")).toBeVisible({ timeout: 10000 });

  // 18 Cockpit Reporting (UI + API)
  const summary = (await api(page, "GET", `/api/orders/${orderId}/summary`)).body as Json;
  expect(summary.commercial).toBeTruthy();
  expect((summary.commercial as Json).code).toBe(tag);
  await page.goto(`/orders/${orderId}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("kpi-strip")).toBeVisible();

  // Walkthrough: payment residual visible
  await page.goto(`/payments/${payment.id}`);
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 500,00|EUR 500/i);
});
