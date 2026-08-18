import { useMemo } from "react";
import { MoneyDisplay, SectionCard } from "../../ui";
import { formatDateOnly } from "../../ui/format";
import type { DocumentDetail, RowOut } from "./ingestionApi";

type Props = { doc: DocumentDetail };

type Scadenza = {
  date?: string;
  due_date_iso?: string;
  due_date_raw?: string;
  amount?: string | number;
  label?: string;
};

function field(doc: DocumentDetail, key: string): string | null {
  const f = (doc.fields ?? []).find((x) => x.field_key === key);
  return f?.effective_value ?? f?.normalized_value ?? f?.raw_value ?? null;
}

function parseCells(row: RowOut): Record<string, { normalized?: string; raw?: string }> {
  try {
    return JSON.parse(row.cells_json) as Record<string, { normalized?: string; raw?: string }>;
  } catch {
    return {};
  }
}

function cellVal(cells: Record<string, { normalized?: string; raw?: string }>, key: string): string {
  const c = cells[key];
  return c?.normalized ?? c?.raw ?? "—";
}

export function FatturaStructuredPanel({ doc }: Props) {
  const header = useMemo(
    () => ({
      supplier: field(doc, "supplier_name"),
      supplierPi: field(doc, "supplier_pi_cf"),
      invoiceNumber: field(doc, "invoice_number"),
      invoiceDate: field(doc, "invoice_date"),
      currency: field(doc, "currency") ?? "EUR",
      ddt: field(doc, "ddt_ref"),
      paymentTerms: field(doc, "payment_terms_text"),
    }),
    [doc],
  );

  const totals = useMemo(
    () => ({
      taxable: field(doc, "total_taxable"),
      exempt: field(doc, "total_exempt"),
      document: field(doc, "total_document"),
    }),
    [doc],
  );

  const scadenze = useMemo((): Scadenza[] => {
    const raw = field(doc, "scadenze_json");
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as Scadenza[] | { items?: Scadenza[] };
      if (Array.isArray(parsed)) return parsed;
      if (parsed && Array.isArray(parsed.items)) return parsed.items;
      return [];
    } catch {
      return [];
    }
  }, [doc]);

  const lineRows = useMemo(() => {
    const rows = (doc.rows ?? []).filter((r) => {
      const cells = parseCells(r);
      return cells.sku || cells.description;
    });
    return rows.sort((a, b) => a.row_index - b.row_index);
  }, [doc.rows]);

  if (doc.doc_type !== "FATTURA_VENDITA") return null;

  return (
    <SectionCard title="Fattura — visão estruturada" data-testid="fattura-structured-panel">
      <div className="fattura-structured-header" data-testid="fattura-header">
        <dl className="ingestion-summary-dl">
          <div>
            <dt>Fornecedor</dt>
            <dd>{header.supplier ?? "—"}</dd>
          </div>
          <div>
            <dt>PI/CF</dt>
            <dd>{header.supplierPi ?? "—"}</dd>
          </div>
          <div>
            <dt>Fatura nº</dt>
            <dd>{header.invoiceNumber ?? "—"}</dd>
          </div>
          <div>
            <dt>Data</dt>
            <dd>{header.invoiceDate ? formatDateOnly(header.invoiceDate) : "—"}</dd>
          </div>
          <div>
            <dt>DDT</dt>
            <dd>{header.ddt ?? "—"}</dd>
          </div>
          <div>
            <dt>Pagamento</dt>
            <dd>{header.paymentTerms ?? "—"}</dd>
          </div>
        </dl>
      </div>

      <div className="fattura-structured-lines" data-testid="fattura-lines">
        <h3 className="ingestion-subtitle">Linhas ({lineRows.length})</h3>
        {lineRows.length === 0 ? (
          <p className="muted">Nenhuma linha extraída</p>
        ) : (
          <table className="dense-table" data-testid="fattura-lines-table">
            <thead>
              <tr>
                <th>#</th>
                <th>SKU</th>
                <th>Descrição</th>
                <th>Qtd</th>
                <th>Preço</th>
                <th>Total</th>
                <th>IVA</th>
              </tr>
            </thead>
            <tbody>
              {lineRows.map((row) => {
                const cells = parseCells(row);
                return (
                  <tr key={row.id} data-testid={`fattura-line-${row.id}`}>
                    <td>{row.row_index}</td>
                    <td>{cellVal(cells, "sku")}</td>
                    <td>{cellVal(cells, "description")}</td>
                    <td>{cellVal(cells, "quantity")}</td>
                    <td>{cellVal(cells, "unit_price")}</td>
                    <td>{cellVal(cells, "line_total")}</td>
                    <td>{cellVal(cells, "iva_code")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="fattura-structured-totals" data-testid="fattura-totals">
        <h3 className="ingestion-subtitle">Totais</h3>
        <dl className="ingestion-summary-dl">
          <div>
            <dt>Imponibile</dt>
            <dd>{totals.taxable ?? "—"}</dd>
          </div>
          <div>
            <dt>Esente</dt>
            <dd>{totals.exempt ?? "—"}</dd>
          </div>
          <div>
            <dt>Total documento</dt>
            <dd>
              {totals.document ? (
                <MoneyDisplay amount={totals.document} currency={header.currency} />
              ) : (
                "—"
              )}
            </dd>
          </div>
        </dl>
      </div>

      <div className="fattura-structured-scadenze" data-testid="fattura-scadenze">
        <h3 className="ingestion-subtitle">Scadenze ({scadenze.length})</h3>
        {scadenze.length === 0 ? (
          <p className="muted">Nenhuma scadenza extraída</p>
        ) : (
          <ul>
            {scadenze.map((s, idx) => (
              <li key={idx} data-testid={`fattura-scadenza-${idx}`}>
                {(() => {
                  const iso = s.due_date_iso || s.date;
                  const formatted = iso ? formatDateOnly(iso) : "—";
                  const dateLabel =
                    formatted !== "—"
                      ? formatted
                      : s.due_date_raw || s.label || `Parcela ${idx + 1}`;
                  return dateLabel;
                })()}:{" "}
                {s.amount != null ? (
                  <MoneyDisplay amount={String(s.amount)} currency={header.currency} />
                ) : (
                  "—"
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
