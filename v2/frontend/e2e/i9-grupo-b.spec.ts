import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9/grupo-B/screenshots",
);

/**
 * Grupo B — Pedidos enrichment, Novo pedido, Cockpit, Faturas.
 * epic_v2_test only (via npm run e2e).
 */
test("I9-2…5 Pedidos Cockpit Faturas", async ({ page }) => {
  const code = `I9B-${Date.now()}`;
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("heading", { name: /^Pedidos$/i })).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "i9-2-orders-1366.png"), fullPage: true });

  await page.getByTestId("orders-new-cta").click();
  await expect(page.getByTestId("order-create-page")).toBeVisible();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("100");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.screenshot({ path: path.join(evidenceDir, "i9-3-new-order-1366.png"), fullPage: true });
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();

  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("kpi-strip")).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "i9-4-cockpit-1366.png"), fullPage: true });

  await page.getByTestId("cockpit-commercial-link").click();
  await page.getByTestId("new-invoice-number").fill(`F-${code}`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("discount-type-0").selectOption("NONE");
  await page.getByTestId("save-items").click();
  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  await page.waitForTimeout(400);
  const d1 = new Date().toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("1000");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("payables-list")).toBeVisible();

  await page.getByLabel("Principal").getByRole("link", { name: /^faturas$/i }).click();
  await expect(page.getByTestId("invoices-table")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(`F-${code}`)).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "i9-5-invoices-1366.png"), fullPage: true });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByLabel("Principal").getByRole("link", { name: /^pedidos$/i }).click();
  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15000 });
  await expect(page.getByRole("link", { name: code })).toBeVisible({ timeout: 15000 });
  await page.screenshot({ path: path.join(evidenceDir, "i9-2-orders-1440.png"), fullPage: true });
});
