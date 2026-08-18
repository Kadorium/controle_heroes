/**
 * E8-FINAL-VERIFY V4 — família 202 PDFs reais → nacionalização → estoque na UI.
 * Uploads via intake-file-input.setInputFiles (input real). Sem POST upload/adapter/commit.
 * Inventory mutations só depois da nacionalização, via ReceiptPanel.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../../../..");
const frontendRoot = path.resolve(repoRoot, "v2/frontend");
const require = createRequire(path.join(frontendRoot, "package.json"));
const { chromium } = require("playwright");

const shotDir = path.resolve(__dirname, "../screenshots/final-doc202");
const logPath = path.join(__dirname, "e8-final-doc202-log.json");
const BASE = process.env.E8_WALK_BASE || "http://localhost:5174";
const CORPUS = path.join(repoRoot, "v2/tests/fixtures/ingestion/corpus_202");

const LINES = [
  { sku: "8057628950936", qty: "150", price: "6.50" },
  { sku: "8057628953104", qty: "150", price: "6.50" },
  { sku: "8057628954194", qty: "200", price: "6.50" },
  { sku: "8057628953814", qty: "200", price: "6.50" },
  { sku: "8057628955191", qty: "300", price: "43.03" },
  { sku: "8057628955207", qty: "300", price: "35.93" },
  { sku: "8057628955214", qty: "300", price: "6.50" },
];

fs.mkdirSync(shotDir, { recursive: true });

const log = [];
const mutating = [];
function note(step, data) {
  log.push({ step, ...data, at: new Date().toISOString() });
  console.log(JSON.stringify({ step, ...data }));
}

async function dump(page, name) {
  const p = path.join(shotDir, `FAIL-${name}.png`);
  await page.screenshot({ path: p, fullPage: true }).catch(() => {});
  const txt = path.join(shotDir, `FAIL-${name}.txt`);
  const body = await page.locator("body").innerText().catch(() => "");
  fs.writeFileSync(txt, `${page.url()}\n\n${body}`, "utf8");
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(shotDir, `${name}.png`), fullPage: true });
}

async function ingestPdf(page, filename, adapterId) {
  const filePath = path.join(CORPUS, filename);
  if (!fs.existsSync(filePath)) throw new Error(`missing PDF ${filePath}`);
  await page.goto(`${BASE}/ingestion`);
  await page.getByTestId("ingestion-intake-panel").waitFor();
  await page.getByTestId("intake-new-batch").click();
  await page.waitForTimeout(250);
  await page.getByTestId("intake-file-input").setInputFiles(filePath);
  const row = page.locator("[data-testid=intake-files-table] tr").filter({ hasText: filename }).first();
  await row.waitFor({ timeout: 45_000 });
  const select = row.locator('[data-testid^="intake-adapter-select-"]');
  await select.waitFor({ timeout: 45_000 });
  await select.selectOption(adapterId);
  await row.locator('[data-testid^="intake-run-adapter-"]').click();
  const open = row.locator('[data-testid^="intake-open-doc-"]');
  const err = row.locator(".error-text");
  try {
    await open.waitFor({ timeout: 90_000 });
  } catch (e) {
    const msg = (await err.innerText().catch(() => "")) || (await row.innerText());
    throw new Error(`extract failed for ${filename}: ${msg}`);
  }
  await open.click();
  await page.getByTestId("ingestion-workspace-page").waitFor();
}

async function fillProposedBySku(page, rowPrefix, proposedPrefix, sku, value, zeroOthers = true) {
  const rows = page.locator(`tr[data-testid^="${rowPrefix}"]`);
  await rows.first().waitFor();
  const n = await rows.count();
  let found = false;
  for (let i = 0; i < n; i++) {
    const row = rows.nth(i);
    const text = await row.innerText();
    const input = row.locator(`[data-testid^="${proposedPrefix}"]`);
    if (text.includes(sku)) {
      await input.fill(value);
      found = true;
    } else if (zeroOthers) {
      await input.fill("0");
    }
  }
  if (!found) throw new Error(`${rowPrefix} missing sku ${sku}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  page.setDefaultTimeout(45_000);
  page.on("request", (req) => {
    const url = req.url();
    const method = req.method();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
    if (!/\/api\//.test(url)) return;
    const rec = { method, url, at: new Date().toISOString() };
    mutating.push(rec);
    log.push({ step: "HTTP", ...rec });
  });

  try {
    await page.goto(`${BASE}/login`);
    await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
    await page.getByLabel(/senha/i).fill("admin123");
    await page.getByRole("button", { name: /entrar/i }).click();
    await page.waitForURL((u) => !u.pathname.includes("/login"));

    const resume = process.env.E8_DOC_RESUME || "";
    if (resume === "nat") {
      await page.goto(`${BASE}/customs/1`);
      await page.getByTestId("customs-nationalization-panel").waitFor();
      note("RESUME", { from: "nat", url: page.url() });
    } else if (resume === "doganale") {
      await page.goto(`${BASE}/ingestion/3`);
      await page.getByTestId("ingestion-workspace-page").waitFor();
      note("RESUME", { from: "doganale", url: page.url() });
    } else if (resume === "shipment") {
      await page.goto(`${BASE}/shipments/1`);
      await page.getByTestId("shipment-detail").waitFor();
      note("RESUME", { from: "shipment", url: page.url() });
    } else if (resume !== "packing") {
    await page.goto(`${BASE}/orders/new`);
    await page.getByTestId("order-create-page").waitFor();
    await page.getByTestId("order-code").fill("202");
    await page.getByTestId("new-supplier-name").fill("Heroe's Srl");
    await page.getByTestId("order-notes").fill(
      "Pedido 202 reconstruído na UI — não há Ordine 202 no corpus. Qtys/preços da Fattura_202.pdf.",
    );
    for (const ln of LINES) {
      await page.getByTestId("line-sku").fill(ln.sku);
      await page.getByRole("button", { name: "Criar SKU" }).click();
      await page.waitForTimeout(400);
      await page.getByTestId("line-qty").fill(ln.qty);
      await page.getByTestId("line-unit").fill("PZ");
      await page.getByTestId("line-price").fill(ln.price);
      await page.getByRole("button", { name: "Adicionar linha" }).click();
      const err = page.locator(".error, [class*='Notice']").filter({ hasText: "SKU não encontrado" });
      if (await err.count()) {
        throw new Error(`SKU ${ln.sku} not added`);
      }
    }
    await page.getByTestId("save-confirm").click();
    await page.getByTestId("confirm-modal-ok").click();
    await page.waitForURL(/\/orders\/\d+/);
    await shot(page, "01-order-confirmed");
    note("A-order", { url: page.url(), vi: await page.locator("body").innerText().then((t) => t.slice(0, 400)) });

    await ingestPdf(page, "Fattura_202.pdf", "fattura_heroes_v1");
    await page.getByTestId("fattura-commit-panel").waitFor();
    await page.getByTestId("fattura-order-candidate-list").waitFor();
    await page.locator('[data-testid^="fattura-order-candidate-"] input').first().check();
    await page.getByTestId("fattura-order-confirm-btn").click();
    await page.getByTestId("fattura-preview-result").waitFor({ timeout: 45_000 });
    await page.getByTestId("fattura-commit-submit").click();
    await page.getByTestId("fattura-processed-banner").waitFor({ timeout: 45_000 });
    await shot(page, "02-fattura-committed");
    note("B-fattura", { url: page.url() });

    const invCta = page.getByTestId("fattura-invoice-cta");
    if (await invCta.count()) await invCta.click();
    else await page.getByTestId("fattura-invoice-link").click();
    await page.getByTestId("issue-invoice").waitFor();
    await page.getByTestId("issue-invoice").click();
    await page.getByTestId("confirm-modal-ok").click();
    await page.getByText(/Emitida/i).first().waitFor({ timeout: 30_000 });
    await shot(page, "03-invoice-issued");
    note("C-issue", { url: page.url() });
    }

    if (resume !== "shipment" && resume !== "doganale" && resume !== "nat") {
    if (resume === "packing") {
      await page.goto(`${BASE}/ingestion/2`);
      await page.getByTestId("ingestion-workspace-page").waitFor();
      note("RESUME", { from: "packing", url: page.url() });
    } else {
      await ingestPdf(page, "PackingList_202.pdf", "packing_list_detail_v1");
    }
    await page.getByTestId("packing-commit-panel").waitFor();
    await page.getByTestId("packing-order-candidate-list").waitFor();
    const suggested = await page.getByTestId("packing-order-suggested").innerText();
    const oid = suggested.match(/#(\d+)/)?.[1];
    if (!oid) throw new Error(`no order id in ${suggested}`);
    await page.getByTestId(`packing-order-candidate-${oid}`).click();
    await page.getByTestId("packing-order-confirm-btn").click();
    await page.getByTestId("packing-order-id-input").fill(oid);
    await page.getByTestId("packing-preview-btn").click();
    await page.locator('[data-testid^="packing-group-"] input[type="radio"]').first().waitFor({ timeout: 30_000 });
    const DESC_SKU = {
      "GRAVITY ARION": "8057628955207",
      "THUNDER ARION": "8057628955191",
      "WASH BAG ARION": "8057628955214",
      "WASH BAG FIERCE": "8057628953104",
      "WASH BAG REBEL": "8057628950936",
      "WASH BAG SHOW": "8057628954194",
      "WASH BAG STARLIGHT": "8057628953814",
    };
    const used = [];
    for (const [desc, sku] of Object.entries(DESC_SKU)) {
      const group = page.locator("[data-testid^='packing-group-']").filter({
        has: page.locator("strong", { hasText: new RegExp(`^${desc}$`) }),
      });
      const radio = group.locator("label").filter({ hasText: sku }).locator("input");
      await radio.click();
      used.push(`${desc}→${sku}`);
      await page.waitForTimeout(250);
    }
    await page.getByTestId("packing-preview-btn").click();
    await page.waitForTimeout(400);
    await page.getByTestId("packing-preview-btn").click();
    await page.getByTestId("packing-preview-result").getByText("Pode commit: sim").waitFor({ timeout: 30_000 });
    const previewText = await page.getByTestId("packing-preview-result").innerText();
    note("D-packing-preview", { oid, used, previewText: previewText.slice(0, 600) });
    await page.getByTestId("packing-commit-btn").click();
    await page.getByTestId("packing-processed-banner").waitFor({ timeout: 45_000 });
    const shipHref = await page.getByTestId("packing-shipment-link").getAttribute("href");
    await shot(page, "04-packing-committed");
    note("D-packing", { url: page.url(), usedSkus: [...used], shipHref });

    await page.goto(`${BASE}/logistics-providers`);
    await page.getByTestId("provider-legal-name").fill("Transportadora Ensaio 202");
    await page.getByTestId("provider-trade-name").fill("Ensaio 202");
    await page.getByTestId("provider-type").selectOption("TRANSPORTADOR");
    await page.getByTestId("provider-create-submit").click();
    await page.getByTestId("providers-table").getByText("Ensaio 202").waitFor();

    if (shipHref) {
      await page.goto(`${BASE}${shipHref}`);
    } else {
      await page.goto(`${BASE}/shipments`);
      await page.getByTestId("shipments-table").locator("a").first().click();
    }
    await page.getByTestId("shipment-detail").waitFor();
    }
    if (resume !== "doganale" && resume !== "nat") {
    if (await page.getByTestId("shipment-booked-prereq").count()) {
      await page.getByTestId("detail-modal").selectOption("SEA");
      await page.getByTestId("detail-provider").selectOption({ index: 1 });
      await page.getByTestId("shipment-save-resumo").click();
      await page.getByTestId("shipment-advance-cta").waitFor({ timeout: 20_000 });
    }
    for (let i = 0; i < 3; i++) {
      const cta = page.getByTestId("shipment-advance-cta");
      await cta.waitFor();
      await cta.click();
      await page.getByTestId("confirmation-modal").waitFor();
      await page.getByTestId("confirm-modal-ok").click();
      await page.getByTestId("confirmation-modal").waitFor({ state: "hidden", timeout: 20_000 });
    }
    await page.reload();
    await page.getByTestId("shipment-detail").waitFor();
    await shot(page, "05-shipment-arrived");
    const shipText = await page.locator("body").innerText();
    if (!/Chegou|ARRIVED/i.test(shipText)) throw new Error("shipment not ARRIVED after reload");
    note("E-arrived", { url: page.url() });

    await ingestPdf(page, "FatturaDoganale_202.pdf", "fattura_doganale_v1");
    }
    let processId;
    if (resume !== "nat") {
    await page.getByTestId("doganale-commit-panel").waitFor();
    await page.locator('[data-testid^="doganale-invoice-candidate-"]').first().check();
    await page.getByTestId("doganale-invoice-confirm").click();
    await page.waitForTimeout(400);
    await page.locator('[data-testid^="doganale-shipment-candidate-"]').first().check();
    await page.getByTestId("doganale-shipment-confirm").click();
    await page.waitForFunction(() => {
      const b = document.querySelector('[data-testid="doganale-commit-submit"]');
      return b && !b.disabled;
    });
    await page.getByTestId("doganale-commit-submit").click();
    await page.getByTestId("doganale-processed-banner").waitFor({ timeout: 45_000 });
    await shot(page, "06-doganale-committed");
    note("F-doganale", { url: page.url() });
    await page.getByTestId("doganale-process-link").click();
    await page.getByTestId("customs-section-resumo").waitFor();
    await shot(page, "07-process-after-doganale");
    const processUrl = page.url();
    processId = Number(processUrl.match(/\/customs\/(\d+)/)?.[1]);
    if (!processId) throw new Error(`no process id in ${processUrl}`);

    await ingestPdf(page, "PrintDeclaration_202.pdf", "print_declaration_v1");
    await page.getByTestId("print-commit-panel").waitFor();
    await page.locator('[data-testid^="print-process-candidate-"]').first().check();
    await page.getByTestId("print-process-confirm").click();
    await page.getByTestId("print-commit-submit").click();
    await page.getByTestId("print-processed-banner").waitFor({ timeout: 45_000 });
    await shot(page, "08-print-attached");
    note("G-print", { url: page.url() });

    await ingestPdf(page, "Solicitacao_Numerario.pdf", "solicitacao_numerario_v1");
    await page.getByTestId("numerario-commit-panel").waitFor();
    await page.locator('[data-testid^="numerario-process-candidate-"]').first().check();
    await page.getByTestId("numerario-process-confirm").click();
    await page.getByTestId("numerario-preview").waitFor({ timeout: 45_000 });
    await page.getByTestId("numerario-commit-submit").click();
    await page.getByTestId("numerario-commit-result").waitFor({ timeout: 45_000 });
    await shot(page, "09-numerario-committed");
    note("H-numerario", { url: page.url() });

    await page.goto(`${BASE}/customs/${processId}`);
    await page.getByTestId("numerario-confirm").waitFor();
    await page.getByTestId("numerario-confirm").click();
    await page.getByText(/CONFIRMADO|Confirmado/i).first().waitFor({ timeout: 20_000 });
    await shot(page, "10-funding-confirmed");
    note("I-funding", { url: page.url() });

    await page.getByTestId("customs-edit-ext").fill("TEST-DUIMP-E8-DOC-202");
    await page.getByTestId("customs-save-ext").click();
    await page.getByTestId("customs-detail-ext").getByText("TEST-DUIMP-E8-DOC-202").waitFor();
    await page.getByTestId("customs-submit").click();
    await page.getByText(/Submetido/i).first().waitFor({ timeout: 20_000 });
    await shot(page, "11-duimp-submitted");
    note("J-duimp", { url: page.url(), duimp: "TEST-DUIMP-E8-DOC-202" });
    } else {
      processId = 1;
    }

    await page.getByTestId("customs-nationalization-panel").scrollIntoViewIfNeeded();
    const alreadyNat = await page.getByTestId("nationalization-list").getByText(/Confirmad/i).count();
    if (!alreadyNat) {
      await fillProposedBySku(
        page,
        "nationalization-residual-",
        "nationalization-proposed-",
        "8057628953814",
        "50",
      );
      await page.getByTestId("nationalization-create").click();
      await page.getByTestId("nationalization-add-items").click();
      await page.locator('[data-testid^="nationalization-confirm-"]').first().click();
    }
    await page.getByTestId("nationalization-list").getByText(/Confirmad/i).waitFor();
    await shot(page, "12-nationalization-partial");
    note("K-nat", { url: page.url(), alreadyNat: Boolean(alreadyNat) });

    await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
    await page.getByTestId("receipt-residual-table").waitFor();
    const residual0 = await page.getByTestId("receipt-residual-table").innerText();
    const typeVal = await page.getByTestId("receipt-type").inputValue();
    const hasProductId = await page.getByTestId("receipt-product-id").count();
    const hasNatItemId = await page.getByTestId("receipt-nationalization-item-id").count();
    await shot(page, "13-receipt-residual");
    note("L-residual", { residual0, typeVal, hasProductId, hasNatItemId });
    if (!residual0.includes("8057628953814")) throw new Error("residual missing 3814");
    if (typeVal !== "DOMESTIC_IN") throw new Error(`type=${typeVal}`);
    if (hasProductId !== 0 || hasNatItemId !== 0) throw new Error("raw id fields present");

    const invBefore = mutating.filter((m) => /\/api\/inventory\//.test(m.url)).length;
    await fillProposedBySku(page, "receipt-residual-", "receipt-proposed-", "8057628953814", "20");
    await page.getByTestId("receipt-location").selectOption("DOMESTIC-MAIN");
    await page.getByTestId("receipt-receive").evaluate((btn) => {
      btn.click();
      btn.click();
    });
    await page.getByTestId("receipt-list").getByText("Confirmado").waitFor();
    const residualAfter20 = await page.getByTestId("receipt-residual-table").innerText();
    await shot(page, "14-received-20");
    note("M-receive-20", { residualAfter20, invPosts: mutating.filter((m) => /\/api\/inventory\//.test(m.url)).length - invBefore });
    if (!residualAfter20.includes("30") && !/30/.test(residualAfter20)) {
      throw new Error(`expected residual 30 after 20 of 50: ${residualAfter20}`);
    }

    const reverseVisible = page.locator('[data-testid^="nationalization-reverse-"]').filter({
      hasNot: page.locator('[data-testid*="hidden"]'),
    });
    const reverseNat = await page.locator('[data-testid^="nationalization-reverse-"]:not([data-testid*="hidden"])').count();
    const reverseHidden = await page.locator('[data-testid^="nationalization-reverse-hidden-"]').count();
    note("V5-nat-reverse", { reverseNat, reverseHidden, reverseVisibleIgnored: await reverseVisible.count() });
    if (reverseHidden < 1) throw new Error("NAT reverse should be hidden after receipt");

    await page.getByTestId("receipt-residual-table").getByRole("link").filter({ hasText: "8057628953814" }).first().click();
    await page.getByTestId("sku-position-page").waitFor();
    const available = await page.getByTestId("sku-bucket-available_qty").innerText();
    const balances = await page.getByTestId("sku-balances").innerText();
    await page.reload();
    await page.getByTestId("sku-bucket-available_qty").waitFor();
    const availableReload = await page.getByTestId("sku-bucket-available_qty").innerText();
    await shot(page, "15-sku-position");
    note("N-sku", { available, balances, availableReload });
    if (!available.includes("20")) throw new Error(`available=${available}`);
    if (availableReload !== available) throw new Error("sku position changed on reload");

    await page.goto(`${BASE}/inventory/movements`);
    await page.getByTestId("inventory-movements-page").waitFor();
    const movText = await page.getByTestId("movements-list").innerText();
    await shot(page, "16-movements");
    note("N-movements", { movText: movText.slice(0, 500) });
    if (!/Entrada doméstica|DOMESTIC_IN/i.test(movText)) throw new Error("movement missing DOMESTIC_IN");
    if (/BONDED|RECLASS/i.test(movText)) throw new Error("unexpected bonded/reclass movement");

    await page.goto(`${BASE}/customs/${processId}`);
    await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
    const proposedInputs = page.locator('[data-testid^="receipt-proposed-"]');
    if (await proposedInputs.count()) {
      await fillProposedBySku(page, "receipt-residual-", "receipt-proposed-", "8057628953814", "31", true);
      const over = page.locator('[data-testid^="receipt-over-"]');
      await over.first().waitFor({ timeout: 10_000 }).catch(() => {});
      const overCopy = (await over.first().innerText().catch(() => "")) || "";
      await shot(page, "17-over-receipt-attempt");
      note("P-over-before-second", { overCopy });
      await fillProposedBySku(page, "receipt-residual-", "receipt-proposed-", "8057628953814", "30", true);
    }
    await page.getByTestId("receipt-location").selectOption("DOMESTIC-MAIN");
    await page.getByTestId("receipt-receive").click();
    await page.getByTestId("receipt-list").getByText("Confirmado").nth(1).waitFor();
    const residualAfter30 = await page.getByTestId("receipt-residual-table").innerText().catch(async () => {
      return await page.getByTestId("customs-receipt-panel").innerText();
    });
    await shot(page, "18-received-30");
    note("O-receive-30", { residualAfter30 });

    const overInput = page.locator('[data-testid^="receipt-proposed-"]');
    if (await overInput.count()) {
      await overInput.first().fill("1");
      const overHint = await page.locator('[data-testid^="receipt-over-"]').first().innerText().catch(() => "");
      await shot(page, "19-over-receipt-zero-residual");
      note("P-over-after", { overHint });
    } else {
      await shot(page, "19-no-proposed-zero-residual");
      note("P-over-after", { overHint: "no proposed inputs — residual table empty as expected" });
    }

    await page.getByTestId("sku-position-page").waitFor({ timeout: 1_000 }).catch(() => {});
    await page.goto(`${BASE}/customs/${processId}`);
    await page.getByTestId("receipt-residual-table").getByRole("link").filter({ hasText: "8057628953814" }).first().click().catch(async () => {
      await page.goto(`${BASE}/inventory/movements`);
      await page.getByTestId("movements-list").getByRole("link").first().click();
    });
    await page.getByTestId("sku-position-page").waitFor();
    const available50 = await page.getByTestId("sku-bucket-available_qty").innerText();
    await shot(page, "20-sku-after-50");
    note("O-sku-50", { available50 });
    if (!available50.includes("50")) throw new Error(`available after 50=${available50}`);

    const invPosts = mutating.filter((m) => m.method === "POST" && /\/api\/inventory\//.test(m.url));
    const invNonUi = invPosts.filter((m) => !/\/api\/inventory\/(receipts|movements)/.test(m.url));
    const uploadPosts = mutating.filter((m) => /\/api\/ingestion\/.*\/(upload|commit|run-adapter|classify)/.test(m.url));
    note("NET", {
      inventoryPostCount: invPosts.length,
      inventoryUrls: invPosts.map((m) => m.url),
      uploadViaUiCount: mutating.filter((m) => /\/api\/ingestion\//.test(m.url)).length,
    });

    fs.writeFileSync(
      logPath,
      JSON.stringify(
        {
          result: "PASS",
          process_id: processId,
          duimp: "TEST-DUIMP-E8-DOC-202",
          inventoryMutations: invPosts,
          mutating,
          log,
        },
        null,
        2,
      ),
      "utf8",
    );
    await browser.close();
    console.log("DOC202 PASS", logPath, "inventoryPOSTs", invPosts.length, "invNonUi", invNonUi.length, "uploadPosts", uploadPosts.length);
  } catch (err) {
    await dump(page, "last");
    fs.writeFileSync(
      logPath,
      JSON.stringify({ error: String(err), stack: err?.stack, log, mutating }, null, 2),
      "utf8",
    );
    await browser.close();
    throw err;
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
