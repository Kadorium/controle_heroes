import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Card, EditableCell, EmptyState, LoadingState, PageHeader, useToast } from "../components";
import { importationsApi, dashboardApi, type OrderQueueRow } from "../api";
import { normalizeImportCurrency } from "../constants/currency";
import { emptyDash, formatMoney, statusLabel } from "../i18n/glossario";
import { fmtDate } from "../utils/formatDate";
import { NovaOrdemModal } from "./importation/NovaOrdemModal";

type QuickFilter = "all" | "saldo" | "due7" | "overdue" | "dispatch" | "pending" | "closure";

const FILTERS: { id: QuickFilter; label: string }[] = [
  { id: "all", label: "Tudo" },
  { id: "saldo", label: "Com saldo a pagar" },
  { id: "overdue", label: "Vencidos" },
  { id: "dispatch", label: "A despachar" },
  { id: "pending", label: "Com pendência" },
  { id: "closure", label: "Pronto para fechamento" },
];

type SortKey =
  | "po_number"
  | "supplier_name"
  | "status"
  | "total_invoiced"
  | "total_paid"
  | "consolidated_balance"
  | "next_due_date"
  | "responsible"
  | "internal_forecast_date"
  | "pending_actions_count"
  | "updated_at";

const PRIORITY_OPTIONS = [
  { value: "HIGH", label: "Alta" },
  { value: "MEDIUM", label: "Média" },
  { value: "LOW", label: "Baixa" },
];

function sortMark(active: boolean, asc: boolean): string {
  if (!active) return "";
  return asc ? " ▲" : " ▼";
}

function yearFrom(iso: string): string {
  return iso ? iso.slice(0, 4) : emptyDash(null);
}

function priorityLabel(p: string | null | undefined): string {
  return PRIORITY_OPTIONS.find((o) => o.value === p)?.label ?? "—";
}

function exportSheet(rows: OrderQueueRow[]) {
  const header = [
    "Ordem", "Ano", "Fornecedor", "Status", "Prioridade", "Responsável", "Previsão interna",
    "Valor faturado", "Pago", "Saldo a pagar", "Próx. vencimento", "Vencidos",
    "Faturas quitadas", "Faturas total",
    "Produtos", "Qtd pedida", "Qtd faturada", "Qtd despachada", "A despachar",
    "Docs pendentes", "Pendências", "Observação", "Última atualização",
  ];
  const lines = rows.map((r) =>
    [
      r.po_number, yearFrom(r.created_at), r.supplier_name, statusLabel(r.status),
      priorityLabel(r.priority), r.responsible ?? "", r.internal_forecast_date ?? "",
      r.total_invoiced ?? "", r.total_paid ?? "", r.consolidated_balance ?? "",
      r.next_due_date ?? "", r.overdue_count ?? 0,
      r.invoices_settled_count ?? 0, r.invoices_count ?? 0,
      r.products_count ?? 0, r.qty_ordered ?? "", r.qty_invoiced ?? "", r.qty_shipped ?? "", r.to_dispatch ?? "",
      r.docs_pending_count ?? 0, r.pending_actions_count || 0, r.brazil_operational_notes ?? "",
      r.updated_at ? fmtDate(r.updated_at) : fmtDate(r.created_at),
    ]
      .map((c) => `"${String(c).replace(/"/g, '""')}"`)
      .join(",")
  );
  const blob = new Blob([`\uFEFF${header.join(",")}\n${lines.join("\n")}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ordens-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function ImportationsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<OrderQueueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<QuickFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("po_number");
  const [sortAsc, setSortAsc] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<OrderQueueRow | null>(null);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      try {
        const queue = await importationsApi.orderQueue(200);
        setRows(queue.items);
      } catch {
        const dash = await dashboardApi.importations(200);
        setRows(
          dash.items.map(
            (r): OrderQueueRow => ({
              id: r.id,
              po_number: r.po_number,
              supplier_id: 0,
              supplier_name: r.supplier_name,
              status: r.status,
              currency: r.currency,
              total_invoiced: null,
              total_paid: null,
              consolidated_balance: r.open_value,
              to_dispatch: null,
              pending_actions_count: r.closure_pending_count + r.action_items.length,
              updated_at: null,
              created_at: r.created_at,
            })
          )
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function saveField(id: number, patch: Record<string, string | null>) {
    const updated = await importationsApi.updateBrazilFields(id, patch);
    setRows((prev) =>
      prev.map((r) =>
        r.id === id
          ? {
              ...r,
              priority: updated.priority,
              responsible: updated.responsible,
              internal_forecast_date: updated.internal_forecast_date,
              brazil_operational_notes: updated.brazil_operational_notes,
            }
          : r
      )
    );
  }

  const filtered = useMemo(() => {
    let list = [...rows];
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (r) =>
          r.po_number.toLowerCase().includes(q) ||
          (r.supplier_name ?? "").toLowerCase().includes(q) ||
          (r.responsible ?? "").toLowerCase().includes(q)
      );
    }
    switch (filter) {
      case "saldo":
        list = list.filter((r) => r.consolidated_balance != null && Number(r.consolidated_balance) > 0);
        break;
      case "overdue":
        list = list.filter((r) => (r.overdue_count ?? 0) > 0);
        break;
      case "pending":
        list = list.filter((r) => r.pending_actions_count > 0);
        break;
      case "dispatch":
        list = list.filter((r) => (r.to_dispatch ?? 0) > 0);
        break;
      case "closure":
        list = list.filter(
          (r) =>
            r.pending_actions_count === 0 &&
            (r.consolidated_balance == null || Number(r.consolidated_balance) === 0)
        );
        break;
      default:
        break;
    }
    list.sort((a, b) => {
      let va: string | number = "";
      let vb: string | number = "";
      switch (sortKey) {
        case "po_number": va = a.po_number; vb = b.po_number; break;
        case "supplier_name": va = a.supplier_name ?? ""; vb = b.supplier_name ?? ""; break;
        case "status": va = a.status; vb = b.status; break;
        case "consolidated_balance": va = Number(a.consolidated_balance ?? NaN); vb = Number(b.consolidated_balance ?? NaN); break;
        case "total_invoiced": va = Number(a.total_invoiced ?? NaN); vb = Number(b.total_invoiced ?? NaN); break;
        case "total_paid": va = Number(a.total_paid ?? NaN); vb = Number(b.total_paid ?? NaN); break;
        case "next_due_date": va = a.next_due_date ?? "9999"; vb = b.next_due_date ?? "9999"; break;
        case "responsible": va = a.responsible ?? ""; vb = b.responsible ?? ""; break;
        case "internal_forecast_date": va = a.internal_forecast_date ?? "9999"; vb = b.internal_forecast_date ?? "9999"; break;
        case "pending_actions_count": va = a.pending_actions_count; vb = b.pending_actions_count; break;
        case "updated_at": va = a.updated_at ?? a.created_at; vb = b.updated_at ?? b.created_at; break;
      }
      const cmp =
        typeof va === "number" && typeof vb === "number" && (Number.isNaN(va) || Number.isNaN(vb))
          ? (Number.isNaN(va) ? 1 : Number.isNaN(vb) ? -1 : 0)
          : va < vb ? -1 : va > vb ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
    return list;
  }, [rows, search, filter, sortKey, sortAsc]);

  const totalsByCurrency = useMemo(() => {
    const acc: Record<string, { invoiced: number; paid: number; balance: number }> = {};
    for (const r of filtered) {
      const cur = normalizeImportCurrency(r.currency);
      acc[cur] = acc[cur] ?? { invoiced: 0, paid: 0, balance: 0 };
      acc[cur].invoiced += Number(r.total_invoiced ?? 0);
      acc[cur].paid += Number(r.total_paid ?? 0);
      acc[cur].balance += Number(r.consolidated_balance ?? 0);
    }
    return acc;
  }, [filtered]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  }

  async function confirmDeleteOrder() {
    if (!deleteTarget || deleteReason.trim().length < 3) {
      toast.error("Informe o motivo (mín. 3 caracteres)");
      return;
    }
    setDeleteLoading(true);
    try {
      await importationsApi.cancel(deleteTarget.id, deleteReason.trim());
      setRows((prev) => prev.filter((r) => r.id !== deleteTarget.id));
      toast.success(`Ordem ${deleteTarget.po_number} excluída`);
      setDeleteTarget(null);
      setDeleteReason("");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Não foi possível excluir a ordem");
    } finally {
      setDeleteLoading(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <PageHeader title="Ordens" />
        <LoadingState />
      </Card>
    );
  }

  return (
    <Card>
      <PageHeader
        title="Ordens"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <Button onClick={() => setShowNew(true)}>+ Nova ordem</Button>
            <Button variant="secondary" onClick={() => navigate("/cadastros/heroes")}>Importar Heroes</Button>
            <Button variant="ghost" onClick={() => exportSheet(filtered)}>Exportar</Button>
          </div>
        }
      />

      {error && <p className="error">{error}</p>}

      <div className="sheet-toolbar">
        <input
          className="search"
          type="text"
          placeholder="Buscar ordem, fornecedor ou responsável…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="order-queue__filters">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={`order-queue__filter${filter === f.id ? " order-queue__filter--on" : ""}`}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <span className="spacer" />
        <span className="order-queue__meta">{filtered.length} de {rows.length} ordens</span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="Nenhuma ordem encontrada" />
      ) : (
        <div className="sheet-grid-wrap">
          <table className="sheet-grid">
            <thead>
              <tr>
                <th className="sticky-col sortable" onClick={() => toggleSort("po_number")}>Ordem{sortMark(sortKey === "po_number", sortAsc)}</th>
                <th className="sortable" onClick={() => toggleSort("status")}>Status{sortMark(sortKey === "status", sortAsc)}</th>
                <th>Prioridade</th>
                <th className="num sortable" onClick={() => toggleSort("total_invoiced")}>Faturado{sortMark(sortKey === "total_invoiced", sortAsc)}</th>
                <th className="num sortable" onClick={() => toggleSort("total_paid")}>Pago{sortMark(sortKey === "total_paid", sortAsc)}</th>
                <th className="num sortable" onClick={() => toggleSort("consolidated_balance")}>Saldo{sortMark(sortKey === "consolidated_balance", sortAsc)}</th>
                <th className="sortable" onClick={() => toggleSort("next_due_date")}>Próx. venc.{sortMark(sortKey === "next_due_date", sortAsc)}</th>
                <th className="num">Vencidos</th>
                <th className="num" title="Faturas quitadas / total. Uma ordem costuma ter 3: antecipo, na chegada e saldo (30/60 dias).">Faturas</th>
                <th className="num">Prod.</th>
                <th className="num">Faturada</th>
                <th className="num">Despach.</th>
                <th className="sortable" onClick={() => toggleSort("responsible")}>Responsável{sortMark(sortKey === "responsible", sortAsc)}</th>
                <th className="sortable" onClick={() => toggleSort("internal_forecast_date")}>Prev. interna{sortMark(sortKey === "internal_forecast_date", sortAsc)}</th>
                <th className="num">Docs</th>
                <th className="num sortable" onClick={() => toggleSort("pending_actions_count")}>Pend.{sortMark(sortKey === "pending_actions_count", sortAsc)}</th>
                <th>Observação</th>
                <th className="sortable" onClick={() => toggleSort("updated_at")}>Atualização{sortMark(sortKey === "updated_at", sortAsc)}</th>
                <th className="sortable" onClick={() => toggleSort("supplier_name")}>Fornecedor{sortMark(sortKey === "supplier_name", sortAsc)}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => {
                const cur = normalizeImportCurrency(r.currency);
                return (
                  <tr key={r.id}>
                    <td className="sticky-col">
                      <span className="row-po sheet-grid__open" onClick={() => navigate(`/importacoes/${r.id}/resumo`)}>{r.po_number}</span>
                    </td>
                    <td><Badge status={r.status}>{statusLabel(r.status)}</Badge></td>
                    <td>
                      <EditableCell
                        type="select"
                        options={PRIORITY_OPTIONS}
                        value={r.priority ?? ""}
                        display={r.priority ? <span className={`prio-badge prio-badge--${r.priority}`}>{priorityLabel(r.priority)}</span> : undefined}
                        onSave={(v) => saveField(r.id, { priority: v || null })}
                      />
                    </td>
                    <td className="num">{formatMoney(r.total_invoiced, cur)}</td>
                    <td className="num">{formatMoney(r.total_paid, cur)}</td>
                    <td className="num">{formatMoney(r.consolidated_balance, cur)}</td>
                    <td>{r.next_due_date ? fmtDate(r.next_due_date) : emptyDash(null)}</td>
                    <td className="num">{(r.overdue_count ?? 0) > 0 ? <span className="overdue-pill">{r.overdue_count}</span> : emptyDash(null)}</td>
                    <td className="num">
                      {(r.invoices_count ?? 0) > 0 ? (
                        <span
                          className={`inv-count${(r.invoices_settled_count ?? 0) >= (r.invoices_count ?? 0) ? " inv-count--done" : ""}`}
                          title={`${r.invoices_settled_count ?? 0} de ${r.invoices_count} faturas quitadas`}
                        >
                          {r.invoices_settled_count ?? 0}/{r.invoices_count}
                        </span>
                      ) : emptyDash(null)}
                    </td>
                    <td className="num">{r.products_count || emptyDash(null)}</td>
                    <td className="num">{r.qty_invoiced ?? emptyDash(null)}</td>
                    <td className="num">{r.qty_shipped ?? emptyDash(null)}</td>
                    <td>
                      <EditableCell value={r.responsible ?? ""} onSave={(v) => saveField(r.id, { responsible: v || null })} placeholder="—" />
                    </td>
                    <td>
                      <EditableCell type="date" value={r.internal_forecast_date ?? ""} display={r.internal_forecast_date ? fmtDate(r.internal_forecast_date) : undefined} onSave={(v) => saveField(r.id, { internal_forecast_date: v || null })} />
                    </td>
                    <td className="num">{(r.docs_pending_count ?? 0) > 0 ? r.docs_pending_count : emptyDash(null)}</td>
                    <td className="num">{r.pending_actions_count > 0 ? r.pending_actions_count : emptyDash(null)}</td>
                    <td>
                      <EditableCell value={r.brazil_operational_notes ?? ""} onSave={(v) => saveField(r.id, { brazil_operational_notes: v || null })} placeholder="—" />
                    </td>
                    <td>{fmtDate(r.updated_at ?? r.created_at)}</td>
                    <td>{r.supplier_name ?? emptyDash(null)}</td>
                    <td>
                      <div className="order-queue__row-actions">
                        <Button variant="ghost" className="ui-btn--sm" onClick={() => navigate(`/importacoes/${r.id}/resumo`)}>
                          Abrir
                        </Button>
                        <Button
                          variant="ghost"
                          className="ui-btn--sm ui-btn--danger"
                          onClick={() => {
                            setDeleteTarget(r);
                            setDeleteReason("");
                          }}
                        >
                          Excluir
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              {Object.entries(totalsByCurrency).map(([cur, t]) => (
                <tr key={cur}>
                  <td className="sticky-col">Totais {cur}</td>
                  <td colSpan={2}></td>
                  <td className="num">{formatMoney(t.invoiced, cur)}</td>
                  <td className="num">{formatMoney(t.paid, cur)}</td>
                  <td className="num">{formatMoney(t.balance, cur)}</td>
                  <td colSpan={14}></td>
                </tr>
              ))}
            </tfoot>
          </table>
        </div>
      )}

      {showNew && (
        <NovaOrdemModal
          onClose={() => setShowNew(false)}
          onCreated={(id) => {
            setShowNew(false);
            toast.success("Ordem criada");
            navigate(`/importacoes/${id}/resumo`);
          }}
        />
      )}

      {deleteTarget && (
        <div className="modal-back" onClick={() => !deleteLoading && setDeleteTarget(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>Excluir ordem {deleteTarget.po_number}</h3>
            <p className="meta">
              A ordem será anulada e sairá da lista. Pagamentos, faturas e histórico permanecem registrados.
            </p>
            <label>
              Motivo da exclusão
              <textarea
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                rows={3}
                placeholder="Ex.: ordem de teste"
              />
            </label>
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setDeleteTarget(null)} disabled={deleteLoading}>
                Cancelar
              </Button>
              <Button
                variant="danger"
                onClick={() => void confirmDeleteOrder()}
                disabled={deleteLoading || deleteReason.trim().length < 3}
              >
                {deleteLoading ? "Excluindo…" : "Confirmar exclusão"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
