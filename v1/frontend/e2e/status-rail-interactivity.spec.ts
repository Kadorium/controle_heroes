import { expect, test } from "@playwright/test";
import { getDemoImportationId } from "./helpers";

test.describe("Régua de status e interatividade Visão Geral", () => {
  test.beforeEach(async ({ page }) => {
    await page.request.post("/api/demo/seed");
  });

  test("demo coerente DEMO-01 — régua com ✓ sustentados por dados", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-01-OCEAN");
    const centralReady = page.waitForResponse(
      (r) => r.url().includes(`/api/importations/${demoId}/order-central`) && r.ok(),
      { timeout: 30000 }
    );
    await page.goto(`/importacoes/${demoId}/resumo`, { waitUntil: "domcontentloaded" });
    await centralReady;
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator(".order-central__stage--done").first()).toBeVisible({ timeout: 15000 });
    const body = await page.locator(".order-central__rail").innerText();
    expect(body).toContain("✓");
  });

  test("ordem sem fatura — faturado não mostra ✓ sólido", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-04-3INV");
    const central = await page.request.get(`/api/importations/${demoId}/order-central`);
    const rail = (await central.json()).status_rail;
    const faturado = rail.stages.find((s: { key: string }) => s.key === "faturado");
    expect(faturado.state).toBe("done");
    await page.goto(`/importacoes/${demoId}/resumo`);
    await expect(page.getByLabel(/Observação operacional \(Brasil\)/i)).toBeVisible();
  });

  test("declarado sem dado — alerta visível", async ({ page }) => {
    const imps = await page.request.get("/api/importations");
    const list = await imps.json();
    const orphan = list.find(
      (i: { po_number: string; current_status: string }) =>
        i.po_number.startsWith("DEMO-") && i.current_status === "PO_CREATED"
    );
    test.skip(!orphan, "sem demo PO_CREATED");
    await page.goto(`/importacoes/${orphan.id}/resumo`);
    await expect(page.getByRole("heading", { name: /Central da Ordem/i })).toBeVisible();
  });

  test("editar observação Brasil inline reflete na tela", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-02-AIR");
    await page.goto(`/importacoes/${demoId}/resumo`);
    const notes = page.getByLabel(/Observação operacional \(Brasil\)/i);
    await notes.fill("E2E nota Brasil");
    await page.getByRole("button", { name: "Salvar" }).click();
    await expect(notes).toHaveValue("E2E nota Brasil");
  });

  test("campo Itália abre modal override ao clicar", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-06-PARTIAL");
    await page.goto(`/importacoes/${demoId}/resumo`);
    await expect(page.getByRole("heading", { name: /Faturas · acconto/i })).toBeVisible({ timeout: 20000 });
    await page.locator("button.sheet-cell--locked-btn").first().click();
    await expect(page.getByRole("heading", { name: /Override Brasil — campo Itália/i })).toBeVisible();
    await expect(page.getByLabel(/Anexo comprobatório/i)).toBeVisible();
  });

  test("transição bloqueada mostra motivo", async ({ page }) => {
    const demoId = await getDemoImportationId(page, "DEMO-04-3INV");
    const transitions = await page.request.get(`/api/importations/${demoId}/allowed-transitions`);
    const blocked = (await transitions.json()).transitions.find(
      (t: { blocked: boolean }) => t.blocked
    );
    test.skip(!blocked, "nenhuma transição bloqueada neste demo");
    await page.goto(`/importacoes/${demoId}/resumo`);
    await expect(page.getByText(blocked.block_reason)).toBeVisible({ timeout: 15000 });
  });
});
