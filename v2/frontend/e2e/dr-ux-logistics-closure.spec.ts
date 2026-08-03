/**
 * DR-UX — fechamento operacional UI (patch corretivo + regressão).
 * Asserts de valor (qty compacta, provenance PT, download bytes, reload).
 */
import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

const EVIDENCE = path.resolve(process.cwd(), "..", "..", "docs", "v2", "etapa-doc-readiness");
const SHOT = path.join(EVIDENCE, "screenshots");

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({
    timeout: 20000,
  });
}

async function modalConfirm(page: Page) {
  await page.getByTestId("confirm-modal-ok").click();
}

async function createConfirmedOrder(page: Page, tag: string) {
  const supplierName = `Fornecedor DRUX ${tag}`;
  await page.goto("/orders/new");
  await expect(page.getByTestId("order-create-page")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("order-code").fill(tag);
  await page.getByTestId("new-supplier-name").fill(supplierName);

  await page.getByTestId("line-sku").fill(`SKU-${tag}-A`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-unit").fill("PZ");
  await page.getByTestId("line-price").fill("5");
  await page.getByRole("button", { name: /adicionar linha/i }).click();

  await page.getByTestId("line-sku").fill(`SKU-${tag}-B`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("2");
  await page.getByTestId("line-unit").fill("SET");
  await page.getByTestId("line-price").fill("50");
  await page.getByRole("button", { name: /adicionar linha/i }).click();

  await page.getByTestId("save-confirm").click();
  await modalConfirm(page);
  await expect(page.getByTestId("order-cockpit").or(page.getByTestId("order-detail"))).toBeVisible({
    timeout: 20000,
  });
  if (await page.getByTestId("order-cockpit").count()) {
    await page.getByTestId("cockpit-commercial-link").click();
  }
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });
  return supplierName;
}

function expectCompactWire(value: string) {
  expect(value).not.toMatch(/\.\d*0{3,}$/);
  expect(value).not.toMatch(/\.0000$/);
}

test.describe("DR-UX logistics closure", () => {
  test("contents + summary reload + A2 regression screenshots", async ({ page }) => {
    test.setTimeout(300_000);
    fs.mkdirSync(SHOT, { recursive: true });
    await page.setViewportSize({ width: 1366, height: 900 });

    const tag = `DRUX-${Date.now().toString().slice(-8)}`;
    await login(page);

    const supplierName = await createConfirmedOrder(page, tag);
    await expect(page.getByTestId("order-detail")).toContainText(supplierName);
    await page.screenshot({ path: path.join(SHOT, "drux-order-supplier.png"), fullPage: true });

    await page.getByTestId("order-doc-upload").setInputFiles({
      name: "Ordine_DRUX.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 drux-order"),
    });
    await expect(page.getByTestId(/order-doc-actions-\d+-name/).first()).toHaveText(
      "Ordine_DRUX.pdf",
      { timeout: 15000 },
    );
    const orderDocActions = page.getByTestId(/order-doc-actions-\d+$/).first();
    const orderDocTestId = await orderDocActions.getAttribute("data-testid");
    const orderDocId = Number(orderDocTestId?.match(/order-doc-actions-(\d+)/)?.[1]);
    expect(orderDocId).toBeGreaterThan(0);

    const dlRes = await page.request.get(`/api/documents/${orderDocId}/content?download=1`);
    expect(dlRes.status()).toBe(200);
    const dlBody = await dlRes.body();
    expect(dlBody.toString("utf8")).toContain("%PDF-1.4 drux-order");
    expect(dlRes.headers()["content-type"] ?? "").toMatch(/pdf|octet-stream/i);
    expect(JSON.stringify(await dlRes.headersArray())).not.toMatch(/absolute_path/i);

    await page.getByTestId(`order-doc-actions-${orderDocId}-download`).focus();
    await page.keyboard.press("Tab");
    await page.screenshot({ path: path.join(SHOT, "drux-doc-download.png"), fullPage: true });

    await page.getByTestId("cancel-order").click();
    await expect(page.getByText(/informe o motivo do cancelamento/i)).toBeVisible();
    await expect(page.getByTestId("cancel-reason")).toHaveValue("");

    await page.goto("/shipments/new");
    await expect(page.getByTestId("shipment-create-page")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("shipment-create-submit").click();
    await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 20000 });

    await page.getByTestId("shipment-add-item").click();
    await page.getByTestId("picker-order-code").fill(tag);
    await page.getByRole("button", { name: /buscar candidatos/i }).click();
    await expect(page.getByTestId("picker-candidate").first()).toBeVisible({ timeout: 10000 });
    await page.getByTestId("picker-qty").fill("10");
    await modalConfirm(page);
    await expect(page.getByTestId("shipment-items")).toContainText(/SKU-/i, { timeout: 10000 });

    const itemQty = page.getByTestId(/item-qty-\d+/).first();
    await expect(itemQty).toBeVisible();
    expectCompactWire(await itemQty.inputValue());
    await expect(itemQty).toHaveValue("10");

    await page.getByTestId("package-type").selectOption("CARTON");
    await page.getByTestId("package-count").fill("1");
    await page.getByTestId("package-external-no").fill("1");
    await page.getByTestId("package-packaging-ncm").fill("4819100000");
    await page.getByTestId("package-length").fill("47");
    await page.getByTestId("package-width").fill("34");
    await page.getByTestId("package-height").fill("56");
    await page.getByTestId("package-net-weight").fill("5.40");
    await page.getByTestId("package-gross-weight").fill("6.00");
    await page.getByTestId("shipment-add-package").click();
    await expect(page.getByText("4819100000")).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SHOT, "drux-a1-package.png"), fullPage: true });

    await page.getByTestId("package-range-from").fill("10");
    await page.getByTestId("package-range-to").fill("11");
    await page.getByTestId("package-net-weight").fill("1.40");
    await page.getByTestId("package-gross-weight").fill("1.60");
    await page.getByTestId("shipment-batch-range").click();
    await expect(page.getByTestId("shipment-packages")).toContainText("10", { timeout: 15000 });
    await page.screenshot({ path: path.join(SHOT, "drux-a1-batch.png"), fullPage: true });

    await page.getByTestId(/shipment-edit-contents-\d+/).first().click();
    await expect(page.getByTestId("package-contents-editor")).toBeVisible();
    await expect(page.locator("#package-contents-heading")).toBeFocused();

    const itemSelect = page.getByTestId("content-item-0");
    const itemValue = await itemSelect.locator("option").nth(1).getAttribute("value");
    await itemSelect.selectOption(itemValue!);

    await page.getByTestId("content-qty-0").fill("10");
    await page.getByTestId("content-units-per-0").fill("10");
    await page.getByTestId("content-unit-0").fill("PZ");
    await page.getByTestId("content-ncm-0").fill("9403609000");
    await page.getByTestId("content-desc-0").fill("Mesa DRUX");
    await page.getByTestId("content-line-ref-0").fill("L1");
    await page.getByTestId("content-unit-net-0").fill("0.540");
    await page.getByTestId("content-unit-gross-0").fill("0.600");
    await page.getByTestId("content-total-net-0").fill("5.40");
    await page.getByTestId("content-total-gross-0").fill("6.00");
    await page.screenshot({ path: path.join(SHOT, "drux-a1-contents-filled.png"), fullPage: true });

    await page.getByTestId("shipment-save-contents").click();
    await page.waitForTimeout(800);
    await page.reload();
    await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 20000 });
    await page.getByTestId(/shipment-edit-contents-\d+/).first().click();
    await expect(page.getByTestId("package-contents-editor")).toBeVisible();
    await expect(page.getByTestId("content-qty-0")).toHaveValue("10");
    await expect(page.getByTestId("content-units-per-0")).toHaveValue("10");
    expectCompactWire(await page.getByTestId("content-qty-0").inputValue());
    await expect(page.getByTestId("content-unit-0")).toHaveValue("PZ");
    await expect(page.getByTestId("content-ncm-0")).toHaveValue("9403609000");
    await expect(page.getByTestId("content-desc-0")).toHaveValue("Mesa DRUX");
    await expect(page.getByTestId("content-line-ref-0")).toHaveValue("L1");
    await expect(page.getByTestId("content-unit-net-0")).toHaveValue("0.54");
    await expect(page.getByTestId("content-unit-gross-0")).toHaveValue("0.6");
    await expect(page.getByTestId("content-total-net-0")).toHaveValue("5.4");
    await expect(page.getByTestId("content-total-gross-0")).toHaveValue("6");
    await page.screenshot({ path: path.join(SHOT, "drux-a1-contents-reload.png"), fullPage: true });

    await page.getByTestId("shipment-doc-upload").setInputFiles({
      name: "PackingList_DRUX.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 packing-drux"),
    });
    await expect(page.getByTestId(/shipment-doc-actions-\d+-name/).first()).toHaveText(
      "PackingList_DRUX.pdf",
      { timeout: 15000 },
    );

    const summaryDoc = page.getByTestId("summary-document-id");
    await expect(summaryDoc.locator("option")).toHaveCount(2, { timeout: 10000 });
    const docVal = await summaryDoc.locator("option").nth(1).getAttribute("value");
    await summaryDoc.selectOption(docVal!);
    await page.getByTestId("summary-provenance").selectOption("PACKING_LIST");
    await page.getByTestId("summary-net").fill("12.00");
    await page.getByTestId("summary-gross").fill("14.00");
    await page.getByTestId("summary-pallets").fill("0");
    await page.getByTestId("summary-cartons").fill("3");
    await page.getByTestId("summary-volume").fill("0.180");
    await page.getByTestId("shipment-save-summary").click();
    await page.waitForTimeout(800);

    await page.reload();
    await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("shipment-documents")).toContainText("PackingList_DRUX.pdf");
    await expect(page.getByTestId("shipment-documents")).toContainText("Origem do total declarado");
    await expect(page.getByTestId("shipment-documents")).toContainText("Packing List");
    await expect(page.getByText("Provenance", { exact: true })).toHaveCount(0);
    await expect(page.getByTestId("shipment-documents")).toContainText("12");
    await expect(page.getByTestId("shipment-totals")).toBeVisible();
    await page.screenshot({ path: path.join(SHOT, "drux-a1-summary-reload.png"), fullPage: true });

    await page.goto("/orders");
    await page.getByRole("link", { name: new RegExp(tag) }).first().click();
    await expect(page.getByTestId("order-cockpit").or(page.getByTestId("order-detail"))).toBeVisible({
      timeout: 15000,
    });
    if (await page.getByTestId("order-cockpit").count()) {
      await page.getByTestId("cockpit-commercial-link").click();
    }
    await expect(page.getByTestId("order-detail")).toBeVisible();
    await page.getByTestId("new-invoice-number").fill(`F-${tag}`);
    await page.getByTestId("new-invoice-date").fill("2026-03-30");
    await page.getByTestId("create-invoice").click();
    await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("invoice-header")).toBeVisible();
    await expect(page.getByTestId("invoice-items-table")).toBeVisible();
    await expect(page.getByTestId("qty-0")).toHaveValue("10");
    await expect(page.getByTestId("qty-1")).toHaveValue("2");
    expectCompactWire(await page.getByTestId("qty-0").inputValue());
    expectCompactWire(await page.getByTestId("qty-1").inputValue());
    await expect(page.getByTestId("save-items")).toBeVisible();
    const liquidoHeader = page.getByTestId("invoice-items-table").getByRole("columnheader", {
      name: "Líquido",
    });
    await expect(liquidoHeader).toBeVisible();
    await page.screenshot({ path: path.join(SHOT, "drux-invoice-header.png"), fullPage: true });
  });
});
