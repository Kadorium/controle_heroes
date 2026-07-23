import { test, expect } from "@playwright/test";

test("Inc-1 full walkthrough", async ({ page, request }) => {
  const code = `WT-${Date.now()}`;
  const sku = `SKU-${code}`;

  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /ordens/i })).toBeVisible({ timeout: 15000 });

  await page.getByRole("main").getByRole("link", { name: /nova ordem/i }).click();
  await page.getByTestId("order-code").fill(code);
  await page.getByTestId("new-supplier-name").fill(`Forn ${code}`);
  await page.getByTestId("line-sku").fill(sku);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(500);
  await page.getByTestId("line-qty").fill("2");
  await page.getByTestId("line-price").fill("10.00");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await expect(page.getByTestId("commercial-total")).toContainText("20.0000");

  await page.getByTestId("line-sku").fill(sku);
  await page.getByTestId("line-qty").fill("1");
  await page.getByTestId("line-price").fill("");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await expect(page.getByTestId("commercial-total")).toContainText(/incompleto/i);

  await page.getByTestId("save-draft").click();
  await expect(page.getByTestId("order-detail")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("detail-commercial-total")).toContainText(/incompleto/i);

  const cookies = await page.context().cookies();
  const cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join("; ");
  const orderId = Number(page.url().split("/").pop());

  const up = await request.post("http://127.0.0.1:8081/api/documents", {
    headers: { Cookie: cookieHeader },
    multipart: {
      file: { name: "nota.txt", mimeType: "text/plain", buffer: Buffer.from("hello") },
      entity_type: "order",
      entity_id: String(orderId),
    },
  });
  expect(up.ok()).toBeTruthy();
  await page.getByRole("button", { name: /atualizar/i }).click();
  await expect(page.getByText("nota.txt")).toBeVisible();

  // Confirm path on a fully priced order
  await page.goto("/orders/new");
  const code2 = `${code}-B`;
  await page.getByTestId("order-code").fill(code2);
  await page.getByTestId("new-supplier-name").fill(`Forn ${code2}`);
  await page.getByTestId("line-sku").fill(sku);
  await page.getByTestId("line-qty").fill("1");
  await page.getByTestId("line-price").fill("5");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await expect(page.getByTestId("readonly-banner")).toBeVisible({ timeout: 15000 });
  await expect(page.getByTestId("confirm-order")).toHaveCount(0);

  await page.getByTestId("cancel-reason").fill("ORDER_CANCEL_WT");
  await page.getByTestId("cancel-order").click();
  await expect(page.getByTestId("readonly-banner")).toContainText(/CANCELLED/i, { timeout: 10000 });

  const id2 = Number(page.url().split("/").pop());
  await page.getByRole("link", { name: /fila/i }).click();
  await expect(page.getByRole("link", { name: code2 })).toBeVisible();

  const audit2 = await request.get(
    `http://127.0.0.1:8081/api/audit?entity_type=order&entity_id=${id2}`,
    { headers: { Cookie: cookieHeader } },
  );
  expect(audit2.ok()).toBeTruthy();
  const actions = (await audit2.json()).map((e: { action: string }) => e.action);
  expect(actions).toEqual(expect.arrayContaining(["create", "confirm", "cancel"]));
});
