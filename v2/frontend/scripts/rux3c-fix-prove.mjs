/**
 * Gate RUX-3C-fix — prova no runtime Ricardo (:8081 / epic_v2), catálogo sem Heroes.
 * Não reseta o DB (use rux3c_reset_ordine_runtime.py antes).
 */
import { chromium, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../../..");
const shotDir = path.resolve(root, "docs/v2/etapa-j3/screenshots/rux-3c-fix");
const ordinePdf = path.resolve(root, "v2/tests/fixtures/ingestion/corpus_589/Ordine_589.pdf");
const base = process.env.RUX3C_BASE_URL || "http://127.0.0.1:8081";

async function main() {
  if (!fs.existsSync(ordinePdf)) throw new Error(`PDF missing: ${ordinePdf}`);
  fs.mkdirSync(shotDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  fs.writeFileSync(path.join(shotDir, "chromium-version.txt"), `${browser.version()}\n`);

  await page.goto(`${base}/login`);
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  // Health / asset hash
  const health = await page.request.get(`${base}/api/health`);
  const hj = await health.json();
  fs.writeFileSync(path.join(shotDir, "health.json"), JSON.stringify(hj, null, 2));
  const html = await (await page.request.get(`${base}/`)).text();
  const m = html.match(/index-([A-Za-z0-9_-]+)\.js/);
  fs.writeFileSync(path.join(shotDir, "served-asset.txt"), m ? m[0] : html.slice(0, 200));

  await page.goto(`${base}/ingestion`);
  await expect(page.getByTestId("ingestion-queue-page")).toBeVisible();
  await page.getByTestId("intake-new-batch").click();
  await page.getByTestId("intake-file-input").setInputFiles(ordinePdf);
  await expect(page.getByTestId("intake-files-table")).toBeVisible({ timeout: 30_000 });
  const adapterSelect = page.locator("[data-testid^=intake-adapter-select-]").first();
  await expect(adapterSelect).toBeVisible({ timeout: 60_000 });
  const opts = adapterSelect.locator("option");
  if ((await opts.count()) > 1) {
    const val = await opts.nth(1).getAttribute("value");
    if (val) await adapterSelect.selectOption(val);
  }
  await page.locator("[data-testid^=intake-run-adapter-]").first().click();
  const openLink = page.locator("[data-testid^=intake-open-doc-]").first();
  await openLink.waitFor({ state: "visible", timeout: 120_000 });
  await page.screenshot({ path: path.join(shotDir, "01-fila.png"), fullPage: true });
  await openLink.click();
  await expect(page.getByTestId("ingestion-workspace-page")).toBeVisible({ timeout: 30_000 });

  // Supplier CTA
  await expect(page.getByTestId("ordine-before-create-panel")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("matching-create-open").click();
  await expect(page.getByTestId("matching-create-modal")).toBeVisible();
  await page.screenshot({ path: path.join(shotDir, "02-modal-fornecedor.png"), fullPage: true });
  await page.getByTestId("matching-create-confirm").click();

  // Preview PT + enabled button — no "ignorada"
  await expect(page.getByTestId("commit-submit")).toBeEnabled({ timeout: 30_000 });
  const preview = page.getByTestId("preview-ops-human");
  await expect(preview).toBeVisible();
  const text = await preview.innerText();
  if (/ignorada|IGNORADA|produto não resolvido/i.test(text)) {
    throw new Error(`Preview ainda tem skip antigo: ${text}`);
  }
  if (!/linhas de compromisso/i.test(text) || !/fatura/i.test(text)) {
    throw new Error(`Preview sem compromisso/fatura: ${text}`);
  }
  // No tech details panel
  await expect(page.getByTestId("ingestion-tech-details")).toHaveCount(0);
  await page.screenshot({ path: path.join(shotDir, "03-preview-compromisso.png"), fullPage: true });

  // Zoom
  const zoomBefore = await page.getByTestId("pdf-zoom-label").innerText();
  await page.getByTestId("pdf-zoom-in").click();
  await page.waitForTimeout(800);
  const zoomAfter = await page.getByTestId("pdf-zoom-label").innerText();
  if (zoomBefore === zoomAfter) throw new Error(`Zoom sem efeito: ${zoomBefore}`);
  await page.screenshot({ path: path.join(shotDir, "04-pdf-zoom.png"), fullPage: true });

  // Commit
  const commitResp = page.waitForResponse(
    (r) => r.url().includes("/commit") && r.request().method() === "POST",
    { timeout: 90_000 },
  );
  await page.getByTestId("commit-submit").click();
  const resp = await commitResp;
  if (!resp.ok()) throw new Error(`Commit HTTP ${resp.status()}: ${(await resp.text()).slice(0, 400)}`);
  await expect(page.getByTestId("commit-result")).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: path.join(shotDir, "05-resultado.png"), fullPage: true });
  await page.getByTestId("commit-order-open").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 30_000 });
  const kinds = page.locator("[data-testid^=order-item-kind-]");
  await expect(kinds).toHaveCount(2);
  await expect(kinds.nth(0)).toHaveText(/Compromisso/i);
  await page.screenshot({ path: path.join(shotDir, "06-pedido-compromissos.png"), fullPage: true });

  console.log("PASS screenshots →", shotDir);
  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
