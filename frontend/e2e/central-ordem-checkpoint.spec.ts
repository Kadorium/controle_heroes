import { expect, test } from "@playwright/test";

const ADMIN = { email: "admin@epic.com.br", password: "admin123" };

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

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-mail|email/i).fill(ADMIN.email);
  await page.getByLabel(/senha|password/i).fill(ADMIN.password);
  await page.getByRole("button", { name: /entrar|login/i }).click();
  await expect(page).toHaveURL(/\/(\?.*)?$/);
}

async function seedAndGetDemoId(page: import("@playwright/test").Page): Promise<number> {
  const seedRes = await page.request.post("/api/demo/seed");
  expect(seedRes.ok()).toBeTruthy();
  const impsRes = await page.request.get("/api/importations");
  expect(impsRes.ok()).toBeTruthy();
  const imps = await impsRes.json();
  const demo = imps.find((i: { po_number: string }) => i.po_number.startsWith("DEMO-"));
  expect(demo?.id).toBeTruthy();
  return demo.id as number;
}

test.describe("Central da Ordem — checkpoint pós-Fase 5", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.request.post("/api/demo/seed");
  });

  test("topbar: Ordens, Financeiro, Demo Epic", async ({ page }) => {
    await expect(page.getByRole("link", { name: "Painel" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ordens" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Financeiro" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Demo Epic" })).toBeVisible();
  });

  test("glossário PT — ausência de labels técnicos principais", async ({ page }) => {
    const demoId = await seedAndGetDemoId(page);

    const routes = ["/", "/importacoes", `/importacoes/${demoId}`, "/financeiro"];
    for (const route of routes) {
      await page.goto(route, { waitUntil: "domcontentloaded" });
      const body = await page.locator("body").innerText();
      for (const pattern of TECH_LABEL_PATTERNS) {
        expect(body, `label técnico ${pattern} em ${route}`).not.toMatch(pattern);
      }
    }
  });

  test("honestidade — sem números fake do mock", async ({ page }) => {
    const demoId = await seedAndGetDemoId(page);
    await page.goto(`/importacoes/${demoId}`);
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 15000 });
    const body = await page.locator("body").innerText();
    for (const fake of MOCK_FAKE_VALUES) {
      expect(body).not.toContain(fake);
    }
  });

  test("fila de ordens carrega e abre central", async ({ page }) => {
    await seedAndGetDemoId(page);
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Fila de ordens|Ordens/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator(".order-queue__row, .row__po").first()).toBeVisible({ timeout: 45000 });
    await page.locator(".order-queue__row").first().click();
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 15000 });
  });

  test("central: Visão Geral, Bloco A e Bloco B", async ({ page }) => {
    const demoId = await seedAndGetDemoId(page);
    await page.goto(`/importacoes/${demoId}`);
    await expect(page.getByRole("link", { name: "Visão Geral", exact: true })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Faturas.*acconto.*raquete/i)).toBeVisible();
    await expect(page.getByText(/DA SPEDIRE/i)).toBeVisible();
  });

  test("Demo Epic navega para /demo", async ({ page }) => {
    await page.getByRole("link", { name: "Demo Epic" }).click();
    await expect(page).toHaveURL(/\/demo/);
  });

  test("financeiro global carrega fila", async ({ page }) => {
    await seedAndGetDemoId(page);
    await page.goto("/financeiro");
    await expect(page.getByRole("heading", { name: /Financeiro|Contas a pagar/i })).toBeVisible({ timeout: 15000 });
  });

  test("glossário operacional em cadastros", async ({ page }) => {
    await page.goto("/cadastros/glossario");
    await expect(page.getByRole("heading", { name: /Glossário operacional/i })).toBeVisible();
  });

  test("order-queue API responde com ordens", async ({ page }) => {
    const res = await page.request.get("/api/importations/order-queue?limit=20");
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items?.length ?? 0).toBeGreaterThan(0);
  });
});
