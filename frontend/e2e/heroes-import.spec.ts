import { expect, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

test.describe("Heroes XLSX import", () => {
  test.use({ storageState: "e2e/.auth/admin.json" });

  test("upload preview commit e central", async ({ page }) => {
    const fixturePath = path.join(__dirname, "fixtures", "ordine759.xlsx");
    test.skip(!fs.existsSync(fixturePath), "fixture ordine759.xlsx ausente");

    const probe = await page.request.post("/api/imports/heroes/xlsx/preview", {
      data: { raw_file_id: 0, sheet_name: "x" },
    });
    test.skip(probe.status() === 404, "reinicie uvicorn com migração 007 + openpyxl");

    const buffer = fs.readFileSync(fixturePath);
    const upload = await page.request.post("/api/imports/heroes/xlsx/upload", {
      multipart: {
        file: {
          name: "ordine759.xlsx",
          mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          buffer,
        },
      },
    });
    expect(upload.ok(), await upload.text()).toBeTruthy();
    const upBody = await upload.json();

    const preview = await page.request.post("/api/imports/heroes/xlsx/preview", {
      data: { raw_file_id: upBody.raw_file_id, sheet_name: "Ordine 759" },
    });
    expect(preview.ok(), await preview.text()).toBeTruthy();
    const prevBody = await preview.json();
    expect(prevBody.order_number).toBe("759");

    const commit = await page.request.post("/api/imports/heroes/xlsx/commit", {
      data: {
        run_id: prevBody.run_id,
        confirm_import: true,
        confirm_sheet_match: true,
        confirmed_order_number: "759",
      },
    });
    expect(commit.ok(), await commit.text()).toBeTruthy();
    const impId = (await commit.json()).importation_id;

    await page.goto(`/importacoes/${impId}/resumo`);
    await expect(page.getByRole("heading", { name: /Central da Ordem HEROES-759/i })).toBeVisible({
      timeout: 30000,
    });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por produto/i })).toBeVisible();
    await expect(page.getByText("OLYMPIA")).toBeVisible();
  });

  test("UI heroes upload page abre", async ({ page }) => {
    await page.goto("/cadastros/heroes");
    await expect(page.getByRole("heading", { name: /Importação Heroes/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Analisar planilha/i })).toBeVisible();
  });
});
