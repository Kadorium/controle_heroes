import { describe, expect, it } from "vitest";
import type { DocumentDetail, PreviewCommitOut } from "../ingestion/ingestionApi";
import { isOrdineDocType, mapOrdinePreviewToForm } from "./mapOrdinePreviewToForm";

function field(key: string, value: string) {
  return {
    id: 1,
    document_id: 1,
    section_id: 1,
    field_key: key,
    value_type: "string",
    raw_value: value,
    normalized_value: value,
    corrected_value: null,
    effective_value: value,
    locator_json: null,
    provenance_json: null,
    review_status: "DRAFT",
    version: 1,
  };
}

function row(index: number, sku: string, description: string, qty: string, price: string) {
  return {
    id: index,
    document_id: 1,
    section_id: 1,
    row_index: index,
    row_key: `r${index}`,
    cells_json: JSON.stringify({
      sku: { raw: sku, normalized: sku },
      description: { raw: description, normalized: description },
      quantity: { raw: qty, normalized: qty },
      unit_price: { raw: price, normalized: price },
      unit: { raw: "PZ", normalized: "PZ" },
    }),
    review_status: "DRAFT",
    version: 1,
  };
}

const doc589 = {
  id: 9,
  occurrence_id: 3,
  batch_id: 1,
  document_set_id: null,
  doc_type: "ORDINE_COMPRA",
  adapter_id: "ordine_heroes_v1",
  adapter_version: "1",
  ir_schema_version: "1",
  review_status: "READY",
  version: 2,
  locked_by_actor_id: null,
  locked_at: null,
  created_by_actor_id: null,
  created_at: null,
  updated_at: null,
  open_issue_count: 0,
  fields: [
    field("order_number", "589"),
    field("order_date", "2026-06-04"),
    field("currency", "EUR"),
    field("supplier_name", "Heroe's Srl"),
  ],
  rows: [
    row(0, "I.V. 2", "racchette 2027 GRAFICATE", "14600", "50"),
    row(1, "I.V. 1", "racchette 2027 NON GRAFICATE", "2000", "50"),
  ],
} as DocumentDetail;

describe("mapOrdinePreviewToForm", () => {
  it("mapeia IR 589 para código, fornecedor novo e duas linhas compromisso", () => {
    const draft = mapOrdinePreviewToForm(doc589, null);
    expect(draft.code).toBe("589");
    expect(draft.orderDate).toBe("2026-06-04");
    expect(draft.supplierId).toBe("");
    expect(draft.newSupplierName).toBe("Heroe's Srl");
    expect(draft.lines).toHaveLength(2);
    expect(draft.lines[0].line_kind).toBe("COMMITMENT");
    expect(draft.lines[0].sku).toBe("I.V. 2");
    expect(draft.lines[1].sku).toBe("I.V. 1");
  });

  it("prefere código e linhas do preview-commit quando existem", () => {
    const preview = {
      document_id: 9,
      fingerprint: "x",
      open_error_count: 0,
      can_commit: true,
      can_create_order: true,
      human_summary: "",
      readiness_derived: true,
      operations: [
        {
          op_key: "create_supplier",
          description: "Cadastrar",
          entity_type: "supplier",
          params: { name: "Heroe's Srl" },
        },
        {
          op_key: "create_order",
          description: "Criar",
          entity_type: "order",
          params: { code: "589-A", order_date: "2026-06-04", currency: "EUR" },
        },
        {
          op_key: "add_item_0",
          description: "item",
          entity_type: "order_item",
          params: {
            line_kind: "COMMITMENT",
            external_code: "I.V. 2",
            description: "racchette 2027 GRAFICATE",
            quantity: "14600",
            unit_price: "50",
            unit: "PZ",
          },
        },
      ],
    } as PreviewCommitOut;
    const draft = mapOrdinePreviewToForm(doc589, preview);
    expect(draft.code).toBe("589-A");
    expect(draft.lines).toHaveLength(1);
    expect(draft.lines[0].sku).toBe("I.V. 2");
  });

  it("reconhece tipo Ordine", () => {
    expect(isOrdineDocType("ORDINE_COMPRA")).toBe(true);
    expect(isOrdineDocType("FATTURA_VENDITA")).toBe(false);
  });
});
