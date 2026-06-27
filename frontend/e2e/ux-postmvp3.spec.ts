import { expect, test } from "@playwright/test";
import { getDemoImportationId } from "./helpers";

test.describe("Epic — UX pós-MVP 3", () => {
  test("financeiro global — fila de contas a pagar", async ({ page }) => {
    await page.goto("/financeiro", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Fila de contas a pagar/i })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator(".order-queue__filter").first()).toBeVisible({ timeout: 15000 });
  });

  test("hub importação — resumo operacional", async ({ page }) => {
    const demoId = await getDemoImportationId(page);
    await page.goto(`/importacoes/${demoId}/resumo`);
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: /a despachar · preço e desconto/i })).toBeVisible({ timeout: 20000 });
  });

  test("demo guiada abre cenários", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByRole("heading", { name: /Roteiro de demonstração/i })).toBeVisible();
    await expect(page.getByText("Marítima simples")).toBeVisible();
    await page.getByRole("button", { name: "Abrir cenário" }).first().click();
    await expect(page).toHaveURL(/\/importacoes\/\d+/);
  });

  test("dashboard — demo link e widgets", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("link", { name: "Demo Epic" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: /Painel de controle/i })).toBeVisible({ timeout: 15000 });
    const body = await page.locator("body").innerText();
    expect(body).not.toContain("R$ 1,84 mil");
  });

  test("aba financeiro importação — despesas", async ({ page }) => {
    const demoId = await getDemoImportationId(page);
    await page.goto(`/importacoes/${demoId}/financeiro`);
    await page.getByRole("tab", { name: "Despesas Brasil" }).click();
    await expect(page.getByText("Entra no landed cost")).toBeVisible({ timeout: 15000 });
  });
});
