import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  ContextBreadcrumb,
  DetailDrawer,
  EmptyState,
  ErrorState,
  FilterBar,
  FxDisplay,
  KpiStrip,
  LoadingState,
  MoneyDisplay,
  PageHeader,
  StatusBadge,
} from "../../ui";
import { fetchApQueue, type ApQueueResponse } from "../reporting/reportingApi";

type Props = { user: User };

function canReadReporting(user: User) {
  if (user.role === "admin") return true;
  return (user.permissions ?? []).includes("reporting:read");
}

export function ApQueuePage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<ApQueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);

  const query = useMemo(
    () => ({
      status: params.get("status") || undefined,
      currency: params.get("currency") || undefined,
      order_id: params.get("order_id") || undefined,
      invoice_id: params.get("invoice_id") || undefined,
      supplier_id: params.get("supplier_id") || undefined,
      pending: params.get("pending") || undefined,
      due_before: params.get("due_before") || undefined,
      due_after: params.get("due_after") || undefined,
      limit: params.get("limit") || "50",
      offset: params.get("offset") || "0",
    }),
    [params],
  );

  const load = useCallback(() => {
    if (!canReadReporting(user)) {
      setError("Sem permissão reporting:read");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    void fetchApQueue(query)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"))
      .finally(() => setLoading(false));
  }, [query, user]);

  useEffect(() => {
    load();
  }, [load]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    next.delete("offset");
    setParams(next);
  }

  if (!canReadReporting(user)) {
    return <ErrorState message="Sem permissão para Contas a pagar (reporting)." />;
  }

  const kpis = data?.kpis ?? {};
  const uniqueSuppliers = useMemo(() => {
    if (!data?.items?.length) return [] as string[];
    const names = new Set(
      data.items
        .map((r) => (typeof r.supplier_name === "string" ? r.supplier_name : null))
        .filter((n): n is string => !!n),
    );
    return [...names];
  }, [data]);
  const singleSupplierContext = uniqueSuppliers.length === 1 ? uniqueSuppliers[0] : null;

  return (
    <section className="panel dense" data-testid="ap-queue-page">
      <ContextBreadcrumb items={[{ label: "Financeiro" }, { label: "Contas a pagar" }]} />
      <PageHeader
        title="Contas a pagar"
        subtitle={
          singleSupplierContext
            ? `Fila operacional · ${singleSupplierContext} · ordenação: vencidos primeiro`
            : "Fila operacional de Payables · ordenação: vencidos primeiro"
        }
        actions={
          <button type="button" className="btn" onClick={load} data-testid="ap-refresh">
            Atualizar
          </button>
        }
      />
      {error ? <ErrorState message={error} /> : null}
      <KpiStrip
        items={[
          { label: "Vencido", value: String(kpis.overdue_balance ?? "—"), hint: `${kpis.overdue_count ?? 0} títulos` },
          { label: "Hoje", value: String(kpis.due_today_balance ?? "—") },
          { label: "Próx. 7d", value: String(kpis.next_7d_balance ?? "—") },
          { label: "Saldo aberto", value: String(kpis.open_balance ?? "—") },
          {
            label: "Candidatos unalloc.",
            value: String(kpis.unallocated_candidates_total ?? "—"),
            hint: "Não são relações allocation",
          },
        ]}
      />
      <FilterBar>
        <label>
          Status
          <select
            data-testid="ap-filter-status"
            value={params.get("status") ?? ""}
            onChange={(e) => setFilter("status", e.target.value)}
          >
            <option value="">Abertos</option>
            <option value="OPEN">OPEN</option>
            <option value="PARTIALLY_PAID">PARTIALLY_PAID</option>
            <option value="PAID">PAID</option>
          </select>
        </label>
        <label>
          Pendência
          <select
            data-testid="ap-filter-pending"
            value={params.get("pending") ?? ""}
            onChange={(e) => setFilter("pending", e.target.value)}
          >
            <option value="">Todas</option>
            <option value="OVERDUE">OVERDUE</option>
            <option value="OPEN_BALANCE">OPEN_BALANCE</option>
          </select>
        </label>
        <label>
          Moeda
          <input
            data-testid="ap-filter-currency"
            value={params.get("currency") ?? ""}
            onChange={(e) => setFilter("currency", e.target.value.toUpperCase())}
            placeholder="EUR"
          />
        </label>
        <label>
          Ordem
          <input
            data-testid="ap-filter-order"
            value={params.get("order_id") ?? ""}
            onChange={(e) => setFilter("order_id", e.target.value)}
          />
        </label>
      </FilterBar>
      {loading ? <LoadingState /> : null}
      {!loading && data && data.items.length === 0 ? <EmptyState message="Nada a pagar no filtro" /> : null}
      {data && data.items.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table dense" data-testid="ap-table">
            <thead>
              <tr>
                <th>Vencimento</th>
                <th>Atraso</th>
                <th>Invoice</th>
                <th>Ordem</th>
                <th>Moeda</th>
                <th className="num">Valor</th>
                <th className="num">Alocado</th>
                <th className="num">Saldo</th>
                <th className="num">FX proj.</th>
                <th className="num">BRL proj.</th>
                <th>Status</th>
                <th>Pendências</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((row) => (
                <tr
                  key={String(row.id)}
                  data-testid={`ap-row-${row.id}`}
                  onClick={() => setSelected(row)}
                  className="row-click"
                >
                  <td>{String(row.due_date)}</td>
                  <td>{Number(row.days_overdue) > 0 ? String(row.days_overdue) : "—"}</td>
                  <td>
                    <Link to={`/invoices/${row.invoice_id}`} onClick={(e) => e.stopPropagation()}>
                      {String(row.invoice_number ?? row.invoice_id)}
                    </Link>
                  </td>
                  <td>
                    <Link to={`/orders/${row.order_id}`} onClick={(e) => e.stopPropagation()}>
                      #{String(row.order_id)}
                    </Link>
                  </td>
                  <td>{String(row.currency)}</td>
                  <td className="num">
                    <MoneyDisplay amount={String(row.amount)} />
                  </td>
                  <td className="num">
                    <MoneyDisplay amount={String(row.allocated)} />
                  </td>
                  <td className="num">
                    <MoneyDisplay amount={String(row.balance)} />
                  </td>
                  <td className="num">
                    <FxDisplay rate={row.fx_projected_rate as string | null} />
                  </td>
                  <td className="num">
                    <MoneyDisplay amount={row.fx_projected_brl as string | null} currency="BRL" />
                  </td>
                  <td>
                    <StatusBadge status={String(row.status)} />
                  </td>
                  <td>{Array.isArray(row.pendencies) ? (row.pendencies as string[]).join(", ") || "—" : "—"}</td>
                  <td>
                    <Link to={`/payables/${row.id}/fx`} onClick={(e) => e.stopPropagation()}>
                      FX
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            {data.total} no filtro · página offset {data.offset} / limit {data.limit} · {data.sort}
          </p>
        </div>
      ) : null}

      <DetailDrawer
        open={!!selected}
        title={`Payable #${selected?.id ?? ""}`}
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div className="stack">
            <p>
              <StatusBadge status={String(selected.status)} /> ·{" "}
              <MoneyDisplay amount={String(selected.balance)} currency={String(selected.currency)} />
            </p>
            <p className="muted">
              Fornecedor:{" "}
              {selected.supplier_resolved === false
                ? "não resolvido"
                : String(selected.supplier_name ?? selected.supplier_id ?? "—")}
            </p>
            <p>
              <Link to={`/invoices/${selected.invoice_id}`}>Abrir invoice</Link>
              {" · "}
              <Link to={`/orders/${selected.order_id}`}>Cockpit ordem</Link>
              {" · "}
              <Link to={`/payables/${selected.id}/fx`}>FX</Link>
              {" · "}
              <Link to="/payments/new">Registrar payment</Link>
            </p>
            <p className="muted">Candidatos unallocated não são relações — ver bloco da fila.</p>
          </div>
        ) : null}
      </DetailDrawer>
    </section>
  );
}
