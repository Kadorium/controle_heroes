import { describe, expect, it } from "vitest";
import type { OrderCentralModel } from "../../api";
import {
  computeOpSummary,
  EMPTY_ITEMS_FILTER,
  filterModels,
  modelLineValue,
  summarizeModels,
} from "./orderCentralItemsUtils";

function model(partial: Partial<OrderCentralModel> & Pick<OrderCentralModel, "importation_item_id">): OrderCentralModel {
  return {
    model_label: null,
    description: null,
    product_id: null,
    product_sku: null,
    supplier_sku: null,
    product_category: null,
    quantity_ordered: null,
    quantity_invoiced: null,
    quantity_shipped: null,
    quantity_nationalized: null,
    quantity_stocked: null,
    to_dispatch: null,
    price_listino: null,
    price_fattura: null,
    discount_unit: null,
    heroes_source: false,
    dispatch_needs_review: false,
    ...partial,
  };
}

describe("modelLineValue", () => {
  it("multiplica quantidade pedida pelo preço fattura", () => {
    expect(modelLineValue({ quantity_ordered: 10, price_fattura: "12.5" })).toBe("125");
  });

  it("retorna null quando falta qty ou preço", () => {
    expect(modelLineValue({ quantity_ordered: null, price_fattura: "10" })).toBeNull();
    expect(modelLineValue({ quantity_ordered: 5, price_fattura: null })).toBeNull();
  });
});

describe("summarizeModels", () => {
  it("soma quantidades e valores de linha", () => {
    const totals = summarizeModels([
      model({ importation_item_id: 1, quantity_ordered: 10, price_fattura: "12.5" }),
      model({ importation_item_id: 2, quantity_ordered: 5, price_fattura: "8" }),
    ]);
    expect(totals.qty).toBe(15);
    expect(totals.value).toBe("165");
  });
});

describe("computeOpSummary", () => {
  it("agrega cadeia operacional", () => {
    const summary = computeOpSummary([
      model({
        importation_item_id: 1,
        quantity_ordered: 100,
        quantity_invoiced: 80,
        quantity_shipped: 50,
        to_dispatch: 20,
      }),
      model({
        importation_item_id: 2,
        quantity_ordered: 50,
        quantity_invoiced: 50,
        quantity_shipped: 10,
        to_dispatch: 5,
      }),
    ]);
    expect(summary).toEqual({ ordered: 150, invoiced: 130, shipped: 60, toDispatch: 25 });
  });
});

describe("filterModels", () => {
  const rows = [
    model({
      importation_item_id: 1,
      model_label: "STARLIGHT",
      product_sku: "EP-01",
      supplier_sku: "IT-01",
      to_dispatch: 10,
      product_id: 1,
      dispatch_needs_review: false,
    }),
    model({
      importation_item_id: 2,
      model_label: "SHOW26",
      product_sku: null,
      supplier_sku: "IT-02",
      to_dispatch: 0,
      product_id: null,
      dispatch_needs_review: true,
    }),
  ];

  it("retorna todos quando filtro vazio", () => {
    expect(filterModels(rows, EMPTY_ITEMS_FILTER)).toHaveLength(2);
  });

  it("filtra por busca textual parcial", () => {
    const filtered = filterModels(rows, { ...EMPTY_ITEMS_FILTER, search: "star" });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].importation_item_id).toBe(1);
  });

  it("combina chips de filtro", () => {
    const filtered = filterModels(rows, {
      ...EMPTY_ITEMS_FILTER,
      unmapped: true,
      needsReview: true,
    });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].importation_item_id).toBe(2);
  });

  it("filtra a despachar", () => {
    const filtered = filterModels(rows, { ...EMPTY_ITEMS_FILTER, toDispatch: true });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].to_dispatch).toBe(10);
  });
});
