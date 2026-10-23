import { test, expect } from "@playwright/test";
test.skip(process.env.DEMO_NORMAL_BUILD !== "true", "Dedicated tour-disabled build only");
test.use({ viewport: { width: 1366, height: 768 } });

test("normal build: login validation, safe return, logout and tour absent", async ({ page }) => {
  expect((await (await page.request.get("/api/health")).json()).logical_database).toBe("epic_v2_test");
  await page.goto("/login?next=/invoices/1");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("incorrect-demo-password");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  await expect(page.getByTestId("demo-start")).toHaveCount(0);
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.goto("/login?next=https://example.invalid");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page).toHaveURL(/\/orders$/);
  expect(new URL(page.url()).hostname).toBe("127.0.0.1");
});

test("normal build: AP drawer, invoice filter, stock origin and operational customs copy", async ({ page }) => {
  await page.request.post("/api/auth/dev-login");
  await page.goto("/payables");
  const table = page.getByTestId("ap-table"); await expect(table).toContainText("1.200");
  await table.locator("tbody tr").first().click();
  await expect(page.getByRole("dialog")).toContainText("DEMO-FAT-20261022");
  await page.keyboard.press("Escape"); await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.goto("/invoices");
  await expect(page.getByTestId("invoices-table")).toContainText("DEMO-FAT-20261022");
  await page.getByTestId("invoices-status-DRAFT").click();
  await expect(page.locator("#main-content")).toContainText("Nenhuma fatura neste filtro");
  await page.getByTestId("invoices-status-all").click();
  await expect(page.getByTestId("invoices-table")).toContainText("DEMO-FAT-20261022");
  await page.goto("/inventory/sku/1");
  await expect(page.getByTestId("sku-bucket-available_qty")).toContainText("6");
  await page.goto("/inventory/movements?product_id=1");
  await expect(page.locator("#main-content")).toContainText("DOMESTIC-MAIN");
  await page.goto("/customs/1");
  await expect(page.getByTestId("customs-detail-ext")).toContainText("DEMO-DI-20261022");
  await expect(page.locator("#main-content")).not.toContainText("L-007");
  await expect(page.locator("#main-content")).not.toContainText("corpus");
  await expect(page.getByTestId("demo-start")).toHaveCount(0);
});
