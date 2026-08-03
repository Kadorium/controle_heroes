import { test, expect } from "@playwright/test";

test("Inc-5 AP queue + order cockpit (Reporting)", async ({ page }) => {
  const code = `INC5-${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /contas a pagar/i })).toBeVisible({ timeout: 15000 });

  await page.getByRole("main").getByRole("link", { name: /novo pedido/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("100");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("kpi-strip")).toBeVisible();

  const orderUrl = page.url();
  const orderId = Number(orderUrl.match(/orders\/(\d+)/)?.[1]);
  expect(orderId).toBeGreaterThan(0);

  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible();
  await expect(page.getByTestId("order-detail")).toBeVisible();

  await page.getByTestId("new-invoice-number").fill(`F-${code}`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("discount-type-0").selectOption("NONE");
  await page.getByTestId("save-items").click();
  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  await page.waitForTimeout(400);
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  const d1 = new Date().toISOString().slice(0, 10);
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("1000");
  await page.getByTestId("save-terms").click();
  await expect(page.getByTestId("invoice-blockers")).toHaveCount(0, { timeout: 10000 });
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });

  await page.goto(`/orders/${orderId}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("kpi-strip")).toContainText(/Pago/i);

  await page.goto(`/payables?order_id=${orderId}`);
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("kpi-strip")).toBeVisible();
  await expect(page.getByTestId("ap-filter-order")).toHaveValue(String(orderId));
  await expect(page.getByTestId("ap-table")).toBeVisible({ timeout: 10000 });
  await expect(page.locator(`[data-testid^="ap-row-"]`)).toHaveCount(1, { timeout: 10000 });

  const summary = await page.evaluate(async (oid) => {
    const r = await fetch(`/api/orders/${oid}/summary`, { credentials: "include" });
    return { status: r.status, body: await r.json() };
  }, orderId);
  expect(summary.status).toBe(200);
  expect(summary.body.kpis?.paid).toBeTruthy();
  expect(summary.body.commercial?.code).toBe(code);
});
