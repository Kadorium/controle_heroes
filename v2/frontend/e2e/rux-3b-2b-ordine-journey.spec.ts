/**
 * RUX-3B-2b — jornada Ordine 589 com catálogo vazio (sem seed).
 * Screenshots em docs/v2/etapa-j3/screenshots/rux-3b-2b/
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-j3/screenshots/rux-3b-2b");
const fixtures = path.resolve(__dirname, "../../tests/fixtures/ingestion");
const ordinePdf = path.join(fixtures, "corpus_589", "Ordine_589.pdf");

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));
}

async function shot(page: import("@playwright/test").Page, name: string) {
  fs.mkdirSync(shotDir, { recursive: true });
  await page.screenshot({ path: path.join(shotDir, name), fullPage: true });
}

function assertNoTechLeak(text: string) {
  const forbidden = [
    /\bcreate_supplier\b/i,
    /\bstore_document\b/i,
    /\badd_item\b/i,
    /\blink_document\b/i,
    /\bop_key\b/i,
    /\bfingerprint\b/i,
    /\boperation_key\b/i,
  ];
  for (const re of forbidden) {
    expect(text, `vazamento técnico: ${re}`).not.toMatch(re);
  }
}

test.describe("RUX-3B-2b Ordine empty-catalog journey", () => {
  test.setTimeout(300_000);

  test("jornada 589 catálogo vazio → Order DRAFT compromisso", async ({ page, browser }) => {
    test.skip(!fs.existsSync(ordinePdf), "Ordine_589.pdf missing");

    fs.mkdirSync(shotDir, { recursive: true });
    await page.setViewportSize({ width: 1366, height: 768 });

    const consoleErrors: string[] = [];
    const unauthorized: string[] = [];
    page.on("pageerror", (err) => consoleErrors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("response", (res) => {
      if (res.status() === 401) unauthorized.push(`${res.request().method()} ${res.url()}`);
    });

    const version = await browser.version();
    fs.writeFileSync(path.join(shotDir, "chromium-version.txt"), `${version}\n`, "utf8");

    await login(page);
    // Monitor after auth — pre-login 401 do probe de sessão não conta na jornada.
    consoleErrors.length = 0;
    unauthorized.length = 0;

    // 1. Fila — importar Ordine 589 (sem seed de catálogo)
    await page.goto("/ingestion");
    await expect(page.getByTestId("ingestion-queue-page")).toBeVisible();
    await page.getByTestId("intake-new-batch").click();
    await page.getByTestId("intake-file-input").setInputFiles(ordinePdf);
    await expect(page.getByTestId("intake-files-table")).toBeVisible({ timeout: 30_000 });

    const adapterSelect = page.locator("[data-testid^=intake-adapter-select-]").first();
    await expect(adapterSelect).toBeVisible({ timeout: 60_000 });
    const opts = adapterSelect.locator("option");
    const count = await opts.count();
    if (count > 1) {
      const val = await opts.nth(1).getAttribute("value");
      if (val) await adapterSelect.selectOption(val);
    }
    await page.locator("[data-testid^=intake-run-adapter-]").first().click();
    const openLink = page.locator("[data-testid^=intake-open-doc-]").first();
    const adapterErr = page.locator(".error-text").first();
    await Promise.race([
      openLink.waitFor({ state: "visible", timeout: 120_000 }),
      adapterErr.waitFor({ state: "visible", timeout: 120_000 }).then(async () => {
        const msg = await adapterErr.innerText();
        throw new Error(`Adapter falhou na UI: ${msg}`);
      }),
    ]);
    await shot(page, "01-ordine-589-fila.png");
    await openLink.click();
    await expect(page.getByTestId("ingestion-workspace-page")).toBeVisible({ timeout: 30_000 });

    // 2. Revisão com pendência de fornecedor
    await expect(page.getByTestId("ordine-before-create-panel")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("ingestion-matching-panel")).toBeVisible();
    await shot(page, "02-revisao-pendencia.png");
    assertNoTechLeak(await page.locator("main").innerText());

    // 3. Modal cadastrar fornecedor
    await page.getByTestId("matching-create-open").click();
    await expect(page.getByTestId("matching-create-modal")).toBeVisible();
    await expect(page.getByTestId("create-supplier-name")).not.toHaveValue("");
    await shot(page, "03-modal-cadastro-fornecedor.png");
    await page.getByTestId("matching-create-confirm").click();

    // 4. Preview em português (5 passos)
    await expect(page.getByTestId("ingestion-commit-panel")).toBeVisible();
    await expect(page.getByTestId("commit-submit")).toBeEnabled({ timeout: 30_000 });
    const previewList = page.getByTestId("preview-ops-human");
    await expect(previewList).toBeVisible();
    const steps = await previewList.locator("li").allTextContents();
    expect(steps.length).toBeGreaterThanOrEqual(5);
    expect(steps.some((s) => /Cadastrar fornecedor/i.test(s))).toBeTruthy();
    expect(steps.some((s) => /Guardar o documento/i.test(s))).toBeTruthy();
    expect(steps.some((s) => /Criar pedido/i.test(s) && /rascunho/i.test(s))).toBeTruthy();
    expect(steps.some((s) => /linhas de compromisso/i.test(s))).toBeTruthy();
    expect(steps.some((s) => /Vincular o documento/i.test(s))).toBeTruthy();
    await shot(page, "04-preview-portugues.png");
    assertNoTechLeak(await page.getByTestId("ingestion-commit-panel").innerText());

    // 5. Criar pedido — resultado
    const commitRespPromise = page.waitForResponse(
      (r) => r.url().includes("/commit") && r.request().method() === "POST",
      { timeout: 90_000 },
    );
    await page.getByTestId("commit-submit").click();
    const commitResp = await commitRespPromise;
    if (!commitResp.ok()) {
      const body = await commitResp.text();
      throw new Error(`Commit HTTP ${commitResp.status()}: ${body.slice(0, 500)}`);
    }
    await expect(page.getByTestId("commit-result")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("commit-result-status")).toContainText(/Pedido criado/i);
    await expect(page.getByTestId("commit-order-open")).toBeVisible();
    await shot(page, "05-resultado-pedido-criado.png");
    assertNoTechLeak(await page.getByTestId("commit-result").innerText());

    // 6. Pedido comercial com 2 linhas de compromisso
    await page.getByTestId("commit-order-open").click();
    await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("order-header")).toBeVisible();
    const kindCells = page.locator("[data-testid^=order-item-kind-]");
    await expect(kindCells).toHaveCount(2);
    await expect(kindCells.nth(0)).toHaveText(/Compromisso/i);
    await expect(kindCells.nth(1)).toHaveText(/Compromisso/i);
    await shot(page, "06-pedido-compromissos.png");
    assertNoTechLeak(await page.locator("main").innerText());

    expect(
      consoleErrors,
      `console errors: ${consoleErrors.join(" | ")} | 401s: ${unauthorized.join(" | ")}`,
    ).toEqual([]);
    expect(unauthorized, `unexpected 401: ${unauthorized.join(" | ")}`).toEqual([]);
  });
});
