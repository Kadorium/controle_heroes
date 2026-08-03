import { test, expect } from "@playwright/test";

test("Inc-3 payment allocate flow", async ({ page }) => {
  const code = `PAY-${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({ timeout: 15000 });

  // Create CONFIRMED order 13 x 100 → invoice 600+700
  await page.getByRole("main").getByRole("link", { name: /novo pedido/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("13");
  await page.getByTestId("line-price").fill("100");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("cockpit-commercial-link").click();
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
  const d2 = new Date(Date.now() + 86400000 * 30).toISOString().slice(0, 10);
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("600");
  await page.getByTestId("term-date-1").fill(d2);
  await page.getByTestId("term-amt-1").fill("700");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });

  // Payment 1000
  await page.getByLabel("Principal").getByRole("link", { name: /pagamentos/i }).click();
  await page.getByTestId("new-payment").click();
  await page.getByTestId("pay-supplier").selectOption({ label: `Fornecedor ${code}` });
  await page.getByTestId("pay-amount").click();
  await page.getByTestId("pay-amount").fill("1000");
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-recibo"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 1\.000,00|EUR 1000/i);

  const table = page.getByTestId("eligible-table");
  await expect(table).toBeVisible();
  // Payable A €600 first (sorted by due date / id); alocar 400
  const firstAmt = table.locator("tbody tr").nth(0).locator("input");
  await firstAmt.click();
  await firstAmt.fill("400");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 600,00/i, { timeout: 10000 });

  // Alocar 300 no payable que ainda tem saldo ≥300 (B €700)
  const rowB = table.locator("tbody tr").filter({ hasText: /700/ });
  const amtB = rowB.locator("input");
  await amtB.click();
  await amtB.fill("300");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 300,00/i, { timeout: 10000 });

  await firstAmt.click();
  await firstAmt.fill("9999");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-detail").locator(".error")).toBeVisible();
});
