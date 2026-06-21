import { expect, test } from "@playwright/test";

const ADMIN = { email: "admin@epic.com.br", password: "admin123" };

/** Valores fictícios do mock-redesign-v2.html que não devem aparecer como métricas reais. */
const MOCK_FAKE_VALUES = ["R$ 1,84", "R$ 162,6 mil", "R$ 12.300", "R$ 108,4 mil"];

test.describe("Epic Importações — smoke E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/e-mail|email/i).fill(ADMIN.email);
    await page.getByLabel(/senha|password/i).fill(ADMIN.password);
    await page.getByRole("button", { name: /entrar|login/i }).click();
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await page.request.post("/api/demo/seed");
  });

  test("topbar com itens principais", async ({ page }) => {
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
    const seedRes = await page.request.post("/api/demo/seed");
    expect(seedRes.ok()).toBeTruthy();

    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Fila de ordens|Ordens/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator(".order-queue__row, .row__po").first()).toBeVisible({ timeout: 45000 });
    await page.locator(".order-queue__row").first().click();
    const sidebar = page.getByRole("complementary");
    await expect(sidebar.getByRole("link", { name: "Visão Geral", exact: true })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Faturas e pagamentos" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Crédito / conta corrente" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Logística" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Aduana e custos BR" })).toBeVisible();
    await expect(sidebar.getByRole("link", { name: "Conciliação e fechamento" })).toBeVisible();
  });

  test("conciliação/fechamento e aduaneiro", async ({ page }) => {
    await page.request.post("/api/demo/seed");

    const impsRes = await page.request.get("/api/importations");
    expect(impsRes.ok()).toBeTruthy();
    const imps = await impsRes.json();
    const demo = imps.find((i: { po_number: string }) => i.po_number.startsWith("DEMO-"));
    expect(demo?.id).toBeTruthy();

    await page.goto(`/importacoes/${demo.id}/conciliacao`);
    await expect(page.getByRole("button", { name: /Executar conciliações/i })).toBeVisible({
      timeout: 15000,
    });

    await page.goto(`/importacoes/${demo.id}/aduaneiro`);
    await expect(page.locator("#di-duimp")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#landed-cost")).toBeVisible();
  });
});
