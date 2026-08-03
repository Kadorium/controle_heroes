import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/grupo-VF/screenshots",
);

const CODE = `VF-${Date.now()}`;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15000 });
}

async function shot(page: import("@playwright/test").Page, name: string, w: number, h: number) {
  await page.setViewportSize({ width: w, height: h });
  await page.waitForTimeout(200);
  await expect(page.getByText(/Carregando/i)).toHaveCount(0);
  await page.screenshot({
    path: path.join(evidenceDir, `${name}-${w}.png`),
    fullPage: true,
  });
}

/**
 * Etapa 9V VF — 12 SCR × 2 resoluções (1366 / 1440).
 * Somente epic_v2_test.
 */
test("I9V-VF capture 12 SCR × 2 viewports", async ({ page }) => {
  // SCR-001 login (sem shell)
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await expect(page.getByTestId("login-page")).toBeVisible();
  await expect(page.getByRole("navigation", { name: /módulos/i })).toHaveCount(0);
  await shot(page, "scr-001-login", 1366, 768);
  await shot(page, "scr-001-login", 1440, 900);

  await login(page);

  // SCR-002 shell (sobre pedidos)
  await expect(page.getByRole("navigation", { name: /módulos/i })).toBeVisible();
  await shot(page, "scr-002-shell", 1366, 768);
  await shot(page, "scr-002-shell", 1440, 900);

  // SCR-003 pedidos
  await shot(page, "scr-003-orders", 1366, 768);
  await shot(page, "scr-003-orders", 1440, 900);

  // SCR-004 novo pedido
  await page.getByTestId("orders-new-cta").click();
  await expect(page.getByTestId("order-create-page")).toBeVisible();
  await shot(page, "scr-004-order-new", 1366, 768);
  await shot(page, "scr-004-order-new", 1440, 900);

  // Criar pedido confirmado para demais telas
  await page.getByTestId("order-code").fill(CODE);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${CODE}`);
  await page.getByTestId("line-sku").fill(`SKU-${CODE}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(300);
  await page.getByTestId("line-qty").fill("2");
  await page.getByTestId("line-price").fill("200");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });

  // SCR-005 cockpit
  await shot(page, "scr-005-cockpit", 1366, 768);
  await shot(page, "scr-005-cockpit", 1440, 900);

  // Emitir fatura
  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("new-invoice-number").fill(`F-${CODE}`);
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
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  const d1 = new Date().toISOString().slice(0, 10);
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("400");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });

  // SCR-007 fatura
  await shot(page, "scr-007-invoice", 1366, 768);
  await shot(page, "scr-007-invoice", 1440, 900);

  // SCR-006 faturas
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Faturas$/i }).click();
  await expect(page.getByTestId("invoices-list")).toBeVisible();
  await shot(page, "scr-006-invoices", 1366, 768);
  await shot(page, "scr-006-invoices", 1440, 900);

  // SCR-008 AP
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 15000 });
  await shot(page, "scr-008-ap", 1366, 768);
  await shot(page, "scr-008-ap", 1440, 900);

  // Abrir FX da primeira obrigação
  const apRow = page.locator('[data-testid^="ap-row-"]').first();
  await expect(apRow).toBeVisible();
  const fxLink = apRow.getByRole("link", { name: /câmbio/i });
  await fxLink.click();
  await expect(page.getByTestId("payable-fx-page")).toBeVisible({ timeout: 15000 });

  // SCR-009 FX
  await shot(page, "scr-009-fx", 1366, 768);
  await shot(page, "scr-009-fx", 1440, 900);

  // SCR-010 pagamentos
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page.getByTestId("payments-list")).toBeVisible();
  await shot(page, "scr-010-payments", 1366, 768);
  await shot(page, "scr-010-payments", 1440, 900);

  // SCR-011 novo pagamento (G02 via AP)
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible();
  await page.locator('[data-testid^="ap-row-"]').first().locator("td").nth(1).click();
  await expect(page.getByTestId("detail-drawer")).toBeVisible();
  await page.getByTestId("ap-g02-new-payment").click();
  await expect(page.getByTestId("payment-create")).toBeVisible({ timeout: 10000 });
  await shot(page, "scr-011-payment-new", 1366, 768);
  await shot(page, "scr-011-payment-new", 1440, 900);

  // Registrar pagamento e abrir detalhe SCR-012
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-recibo"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });
  await shot(page, "scr-012-payment", 1366, 768);
  await shot(page, "scr-012-payment", 1440, 900);

  // Nav ativa em rota aninhada
  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByRole("link", { name: /^Pagamentos$/i })).toHaveClass(/active/);
});
