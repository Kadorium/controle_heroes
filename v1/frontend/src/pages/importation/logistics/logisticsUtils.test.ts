import { describe, expect, it } from "vitest";
import { buildSkuRows, qtyCell, skuLabel } from "./logisticsUtils";
import type { OrderCentralModel, QuantityChain } from "../../../api";

describe("logisticsUtils", () => {
  const models: OrderCentralModel[] = [
    {
      importation_item_id: 1,
      product_id: 10,
      supplier_sku: "SKU-A",
      model_label: "Model A",
      quantity_ordered: 100,
      quantity_shipped: null,
      quantity_nationalized: null,
      quantity_stocked: null,
      quantity_invoiced: 80,
      to_dispatch: 50,
    },
  ];

  const chain: QuantityChain[] = [
    {
      importation_item_id: 1,
      quantity_ordered: 100,
      quantity_shipped: 50,
      quantity_nationalized: null,
      quantity_stocked: null,
      quantity_entreposto_balance: 10,
      quantity_entreposto_consumed: 2,
      difference_ordered_stocked: null,
    },
  ];

  it("buildSkuRows merges model and chain", () => {
    const rows = buildSkuRows(models, chain);
    expect(rows).toHaveLength(1);
    expect(rows[0].quantity_shipped).toBe(50);
    expect(rows[0].quantity_entreposto_balance).toBe(10);
    expect(rows[0].to_dispatch).toBe(50);
  });

  it("skuLabel prefers model_label", () => {
    expect(skuLabel(models[0])).toBe("Model A");
  });

  it("qtyCell shows dash for null", () => {
    expect(qtyCell(null)).toBe("—");
    expect(qtyCell(5)).toBe("5");
  });
});
