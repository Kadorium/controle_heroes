import { expect, test } from "@playwright/test";

test.describe("QA Rodada 2 — correções UI", () => {
  test("QA-MED-001: Cadastrar fornecedor submete por clique", async ({ page }) => {
    const name = `QA-SUP-${Date.now()}`;
    await page.goto("/cadastros/fornecedores", { waitUntil: "domcontentloaded" });
    await page.getByPlaceholder("Nome").fill(name);
    const createReq = page.waitForResponse(
      (r) => r.url().includes("/api/suppliers") && r.request().method() === "POST",
      { timeout: 15000 },
    );
    await page.getByRole("button", { name: "Cadastrar" }).click();
    const res = await createReq;
    expect(res.ok()).toBeTruthy();
    await expect(page.locator("table tbody")).toContainText(name, { timeout: 10000 });
  });

  test("QA-MED-004: preço unitário formatado pt-BR na aba itens", async ({ page, request }) => {
    const login = await request.post("/api/auth/login", {
      data: { email: "admin@epic.com.br", password: "admin123" },
    });
    expect(login.ok()).toBeTruthy();

    const supplier = await (
      await request.post("/api/suppliers", { data: { name: `QA-PRC-${Date.now()}`, country: "CN" } })
    ).json();
    const product = await (
      await request.post("/api/products", {
        data: { sku_code: `SKU-PRC-${Date.now()}`, description: "Preço QA", ncm: "95069900" },
      })
    ).json();
    const imp = await (
      await request.post("/api/importations", {
        data: {
          po_number: `PO-PRC-${Date.now()}`,
          supplier_id: supplier.id,
          currency: "EUR",
          items: [{ product_id: product.id, quantity_ordered: 10, unit_price_foreign: "12.50" }],
        },
      })
    ).json();

    await page.goto(`/importacoes/${imp.id}/itens`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("table tbody td").filter({ hasText: "12,50" })).toBeVisible({
      timeout: 15000,
    });
  });
});
