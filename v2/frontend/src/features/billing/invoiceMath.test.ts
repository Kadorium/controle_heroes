import { describe, expect, it } from "vitest";
import { lineAmounts, previewPercentPayables, canIssueBilling } from "./invoiceMath";

describe("invoiceMath", () => {
  it("calculates NONE / UNIT / PERCENT", () => {
    expect(
      lineAmounts({
        quantity: "10",
        unit_price_gross: "100",
        discount_type: "NONE",
      }),
    ).toEqual({ gross: "1000.00", discount: "0.00", net: "1000.00" });

    expect(
      lineAmounts({
        quantity: "10",
        unit_price_gross: "100",
        discount_type: "PERCENT",
        discount_percent: "10",
      }),
    ).toEqual({ gross: "1000.00", discount: "100.00", net: "900.00" });

    expect(
      lineAmounts({
        quantity: "10",
        unit_price_gross: "100",
        discount_type: "UNIT_AMOUNT",
        discount_unit_amount: "5",
      }),
    ).toEqual({ gross: "1000.00", discount: "50.00", net: "950.00" });
  });

  it("leaves net null when discount incomplete", () => {
    expect(
      lineAmounts({
        quantity: "1",
        unit_price_gross: "10",
        discount_type: "",
      }).net,
    ).toBeNull();
  });

  it("preview residual on last scadenza", () => {
    const parts = previewPercentPayables(100, [33.33, 33.33, 33.34]);
    expect(parts.reduce((a, b) => a + Number(b), 0)).toBeCloseTo(100, 2);
  });

  it("permission gating", () => {
    expect(canIssueBilling({ role: "admin", permissions: [] })).toBe(true);
    expect(canIssueBilling({ role: "comprador", permissions: ["billing:issue"] })).toBe(true);
    expect(canIssueBilling({ role: "x", permissions: ["billing:read"] })).toBe(false);
  });
});
