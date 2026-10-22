/**
 * B0 — picker residual na fatura digitada na comercial do pedido.
 * SKU interno ≠ código de barras. Prepare fresco; não misturar com cat-pim.
 */
import { test, expect } from "@playwright/test";
import {
  loginAs,
  openOrdersList,
  clickNewOrder,
  createSkuAndAddLine,
  issueInvoiceFromUi,
} from "./helpers/orderCreate";

test("B0 residual picker on manual invoice", async ({ page }) => {
  const stamp = Date.now();
  const code = `B0-${stamp}`;
  const skuA = `SKU-B0A-${stamp}`;
  const skuB = `SKU-B0B-${stamp}`;

  await loginAs(page);
  await openOrdersList(page);
  await clickNewOrder(page);
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await createSkuAndAddLine(page, {
    sku: skuA,
    description: "Bola residual",
    qty: "10",
    price: "8",
  });
  await createSkuAndAddLine(page, {
    sku: skuB,
    description: "Raquete residual",
    qty: "5",
    price: "12",
  });
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("cockpit-commercial-link").click();
  await expect(page.getByTestId("order-invoices")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("invoice-residual-hint")).toBeVisible();

  const residualBoxes = page.getByTestId("invoiced-qty").locator('input[type="checkbox"]');
  await expect(residualBoxes).toHaveCount(2);
  await residualBoxes.nth(1).uncheck();

  const commercialUrl = page.url();
  await page.getByTestId("new-invoice-number").fill(`F-${code}-1`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("invoice-item-sku-0")).toHaveText(skuA);
  await expect(page.getByTestId("invoice-items-table")).not.toContainText(skuB);
  await expect(page.getByTestId("qty-0")).toHaveValue("10");

  await page.getByTestId("discount-type-0").selectOption("NONE");
  await page.getByTestId("save-items").click();
  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 epic"),
  });
  const today = new Date().toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("PERCENT");
  await page.getByTestId("term-date-0").fill(today);
  await page.getByTestId("term-pct-0").fill("100");
  await page.getByTestId("save-terms").click();
  await expect(page.getByTestId("payables-preview")).toBeVisible({ timeout: 10_000 });
  await issueInvoiceFromUi(page);

  await page.goto(commercialUrl);
  await expect(page.getByTestId("order-invoices")).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByTestId("invoiced-qty").locator('input[type="checkbox"]'),
  ).toHaveCount(1);
  await page.getByTestId("new-invoice-number").fill(`F-${code}-2`);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("invoice-item-sku-0")).toHaveText(skuB);
  await expect(page.getByTestId("invoice-items-table")).not.toContainText(skuA);
  await expect(page.getByTestId("qty-0")).toHaveValue("5");
});
