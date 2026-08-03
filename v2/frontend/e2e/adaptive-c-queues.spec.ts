import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/adaptive-c/screenshots",
);

const VIEWPORTS = [
  { w: 1024, h: 768 },
  { w: 1366, h: 768 },
  { w: 1440, h: 900 },
  { w: 1920, h: 1080 },
] as const;

const QUEUES = [
  {
    path: "/orders",
    pageTestId: "orders-list-page",
    tableTestId: "orders-table",
    slug: "scr-003-orders",
    p0: ["Código", "Fornecedor", "Status", "Saldo"],
  },
  {
    path: "/invoices",
    pageTestId: "invoices-list",
    tableTestId: "invoices-table",
    slug: "scr-006-invoices",
    p0: ["Número", "Pedido", "Fornecedor", "Status", "Saldo"],
  },
  {
    path: "/payments",
    pageTestId: "payments-list",
    tableTestId: "payments-table",
    slug: "scr-010-payments",
    p0: ["Data", "Referência", "Fornecedor", "Residual", "Status"],
  },
] as const;

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();
  await expect(page.getByRole("navigation", { name: /módulos/i })).toBeVisible({
    timeout: 15000,
  });
}

/** Onda C — filas SCR-003/006/010 em colunas adaptativas. */
test("adaptive-C queues width matrix + C-010 Abrir", async ({ page }) => {
  mkdirSync(evidenceDir, { recursive: true });
  await page.setViewportSize({ width: 1366, height: 768 });
  await login(page);

  // Seed pagamento (lista pode estar vazia após prepare; C-010 precisa de linhas)
  const stamp = Date.now();
  await page.evaluate(async (supplierName) => {
    const sRes = await fetch("/api/suppliers", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: supplierName, country_code: "IT" }),
    });
    if (!sRes.ok) throw new Error(`supplier ${sRes.status}`);
    const s = (await sRes.json()) as { id: number };
    const pRes = await fetch("/api/payments", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        supplier_id: s.id,
        amount: "250.0000",
        currency: "EUR",
        payment_date: "2026-07-28",
        register_without_document: true,
        reason_code: "TEST_OVERRIDE",
      }),
    });
    if (!pRes.ok) throw new Error(`payment ${pRes.status} ${await pRes.text()}`);
  }, `Adaptive-C Supplier ${stamp}`);

  for (const q of QUEUES) {
    await page.goto(q.path);
    await expect(page.getByTestId(q.pageTestId)).toBeVisible({ timeout: 15000 });

    // Sem “Mais filtros” vazio (só primary)
    await expect(page.getByTestId("filter-bar-more-trigger")).toHaveCount(0);

    const empty = page.getByTestId("empty-state");
    if (await empty.isVisible().catch(() => false)) {
      // Pedidos/Faturas podem estar vazios se este spec rodar isolado — ainda captura shell
      await page.screenshot({
        path: path.join(evidenceDir, `${q.slug}-empty-1366.png`),
        fullPage: true,
      });
      continue;
    }

    await expect(page.getByTestId(q.tableTestId)).toBeVisible({ timeout: 15000 });

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.w, height: vp.h });
      await page.waitForTimeout(300);

      const snap = await page.evaluate((tableId) => {
        const table = document.querySelector(`[data-testid="${tableId}"]`) as HTMLElement | null;
        const shell = table?.closest(".queue-shell") as HTMLElement | null;
        const wrap = table?.closest(".operational-table-wrap") as HTMLElement | null;
        const headers = Array.from(
          document.querySelectorAll(`[data-testid="${tableId}"] thead th`),
        ).map((th) => (th.textContent || "").trim());
        const rows = Array.from(
          document.querySelectorAll(`[data-testid="${tableId}"] tbody tr`),
        );
        const firstCells = Array.from(
          document.querySelectorAll(`[data-testid="${tableId}"] tbody tr:first-child td`),
        ).slice(0, 5) as HTMLElement[];
        const p0Wrap = firstCells.some((td) => td.getBoundingClientRect().height > 52);
        const dashLinks = Array.from(
          document.querySelectorAll(`[data-testid="${tableId}"] tbody a`),
        ).filter((a) => (a.textContent || "").trim() === "—").length;
        return {
          layoutMode: shell?.getAttribute("data-layout") || "?",
          containerW: shell ? Math.round(shell.getBoundingClientRect().width) : -1,
          headers,
          tableCount: document.querySelectorAll(`[data-testid="${tableId}"]`).length,
          rowCount: rows.length,
          p0Wrap,
          dashLinks,
          overflow:
            wrap != null ? wrap.scrollWidth > wrap.clientWidth + 2 : false,
        };
      }, q.tableTestId);

      expect(snap.tableCount).toBe(1);
      expect(snap.p0Wrap).toBe(false);
      expect(snap.dashLinks).toBe(0);
      for (const h of q.p0) {
        expect(snap.headers).toContain(h);
      }

      if (q.slug === "scr-010-payments" && snap.rowCount > 0) {
        const abrir = page.getByTestId(q.tableTestId).getByRole("link", { name: /^Abrir$/i });
        await expect(abrir).toHaveCount(snap.rowCount);
        // Referência "—" não é link
        await expect(
          page.getByTestId(q.tableTestId).getByRole("link", { name: /^—$/ }),
        ).toHaveCount(0);
        // Sem coluna Moeda isolada
        expect(snap.headers).not.toContain("Moeda");
      }

      await page.screenshot({
        path: path.join(evidenceDir, `${q.slug}-${vp.w}.png`),
        fullPage: true,
      });
    }
  }
});
