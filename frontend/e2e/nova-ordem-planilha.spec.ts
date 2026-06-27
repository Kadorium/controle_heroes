import { expect, test } from "@playwright/test";

test.describe("Nova ordem — planilha", () => {
  test.beforeEach(async ({ page }) => {
    await page.request.post("/api/demo/seed").catch(() => undefined);
  });

  test("Heroes pré-selecionado e sem abas wizard", async ({ page }) => {
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "+ Nova ordem" }).click();
    await expect(page.getByRole("heading", { name: "Nova ordem" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cadastro rápido" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Wizard guiado" })).toHaveCount(0);
    const supplier = page.locator("#nova-supplier");
    await expect(supplier).toBeVisible();
    const label = await supplier.locator("option:checked").innerText();
    expect(label.toLowerCase()).toContain("heroes");
  });

  test("subtotal e totais atualizam ao digitar", async ({ page }) => {
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "+ Nova ordem" }).click();
    const po = `PLAN-${Date.now()}`;
    await page.locator("#nova-po").fill(po);
    const row = page.locator(".nova-ordem__grid tbody tr").first();
    await row.locator(".product-combobox__input").fill("SKU");
    await row.locator('input[type="number"]').fill("10");
    await row.locator("td.num").nth(1).locator("input").fill("12.50");
    await expect(row.locator("td.num").nth(3)).toContainText("125,00");
    await expect(page.locator(".nova-ordem__grid tfoot")).toContainText("125,00");
    await row.locator("td.num").nth(2).locator("input").fill("1");
    await expect(row.locator("td.num").nth(3)).toContainText("115,00");
    await expect(page.locator(".nova-ordem-fx")).toBeVisible();
    await expect(page.locator(".nova-ordem-fx__row--total")).toContainText("115,00");
  });
});
