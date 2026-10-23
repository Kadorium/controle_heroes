import { test, expect, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

// Read-only suite: call Playwright directly, NOT e2e:prepare / e2e:j8.
const evidence = process.env.DEMO_EVIDENCE_DIR;
const duration = process.env.DEMO_REHEARSAL === "true" ? "50" : "2";
test.use({ viewport: process.env.DEMO_FULL_HD === "true" ? { width: 1920, height: 1080 } : { width: 1366, height: process.env.DEMO_LAPTOP_SHORT === "true" ? 681 : 768 }, deviceScaleFactor: 1 });

async function login(page: Page) {
  const health = await (await page.request.get("/api/health")).json();
  expect(health.logical_database).toBe("epic_v2_test"); expect(health.app_env).toBe("test");
  expect((await page.request.post("/api/auth/dev-login")).ok()).toBeTruthy();
  await page.goto("/dashboard");
  await expect(page.getByTestId("demo-start")).toBeVisible();
}
async function start(page: Page) {
  await page.getByTestId("demo-start").click();
  await expect(page.getByTestId("demo-panel")).toHaveAttribute("data-phase", "running", { timeout: 25000 });
}
async function capture(page: Page, name: string) {
  if (!evidence) return;
  mkdirSync(evidence, { recursive: true });
  await page.screenshot({ path: join(evidence, `${name}.png`) });
}
async function openPurchaseNavigation(page: Page, name: string) {
  const link = page.getByRole("link", { name, exact: true });
  if (!await link.isVisible()) await page.getByText("Compras e documentos", { exact: true }).click();
  await link.click();
}

test("automatic eight steps, repeatable and read-only", async ({ page }) => {
  test.setTimeout(duration === "50" ? 510000 : 90000);
  if (process.env.DEMO_QUOTE_OFFLINE === "true") {
    await page.route("**/api/fx/quotes/**", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"message":"Cotação indisponível no ensaio"}' }));
  }
  await login(page);
  if (process.env.DEMO_QUOTE_OFFLINE === "true") await expect(page.getByTestId("fx-quote-strip")).toContainText(/indisponível|Erro|Falha/i);
  const writes: string[] = [], itinerary: object[] = [];
  page.on("request", r => { if (!["GET", "HEAD", "OPTIONS"].includes(r.method())) writes.push(`${r.method()} ${new URL(r.url()).pathname}`); });
  const started = Date.now();
  await start(page);
  await page.getByText("Ritmo e informações", { exact: true }).click();
  await page.getByLabel("Tempo por etapa").selectOption(duration);
  await page.getByText("Ritmo e informações", { exact: true }).click();
  const manifest = await (await page.request.get('/assets/demo-manifest.json')).json();
  const targets = ['[data-demo-ready="true"] [data-demo-summary]', '[data-demo-document] [data-pdf-ready="true"]', '[data-testid="payables-list"]', '[data-testid="alloc-list"]', '[data-testid="shipment-items"]', '[data-testid="customs-section-liberacoes"]', manifest.scenario_id.startsWith('DEMO-HEROES') ? '.stock-numbers' : '[data-testid="sku-buckets"]', '[data-testid="costing-result"]'];
  for (let n = 1; n <= 8; n++) {
    const panel = page.getByTestId("demo-panel");
    await expect(panel).toHaveAttribute("data-step", String(n), { timeout: 65000 });
    await expect(panel).toHaveAttribute("data-phase", "running", { timeout: 20000 });
    const el = page.locator(targets[n - 1]);
    await expect(el).toBeVisible();
    await expect(el).toHaveClass(/demo-highlight/);
    const box = await el.boundingBox(), panelBox = await panel.boundingBox();
    expect(panelBox!.y).toBeGreaterThanOrEqual(0);
    await expect(panel.getByRole("button", { name: "Pausar", exact: true })).toBeInViewport();
    await expect(panel.getByRole("button", { name: "Sair do tour", exact: true })).toBeInViewport();
    if (await page.locator("body").evaluate(el => el.classList.contains("demo-wide"))) expect(box!.x + box!.width).toBeLessThanOrEqual(panelBox!.x + 1);
    else expect(box!.y).toBeGreaterThanOrEqual(panelBox!.y + panelBox!.height - 1);
    itinerary.push({ step: n, route: new URL(page.url()).pathname, elapsed_seconds: Math.round((Date.now() - started) / 1000), viewport: page.viewportSize(), zoom: await page.evaluate(() => window.visualViewport?.scale), observed: (await el.innerText()).slice(0, 4000) });
    await capture(page, `tour-${duration}s-${n}`);
  }
  await expect(page.getByTestId("demo-panel")).toHaveAttribute("data-phase", "complete", { timeout: 65000 });
  expect(writes.filter(p => !/\/fx\/quotes\//.test(p))).toEqual([]);
  if (evidence) writeFileSync(join(evidence, `tour-${duration}s-itinerary.json`), JSON.stringify({ elapsed_seconds: Math.round((Date.now()-started)/1000), writes, itinerary }, null, 2));
  await page.getByRole("button", { name: "Sair do tour", exact: true }).click();
  await expect(page.getByTestId("demo-start")).toBeFocused();
  await expect(page.locator(".demo-highlight")).toHaveCount(0);
});

test("pause, resume, previous, next, chapter, manual navigation and keyboard exit", async ({ page }) => {
  await login(page); await start(page);
  const panel = page.getByTestId("demo-panel");
  await page.getByRole("button", { name: "Pausar", exact: true }).click();
  await expect(panel).toHaveAttribute("data-phase", "paused");
  await page.waitForTimeout(2200);
  await expect(panel).toHaveAttribute("data-step", "1");
  await page.getByRole("button", { name: "Continuar", exact: true }).click();
  await expect(panel).toHaveAttribute("data-phase", "running");
  await panel.getByRole("button", { name: "Recolher", exact: true }).click();
  await expect(panel).toHaveAttribute("data-phase", "running");
  await page.setViewportSize({ width: 1920, height: 1080 });
  await expect(panel).toHaveAttribute("data-step", "1");
  await expect(panel).toHaveAttribute("data-phase", "running");
  await page.setViewportSize({ width: 1366, height: 681 });
  await panel.getByRole("button", { name: "Expandir", exact: true }).click();
  await expect(panel).toHaveAttribute("data-phase", "running");
  await panel.getByRole("button", { name: "Próximo", exact: true }).click();
  await expect(panel).toHaveAttribute("data-step", "2");
  await expect(page.locator('[data-demo-document] [data-pdf-ready="true"]')).toBeVisible();
  await panel.getByRole("button", { name: "Anterior", exact: true }).click();
  await expect(panel).toHaveAttribute("data-step", "1");
  await page.getByLabel("Escolher etapa").selectOption("7");
  await expect(panel).toHaveAttribute("data-step", "8");
  await expect(panel).toHaveAttribute("data-phase", "running");
  await openPurchaseNavigation(page, "Pedidos");
  await expect(panel).toHaveAttribute("data-phase", "paused");
  await expect(page).toHaveURL(/\/orders$/);
  await page.keyboard.press("Escape");
  await expect(panel).toHaveCount(0);
  await expect(page.getByTestId("demo-start")).toBeFocused();
  await openPurchaseNavigation(page, "Faturas");
  await expect(page).toHaveURL(/\/invoices$/);
});

test("missing target interrupts, exit cancels loading and does not navigate later", async ({ page }) => {
  await login(page); await start(page);
  const currentManifest = await (await page.request.get('/assets/demo-manifest.json')).json();
  await page.route(`**/api/shipments/${currentManifest.ids.shipment}`, route => route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"Falha controlada do ensaio"}' }));
  await page.getByLabel("Escolher etapa").selectOption("4");
  await expect(page.getByTestId("demo-panel")).toHaveAttribute("data-phase", "error", { timeout: 20000 });
  await expect(page.getByTestId("demo-panel")).toContainText(/interrompido|erro/i);
  await capture(page, "tour-target-unavailable");
  await page.unroute(`**/api/shipments/${currentManifest.ids.shipment}`);
  await page.route('**/api/reporting/stock-explorer?*', async route => { await new Promise(r => setTimeout(r, 4000)); await route.continue().catch(()=>{}); });
  await page.getByLabel("Escolher etapa").selectOption("6");
  await expect(page.getByTestId("demo-panel")).toHaveAttribute("data-phase", "loading");
  await page.getByRole("button", { name: "Sair do tour", exact: true }).click();
  await openPurchaseNavigation(page, "Pedidos");
  await page.waitForTimeout(4500);
  await expect(page).toHaveURL(/\/orders$/);
  await expect(page.getByTestId("demo-panel")).toHaveCount(0);
  await expect(page.locator(".demo-highlight")).toHaveCount(0);
});

test("changed manifest refuses to start without business writes", async ({ page }) => {
  await login(page);
  await page.route("**/demo-manifest.json", async route => {
    const response = await route.fetch(); const data = await response.json();
    data.checks[0].fields.code = "WRONG-SCENARIO";
    await route.fulfill({ response, json: data });
  });
  await page.getByTestId("demo-start").click();
  await expect(page.getByTestId("demo-panel")).toHaveAttribute("data-phase", "error");
  await expect(page.getByTestId("demo-panel")).toContainText("Cenário alterado");
});

test("full HD, reloaded invoice, cost sources and dashboard origin", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await login(page); await start(page);
  await page.getByRole("button", { name: "Pausar", exact: true }).click();
  await capture(page, "tour-fullhd-dashboard");
  await page.getByRole("button", { name: "Sair do tour", exact: true }).click();
  const main = page.locator("#main-content");
  console.log("Dashboard origin links:", await main.getByRole("link").evaluateAll(es => es.map(e => ({ text: e.textContent, href: e.getAttribute("href") }))));
  await main.getByTestId("dash-widget-ap.cash_due").getByRole("link").click();
  await expect(page.getByTestId("ap-table")).toContainText("1.200");
  await capture(page, "dashboard-to-ap-fullhd");
  await page.goto("/invoices/1"); await page.reload();
  await expect(page.getByTestId("term-date-0")).toContainText("21/11/2026");
  await expect(page.getByTestId("term-date-1")).toHaveCount(0);
  await expect(page.getByTestId("payables-list")).toContainText("1.200");
  await capture(page, "invoice-reloaded-one-term");
  await page.goto("/costing/1"); await page.reload();
  await expect(page.getByTestId("costing-products")).toContainText("620");
  await expect(page.getByTestId("costing-components")).toContainText("12.000");
  await expect(page.getByTestId("costing-included-total")).toContainText("12.400");
  await page.getByTestId("costing-products").scrollIntoViewIfNeeded();
  await capture(page, "cost-published-fullhd");
  const documentLink = page.getByTestId("costing-expenses").getByRole("link", { name: "Documento #6" });
  await expect(documentLink).toHaveAttribute("href", "/api/documents/6/content");
  const sourceResponse = page.context().waitForEvent("response", r => r.url().endsWith("/api/documents/6/content"));
  await documentLink.click();
  // Headless Chromium may download PDFs and keep the popup at about:blank.
  // This proves the UI action fetched the source, not native-viewer fidelity.
  const source = await sourceResponse;
  expect(source.status()).toBe(200); expect(source.headers()["content-type"]).toBe("application/pdf");
  for (const extra of page.context().pages()) if (extra !== page) await extra.close();
  await page.getByTestId("costing-invoice-sources").getByRole("link", { name: "DEMO-FAT-20261022" }).click();
  await expect(page.getByTestId("invoice-net")).toContainText("2.000");
});
