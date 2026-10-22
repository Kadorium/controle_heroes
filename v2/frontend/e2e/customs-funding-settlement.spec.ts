/**
 * CUSTOMS-FUNDING — registrar pagamento + alocar (Create ≠ Allocate).
 * Prereqs via API; financeiro na UI.
 */
import { test, expect } from "@playwright/test";

test("CUSTOMS_FUNDING settlement: partial then residual", async ({ page }) => {
  test.setTimeout(180_000);

  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({ timeout: 15000 });

  const tag = Date.now().toString(36);
  const payeeName = `Bechtrans-${tag}`;

  const created = await page.evaluate(async ({ payeeName }) => {
    const post = async (url: string, body: unknown) => {
      const r = await fetch(url, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`${url} ${r.status} ${await r.text()}`);
      return r.json();
    };
    const process = await post("/api/import-processes", {
      external_reference: `CFUND-${payeeName}`,
    });
    const payee = await post("/api/customs/payees", { name: payeeName, tax_id: "12345678000199" });
    const due = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
    const fr = await post(`/api/import-processes/${process.id}/funding-requests`, {
      payee_id: payee.id,
      currency: "BRL",
      declared_total: "100.00",
      due_date: due,
    });
    const confirmed = await post(
      `/api/import-processes/${process.id}/funding-requests/${fr.id}/confirm`,
      { expected_version: fr.version },
    );
    return {
      processId: process.id,
      payableId: confirmed.payable_links[0].payable_id as number,
    };
  }, { payeeName });

  await page.goto(`/customs/${created.processId}`);
  await expect(page.getByTestId("customs-numerario-panel")).toBeVisible();
  await expect(page.getByTestId("numerario-settlement-status")).toHaveText("A pagar");
  await page.getByTestId("numerario-register-payment").click();
  await expect(page.getByTestId("payment-create")).toBeVisible();
  await expect(page.getByTestId("pay-payee-readonly")).toHaveValue(payeeName);
  await page.getByTestId("pay-amount").click();
  await page.getByTestId("pay-amount").fill("40.00");
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo-ensaio.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-ensaio-cfund"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("payment-registered-notice")).toBeVisible();
  await expect(page.getByTestId("fx-not-applicable")).toContainText("Não se aplica");
  await expect(page.getByTestId("eligible-preselected")).toBeVisible();
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/BRL 0,00/i, { timeout: 10000 });

  await page.goto(`/customs/${created.processId}`);
  await expect(page.getByTestId("numerario-settlement-status")).toHaveText("Parcialmente pago");
  await page.getByTestId("numerario-register-payment").click();
  await page.getByTestId("pay-amount").click();
  await page.getByTestId("pay-amount").fill("60.00");
  await page.getByTestId("pay-doc").setInputFiles({
    name: "recibo-ensaio-2.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-ensaio-cfund-2"),
  });
  await page.getByTestId("save-payment").click();
  await expect(page.getByTestId("payment-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("allocate-btn").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payment-residual")).toContainText(/BRL 0,00/i, { timeout: 10000 });

  await page.goto(`/customs/${created.processId}`);
  await expect(page.getByTestId("numerario-settlement-status")).toHaveText("Pago");
  await expect(page.getByTestId("numerario-register-payment")).toHaveCount(0);

  await page.goto("/payables");
  await expect(page.getByTestId("ap-queue-page")).toBeVisible();
  await page.getByTestId("ap-filter-saldo").getByRole("button", { name: "Todos" }).click();
  await expect(page.getByTestId("ap-table")).toContainText(payeeName);
});
