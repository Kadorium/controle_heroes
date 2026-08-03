import { test, expect } from "@playwright/test";

/**
 * I9-0 shell TARGET — navegação Compras/Financeiro.
 * Roda apenas via npm run e2e (epic_v2_test @ 8082).
 */
test("I9-0 App Shell nav TARGET", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByText(/^Compras$/i)).toBeVisible({ timeout: 15000 });
  await expect(nav.getByText(/^Financeiro$/i)).toBeVisible();

  await expect(nav.getByRole("link", { name: /^Pedidos$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Faturas$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /contas a pagar/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Pagamentos$/i })).toBeVisible();

  // Novo pedido NÃO é item de sidebar — CTA contextual na fila
  await expect(nav.getByRole("link", { name: /novo pedido/i })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /^\/fx$/ })).toHaveCount(0);
  await expect(nav.locator('a[href="/fx"]')).toHaveCount(0);

  await expect(page.getByRole("main").getByRole("link", { name: /novo pedido/i })).toBeVisible();

  await nav.getByRole("link", { name: /^Faturas$/i }).click();
  await expect(page).toHaveURL(/\/invoices/);

  await nav.getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page).toHaveURL(/\/payables/);

  await nav.getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page).toHaveURL(/\/payments/);

  await nav.getByRole("link", { name: /^Pedidos$/i }).click();
  await expect(page).toHaveURL(/\/orders/);
});
