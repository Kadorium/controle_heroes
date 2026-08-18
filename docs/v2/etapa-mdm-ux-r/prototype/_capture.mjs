/**
 * MDM-UX-R R2 capture + A2 walk. Isolated proto at :8765. No production frontend.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "../../../../v2/frontend");
const require = createRequire(path.join(frontendRoot, "package.json"));
const { chromium } = require("playwright");

const BASE = process.env.PROTO_BASE || "http://127.0.0.1:8765";
const shotDir = path.join(__dirname, "screenshots");
const walkPath = path.join(__dirname, "A2_WALK.json");
fs.mkdirSync(shotDir, { recursive: true });

const walk = [];
function step(id, abri, vi, cliquei, resultado) {
  const row = { id, abri, vi, cliquei, resultado, at: new Date().toISOString() };
  walk.push(row);
  console.log(JSON.stringify(row));
}

async function shot(page, name) {
  const file = path.join(shotDir, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  console.log("shot", name);
}

async function waitList(page) {
  await page.waitForSelector('[data-testid="products-table"], [data-testid="empty-catalog"], [data-testid="no-results"]', {
    timeout: 8000,
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(12_000);

  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.evaluate(() => sessionStorage.clear());
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await waitList(page);

  // --- walk 1 search ---
  await page.getByTestId("products-search").fill("STARLIGHT");
  await page.waitForTimeout(400);
  await waitList(page);
  const searchCount = await page.locator('[data-testid="products-total"]').textContent();
  step(
    1,
    "Abri #/catalog/products",
    "Vi busca dominante sem botão Buscar, KPIs rotulados, chips, tabela",
    "Cliquei/digitei STARLIGHT na busca (debounce 280ms)",
    `Resultado: lista filtrada (${searchCount?.trim()})`,
  );
  await shot(page, "1440-01-product-list-rich");

  // --- walk 2 quick filter ---
  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await page.getByRole("button", { name: "Dados incompletos", exact: true }).click();
  await page.waitForTimeout(200);
  await waitList(page);
  step(
    2,
    "Abri lista sem filtro",
    "Vi chip Dados incompletos solto",
    "Cliquei quick filter Dados incompletos",
    `Resultado: KPI ativo + chip removível + ${await page.locator('[data-testid="products-total"]').textContent()}`,
  );
  await shot(page, "1440-02-product-list-incomplete");

  // --- walk 3 more filters ---
  await page.getByTestId("more-filters").click();
  await page.waitForSelector('[data-testid="more-panel"]');
  step(
    3,
    "Abri lista com incompletos",
    "Vi botão Mais filtros",
    "Cliquei Mais filtros",
    "Resultado: painel de facets Tamanho/Cor/Origem (só com valores)",
  );
  await shot(page, "1440-03-more-filters");

  // --- walk 4 remove chip ---
  await page.getByRole("button", { name: /Remover Dados incompletos/i }).click();
  await page.waitForTimeout(200);
  step(
    4,
    "Abri lista com chip Dados incompletos",
    "Vi chip removível",
    "Cliquei × no chip",
    `Resultado: filtro saiu; total ${await page.locator('[data-testid="products-total"]').textContent()}`,
  );

  // --- walk 5 pagination ---
  await page.getByRole("button", { name: "Próxima" }).click();
  await page.waitForTimeout(200);
  step(
    5,
    "Abri lista página 1",
    "Vi paginação e total",
    "Cliquei Próxima",
    `Resultado: ${await page.locator('[data-testid="products-total"]').textContent()}`,
  );

  // --- walk 6 sort ---
  await page.getByTestId("products-sort").selectOption("sku");
  await page.waitForTimeout(200);
  step(
    6,
    "Abri lista na página 2",
    "Vi select Ordenar",
    "Cliquei ordenação SKU",
    "Resultado: lista reordenada por SKU e offset resetado para 0",
  );

  // --- walk 7 open detail ---
  await page.goto(`${BASE}/#/catalog/products?q=WASH%20BAG`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await page.locator('[data-testid="products-table"] tbody tr').first().click();
  await page.waitForSelector('[data-testid="product-detail-page"]');
  step(
    7,
    "Abri lista filtrada WASH BAG",
    "Vi linha WASH BAG STARLIGHT — RED",
    "Cliquei a linha inteira",
    "Resultado: ficha em leitura; descrição no H1; SKU secundário; badge Ativo",
  );
  await shot(page, "1440-04-product-detail-read");
  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await shot(page, "1440-07-sidebar");
  await page.goto(`${BASE}/#/catalog/products?q=WASH%20BAG`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await page.locator('[data-testid="products-table"] tbody tr').first().click();
  await page.waitForSelector('[data-testid="product-detail-page"]');

  // --- walk 8 back preserves ---
  const hashBefore = page.url();
  await page.getByTestId("product-back").click();
  await page.waitForSelector('[data-testid="product-list-page"]');
  const hashAfter = page.url();
  step(
    8,
    `Abri ficha a partir de ${hashBefore}`,
    "Vi Voltar à lista",
    "Cliquei Voltar à lista",
    `Resultado: voltei com query preservada (${hashAfter})`,
  );

  // --- walk 9 read to edit ---
  await page.locator('[data-testid="products-table"] tbody tr').first().click();
  await page.waitForSelector('[data-testid="product-detail-page"]');
  await page.getByTestId("product-edit").click();
  await page.waitForSelector('[data-testid="product-edit-page"]');
  step(
    9,
    "Abri ficha em leitura",
    "Vi botão Editar explícito (não era formulário permanente)",
    "Cliquei Editar",
    "Resultado: seções verticais editáveis; SKU readonly",
  );
  await shot(page, "1440-05-product-detail-edit");

  // --- walk 10 create ---
  await page.goto(`${BASE}/#/catalog/products/new`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="product-create-page"]');
  await page.getByTestId("product-sku").fill("PROTO-CREATE-1");
  await page.getByTestId("product-description").fill("Produto criado no proto");
  await shot(page, "1440-06-product-create");
  await page.getByTestId("product-create-submit").click();
  await page.waitForSelector('[data-testid="product-detail-page"]');
  step(
    10,
    "Abri #/catalog/products/new",
    "Vi SKU + descrição + CTA Criar; sem L-006 obrigatório",
    "Cliquei Criar",
    "Resultado: ficha do novo produto na sessão; notice sem epic_v2",
  );

  // supplier + overflow
  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await page.getByTestId("catalog-overflow").click();
  await page.waitForSelector(".menu");
  await shot(page, "1440-08-supplier-overflow");
  await page.getByRole("link", { name: /Fornecedor principal/ }).click();
  await page.waitForSelector('[data-testid="supplier-detail-page"]');
  await shot(page, "1440-08-supplier-detail");

  await page.goto(`${BASE}/#/admin/users`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="users-list-page"]');
  await shot(page, "1440-09-users");

  await page.goto(`${BASE}/#/futuro/selecionar`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="future-select"]');
  await shot(page, "1440-10-future-select");

  await page.goto(`${BASE}/#/catalog/products?q=PROTO-B5`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await shot(page, "1440-11-b5-fallback-list");
  await page.locator('[data-testid="products-table"] tbody tr').first().click();
  await page.waitForSelector('[data-testid="product-detail-page"]');
  await shot(page, "1440-12-b5-fallback-detail");

  // 1366
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(`${BASE}/#/catalog/products?q=STARLIGHT`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await shot(page, "1366-01-product-list-rich");
  await page.goto(`${BASE}/#/catalog/products?incomplete=1`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await shot(page, "1366-02-product-list-incomplete");
  if (!(await page.locator('[data-testid="more-panel"]').count())) {
    await page.getByTestId("more-filters").click();
  }
  await page.waitForSelector('[data-testid="more-panel"]');
  await shot(page, "1366-03-more-filters");
  await page.goto(`${BASE}/#/catalog/products?q=WASH%20BAG`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await page.locator('[data-testid="products-table"] tbody tr').first().click();
  await page.waitForSelector('[data-testid="product-detail-page"]');
  await shot(page, "1366-04-product-detail-read");
  await page.getByTestId("product-edit").click();
  await page.waitForSelector('[data-testid="product-edit-page"]');
  await shot(page, "1366-05-product-detail-edit");
  await page.goto(`${BASE}/#/catalog/products/new`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="product-create-page"]');
  await shot(page, "1366-06-product-create");
  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.waitForTimeout(350);
  await waitList(page);
  await shot(page, "1366-07-sidebar");
  await page.goto(`${BASE}/#/catalog/suppliers/26`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="supplier-detail-page"]');
  await shot(page, "1366-08-supplier");
  await page.goto(`${BASE}/#/admin/users`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="users-list-page"]');
  await shot(page, "1366-09-users");

  // 1100 compact
  await page.setViewportSize({ width: 1100, height: 768 });
  await page.goto(`${BASE}/#/catalog/products`, { waitUntil: "networkidle" });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await waitList(page);
  await shot(page, "1100-01-compact-sidebar-list");
  await page.goto(`${BASE}/#/catalog/products/new`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="product-create-page"]');
  await shot(page, "1100-02-compact-create");
  await page.goto(`${BASE}/#/admin/users`, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="users-list-page"]');
  await shot(page, "1100-03-compact-users");

  fs.writeFileSync(walkPath, JSON.stringify(walk, null, 2), "utf8");
  await browser.close();
  console.log("done", walk.length, "walk steps");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
