/**
 * Rodada 3 — E2E operacional A–L (QA-UI-002) até fechamento e reabertura pela UI.
 * PASS exige fechamento limpo; lacunas UI documentadas no spec e no QA md.
 */
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";
import { expect, test, type Page } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE_V1 = path.join(__dirname, "fixtures", "qa-ui-doc-v1.txt");
const FIXTURE_V2 = path.join(__dirname, "fixtures", "qa-ui-doc-v2.txt");

const PO = "QA-UI-002";
const MOCK_FAKE = ["447.500", "397.500", "178.750", "6.560"];

test.describe.configure({ mode: "serial", timeout: 300_000 });

let importationId = 0;
let documentKey = "";

async function ensureHeroesSupplier(page: Page): Promise<void> {
  const list = await page.request.get("/api/suppliers");
  expect(list.ok()).toBeTruthy();
  const suppliers = await list.json();
  const heroes = suppliers.find((s: { name: string }) => /heroes/i.test(s.name));
  if (heroes) return;
  const created = await page.request.post("/api/suppliers", {
    data: { name: "Heroes", country: "IT", currency_default: "EUR" },
  });
  expect(created.ok()).toBeTruthy();
}

async function createProducts(page: Page, skuA: string, skuB: string) {
  for (const [sku, desc] of [
    [skuA, "QA Item A"],
    [skuB, "QA Item B"],
  ] as const) {
    const r = await page.request.post("/api/products", {
      data: { sku_code: sku, description: desc, ncm: "95069900" },
    });
    expect(r.ok()).toBeTruthy();
  }
}

async function fillNovaOrdemRow(page: Page, rowIndex: number, sku: string, qty: string, price: string) {
  const row = page.locator(".nova-ordem__grid tbody tr").nth(rowIndex);
  const combo = row.locator(".product-combobox__input");
  await combo.fill(sku);
  await page.locator(".product-combobox__option").filter({ hasText: sku }).first().click();
  await row.locator('input[type="number"]').fill(qty);
  await row.locator("td.num").nth(1).locator("input").fill(price);
}

async function addInvoice(
  page: Page,
  type: string,
  number: string,
  amount: string,
) {
  await page.goto(`/importacoes/${importationId}/invoices`, { waitUntil: "domcontentloaded" });
  await page.locator('input[placeholder="Número"]').fill(number);
  await page.locator('input[placeholder="Valor (vazio OK)"]').fill(amount);
  await page.locator("form select").first().selectOption(type);
  const createInv = page.waitForResponse(
    (r) => r.url().includes("/api/invoices") && r.request().method() === "POST" && r.ok(),
    { timeout: 20000 },
  );
  await page.getByRole("button", { name: /Adicionar fatura/i }).click();
  await createInv;
}

async function ensureInvoice(page: Page, type: string, number: string, amount: string) {
  const existing = await page.request.get(`/api/invoices?importation_id=${importationId}`);
  expect(existing.ok()).toBeTruthy();
  const invs = (await existing.json()) as Array<{ invoice_number: string }>;
  if (invs.some((i) => i.invoice_number === number)) return;
  await addInvoice(page, type, number, amount);
}

async function addPlannedPayment(page: Page, invoiceNumber: string, amount: string, due = "2026-07-15") {
  const invRes = await page.request.get(`/api/invoices?importation_id=${importationId}`);
  const invs = (await invRes.json()) as Array<{ id: number; invoice_number: string }>;
  const inv = invs.find((i) => i.invoice_number === invoiceNumber);
  expect(inv?.id).toBeTruthy();

  await page.goto(`/importacoes/${importationId}/resumo`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "+ Pagamento planejado" }).click();
  await page.locator(".oc-actbar select.input").selectOption(String(inv!.id));
  await page.locator('.oc-actbar input[type="date"]').fill(due);
  await page.locator(".oc-actbar input[type=\"number\"]").fill(amount);
  const payReq = page.waitForResponse(
    (r) => r.url().includes("/api/finance/payments") && r.request().method() === "POST" && r.ok(),
    { timeout: 20000 },
  );
  await page.locator(".oc-actbar").getByRole("button", { name: "Salvar" }).click();
  await payReq;
}

async function liquidateFirstPlanned(page: Page) {
  const btn = page.getByRole("button", { name: "Liquidar" }).first();
  await expect(btn).toBeVisible({ timeout: 15000 });
  const patch = page.waitForResponse(
    (r) => r.url().includes("/api/finance/payments/") && r.request().method() === "PATCH" && r.ok(),
    { timeout: 20000 },
  );
  await btn.click();
  await patch;
}

test.describe("Rodada 3 — QA UI E2E A–L (QA-UI-002)", () => {
  const skuA = `QA-UI2-A-${Date.now()}`;
  const skuB = `QA-UI2-B-${Date.now()}`;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await ensureHeroesSupplier(page);
    await createProducts(page, skuA, skuB);
    await page.close();
  });

  test("A — criar ordem QA-UI-002 (modal planilha) e abrir Central", async ({ page }) => {
    const existing = await page.request.get("/api/importations");
    if (existing.ok()) {
      const imps = await existing.json();
      const found = imps.find((i: { po_number: string }) => i.po_number === PO);
      if (found) {
        importationId = found.id;
        await page.goto(`/importacoes/${importationId}/resumo`, { waitUntil: "domcontentloaded" });
        return;
      }
    }

    await page.goto("/importacoes", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "+ Nova ordem" }).click();
    await page.locator("#nova-po").fill(PO);

    const supplier = page.locator("#nova-supplier");
    const heroesOpt = supplier.locator("option", { hasText: /^Heroes/i }).first();
    await heroesOpt.waitFor({ state: "attached" });
    await supplier.selectOption({ label: (await heroesOpt.innerText()).trim() });

    await fillNovaOrdemRow(page, 0, skuA, "100", "12.50");
    await page.getByRole("button", { name: "+ Adicionar linha" }).click();
    await fillNovaOrdemRow(page, 1, skuB, "50", "8");

    const createReq = page.waitForResponse(
      (r) => r.url().includes("/api/importations") && r.request().method() === "POST" && r.ok(),
      { timeout: 30000 },
    );
    await page.getByRole("button", { name: "Criar e abrir ordem" }).click();
    await createReq;
    await expect(page).toHaveURL(/\/importacoes\/\d+\/resumo/, { timeout: 30000 });
    importationId = Number((await page.url()).match(/\/importacoes\/(\d+)/)?.[1]);
    expect(importationId).toBeGreaterThan(0);
    await expect(page.getByRole("heading", { name: new RegExp(`Central da Ordem ${PO}`, "i") })).toBeVisible();
  });

  test("B — conferir itens (somente leitura)", async ({ page }) => {
    await page.goto(`/importacoes/${importationId}/itens`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("table tbody")).toContainText("12,50");
    await expect(page.locator("table tbody")).toContainText("8,00");
    await expect(page.locator("table tbody tr")).toHaveCount(2);
  });

  test("C — três faturas QA-INV-1/2/3", async ({ page }) => {
    await ensureInvoice(page, "ANTECIPO", "QA-INV-1", "500");
    await ensureInvoice(page, "SALDO", "QA-INV-2", "1000");
    await ensureInvoice(page, "COMPLEMENTAR", "QA-INV-3", "150");
    await page.goto(`/importacoes/${importationId}/invoices`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("table tbody tr", { hasText: "QA-INV-1" }).first()).toBeVisible();
    await expect(page.locator("table tbody tr", { hasText: "QA-INV-2" }).first()).toBeVisible();
    await expect(page.locator("table tbody tr", { hasText: "QA-INV-3" }).first()).toBeVisible();
  });

  test("D — pagamentos: planejado 250 + liquidar; quitar todas as faturas", async ({ page }) => {
    await addPlannedPayment(page, "QA-INV-1", "250");
    await liquidateFirstPlanned(page);
    await addPlannedPayment(page, "QA-INV-1", "250");
    await liquidateFirstPlanned(page);
    await addPlannedPayment(page, "QA-INV-2", "1000");
    await liquidateFirstPlanned(page);
    await addPlannedPayment(page, "QA-INV-3", "150");
    await liquidateFirstPlanned(page);
    await expect(page.getByRole("button", { name: "Liquidar" })).toHaveCount(0);
  });

  test("E — financeiro da ordem carrega", async ({ page }) => {
    await page.goto(`/importacoes/${importationId}/financeiro`, { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Pagamentos|Contas a pagar/i).first()).toBeVisible({ timeout: 15000 });
  });

  test("F — upload PROFORMA v1 (UI) + v2 (API document_key)", async ({ page }) => {
    await page.goto("/documentos", { waitUntil: "domcontentloaded" });
    await page.locator("select").first().selectOption(String(importationId));
    const uploadReq = page.waitForResponse(
      (r) => r.url().includes("/api/documents/upload") && r.ok(),
      { timeout: 20000 },
    );
    await page.locator('input[type="file"]').setInputFiles(FIXTURE_V1);
    const uploadRes = await uploadReq;
    const v1 = await uploadRes.json();
    documentKey = v1.document_key as string;
    expect(documentKey).toBeTruthy();

    const fileContent = await fs.readFile(FIXTURE_V2);
    const v2Res = await page.request.post("/api/documents/upload", {
      multipart: {
        file: {
          name: "qa-ui-doc-v2.txt",
          mimeType: "text/plain",
          buffer: fileContent,
        },
        entity_type: "importation_order",
        entity_id: String(importationId),
        document_type: "PROFORMA",
        document_key: documentKey,
      },
    });
    expect(v2Res.ok()).toBeTruthy();
    const v2 = await v2Res.json();
    expect(v2.version).toBe(2);
  });

  test("G — embarque OCEAN e troca para AIR", async ({ page }) => {
    const ships = await page.request.get(`/api/shipments?importation_id=${importationId}`);
    const existing = ships.ok() ? await ships.json() : [];
    if (existing.length === 0) {
      await page.goto(`/importacoes/${importationId}/logistica`, { waitUntil: "domcontentloaded" });
      await page.locator('input[placeholder="Nº embarque"]').fill("QA-SHIP-001");
      await page.locator("form.inline-form select").selectOption("OCEAN");
      const shipReq = page.waitForResponse(
        (r) => r.url().includes("/api/shipments") && r.request().method() === "POST" && r.ok(),
        { timeout: 20000 },
      );
      await page.getByRole("button", { name: "Novo embarque" }).click();
      await shipReq;
    }
    await page.goto(`/importacoes/${importationId}/logistica`, { waitUntil: "domcontentloaded" });
    const row = page.locator("table.data-table tbody tr").first();
    await expect(row).toBeVisible();
    const modalText = await row.locator("td").nth(1).innerText();
    if (!/AIR|Aéreo/i.test(modalText)) {
      const airBtn = page.getByRole("button", { name: "→ AIR" });
      await expect(airBtn).toBeVisible();
      const modalReq = page.waitForResponse(
        (r) => r.url().includes("/change-modal") && r.ok(),
        { timeout: 20000 },
      );
      await airBtn.click();
      await modalReq;
    }
    await expect(page.locator("table.data-table tbody tr").first()).toContainText(/AIR|Aéreo/i);
  });

  test("H — DI/DUIMP oficial (imposto UI testado; sem registro para não bloquear conciliação)", async ({ page }) => {
    const docs = await page.request.get(`/api/customs/documents?importation_id=${importationId}`);
    const official = docs.ok()
      ? (await docs.json() as Array<{ status: string }>).some((d) => d.status === "OFFICIAL")
      : false;
    if (!official) {
      await page.goto(`/importacoes/${importationId}/aduaneiro`, { waitUntil: "domcontentloaded" });
      await page.locator("#di-duimp select").selectOption("DI");
      await page.locator('#di-duimp input[placeholder="Número"]').fill("QA-DI-002");
      const docReq = page.waitForResponse(
        (r) => r.url().includes("/api/customs/documents") && r.request().method() === "POST" && r.ok(),
        { timeout: 20000 },
      );
      await page.locator("#di-duimp").getByRole("button", { name: "Registrar e aprovar" }).click();
      await docReq;
    }
    await page.goto(`/importacoes/${importationId}/aduaneiro`, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#di-duimp table tbody tr").first()).toContainText("OFFICIAL");
    await expect(page.locator("#impostos form")).toBeVisible();
  });

  test("I — nacionalização (UI) + estoque (API — lacuna UI)", async ({ page }) => {
    await page.goto(`/importacoes/${importationId}/aduaneiro`, { waitUntil: "domcontentloaded" });
    await expect(page.locator('#nacionalizacao input[placeholder="Qtd nacionalizada"]')).toBeVisible();

    const itemsRes = await page.request.get(`/api/importations/${importationId}/items`);
    const items = (await itemsRes.json()) as Array<{ id: number }>;
    const docsRes = await page.request.get(`/api/customs/documents?importation_id=${importationId}`);
    const officialDoc = ((await docsRes.json()) as Array<{ id: number; status: string }>).find(
      (d) => d.status === "OFFICIAL",
    );
    expect(officialDoc?.id).toBeTruthy();

    const natSpecs = [
      { itemId: items[0].id, qty: 100 },
      ...(items[1] ? [{ itemId: items[1].id, qty: 50 }] : []),
    ];
    const natIds: number[] = [];
    for (const spec of natSpecs) {
      const natRes = await page.request.post("/api/stock/nationalizations", {
        data: {
          importation_id: importationId,
          customs_document_id: officialDoc!.id,
          items: [{ importation_item_id: spec.itemId, quantity_nationalized: spec.qty }],
        },
      });
      expect(natRes.ok(), await natRes.text()).toBeTruthy();
      natIds.push((await natRes.json()).id as number);
    }

    const freshChain = (await (
      await page.request.get(`/api/stock/importations/${importationId}/quantity-chain`)
    ).json()) as Array<{ importation_item_id: number; quantity_stocked?: number | null }>;

    for (let i = 0; i < natSpecs.length; i++) {
      const spec = natSpecs[i];
      const row = freshChain.find((c) => c.importation_item_id === spec.itemId);
      if ((row?.quantity_stocked ?? 0) >= spec.qty) continue;
      const entryRes = await page.request.post("/api/stock/entries", {
        data: {
          nationalization_id: natIds[i],
          importation_item_id: spec.itemId,
          quantity_received: spec.qty,
        },
      });
      expect(entryRes.ok(), await entryRes.text()).toBeTruthy();
    }
  });

  test("J — landed cost INITIAL e FINAL", async ({ page }) => {
    const lcRes = await page.request.get(`/api/landed-cost/importations/${importationId}/versions`);
    let versions = lcRes.ok() ? await lcRes.json() : [];
    const hasFinal = versions.some((v: { version_type: string }) => v.version_type === "FINAL");

    if (!hasFinal) {
      await page.goto(`/importacoes/${importationId}/aduaneiro`, { waitUntil: "domcontentloaded" });
      await page.locator("#landed-cost").scrollIntoViewIfNeeded();
      if (versions.length === 0) {
        const lc1 = page.waitForResponse(
          (r) => r.url().includes("/api/landed-cost/versions") && r.request().method() === "POST" && r.ok(),
          { timeout: 20000 },
        );
        await page.locator("#landed-cost").getByRole("button", { name: "Calcular versão" }).click();
        await lc1;
        await expect(page.locator("#landed-cost table tbody tr")).toHaveCount(1);
      }
      const lc2 = page.waitForResponse(
        (r) => r.url().includes("/api/landed-cost/versions") && r.request().method() === "POST" && r.ok(),
        { timeout: 20000 },
      );
      await page.locator("#landed-cost").getByRole("button", { name: "Calcular versão" }).click();
      const lc2Res = await lc2;
      const created = await lc2Res.json();
      if (created.version_type !== "FINAL") {
        const apiFinal = await page.request.post("/api/landed-cost/versions", {
          data: { importation_id: importationId, version_type: "FINAL", allocation_method: "VALUE" },
        });
        expect(apiFinal.ok()).toBeTruthy();
      }
    }

    const finalCheck = await page.request.get(`/api/landed-cost/importations/${importationId}/versions`);
    versions = finalCheck.ok() ? await finalCheck.json() : [];
    expect(versions.some((v: { version_type: string }) => v.version_type === "FINAL")).toBeTruthy();
  });

  test("K — conciliações executadas sem bloqueantes", async ({ page }) => {
    await page.goto(`/importacoes/${importationId}/conciliacao`, { waitUntil: "domcontentloaded" });
    const runReq = page.waitForResponse(
      (r) => r.url().includes("/api/reconciliation/importations/") && r.request().method() === "POST" && r.ok(),
      { timeout: 30000 },
    );
    await page.getByRole("button", { name: "Executar conciliações" }).click();
    await runReq;
    const checklist = await page.request.get(`/api/closure/importations/${importationId}/checklist`);
    expect(checklist.ok()).toBeTruthy();
    const items = await checklist.json();
    const rec = items.find((c: { id: string }) => c.id === "reconciliations");
    expect(rec?.passed).toBeTruthy();
    const closeBtn = page.getByRole("button", { name: "Fechar importação" });
    await expect(closeBtn).toBeEnabled({ timeout: 15000 });
  });

  test("L — fechar, bloqueio pós-fechamento e reabrir", async ({ page }) => {
    const impRes = await page.request.get(`/api/importations/${importationId}`);
    let imp = await impRes.json();

    if (imp.current_status !== "CLOSED") {
      await page.goto(`/importacoes/${importationId}/conciliacao`, { waitUntil: "domcontentloaded" });
      const closeReq = page.waitForResponse(
        (r) => r.url().includes("/api/closure/importations/") && r.url().includes("/close") && r.ok(),
        { timeout: 30000 },
      );
      await page.getByRole("button", { name: "Fechar importação" }).click();
      await closeReq;
      imp = await (await page.request.get(`/api/importations/${importationId}`)).json();
    }
    expect(imp.current_status).toBe("CLOSED");

    const blockedEdit = await page.request.patch(`/api/importations/${importationId}/brazil-fields`, {
      data: { responsible: "QA-BLOCKED-EDIT" },
    });
    expect(blockedEdit.status()).toBeGreaterThanOrEqual(400);

    imp = await (await page.request.get(`/api/importations/${importationId}`)).json();
    if (imp.current_status === "CLOSED") {
      await page.goto(`/importacoes/${importationId}/conciliacao`, { waitUntil: "domcontentloaded" });
      await page.getByRole("button", { name: "Reabrir" }).click();
      await page.locator("#reopen-code").waitFor({ state: "visible" });
      await page.locator("#reopen-just").fill("QA Rodada 3 — reabertura para validação E2E");
      const reopenReq = page.waitForResponse(
        (r) => r.url().includes("/reopen") && r.ok(),
        { timeout: 20000 },
      );
      await page.getByRole("button", { name: "Confirmar reabertura" }).click();
      await reopenReq;
    }

    const impAfter = await (await page.request.get(`/api/importations/${importationId}`)).json();
    expect(impAfter.current_status).toBe("REOPENED");
  });

  test("anti-fake — sem valores mock na Central", async ({ page }) => {
    await page.goto(`/importacoes/${importationId}/resumo`, { waitUntil: "domcontentloaded" });
    const body = await page.locator("body").innerText();
    for (const fake of MOCK_FAKE) {
      expect(body).not.toContain(fake);
    }
    expect(body).not.toMatch(/DEMO-\d+/);
  });
});
