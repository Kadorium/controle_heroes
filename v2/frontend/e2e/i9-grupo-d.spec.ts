import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9/grupo-D/screenshots",
);

test("I9-9 retorno contextual + Escape modal", async ({ page }) => {
  const code = `I9D-${Date.now()}`;
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByTestId("orders-list-page")).toBeVisible({ timeout: 15000 });

  await page.getByTestId("orders-new-cta").click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Fornecedor ${code}`);
  await page.getByTestId("line-sku").fill(`SKU-${code}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(300);
  await page.getByTestId("line-qty").fill("1");
  await page.getByTestId("line-price").fill("10");
  await page.getByRole("button", { name: /adicionar linha/i }).click();

  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("confirmation-modal")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("confirmation-modal")).toHaveCount(0);

  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });

  await page.getByLabel("Principal").getByRole("link", { name: /^pedidos$/i }).click();
  await expect(page.getByTestId("orders-list-page")).toBeVisible();
  await page.getByTestId("orders-status-CONFIRMED").click();
  await expect(page).toHaveURL(/status=CONFIRMED/);
  await expect(page.getByRole("link", { name: code })).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: path.join(evidenceDir, "i9-9-orders-filter-1366.png"), fullPage: true });

  await page.getByRole("link", { name: code }).click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 10000 });
  await page.getByTestId("breadcrumb").getByRole("link", { name: /^Pedidos$/i }).click();
  await expect(page).toHaveURL(/status=CONFIRMED/);
  await expect(page.getByTestId("orders-status-CONFIRMED")).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("link", { name: code })).toBeVisible();

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByLabel("Principal").getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: path.join(evidenceDir, "i9-10-ap-1440.png"), fullPage: true });
});
