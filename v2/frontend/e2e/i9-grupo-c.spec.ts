import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9/grupo-C/screenshots",
);

/** Grupo C — AP G02 → Payment → Allocation + FX (epic_v2_test). */
test("I9-6…8 AP G02 Payment Allocation FX", async ({ page }) => {
  const code = `I9C-${Date.now()}`;
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  await page.getByRole("main").getByRole("link", { name: /novo pedido/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("100");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
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
  await page.waitForTimeout(300);
  const d1 = new Date().toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("1000");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payables-list")).toBeVisible({ timeout: 15000 });

  const payableId = await page.evaluate(async () => {
    const r = await fetch("/api/payables?limit=5", { credentials: "include" });
    const rows = await r.json();
    return rows[0]?.id as number;
  });
  const balanceBefore = await page.evaluate(async (pid) => {
    const r = await fetch(`/api/payables?limit=100`, { credentials: "include" });
    const rows = await r.json();
    return rows.find((x: { id: number }) => x.id === pid)?.balance as string;
  }, payableId);

  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: path.join(evidenceDir, "i9-6-ap-1366.png"), fullPage: true });
  // Clique em célula sem link; linha específica do payable criado neste teste
  await page.locator(`[data-testid="ap-row-${payableId}"]`).locator("td").nth(1).click();
  await expect(page.getByTestId("detail-drawer")).toBeVisible();
  await page.getByTestId("ap-g02-new-payment").click();
  await expect(page.getByTestId("payment-create")).toBeVisible();
  await expect(page.getByTestId("g02-banner")).toBeVisible();
  await expect(page).toHaveURL(/supplier_id=/);
  await page.getByTestId("pay-amount").click();
  await page.getByTestId("pay-amount").fill("1000");
  await page.screenshot({ path: path.join(evidenceDir, "i9-7-payment-new-g02-1366.png"), fullPage: true });

  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-recibo"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });

  const balanceAfterCreate = await page.evaluate(async (pid) => {
    const r = await fetch(`/api/payables?limit=100`, { credentials: "include" });
    const rows = await r.json();
    return rows.find((x: { id: number }) => x.id === pid)?.balance as string;
  }, payableId);
  expect(balanceAfterCreate).toBe(balanceBefore);

  const table = page.getByTestId("eligible-table");
  const amt = table.locator("tbody tr").first().locator("input");
  await amt.click();
  await amt.fill("400");
  await expect(page.getByTestId("alloc-preview")).toBeVisible();
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 600,00/i, { timeout: 10000 });

  const balanceAfterAlloc = await page.evaluate(async (pid) => {
    const r = await fetch(`/api/payables?limit=100`, { credentials: "include" });
    const rows = await r.json();
    return rows.find((x: { id: number }) => x.id === pid)?.balance as string;
  }, payableId);
  expect(Number(balanceAfterAlloc)).toBeLessThan(Number(balanceBefore));

  await page.goto(`/payables/${payableId}/fx`);
  await expect(page.getByTestId("payable-fx-page")).toBeVisible();
  await expect(page.getByTestId("payable-fx-panel")).toBeVisible();
  const balanceOnFxPage = await page.evaluate(async (pid) => {
    const r = await fetch(`/api/payables?limit=100`, { credentials: "include" });
    const rows = await r.json();
    return rows.find((x: { id: number }) => x.id === pid)?.balance as string;
  }, payableId);
  expect(Number(balanceOnFxPage)).toBeLessThan(Number(balanceBefore));
  await page.screenshot({ path: path.join(evidenceDir, "i9-8-fx-1366.png"), fullPage: true });

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page.getByTestId("payments-list")).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "i9-7-payments-1440.png"), fullPage: true });
});
