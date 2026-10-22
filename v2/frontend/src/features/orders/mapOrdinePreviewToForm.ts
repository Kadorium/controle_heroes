import type { DocumentDetail, PreviewCommitOut } from "../ingestion/ingestionApi";
import { cellText, isCommitmentLine, isProductResolved, parseRowCells } from "../ingestion/ordineShellHelpers";

export type OrdineDraftLine = {
  sku: string;
  product_id: number | null;
  quantity: string;
  unit_price: string;
  unit: string;
  line_kind: "PRODUCT" | "COMMITMENT";
  description: string;
};

export type OrdineFormDraft = {
  code: string;
  orderDate: string;
  currency: string;
  supplierId: number | "";
  newSupplierName: string;
  lines: OrdineDraftLine[];
};

function fieldVal(doc: DocumentDetail, key: string): string {
  const f = (doc.fields ?? []).find((x) => x.field_key === key);
  return String(f?.effective_value ?? f?.corrected_value ?? f?.normalized_value ?? f?.raw_value ?? "").trim();
}

function paramStr(params: Record<string, unknown> | undefined, key: string): string {
  const v = params?.[key];
  if (v == null) return "";
  return String(v).trim();
}

export function isOrdineDocType(docType: string | null | undefined): boolean {
  const t = String(docType ?? "").toUpperCase();
  return t === "ORDINE_COMPRA" || t === "ORDINE";
}

export function mapOrdinePreviewToForm(
  doc: DocumentDetail,
  preview?: PreviewCommitOut | null,
): OrdineFormDraft {
  const createOp = (preview?.operations ?? []).find((o) => o.op_key === "create_order");
  const supplierOp = (preview?.operations ?? []).find((o) => o.op_key === "create_supplier");
  const code =
    paramStr(createOp?.params, "code") || fieldVal(doc, "order_number") || fieldVal(doc, "order_code");
  const orderDate = paramStr(createOp?.params, "order_date") || fieldVal(doc, "order_date");
  const currency = paramStr(createOp?.params, "currency") || fieldVal(doc, "currency") || "EUR";

  const catalogIdRaw = fieldVal(doc, "supplier_id_catalog") || paramStr(createOp?.params, "supplier_id");
  const supplierId = /^\d+$/.test(catalogIdRaw) ? Number(catalogIdRaw) : ("" as const);
  const newSupplierName =
    supplierId === ""
      ? paramStr(supplierOp?.params, "name") || fieldVal(doc, "supplier_name")
      : "";

  const addOps = (preview?.operations ?? []).filter((o) => o.op_key.startsWith("add_item_"));
  const linesFromPreview: OrdineDraftLine[] = addOps.map((op) => {
    const kind = paramStr(op.params, "line_kind").toUpperCase() === "PRODUCT" ? "PRODUCT" : "COMMITMENT";
    const productRaw = paramStr(op.params, "product_id");
    const product_id = kind === "PRODUCT" && /^\d+$/.test(productRaw) ? Number(productRaw) : null;
    return {
      sku: paramStr(op.params, "external_code") || paramStr(op.params, "sku"),
      product_id,
      quantity: paramStr(op.params, "quantity") || "1",
      unit_price: paramStr(op.params, "unit_price"),
      unit: paramStr(op.params, "unit") || "PZ",
      line_kind: kind,
      description: paramStr(op.params, "description"),
    };
  });

  const linesFromRows: OrdineDraftLine[] = [...(doc.rows ?? [])]
    .sort((a, b) => a.row_index - b.row_index)
    .map((row) => {
      const cells = parseRowCells(row.cells_json);
      const commitment = isCommitmentLine(cells);
      const productRaw = cellText(cells, "product_id_catalog");
      const product_id = isProductResolved(cells) ? Number(productRaw) : null;
      const line_kind: OrdineDraftLine["line_kind"] =
        commitment || product_id == null ? "COMMITMENT" : "PRODUCT";
      return {
        sku: cellText(cells, "sku"),
        product_id,
        quantity: cellText(cells, "quantity") || "1",
        unit_price: cellText(cells, "unit_price"),
        unit: cellText(cells, "unit") || "PZ",
        line_kind,
        description: cellText(cells, "description"),
      };
    })
    .filter((l) => l.sku || l.description);

  return {
    code,
    orderDate,
    currency: currency || "EUR",
    supplierId,
    newSupplierName,
    lines: linesFromPreview.length > 0 ? linesFromPreview : linesFromRows,
  };
}
