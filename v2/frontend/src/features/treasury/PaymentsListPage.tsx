import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
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
import { canWriteTreasury, listPayments, type Payment } from "./treasuryApi";
import { useListReturn } from "../../navigation/useListReturn";
import { PAYMENTS_QUEUE_COLUMNS } from "./paymentsQueueColumns";

type Props = { user: User };

export function PaymentsListPage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const unallocatedOnly = params.get("unallocated_only") === "1";
  const [rows, setRows] = useState<Payment[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  useListReturn("/payments", selectedId);

  useEffect(() => {
    void listPayments({ unallocated_only: unallocatedOnly || undefined })
      .then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [unallocatedOnly]);

  function setUnallocated(value: boolean) {
    const next = new URLSearchParams(params);
    if (value) next.set("unallocated_only", "1");
    else next.delete("unallocated_only");
    setParams(next);
  }

  const activeFilters = unallocatedOnly
    ? [
        {
          id: "residual",
          label: "Somente crédito em aberto",
          onRemove: () => setUnallocated(false),
        },
      ]
    : undefined;

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando pagamentos…" />;

  return (
    <section className="panel dense" data-testid="payments-list">
      <PageHeader
        title="Pagamentos realizados"
        subtitle="Dinheiro que saiu do caixa — residual ainda não aplicado a Contas a pagar"
        actions={
          canWriteTreasury(user) ? (
            <Link className="ui-button" to="/payments/new" data-testid="new-payment">
              Novo pagamento
            </Link>
          ) : null
        }
      />
      <div className="queue-shell">
        <FilterBar
          primary={
            <div
              className="filter-chip-group"
              data-testid="payments-unallocated-filter"
              role="group"
              aria-label="Crédito em aberto"
            >
              <FilterChip pressed={!unallocatedOnly} onClick={() => setUnallocated(false)}>
                Todos
              </FilterChip>
              <FilterChip
                pressed={unallocatedOnly}
                data-testid="payments-residual-only"
                onClick={() => setUnallocated(true)}
              >
                Somente crédito em aberto
              </FilterChip>
            </div>
          }
          activeFilters={activeFilters}
          onClearAll={unallocatedOnly ? () => setUnallocated(false) : undefined}
        />
      </div>
      {rows.length === 0 ? (
        <EmptyState
          message="Nenhum pagamento neste filtro"
          orientation="Registre um pagamento ou limpe o filtro de residual."
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="payments-table"
            columns={PAYMENTS_QUEUE_COLUMNS}
            rows={rows}
            getRowId={(row) => String(row.id)}
            selectedId={selectedId}
            onRowClick={(row) => setSelectedId(String(row.id))}
          />
          <PaginationSummary offset={0} limit={50} loadedCount={rows.length} />
        </>
      )}
    </section>
  );
}
