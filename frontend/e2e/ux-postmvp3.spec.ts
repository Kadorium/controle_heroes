import { expect, test } from "@playwright/test";

const ADMIN = { email: "admin@epic.com.br", password: "admin123" };

test.describe("Epic — UX pós-MVP 3", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/e-mail|email/i).fill(ADMIN.email);
    await page.getByLabel(/senha|password/i).fill(ADMIN.password);
    await page.getByRole("button", { name: /entrar|login/i }).click();
    await expect(page).toHaveURL(/\/(\?.*)?$/);
    await page.request.post("/api/demo/seed");
  });

  test("financeiro global — fila de contas a pagar", async ({ page }) => {
    await page.goto("/financeiro");
    await expect(page.getByRole("heading", { name: /Fila de contas a pagar/i })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText(/Planejado não reduz saldo/i)).toBeVisible();
    await expect(page.getByText(/Crédito ≠ desconto/i)).toBeVisible();
  });

  test("hub importação — resumo operacional", async ({ page }) => {
    const imps = await (await page.request.get("/api/importations")).json();
    const demo = imps.find((i: { po_number: string }) => i.po_number === "DEMO-04-3INV")
      ?? imps.find((i: { po_number: string }) => i.po_number.startsWith("DEMO-"));
    expect(demo?.id).toBeTruthy();
    await page.goto(`/importacoes/${demo.id}/resumo`);
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/Faturas.*acconto.*raquete/i)).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/DA SPEDIRE/i)).toBeVisible();
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
    const imps = await (await page.request.get("/api/importations")).json();
    const demo = imps.find((i: { po_number: string }) => i.po_number.startsWith("DEMO-"));
    await page.goto(`/importacoes/${demo.id}/financeiro`);
    await page.getByRole("tab", { name: "Despesas Brasil" }).click();
    await expect(page.getByText("Entra no landed cost")).toBeVisible({ timeout: 15000 });
  });
});
