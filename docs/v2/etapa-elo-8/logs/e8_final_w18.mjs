/**
 * E8-FINAL-VERIFY W1–W8. Inventory mutations only via UI.
 * Reads process/product from e8-walk-fixture.json after rebuild.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "../../../../v2/frontend");
const require = createRequire(path.join(frontendRoot, "package.json"));
const { chromium } = require("playwright");

const shotDir = path.resolve(__dirname, "../screenshots/final-w18");
const logPath = path.join(__dirname, "e8-final-w18-log.json");
const fixturePath = path.join(__dirname, "e8-walk-fixture.json");
const BASE = process.env.E8_WALK_BASE || "http://localhost:5174";

fs.mkdirSync(shotDir, { recursive: true });

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const PROCESS = Number(fixture.process_id);
const PRODUCT_STARLIGHT = Number(fixture.products["8057628953814"]);

const log = [];
const inventoryMutations = [];
function note(step, data) {
  log.push({ step, ...data, at: new Date().toISOString() });
  console.log(JSON.stringify({ step, ...data }));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  page.setDefaultTimeout(20_000);
  page.on("request", (req) => {
    const url = req.url();
    const method = req.method();
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
    if (!/\/api\//.test(url)) return;
    const rec = { method, url, at: new Date().toISOString() };
    if (/\/api\/inventory\//.test(url)) inventoryMutations.push(rec);
    log.push({ step: "HTTP", ...rec });
  });

  await page.goto(`${BASE}/login`);
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  await page.goto(`${BASE}/customs/${PROCESS}`);
  await page.getByTestId("customs-receipt-panel").scrollIntoViewIfNeeded();
  await page.getByTestId("receipt-residual-table").waitFor();
  const w1Table = await page.getByTestId("receipt-residual-table").innerText();
  const typeVal = await page.getByTestId("receipt-type").inputValue();
  const hasProductId = await page.getByTestId("receipt-product-id").count();
  const hasNatItemId = await page.getByTestId("receipt-nationalization-item-id").count();
  const typeOptions = await page.locator("#receipt-type option").evaluateAll((opts) =>
    opts.map((o) => o.value),
  );
  await page.screenshot({ path: path.join(shotDir, "w1-residual.png"), fullPage: true });
  note("W1", {
    abri: `/customs/${PROCESS}`,
    vi: w1Table,
    typeVal,
    hasProductId,
    hasNatItemId,
    typeOptions,
  });
  if (!w1Table.includes("WASH BAG STARLIGHT - RED") || !w1Table.includes("8057628953814")) {
    throw new Error("W1 missing STARLIGHT / EAN");
  }
  if (typeVal !== "DOMESTIC_IN") throw new Error(`W1 type=${typeVal}`);
  if (hasProductId !== 0) throw new Error("W1 still has product id field");
  if (hasNatItemId !== 0) throw new Error("W1 still has nationalization_item_id field");
  if (typeOptions.some((v) => v === "BONDED_IN" || v === "RECLASS")) {
    throw new Error("W1 type select not frozen");
  }

  const invBeforeW2 = inventoryMutations.length;
  await page.getByTestId("receipt-proposed-1").fill("20");
  await page.getByTestId("receipt-proposed-2").fill("0");
  await page.getByTestId("receipt-location").selectOption("DOMESTIC-MAIN");
  const receive = page.getByTestId("receipt-receive");
  await receive.evaluate((btn) => {
    btn.click();
    btn.click();
  });
  await page.getByTestId("receipt-list").getByText("Confirmado").waitFor();
  const listAfterW2 = await page.getByTestId("receipt-list").innerText();
  const residualAfterW2 = await page.getByTestId("receipt-residual-table").innerText();
  await page.screenshot({ path: path.join(shotDir, "w2-received-20.png"), fullPage: true });
  note("W2", {
    cliquei: "Receber 20 + double-click mesmo tick; location DOMESTIC-MAIN",
    listAfterW2,
    residualAfterW2,
    inventoryPostsThisStep: inventoryMutations.length - invBeforeW2,
  });
  const confirmedCount = (listAfterW2.match(/Confirmado/g) || []).length;
  if (confirmedCount !== 1) throw new Error(`W2 expected 1 confirmed, got ${confirmedCount}`);
  if (!residualAfterW2.includes("30")) throw new Error("W2 residual 3814 should be 30");

  await page.goto(`${BASE}/inventory/movements?product_id=${PRODUCT_STARLIGHT}`);
  await page.getByTestId("inventory-movements-page").waitFor();
  const movText = await page.getByTestId("movements-list").innerText();
  await page.screenshot({ path: path.join(shotDir, "w3-movements.png"), fullPage: true });
  await page.goto(`${BASE}/inventory/sku/${PRODUCT_STARLIGHT}`);
  await page.getByTestId("sku-position-page").waitFor();
  const available = await page.getByTestId("sku-bucket-available_qty").innerText();
  const cleared = await page.getByTestId("sku-bucket-cleared_not_received_qty").innerText();
  const scope = await page.getByTestId("sku-bucket-scope-cleared_not_received_qty").innerText();
  const balances = await page.getByTestId("sku-balances").innerText();
  await page.reload();
  await page.getByTestId("sku-bucket-available_qty").waitFor();
  const availableReload = await page.getByTestId("sku-bucket-available_qty").innerText();
  await page.screenshot({ path: path.join(shotDir, "w3-sku-position.png"), fullPage: true });
  note("W3", { movText, available, cleared, scope, balances, availableReload });
  if (!available.includes("20")) throw new Error(`W3 available=${available}`);
  if (!scope.toLowerCase().includes("todos os processos")) throw new Error("W3 missing scope label");
  if (availableReload !== available) throw new Error("W3 reload changed available");

  await page.goto(`${BASE}/customs/${PROCESS}`);
  await page.getByTestId("receipt-residual-table").waitFor();
  await page.getByTestId("receipt-proposed-1").fill("30");
  await page.getByTestId("receipt-proposed-2").fill("0");
  await page.getByTestId("receipt-receive").click();
  await page.getByTestId("receipt-list").getByText("Confirmado").first().waitFor();
  await page.screenshot({ path: path.join(shotDir, "w4-received-30.png"), fullPage: true });
  await page.goto(`${BASE}/inventory/sku/${PRODUCT_STARLIGHT}`);
  const available50 = await page.getByTestId("sku-bucket-available_qty").innerText();
  note("W4", { available50 });
  if (!available50.includes("50")) throw new Error(`W4 available=${available50}`);

  await page.goto(`${BASE}/customs/${PROCESS}`);
  await page.getByTestId("receipt-residual-table").waitFor();
  const overInput = page.getByTestId("receipt-proposed-2");
  await overInput.fill("99");
  const overHint = await page.getByTestId("receipt-over-2").innerText();
  await page.getByTestId("receipt-receive").click();
  await page.getByTestId("receipt-error").waitFor();
  const overCopy = await page.getByTestId("receipt-error").innerText();
  await page.screenshot({ path: path.join(shotDir, "w5-over-receipt.png"), fullPage: true });
  note("W5", { overHint, overCopy });
  if (!/residual/i.test(overCopy)) throw new Error(`W5 copy=${overCopy}`);

  await overInput.fill("10");
  await page.getByTestId("receipt-receive").click();
  await page.getByText("Nada a receber").waitFor();
  const afterW6 = await page.getByTestId("receipt-list").innerText();
  await page.screenshot({ path: path.join(shotDir, "w6-fierce.png"), fullPage: true });
  note("W6", { afterW6 });

  const reverseNat = await page
    .locator('[data-testid^="nationalization-reverse-"]:not([data-testid*="hidden"])')
    .count();
  const reverseHidden = await page.locator('[data-testid^="nationalization-reverse-hidden-"]').count();
  const hiddenCopy = await page.locator('[data-testid^="nationalization-reverse-hidden-"]').first().innerText();
  await page.locator('[data-testid^="receipt-reverse-"]').first().click();
  await page.getByTestId("receipt-list").getByText("Estornado").waitFor();
  await page.screenshot({ path: path.join(shotDir, "w7-reversed.png"), fullPage: true });
  await page.getByTestId("receipt-proposed-2").waitFor();
  await page.getByTestId("receipt-proposed-2").fill("10");
  await page.getByTestId("receipt-receive").click();
  await page.getByText("Nada a receber").waitFor();
  const afterRereceive = await page.getByTestId("receipt-list").innerText();
  note("W7", { reverseNat, reverseHidden, hiddenCopy, afterRereceive });
  if (reverseNat !== 0) throw new Error("W7 Reverter liberação still visible");
  if (reverseHidden < 1) throw new Error("W7 reverse-hidden missing");

  await page.getByTestId("customs-section-audit").scrollIntoViewIfNeeded();
  const audit = await page.getByTestId("customs-audit-table").innerText();
  await page.screenshot({ path: path.join(shotDir, "w8-audit.png"), fullPage: true });
  note("W8", { audit });
  if (!audit.includes("Recebimento")) throw new Error("W8 audit missing Recebimento scope");
  if (!/Recebimento confirmado|Recebimento criado/i.test(audit)) {
    throw new Error(`W8 audit actions=${audit}`);
  }

  const invPosts = inventoryMutations.filter((m) => m.method === "POST");
  const externalInv = inventoryMutations.filter((m) => !/\/api\/inventory\//.test(m.url));
  fs.writeFileSync(
    logPath,
    JSON.stringify(
      {
        result: "PASS",
        process_id: PROCESS,
        product_starlight: PRODUCT_STARLIGHT,
        inventoryMutations,
        inventoryPostCount: invPosts.length,
        log,
      },
      null,
      2,
    ),
    "utf-8",
  );
  await browser.close();
  console.log("WALK PASS", logPath, "inventoryPOSTs", invPosts.length, "nonInvMut", externalInv.length);
}

main().catch((err) => {
  console.error(err);
  fs.writeFileSync(logPath, JSON.stringify({ error: String(err), log, inventoryMutations }, null, 2), "utf-8");
  process.exit(1);
});
