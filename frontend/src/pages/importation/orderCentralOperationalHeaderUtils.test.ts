import { describe, expect, it } from "vitest";
import type { OperationalHeader } from "../../api";
import {
  aggregateItemPreviewRows,
  buildItemPreviewRows,
  estimateItemPreviewRowCount,
  normalizeItemLabel,
  resolveFinance,
} from "./orderCentralOperationalHeaderUtils";

describe("normalizeItemLabel", () => {
  it("ignora hífen e case para agrupar SKUs equivalentes", () => {
    expect(normalizeItemLabel("SHOW-26")).toBe(normalizeItemLabel("SHOW26"));
    expect(normalizeItemLabel("Starlight")).toBe("STARLIGHT");
  });
});

describe("aggregateItemPreviewRows", () => {
  it("soma quantidades e valores de itens com o mesmo nome", () => {
    const merged = aggregateItemPreviewRows([
      { key: "1", label: "STARLIGHT", qty: 1000, unitPrice: "10", paid: "10000" },
      { key: "2", label: "STARLIGHT", qty: 1000, unitPrice: "10", paid: "10000" },
      { key: "3", label: "SHOW-26", qty: 1000, unitPrice: "50", paid: "50000" },
      { key: "4", label: "SHOW26", qty: 80, unitPrice: null, paid: null },
    ]);
    expect(merged).toHaveLength(2);
    const star = merged.find((r) => r.label === "STARLIGHT");
    expect(star?.qty).toBe(2000);
    expect(star?.paid).toBe("20000");
    const show = merged.find((r) => r.label.startsWith("SHOW"));
    expect(show?.qty).toBe(1080);
  });
});

describe("resolveFinance", () => {
  const baseHeader: OperationalHeader = {
    invoices_count: 1,
    invoices_settled_count: 1,
    totals_by_currency: null,
    total_invoiced: null,
    total_paid: "347500",
    open_balance: null,
    open_balance_brl_equivalent: null,
    next_due_date: null,
    overdue_count: 0,
    overdue_amount_foreign: null,
    next_etd: null,
    next_eta: null,
    active_modal: null,
    to_dispatch: null,
    quantity_ordered: null,
    supplier_credit_available: null,
    pending_actions_count: 0,
    settled_eur: "347500",
    settled_brl: null,
    fx_pnl: { label: "PnL", disclaimer: "", mark_rate: "6.10", pnl_realized_brl: null, pnl_planned_brl: null, pnl_unrealized_brl: null, pnl_total_brl: null },
  };

  it("usa versato e câmbio atual quando total da ordem não veio do backend", () => {
    const fin = resolveFinance(baseHeader, null, "397500");
    expect(fin.orderTotalEur).toBe("397500");
    expect(fin.orderTotalBrl).toBe(String(397500 * 6.1));
  });

  it("converte liquidado para BRL pelo câmbio atual quando não há BRL efetivo", () => {
    const fin = resolveFinance(baseHeader);
    expect(fin.settledBrl).toBe(String(347500 * 6.1));
  });
});

describe("estimateItemPreviewRowCount", () => {
  it("calcula quantas linhas cabem na altura do card", () => {
    expect(estimateItemPreviewRowCount(324, 24, 40, 22, 22)).toBeGreaterThan(5);
  });
});

describe("buildItemPreviewRows", () => {
  it("deduplica modelos repetidos pelo nome", () => {
    const rows = buildItemPreviewRows(
      [
        {
          importation_item_id: 1,
          quantity_ordered: 1000,
          model_label: "SHOW-26",
          acconto_amount: "50000",
          heroes_source: true,
          dispatch_needs_review: false,
        },
        {
          importation_item_id: 2,
          quantity_ordered: 80,
          model_label: "SHOW26",
          heroes_source: true,
          dispatch_needs_review: false,
        },
      ],
      undefined,
      undefined,
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].qty).toBe(1080);
  });
});
