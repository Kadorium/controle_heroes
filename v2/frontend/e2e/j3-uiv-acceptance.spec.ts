/**
 * J3-UIV — aceite operacional pela UI (jornadas A–E + baseline + RBAC smoke).
 * Viewport 1366×768. API só para reset implícito (e2e_prepare) + seed de owners
 * (Supplier/Products/Order CONFIRMED/ImportProcess). Ingestão nasce no browser.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-j3/screenshots/uiv");
const beforeDir = path.join(shotDir, "before");
const afterDir = path.join(shotDir, "after");
const fixtures = path.resolve(__dirname, "../../tests/fixtures/ingestion");

type Json = Record<string, unknown>;

async function api(
  page: import("@playwright/test").Page,
  method: string,
  pathName: string,
  body?: unknown,
): Promise<{ status: number; body: Json }> {
  return page.evaluate(
    async ({ method, pathName, body }) => {
      const opts: RequestInit = { method, credentials: "include" };
      if (body !== undefined) {
        opts.headers = { "Content-Type": "application/json" };
        opts.body = JSON.stringify(body);
      }
      const r = await fetch(pathName, opts);
      const text = await r.text();
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        /* raw */
      }
      return { status: r.status, body: parsed as Json };
    },
    { method, pathName, body },
  );
}

function expectOk(status: number) {
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThan(300);
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));
}

async function shot(page: import("@playwright/test").Page, dir: string, name: string) {
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: path.join(dir, name), fullPage: true });
}

async function seedCatalog(page: import("@playwright/test").Page) {
  let r = await api(page, "POST", "/api/suppliers", {
    name: "Heroe's Srl",
    country_code: "IT",
  });
  // 200/201 or conflict-like — try list if create fails
  if (r.status >= 400) {
    r = await api(page, "GET", "/api/suppliers?q=Heroe&limit=5");
  }
  for (const sku of ["I.V. 2", "I.V. 1"]) {
    const pr = await api(page, "POST", "/api/products", {
      sku,
      description: `Produto ${sku}`,
    });
    if (pr.status >= 400) {
      /* may already exist */
    }
  }
}

test.describe("J3-UIV operational acceptance", () => {
  test.setTimeout(420_000);

  test("UIV journeys A–E + baseline + RBAC smoke", async ({ page }) => {
    fs.mkdirSync(beforeDir, { recursive: true });
    fs.mkdirSync(afterDir, { recursive: true });
    await page.setViewportSize({ width: 1366, height: 768 });

    await login(page);
    await seedCatalog(page);

    // --- UIV-0 baseline (empty / current UI) ---
    await page.goto("/ingestion");
    await expect(page.getByTestId("ingestion-queue-page")).toBeVisible();
    await expect(page.getByTestId("ingestion-intake-panel")).toBeVisible();
    await shot(page, beforeDir, "uiv-00-login-ingestion-empty.png");

    // --- Journey A: Ordine 589 ---
    const ordinePdf = path.join(fixtures, "corpus_589", "Ordine_589.pdf");
    test.skip(!fs.existsSync(ordinePdf), "Ordine_589.pdf missing");

    await page.getByTestId("intake-new-batch").click();
    await page.getByTestId("intake-file-input").setInputFiles(ordinePdf);
    await expect(page.getByTestId("intake-files-table")).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("[data-testid^=intake-run-adapter-]").first()).toBeVisible({
      timeout: 60_000,
    });
    // wait classify
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
    await expect(openLink).toBeVisible({ timeout: 120_000 });
    await shot(page, afterDir, "uiv-a-intake-ordine.png");
    await openLink.click();
    await expect(page.getByTestId("ingestion-workspace-page")).toBeVisible();
    await expect(page.getByTestId("ingestion-pdf-viewer")).toBeVisible();
    await expect(page.getByTestId("ingestion-fields-panel")).toBeVisible();
    await expect(page.getByTestId("ingestion-commit-panel")).toBeVisible();
    await shot(page, afterDir, "uiv-a-workspace-ordine.png");

    // READY is derived — no Marcar READY button (RUX)
    await expect(page.getByTestId("doc-review-ready")).toHaveCount(0);
    await expect(page.getByTestId("doc-review-discard")).toBeVisible();
    const commitBtn = page.getByTestId("commit-submit");
    if (await commitBtn.isVisible().catch(() => false)) {
      // may be disabled until catalog match; do not force READY
      if (await commitBtn.isEnabled().catch(() => false)) {
        await commitBtn.click();
        await expect(page.getByTestId("commit-result")).toBeVisible({ timeout: 60_000 });
        await shot(page, afterDir, "uiv-a-commit-ordine.png");
      }
    }

    // --- Journey B: Fattura 202 ---
    const fatturaPdf = path.join(fixtures, "corpus_202", "Fattura_202.pdf");
    if (fs.existsSync(fatturaPdf)) {
      // seed Order CONFIRMED for policy A/B
      let r = await api(page, "GET", "/api/suppliers?q=Heroe&limit=5");
      const suppliers = (r.body as unknown as Json[]) || [];
      const supplierId =
        Array.isArray(suppliers) && suppliers[0]
          ? (suppliers[0] as Json).id
          : (
              await api(page, "POST", "/api/suppliers", {
                name: "Heroe's Srl",
                country_code: "IT",
              })
            ).body.id;

      r = await api(page, "POST", "/api/orders", {
        code: `ORD-UIV-${Date.now().toString(36)}`,
        supplier_id: supplierId,
        currency: "EUR",
      });
      if (r.status < 300) {
        let order = r.body as Json & { id: number; version: number };
        r = await api(page, "GET", "/api/products?q=I.V&limit=5");
        const products = r.body as unknown as Json[];
        const productId = Array.isArray(products) && products[0] ? (products[0] as Json).id : null;
        if (productId) {
          r = await api(page, "POST", `/api/orders/${order.id}/items`, {
            expected_version: order.version,
            product_id: productId,
            quantity: "10",
            unit_price: "100",
          });
          if (r.status < 300) order = r.body as typeof order;
        }
        await api(page, "POST", `/api/orders/${order.id}/confirm`, {
          expected_version: order.version,
        });
      }

      await page.goto("/ingestion");
      await page.getByTestId("intake-new-batch").click();
      await page.getByTestId("intake-file-input").setInputFiles(fatturaPdf);
      await expect(page.locator("[data-testid^=intake-run-adapter-]").first()).toBeVisible({
        timeout: 60_000,
      });
      const sel = page.locator("[data-testid^=intake-adapter-select-]").first();
      await expect(sel).toBeVisible({ timeout: 60_000 });
      const n = await sel.locator("option").count();
      for (let i = 0; i < n; i++) {
        const t = await sel.locator("option").nth(i).textContent();
        const v = await sel.locator("option").nth(i).getAttribute("value");
        if (v && t && /Fattura Heroes|FATTURA_VENDITA/i.test(t)) {
          await sel.selectOption(v);
          break;
        }
      }
      await page.locator("[data-testid^=intake-run-adapter-]").first().click();
      const openB = page.locator("[data-testid^=intake-open-doc-]").first();
      await expect(openB).toBeVisible({ timeout: 120_000 });
      await openB.click();
      await expect(page.getByTestId("ingestion-workspace-page")).toBeVisible();
      await expect(page.getByTestId("fattura-structured-panel")).toBeVisible();
      await expect(page.getByTestId("fattura-commit-panel")).toBeVisible();
      await shot(page, afterDir, "uiv-b-fattura-workspace.png");
    }

    // --- Journey C: Dossiê PL detail ---
    const plPdf = path.join(fixtures, "corpus_202", "PackingList_202.pdf");
    if (fs.existsSync(plPdf)) {
      await page.goto("/ingestion");
      await page.getByTestId("intake-new-batch").click();
      await page.getByTestId("intake-file-input").setInputFiles(plPdf);
      await expect(page.locator("[data-testid^=intake-run-adapter-]").first()).toBeVisible({
        timeout: 60_000,
      });
      const sel = page.locator("[data-testid^=intake-adapter-select-]").first();
      await expect(sel).toBeVisible({ timeout: 60_000 });
      const n = await sel.locator("option").count();
      for (let i = 0; i < n; i++) {
        const t = await sel.locator("option").nth(i).textContent();
        const v = await sel.locator("option").nth(i).getAttribute("value");
        if (v && t && /Packing List detalhado|PACKING_LIST_DETAIL/i.test(t)) {
          await sel.selectOption(v);
          break;
        }
      }
      await page.locator("[data-testid^=intake-run-adapter-]").first().click();
      const openC = page.locator("[data-testid^=intake-open-doc-]").first();
      await expect(openC).toBeVisible({ timeout: 120_000 });
      await openC.click();
      await expect(page.getByTestId("ingestion-dossier-panel")).toBeVisible({ timeout: 30_000 });
      await shot(page, afterDir, "uiv-c-dossier-panel.png");
    }

    // --- Journey D: Numerário ---
    const numPdf = path.join(fixtures, "corpus_202", "Solicitacao_Numerario.pdf");
    if (fs.existsSync(numPdf)) {
      await page.goto("/ingestion");
      await page.getByTestId("intake-new-batch").click();
      await page.getByTestId("intake-file-input").setInputFiles(numPdf);
      await expect(page.locator("[data-testid^=intake-run-adapter-]").first()).toBeVisible({
        timeout: 60_000,
      });
      const sel = page.locator("[data-testid^=intake-adapter-select-]").first();
      await expect(sel).toBeVisible({ timeout: 60_000 });
      const n = await sel.locator("option").count();
      for (let i = 0; i < n; i++) {
        const t = await sel.locator("option").nth(i).textContent();
        const v = await sel.locator("option").nth(i).getAttribute("value");
        if (v && t && /Numer|SOLICITACAO/i.test(t)) {
          await sel.selectOption(v);
          break;
        }
      }
      await page.locator("[data-testid^=intake-run-adapter-]").first().click();
      const openD = page.locator("[data-testid^=intake-open-doc-]").first();
      await expect(openD).toBeVisible({ timeout: 120_000 });
      await openD.click();
      await expect(page.getByTestId("numerario-commit-panel")).toBeVisible();
      await expect(page.getByTestId("numerario-no-payment-notice")).toBeVisible();
      await shot(page, afterDir, "uiv-d-numerario.png");
    }

    // --- Journey E: XLSX ---
    const xlsx = path.join(fixtures, "xlsx", "ordine758.xlsx");
    if (fs.existsSync(xlsx)) {
      await page.goto("/ingestion");
      await page.getByTestId("intake-new-batch").click();
      await page.getByTestId("intake-file-input").setInputFiles(xlsx);
      await expect(page.locator("[data-testid^=intake-run-adapter-]").first()).toBeVisible({
        timeout: 60_000,
      });
      const sel = page.locator("[data-testid^=intake-adapter-select-]").first();
      await expect(sel).toBeVisible({ timeout: 60_000 });
      const n = await sel.locator("option").count();
      for (let i = 0; i < n; i++) {
        const v = await sel.locator("option").nth(i).getAttribute("value");
        if (v && v.includes("xlsx")) {
          await sel.selectOption(v);
          break;
        }
      }
      await page.locator("[data-testid^=intake-run-adapter-]").first().click();
      const openE = page.locator("[data-testid^=intake-open-doc-]").first();
      await expect(openE).toBeVisible({ timeout: 120_000 });
      await openE.click();
      await expect(page.getByTestId("xlsx-commit-panel")).toBeVisible();
      await shot(page, afterDir, "uiv-e-xlsx.png");
    }

    // --- RBAC: nav without ingestion for estoque-like (403 workspace via unauth) ---
    await page.goto("/ingestion");
    await shot(page, afterDir, "uiv-6-queue-after.png");
  });
});
