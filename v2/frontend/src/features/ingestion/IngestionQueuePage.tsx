import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import {
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  OperationalTable,
  PageHeader,
} from "../../ui";
import { deleteIngestionDocument, fetchStagingQueue, type DocumentSummary } from "./ingestionApi";
import { createIngestionQueueColumns } from "./ingestionQueueColumns";
import { IntakePanel } from "./IntakePanel";

type Props = { user: User };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "IN_REVIEW", label: "Em revisão" },
  { value: "READY", label: "Pronto" },
  { value: "REJECTED", label: "Rejeitado" },
];

const QUEUE_SUBTITLE = "Envie os documentos e confira antes de gravar";

export function IngestionQueuePage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") ?? "";
  const [rows, setRows] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [refreshKey, setRefreshKey] = useState(0);

  const reloadQueue = useCallback(() => setRefreshKey((k) => k + 1), []);

  useListReturn("/ingestion", selectedId);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setRows(null);
      setError(null);
      try {
        const data = await fetchStagingQueue({
          review_status: statusFilter || undefined,
        });
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [statusFilter, refreshKey]);

  function setStatus(value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete("status");
    else next.set("status", value);
    setParams(next);
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/ingestion", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const onDeleteRow = useCallback(
    async (row: DocumentSummary) => {
      if (
        !window.confirm(
          `Excluir a importação #${row.id} em definitivo?\nSó funciona se ela ainda não criou pedido.`,
        )
      ) {
        return;
      }
      try {
        await deleteIngestionDocument(row.id);
        reloadQueue();
      } catch (e) {
        window.alert(e instanceof Error ? e.message : "Não foi possível excluir");
      }
    },
    [reloadQueue],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    () =>
      createIngestionQueueColumns({
        returnTo,
        onRememberRow: rememberRow,
        onDeleteRow: canWrite(user) ? onDeleteRow : undefined,
      }),
    [returnTo, rememberRow, onDeleteRow, user],
  );

  const statusLabel = STATUS_CHIPS.find((c) => c.value === statusFilter)?.label;
  const activeFilters = statusFilter
    ? [
        {
          id: "status",
          label: `Status: ${statusLabel ?? statusFilter}`,
          onRemove: () => setStatus(""),
        },
      ]
    : undefined;

  if (error) {
    return (
      <section className="panel dense" data-testid="ingestion-queue-page">
        <PageHeader title="Ingestão" subtitle={QUEUE_SUBTITLE} />
        {canWrite(user) ? <IntakePanel user={user} onAdapterSuccess={reloadQueue} /> : null}
        <ErrorState message={error} onRetry={reloadQueue} />
      </section>
    );
  }

  if (rows === null) {
    return (
      <section className="panel dense" data-testid="ingestion-queue-page">
        <PageHeader title="Ingestão" subtitle={QUEUE_SUBTITLE} />
        {canWrite(user) ? <IntakePanel user={user} onAdapterSuccess={reloadQueue} /> : null}
        <LoadingState message="Carregando fila…" />
      </section>
    );
  }

  return (
    <section className="panel dense" data-testid="ingestion-queue-page">
      <PageHeader title="Ingestão" subtitle={QUEUE_SUBTITLE} />
      {canWrite(user) ? <IntakePanel user={user} onAdapterSuccess={reloadQueue} /> : null}
      <div className="queue-shell">
        <FilterBar
          primary={
            <div
              className="filter-chip-group"
              data-testid="ingestion-status-filter"
              role="group"
              aria-label="Status"
            >
              {STATUS_CHIPS.map((chip) => (
                <FilterChip
                  key={chip.value || "all"}
                  pressed={statusFilter === chip.value}
                  data-testid={`ingestion-status-${chip.value || "all"}`}
                  onClick={() => setStatus(chip.value)}
                >
                  {chip.label}
                </FilterChip>
              ))}
            </div>
          }
          activeFilters={activeFilters}
          onClearAll={statusFilter ? () => setStatus("") : undefined}
        />
      </div>
      {rows.length === 0 ? (
        <EmptyState
          message="Nenhuma importação na fila"
          orientation="Envie os documentos acima, extraia os dados e confira antes de gravar."
        />
      ) : (
        <OperationalTable
          density="standard"
          data-testid="ingestion-queue-table"
          columns={columns}
          rows={rows}
          getRowId={(row) => String(row.id)}
          selectedId={selectedId}
          onRowClick={(row) => rememberRow(row.id)}
        />
      )}
    </section>
  );
}
