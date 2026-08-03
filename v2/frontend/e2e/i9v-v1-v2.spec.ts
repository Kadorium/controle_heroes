import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/grupo-V1-V2/screenshots",
);

const SUPPLIER = "Heroes Metalúrgica V12";
const CODE = "V12-PEDIDO-CANON";
const INV = "V12-FATURA-001";

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15000 });
}

async function shot(page: import("@playwright/test").Page, name: string, w: number, h: number) {
  await page.setViewportSize({ width: w, height: h });
  await page.screenshot({ path: path.join(evidenceDir, `${name}-${w}.png`), fullPage: true });
}

/** Etapa 9V V1+V2 — 8 SCR com dados determinísticos (epic_v2_test). */
test("I9V V1+V2 eight surfaces", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 1366, height: 768 });
  await login(page);

  // Create deterministic order → invoice → payment via UI
  await page.getByTestId("orders-new-cta").click();
  await page.getByTestId("order-code").fill(CODE);
  await page.getByTestId("new-supplier-name").fill(SUPPLIER);
  await page.getByTestId("line-sku").fill("SKU-V12");
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("40");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });

  const orderUrl = page.url();
  const orderId = Number(orderUrl.match(/orders\/(\d+)/)?.[1]);

  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible();
  await page.getByTestId("new-invoice-number").fill(INV);
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
  const d1 = "2026-07-23";
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("400");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });

  // SCR-003 Pedidos
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pedidos$/i }).click();
  await expect(page.getByTestId("orders-table")).toBeVisible();
  const orderRow = page.getByTestId("orders-table").getByRole("row").filter({ hasText: CODE });
  await expect(orderRow.getByText(SUPPLIER)).toBeVisible();
  await expect(orderRow.getByTestId("status-badge")).toHaveText("Confirmado");
  await expect(orderRow.getByText("EUR 400,00").first()).toBeVisible();
  await expect(page.getByText("CREATE")).toHaveCount(0);
  await shot(page, "scr-003-orders", 1366, 768);

  // SCR-005 Cockpit
  await page.goto(`/orders/${orderId}`);
  await expect(page.getByTestId("order-cockpit")).toBeVisible();
  await expect(page.getByText("Faturamento")).toBeVisible();
  await expect(page.getByText(/Carregando/i)).toHaveCount(0);
  await expect(page.getByText("Invoices")).toHaveCount(0);
  await expect(page.getByText("Payables")).toHaveCount(0);
  await shot(page, "scr-005-cockpit", 1366, 768);

  // SCR-006 Faturas
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Faturas$/i }).click();
  await expect(page.getByTestId("invoices-table")).toBeVisible();
  const invRow = page.getByTestId("invoices-table").getByRole("row").filter({ hasText: INV });
  await expect(invRow).toBeVisible();
  await expect(invRow.getByTestId("status-badge")).toHaveText("Emitida");
  await expect(page.getByTestId("status-badge").filter({ hasText: "ISSUED" })).toHaveCount(0);
  await shot(page, "scr-006-invoices", 1366, 768);

  // SCR-007 Fatura
  await invRow.getByRole("link", { name: INV }).click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  await expect(page.getByText("Condições de pagamento")).toBeVisible();
  await expect(page.getByText("Obrigações")).toBeVisible();
  await shot(page, "scr-007-invoice", 1366, 768);

  // SCR-008 AP
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible();
  await expect(page.getByText("Pagamentos com residual")).toBeVisible();
  await expect(page.getByText(/unalloc/i)).toHaveCount(0);
  await expect(page.getByText("Payables")).toHaveCount(0);
  await page.locator(`[data-testid^="ap-row-"]`).first().locator("td").nth(1).click();
  await expect(page.getByTestId("detail-drawer")).toBeVisible();
  await shot(page, "scr-008-ap", 1366, 768);

  const payableId = await page.locator(`[data-testid^="ap-row-"]`).first().getAttribute("data-testid");
  const pid = payableId?.replace("ap-row-", "") ?? "";

  // SCR-009 FX
  await page.goto(`/payables/${pid}/fx`);
  await expect(page.getByTestId("payable-fx-page")).toBeVisible();
  await expect(page.getByTestId("payable-fx-panel")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Planejado" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mercado" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Executado/i })).toBeVisible();
  await expect(page.getByText(/Carregando/i)).toHaveCount(0);
  await expect(page.getByText(/Inc-4A|open×current|FX não liquida Payable/i)).toHaveCount(0);
  await expect(page.getByTestId("fx-plan-kind").locator("option:checked")).toHaveText("Inicial");
  await shot(page, "scr-009-fx", 1366, 768);

  // Payment via G02
  await page.goto("/payables");
  await page.locator(`[data-testid^="ap-row-"]`).first().locator("td").nth(1).click();
  await page.getByTestId("ap-g02-new-payment").click();
  await expect(page.getByTestId("payment-create")).toBeVisible();
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-recibo"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });

  // SCR-012
  await expect(page.getByTestId("payment-detail").getByTestId("status-badge")).toHaveText("Registrado");
  await expect(page.getByTestId("status-badge").filter({ hasText: "REGISTERED" })).toHaveCount(0);
  await expect(page.getByText(/Create ≠ Allocate/i)).toHaveCount(0);
  await expect(
    page.getByTestId("payment-detail").getByRole("heading", { name: new RegExp(SUPPLIER) }),
  ).toBeVisible();
  await shot(page, "scr-012-payment", 1366, 768);

  // Allocate partial for residual semantics
  const table = page.getByTestId("eligible-table");
  await table.locator("tbody tr").first().locator("input").fill("100");
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/EUR 300/i, { timeout: 10000 });

  // SCR-010 Pagamentos
  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /^Pagamentos$/i }).click();
  await expect(page.getByTestId("payments-table")).toBeVisible();
  const payRow = page.getByTestId("payments-table").getByRole("row").filter({ hasText: SUPPLIER });
  await expect(payRow.getByText(SUPPLIER)).toBeVisible();
  await expect(payRow.getByText(/\d{2}\/\d{2}\/\d{4}/)).toBeVisible();
  await expect(payRow.getByText("EUR 400,00").first()).toBeVisible();
  await expect(payRow.getByTestId("status-badge")).toHaveText("Registrado");
  await expect(page.getByText(/Create ≠ Allocate/i)).toHaveCount(0);
  await expect(page.getByText(/^#\d+$/)).toHaveCount(0);
  await shot(page, "scr-010-payments", 1366, 768);

  // 1440 captures — aguardar conteúdo (não só shell/loading)
  for (const [route, name, testId, ready] of [
    ["/orders", "scr-003-orders", "orders-list-page", { testId: "orders-table" }],
    [`/orders/${orderId}`, "scr-005-cockpit", "order-cockpit", { text: "Faturamento" }],
    ["/invoices", "scr-006-invoices", "invoices-list", { testId: "invoices-table" }],
    ["/payables", "scr-008-ap", "ap-queue-page", { testId: "ap-table" }],
    [`/payables/${pid}/fx`, "scr-009-fx", "payable-fx-page", { testId: "payable-fx-panel" }],
    ["/payments", "scr-010-payments", "payments-list", { testId: "payments-table" }],
  ] as const) {
    await page.goto(route);
    await expect(page.getByTestId(testId)).toBeVisible({ timeout: 10000 });
    if ("testId" in ready) {
      await expect(page.getByTestId(ready.testId)).toBeVisible({ timeout: 15000 });
    } else {
      await expect(page.getByText(ready.text)).toBeVisible({ timeout: 15000 });
    }
    await expect(page.getByText(/Carregando/i)).toHaveCount(0);
    await shot(page, name, 1440, 900);
  }

  // invoice + payment detail 1440
  await page.goto("/invoices");
  await page.getByRole("link", { name: INV }).first().click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible();
  await expect(page.getByTestId("payables-list")).toBeVisible();
  await shot(page, "scr-007-invoice", 1440, 900);

  await page.goto("/payments");
  const abrir = page.getByRole("link", { name: /^Abrir$/i });
  await expect(abrir).not.toHaveCount(0);
  await abrir.nth(0).click();
  await expect(page.getByTestId("payment-detail")).toBeVisible();
  await expect(page.getByTestId("payment-residual")).toBeVisible();
  await shot(page, "scr-012-payment", 1440, 900);
});
