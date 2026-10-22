import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { User } from "../auth/types";
import { canReadCosting, canWriteCosting } from "./costingPermissions";
import { ensureCostingCase, listCostingQueue, type CostingQueueRow } from "./costingApi";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  PageHeader,
  StatusBadge,
} from "../../ui";

type Props = { user: User };

const SUBTITLE =
  "Inclui tributos em valor bruto. Não representa tratamento contábil ou fiscal de recuperabilidade.";

function situation(row: CostingQueueRow): string {
  if (!row.id) return "Sem caso";
  if (row.partial_coverage) return "Cobertura incompleta";
  if (row.current_status === "PUBLISHED") return "Publicado";
  if (row.current_kind) return row.current_kind;
  return "Rascunho possível";
}

export function CostingListPage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const filter = params.get("sit") ?? "";
  const [rows, setRows] = useState<CostingQueueRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    listCostingQueue()
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!canReadCosting(user)) {
    return <ErrorState message="É preciso costing:read." />;
  }
  if (error) return <ErrorState message={error} />;
  if (!rows) return <LoadingState />;

  const filtered = rows.filter((r) => {
    if (!filter) return true;
    if (filter === "blocked") return r.partial_coverage === true;
    if (filter === "ready") return r.current_status === "PUBLISHED";
    if (filter === "empty") return !r.id;
    return true;
  });

  async function openCase(processId: number) {
    setBusy(processId);
    try {
      const caseRow = await ensureCostingCase(processId);
      window.location.assign(`/costing/${caseRow.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  return (
    <div data-testid="costing-queue">
      <ContextBreadcrumb items={[{ label: "Custos" }, { label: "Custos de importação" }]} />
      <PageHeader
        title="Custo desembarcado por produto"
        subtitle={SUBTITLE}
      />
      <FilterBar>
        <FilterChip pressed={!filter} onClick={() => setParams({})}>
          Todos
        </FilterChip>
        <FilterChip pressed={filter === "blocked"} onClick={() => setParams({ sit: "blocked" })}>
          Cobertura incompleta
        </FilterChip>
        <FilterChip pressed={filter === "ready"} onClick={() => setParams({ sit: "ready" })}>
          Publicado
        </FilterChip>
      </FilterBar>
      {filtered.length === 0 ? (
        <EmptyState
          title="Nenhum processo nesta fila"
          message="Abra um processo aduaneiro para iniciar o custo desembarcado."
          action={
            <Link to="/customs" className="btn">
              Ir para processos
            </Link>
          }
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Processo</th>
                <th>Referência</th>
                <th>Status aduaneiro</th>
                <th>Situação do custo</th>
                <th>Total BRL</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.import_process_id}>
                  <td>{row.process_code}</td>
                  <td>{row.process_reference || "—"}</td>
                  <td>
                    <StatusBadge status={row.process_status} entity="customs" />
                  </td>
                  <td>{situation(row)}</td>
                  <td>{row.included_total_brl ?? "—"}</td>
                  <td>
                    {row.id ? (
                      <Link to={`/costing/${row.id}`}>Abrir</Link>
                    ) : canWriteCosting(user) ? (
                      <button
                        type="button"
                        className="btn"
                        disabled={busy === row.import_process_id}
                        onClick={() => void openCase(row.import_process_id)}
                      >
                        Iniciar
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
