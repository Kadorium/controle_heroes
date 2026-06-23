import { expect, test } from "@playwright/test";
import { getDemoImportationId } from "./helpers";

/**
 * Fase pós-MVP 6 — UX operacional estilo planilha.
 * Fluxos de usuário real: grade densa, edição inline, cadastro rápido,
 * Central da Ordem em seções empilhadas, financeiro acionável, Heroes guiado.
 */
test.describe("UX pós-MVP 6 — planilha operacional", () => {
  test.beforeEach(async ({ page }) => {
    await page.request.post("/api/demo/seed").catch(() => undefined);
  });

  test("grade /importacoes é densa estilo planilha (header fixo + totais)", async ({ page }) => {
    const queueReady = page.waitForResponse(
      (r) => r.url().includes("/api/importations/order-queue") && r.ok(),
      { timeout: 120_000 }
    );
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await queueReady;
    await expect(page.getByRole("heading", { name: /^Ordens$/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator(".sheet-grid")).toBeVisible({ timeout: 15000 });
    await expect(page.locator(".sheet-grid thead th.sticky-col").first()).toBeVisible();
    // totais por moeda no rodapé
    await expect(page.locator(".sheet-grid tfoot")).toBeVisible();
    // filtros rápidos
    await expect(page.getByRole("button", { name: "Com saldo a pagar" })).toBeVisible();
  });

  test("edição inline de prioridade na grade persiste após recarregar", async ({ page }) => {
    const queueReady = page.waitForResponse(
      (r) => r.url().includes("/api/importations/order-queue") && r.ok(),
      { timeout: 120_000 }
    );
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await queueReady;
    const firstRow = page.locator(".sheet-grid tbody tr").first();
    await expect(firstRow).toBeVisible({ timeout: 15000 });
    const po = (await firstRow.locator(".sheet-grid__open").innerText()).trim();
    // primeira célula editável da linha = prioridade
    const prioCell = firstRow.locator(".editable-cell").first();
    await prioCell.click();
    await page.locator(".editable-cell__input").selectOption("HIGH");
    await page.keyboard.press("Enter");
    await expect(firstRow.locator(".prio-badge--HIGH")).toBeVisible({ timeout: 10000 });

    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForResponse((r) => r.url().includes("/api/importations/order-queue") && r.ok(), { timeout: 120_000 });
    const reloadedRow = page.locator(".sheet-grid tbody tr", { hasText: po }).first();
    await expect(reloadedRow.locator(".prio-badge--HIGH")).toBeVisible({ timeout: 15000 });
  });

  test("cadastro rápido cria ordem e abre a Central", async ({ page }) => {
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "+ Nova ordem" }).click();
    await expect(page.getByRole("heading", { name: "Nova ordem" })).toBeVisible();
    await expect(page.locator(".nova-ordem__grid")).toBeVisible();

    const po = `E2E6-${Date.now()}`;
    await page.locator("#nova-po").fill(po);
    const supplier = page.locator("#nova-supplier");
    await expect(supplier).toBeVisible();
    const heroes = supplier.locator('option', { hasText: /^Heroes/i }).first();
    if ((await heroes.count()) > 0) {
      await supplier.selectOption({ label: (await heroes.innerText()).trim() });
    } else {
      await supplier.selectOption({ index: 1 });
    }
    await page.locator(".product-combobox__input").first().fill("Modelo E2E");

    await page.getByRole("button", { name: "Criar e abrir ordem" }).click();
    await expect(page).toHaveURL(/\/importacoes\/\d+\/resumo/, { timeout: 20000 });
    await expect(page.getByRole("heading", { name: new RegExp(`Central da Ordem ${po}`, "i") })).toBeVisible({ timeout: 20000 });
  });

  test("Central da Ordem mostra seções empilhadas na primeira tela", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-04-3INV");
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /Resumo operacional/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /^Pagamentos$/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /a despachar · preço e desconto/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /^Documentos$/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByRole("heading", { name: /Histórico recente/i })).toBeVisible({ timeout: 20000 });
  });

  test("faturas aparecem como etapas (antecipo / chegada / saldo)", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-04-3INV");
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Faturas · acconto · crédito por/i })).toBeVisible({ timeout: 20000 });
    // faixa de etapas com múltiplos cards
    const stages = page.locator(".inv-stage");
    await expect(stages.first()).toBeVisible({ timeout: 15000 });
    expect(await stages.count()).toBeGreaterThan(1);
    await expect(page.getByText("Fatura 1").first()).toBeVisible();
    await expect(page.getByText(/antecipo.*na chegada.*saldo \(30\/60 dias\)/i)).toBeVisible();
    // grade detalhada tem coluna Etapa
    await expect(page.getByRole("columnheader", { name: "Etapa" })).toBeVisible();
  });

  test("grade de ordens mostra contador de faturas (quitadas/total)", async ({ page }) => {
    const queueReady = page.waitForResponse(
      (r) => r.url().includes("/api/importations/order-queue") && r.ok(),
      { timeout: 120_000 }
    );
    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await queueReady;
    await expect(page.getByRole("columnheader", { name: "Faturas" })).toBeVisible({ timeout: 15000 });
    await expect(page.locator(".inv-count").first()).toBeVisible({ timeout: 15000 });
  });

  test("edição inline de responsável no cabeçalho da Central persiste", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-05-MULTI");
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    const resp = page.getByLabel("Responsável");
    await expect(resp).toBeVisible({ timeout: 20000 });
    const value = `Resp ${Date.now() % 100000}`;
    await resp.fill(value);
    await resp.blur();
    await page.waitForTimeout(600);
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByLabel("Responsável")).toHaveValue(value, { timeout: 20000 });
  });

  test("adicionar pagamento planejado e liquidar na Central", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-04-3INV");
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /^Pagamentos$/i })).toBeVisible({ timeout: 20000 });

    await page.getByRole("button", { name: "+ Pagamento planejado" }).click();
    const paySection = page.locator(".oc-section", { hasText: "Pagamentos" });
    const addBar = paySection.locator(".oc-actbar").last();
    await addBar.locator("select").selectOption({ index: 1 });
    await addBar.locator('input[type="date"]').fill("2026-12-01");
    await addBar.locator('input[type="number"]').fill("1500");
    await addBar.getByRole("button", { name: "Salvar" }).click();

    const liquidar = page.getByRole("button", { name: /^Liquidar$/i }).first();
    await expect(liquidar).toBeVisible({ timeout: 15000 });
    await liquidar.click();
    await expect(page.getByText(/Pagamento liquidado/i)).toBeVisible({ timeout: 15000 });
  });

  test("financeiro global lista fila acionável (planejado vs liquidado)", async ({ page }) => {
    await page.goto("/financeiro", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Fila de contas a pagar/i })).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/Planejado não reduz saldo/i)).toBeVisible({ timeout: 15000 });
    // fila renderiza tabela de pagamentos ou estado vazio explícito
    const hasTable = await page.locator("table").first().isVisible().catch(() => false);
    const hasEmpty = await page.getByText(/Nenhum pagamento encontrado/i).isVisible().catch(() => false);
    expect(hasTable || hasEmpty).toBeTruthy();
  });

  test("Heroes Upload é fluxo guiado com stepper", async ({ page }) => {
    await page.goto("/cadastros/heroes", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Importar planilha Heroes/i })).toBeVisible({ timeout: 15000 });
    await expect(page.locator(".ux-steps")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Carregar planilha/i).first()).toBeVisible();
  });
});
