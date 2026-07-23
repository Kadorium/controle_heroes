import { expect, test } from "@playwright/test";
import { getDemoImportationId } from "./helpers";

/** Valores fictícios do mock-redesign-v2.html que não devem aparecer como métricas reais. */
const MOCK_FAKE_VALUES = ["R$ 1,84", "R$ 162,6 mil", "R$ 12.300", "R$ 108,4 mil"];

test.describe("Epic Importações — smoke E2E", () => {
  test("topbar com itens principais", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Painel" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ordens" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Financeiro" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Demo Epic" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Cadastros" })).toBeVisible();
  });

  test("dashboard carrega sem números fake do mock", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Painel de controle/i })).toBeVisible({ timeout: 30000 });
    const body = await page.locator("body").innerText();
    for (const fake of MOCK_FAKE_VALUES) {
      expect(body).not.toContain(fake);
    }
    await page.getByRole("button", { name: "Personalizar" }).click();
    await expect(page.getByRole("heading", { name: /Personalizar painel/i })).toBeVisible();
  });

  test("lista e detalhe de importação demo", async ({ page }) => {
    const queueReady = page.waitForResponse(
      (r) => r.url().includes("/api/importations/order-queue") && r.ok(),
      { timeout: 120_000 }
    );
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await queueReady;
    await expect(page.getByRole("heading", { name: /^Ordens$/i })).toBeVisible({ timeout: 20000 });
    const firstOpen = page.locator(".sheet-grid__open").first();
    await expect(firstOpen).toBeVisible({ timeout: 15000 });
    await firstOpen.click();
    const sidebar = page.getByRole("complementary");
    await expect(sidebar.getByRole("link", { name: "Visão Geral", exact: true })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Faturas e pagamentos" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Crédito / conta corrente" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Logística" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Aduana e custos BR" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Conciliação e fechamento" })).toBeVisible();
  });

  test("conciliação/fechamento e aduaneiro", async ({ page }) => {
    const demoId = await getDemoImportationId(page);

    await page.goto(`/importacoes/${demoId}/conciliacao`);
    await expect(page.getByRole("button", { name: /Executar conciliações/i })).toBeVisible({
      timeout: 15000,
    });

    await page.goto(`/importacoes/${demoId}/aduaneiro`);
    await expect(page.locator("#di-duimp")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#landed-cost")).toBeVisible();
  });
});
