import { useMemo, useState } from "react";
import { Button, SectionCard, TextInput } from "../../ui";
import { formatDateOnly } from "../../ui/format";
import type { User } from "../auth/types";
import {
  addDocumentRow,
  correctIngestionField,
  deleteIngestionRow,
  patchIngestionRow,
  type DocumentDetail,
  type FieldOut,
  type RowOut,
} from "./ingestionApi";
import {
  cellText,
  formatMoneyEur,
  formatQty,
  isCommitmentLine,
  parseRowCells,
  type CellMap,
} from "./ordineShellHelpers";

type Props = {
  user: User;
  doc: DocumentDetail;
  onUpdated: () => void;
};

function fieldByKey(doc: DocumentDetail, key: string): FieldOut | undefined {
  return (doc.fields ?? []).find((x) => x.field_key === key);
}

function fieldVal(doc: DocumentDetail, key: string): string {
  const f = fieldByKey(doc, key);
  return String(f?.effective_value ?? f?.raw_value ?? "").trim();
}

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

const HEADER_KEYS: { key: string; label: string; type?: string; editable?: boolean }[] = [
  { key: "order_number", label: "Número do documento", editable: false },
  { key: "order_date", label: "Data", type: "date", editable: true },
  { key: "currency", label: "Moeda", editable: true },
  // Total do cabeçalho PDF não é editável no Resumo: a UI mostra a soma das linhas
  // (RUX-3F) — total_document não alimenta o commit do pedido.
];

/** RESUMO operacional editável — pedido + linhas (D8). Sem JSON / raw / status. */
export function OrdineSummaryPanel({ user, doc, onUpdated }: Props) {
  const writable = canWrite(user);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingHeader, setEditingHeader] = useState(false);
  const [headerDraft, setHeaderDraft] = useState<Record<string, string>>({});
  const [editingRowId, setEditingRowId] = useState<number | null>(null);
  const [rowDraft, setRowDraft] = useState({
    description: "",
    quantity: "",
    unit: "",
    unit_price: "",
  });

  const supplier = fieldVal(doc, "supplier_name") || "—";

  const rows = useMemo(
    () =>
      (doc.rows ?? []).map((r) => {
        const cells = parseRowCells(r.cells_json);
        return { row: r, cells, commitment: isCommitmentLine(cells) };
      }),
    [doc.rows],
  );

  const qtySum = rows.reduce((acc, { cells }) => {
    const q = Number(cellText(cells, "quantity").replace(",", "."));
    return acc + (Number.isFinite(q) ? q : 0);
  }, 0);

  /** Total honesto = soma das linhas (qty×preço ou line_total), não o campo PDF stale. */
  const totalFromLines = rows.reduce((acc, { cells }) => {
    const lt = Number(cellText(cells, "line_total").replace(",", "."));
    if (Number.isFinite(lt) && lt !== 0) return acc + lt;
    const q = Number(cellText(cells, "quantity").replace(",", "."));
    const p = Number(cellText(cells, "unit_price").replace(",", "."));
    if (Number.isFinite(q) && Number.isFinite(p)) return acc + q * p;
    return acc;
  }, 0);

  function startHeaderEdit() {
    const draft: Record<string, string> = {};
    for (const h of HEADER_KEYS) draft[h.key] = fieldVal(doc, h.key);
    setHeaderDraft(draft);
    setEditingHeader(true);
    setError(null);
  }

  async function saveHeader() {
    setBusy(true);
    setError(null);
    try {
      for (const h of HEADER_KEYS) {
        if (h.editable === false) continue;
        const f = fieldByKey(doc, h.key);
        if (!f) continue;
        const next = (headerDraft[h.key] ?? "").trim();
        const cur = fieldVal(doc, h.key);
        if (next === cur) continue;
        await correctIngestionField(f.id, {
          corrected_value: next || null,
          expected_version: f.version,
          reason: "resumo_operador",
        });
      }
      setEditingHeader(false);
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível salvar");
    } finally {
      setBusy(false);
    }
  }

  function startRowEdit(row: RowOut, cells: CellMap) {
    setEditingRowId(row.id);
    setRowDraft({
      description: cellText(cells, "description"),
      quantity: cellText(cells, "quantity"),
      unit: cellText(cells, "unit") || "PZ",
      unit_price: cellText(cells, "unit_price"),
    });
    setError(null);
  }

  async function saveRow(row: RowOut) {
    setBusy(true);
    setError(null);
    try {
      const cells = parseRowCells(row.cells_json);
      const next = { ...cells };
      for (const key of ["description", "quantity", "unit", "unit_price"] as const) {
        const v = rowDraft[key].trim();
        next[key] = { raw: (cells[key] as { raw?: string } | undefined)?.raw ?? v, normalized: v };
      }
      const qty = Number(rowDraft.quantity.replace(",", "."));
      const price = Number(rowDraft.unit_price.replace(",", "."));
      if (Number.isFinite(qty) && Number.isFinite(price)) {
        const total = (qty * price).toFixed(2);
        next.line_total = {
          raw: (cells.line_total as { raw?: string } | undefined)?.raw ?? total,
          normalized: total,
        };
      }
      await patchIngestionRow(row.id, {
        cells_json: JSON.stringify(next),
        expected_version: row.version,
        reason: "resumo_operador",
      });
      setEditingRowId(null);
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível salvar a linha");
    } finally {
      setBusy(false);
    }
  }

  async function removeRow(row: RowOut) {
    if (!window.confirm("Remover esta linha do documento?")) return;
    setBusy(true);
    setError(null);
    try {
      await deleteIngestionRow(row.id, row.version);
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível remover");
    } finally {
      setBusy(false);
    }
  }

  async function addLine() {
    setBusy(true);
    setError(null);
    try {
      const cells = {
        sku: { raw: null, normalized: null },
        description: { raw: "Nova linha", normalized: "Nova linha" },
        quantity: { raw: "1", normalized: "1" },
        unit: { raw: "PZ", normalized: "PZ" },
        unit_price: { raw: "0", normalized: "0" },
        line_total: { raw: "0", normalized: "0" },
        product_id_catalog: { raw: null, normalized: null },
      };
      await addDocumentRow(doc.id, {
        cells_json: JSON.stringify(cells),
        expected_version: doc.version,
      });
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível adicionar linha");
    } finally {
      setBusy(false);
    }
  }

  const currency = fieldVal(doc, "currency") || "EUR";
  const totalDisplay =
    totalFromLines > 0
      ? String(totalFromLines)
      : fieldVal(doc, "total_document");

  return (
    <SectionCard
      title="Resumo"
      data-testid="ordine-summary-panel"
      actions={
        writable && !editingHeader ? (
          <Button type="button" variant="ghost" disabled={busy} onClick={startHeaderEdit} data-testid="ordine-summary-edit-header">
            Corrigir cabeçalho
          </Button>
        ) : null
      }
    >
      {error ? <p className="error-text">{error}</p> : null}

      {editingHeader ? (
        <div className="ordine-summary-edit" data-testid="ordine-summary-header-edit">
          {HEADER_KEYS.filter((h) => h.editable !== false).map((h) => (
            <label key={h.key}>
              {h.label}
              <TextInput
                type={h.type === "date" ? "date" : "text"}
                value={headerDraft[h.key] ?? ""}
                onChange={(e) => setHeaderDraft((d) => ({ ...d, [h.key]: e.target.value }))}
                data-testid={`ordine-summary-field-${h.key}`}
              />
            </label>
          ))}
          <p className="muted" data-testid="ordine-summary-order-number-readonly">
            Número do documento (não editável): {fieldVal(doc, "order_number") || "—"}
          </p>
          <div className="stack-row">
            <Button type="button" disabled={busy} onClick={() => void saveHeader()} data-testid="ordine-summary-save-header">
              Salvar
            </Button>
            <Button type="button" variant="ghost" disabled={busy} onClick={() => setEditingHeader(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <dl className="ingestion-summary-dl ordine-summary-meta" data-testid="ordine-summary-meta">
          <div>
            <dt>Número do documento</dt>
            <dd data-testid="ordine-summary-doc-number">{fieldVal(doc, "order_number") || "—"}</dd>
          </div>
          <div>
            <dt>Fornecedor</dt>
            <dd>{supplier}</dd>
          </div>
          <div>
            <dt>Data</dt>
            <dd>{fieldVal(doc, "order_date") ? formatDateOnly(fieldVal(doc, "order_date")) : "—"}</dd>
          </div>
          <div>
            <dt>Moeda</dt>
            <dd>{currency}</dd>
          </div>
          <div>
            <dt>Quantidade</dt>
            <dd>{qtySum > 0 ? `${formatQty(String(qtySum))} PZ` : "—"}</dd>
          </div>
          <div>
            <dt>Total</dt>
            <dd data-testid="ordine-summary-total">
              {totalDisplay
                ? currency === "EUR"
                  ? formatMoneyEur(totalDisplay)
                  : `${currency} ${totalDisplay}`
                : "—"}
            </dd>
          </div>
        </dl>
      )}

      {rows.length === 0 ? (
        <p className="muted">Nenhuma linha no documento.</p>
      ) : (
        <ul className="ordine-summary-lines" data-testid="ordine-summary-lines">
          {rows.map(({ row, cells, commitment }) => {
            const sku = cellText(cells, "sku");
            const desc = cellText(cells, "description") || "—";
            const qty = cellText(cells, "quantity");
            const unit = cellText(cells, "unit") || "PZ";
            const price = cellText(cells, "unit_price");
            const lineTotal = cellText(cells, "line_total");
            if (editingRowId === row.id) {
              return (
                <li key={row.id} data-testid={`ordine-summary-line-edit-${row.id}`}>
                  <label>
                    Descrição
                    <TextInput
                      value={rowDraft.description}
                      onChange={(e) => setRowDraft((d) => ({ ...d, description: e.target.value }))}
                      data-testid="ordine-line-edit-description"
                    />
                  </label>
                  <label>
                    Quantidade
                    <TextInput
                      value={rowDraft.quantity}
                      onChange={(e) => setRowDraft((d) => ({ ...d, quantity: e.target.value }))}
                      data-testid="ordine-line-edit-quantity"
                    />
                  </label>
                  <label>
                    Unidade
                    <TextInput
                      value={rowDraft.unit}
                      onChange={(e) => setRowDraft((d) => ({ ...d, unit: e.target.value }))}
                      data-testid="ordine-line-edit-unit"
                    />
                  </label>
                  <label>
                    Preço unitário
                    <TextInput
                      value={rowDraft.unit_price}
                      onChange={(e) => setRowDraft((d) => ({ ...d, unit_price: e.target.value }))}
                      data-testid="ordine-line-edit-price"
                    />
                  </label>
                  <div className="stack-row">
                    <Button type="button" disabled={busy} onClick={() => void saveRow(row)} data-testid="ordine-line-save">
                      Salvar linha
                    </Button>
                    <Button type="button" variant="ghost" disabled={busy} onClick={() => setEditingRowId(null)}>
                      Cancelar
                    </Button>
                  </div>
                </li>
              );
            }
            return (
              <li key={row.id} data-testid={`ordine-summary-line-${row.id}`}>
                <span className="ordine-summary-line-main">
                  {desc}
                  {sku ? <span className="muted"> · {sku}</span> : null}
                </span>
                <span className="ordine-summary-line-meta">
                  {qty ? `${formatQty(qty)} ${unit}` : null}
                  {price ? ` · ${formatMoneyEur(price)}` : null}
                  {lineTotal ? ` · total ${formatMoneyEur(lineTotal)}` : null}
                  {commitment ? <span className="ordine-commitment-tag"> compromisso</span> : null}
                </span>
                {writable ? (
                  <span className="stack-row">
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => startRowEdit(row, cells)}
                      data-testid={`ordine-line-edit-${row.id}`}
                    >
                      Corrigir
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={busy}
                      onClick={() => void removeRow(row)}
                      data-testid={`ordine-line-remove-${row.id}`}
                    >
                      Remover
                    </Button>
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {writable ? (
        <Button type="button" variant="ghost" disabled={busy} onClick={() => void addLine()} data-testid="ordine-line-add">
          Adicionar linha
        </Button>
      ) : null}
    </SectionCard>
  );
}
