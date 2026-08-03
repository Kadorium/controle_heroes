import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { canWriteOrders } from "./orderTotals";
import { fetchOrdersList, type OrderListRow } from "../reporting/reportingApi";
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
  PaginationSummary,
} from "../../ui";
import { createOrdersQueueColumns } from "./ordersQueueColumns";

type Props = { user: User };

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "CONFIRMED", label: "Confirmado" },
  { value: "CANCELLED", label: "Cancelado" },
];

export function OrdersListPage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") ?? "";
  const [rows, setRows] = useState<OrderListRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);

  useListReturn("/orders", selectedId);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setRows(null);
      try {
        const data = await fetchOrdersList({
          status: statusFilter || undefined,
          limit: 50,
        });
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [statusFilter]);

  function setStatus(value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete("status");
    else next.set("status", value);
    setParams(next);
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/orders", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    () => createOrdersQueueColumns({ returnTo, onRememberRow: rememberRow }),
    [returnTo, rememberRow],
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

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando pedidos…" />;

  return (
    <section className="panel dense" data-testid="orders-list-page">
      <PageHeader
        title="Pedidos"
        subtitle="Fila operacional de compras"
        actions={
          canWriteOrders(user) ? (
            <Link className="ui-button" to="/orders/new" data-testid="orders-new-cta">
              Novo pedido
            </Link>
          ) : null
        }
      />
      <div className="queue-shell">
        <FilterBar
          primary={
            <div
              className="filter-chip-group"
              data-testid="orders-status-filter"
              role="group"
              aria-label="Status"
            >
              {STATUS_CHIPS.map((chip) => (
                <FilterChip
                  key={chip.value || "all"}
                  pressed={statusFilter === chip.value}
                  data-testid={`orders-status-${chip.value || "all"}`}
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
          message="Nenhum pedido neste filtro"
          orientation="Ajuste o status ou crie um novo pedido."
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="orders-table"
            columns={columns}
            rows={rows}
            getRowId={(row) => String(row.id)}
            selectedId={selectedId}
            onRowClick={(row) => rememberRow(row.id)}
          />
          <PaginationSummary offset={0} limit={50} loadedCount={rows.length} />
        </>
      )}
    </section>
  );
}
