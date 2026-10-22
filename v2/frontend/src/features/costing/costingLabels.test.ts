import { describe, expect, it } from "vitest";
import { componentTypeLabel, expenseCategoryLabel, allocationMethodLabel } from "./costingLabels";

describe("costingLabels", () => {
  it("traduz categorias e métodos", () => {
    expect(expenseCategoryLabel("OUTRAS")).toBe("Outras");
    expect(allocationMethodLabel("VALUE")).toBe("Valor da mercadoria");
    expect(componentTypeLabel("EXPENSE_COSTING_OUTRAS")).toMatch(/Despesa/);
  });
});
