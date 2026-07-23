import { test, expect } from "@playwright/test";

test("Inc-1 order flow", async ({ page }) => {
  const code = `E2E-${Date.now()}`;
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /ordens/i })).toBeVisible({ timeout: 15000 });

  await page.getByRole("main").getByRole("link", { name: /nova ordem/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(500);
  await page.getByTestId("line-qty").fill("2");
  await page.getByTestId("line-price").fill("15.00");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await expect(page.getByTestId("commercial-total")).toContainText("30.0000");
  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("readonly-banner")).toBeVisible();
  await expect(page.getByText(`Ordem ${code}`)).toBeVisible();

  await page.getByRole("link", { name: /fila/i }).click();
  await expect(page.getByRole("link", { name: code })).toBeVisible();
});
