import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/grupo-V0/screenshots",
);

const SUPPLIER = "Heroes Metalúrgica LTDA";
const PAY_DATE = "2026-07-23";

/**
 * Etapa 9V Grupo V0 — primitives + shell + enrichment Payments.
 * Somente epic_v2_test (via npm run e2e).
 */
test("I9V-V0 foundation shell + payments primitives", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByText(/^Compras$/i)).toBeVisible({ timeout: 15000 });
  await expect(nav.getByText(/^Financeiro$/i)).toBeVisible();
  await expect(nav.getByRole("link", { name: /novo pedido/i })).toHaveCount(0);
  await expect(nav.locator('a[href="/fx"]')).toHaveCount(0);
  await expect(nav.getByRole("link", { name: /contas a pagar/i })).toBeVisible();

  await page.screenshot({
    path: path.join(evidenceDir, "v0-shell-1366.png"),
    fullPage: true,
  });

  // Fixture determinística via API (não toca epic_v2)
  const created = await page.evaluate(
    async ({ supplierName, payDate }) => {
      const sRes = await fetch("/api/suppliers", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: supplierName, country_code: "IT" }),
      });
      if (!sRes.ok) throw new Error(`supplier ${sRes.status}`);
      const s = await sRes.json();
      const pRes = await fetch("/api/payments", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_id: s.id,
          amount: "400.0000",
          currency: "EUR",
          payment_date: payDate,
          register_without_document: true,
          reason_code: "TEST_OVERRIDE",
        }),
      });
      if (!pRes.ok) throw new Error(`payment ${pRes.status} ${await pRes.text()}`);
      return await pRes.json();
    },
    { supplierName: SUPPLIER, payDate: PAY_DATE },
  );

  expect(created.supplier_name).toBe(SUPPLIER);

  await nav.getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page).toHaveURL(/\/payments/);
  await expect(page.getByTestId("payments-list")).toBeVisible();

  const table = page.getByTestId("payments-table");
  await expect(table.getByText("23/07/2026")).toBeVisible();
  await expect(table.getByText(SUPPLIER)).toBeVisible();
  await expect(table.getByText("EUR 400,00").first()).toBeVisible();
  await expect(table.getByText("Registrado").first()).toBeVisible();
  await expect(table.getByText("REGISTERED")).toHaveCount(0);
  await expect(table.getByText(/#\d+/)).toHaveCount(0);
  await expect(table.getByText(/400\.0000/)).toHaveCount(0);
  // C-010: Referência é texto; uma ação Abrir por linha (não RowLink na ref)
  const rowCount = await table.locator("tbody tr").count();
  const abrir = table.getByRole("link", { name: /^Abrir$/i });
  await expect(abrir).toHaveCount(rowCount);
  await expect(abrir.nth(0)).toBeVisible();
  await expect(page.getByTestId("page-header")).not.toContainText(/Create/);

  await page.screenshot({
    path: path.join(evidenceDir, "v0-payments-1366.png"),
    fullPage: true,
  });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pedidos$/i }).click();
  await expect(page).toHaveURL(/\/orders/);
  await page.screenshot({
    path: path.join(evidenceDir, "v0-shell-1440.png"),
    fullPage: true,
  });
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page.getByTestId("payments-list")).toBeVisible();
  await page.screenshot({
    path: path.join(evidenceDir, "v0-payments-1440.png"),
    fullPage: true,
  });
});
