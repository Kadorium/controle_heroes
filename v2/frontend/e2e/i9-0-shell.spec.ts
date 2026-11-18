import { loginAs, expandNavigation } from "./helpers/orderCreate";
import { test, expect } from "@playwright/test";

/**
 * I9-0 shell TARGET — navegação Compras/Financeiro.
 * Executar somente com backend/banco de teste verificados (porta não prova isolamento).
 */
test("I9-0 App Shell nav TARGET", async ({ page }) => {
  await loginAs(page);

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByText(/^Compras$/i)).toBeVisible({ timeout: 15000 });
  await expect(nav.getByText(/^Financeiro$/i)).toBeVisible();

  await expect(nav.getByRole("link", { name: /^Compras$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Visão geral$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Produtos$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Importações$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Financeiro$/i })).toBeVisible();

  // Novo pedido NÃO é item de sidebar — CTA contextual na fila
  await expect(nav.getByRole("link", { name: /novo pedido/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /^\/fx$/ })).toHaveCount(0);
  await expect(nav.locator('a[href="/fx"]')).toHaveCount(0);

  await expect(page).toHaveURL(/\/dashboard/);
  await nav.getByRole("link", { name: /^Compras$/i }).click();
  await expect(page.getByTestId("orders-new-cta")).toBeVisible();

  await page.locator(".area-navigation").getByRole("link", { name: /^Faturas$/i }).click();
  await expect(page).toHaveURL(/\/invoices/);

  await nav.getByRole("link", { name: /^Financeiro$/i }).click();
  await expect(page).toHaveURL(/\/payables/);

  await page.locator(".area-navigation").getByRole("link", { name: /^Pagamentos realizados$/i }).click();
  await expect(page).toHaveURL(/\/payments/);

  await expandNavigation(page);
  await nav.getByRole("link", { name: /^Compras$/i }).click();
  await expect(page).toHaveURL(/\/orders/);
});
