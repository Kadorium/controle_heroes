import { test, expect } from "@playwright/test";
import {
  fillAndConfirmOrder,
  fillMoneyInput,
  issueInvoiceFromUi,
  loginAs,
  PAYMENTS_NAV,
} from "./helpers/orderCreate";

test("Inc-3 payment allocate flow", async ({ page }) => {
  test.setTimeout(120_000);
  const code = `PAY-${Date.now()}`;
  await loginAs(page);
  await fillAndConfirmOrder(page, {
    code,
    supplierName: `Fornecedor ${code}`,
    sku: `SKU-${code}`,
    description: `Produto ${code}`,
    qty: "13",
    price: "100",
  });
  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });

  await page.getByTestId("new-invoice-number").fill(`F-${code}`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("discount-type-0").selectOption("NONE");
  await page.getByTestId("save-items").click();
  const docUploaded = page.waitForResponse(
    (r) => r.url().includes("/documents") && r.request().method() === "POST" && r.ok(),
  );
  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  await docUploaded;
  await expect(page.getByText("fattura.pdf")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  const d1 = new Date().toISOString().slice(0, 10);
  const d2 = new Date(Date.now() + 86400000 * 30).toISOString().slice(0, 10);
  await page.getByTestId("term-date-0").fill(d1);
  await fillMoneyInput(page, page.getByTestId("term-amt-0"), "600");
  await page.getByTestId("term-date-1").fill(d2);
  await fillMoneyInput(page, page.getByTestId("term-amt-1"), "700");
  const termsSaved = page.waitForResponse(
    (r) => r.url().includes("/terms") && r.request().method() === "PUT" && r.ok(),
  );
  await page.getByTestId("save-terms").click();
  await termsSaved;
  await expect(page.getByTestId("save-terms")).toBeEnabled();
  await issueInvoiceFromUi(page);

  // Payment 1000
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: PAYMENTS_NAV }).click();
  await page.getByTestId("new-payment").click();
  await page.getByTestId("pay-supplier").selectOption({ label: `Fornecedor ${code}` });
  await fillMoneyInput(page, page.getByTestId("pay-amount"), "1000");
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
  await fillMoneyInput(page, firstAmt, "400");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 600,00/i, { timeout: 10000 });

  // Alocar 300 no payable que ainda tem saldo ≥300 (B €700)
  const rowB = table.locator("tbody tr").filter({ hasText: /700/ });
  const amtB = rowB.locator("input");
  await fillMoneyInput(page, amtB, "300");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 300,00/i, { timeout: 10000 });

  await fillMoneyInput(page, table.locator("tbody tr").nth(0).locator("input"), "9999");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-detail").locator(".error")).toBeVisible();
});
