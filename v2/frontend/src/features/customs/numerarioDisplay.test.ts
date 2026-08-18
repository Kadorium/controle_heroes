import { describe, expect, it } from "vitest";
import { numerarioDisplayTotals, sumAmountsWire } from "./numerarioDisplay";

describe("numerarioDisplayTotals", () => {
  it("não mistura bases FOB/CIF no total comparável ao declarado", () => {
    const t = numerarioDisplayTotals({
      declared_total: "1425554.64",
      value_bases: [
        { amount: "288195.20", currency: "EUR" },
        { amount: "3164324.24", currency: "BRL" },
      ],
      tax_lines: [
        { amount: "343800.00", currency: "BRL" },
        { amount: "253500.00", currency: "BRL" },
      ],
      expense_lines: [{ amount: "2000.00", currency: "BRL" }],
    });
    expect(t.obligationWire).toBe("599300.00");
    expect(t.declaredWire).toBe("1425554.64");
    expect(t.basesMixedCurrency).toBe(true);
    expect(Number(t.obligationWire)).toBeLessThan(Number("4878074.08"));
  });

  it("soma só linhas com amount (vazio não entra)", () => {
    expect(sumAmountsWire([{ amount: "10" }, { amount: null }, { amount: "2.5" }])).toBe("12.50");
  });
});
