import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, Button, Card, EmptyState, LoadingState, PageHeader, Table, useToast } from "../components";
import { importationsApi, dashboardApi, suppliersApi, type OrderQueueRow, type Supplier } from "../api";
import { DEFAULT_IMPORT_CURRENCY } from "../constants/currency";
import { emptyDash, fieldLabel, statusLabel } from "../i18n/glossario";
import { fmtDate } from "../utils/formatDate";

type QuickFilter =
  | "all"
  | "saldo"
  | "due7"
  | "overdue"
  | "pending"
  | "dispatch"
  | "transit"
  | "divergence"
  | "review"
  | "closure";

const FILTERS: { id: QuickFilter; label: string }[] = [
  { id: "all", label: "Tudo" },
  { id: "saldo", label: "Com saldo a pagar" },
  { id: "dispatch", label: "A despachar" },
  { id: "pending", label: "Com pendência" },
  { id: "closure", label: "Pronto para fechamento" },
];

type SortKey = "po_number" | "supplier_name" | "status" | "consolidated_balance" | "updated_at";

function yearFrom(iso: string): string {
  return iso ? iso.slice(0, 4) : emptyDash(null);
}

function exportCsv(rows: OrderQueueRow[]) {
  const header = [
    "Ordem",
    "Ano",
    "Fornecedor",
    "Status",
    "Valor faturado",
    "Pago",
    "Saldo a pagar",
    "A despachar",
    "Pendências",
    "Última atualização",
  ];
  const lines = rows.map((r) =>
    [
      r.po_number,
      yearFrom(r.created_at),
      r.supplier_name,
      statusLabel(r.status),
      r.total_invoiced ?? emptyDash(null),
      r.total_paid ?? emptyDash(null),
      r.consolidated_balance ?? emptyDash(null),
      r.to_dispatch ?? emptyDash(null),
      r.pending_actions_count || emptyDash(null),
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
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<QuickFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("po_number");
  const [sortAsc, setSortAsc] = useState(true);
  const [po, setPo] = useState("");
  const [supplierId, setSupplierId] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const sups = await suppliersApi.list();
      setSuppliers(sups);
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

  const filtered = useMemo(() => {
    let list = [...rows];
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (r) =>
          r.po_number.toLowerCase().includes(q) ||
          (r.supplier_name ?? "").toLowerCase().includes(q)
      );
    }
    switch (filter) {
      case "saldo":
        list = list.filter((r) => r.consolidated_balance != null && Number(r.consolidated_balance) > 0);
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
        case "po_number":
          va = a.po_number;
          vb = b.po_number;
          break;
        case "supplier_name":
          va = a.supplier_name ?? "";
          vb = b.supplier_name ?? "";
          break;
        case "status":
          va = a.status;
          vb = b.status;
          break;
        case "consolidated_balance":
          va = Number(a.consolidated_balance ?? 0);
          vb = Number(b.consolidated_balance ?? 0);
          break;
        case "updated_at":
          va = a.updated_at ?? a.created_at;
          vb = b.updated_at ?? b.created_at;
          break;
      }
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });
    return list;
  }, [rows, search, filter, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await importationsApi.create({
        po_number: po,
        supplier_id: Number(supplierId),
        currency: DEFAULT_IMPORT_CURRENCY,
        incoterm: "FOB",
      });
      setPo("");
      toast.success("Ordem criada");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao criar";
      setError(msg);
      toast.error(msg);
    }
  }

  if (loading) {
    return (
      <Card>
        <PageHeader
          title={`Fila de ${fieldLabel("Importations")}`}
          subtitle="Visão operacional estilo planilha — clique na linha para abrir a Central da Ordem."
        />
        <LoadingState />
      </Card>
    );
  }

  return (
    <Card>
      <PageHeader
        title={`Fila de ${fieldLabel("Importations")}`}
        subtitle="Visão operacional estilo planilha — clique na linha para abrir a Central da Ordem."
        actions={
          <Button variant="secondary" onClick={() => exportCsv(filtered)}>
            Exportar CSV
          </Button>
        }
      />

      {error && <p className="error">{error}</p>}

      <form className="inline-form" onSubmit={handleCreate}>
        <input placeholder="Nº ordem" value={po} onChange={(e) => setPo(e.target.value)} required />
        <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required>
          <option value="">Fornecedor</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <Button type="submit">Nova ordem</Button>
      </form>

      <div className="search-bar">
        <input
          placeholder="Buscar ordem ou fornecedor..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

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

      {filtered.length === 0 ? (
        <EmptyState title="Nenhuma ordem encontrada" />
      ) : (
        <div className="order-queue__scroll">
          <Table>
            <thead>
              <tr>
                <th className="sortable" onClick={() => toggleSort("po_number")}>
                  Ordem
                </th>
                <th>Ano</th>
                <th className="sortable" onClick={() => toggleSort("supplier_name")}>
                  Fornecedor
                </th>
                <th className="sortable" onClick={() => toggleSort("status")}>
                  Status
                </th>
                <th>Valor faturado</th>
                <th>Pago</th>
                <th className="sortable num" onClick={() => toggleSort("consolidated_balance")}>
                  Saldo a pagar
                </th>
                <th>A despachar</th>
                <th>Pendências</th>
                <th className="sortable" onClick={() => toggleSort("updated_at")}>
                  Atualização
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr
                  key={r.id}
                  className="order-queue__row"
                  onClick={() => navigate(`/importacoes/${r.id}/resumo`)}
                >
                  <td>
                    <span className="row__po">{r.po_number}</span>
                  </td>
                  <td>{yearFrom(r.created_at)}</td>
                  <td>{r.supplier_name ?? emptyDash(null)}</td>
                  <td>
                    <Badge status={r.status}>{statusLabel(r.status)}</Badge>
                  </td>
                  <td className="num">
                    {r.total_invoiced != null
                      ? `${r.currency} ${Number(r.total_invoiced).toLocaleString("pt-BR")}`
                      : emptyDash(null)}
                  </td>
                  <td className="num">
                    {r.total_paid != null
                      ? `${r.currency} ${Number(r.total_paid).toLocaleString("pt-BR")}`
                      : emptyDash(null)}
                  </td>
                  <td className="num">
                    {r.consolidated_balance != null
                      ? `${r.currency} ${Number(r.consolidated_balance).toLocaleString("pt-BR")}`
                      : emptyDash(null)}
                  </td>
                  <td className="num">{r.to_dispatch ?? emptyDash(null)}</td>
                  <td className="num">{r.pending_actions_count || emptyDash(null)}</td>
                  <td>{fmtDate(r.updated_at ?? r.created_at)}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <Button variant="ghost" className="ui-btn--sm" onClick={() => navigate(`/importacoes/${r.id}/resumo`)}>
                      Abrir ordem
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </Card>
  );
}
