import { expect, test } from "@playwright/test";

/**
 * Anti-regressão: ordem completa equivalente ao QA-UI-001 (PO + Heroes + 2 itens + Central + grade).
 */
test.describe("Nova ordem — anti-regressão ordem completa", () => {
  test.beforeEach(async ({ page }) => {
    await page.request.post("/api/demo/seed").catch(() => undefined);
  });

  test("cria ordem com 2 itens e valores corretos na Central e na grade", async ({ page }) => {
    const po = `QA-REG-${Date.now()}`;
    const skuA = `QA-REG-A-${Date.now()}`;
    const skuB = `QA-REG-B-${Date.now()}`;

    const login = await page.request.post("/api/auth/login", {
      data: { email: "admin@epic.com.br", password: "admin123" },
    });
    expect(login.ok()).toBeTruthy();

    for (const [sku, desc] of [
      [skuA, "Item Reg A"],
      [skuB, "Item Reg B"],
    ] as const) {
      const r = await page.request.post("/api/products", {
        data: { sku_code: sku, description: desc, ncm: "95069900" },
      });
      expect(r.ok()).toBeTruthy();
    }

    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "+ Nova ordem" }).click();
    await page.locator("#nova-po").fill(po);

    const supplier = page.locator("#nova-supplier");
    const heroesOpt = supplier.locator('option', { hasText: /^Heroes/i }).first();
    await heroesOpt.waitFor({ state: "attached" });
    await supplier.selectOption({ label: (await heroesOpt.innerText()).trim() });

    async function fillRow(rowIndex: number, sku: string, qty: string, price: string) {
      const row = page.locator(".nova-ordem__grid tbody tr").nth(rowIndex);
      const combo = row.locator(".product-combobox__input");
      await combo.fill(sku);
      await page.locator(".product-combobox__option").filter({ hasText: sku }).first().click();
      await row.locator('input[type="number"]').fill(qty);
      await row.locator("td.num").nth(1).locator("input").fill(price);
    }

    await fillRow(0, skuA, "100", "12.50");
    await page.getByRole("button", { name: "+ Adicionar linha" }).click();
    await fillRow(1, skuB, "50", "8");

    const createReq = page.waitForResponse(
      (r) => r.url().includes("/api/importations") && r.request().method() === "POST" && r.ok(),
      { timeout: 20000 },
    );
    await page.getByRole("button", { name: "Criar e abrir ordem" }).click();
    await createReq;
    await expect(page).toHaveURL(/\/importacoes\/\d+\/resumo/, { timeout: 20000 });
    await expect(page.getByRole("heading", { name: new RegExp(`Central da Ordem ${po}`, "i") })).toBeVisible({
      timeout: 15000,
    });

    await page.goto(`/importacoes/${(await page.url()).match(/\/importacoes\/(\d+)/)?.[1]}/itens`, {
      waitUntil: "domcontentloaded",
    });
    await expect(page.locator("table tbody")).toContainText("12,50");
    await expect(page.locator("table tbody")).toContainText("8,00");

    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.waitForResponse((r) => r.url().includes("/api/importations/order-queue") && r.ok(), {
      timeout: 30000,
    });
    const row = page.locator(".sheet-grid tbody tr", { hasText: po }).first();
    await expect(row).toBeVisible({ timeout: 15000 });
    await expect(row).toContainText(po);
  });
});
