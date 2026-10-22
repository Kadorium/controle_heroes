/**
 * Ordine PDF na tela de pedido — Preencher e Importar.
 * Isolar: suíte própria (prepare fresco). Não misturar com cat-pim.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import { loginAs } from "./helpers/orderCreate";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ordinePdf = path.resolve(__dirname, "../../tests/fixtures/ingestion/corpus_589/Ordine_589.pdf");

test.describe("Ordine PDF na tela de pedido", () => {
  test.describe.configure({ mode: "serial" });
  test.setTimeout(180_000);

  test("importar Ordine_589 cria pedido rascunho com linhas compromisso", async ({ page }) => {
    test.skip(!fs.existsSync(ordinePdf), "Ordine_589.pdf missing");
    await loginAs(page);
    await page.goto("/orders/new?pdf=1");
    await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("order-pdf-panel")).toBeVisible();
    await page.getByTestId("order-pdf-upload").setInputFiles(ordinePdf);
    await expect(page.getByTestId("order-pdf-ready")).toBeVisible({ timeout: 90_000 });
    await expect(page.getByTestId("order-pdf-import")).toBeEnabled({ timeout: 15_000 });
    await page.getByTestId("order-pdf-import").click();
    await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("order-header")).toBeVisible();
    await expect(page.locator("body")).toContainText("589");
    const kinds = page.locator("[data-testid^='order-item-kind-']");
    await expect(kinds).toHaveCount(2);
    await expect(kinds.nth(0)).toHaveText(/compromisso/i);
    await expect(kinds.nth(1)).toHaveText(/compromisso/i);
  });

  test("preencher tela a partir do PDF e salvar rascunho", async ({ page }) => {
    test.skip(!fs.existsSync(ordinePdf), "Ordine_589.pdf missing");
    await loginAs(page);
    await page.goto("/orders/new");
    await expect(page.getByTestId("order-pdf-panel")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("order-pdf-upload").setInputFiles(ordinePdf);
    await expect(page.getByTestId("order-pdf-fill")).toBeEnabled({ timeout: 90_000 });
    await page.getByTestId("order-pdf-fill").click();
    await expect(page.getByTestId("order-code")).toHaveValue("589");
    const newSupplier = page.getByTestId("new-supplier-name");
    if (await newSupplier.count()) {
      await expect(newSupplier).toHaveValue(/Heroe/i);
    } else {
      await expect(page.getByTestId("order-supplier")).not.toHaveValue("");
    }
    await expect(page.getByTestId("order-lines-table")).toContainText("I.V. 2");
    await expect(page.getByTestId("order-lines-table")).toContainText("Compromisso");
    await expect(page.getByTestId("save-confirm")).toBeEnabled();
    const unique = `589-UI-${Date.now()}`;
    await page.getByTestId("order-code").fill(unique);
    await page.getByTestId("save-draft").click();
    await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("body")).toContainText(unique);
    await expect(page.locator("[data-testid^='order-item-kind-']").first()).toHaveText(/compromisso/i);
  });
});
