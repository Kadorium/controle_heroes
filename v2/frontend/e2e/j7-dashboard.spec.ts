import { test, expect } from "@playwright/test";

test("Painel UX2 — Executiva, Comercial e Controle", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByRole("link", { name: /^Painel$/i })).toBeVisible();
  await expect(page.getByTestId("dashboard-page")).toBeVisible();
  await expect(page.getByText("O que espera por você")).toBeVisible();
  await expect(page.getByText("Caixa nos próximos meses")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Fila AP");
  await expect(page.locator("body")).not.toContainText("Qualidade do cadastro");
  await expect(page.locator("body")).not.toContainText("Fluxo da importação");

  await page.getByRole("button", { name: /o que é o que espera por você/i }).click();
  const dlg = page.getByTestId("explainer-dialog");
  await expect(dlg).toBeVisible();
  await expect(dlg).not.toContainText("attention.inbox");
  await dlg.getByRole("button", { name: /fechar/i }).click();

  await page.goto("/dashboard?view=comercial");
  await expect(page).toHaveURL(/view=comercial/);
  await expect(page.getByTestId("commercial-table")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Disponível para oferecer")).toBeVisible();

  await page.goto("/dashboard?view=controle");
  await expect(page.getByTestId("control-exceptions")).toBeVisible({ timeout: 15000 });

  await page.goto("/dashboard?view=financeiro&currency=EUR");
  await expect(page).toHaveURL(/view=financeiro/);
  await expect(page.getByTestId("aging-bar")).toBeVisible();
});
