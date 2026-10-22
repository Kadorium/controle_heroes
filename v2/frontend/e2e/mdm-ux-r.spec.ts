/**
 * MDM-UX-R R6 — walk UI de produção (:8082 / epic_v2_test).
 * Fixture via API; operador via UI.
 */
import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOT_DIR = path.resolve(__dirname, "../../../docs/v2/etapa-mdm-ux-r/screenshots");

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));
}

async function ensureMass(page: Page) {
  for (let i = 1; i <= 55; i += 1) {
    const sku = `MDM-R-${String(i).padStart(3, "0")}`;
    const description = i === 55 ? "Fora da primeira página MDM" : `Massa visual MDM ${i}`;
    const res = await page.request.post("/api/products", { data: { sku, description } });
    expect([201, 409]).toContain(res.status());
    if (i === 55) {
      const found = await page.request.get("/api/catalog/product-list", { params: { q: sku, limit: 5 } });
      const item = (await found.json()).items.find((row: { sku: string }) => row.sku === sku);
      if (item?.id) {
        await page.request.patch(`/api/products/${item.id}`, {
          data: { commercial_name: description, is_active: true },
        });
      }
    }
  }
  const hero = await page.request.post("/api/suppliers", {
    data: { name: "Heroes", code: "HERO", country_code: "IT" },
  });
  expect([201, 409, 422]).toContain(hero.status());

  const found = await page.request.get("/api/catalog/product-list", {
    params: { q: "MDM-R-001", limit: 1 },
  });
  expect(found.ok()).toBeTruthy();
  const item = (await found.json()).items[0];
  if (item?.id) {
    await page.request.patch(`/api/products/${item.id}`, {
      data: { size: "M", color: "Red", country_of_origin: "IT", ncm: "42029200", ean: "7900000000001" },
    });
  }
}

test("MDM-UX-R walk produtos / users / supplier / rail", async ({ page }) => {
  test.setTimeout(240_000);
  await login(page);
  await ensureMass(page);

  const nav = page.getByRole("navigation", { name: /módulos/i });
  await expect(nav.getByText(/^Compras$/i)).toBeVisible();
  await expect(nav.getByText(/^Catálogo$/i)).toBeVisible();
  await expect(nav.getByRole("link", { name: /^Produtos$/i })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Fornecedores" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Prestadores" })).toHaveCount(0);
  await expect(nav.locator('a[href="/catalog/suppliers"]')).toHaveCount(0);
  await expect(nav.locator('a[href="/logistics-providers"]')).toHaveCount(0);

  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await expect(page.getByTestId("product-list-page")).toBeVisible();
  await expect(page.getByTestId("kpi-inline")).toBeVisible();
  await expect(page.getByRole("button", { name: /^buscar$/i })).toHaveCount(0);

  await page.getByTestId("products-search").fill("Fora da primeira página MDM");
  await expect(page).toHaveURL(/q=Fora/, { timeout: 10_000 });
  await expect(page.getByText("Fora da primeira página MDM", { exact: true })).toBeVisible();
  await expect(page.getByText("MDM-R-055").first()).toBeVisible();

  await page.getByTestId("products-filter-active").click();
  await page.getByTestId("products-search").fill("MDM-R-001");
  await expect(page).toHaveURL(/q=MDM-R-001/, { timeout: 10_000 });
  await expect(page.getByTestId("products-table").locator("tbody tr")).toHaveCount(1);
  await expect(page.getByText("Massa visual MDM 1", { exact: true })).toBeVisible();

  const more = page.getByTestId("filter-bar-more-trigger");
  if (await more.count()) {
    await more.click();
    await expect(page.getByTestId("filter-bar-more-panel")).toBeVisible();
    await page.getByTestId("filter-bar-more-panel").getByRole("button", { name: /^M$/ }).click();
    await expect(page.getByTestId("filter-bar-active")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.getByTestId("filter-bar-clear-all").click();
  }

  await page.getByTestId("products-sort").click();
  await page.getByRole("menuitemradio", { name: /^SKU$/i }).click();
  await page.getByTestId("products-search").fill("MDM-R-");
  await expect(page.getByTestId("products-table").locator("tbody tr")).toHaveCount(50, { timeout: 10_000 });
  await expect(page.getByTestId("products-next-page")).toBeEnabled();
  await page.getByTestId("products-next-page").click();
  await expect(page).toHaveURL(/offset=50/);

  await page.getByTestId("products-search").fill("Fora da primeira página MDM");
  await expect(page).toHaveURL(/q=Fora/, { timeout: 10_000 });
  await expect(page.getByText("Fora da primeira página MDM", { exact: true })).toBeVisible();
  await page.getByTestId("products-table").locator("tbody tr").first().click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await page.getByTestId("product-back").click();
  await expect(page.getByTestId("product-list-page")).toBeVisible();
  await expect(page.getByTestId("products-search")).toHaveValue("Fora da primeira página MDM");

  await page.getByTestId("products-table").locator("tbody tr").first().click();
  await page.getByTestId("product-edit").click();
  await expect(page.getByTestId("product-edit-page")).toBeVisible();
  const desc = page.getByTestId("product-description");
  await desc.fill("Fora da primeira página MDM editado");
  await page.getByTestId("product-save").click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: /editado/i })).toBeVisible();

  await page.getByTestId("product-toggle-active").click();
  await expect(page.getByTestId("product-toggle-active")).toHaveText(/reativar/i);
  const pickerOff = await page.request.get("/api/products", {
    params: { q: "MDM-R-055", active_only: true },
  });
  expect(pickerOff.ok()).toBeTruthy();
  expect((await pickerOff.json()).every((p: { sku: string }) => p.sku !== "MDM-R-055")).toBeTruthy();
  await page.getByTestId("product-toggle-active").click();
  await expect(page.getByTestId("product-toggle-active")).toHaveText(/inativar/i);

  const minList = await page.request.get("/api/products", { params: { q: "MDM-R-MIN" } });
  const minRow = ((await minList.json()) as Array<{ id: number; sku: string }>).find((p) => p.sku === "MDM-R-MIN");
  if (!minRow) {
    await page.goto("/catalog/products/new");
    await page.getByTestId("product-sku").fill("MDM-R-MIN");
    await page.getByTestId("product-description").fill("SKU mínimo MDM");
    await page.getByTestId("product-create-submit").click();
    await expect(page.getByTestId("product-detail-page")).toBeVisible();
  } else {
    await page.goto(`/catalog/products/${minRow.id}`);
    await expect(page.getByTestId("product-detail-page")).toBeVisible();
  }
  await page.getByTestId("product-edit").click();
  await page.getByTestId("product-ncm").fill("61091000");
  await page.getByTestId("product-save").click();
  await expect(page.getByTestId("product-detail-page")).toBeVisible();

  await page.goto("/orders/new");
  await page.getByTestId("line-sku").fill("MDM-R-001");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await expect(page.getByText("MDM-R-001").first()).toBeVisible({ timeout: 10_000 });

  await nav.getByRole("link", { name: /^Usuários$/i }).click();
  await expect(page.getByTestId("users-list-page")).toBeVisible();
  await page.getByTestId("users-search").fill("admin");
  await expect(page.getByText("admin@epic.com.br")).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: /^Ativos$/i }).click();
  await page.getByTestId("users-table").locator("tbody tr").first().click();
  await expect(page.getByTestId("user-detail-page")).toBeVisible();
  await expect(page.getByLabel(/último acesso/i)).toBeVisible();

  await nav.getByRole("link", { name: /^Produtos$/i }).click();
  await page.getByTestId("catalog-overflow").click();
  await expect(page.getByRole("menuitem", { name: /fornecedor principal/i })).toBeVisible();
  await page.getByRole("menuitem", { name: /gerenciar fornecedores/i }).click();
  await expect(page).toHaveURL(/\/catalog\/suppliers/);

  await nav.getByRole("link", { name: /^Embarques$/i }).click();
  await expect(page.getByTestId("shipments-providers-cta")).toBeVisible();
  await expect(nav.getByRole("link", { name: "Prestadores" })).toHaveCount(0);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.screenshot({ path: path.join(SHOT_DIR, "r6-1440-products.png"), fullPage: false });
  await page.setViewportSize({ width: 1366, height: 800 });
  await page.screenshot({ path: path.join(SHOT_DIR, "r6-1366-shell.png"), fullPage: false });
  await page.setViewportSize({ width: 1100, height: 800 });
  await nav.getByRole("link", { name: /^Produtos$/i }).click();
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
  await page.screenshot({ path: path.join(SHOT_DIR, "r6-1100-compact-rail.png"), fullPage: false });
  await page.getByTestId("shell-rail-toggle").click();
  await expect(page.locator(".shell--rail-open")).toBeVisible();
  await page.getByTestId("shell-rail-toggle").click();

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
  await page.screenshot({ path: path.join(SHOT_DIR, "r6-1024-compact-rail.png"), fullPage: false });
});
