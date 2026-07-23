import { expect, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, "..", "..");
const REAL_WORKBOOK = path.join(ROOT, "CONTI ITALIA-BRASILE.xlsx");
const SHEET = "Ordine 758";
const ORDER_NUMBER = "758";

test.describe("Heroes XLSX import — Ordine 758 real", () => {
  test.use({ storageState: "e2e/.auth/admin.json" });

  test("load-local preview commit e central (planilha real na raiz)", async ({ page }) => {
    test.skip(!fs.existsSync(REAL_WORKBOOK), "CONTI ITALIA-BRASILE.xlsx ausente na raiz do projeto");

    await page.request.post("/api/imports/reset-operational").catch(() => {});
    await page.request.post("/api/demo/seed").catch(() => {});

    const locate = await page.request.get("/api/imports/heroes/xlsx/locate");
    test.skip(locate.status() === 404, "reinicie uvicorn com heroes xlsx endpoints");
    expect(locate.ok(), await locate.text()).toBeTruthy();

    const load = await page.request.post("/api/imports/heroes/xlsx/load-local");
    expect(load.ok(), await load.text()).toBeTruthy();
    const loadBody = await load.json();
    expect(loadBody.workbook_profile?.sheet_count).toBe(14);

    const preview = await page.request.post("/api/imports/heroes/xlsx/preview", {
      data: {
        raw_file_id: loadBody.raw_file_id,
        sheet_name: SHEET,
        confirmed_order_number: ORDER_NUMBER,
      },
    });
    expect(preview.ok(), await preview.text()).toBeTruthy();
    const prevBody = await preview.json();
    expect(prevBody.order_number).toBe(ORDER_NUMBER);
    expect(prevBody.preview?.invoice_items?.length ?? 0).toBeGreaterThan(0);
    expect(prevBody.preview?.da_spedire?.length ?? 0).toBeGreaterThan(0);

    const commit = await page.request.post("/api/imports/heroes/xlsx/commit", {
      data: {
        run_id: prevBody.run_id,
        confirm_import: true,
        confirm_sheet_match: true,
        confirmed_order_number: ORDER_NUMBER,
      },
    });
    let impId: number;
    if (commit.ok()) {
      impId = (await commit.json()).importation_id;
    } else {
      const errText = await commit.text();
      if (errText.includes("já existe")) {
        const listRes = await page.request.get("/api/importations");
        const list = await listRes.json();
        const found = list.find((i: { po_number: string }) => i.po_number === `HEROES-${ORDER_NUMBER}`);
        expect(found, errText).toBeTruthy();
        impId = found.id;
      } else {
        expect(commit.ok(), errText).toBeTruthy();
        return;
      }
    }

    await page.goto(`/importacoes/${impId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Central da Ordem HEROES-758/i })).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 30000 });
    await expect(page.getByRole("heading", { name: /a despachar · preço e desconto/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/Versato Heroes/i).first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/starlight/i).first()).toBeVisible();

    // Idempotência: recommit do mesmo run não duplica
    const commit2 = await page.request.post("/api/imports/heroes/xlsx/commit", {
      data: {
        run_id: prevBody.run_id,
        confirm_import: true,
        confirm_sheet_match: true,
        confirmed_order_number: ORDER_NUMBER,
      },
    });
    expect(commit2.ok(), await commit2.text()).toBeTruthy();
    expect((await commit2.json()).importation_id).toBe(impId);

    await page.request.post("/api/demo/seed").catch(() => {});
  });

  test("UI heroes upload page abre", async ({ page }) => {
    await page.goto("/cadastros/heroes");
    await expect(page.getByRole("heading", { name: /Importar planilha Heroes/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Analisar planilha/i })).toBeVisible();
  });

  test("Ordine 759 preview exige revisão por divergência", async ({ page }) => {
    test.skip(!fs.existsSync(REAL_WORKBOOK), "CONTI ITALIA-BRASILE.xlsx ausente na raiz do projeto");
    const load = await page.request.post("/api/imports/heroes/xlsx/load-local");
    expect(load.ok()).toBeTruthy();
    const loadBody = await load.json();
    const preview = await page.request.post("/api/imports/heroes/xlsx/preview", {
      data: { raw_file_id: loadBody.raw_file_id, sheet_name: "Ordine 759" },
    });
    expect(preview.ok()).toBeTruthy();
    const body = await preview.json();
    expect(body.order_number_divergence).toBe(true);
    expect(body.review_required === true || body.status === "REVIEW_REQUIRED").toBeTruthy();
    const commit = await page.request.post("/api/imports/heroes/xlsx/commit", {
      data: {
        run_id: body.run_id,
        confirm_import: true,
        confirm_sheet_match: true,
      },
    });
    expect(commit.ok()).toBeFalsy();
  });
});
