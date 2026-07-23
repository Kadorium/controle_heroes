import { describe, expect, it } from "vitest";
import { canWriteOrders, deriveLineTotal, summarizeLines } from "./orderTotals";

describe("orderTotals", () => {
  it("keeps empty price as null total", () => {
    expect(deriveLineTotal("2", null)).toBeNull();
    expect(deriveLineTotal("2", "")).toBeNull();
  });

  it("marks commercial total incomplete when any line unpriced", () => {
    const t = summarizeLines([
      { quantity: "2", unit_price: "10" },
      { quantity: "1", unit_price: null },
    ]);
    expect(t.unpriced_item_count).toBe(1);
    expect(t.commercial_total).toBeNull();
    expect(t.priced_subtotal).toBe("20.0000");
  });

  it("gates write permission", () => {
    expect(canWriteOrders({ role: "admin", permissions: [] })).toBe(true);
    expect(canWriteOrders({ role: "comprador", permissions: ["orders:read"] })).toBe(false);
    expect(canWriteOrders({ role: "comprador", permissions: ["orders:write"] })).toBe(true);
  });
});
