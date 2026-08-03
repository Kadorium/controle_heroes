/**
 * J#4 Logistics — domain + UI acceptance.
 * Gate: npm run e2e:logistics
 */
import { test, expect } from "@playwright/test";

type Json = Record<string, unknown>;

async function api(
  page: import("@playwright/test").Page,
  method: string,
  path: string,
  body?: unknown,
): Promise<{ status: number; body: Json | Json[] | string }> {
  return page.evaluate(
    async ({ method, path, body }) => {
      const opts: RequestInit = { method, credentials: "include" };
      if (body !== undefined) {
        opts.headers = { "Content-Type": "application/json" };
        opts.body = JSON.stringify(body);
      }
      const r = await fetch(path, opts);
      const text = await r.text();
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        /* raw */
      }
      return { status: r.status, body: parsed as Json };
    },
    { method, path, body },
  );
}

function expectOk(status: number) {
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThan(300);
}

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("link", { name: /pedidos/i }).first()).toBeVisible({
    timeout: 15000,
  });
}

async function createConfirmedOrder(
  page: import("@playwright/test").Page,
  tag: string,
  qty = "20",
) {
  const supplierRes = await api(page, "POST", "/api/suppliers", {
    name: `Sup ${tag}`,
    country_code: "IT",
  });
  expectOk(supplierRes.status);
  const supplier = supplierRes.body as Json;

  const productRes = await api(page, "POST", "/api/products", {
    sku: `SKU-${tag}`,
    description: `Product ${tag}`,
  });
  expectOk(productRes.status);
  const product = productRes.body as Json;

  let orderRes = await api(page, "POST", "/api/orders", {
    code: tag,
    supplier_id: supplier.id,
    currency: "EUR",
    external_ref: `ORDINE-${tag}`,
  });
  expectOk(orderRes.status);
  let order = orderRes.body as Json;

  orderRes = await api(page, "POST", `/api/orders/${order.id}/items`, {
    expected_version: order.version,
    product_id: product.id,
    quantity: qty,
    unit_price: "10",
  });
  expectOk(orderRes.status);
  order = orderRes.body as Json;

  orderRes = await api(page, "POST", `/api/orders/${order.id}/confirm`, {
    expected_version: order.version,
  });
  expectOk(orderRes.status);
  return orderRes.body as Json;
}

test.describe("J#4 logistics", () => {
  test("happy path multi-order packages refs advance audit", async ({ page }) => {
    test.setTimeout(180_000);
    await login(page);
    const tag = `J4-${Date.now()}`;
    const o1 = await createConfirmedOrder(page, `${tag}-A`, "20");
    const o2 = await createConfirmedOrder(page, `${tag}-B`, "15");
    const item1 = (o1.items as Json[])[0];
    const item2 = (o2.items as Json[])[0];

    const providerRes = await api(page, "POST", "/api/logistics-providers", {
      legal_name: `Provider ${tag} LTDA`,
      trade_name: `Carrier ${tag}`,
      provider_type: "TRANSPORTADOR",
      active: true,
    });
    expectOk(providerRes.status);
    const provider = providerRes.body as Json;

    let shRes = await api(page, "POST", "/api/shipments", {
      modal: "SEA",
      logistics_provider_id: provider.id,
    });
    expectOk(shRes.status);
    let sh = shRes.body as Json;
    expect(sh.carrier_name_snapshot).toBe(`Carrier ${tag}`);
    expect(sh.logistics_provider_id).toBe(provider.id);

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/items`, {
      expected_version: sh.version,
      order_item_id: item1.id,
      quantity: "5",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/items`, {
      expected_version: sh.version,
      order_item_id: item2.id,
      quantity: "3",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;
    expect((sh.items as Json[]).length).toBe(2);

    for (const [count, net, L] of [
      [10, "2", "40"],
      [20, "3", "50"],
      [5, "1.5", "30"],
    ] as const) {
      shRes = await api(page, "POST", `/api/shipments/${sh.id}/packages`, {
        expected_version: sh.version,
        package_type: "CARTON",
        package_count: count,
        net_weight_kg: net,
        length: L,
        width: "40",
        height: "30",
        dimension_unit: "CM",
      });
      expectOk(shRes.status);
      sh = shRes.body as Json;
    }

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/packages`, {
      expected_version: sh.version,
      package_type: "PALLET",
      package_count: 1,
      packaging_ncm: "48191000",
      net_weight_kg: "12",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;

    for (let i = 1; i <= 20; i++) {
      shRes = await api(page, "POST", `/api/shipments/${sh.id}/packages`, {
        expected_version: sh.version,
        package_type: "PALLET",
        package_count: 1,
        external_package_no: String(i),
        gross_weight_kg: "100",
      });
      expectOk(shRes.status);
      sh = shRes.body as Json;
    }

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/references`, {
      expected_version: sh.version,
      reference_type: "DDT",
      reference_value: "DDT-371",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;
    shRes = await api(page, "POST", `/api/shipments/${sh.id}/references`, {
      expected_version: sh.version,
      reference_type: "BL",
      reference_value: "HKSTS26054756",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;

    const sh2Res = await api(page, "POST", "/api/shipments", {});
    expectOk(sh2Res.status);
    const sh2 = sh2Res.body as Json;
    const over2 = await api(page, "POST", `/api/shipments/${sh2.id}/items`, {
      expected_version: sh2.version,
      order_item_id: item1.id,
      quantity: "20",
    });
    expect(over2.status).toBe(409);

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/advance`, {
      expected_version: sh.version,
      event_date: "2026-07-01",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;
    expect(sh.status).toBe("BOOKED");

    const blocked = await api(page, "POST", `/api/shipments/${sh.id}/packages`, {
      expected_version: sh.version,
      package_type: "BOX",
      package_count: 1,
    });
    expect(blocked.status).toBe(409);

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/advance`, {
      expected_version: sh.version,
      event_date: "2026-07-10",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;
    expect(sh.status).toBe("IN_TRANSIT");
    expect(sh.actual_departure).toBe("2026-07-10");

    shRes = await api(page, "POST", `/api/shipments/${sh.id}/advance`, {
      expected_version: sh.version,
      event_date: "2026-07-20",
    });
    expectOk(shRes.status);
    sh = shRes.body as Json;
    expect(sh.status).toBe("ARRIVED");
    expect(sh.actual_arrival).toBe("2026-07-20");

    const audit = await api(
      page,
      "GET",
      `/api/audit?entity_type=shipment&entity_id=${sh.id}`,
    );
    expectOk(audit.status);
    expect(Array.isArray(audit.body)).toBe(true);
    expect((audit.body as Json[]).length).toBeGreaterThan(0);

    await page.goto(`/shipments/${sh.id}`);
    await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: new RegExp(String(sh.code)) })).toBeVisible();
  });

  test("UI create shipment with modal and provider", async ({ page }) => {
    test.setTimeout(120_000);
    await login(page);
    const tag = `UX1-${Date.now()}`;

    await page.goto("/logistics-providers");
    await expect(page.getByTestId("logistics-providers-page")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("provider-legal-name").fill(`UX Provider ${tag}`);
    await page.getByTestId("provider-trade-name").fill(`UX Trade ${tag}`);
    await page.getByTestId("provider-type").selectOption("TRANSPORTADOR");
    await page.getByTestId("provider-create-submit").click();
    await expect(page.getByTestId("providers-table")).toContainText(`UX Trade ${tag}`);

    await page.goto("/shipments/new");
    await expect(page.getByTestId("shipment-create-page")).toBeVisible({ timeout: 15000 });
    await expect(
      page.getByText(/Cadastre os dados básicos/i),
    ).toBeVisible();
    await page.getByTestId("shipment-modal").selectOption("SEA");
    const providerSelect = page.getByTestId("shipment-provider");
    await expect(providerSelect).toBeVisible();
    const options = providerSelect.locator("option");
    const count = await options.count();
    if (count > 2) {
      await providerSelect.selectOption({ label: `UX Trade ${tag}` });
    }
    await page.getByTestId("shipment-create-submit").click();
    await expect(page.getByTestId("shipment-detail")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("detail-modal")).toHaveValue("SEA");
  });

  test("delete empty planned + list", async ({ page }) => {
    await login(page);
    const shRes = await api(page, "POST", "/api/shipments", {});
    expectOk(shRes.status);
    const sh = shRes.body as Json;
    const del = await api(
      page,
      "DELETE",
      `/api/shipments/${sh.id}?expected_version=${sh.version}`,
    );
    expect(del.status).toBe(204);

    await page.goto("/shipments?status=PLANNED");
    await expect(page.getByTestId("shipments-list")).toBeVisible({ timeout: 15000 });
  });
});
