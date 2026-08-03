/**
 * J4-UX2 — capacidade UI Logistics (packages/contents/summary/docs/batch).
 * Valores representativos; não transcreve PL 202 completo.
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
  await expect(page.getByRole("link", { name: /embarques|shipments/i }).first()).toBeVisible({
    timeout: 20000,
  });
}

test.describe("J4-UX2 logistics readiness UI", () => {
  test("package editor, batch range, summary form visible on PLANNED shipment", async ({
    page,
  }) => {
    fs.mkdirSync(SHOT, { recursive: true });
    await login(page);

    // Create shipment via UI
    await page.goto("/shipments/new");
    await expect(page.getByTestId("shipment-create-page")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("shipment-create-submit").click();
    await expect(page).toHaveURL(/\/shipments\/\d+/, { timeout: 20000 });

    await expect(page.getByTestId("package-editor")).toBeVisible();
    await expect(page.getByTestId("package-external-no")).toBeVisible();
    await expect(page.getByTestId("package-packaging-ncm")).toBeVisible();
    await expect(page.getByTestId("package-net-weight")).toBeVisible();
    await expect(page.getByTestId("shipment-batch-range")).toBeVisible();
    await expect(page.getByTestId("document-summary-editor")).toBeVisible();
    await expect(page.getByTestId("shipment-doc-upload")).toBeVisible();

    await page.getByTestId("package-external-no").fill("1");
    await page.getByTestId("package-count").fill("1");
    await page.getByTestId("package-packaging-ncm").fill("4819100000");
    await page.getByTestId("package-length").fill("47");
    await page.getByTestId("package-width").fill("34");
    await page.getByTestId("package-height").fill("56");
    await page.getByTestId("package-net-weight").fill("5.40");
    await page.getByTestId("package-gross-weight").fill("6.00");
    await page.getByTestId("shipment-add-package").click();
    await expect(page.getByText("4819100000")).toBeVisible({ timeout: 10000 });

    await page.screenshot({ path: path.join(SHOT, "a1-package-editor.png"), fullPage: true });

    // Intervalo pequeno (representativo de escala)
    await page.getByTestId("package-range-from").fill("10");
    await page.getByTestId("package-range-to").fill("12");
    await page.getByTestId("package-net-weight").fill("1.40");
    await page.getByTestId("shipment-batch-range").click();
    await expect(
      page.getByTestId("shipment-packages").getByRole("cell", { name: "12", exact: true }),
    ).toBeVisible({ timeout: 15000 });

    await page.screenshot({ path: path.join(SHOT, "a1-batch-range.png"), fullPage: true });
  });
});
