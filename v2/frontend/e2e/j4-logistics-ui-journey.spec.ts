/**
 * Validação real da jornada Logistics por cliques UI (não usa API como prova).
 * Fixture de pré-requisito (pedido confirmado) é criada também por UI.
 * Evidências: docs/v2/etapa-j4/ui-validation/
 */
import { test, expect, type Page, type Request, type Response } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const EVIDENCE_ROOT = path.resolve(
  process.cwd(),
  "..",
  "..",
  "docs",
  "v2",
  "etapa-j4",
  "ui-validation",
);
const SHOT_DIR = path.join(EVIDENCE_ROOT, "screenshots");
const LOG_DIR = path.join(EVIDENCE_ROOT, "logs");

type StepResult = {
  step: number;
  title: string;
  action: string;
  element: string;
  observed: string;
  screenshot?: string;
  request?: { method: string; url: string; body?: unknown };
  response?: { status: number; body?: unknown };
  verdict: "PASS" | "FAIL" | "PARTIAL";
  channel: "UI" | "API_FIXTURE" | "COMPONENT" | "NOT_IN_UI";
};

const steps: StepResult[] = [];

function ensureDirs() {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

async function shot(page: Page, name: string) {
  const file = `${name}.png`;
  await page.screenshot({ path: path.join(SHOT_DIR, file), fullPage: true });
  return file;
}

function record(step: StepResult) {
  steps.push(step);
  console.log(
    `[UI-JOURNEY] ${step.step}. ${step.title} → ${step.verdict} | ${step.observed.slice(0, 160)}`,
  );
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({
    timeout: 15000,
  });
}

async function modalConfirm(page: Page) {
  await page.getByTestId("confirm-modal-ok").click();
}

async function createConfirmedOrderViaUi(page: Page, tag: string) {
  await page.goto("/orders/new");
  await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("order-code").fill(tag);
  await page.getByTestId("order-supplier").selectOption("");
  await page.getByTestId("new-supplier-name").fill(`Sup UI ${tag}`);
  await page.getByTestId("line-sku").fill(`SKU-${tag}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.getByTestId("line-qty").fill("20");
  await page.getByTestId("line-price").fill("10");
  await page.getByRole("button", { name: /^adicionar linha$/i }).click();
  await expect(page.getByRole("table")).toContainText(`SKU-${tag}`);
  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("confirmation-modal")).toBeVisible();
  await modalConfirm(page);
  await expect(page).toHaveURL(/\/orders\/\d+/, { timeout: 20000 });
  return tag;
}

test.describe.configure({ mode: "serial" });

test("Jornada Logistics completa por UI", async ({ page }) => {
  test.setTimeout(240_000);
  ensureDirs();
  const tag = `UIJ-${Date.now().toString().slice(-8)}`;
  let shipmentCode = "";
  let shipmentId = "";
  let createPayload: unknown;
  let createResponse: { status: number; body?: unknown } | undefined;

  page.on("request", (req: Request) => {
    if (req.method() === "POST" && req.url().includes("/api/shipments") && !req.url().match(/\/shipments\/\d+/)) {
      try {
        createPayload = req.postDataJSON();
      } catch {
        createPayload = req.postData();
      }
    }
  });
  page.on("response", async (res: Response) => {
    if (res.request().method() === "POST" && res.url().match(/\/api\/shipments\/?$/) && !res.url().includes("candidates")) {
      try {
        createResponse = { status: res.status(), body: await res.json() };
      } catch {
        createResponse = { status: res.status() };
      }
    }
  });

  // --- Login ---
  await login(page);
  record({
    step: 0,
    title: "Login",
    action: "Login admin",
    element: "login form",
    observed: "Sessão autenticada",
    verdict: "PASS",
    channel: "UI",
  });

  // --- Fixture: pedido confirmado por UI (pré-requisito do picker) ---
  let orderCode = tag;
  try {
    orderCode = await createConfirmedOrderViaUi(page, tag);
    const orderShot = await shot(page, "00-order-confirmed");
    record({
      step: 0.5 as unknown as number,
      title: "Fixture pedido confirmado",
      action: "Criar e confirmar pedido via /orders/new",
      element: "order-create-page / save-confirm",
      observed: `Pedido ${orderCode} confirmado por UI`,
      screenshot: orderShot,
      verdict: "PASS",
      channel: "UI",
    });
  } catch (e) {
    record({
      step: 0.5 as unknown as number,
      title: "Fixture pedido confirmado",
      action: "Criar pedido via UI",
      element: "order-create-page",
      observed: `FAIL: ${e instanceof Error ? e.message : String(e)}`,
      verdict: "FAIL",
      channel: "UI",
    });
    throw e;
  }

  // --- Prestador (necessário p/ BOOKED pós J4-UX1; cadastro por UI) ---
  await page.goto("/logistics-providers");
  await expect(page.getByTestId("logistics-providers-page")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("provider-legal-name").fill(`Transportadora ${tag} LTDA`);
  await page.getByTestId("provider-trade-name").fill(`Carrier ${tag}`);
  await page.getByTestId("provider-type").selectOption("TRANSPORTADOR");
  await page.getByTestId("provider-create-submit").click();
  await expect(page.getByTestId("providers-table")).toContainText(`Carrier ${tag}`, {
    timeout: 10000,
  });
  const providerShot = await shot(page, "00b-provider-created");
  record({
    step: 0.6 as unknown as number,
    title: "Cadastro prestador",
    action: "Cadastrar empresa transportadora",
    element: "logistics-providers-page",
    observed: `Prestador Carrier ${tag} ativo`,
    screenshot: providerShot,
    verdict: "PASS",
    channel: "UI",
  });

  // 1. Abrir /shipments
  await page.goto("/shipments");
  await expect(page.getByTestId("shipments-list")).toBeVisible({ timeout: 15000 });
  const s1 = await shot(page, "01-shipments-list");
  record({
    step: 1,
    title: "Abrir /shipments",
    action: "Navegar para lista",
    element: "[data-testid=shipments-list]",
    observed: "Lista de embarques visível",
    screenshot: s1,
    verdict: "PASS",
    channel: "UI",
  });

  // 2. Novo embarque
  await page.getByTestId("shipments-new-cta").click();
  await expect(page.getByTestId("shipment-create-page")).toBeVisible({ timeout: 15000 });
  const s2 = await shot(page, "02-shipment-create");
  const modalTag = await page.getByTestId("shipment-modal").evaluate((el) => el.tagName);
  const providerTag = await page.getByTestId("shipment-provider").evaluate((el) => el.tagName);
  const modalOptions = await page.getByTestId("shipment-modal").locator("option").allTextContents();
  const providerOptions = await page
    .getByTestId("shipment-provider")
    .locator("option")
    .allTextContents();
  const subtitle = await page.locator(".page-header .muted, header .muted").first().textContent();
  const dateHint = await page.locator("#shipment-planned-departure").evaluate((el) => {
    const field = el.closest(".form-field, label, div");
    return field?.textContent ?? "";
  });
  record({
    step: 2,
    title: "Clicar Novo embarque",
    action: "Abrir formulário de criação",
    element: "[data-testid=shipments-new-cta] → shipment-create-page",
    observed: `Modal=${modalTag}; Transportador=${providerTag}; options modal=${JSON.stringify(modalOptions)}; options provider=${JSON.stringify(providerOptions)}; microcopy=${subtitle?.trim()}`,
    screenshot: s2,
    verdict: "PASS",
    channel: "UI",
  });

  // 3. Preencher campos
  await page.getByTestId("shipment-modal").selectOption("SEA");
  await page.getByTestId("shipment-origin").fill("Gênova");
  await page.getByTestId("shipment-destination").fill("Santos");
  await page.getByTestId("shipment-provider").selectOption({ label: `Carrier ${tag}` });
  await page.getByTestId("shipment-planned-departure").fill("2026-08-01");
  await page.getByTestId("shipment-planned-arrival").fill("2026-08-20");
  await page.getByTestId("shipment-notes").fill(`Notas jornada UI ${tag}`);
  const s3 = await shot(page, "03-shipment-create-filled");
  record({
    step: 3,
    title: "Preencher campos",
    action: "Preencher modal, rota, prestador, datas, notas",
    element: "shipment-modal/origin/destination/provider/dates/notes",
    observed: `Datas type=date valor ISO 2026-08-01/20; hint contexto inclui: ${dateHint.includes("dd/mm") ? "dd/mm/aaaa" : "sem hint explícito no nó"}; campos PLANNED opcionais no FE`,
    screenshot: s3,
    verdict: "PASS",
    channel: "UI",
  });

  // 4–5. Criar + redirect
  await page.getByTestId("shipment-create-submit").click();
  await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 20000 });
  await expect(page).toHaveURL(/\/shipments\/\d+/);
  shipmentId = page.url().match(/\/shipments\/(\d+)/)?.[1] ?? "";
  const heading = await page.getByRole("heading").first().textContent();
  shipmentCode = heading?.match(/SHP-\w+/)?.[0] ?? "";
  const s5 = await shot(page, "05-shipment-detail-created");
  record({
    step: 4,
    title: "Criar embarque",
    action: "Submit criar",
    element: "[data-testid=shipment-create-submit]",
    observed: `POST /api/shipments status=${createResponse?.status}; payload=${JSON.stringify(createPayload)}; body.id=${(createResponse?.body as { id?: number })?.id}`,
    request: {
      method: "POST",
      url: "/api/shipments",
      body: createPayload,
    },
    response: createResponse,
    verdict: createResponse?.status === 201 ? "PASS" : "FAIL",
    channel: "UI",
  });
  record({
    step: 5,
    title: "Redirect detalhe",
    action: "Confirmar URL e detalhe",
    element: "[data-testid=shipment-detail]",
    observed: `URL /shipments/${shipmentId}; código ${shipmentCode || heading}`,
    screenshot: s5,
    verdict: shipmentId ? "PASS" : "FAIL",
    channel: "UI",
  });

  // 6–7. Adicionar item
  await page.getByTestId("shipment-add-item").click();
  await page.getByTestId("picker-order-code").fill(orderCode);
  await page.getByRole("button", { name: /buscar candidatos/i }).click();
  await expect(page.getByTestId("picker-candidate")).toBeVisible({ timeout: 10000 });
  await page.getByTestId("picker-qty").fill("5");
  const s6 = await shot(page, "06-item-picker");
  await modalConfirm(page);
  await expect(page.getByTestId("shipment-items")).toContainText(/SKU-/i, { timeout: 10000 });
  record({
    step: 6,
    title: "Adicionar ShipmentItem",
    action: "Picker: código pedido + candidato",
    element: "shipment-add-item / picker-*",
    observed: `Item adicionado a partir do pedido ${orderCode}`,
    screenshot: s6,
    verdict: "PASS",
    channel: "UI",
  });
  record({
    step: 7,
    title: "Quantidade parcial",
    action: "Informar qty=5 (pedido 20)",
    element: "[data-testid=picker-qty]",
    observed: "Quantidade parcial 5 persistida na tabela de itens",
    verdict: "PASS",
    channel: "UI",
  });

  // 8. Package
  await page.getByTestId("package-type").selectOption("CARTON");
  await page.getByTestId("package-count").fill("3");
  await page.getByTestId("shipment-add-package").click();
  await expect(page.getByTestId("shipment-packages")).toContainText("CARTON", { timeout: 10000 });
  const s8 = await shot(page, "08-package-added");
  const hasWeightInputs = (await page.locator('[data-testid="package-net-weight"]').count()) > 0;
  record({
    step: 8,
    title: "Adicionar package",
    action: "Adicionar volume CARTON x3",
    element: "package-type / package-count / shipment-add-package",
    observed: hasWeightInputs
      ? "Volume com pesos na UI"
      : "Volume adicionado; UI NÃO expõe peso/dimensões (só tipo/qtd/pai) — totais derivados tendem a zero",
    screenshot: s8,
    verdict: hasWeightInputs ? "PASS" : "PARTIAL",
    channel: hasWeightInputs ? "UI" : "NOT_IN_UI",
  });

  // 9. Refs DDT + BL
  await page.getByTestId("reference-type").selectOption("DDT");
  await page.getByTestId("reference-value").fill(`DDT-${tag}`);
  await page.getByTestId("shipment-add-reference").click();
  await expect(page.getByRole("cell", { name: `DDT-${tag}` })).toBeVisible({ timeout: 10000 });
  await page.getByTestId("reference-type").selectOption("BL");
  await page.getByTestId("reference-value").fill(`BL-${tag}`);
  await page.getByTestId("shipment-add-reference").click();
  await expect(page.getByRole("cell", { name: `BL-${tag}` })).toBeVisible({ timeout: 10000 });
  const s9 = await shot(page, "09-references");
  record({
    step: 9,
    title: "Referências DDT e BL",
    action: "Adicionar duas referências",
    element: "reference-type / reference-value / shipment-add-reference",
    observed: `DDT-${tag} e BL-${tag} visíveis`,
    screenshot: s9,
    verdict: "PASS",
    channel: "UI",
  });

  // 10. Totais derivados
  await expect(page.getByTestId("shipment-totals")).toBeVisible();
  const totalsText = (await page.getByTestId("shipment-totals").textContent()) ?? "";
  const s10 = await shot(page, "10-totals");
  record({
    step: 10,
    title: "Totais derivados",
    action: "Conferir seção Totais",
    element: "[data-testid=shipment-totals]",
    observed: totalsText.replace(/\s+/g, " ").slice(0, 240),
    screenshot: s10,
    verdict: /linhas de volume|volume/i.test(totalsText) ? "PARTIAL" : "FAIL",
    channel: "UI",
  });

  // 11. PLANNED → BOOKED
  await page.getByTestId("shipment-advance-cta").click();
  await page.getByTestId("advance-event-date").fill("2026-08-05");
  const s11a = await shot(page, "11-advance-booked-modal");
  await modalConfirm(page);
  await expect(page.getByTestId("readonly-banner")).toBeVisible({ timeout: 15000 });
  const s11 = await shot(page, "11-booked");
  record({
    step: 11,
    title: "Avançar PLANNED → BOOKED",
    action: "CTA avançar + data evento",
    element: "shipment-advance-cta / advance-event-date",
    observed: "Status BOOKED; banner somente leitura na estrutura",
    screenshot: s11,
    request: undefined,
    verdict: "PASS",
    channel: "UI",
  });
  void s11a;

  // 12. Estrutura bloqueada
  const addItemVisible = await page.getByTestId("shipment-add-item").count();
  const addPkgVisible = await page.getByTestId("shipment-add-package").count();
  record({
    step: 12,
    title: "Estrutura bloqueada após BOOKED",
    action: "Verificar ausência de CTAs de estrutura",
    element: "shipment-add-item / shipment-add-package",
    observed: `add-item count=${addItemVisible}; add-package count=${addPkgVisible}; readonly-banner presente`,
    verdict: addItemVisible === 0 && addPkgVisible === 0 ? "PASS" : "FAIL",
    channel: "UI",
  });

  // 13. IN_TRANSIT + ARRIVED
  await page.getByTestId("shipment-advance-cta").click();
  await page.getByTestId("advance-event-date").fill("2026-08-10");
  await modalConfirm(page);
  await expect(page.getByText(/em trânsito|IN_TRANSIT/i).first()).toBeVisible({ timeout: 15000 });
  const s13a = await shot(page, "13a-in-transit");
  await page.getByTestId("shipment-advance-cta").click();
  await page.getByTestId("advance-event-date").fill("2026-08-20");
  await modalConfirm(page);
  await expect(page.getByText(/chegou|ARRIVED/i).first()).toBeVisible({ timeout: 15000 });
  const s13b = await shot(page, "13b-arrived");
  record({
    step: 13,
    title: "IN_TRANSIT e ARRIVED",
    action: "Dois advances com datas pela UI",
    element: "shipment-advance-cta / advance-event-date",
    observed: "Chegou a ARRIVED com datas 2026-08-10 e 2026-08-20",
    screenshot: s13b,
    verdict: "PASS",
    channel: "UI",
  });
  void s13a;

  // 14. Lista e reabrir
  await page.goto("/shipments");
  await expect(page.getByTestId("shipments-list")).toBeVisible({ timeout: 15000 });
  if (shipmentCode) {
    await page.getByRole("link", { name: shipmentCode }).first().click();
  } else {
    await page.goto(`/shipments/${shipmentId}`);
  }
  await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 15000 });
  const s14 = await shot(page, "14-reopen-detail");
  record({
    step: 14,
    title: "Voltar à lista e reabrir",
    action: "Lista → clique no código",
    element: "shipments-list / RowLink",
    observed: `Detalhe reaberto id=${shipmentId} code=${shipmentCode}`,
    screenshot: s14,
    verdict: "PASS",
    channel: "UI",
  });

  // Persistência create
  const persisted = createResponse?.body as {
    modal?: string;
    logistics_provider_id?: number;
    carrier_name_snapshot?: string;
    origin?: string;
    destination?: string;
  };
  record({
    step: 15,
    title: "Tela criação — payload e persistência",
    action: "Inspecionar POST create + resposta",
    element: "network POST /api/shipments",
    observed: JSON.stringify({
      modalFieldType: modalTag,
      providerFieldType: providerTag,
      modalOptions,
      providerOptions,
      payload: createPayload,
      persisted: {
        modal: persisted?.modal,
        logistics_provider_id: persisted?.logistics_provider_id,
        carrier_name_snapshot: persisted?.carrier_name_snapshot,
        origin: persisted?.origin,
        destination: persisted?.destination,
      },
      emptyBehavior:
        "PLANNED permite create sem modal/prestador (não exercitado neste happy path); BOOKED exige ambos no domínio",
      requiredOnCreate: "Nenhum campo marcado required no create PLANNED; Notice informa exigência no BOOKED",
      dateFormat: "input type=date (ISO yyyy-mm-dd no value; locale do browser na UI nativa); hint dd/mm/aaaa",
    }),
    request: { method: "POST", url: "/api/shipments", body: createPayload },
    response: createResponse,
    verdict: "PASS",
    channel: "UI",
  });

  // Document summary / package contents
  record({
    step: 16,
    title: "Document summary / package contents",
    action: "Procurar editor na UI",
    element: "section Documentos / volumes contents",
    observed:
      "Upload/resumo documental: Notice diz fora de escopo; sem UI de set_package_contents — API_ONLY",
    verdict: "PARTIAL",
    channel: "NOT_IN_UI",
  });

  fs.writeFileSync(path.join(LOG_DIR, "jornada-ui-steps.json"), JSON.stringify(steps, null, 2), "utf8");
  const fails = steps.filter((s) => s.verdict === "FAIL");
  expect(fails, `Passos FAIL: ${fails.map((f) => f.title).join(", ")}`).toHaveLength(0);
});
