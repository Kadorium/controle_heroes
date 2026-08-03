import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { canReadCustoms, canWriteCustoms } from "./customsPermissions";
import { listImportProcesses, type ImportProcessListItem } from "./customsApi";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  KpiStrip,
  LoadingState,
  PageHeader,
  PaginationSummary,
  StatusBadge,
} from "../../ui";

type Props = { user: User };

const PAGE_LIMIT = 50;

const STATUS_CHIPS = [
  { value: "", label: "Todos" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "SUBMITTED", label: "Submetido" },
  { value: "IN_CLEARANCE", label: "Em liberação" },
  { value: "PARTIALLY_CLEARED", label: "Parcial" },
  { value: "CLEARED", label: "Liberado" },
  { value: "CANCELLED", label: "Cancelado" },
];

export function CustomsListPage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") ?? "";
  const [rows, setRows] = useState<ImportProcessListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!canReadCustoms(user)) return;
    let cancelled = false;
    void (async () => {
      setRows(null);
      setError(null);
      try {
        const data = await listImportProcesses({
          status: statusFilter || undefined,
          limit: PAGE_LIMIT,
          offset: 0,
        });
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) {
          const err = e as Error & { status?: number };
          if (err.status === 403) setError("Sem permissão para processos aduaneiros.");
          else setError(e instanceof Error ? e.message : "Erro");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [statusFilter, user, reloadKey]);

  const kpis = useMemo(() => {
    const all = rows ?? [];
    const count = (s: string) => all.filter((r) => r.status === s).length;
    return [
      { label: "Total", value: all.length, "data-testid": "kpi-customs-total" },
      { label: "Rascunho", value: count("DRAFT"), "data-testid": "kpi-customs-draft" },
      { label: "Submetido", value: count("SUBMITTED"), "data-testid": "kpi-customs-submitted" },
      {
        label: "Em liberação",
        value: count("IN_CLEARANCE") + count("PARTIALLY_CLEARED"),
        "data-testid": "kpi-customs-clearance",
      },
      { label: "Liberado", value: count("CLEARED"), "data-testid": "kpi-customs-cleared" },
    ];
  }, [rows]);

  if (!canReadCustoms(user)) {
    return <ErrorState message="Sem permissão para processos aduaneiros." />;
  }
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
  if (rows === null) return <LoadingState message="Carregando processos…" />;

  return (
    <div data-testid="customs-list-page">
      <ContextBreadcrumb items={[{ label: "Aduana" }, { label: "Processos" }]} />
      <PageHeader
        title="Processos aduaneiros"
        subtitle="Fila operacional · origem aduaneira"
        actions={
          canWriteCustoms(user) ? (
            <Link className="btn btn-primary" to="/customs/new" data-testid="customs-new-link">
              Novo processo
            </Link>
          ) : null
        }
      />
      <KpiStrip items={kpis} />
      <FilterBar>
        {STATUS_CHIPS.map((c) => (
          <FilterChip
            key={c.value || "all"}
            pressed={statusFilter === c.value}
            onClick={() => {
              const next = new URLSearchParams(params);
              if (!c.value) next.delete("status");
              else next.set("status", c.value);
              setParams(next);
            }}
          >
            {c.label}
          </FilterChip>
        ))}
      </FilterBar>
      {rows.length === 0 ? (
        <EmptyState
          title="Nenhum processo"
          message="Crie um processo para vincular faturas e embarques."
          action={
            canWriteCustoms(user) ? (
              <Link className="btn btn-primary" to="/customs/new">
                Novo processo
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <table className="operational-table" data-testid="customs-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Ref. externa</th>
                <th>Status</th>
                <th>Faturas</th>
                <th>Embarques</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/customs/${r.id}`} data-testid={`customs-row-${r.id}`}>
                      {r.code}
                    </Link>
                  </td>
                  <td>{r.external_reference || "—"}</td>
                  <td>
                    <StatusBadge status={r.status} entity="customs" />
                  </td>
                  <td>{r.invoice_count}</td>
                  <td>{r.shipment_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PaginationSummary offset={0} limit={PAGE_LIMIT} loadedCount={rows.length} />
        </>
      )}
    </div>
  );
}
