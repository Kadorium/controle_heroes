/**
 * J#8-CLOSE — aceite residual pela UI.
 * SC-08 fatura emitida no histórico; SC-17 conciliação com tolerância provisória.
 * SC-10 (saldo derivado / entrada doméstica) permanece na suíte j5 do runner.
 */
import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fillAndConfirmOrder, issueInvoiceFromUi, loginAs } from "./helpers/orderCreate";

const SHOT_DIR = path.resolve(
  process.cwd(),
  "..",
  "..",
  "docs",
  "v2",
  "etapa-j8",
  "screenshots",
  "close",
);

async function shot(page: import("@playwright/test").Page, name: string) {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  await page.screenshot({ path: path.join(SHOT_DIR, name), fullPage: true });
}

test("J8-CLOSE SC-08 fatura emitida permanece no histórico", async ({ page }) => {
  test.setTimeout(120_000);
  const code = `J8C-${Date.now()}`;
  await loginAs(page);
  await fillAndConfirmOrder(page, {
    code,
    supplierName: `Fornecedor ${code}`,
    sku: `SKU-${code}`,
    description: `Produto ${code}`,
  });
  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15_000 });

  await page.getByTestId("new-invoice-number").fill(`F-${code}`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("cancel-invoice")).toBeVisible();
  await expect(page.getByTestId("qty-0")).toBeVisible();

  await page.getByTestId("discount-type-0").selectOption("PERCENT");
  await page.getByTestId("discount-pct-0").fill("0");
  await page.getByTestId("save-items").click();
  await expect(page.getByTestId("invoice-net")).toContainText("EUR 1.000,00", { timeout: 15_000 });

  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 epic-j8-close"),
  });
  await page.waitForTimeout(500);

  const today = new Date().toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("PERCENT");
  await page.getByTestId("term-date-0").fill(today);
  await page.getByTestId("term-pct-0").fill("100");
  await page.getByTestId("save-terms").click();

  await issueInvoiceFromUi(page);
  await expect(page.getByTestId("invoice-readonly")).toContainText(/histórico/i);
  await expect(page.getByTestId("cancel-invoice")).toHaveCount(0);
  await expect(page.getByTestId("issue-invoice")).toHaveCount(0);
  await expect(page.getByTestId("invoice-date-readonly")).toBeVisible();
  await expect(page.getByTestId("discount-type-0")).toHaveCount(0);
  await shot(page, "sc08-issued-immutable.png");
});

test("J8-CLOSE SC-17 conciliação com tolerância provisória", async ({ page, request }) => {
  test.setTimeout(90_000);
  await loginAs(page);
  await page.goto("/costing");
  await expect(page.getByTestId("costing-queue")).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByText(/Não representa tratamento contábil ou fiscal de recuperabilidade/i),
  ).toBeVisible();
  await shot(page, "sc17-costing-queue.png");

  const login = await request.post("/api/auth/login", {
    data: { email: "admin@epic.com.br", password: "admin123" },
  });
  expect(login.ok()).toBeTruthy();
  const tag = `J8C-${Date.now()}`;
  const proc = await (
    await request.post("/api/import-processes", { data: { external_reference: tag } })
  ).json();
  expect(proc.id).toBeTruthy();
  const cse = await (await request.post("/api/costing/cases", { data: { process_id: proc.id } })).json();
  expect(cse.id).toBeTruthy();

  await page.goto(`/costing/${cse.id}`);
  await expect(page.getByTestId("costing-workspace")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("costing-tolerance-notice")).toContainText(/tolerância provisória/i);
  await expect(page.getByTestId("costing-pairs-empty")).toContainText(/Sem divergências/i);
  await shot(page, "sc17-costing-pairs.png");
});
