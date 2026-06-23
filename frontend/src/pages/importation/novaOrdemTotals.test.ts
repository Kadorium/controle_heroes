import { describe, expect, it } from "vitest";
import { aggregateTotals, lineTotals, parseDecimalInput } from "./novaOrdemTotals";

describe("novaOrdemTotals", () => {
  it("parseDecimalInput: vazio → null (nunca zero implícito)", () => {
    expect(parseDecimalInput("")).toBeNull();
    expect(parseDecimalInput("   ")).toBeNull();
  });

  it("parseDecimalInput: aceita vírgula pt-BR", () => {
    expect(parseDecimalInput("12,50")).toBe(12.5);
  });

  it("lineTotals: linha incompleta → subtotal null", () => {
    expect(lineTotals({ quantity_ordered: "10", unit_price_foreign: "", discount_amount_foreign: "" }).subtotal).toBeNull();
  });

  it("lineTotals: 10 × 12,50 = 125", () => {
    const lt = lineTotals({ quantity_ordered: "10", unit_price_foreign: "12.50", discount_amount_foreign: "" });
    expect(lt.subtotal).toBe(125);
    expect(lt.net).toBe(125);
  });

  it("aggregateTotals: sem linhas completas → gross null", () => {
    expect(aggregateTotals([{ quantity_ordered: "", unit_price_foreign: "", discount_amount_foreign: "" }]).gross).toBeNull();
  });
});
