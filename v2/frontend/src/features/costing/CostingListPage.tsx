import { Link, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { User } from "../auth/types";
import { canReadCosting, canWriteCosting } from "./costingPermissions";
import { ensureCostingCase, readCostingQueuePage, type CostingQueueRow, type CostingQueuePage } from "./costingApi";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  PageHeader,
  StatusBadge,
  TextInput,
  Button,
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
  const requestedFilter = params.get("sit") ?? "";
  const filter = ["blocked", "ready", "empty"].includes(requestedFilter) ? requestedFilter : "";
  const query = params.get("q") ?? "";
  const requestedOffset = Number(params.get("offset"));
  const offset = Number.isSafeInteger(requestedOffset) && requestedOffset > 0 ? requestedOffset : 0;
  const [data, setData] = useState<CostingQueuePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setData(null);
    if (!canReadCosting(user)) return;
    readCostingQueuePage(new URLSearchParams({ q: query, situation: filter, limit: "50", offset: String(offset) }))
      .then((data) => {
        if (!cancelled) setData(data);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [query, filter, offset, user]);

  if (!canReadCosting(user)) {
    return <ErrorState message="É preciso costing:read." />;
  }
  if (error) return <ErrorState message={error} />;
  function changeFilter(sit: string) {
    const next = new URLSearchParams(params);
    if (sit) next.set("sit", sit); else next.delete("sit");
    next.delete("offset"); setParams(next);
  }

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
      <ContextBreadcrumb items={[{ label: "Importações" }, { label: "Custo desembarcado" }]} />
      <PageHeader
        title="Custo desembarcado por produto"
        subtitle={SUBTITLE}
      />
      <FilterBar>
        <form style={{display:"flex", gap:"8px", alignItems:"center"}} onSubmit={event => { event.preventDefault(); const next = new URLSearchParams(params); const value = String(new FormData(event.currentTarget).get("q") || "").trim(); if (value) next.set("q", value); else next.delete("q"); next.delete("offset"); setParams(next); }}>
          <label className="sr-only" htmlFor="costing-search">Código ou referência da operação</label>
          <TextInput id="costing-search" name="q" key={query} defaultValue={query} placeholder="Código ou referência" maxLength={200} />
          <Button variant="secondary" type="submit">Buscar</Button>
        </form>
        <FilterChip pressed={!filter} onClick={() => changeFilter("")}>
          Todos
        </FilterChip>
        <FilterChip pressed={filter === "blocked"} onClick={() => changeFilter("blocked")}>
          Cobertura incompleta
        </FilterChip>
        <FilterChip pressed={filter === "ready"} onClick={() => changeFilter("ready")}>
          Publicado
        </FilterChip>
      </FilterBar>
      {!data ? <LoadingState /> : data.items.length === 0 ? (
        <EmptyState
          title="Nenhuma operação encontrada"
          message={query || filter ? "Revise a busca e a situação selecionadas." : "Abra uma operação para iniciar o custo desembarcado."}
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
              {data.items.map((row) => (
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
      {data && <nav aria-label="Páginas de custo" style={{display:"flex", gap:"12px", alignItems:"center", flexWrap:"wrap", marginTop:"12px"}}>
        <span>{data.total === 0 ? "0 operações" : `${offset + 1}–${offset + data.items.length} de ${data.total} operações`}</span>
        <Button variant="secondary" disabled={offset === 0} onClick={() => { const next = new URLSearchParams(params); next.set("offset", String(Math.max(0, offset - 50))); setParams(next); }}>Anterior</Button>
        <Button variant="secondary" disabled={offset + data.items.length >= data.total} onClick={() => { const next = new URLSearchParams(params); next.set("offset", String(offset + 50)); setParams(next); }}>Próxima</Button>
      </nav>}
    </div>
  );
}
