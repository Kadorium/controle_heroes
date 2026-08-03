import { test, expect } from "@playwright/test";

test("Inc-2 billing issue flow", async ({ page }) => {
  const code = `BILL-${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({ timeout: 15000 });

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
  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });

  await page.getByTestId("new-invoice-number").fill(`F-${code}`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });

  await page.getByTestId("discount-type-0").selectOption("PERCENT");
  await page.getByTestId("discount-pct-0").fill("10");
  await page.getByTestId("save-items").click();
  await expect(page.getByTestId("invoice-net")).toContainText("EUR 900,00");

  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 epic"),
  });
  await page.waitForTimeout(500);

  const today = new Date();
  const d1 = today.toISOString().slice(0, 10);
  const d2 = new Date(today.getTime() + 30 * 86400000).toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("PERCENT");
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-pct-0").fill("30");
  await page.getByTestId("term-date-1").fill(d2);
  await page.getByTestId("term-pct-1").fill("70");
  await page.getByTestId("save-terms").click();
  await expect(page.getByTestId("payables-preview")).toContainText("EUR 270,00");

  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("payables-list")).toContainText("EUR 270,00");
  await expect(page.getByTestId("payables-list")).toContainText("EUR 630,00");

  await expect(page.getByTestId("discount-type-0")).toHaveCount(0);

  await page.getByLabel("Principal").getByRole("link", { name: /^faturas$/i }).click();
  await expect(page.getByTestId("invoices-list")).toBeVisible();
  await expect(page.getByTestId("invoices-table")).toBeVisible();
  await expect(page.getByText(`F-${code}`)).toBeVisible();

  await page.getByLabel("Principal").getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible();
});
