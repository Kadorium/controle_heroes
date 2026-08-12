/**
 * I5-5 smoke — navegação UX Aduana + Estoque (sem campanha I5-6).
 */
import { test, expect } from "@playwright/test";

test("I5-5 customs list/detail + inventory nav smoke", async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByRole("link", { name: /processos aduaneiros/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^estoque$/i })).toBeVisible();

  await nav.getByRole("link", { name: /processos aduaneiros/i }).click();
  await expect(page.getByTestId("customs-list-page")).toBeVisible();
  await expect(page.getByTestId("kpi-strip")).toBeVisible();
  await expect(page.getByTestId("breadcrumb")).toContainText(/processos/i);

  const firstRow = page.getByTestId("customs-table").locator("a").first();
  if (await firstRow.count()) {
    await firstRow.click();
    await expect(page.getByTestId("customs-detail-page")).toBeVisible();
    await expect(page.getByTestId("customs-section-resumo")).toBeVisible();
    await expect(page.getByTestId("customs-section-numerario")).toBeVisible();
    await expect(page.getByTestId("customs-section-liberacoes")).toBeVisible();
    await expect(page.getByTestId("customs-section-audit")).toBeVisible();
    await expect(page.getByTestId("breadcrumb")).toBeVisible();
  }

  await nav.getByRole("link", { name: /^estoque$/i }).click();
  await expect(page.getByTestId("inventory-movements-page")).toBeVisible();
  await expect(page.getByLabel(/produto/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /filtrar/i })).toBeVisible();
});
