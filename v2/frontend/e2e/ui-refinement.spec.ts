import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

// Read-only: run directly with Playwright, never through database preparation wrappers.
const evidence = process.env.DEMO_EVIDENCE_DIR;
test.beforeEach(async ({ page }) => {
  const h = await (await page.request.get("/api/health")).json();
  expect(h.logical_database).toBe("epic_v2_test"); expect(h.app_env).toBe("test");
  await page.request.post("/api/auth/dev-login");
  await page.route("**/api/**", route => ["GET", "HEAD"].includes(route.request().method()) ? route.continue() : route.fulfill({ status: 503, json: { message: "Read-only visual verification: quote refresh intentionally unavailable" } }));
});
test("contract fixtures only: mixed currencies, large values, no history, Control failure and stale refresh", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 681 });
  let failRefresh = false;
  await page.route("**/api/reporting/dashboard**", async route => {
    if (new URL(route.request().url()).searchParams.get("view") === "controle" || failRefresh) {
      return route.fulfill({ status: 503, json: { message: "Fixture local de indisponibilidade; não é falha observada do servidor" } });
    }
    const response = await route.fetch(), snapshot = await response.json();
    for (const w of snapshot.widgets) {
      if (w.widget_id === "orders.to_invoice") w.display = { by_currency: [{ currency: "EUR", amount: "123456789.12" }, { currency: "USD", amount: null }, { currency: "BRL", amount: "0.00" }] };
      if (w.widget_id === "treasury.fx_trend") w.display.points = [];
      if (w.widget_id === "treasury.fx_exposure") w.display.quote.stale = true;
    }
    return route.fulfill({ response, json: snapshot });
  });
  await page.goto("/dashboard?view=executiva");
  await expect(page.getByTestId("executive-priorities")).toContainText("Não foi possível consultar as prioridades");
  await expect(page.getByTestId("dash-widget-treasury.fx_exposure")).toContainText("cotação desatualizada");
  await expect(page.getByTestId("dash-widget-orders.to_invoice").getByTitle("EUR 123.456.789,12")).toBeVisible();
  await expect(page.getByTestId("dash-widget-orders.to_invoice")).toContainText("BRL 0,00");
  await expect(page.getByTestId("dash-widget-orders.to_invoice")).toContainText("USD —");
  await expect(page.getByText("Sem cotações na série consultada.")).toBeAttached();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  // Label screenshot as test data. Overrides affect this browser only, never the database.
  await page.evaluate(() => { const label = document.createElement("div"); label.textContent = "FIXTURE DE TESTE — valores/estados alternativos, não cenário da apresentação"; label.style.cssText = "background:#fff3c4;padding:8px;font-weight:bold"; document.querySelector("#main-content")?.prepend(label); });
  if (evidence) { mkdirSync(evidence, { recursive: true }); await page.screenshot({ path: join(evidence, "fixture-mixed-large-error.png") }); }
  failRefresh = true;
  await page.getByRole("button", { name: "Atualizar", exact: true }).click();
  await expect(page.getByText(/Não foi possível atualizar o painel/)).toBeVisible();
  await expect(page.getByText(/Leitura não atualizada/)).toBeVisible();
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-demo-ready", "false");
});
for (const [name, width, height] of [["laptop", 1366, 681], ["1366x768", 1366, 768], ["fullhd", 1920, 1080]] as const) {
  test(`AP and costs ${name}: persisted values, URL filters, drawer and result hierarchy`, async ({ page }, info) => {
    await page.setViewportSize({ width, height });
    const itinerary: object[] = [];
    const save = async (label: string) => { if (evidence) { mkdirSync(evidence, { recursive: true }); await page.screenshot({ path: join(evidence, `${name}-${label}.png`) }); } };
    await page.goto("/payables?pending=OPEN_BALANCE&invoice_id=1");
    await expect(page.getByTestId("ap-table")).toContainText("1.200");
    await expect(page.getByTestId("filter-bar-active")).toContainText("Fatura: 1");
    await save("ap");
    await page.getByTestId("kpi-overdue-EUR").click();
    await expect(page).toHaveURL(/currency=EUR/); await expect(page).toHaveURL(/due_before=/);
    await expect(page.getByText("Nenhuma obrigação neste filtro", { exact: true })).toBeVisible();
    await page.getByTestId("ap-filter-due").selectOption("all");
    await expect(page.getByTestId("ap-table")).toContainText("1.200");
    await page.getByTestId("filter-bar-more-trigger").click();
    await expect(page.getByRole("dialog", { name: "Mais filtros" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("filter-bar-more-trigger")).toBeFocused();
    await page.getByTestId("ap-table").locator("tbody tr").first().locator("td").first().click();
    await expect(page.getByRole("dialog", { name: /Obrigação/ })).toContainText("800,00");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("dialog", { name: /Obrigação/ }).locator(":focus")).toHaveCount(1);
    await save("ap-drawer");
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("detail-drawer")).toHaveCount(0);
    await page.getByTestId("ap-table").getByRole("link", { name: "DEMO-FAT-20261022", exact: true }).click();
    await expect(page.getByTestId("invoice-net")).toContainText("2.000");
    await page.goBack(); await expect(page).toHaveURL(/invoice_id=1/); await expect(page).toHaveURL(/currency=EUR/);
    await page.reload(); await expect(page.getByTestId("ap-table")).toContainText("1.200");
    itinerary.push({ opened: "/payables?pending=OPEN_BALANCE&invoice_id=1", saw: "EUR1200 outstanding", clicked: "overdue EUR, All dates, More filters/Escape, drawer/Tab/Escape, invoice link, Back/reload", result: "URL context and balances retained; empty overdue result explicit; allocation EUR800 visible in drawer" });
    await page.goto("/costing/1"); await page.reload();
    await expect(page.getByTestId("costing-included-total")).toContainText("12.400");
    await expect(page.getByTestId("costing-result")).toContainText("Revisado");
    await expect(page.getByTestId("costing-freight-absent")).toBeVisible();
    const qty = await page.getByTestId("costing-products").locator("tbody tr td:nth-child(2)").allTextContents();
    expect(qty).toEqual(["10", "10"]);
    expect((await page.getByTestId("costing-included-total").boundingBox())!.y).toBeLessThan(350);
    await save("costs");
    await page.getByTestId("costing-open-version-1").click();
    await expect(page.getByTestId("costing-included-total")).toContainText("12.400");
    await page.getByTestId("costing-invoice-sources").getByRole("link", { name: "DEMO-FAT-20261022" }).click();
    await expect(page.getByTestId("invoice-net")).toContainText("2.000");
    itinerary.push({ opened: "/costing/1", saw: "BRL12400 revised/published, documentary FX, gross tax, quantity10+10, freight absent", clicked: "reload, open persisted version1, invoice source", result: "same totals and sources; no recalculation/publication" });
    await info.attach("read-only-itinerary", { body: JSON.stringify(itinerary, null, 2), contentType: "application/json" });
    if (evidence) writeFileSync(join(evidence, `${name}-ap-cost-itinerary.json`), JSON.stringify(itinerary, null, 2));
  });
  test(`executive ${name}: useful first fold, origins, tour and unchanged navigation`, async ({ page }, info) => {
    await page.setViewportSize({ width, height });
    await page.goto("/dashboard");
    await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-demo-ready", "true");
    await expect(page.getByTestId("executive-priorities")).toHaveAttribute("data-demo-control-state", "settled");
    await expect(page.getByRole("heading", { name: "Painel executivo", exact: true })).toBeVisible();
    const cta = page.getByRole("link", { name: "Consultar origem →" });
    expect((await cta.boundingBox())!.y + (await cta.boundingBox())!.height).toBeLessThan(height - 16);
    const save = async (label: string) => { if (evidence) { mkdirSync(evidence, { recursive: true }); await page.screenshot({ path: join(evidence, `${name}-${label}.png`) }); } };
    await save("dashboard-off");
    await page.getByTestId("dash-widget-ap.cash_due").getByRole("link").click();
    await expect(page.getByTestId("ap-table")).toContainText("1.200");
    await page.goBack(); await expect(page.getByTestId("executive-summary")).toBeVisible();
    await page.getByTestId("demo-start").click();
    const panel = page.getByTestId("demo-panel");
    await expect(panel).toHaveAttribute("data-phase", "running", { timeout: 25000 });
    await expect(page.getByRole("heading", { name: "Painel executivo", exact: true })).toBeInViewport();
    await expect(page.getByTestId("executive-priorities")).toHaveAttribute("data-demo-control-state", "settled");
    await page.waitForTimeout(250); // layout observer, after actual data/target readiness
    const geometry = await page.evaluate(() => ({ viewport: [innerWidth, innerHeight], outer: [outerWidth, outerHeight], dpr: devicePixelRatio, scale: visualViewport?.scale, shell: document.querySelector(".shell")?.getBoundingClientRect().toJSON(), panel: document.querySelector(".demo-panel")?.getBoundingClientRect().toJSON(), summary: document.querySelector("[data-demo-summary]")?.getBoundingClientRect().toJSON(), cta: document.querySelector(".exec-priority-footer .ui-button")?.getBoundingClientRect().toJSON(), overflow: document.documentElement.scrollWidth > innerWidth, wide: document.body.classList.contains("demo-wide") }));
    expect(geometry.overflow).toBe(false);
    expect(geometry.cta!.bottom).toBeLessThan(height - 16);
    expect(geometry.wide).toBe(width === 1920);
    await save("dashboard-tour");
    await info.attach("geometry", { body: JSON.stringify(geometry, null, 2), contentType: "application/json" });
    if (evidence) writeFileSync(join(evidence, `${name}-geometry.json`), JSON.stringify(geometry, null, 2));
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await cta.click(); await expect(page).toHaveURL(/\/customs\/1$/);
    await page.goBack(); await expect(page.getByTestId("executive-summary")).toBeVisible();
  });
}
