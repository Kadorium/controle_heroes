import { test, expect } from "@playwright/test";

test("J6 nav Custos e fila", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByText(/^Custos$/i)).toBeVisible({ timeout: 15000 });
  await nav.getByRole("link", { name: /custos de importação/i }).click();
  await expect(page).toHaveURL(/\/costing/);
  await expect(page.getByTestId("costing-queue")).toBeVisible();
  await expect(
    page.getByText(/Não representa tratamento contábil ou fiscal de recuperabilidade/i),
  ).toBeVisible();
});

test("J6 expense e compare pela UI (fixture sintética)", async ({ page, request }) => {
  test.setTimeout(180_000);
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({ timeout: 15000 });

  // Fixture mínima via API (preparação). Depois: ZERO mutação Costing fora da UI.
  const tag = `J6E2E-${Date.now()}`;
  const login = await request.post("/api/auth/login", {
    data: { email: "admin@epic.com.br", password: "admin123" },
  });
  expect(login.ok()).toBeTruthy();
  const supplier = await (await request.post("/api/suppliers", { data: { name: `S-${tag}`, country_code: "IT" } })).json();
  const pa = await (await request.post("/api/products", { data: { sku: `A-${tag}`, description: "A" } })).json();
  const pb = await (await request.post("/api/products", { data: { sku: `B-${tag}`, description: "B" } })).json();
  let order = await (
    await request.post("/api/orders", { data: { code: `ORD-${tag}`, supplier_id: supplier.id, currency: "EUR" } })
  ).json();
  for (const prod of [pa, pb]) {
    order = await (
      await request.post(`/api/orders/${order.id}/items`, {
        data: {
          expected_version: order.version,
          product_id: prod.id,
          quantity: "10",
          unit_price: "100",
        },
      })
    ).json();
  }
  order = await (await request.post(`/api/orders/${order.id}/confirm`, { data: { expected_version: order.version } })).json();
  let inv = await (
    await request.post(`/api/orders/${order.id}/invoices`, {
      data: { invoice_number: `INV-${tag}`, invoice_type: "FINAL" },
    })
  ).json();
  inv = await (
    await request.put(`/api/invoices/${inv.id}/items`, {
      data: {
        expected_version: inv.version,
        items: order.items.map((oi: { id: number }) => ({
          order_item_id: oi.id,
          quantity: "10",
          unit_price_gross: "100",
          discount_type: "PERCENT",
          discount_percent: "0",
        })),
      },
    })
  ).json();
  const due = new Date(Date.now() + 86400000 * 30).toISOString().slice(0, 10);
  inv = await (
    await request.put(`/api/invoices/${inv.id}/terms`, {
      data: {
        expected_version: inv.version,
        mode: "PERCENT",
        terms: [{ due_date: due, percent: "100" }],
      },
    })
  ).json();
  const pdf = Buffer.from("%PDF-1.4 e2e");
  await request.post("/api/documents", {
    multipart: {
      file: { name: "f.pdf", mimeType: "application/pdf", buffer: pdf },
      entity_type: "invoice",
      entity_id: String(inv.id),
      role: "official",
    },
  });
  inv = await (await request.get(`/api/invoices/${inv.id}`)).json();
  inv = await (await request.post(`/api/invoices/${inv.id}/issue`, { data: { expected_version: inv.version } })).json();
  for (const pay of inv.payables || []) {
    await request.post(`/api/payables/${pay.id}/fx-plan`, {
      data: { kind: "INITIAL", rate: "6.00", effective_from: new Date().toISOString().slice(0, 10) },
    });
  }
  const provider = await (
    await request.post("/api/logistics-providers", {
      data: { legal_name: `FWD-${tag}`, provider_type: "TRANSPORTADOR", active: true },
    })
  ).json();
  let sh = await (await request.post("/api/shipments", { data: { modal: "SEA", logistics_provider_id: provider.id } })).json();
  for (const oi of order.items) {
    sh = await (
      await request.post(`/api/shipments/${sh.id}/items`, {
        data: { expected_version: sh.version, order_item_id: oi.id, quantity: "10" },
      })
    ).json();
  }
  let proc = await (await request.post("/api/import-processes", { data: { external_reference: `MOCK-${tag}` } })).json();
  proc = await (
    await request.post(`/api/import-processes/${proc.id}/invoices`, {
      data: { expected_version: proc.version, invoice_id: inv.id },
    })
  ).json();
  for (const item of inv.items) {
    proc = await (
      await request.post(`/api/import-processes/${proc.id}/invoice-items/allocate`, {
        data: {
          expected_version: proc.version,
          invoice_item_id: item.id,
          allocated_qty: item.quantity,
        },
      })
    ).json();
  }
  proc = await (
    await request.post(`/api/import-processes/${proc.id}/shipments`, {
      data: { expected_version: proc.version, shipment_id: sh.id },
    })
  ).json();
  for (const item of sh.items) {
    proc = await (
      await request.post(`/api/import-processes/${proc.id}/shipment-items/allocate`, {
        data: {
          expected_version: proc.version,
          shipment_item_id: item.id,
          allocated_qty: item.quantity,
        },
      })
    ).json();
  }
  const payee = await (await request.post("/api/customs/payees", { data: { name: `P-${tag}` } })).json();
  let fr = await (
    await request.post(`/api/import-processes/${proc.id}/funding-requests`, {
      data: {
        payee_id: payee.id,
        currency: "BRL",
        declared_total: "100.00",
        due_date: due,
        notes: "MOCK e2e",
      },
    })
  ).json();
  fr = await (
    await request.put(`/api/import-processes/${proc.id}/funding-requests/${fr.id}/value-bases`, {
      data: {
        expected_version: fr.version,
        lines: [{ position: 1, label: "FOB", code: "FOB", amount: "2000", currency: "EUR" }],
      },
    })
  ).json();
  await request.put(`/api/import-processes/${proc.id}/funding-requests/${fr.id}/tax-lines`, {
    data: {
      expected_version: fr.version,
      lines: [{ position: 1, label: "II", code: "II", amount: "100" }],
    },
  });
  const cse = await (await request.post("/api/costing/cases", { data: { process_id: proc.id } })).json();

  await page.goto(`/costing/${cse.id}`);
  await expect(page.getByTestId("costing-workspace")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("costing-tolerance-notice")).toBeVisible();
  await page.getByTestId("costing-kind").selectOption("REVISED");
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/recalculate") && r.request().method() === "POST"),
    page.getByTestId("costing-recalc").click(),
  ]);
  await expect(page.getByTestId("costing-included-total")).toContainText("12100", { timeout: 20000 });
  await page.getByTestId("costing-publish-reason").fill("e2e publish v1");
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/publish") && r.request().method() === "POST" && r.ok()),
    page.getByTestId("costing-publish").click(),
  ]);
  await expect(page.getByTestId("costing-revise")).toBeVisible({ timeout: 15000 });

  await page.getByTestId("costing-revise").click();
  await expect(page.getByTestId("costing-expense-add")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("costing-expense-add").click();
  await page.getByTestId("expense-description").fill("Despesa ensaio E2E");
  await page.getByTestId("expense-amount").fill("50.00");
  await page.getByTestId("expense-document").setInputFiles({
    name: "recibo-ensaio-mock.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 ensaio-expense"),
  });
  await page.getByTestId("expense-save").click();
  await expect(page.getByTestId("costing-preview-stale")).toBeVisible({ timeout: 15000 });
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/recalculate") && r.request().method() === "POST"),
    page.getByTestId("costing-recalc").click(),
  ]);
  await expect(page.getByTestId("costing-included-total")).toContainText("12150", { timeout: 20000 });
  await page.getByTestId("costing-publish-reason").fill("e2e publish v2");
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/publish") && r.request().method() === "POST" && r.ok()),
    page.getByTestId("costing-publish").click(),
  ]);
  await expect
    .poll(async () => page.locator("[data-testid^=costing-compare-left-]").count(), { timeout: 20000 })
    .toBeGreaterThanOrEqual(2);

  const leftIds = await page.locator("[data-testid^=costing-compare-left-]").evaluateAll((els) =>
    els.map((e) => e.getAttribute("data-testid")),
  );
  const rightIds = await page.locator("[data-testid^=costing-compare-right-]").evaluateAll((els) =>
    els.map((e) => e.getAttribute("data-testid")),
  );
  await page.getByTestId(leftIds[leftIds.length - 1]!).click();
  await page.getByTestId(rightIds[0]!).click();
  await expect(page.getByTestId("costing-compare-open")).toHaveAttribute("href", /compare/);
  await page.getByTestId("costing-compare-open").click();
  await expect(page.getByTestId("costing-compare-page")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("costing-compare-total-delta")).toContainText(/50,00/);
  await page.getByTestId("costing-compare-diffs-only").check();
  await expect(page.getByTestId("costing-compare-components")).toContainText(/Despesa|OUTRAS/i);
});
