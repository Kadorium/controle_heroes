/**
 * CAT-PIM Onda 1 — walk UI real (:8082 / epic_v2_test).
 * Importa os 92 via CLI guardado (nunca epic_v2).
 */
import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../../..");
const SHOT_DIR = path.resolve(REPO, "docs/v2/etapa-cat-pim/screenshots");
const PY = path.resolve(REPO, "v2/.venv/Scripts/python.exe");
const COMMIT = path.resolve(REPO, "docs/v2/etapa-cat-pim/scripts/commit_92.py");
const XLSX = path.resolve(REPO, "docs/v2/etapa-cat-pim/review/CAT_PIM_92_REVIEW.xlsx");
const DB_URL = process.env.E2E_DATABASE_URL || "postgresql://postgres@localhost:5433/epic_v2_test";

function import92() {
  if (DB_URL.includes("/epic_v2") && !DB_URL.includes("epic_v2_test")) {
    throw new Error("REFUSADO: import 92 não pode usar epic_v2");
  }
  try {
    const out = execFileSync(
      PY,
      [COMMIT, "--xlsx", XLSX, "--commit", "--i-validated-xlsx", "--database-url", DB_URL],
      { encoding: "utf-8", cwd: REPO },
    );
    console.log(out);
  } catch (err) {
    const blob = `${(err as { stdout?: string }).stdout || ""}${(err as { stderr?: string }).stderr || ""}${(err as Error).message || ""}`;
    if (blob.includes("conflitos explícitos") || blob.includes("edição manual")) {
      console.warn("import 92: lote já presente com edição manual — walk continua sobre a massa existente");
      return;
    }
    throw err;
  }
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));
}

async function searchProducts(page: Page, q: string) {
  await page.getByTestId("products-search").fill(q);
  const token = q.split(" ")[0];
  await expect.poll(() => page.url().toLowerCase().includes(token.toLowerCase()), { timeout: 10_000 }).toBeTruthy();
}

test.describe.configure({ timeout: 300_000 });

test.beforeAll(() => {
  import92();
  import92();
});

test("CAT-PIM Onda 1 walk lista / cockpit / compare / picker / rail", async ({ page }) => {
  await login(page);
  const nav = page.getByRole("navigation", { name: /módulos/i });
  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await expect(page.getByTestId("product-list-page")).toBeVisible();
  await expect(page.getByRole("button", { name: /^buscar$/i })).toHaveCount(0);
  await expect(page.getByText(/CONFIDENT/i)).toHaveCount(0);
  await expect(page.getByText(/Analisar produto/i)).toHaveCount(0);

  const listed = await page.request.get("/api/catalog/product-list", {
    params: { source_kind: "heroes_csv", limit: 1 },
  });
  expect(listed.ok()).toBeTruthy();
  const listedBody = await listed.json();
  expect(listedBody.total).toBe(92);
  expect(listedBody.summary.needs_review).toBe(40);
  expect(listedBody.summary.needs_classification_review).toBe(13);
  expect(listedBody.summary.short_generic).toBe(38);

  const classification = await page.request.get("/api/catalog/product-list", {
    params: { needs_classification_review: true, source_kind: "heroes_csv", limit: 50 },
  });
  const classificationBody = await classification.json();
  expect(classificationBody.total).toBe(13);
  expect(classificationBody.items.every((item: { needs_classification_review: boolean }) => item.needs_classification_review)).toBeTruthy();

  const general = await page.request.get("/api/catalog/product-list", {
    params: { needs_review: true, source_kind: "heroes_csv", limit: 50 },
  });
  expect((await general.json()).total).toBe(40);

  const shorts = await page.request.get("/api/catalog/product-list", {
    params: { short_generic: true, source_kind: "heroes_csv", limit: 50 },
  });
  expect((await shorts.json()).total).toBe(38);

  const weakOnly = await page.request.get("/api/catalog/product-list", {
    params: {
      short_generic: true,
      needs_classification_review: false,
      source_kind: "heroes_csv",
      limit: 50,
    },
  });
  const weakItems = (await weakOnly.json()).items as Array<{
    sku: string;
    needs_classification_review: boolean;
    taxonomy_status: string | null;
  }>;
  const confidentWeak = weakItems.find((item) => item.taxonomy_status === "CONFIDENT");
  expect(confidentWeak).toBeTruthy();
  expect(confidentWeak?.needs_classification_review).toBeFalsy();
  await page.getByTestId("filter-bar-more-trigger").click();
  await page.getByTestId("filter-bar-more-panel").getByTestId("products-filter-historical").click();
  await expect(page.getByTestId("products-table")).toBeVisible();
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1440-01-product-list.png"), fullPage: false });

  await page.getByTestId("products-filter-raquetes").click();
  await expect(page.getByTestId("products-table")).toBeVisible();
  await page.getByTestId("products-filter-acessorios").click();
  await page.getByTestId("products-filter-vestuario").click();
  await page.getByTestId("products-filter-all").click();

  await searchProducts(page, "gravity");
  await expect(page.getByText(/Gravity/i).first()).toBeVisible();
  await searchProducts(page, "beach tennis");
  await expect(page.getByTestId("products-table").locator("tbody tr")).not.toHaveCount(0);
  await searchProducts(page, "2026");
  await expect(page.getByText(/2026/).first()).toBeVisible();
  await searchProducts(page, "HARLEY");
  await expect(page.getByText("#HARLEY 2024")).toBeVisible();
  await expect(page.getByText("#HARLEY 2025")).toBeVisible();
  const harleyApi = await page.request.get("/api/catalog/product-list", {
    params: { q: "#HARLEY 202", source_kind: "heroes_csv", limit: 10 },
  });
  const harleyItems = (await harleyApi.json()).items as Array<{
    commercial_name: string;
    model: string | null;
    collection_year: string | null;
  }>;
  expect(harleyItems).toHaveLength(2);
  expect(harleyItems.every((item) => item.model === "HARLEY")).toBeTruthy();
  expect(new Set(harleyItems.map((item) => item.collection_year))).toEqual(new Set(["2024", "2025"]));

  if (confidentWeak?.sku) {
    await searchProducts(page, confidentWeak.sku);
    const weakRow = page.getByTestId("products-table").locator("tbody tr").first();
    await expect(weakRow).toBeVisible();
    await expect(weakRow).not.toContainText("Revisar classificação");
  }

  await page.getByTestId("filter-bar-clear-all").click();
  await page.getByTestId("products-filter-review").click();
  await expect(page.getByTestId("filter-bar-active")).toContainText("Precisa revisar");
  await page.getByTestId("products-filter-taxonomy-review").click();
  await expect(page.getByText(/Revisar classificação/).first()).toBeVisible();
  await page.getByTestId("filter-bar-clear-all").click();
  await page.getByTestId("products-filter-taxonomy-review").click();
  await expect(page).toHaveURL(/taxonomy_review=1/);
  await expect(page.getByTestId("products-table").locator("tbody tr")).toHaveCount(13);
  await expect(page.getByText(/Revisar classificação/).first()).toBeVisible();
  await page.getByTestId("filter-bar-clear-all").click();
  await page.getByTestId("products-filter-incomplete").click();
  await expect(page.getByTestId("products-table")).toBeVisible();

  await page.getByTestId("filter-bar-more-trigger").click();
  await expect(page.getByTestId("filter-bar-more-panel")).toBeVisible();
  const moreClose = page.getByTestId("filter-bar-more-close");
  if (await moreClose.isVisible()) await moreClose.click();
  await page.getByTestId("filter-bar-clear-all").click();
  await page.getByTestId("products-sort").click();
  await page.getByRole("menuitemradio", { name: /^SKU$/i }).click();
  await expect(page.getByTestId("products-next-page")).toBeEnabled();
  await page.getByTestId("products-next-page").click();
  await expect(page).toHaveURL(/offset=50/);

  await searchProducts(page, "ARION");
  await expect(page.getByText("#ARION 2026").first()).toBeVisible();
  await expect(page).not.toHaveURL(/offset=/);
  await page.getByTestId("products-table").locator("tbody tr").filter({ hasText: "#ARION 2026" }).first().click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /ARION 2026/ })).toBeVisible();
  await expect(page.getByText("Não informado").first()).toBeVisible();
  await expect(page.getByText(/Analisar produto/i)).toHaveCount(0);
  await expect(page.getByText(/CONFIDENT/)).toHaveCount(0);
  await page.getByTestId("product-pendencies").click();
  await expect(page.getByTestId("product-quality-list")).toBeVisible();
  await expect(page.getByText(/informação fiscal pendente/i).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Origem da informação" })).toBeVisible();
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1440-02-arion-cockpit.png"), fullPage: false });

  await page.getByTestId("product-edit").click();
  await expect(page.getByTestId("product-edit-page")).toBeVisible();
  const typeSelect = page.getByTestId("product-type");
  const previous = await typeSelect.inputValue();
  const options = await typeSelect.locator("option").all();
  let other = "";
  for (const opt of options) {
    const value = await opt.getAttribute("value");
    if (value && value !== previous) {
      other = value;
      break;
    }
  }
  expect(other).not.toBe("");
  await typeSelect.selectOption(other);
  await expect(page.getByText(/preservadas até você revisar/i)).toBeVisible();
  await page.getByTestId("product-save").click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await page.reload();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: /ARION/ })).toBeVisible();
  await page.getByTestId("product-edit").click();
  await expect(page.getByTestId("product-edit-page")).toBeVisible();
  await page.getByTestId("product-type").selectOption(previous);
  await page.getByTestId("product-save").click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();

  await page.getByTestId("product-back").click();
  await expect(page.getByTestId("product-list-page")).toBeVisible();
  await expect(page.getByTestId("products-search")).toHaveValue("ARION");

  await page.getByTestId("filter-bar-clear-all").click();
  await searchProducts(page, "Pallina");
  await page.getByTestId("products-table").locator("tbody tr").first().click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await expect(page.getByText("Revisar classificação").first()).toBeVisible();
  await expect(page.getByText(/CONFIDENT|DERIVADO|\bFAKE\b/)).toHaveCount(0);
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1440-03-bola-review.png"), fullPage: false });

  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await searchProducts(page, "HARLEY 202");
  const harleyRows = page.getByTestId("products-table").locator("tbody tr").filter({ hasText: "#HARLEY" });
  await expect(harleyRows).toHaveCount(2);
  await harleyRows.nth(0).locator('input[type="checkbox"]').check();
  await harleyRows.nth(1).locator('input[type="checkbox"]').check();
  await page.getByTestId("products-compare").click();
  await expect(page.getByTestId("product-compare-page")).toBeVisible();
  await expect(page.getByTestId("compare-table")).toContainText("HARLEY");
  await expect(page.getByTestId("compare-table")).toContainText("2024");
  await expect(page.getByTestId("compare-table")).toContainText("2025");
  await page.getByTestId("compare-diffs-only").check();
  await expect(page.getByTestId("compare-table")).toContainText("Coleção");
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1440-04-compare-harley.png"), fullPage: false });

  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await searchProducts(page, "PURE");
  const felpa = page.getByTestId("products-table").locator("tbody tr").filter({ hasText: /PURE (RED|WHITE)/ });
  await expect(felpa).toHaveCount(2);
  await felpa.nth(0).locator('input[type="checkbox"]').check();
  await felpa.nth(1).locator('input[type="checkbox"]').check();
  await page.getByTestId("products-compare").click();
  await expect(page.getByTestId("compare-table")).toContainText("Não informado");
  await expect(page.getByTestId("compare-table")).toContainText("PURE RED");
  await expect(page.getByTestId("compare-table")).toContainText("PURE WHITE");
  const felpaApi = await page.request.get("/api/catalog/product-list", {
    params: { q: "PURE", source_kind: "heroes_csv", limit: 10 },
  });
  const felpaItems = (await felpaApi.json()).items as Array<{
    model: string | null;
    color: string | null;
  }>;
  const felpaPair = felpaItems.filter((item) => item.color === "PURE RED" || item.color === "PURE WHITE");
  expect(felpaPair).toHaveLength(2);
  expect(felpaPair.every((item) => !item.model)).toBeTruthy();
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1440-05-compare-felpa.png"), fullPage: false });

  await page.goto("/orders/new");
  await page.getByTestId("line-sku").fill("#ARION 2026");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await expect(page.getByText("HEROES-BT-ARION-2026").first()).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("line-sku").fill("HEROES-BT-ARION-2026");
  await page.getByRole("button", { name: /adicionar linha/i }).click();

  await page.setViewportSize({ width: 1440, height: 900 });
  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await page.setViewportSize({ width: 1366, height: 800 });
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1366-list.png"), fullPage: false });
  await page.setViewportSize({ width: 1100, height: 800 });
  const leaked1100 = await page.evaluate(() => {
    const rail = document.querySelector(".shell-sidebar") as HTMLElement | null;
    if (!rail) return "no-rail";
    if (rail.getBoundingClientRect().width > 64) return `rail=${rail.getBoundingClientRect().width}`;
    const labels = [...document.querySelectorAll(".shell-nav-label, .nav-group-title, .shell-brand-full, .shell-user")];
    const visible = labels.filter((el) => {
      const s = getComputedStyle(el);
      if (s.display === "none" || s.visibility === "hidden") return false;
      const r = el.getBoundingClientRect();
      return r.width > 2 && r.height > 2;
    });
    return visible.length ? visible.map((el) => el.textContent?.trim()).join("|") : "";
  });
  expect(leaked1100, "rail compacto 1100 não pode vazar texto").toBe("");
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1100-compact-rail.png"), fullPage: false });
  await page.setViewportSize({ width: 1024, height: 768 });
  const leaked1024 = await page.evaluate(() => {
    const rail = document.querySelector(".shell-sidebar") as HTMLElement | null;
    if (!rail) return "no-rail";
    if (rail.getBoundingClientRect().width > 64) return `rail=${rail.getBoundingClientRect().width}`;
    const labels = [...document.querySelectorAll(".shell-nav-label, .nav-group-title, .shell-brand-full")];
    return labels.some((el) => {
      const s = getComputedStyle(el);
      if (s.display === "none") return false;
      const r = el.getBoundingClientRect();
      return r.width > 2 && r.height > 2;
    })
      ? "leaked"
      : "";
  });
  expect(leaked1024).toBe("");
  await page.screenshot({ path: path.join(SHOT_DIR, "onda1-1024-compact-rail.png"), fullPage: false });
});
