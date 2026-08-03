/**
 * A2 — Orders/Billing Document Readiness (UI por cliques).
 * Não cria Order/Invoice centrais via API.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const EVIDENCE = path.resolve(process.cwd(), "..", "..", "docs", "v2", "etapa-doc-readiness");
const SHOT = path.join(EVIDENCE, "screenshots");

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({
    timeout: 20000,
  });
}

test.describe("A2 orders/billing document readiness", () => {
  test("order date/notes/units + doc upload + invoice date/units + issue", async ({ page }) => {
    fs.mkdirSync(SHOT, { recursive: true });
    const code = `A2-${Date.now()}`;
    await login(page);

    await page.getByRole("main").getByRole("link", { name: /novo pedido/i }).click();
    await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("order-code").fill(code);
    await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
    await page.getByTestId("order-date").fill("2026-06-04");
    await page.getByTestId("order-notes").fill("Notas documentais A2");

    await page.getByTestId("line-sku").fill(`SKU-${code}-A`);
    await page.getByRole("button", { name: /criar sku/i }).click();
    await page.waitForTimeout(400);
    await page.getByTestId("line-qty").fill("10");
    await page.getByTestId("line-unit").fill("PZ");
    await page.getByTestId("line-price").fill("5");
    await page.getByRole("button", { name: /adicionar linha/i }).click();

    await page.getByTestId("line-sku").fill(`SKU-${code}-B`);
    await page.getByRole("button", { name: /criar sku/i }).click();
    await page.waitForTimeout(400);
    await page.getByTestId("line-qty").fill("2");
    await page.getByTestId("line-unit").fill("SET");
    await page.getByTestId("line-price").fill("50");
    await page.getByRole("button", { name: /adicionar linha/i }).click();

    await page.screenshot({ path: path.join(SHOT, "a2-order-create.png"), fullPage: true });

    await page.getByTestId("save-confirm").click();
    await page.getByTestId("confirm-modal-ok").click();
    await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 20000 });
    await page.getByTestId("cockpit-commercial-link").click();
    await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });

    await expect(page.getByTestId("order-header")).toContainText("04/06/2026");
    await expect(page.getByTestId("order-notes-readonly")).toContainText("Notas documentais A2");
    await expect(page.getByTestId("order-detail")).toContainText("PZ");
    await expect(page.getByTestId("order-detail")).toContainText("SET");

    await page.getByTestId("order-doc-upload").setInputFiles({
      name: "Ordine_A2.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 a2-order"),
    });
    await expect(page.getByText("Ordine_A2.pdf")).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: path.join(SHOT, "a2-order-detail-docs.png"), fullPage: true });

    await page.getByTestId("new-invoice-number").fill(`F-${code}`);
    await page.getByTestId("new-invoice-date").fill("2026-03-30");
    await page.getByTestId("create-invoice").click();
    await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });

    await expect(page.getByTestId("invoice-item-unit-0").or(page.getByTestId("unit-0"))).toBeVisible();
    const unit0 = page.getByTestId("unit-0");
    if (await unit0.count()) {
      await expect(unit0).toHaveValue("PZ");
    } else {
      await expect(page.getByTestId("invoice-item-unit-0")).toHaveText("PZ");
    }

    await page.getByTestId("discount-type-0").selectOption("NONE");
    await page.getByTestId("discount-type-1").selectOption("NONE");
    await page.getByTestId("save-items").click();
    await page.waitForTimeout(400);

    await page.getByTestId("invoice-doc").setInputFiles({
      name: "Fattura_A2.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 a2-inv"),
    });
    await page.waitForTimeout(500);

    const today = new Date();
    const d1 = today.toISOString().slice(0, 10);
    const d2 = new Date(today.getTime() + 30 * 86400000).toISOString().slice(0, 10);
    await page.getByTestId("terms-mode").selectOption("PERCENT");
    await page.getByTestId("term-date-0").fill(d1);
    await page.getByTestId("term-pct-0").fill("100");
    // single term 100% — remove second if required by UI
    const term1 = page.getByTestId("term-date-1");
    if (await term1.count()) {
      await page.getByTestId("term-date-1").fill(d2);
      await page.getByTestId("term-pct-0").fill("30");
      await page.getByTestId("term-pct-1").fill("70");
    }
    await page.getByTestId("save-terms").click();
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(SHOT, "a2-invoice-before-issue.png"), fullPage: true });

    await page.getByTestId("issue-invoice").click();
    await page.getByTestId("confirm-modal-ok").click();
    await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("invoice-item-unit-0")).toHaveText("PZ");
    await expect(page.getByTestId("invoice-item-unit-1")).toHaveText("SET");
    await expect(page.getByTestId("invoice-detail")).toContainText("30/03/2026");

    await page.reload();
    await expect(page.getByTestId("invoice-readonly")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("invoice-item-unit-0")).toHaveText("PZ");
    await expect(page.getByTestId("invoice-item-unit-1")).toHaveText("SET");
    await expect(page.getByTestId("invoice-detail")).toContainText("30/03/2026");
    await page.screenshot({ path: path.join(SHOT, "a2-invoice-issued.png"), fullPage: true });
  });
});
