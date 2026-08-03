/**
 * I5-2 E2E — Doganale versionada via UI no detalhe do processo.
 */
import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const shotDir = path.resolve(__dirname, "../../../docs/v2/etapa-j5/screenshots");

type Json = Record<string, unknown>;

async function api(
  page: import("@playwright/test").Page,
  method: string,
  pathName: string,
  body?: unknown,
): Promise<{ status: number; body: Json }> {
  return page.evaluate(
    async ({ method, pathName, body }) => {
      const opts: RequestInit = { method, credentials: "include" };
      if (body !== undefined) {
        opts.headers = { "Content-Type": "application/json" };
        opts.body = JSON.stringify(body);
      }
      const r = await fetch(pathName, opts);
      const text = await r.text();
      let parsed: unknown = text;
      try {
        parsed = JSON.parse(text);
      } catch {
        /* raw */
      }
      return { status: r.status, body: parsed as Json };
    },
    { method, pathName, body },
  );
}

function expectOk(status: number) {
  expect(status).toBeGreaterThanOrEqual(200);
  expect(status).toBeLessThan(300);
}

test("I5-2 doganale UI journey", async ({ page }) => {
  test.setTimeout(180_000);
  fs.mkdirSync(shotDir, { recursive: true });

  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/login"));

  const tag = Date.now().toString(36);
  let r = await api(page, "POST", "/api/import-processes", {
    external_reference: `DOG-${tag}`,
  });
  expectOk(r.status);
  const process = r.body as { id: number; code: string };

  await page.goto(`/customs/${process.id}`);
  await expect(page.getByTestId("customs-detail-page")).toBeVisible();
  await expect(page.getByTestId("customs-doganale-panel")).toBeVisible();

  await page.getByTestId("doganale-create-version").click();
  await expect(page.getByTestId("doganale-history")).toContainText("v1");

  await page.getByTestId("doganale-ncm").fill("84713012");
  await page.getByTestId("doganale-desc").fill(`Notebook ${tag}`);
  await page.getByTestId("doganale-qty").fill("10");
  await page.getByTestId("doganale-price").fill("100");
  await page.getByTestId("doganale-save-lines").click();
  await page.getByTestId("doganale-activate").click();
  await expect(page.getByTestId("doganale-current")).toContainText("v1 (ACTIVE)");

  await page.screenshot({
    path: path.join(shotDir, "i5-2-doganale-v1-1366.png"),
    fullPage: true,
  });

  await page.getByTestId("doganale-supersede").click();
  await expect(page.getByTestId("doganale-history")).toContainText("v2");
  await page.getByTestId("doganale-desc").fill(`Notebook retificado ${tag}`);
  await page.getByTestId("doganale-qty").fill("9");
  await page.getByTestId("doganale-save-lines").click();
  await page.getByTestId("doganale-activate").click();
  await expect(page.getByTestId("doganale-current")).toContainText("v2 (ACTIVE)");
  await expect(page.getByTestId("doganale-history")).toContainText("SUPERSEDED");

  await page.getByTestId("doganale-div-msg").fill(`Qty divergente ${tag}`);
  await page.getByTestId("doganale-add-divergence").click();
  await expect(page.getByTestId("doganale-divergences")).toContainText("Qty divergente");

  await page.screenshot({
    path: path.join(shotDir, "i5-2-doganale-v2-history-1366.png"),
    fullPage: true,
  });
});
