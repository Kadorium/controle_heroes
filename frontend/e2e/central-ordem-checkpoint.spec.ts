import { expect, test } from "@playwright/test";
import { getDemoImportationId } from "./helpers";

/** Labels técnicos que não devem aparecer como texto principal visível (word boundary). */
const TECH_LABEL_PATTERNS = [
  /\bPO_CREATED\b/,
  /\bPROFORMA_RECEIVED\b/,
  /\bIN_TRANSIT\b/,
  /\bCLOSED\b/,
  /\bPENDING\b/,
  /\bInvoices\b/,
  /\bShipment\b/,
  /\bLanded Cost\b/,
  /\breason_code\b/,
];

/** Valores fictícios do mock central da ordem — não devem aparecer hardcoded. */
const MOCK_FAKE_VALUES = ["447.500", "397.500", "178.750", "6.560"];

test.describe("Central da Ordem — checkpoint pós-Fase 5", () => {
  test("topbar: Ordens, Financeiro, Demo Epic", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Painel" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ordens" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Financeiro" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Demo Epic" })).toBeVisible();
  });

  test("glossário PT — ausência de labels técnicos principais", async ({ page }) => {
    const demoId = await getDemoImportationId(page);

    const routes = ["/", "/importacoes", `/importacoes/${demoId}/resumo`, "/financeiro"];
    for (const route of routes) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      const body = await page.locator("body").innerText();
      for (const pattern of TECH_LABEL_PATTERNS) {
        expect(body, `label técnico ${pattern} em ${route}`).not.toMatch(pattern);
      }
    }
  });

  test("honestidade — sem números fake do mock", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-01-OCEAN");
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 20000 });
    const body = await page.locator("body").innerText();
    for (const fake of MOCK_FAKE_VALUES) {
      expect(body).not.toContain(fake);
    }
  });

  test("fila de ordens carrega e abre central", async ({ page }) => {
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
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 15000 });
  });

  test("central: painel operacional EUR+BRL e régua compacta", async ({ page }) => {
    const demoId = await getDemoImportationId(page);
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 30000 });
    await expect(page.locator(".oc-operational-header")).toBeVisible({ timeout: 20000 });
    await expect(page.getByText("Pagamentos", { exact: true })).toBeVisible();
    await expect(page.getByText("Logística", { exact: true })).toBeVisible();
    await expect(page.getByText("Prazos", { exact: true })).toBeVisible();
    await expect(page.locator(".order-central__rail--compact")).toBeVisible();
  });

  test("central: Visão Geral, Bloco A e Bloco B", async ({ page }) => {
    const demoId = await getDemoImportationId(page);
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    const sidebar = page.getByRole("complementary");
    await expect(sidebar.getByRole("link", { name: "Visão Geral", exact: true })).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /a despachar · preço e desconto/i })).toBeVisible({
      timeout: 20000,
    });
  });

  test("Demo Epic navega para /demo", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Demo Epic" }).click();
    await expect(page).toHaveURL(/\/demo/);
  });

  test("financeiro global carrega fila", async ({ page }) => {
    await page.goto("/financeiro");
    await expect(page.getByRole("heading", { name: /Financeiro|Contas a pagar/i })).toBeVisible({ timeout: 15000 });
  });

  test("glossário operacional em cadastros", async ({ page }) => {
    await page.goto("/cadastros/glossario");
    await expect(page.getByRole("heading", { name: /Glossário operacional/i })).toBeVisible();
  });

  test("order-queue API responde com ordens", async ({ page }) => {
    const res = await page.request.get("/api/importations/order-queue?limit=20", { timeout: 120_000 });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items?.length ?? 0).toBeGreaterThan(0);
  });
});
