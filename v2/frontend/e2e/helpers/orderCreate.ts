import { expect, type Locator, type Page } from "@playwright/test";

/** Label canônico do rail (J#7) — não é mais só “Pagamentos”. */
export const PAYMENTS_NAV = /pagamentos realizados/i;

/** Login operacional de ensaio (epic_v2_test). Home do admin = Painel. */
export async function loginAs(
  page: Page,
  email = "admin@epic.com.br",
  password = "admin123",
) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill(email);
  await page.getByLabel(/senha/i).fill(password);
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 15_000 });
  await expect(page.getByRole("navigation", { name: /módulos/i })).toBeVisible({
    timeout: 15_000,
  });
}

/** Fila de pedidos — não é mais a home pós-login. */
export async function openOrdersList(page: Page) {
  await page.goto("/orders");
  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15_000 });
}

export async function clickNewOrder(page: Page) {
  await page.getByTestId("orders-new-cta").click();
  await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15_000 });
}

/**
 * Cria SKU (descrição obrigatória) e adiciona a linha na tabela do pedido.
 * Assert na tbody — o thead vazio também é `table`.
 */
export async function createSkuAndAddLine(
  page: Page,
  opts: {
    sku: string;
    description: string;
    qty?: string;
    price?: string;
    unit?: string;
    skipCreateSku?: boolean;
  },
) {
  await page.getByTestId("line-sku").fill(opts.sku);
  if (!opts.skipCreateSku) {
    await page.getByTestId("line-sku-description").fill(opts.description);
    await page.getByRole("button", { name: /criar sku/i }).click();
    await expect(page.getByTestId("line-sku-description")).toHaveValue(opts.description);
  }
  if (opts.qty !== undefined) await page.getByTestId("line-qty").fill(opts.qty);
  if (opts.unit !== undefined) await page.getByTestId("line-unit").fill(opts.unit);
  if (opts.price !== undefined) await page.getByTestId("line-price").fill(opts.price);
  await page.getByRole("button", { name: /^adicionar linha$/i }).click();
  await expect(page.getByTestId("order-lines-table").locator("tbody")).toContainText(opts.sku, {
    timeout: 10_000,
  });
}

/** Pedido novo: código + fornecedor novo + SKU com descrição + confirmar. */
export async function fillAndConfirmOrder(
  page: Page,
  opts: {
    code: string;
    supplierName: string;
    sku: string;
    description: string;
    qty?: string;
    price?: string;
    unit?: string;
  },
) {
  await page.goto("/orders/new");
  await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("order-code").fill(opts.code);
  await page.getByTestId("new-supplier-name").fill(opts.supplierName);
  await createSkuAndAddLine(page, {
    sku: opts.sku,
    description: opts.description,
    qty: opts.qty ?? "10",
    price: opts.price ?? "100",
    unit: opts.unit,
  });
  await expect(page.getByTestId("save-confirm")).toBeEnabled();
  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("confirmation-modal")).toBeVisible();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15_000 });
}

/** MoneyInput seleciona tudo no focus (rAF) — fill() sozinho perde a corrida. */
export async function fillMoneyInput(page: Page, input: Locator, amount: string) {
  await input.click();
  await page.waitForTimeout(120);
  await input.press("Control+A");
  await input.pressSequentially(amount, { delay: 20 });
  await input.blur();
}

/** Emitir rascunho pela UI e esperar fatura somente leitura. */
export async function issueInvoiceFromUi(page: Page) {
  await expect(page.getByTestId("invoice-blockers")).toHaveCount(0, { timeout: 10_000 });
  await expect(page.getByTestId("issue-invoice")).toBeEnabled();
  await page.getByTestId("issue-invoice").click();
  await expect(page.getByTestId("confirmation-modal")).toBeVisible();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15_000 });
}

export async function allocateFirstEligible(page: Page, amount: string) {
  const table = page.getByTestId("eligible-table");
  await expect(table).toBeVisible();
  const pre = page.getByTestId("eligible-preselected");
  const amt =
    (await pre.count()) > 0
      ? pre.locator("input")
      : table.locator("tbody tr").first().locator("input");
  await fillMoneyInput(page, amt, amount);
  await expect(page.getByTestId("alloc-preview")).toBeVisible();
  await expect(page.getByTestId("alloc-preview")).toContainText(amount);
  const posted = page.waitForResponse(
    (r) => r.url().includes("/allocations") && r.request().method() === "POST",
    { timeout: 15_000 },
  );
  await page.getByTestId("allocate-btn").click();
  await expect(page.getByTestId("confirmation-modal")).toBeVisible();
  await page.getByTestId("confirm-modal-ok").click();
  const res = await posted;
  if (!res.ok()) {
    throw new Error(`alocação HTTP ${res.status()} ${await res.text()}`);
  }
}
