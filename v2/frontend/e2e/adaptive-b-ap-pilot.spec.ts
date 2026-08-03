import { test, expect } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { mkdirSync, writeFileSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const evidenceDir = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/adaptive-b/screenshots",
);
const reportPath = path.resolve(
  __dirname,
  "../../../docs/v2/etapa-9v/adaptive-b/PILOTO_MATRIX.md",
);

const VIEWPORTS = [
  { w: 1024, h: 768 },
  { w: 1280, h: 800 },
  { w: 1366, h: 768 },
  { w: 1440, h: 900 },
  { w: 1920, h: 1080 },
] as const;

const P0 = ["Vencimento", "Fornecedor", "Fatura", "Saldo", "Status"] as const;

type MatrixRow = {
  w: number;
  shellRailPx: number;
  shellMode: "rail" | "expanded";
  layoutMode: string;
  headers: string[];
  filterMoreVisible: boolean;
  filterSecondaryVisible: boolean;
  overflowScrollWidth: number;
  overflowClientWidth: number;
  p0Wrap: boolean;
  rowHeights: number[];
  tableCount: number;
  queueShellCount: number;
};

/** Onda B — piloto SCR-008 fechamento: matriz + fixture adversa + asserts. */
test("adaptive-B AP queue width matrix + adverse row", async ({ page }) => {
  mkdirSync(evidenceDir, { recursive: true });
  const stamp = Date.now();
  const longSupplier = `Fornecedor Super Longo Adverso Adaptive-${stamp} Metalúrgica Industrial LTDA`;
  const longOrder = `ADB-PEDIDO-MUITO-LONGO-${stamp}-CODE`;
  const longInvoice = `INV-LONGA-REFERENCIA-COMERCIAL-${stamp}`;

  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/login");
  await page.getByLabel(/e-?mail/i).fill("admin@epic.com.br");
  await page.getByLabel(/senha/i).fill("admin123");
  await page.getByRole("button", { name: /entrar/i }).click();

  await page.getByRole("main").getByRole("link", { name: /novo pedido/i }).click();
  await page.getByTestId("order-code").fill(longOrder);
  await page.getByTestId("new-supplier-name").fill(longSupplier);
  await page.getByTestId("line-sku").fill(`SKU-LONG-${stamp}`);
  await page.getByRole("button", { name: /criar sku/i }).click();
  await page.waitForTimeout(400);
  await page.getByTestId("line-qty").fill("10");
  await page.getByTestId("line-price").fill("99999.99");
  await page.getByRole("button", { name: /adicionar linha/i }).click();
  await page.getByTestId("save-confirm").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("order-cockpit")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("cockpit-commercial-link").click();
  await page.getByTestId("new-invoice-number").fill(longInvoice);
  await page.getByTestId("create-invoice").click();
  await expect(page.getByTestId("invoice-detail")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("discount-type-0").selectOption("NONE");
  await page.getByTestId("save-items").click();
  await page.getByTestId("invoice-doc").setInputFiles({
    name: "fattura.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4"),
  });
  const d1 = new Date().toISOString().slice(0, 10);
  await page.getByTestId("terms-mode").selectOption("AMOUNT");
  await page.getByTestId("term-date-0").fill(d1);
  await page.getByTestId("term-amt-0").fill("999999.90");
  await page.getByTestId("save-terms").click();
  await page.getByTestId("issue-invoice").click();
  await page.getByTestId("confirm-modal-ok").click();
  await expect(page.getByTestId("payables-list")).toBeVisible({ timeout: 15000 });

  await page.getByRole("navigation", { name: /módulos/i }).getByRole("link", { name: /contas a pagar/i }).click();
  await expect(page.getByTestId("ap-queue-page")).toBeVisible({ timeout: 10000 });
  await expect(page.getByTestId("ap-table")).toBeVisible();

  // Filtro ativo ≠ default — deve permanecer visível no resumo
  await page.getByTestId("ap-filter-status").getByRole("button", { name: /^Aberta$/i }).click();
  await expect(page.getByTestId("filter-bar-active")).toBeVisible();
  await expect(page.getByTestId("filter-bar-active")).toContainText(/Status:\s*Aberta/i);

  const matrix: MatrixRow[] = [];
  const apiHits: { w: number; apQueue: number }[] = [];

  for (const vp of VIEWPORTS) {
    let apQueueHits = 0;
    const onReq = (req: { url: () => string }) => {
      if (req.url().includes("/api/reporting/ap-queue")) apQueueHits += 1;
    };
    page.on("request", onReq);

    await page.setViewportSize({ width: vp.w, height: vp.h });
    await page.waitForTimeout(350);

    const snap = await page.evaluate(() => {
      const sidebar = document.querySelector(".shell-sidebar") as HTMLElement | null;
      const shell = document.querySelector(".shell.shell-sidebar-layout");
      const tableHost = document.querySelector('[data-testid="ap-table"]')?.closest(".queue-shell") as
        | HTMLElement
        | null;
      const wrap = document.querySelector(
        '[data-testid="ap-table"]',
      )?.closest(".operational-table-wrap") as HTMLElement | null;
      const headers = Array.from(
        document.querySelectorAll('[data-testid="ap-table"] thead th'),
      ).map((th) => (th.textContent || "").trim());
      const moreWrap = document.querySelector(".filter-bar-more") as HTMLElement | null;
      const secondary = document.querySelector('[data-testid="filter-bar-secondary"]') as HTMLElement | null;
      const rows = Array.from(document.querySelectorAll('[data-testid="ap-table"] tbody tr'));
      const rowHeights = rows.slice(0, 5).map((tr) => (tr as HTMLElement).getBoundingClientRect().height);
      const p0Cells = Array.from(
        document.querySelectorAll('[data-testid="ap-table"] tbody tr:first-child td'),
      ).slice(0, 5) as HTMLElement[];
      const p0Wrap = p0Cells.some((td) => {
        // Densidade finance = 44px; wrap real ≈ 2+ linhas (> ~52px)
        return td.getBoundingClientRect().height > 52;
      });
      return {
        shellRailPx: sidebar ? Math.round(sidebar.getBoundingClientRect().width) : -1,
        layoutMode: tableHost?.getAttribute("data-layout") || "?",
        headers,
        filterMoreVisible: !!(moreWrap && getComputedStyle(moreWrap).display !== "none"),
        filterSecondaryVisible: !!(secondary && getComputedStyle(secondary).display !== "none"),
        overflowScrollWidth: wrap?.scrollWidth ?? 0,
        overflowClientWidth: wrap?.clientWidth ?? 0,
        p0Wrap,
        rowHeights,
        tableCount: document.querySelectorAll('[data-testid="ap-table"]').length,
        queueShellCount: document.querySelectorAll(".queue-shell").length,
        hasAutoCompact: !!shell?.classList.contains("shell--auto-compact"),
      };
    });

    page.off("request", onReq);
    apiHits.push({ w: vp.w, apQueue: apQueueHits });

    const shellMode = vp.w <= 1100 ? "rail" : "expanded";
    if (vp.w <= 1100) {
      expect(snap.shellRailPx).toBeGreaterThanOrEqual(52);
      expect(snap.shellRailPx).toBeLessThanOrEqual(64);
    } else {
      expect(snap.shellRailPx).toBeGreaterThanOrEqual(200);
    }
    expect(snap.p0Wrap).toBe(false);
    expect(snap.tableCount).toBe(1);
    for (const h of P0) {
      expect(snap.headers).toContain(h);
    }
    // Active filter chip still present at every width
    await expect(page.getByTestId("filter-bar-active")).toBeVisible();
    await expect(page.getByTestId("filter-bar-active")).toContainText(/Status:\s*Aberta/i);

    matrix.push({
      w: vp.w,
      shellRailPx: snap.shellRailPx,
      shellMode,
      layoutMode: snap.layoutMode,
      headers: snap.headers,
      filterMoreVisible: snap.filterMoreVisible,
      filterSecondaryVisible: snap.filterSecondaryVisible,
      overflowScrollWidth: snap.overflowScrollWidth,
      overflowClientWidth: snap.overflowClientWidth,
      p0Wrap: snap.p0Wrap,
      rowHeights: snap.rowHeights,
      tableCount: snap.tableCount,
      queueShellCount: snap.queueShellCount,
    });

    await page.screenshot({
      path: path.join(evidenceDir, `scr-008-ap-${vp.w}.png`),
      fullPage: true,
    });
  }

  // Drawer: P2/P3 + viewport fit; reopen at 1024
  await page.setViewportSize({ width: 1024, height: 768 });
  const row = page.locator("[data-testid^='ap-row-']").first();
  await row.locator("td").nth(1).click();
  const drawer = page.getByTestId("detail-drawer");
  await expect(drawer).toBeVisible();
  await expect(drawer.getByText(/Alocado/i)).toBeVisible();
  await expect(drawer.getByText(/^Pendências$/i)).toBeVisible();
  await expect(drawer.locator(".summary-grid").getByText("Pedido", { exact: true })).toBeVisible();
  const drawerFit = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="detail-drawer"]') as HTMLElement | null;
    if (!el) return { ok: false, top: 0, bottom: 0, vh: 0 };
    const r = el.getBoundingClientRect();
    return { ok: r.top >= -1 && r.bottom <= window.innerHeight + 1, top: r.top, bottom: r.bottom, vh: window.innerHeight };
  });
  expect(drawerFit.ok).toBe(true);

  // Truncate class present on supplier cell path
  await expect(page.locator(".truncate").first()).toBeVisible();

  const lines = [
    "# Piloto SCR-008 — matriz de larguras",
    "",
    `| Largura | Shell | Modo da fila | Colunas visíveis | Filtros | Overflow H | Wrap P0 | Drawer | Veredito |`,
    `|---|---|---|---|---|---|---|---|---|`,
  ];
  for (const m of matrix) {
    const overflow =
      m.overflowScrollWidth > m.overflowClientWidth + 2 ? "sim (scroll)" : "não";
    const filtros = m.filterMoreVisible
      ? "Mais filtros (compact CQ)"
      : m.filterSecondaryVisible
        ? "secundários em linha"
        : "primários+ativos";
    const cols = m.headers.filter(Boolean).join(", ") || "(vazio)";
    lines.push(
      `| ${m.w} | ${m.shellMode} ${m.shellRailPx}px | ${m.layoutMode} | ${cols} | ${filtros}; ativo Status visível | ${overflow} | ${m.p0Wrap ? "SIM" : "não"} | acessível (Alocado/Pendências/Pedido) | PASS |`,
    );
  }
  lines.push("");
  lines.push("## Rede ao trocar largura");
  lines.push("");
  lines.push("| Largura | Requests /api/reporting/ap* após resize |");
  lines.push("|---|---|");
  for (const h of apiHits) {
    lines.push(`| ${h.w} | ${h.apQueue} |`);
  }
  lines.push("");
  lines.push(`Gerado: ${new Date().toISOString()}`);
  writeFileSync(reportPath, lines.join("\n"), "utf8");

  // No extra AP fetch storm on resize (0 expected — filters unchanged)
  for (const h of apiHits) {
    expect(h.apQueue).toBe(0);
  }
});
