import { test, expect } from "@playwright/test";

// Explicit isolated regression. Requires snapshot/restore of final demo afterward.
test.skip(process.env.DEMO_TERMS_WRITE_TEST !== "true", "Requires deliberate test-database snapshot gate");
for (const mode of ["PERCENT", "AMOUNT"] as const) for (const count of [1, 2]) {
  test(`persisted ${mode} ${count} terms after UI save, issue and reload`, async ({ page }) => {
    const health = await (await page.request.get("/api/health")).json();
    expect(health.logical_database).toBe("epic_v2_test"); expect(health.app_env).toBe("test");
    await page.request.post("/api/auth/dev-login");
    const code = `TERMS-REGRESSION-${mode}-${count}-${Date.now()}`;
    const post = async (path: string, data: object) => {
      const r = await page.request.post(`/api${path}`, { data }); expect(r.ok(), await r.text()).toBeTruthy(); return r.json();
    };
    const supplier = await post("/suppliers", { name: code, country_code: "IT" });
    const product = await post("/products", { sku: code, description: "Regressão isolada, fora da apresentação" });
    let order = await post("/orders", { code, supplier_id: supplier.id, currency: "EUR", order_date: "2026-10-22" });
    order = await post(`/orders/${order.id}/items`, { expected_version: order.version, product_id: product.id, quantity: "10", unit_price: "100" });
    order = await post(`/orders/${order.id}/confirm`, { expected_version: order.version });
    const invoice = await post(`/orders/${order.id}/invoices`, { invoice_number: `TERMS-${mode}-${count}`, invoice_type: "FINAL", invoice_date: "2026-10-22" });
    await page.goto(`/invoices/${invoice.id}`);
    await page.getByTestId("discount-type-0").selectOption("NONE");
    await page.getByTestId("save-items").click();
    await expect(page.getByTestId("invoice-net")).toContainText("1.000");
    await page.getByTestId("terms-mode").selectOption(mode);
    for (let n = 0; n < count; n++) {
      await page.getByTestId(`term-date-${n}`).fill(n ? "2026-12-21" : "2026-11-21");
      await page.getByTestId(`term-${mode === "PERCENT" ? "pct" : "amt"}-${n}`).fill(String((mode === "PERCENT" ? 100 : 1000) / count));
    }
    const save = page.waitForResponse(r => r.url().endsWith(`/invoices/${invoice.id}/terms`) && r.request().method() === "PUT");
    await page.getByTestId("save-terms").click();
    const saved = await (await save).json(); expect(saved.terms).toHaveLength(count);
    await page.getByTestId("invoice-doc").setInputFiles(`${process.env.DEMO_TERMS_PDF_DIR}/TERMS-${mode}-${count}.pdf`);
    await expect(page.getByTestId("invoice-blockers")).toHaveCount(0);
    await page.getByTestId("issue-invoice").click();
    await page.getByTestId("confirm-modal-ok").click();
    await expect(page.getByTestId("invoice-readonly")).toBeVisible();
    await expect(page.locator('[data-testid^="term-date-"]')).toHaveCount(count);
    await expect(page.getByTestId("term-preview-0")).toContainText(count === 1 ? "1.000,00" : "500,00");
    await page.reload();
    await expect(page.getByTestId("invoice-readonly")).toBeVisible();
    await expect(page.locator('[data-testid^="term-date-"]')).toHaveCount(count);
    const persisted = await (await page.request.get(`/api/invoices/${invoice.id}`)).json();
    expect(persisted.terms).toHaveLength(count); expect(persisted.payables).toHaveLength(count);
    expect(Number(persisted.balance)).toBe(1000);
  });
}
