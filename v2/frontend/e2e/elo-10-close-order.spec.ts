/**
 * Elo 10 — criar → confirmar → encerrar → CLOSED; reabrir.
 */
import { test, expect } from "@playwright/test";
import { fillAndConfirmOrder, loginAs, openOrdersList } from "./helpers/orderCreate";

test("encerrar pedido CONFIRMED e reabrir", async ({ page }) => {
  test.setTimeout(120_000);
  const code = `E10-${Date.now()}`;
  await loginAs(page);
  await fillAndConfirmOrder(page, {
    code,
    supplierName: `Fornecedor ${code}`,
    sku: `SKU-${code}`,
    description: `Produto ${code}`,
    qty: "2",
    price: "10",
  });
  await page.getByTestId("cockpit-close-link").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("close-order").click();
  await page.getByTestId("close-reason").fill("STORY_COMPLETE");
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("readonly-banner")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("close-reason-display")).toContainText("STORY_COMPLETE");
  await expect(page.getByTestId("status-badge").first()).toHaveText("Encerrado");

  const commercialUrl = page.url();
  await openOrdersList(page);
  await page.getByTestId("orders-status-CLOSED").click();
  await expect(page.getByTestId("orders-table")).toContainText(code);

  await page.goto(commercialUrl);
  await expect(page.getByTestId("order-detail")).toBeVisible();
  await expect(page.getByTestId("close-reason-display")).toContainText("STORY_COMPLETE");
  await expect(page.getByTestId("reopen-order")).toBeVisible();

  await page.getByTestId("reopen-order").click();
  await page.getByTestId("reopen-reason").fill("NEED_CORRECTION");
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("close-order")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("status-badge").first()).toHaveText("Confirmado");
});
