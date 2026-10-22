/**
 * ING-FAM — planilha Ordine na tela de novo pedido.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { loginAs } from "./helpers/orderCreate";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const xlsx = path.resolve(__dirname, "../../tests/fixtures/ingestion/xlsx/ordine758.xlsx");
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-ing-fam/screenshots");

test("planilha na tela de pedido cria rascunho com compromisso", async ({ page }) => {
  test.skip(!fs.existsSync(xlsx), "ordine758.xlsx missing");
  test.setTimeout(180_000);
  fs.mkdirSync(shotDir, { recursive: true });
  await page.setViewportSize({ width: 1366, height: 900 });
  await loginAs(page);
  await page.goto("/orders/new?pdf=1");
  await expect(page.getByTestId("order-pdf-panel")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("order-pdf-upload").setInputFiles(xlsx);
  await expect(page.getByTestId("order-xlsx-ready")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("order-xlsx-import")).toBeEnabled();
  await page.screenshot({ path: path.join(shotDir, "03-planilha-novo-pedido.png"), fullPage: true });
  await page.getByTestId("order-xlsx-import").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("body")).toContainText("758");
  const kinds = page.locator("[data-testid^='order-item-kind-']");
  await expect(kinds.first()).toBeVisible();
  await expect(kinds.first()).toHaveText(/compromisso|produto/i);
  await expect(page.getByTestId("order-detail")).not.toContainText("8057628955191");
  await expect(page.getByTestId("order-documents")).not.toContainText(/nenhum documento vinculado/i);
  await page.screenshot({ path: path.join(shotDir, "04-pedido-planilha.png"), fullPage: true });
});
