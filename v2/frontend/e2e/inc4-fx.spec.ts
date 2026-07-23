import { test, expect } from "@playwright/test";

test("Inc-4 FX three views canonical path", async ({ page }) => {
  const code = `FX-${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /ordens/i })).toBeVisible({ timeout: 15000 });

  // Order 10 x 100 = 1000
  await page.getByRole("main").getByRole("link", { name: /nova ordem/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("100");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });

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
  page.once("dialog", (d) => d.accept());
  await page.getByTestId("issue-invoice").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });

  // Payable id da fatura emitida
  const invoiceUrl = page.url();
  const invoiceId = Number(invoiceUrl.match(/invoices\/(\d+)/)?.[1]);
  const payables = await page.evaluate(async (invId) => {
    const r = await fetch(`/api/payables?invoice_id=${invId}`, { credentials: "include" });
    return r.json();
  }, invoiceId);
  const payableId = payables[0].id as number;

  await page.goto(`/payables/${payableId}/fx`);
  await expect(page.getByTestId("payable-fx-panel")).toBeVisible({ timeout: 10000 });

  await page.getByTestId("fx-plan-kind").selectOption("INITIAL");
  await page.getByTestId("fx-plan-rate").fill("6.00");
  await page.getByTestId("fx-plan-save").click();
  await expect(page.getByTestId("payable-fx-panel")).toContainText("6.000000", { timeout: 8000 });

  await page.getByTestId("fx-plan-kind").selectOption("REFORECAST");
  await page.getByTestId("fx-plan-rate").fill("6.10");
  await page.getByTestId("fx-plan-reason").fill("MARKET_UPDATE");
  await page.getByTestId("fx-plan-save").click();
  await expect(page.getByTestId("payable-fx-panel")).toContainText("6.100000", { timeout: 8000 });

  await page.getByTestId("fx-manual-rate").fill("6.25");
  await page.getByTestId("fx-manual-save").click();
  await expect(page.getByTestId("payable-fx-panel")).toContainText("6.250000", { timeout: 8000 });

  // Payment + allocate 400 no payable planejado
  await page.getByLabel("Principal").getByRole("link", { name: /pagamentos/i }).click();
  await page.getByTestId("new-payment").click();
  await page.getByTestId("pay-supplier").selectOption({ label: `Fornecedor ${code}` });
  await page.getByTestId("pay-amount").fill("400");
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-recibo"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });

  const table = page.getByTestId("eligible-table");
  await expect(table).toBeVisible();
  await table.locator("tbody tr").filter({ hasText: `#${payableId}` }).locator("input").fill("400");
  page.once("dialog", (d) => d.accept());
  await page.getByTestId("allocate-btn").click();
  await expect(page.getByText(/Residual 0/i)).toBeVisible({ timeout: 10000 });

  // FX execution @ 6.20
  await expect(page.getByTestId("payment-fx-panel")).toBeVisible();
  await page.getByTestId("fx-exec-amount").fill("400");
  await page.getByTestId("fx-exec-rate").fill("6.20");
  await page.getByTestId("fx-exec-doc").setInputFiles({
    name: "fx.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-fx"),
  });
  await page.getByTestId("fx-exec-save").click();
  await expect(page.getByTestId("fx-exec-list")).toContainText("6.20", { timeout: 10000 });
  await expect(page.getByTestId("fx-alloc-vals")).toContainText("-40", { timeout: 10000 });

  await page.goto(`/payables/${payableId}/fx`);
  await expect(page.getByTestId("payable-fx-panel")).toBeVisible();
  await expect(page.getByTestId("payable-fx-panel")).toContainText("-40.00");
  await expect(page.getByTestId("payable-fx-panel")).toContainText("-90.00");
  await expect(page.getByTestId("payable-fx-panel")).toContainText("-130.00");
});
