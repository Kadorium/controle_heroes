import { test, expect } from "@playwright/test";
import { createHash } from "node:crypto";
import { pointer, type DemoManifest } from "../src/features/demo/demoManifest";

// Optional handoff window, using the authorized existing runner. No reset/seed.
test.skip(process.env.DEMO_PRESENTER !== "true", "Only launch explicitly for the presenter");
test.use({ launchOptions: { args: ["--start-maximized"] } });
test("leave the verified presentation runtime open", async ({ browser }, testInfo) => {
  test.setTimeout(0);
  const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8082";
  const url = new URL(baseURL);
  expect(["127.0.0.1", "localhost"]).toContain(url.hostname);
  expect(url.port).toBe("8082");
  // Explicit context: do not inherit Desktop Chrome's viewport/deviceScaleFactor.
  // Deterministic test projects keep their existing emulation unchanged.
  const context = await browser.newContext({ baseURL, viewport: null, deviceScaleFactor: undefined, isMobile: false });
  const page = await context.newPage();
  try {
  const health = await (await page.request.get("/api/health")).json();
  expect(health.logical_database).toBe("epic_v2_test"); expect(health.app_env).toBe("test");
  expect(health.schema_ok).toBe(true);
  await page.goto("/login");
  await page.getByRole("button", { name: /acesso rápido.*admin/i }).click();
  await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-demo-ready", "true");
  await expect(page.getByTestId("demo-start")).toBeVisible();
  expect((await (await page.request.get("/api/auth/me")).json()).role).toBe("admin");
  const manifest = await (await page.request.get("/assets/demo-manifest.json")).json() as DemoManifest;
  expect(manifest.logical_database).toBe("epic_v2_test");
  expect(manifest.schema_version).toBe(1);
  expect(manifest.checks.length).toBeGreaterThanOrEqual(10);
  for (const check of manifest.checks) {
    expect(check.path).toMatch(/^\/api\/(?:(orders|invoices|payments|shipments|import-processes|inventory|costing)(\/[\w/-]+)?|reporting\/stock-explorer\?product_id=\d+)$/);
    const response = await page.request.get(check.path); expect(response.ok()).toBe(true);
    const actual = await response.json();
    for (const [key, value] of Object.entries(check.fields)) expect(pointer(actual, key)).toEqual(value);
  }
  for (const doc of manifest.documents) {
    expect(doc.url).toBe(`/api/documents/${doc.id}/content`);
    const response = await page.request.get(doc.url); expect(response.ok()).toBe(true);
    expect(createHash("sha256").update(await response.body()).digest("hex")).toBe(doc.sha256);
  }
  if (process.env.DEMO_PRESENTER_VERIFY === "true") {
    for (const route of ["/dashboard", "/orders/new"]) {
      await page.goto(route);
      if (route === "/dashboard") await expect(page.getByTestId("dashboard-page")).toHaveAttribute("data-demo-ready", "true");
      else await expect(page.getByRole("heading", { name: "Novo pedido", exact: true })).toBeVisible();
      const dimensions = await page.evaluate(() => ({
        inner: [innerWidth, innerHeight], outer: [outerWidth, outerHeight], dpr: devicePixelRatio,
        client: [document.documentElement.clientWidth, document.documentElement.clientHeight],
        visualViewport: { width: visualViewport?.width, height: visualViewport?.height, scale: visualViewport?.scale },
        shell: document.querySelector(".shell")?.getBoundingClientRect().toJSON(),
        sidebar: document.querySelector(".shell-sidebar")?.getBoundingClientRect().toJSON(),
      }));
      expect(page.viewportSize()).toBeNull();
      await testInfo.attach(route.replaceAll("/", "_") + "-native.json", { body: JSON.stringify(dimensions, null, 2), contentType: "application/json" });
      await page.screenshot({ path: testInfo.outputPath(route.replaceAll("/", "_") + "-viewport.png") });
      console.log("NATIVE_VIEWPORT", route, JSON.stringify(dimensions));
    }
    return;
  }
  console.log("PRESENTATION_READY: " + baseURL + "; admin; manifest/documents verified; native viewport; tour not started. Close this runner window to finish.");
  await page.waitForEvent("close", { timeout: 0 });
  } finally { await context.close(); }
});
