import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listInvoices, type InvoiceListItem } from "./billingApi";
import {
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  formatDateOnly,
  MoneyDisplay,
  RowLink,
  StatusBadge,
} from "../../ui";
import { useListReturn } from "../../navigation/useListReturn";
import { INVOICES_QUEUE_COLUMNS } from "./invoicesQueueColumns";

type Props = { user: User };

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "", label: "Todas" },
  { value: "DRAFT", label: "Rascunho" },
  { value: "ISSUED", label: "Emitida" },
  { value: "CANCELLED", label: "Cancelada" },
];

export function InvoicesListPage({ user: _user }: Props) {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const [rows, setRows] = useState<InvoiceListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  useListReturn("/invoices", selectedId);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setRows(null);
      try {
        const data = await listInvoices(status ? { status } : undefined);
        if (!cancelled) setRows(data as InvoiceListItem[]);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status]);

  function setStatus(value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete("status");
    else next.set("status", value);
    setParams(next);
  }

  const statusLabel = STATUS_CHIPS.find((c) => c.value === status)?.label;
  const activeFilters = status
    ? [
        {
          id: "status",
          label: `Status: ${statusLabel ?? status}`,
          onRemove: () => setStatus(""),
        },
      ]
    : undefined;

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando faturas…" />;

  return (
    <section className="panel dense" data-testid="invoices-list">
      <PageHeader title="Faturas" subtitle="Uma fatura por pedido" />
      <div className="queue-shell">
        <FilterBar
          primary={
            <div
              className="filter-chip-group"
              data-testid="invoices-status-filter"
              role="group"
              aria-label="Status"
            >
              {STATUS_CHIPS.map((chip) => (
                <FilterChip
                  key={chip.value || "all"}
                  pressed={status === chip.value}
                  data-testid={`invoices-status-${chip.value || "all"}`}
                  onClick={() => setStatus(chip.value)}
                >
                  {chip.label}
                </FilterChip>
              ))}
            </div>
          }
          activeFilters={activeFilters}
          onClearAll={status ? () => setStatus("") : undefined}
        />
      </div>
      {rows.length === 0 ? (
        <EmptyState message="Nenhuma fatura neste filtro" orientation="Ajuste o status ou emita a partir de um pedido." />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="invoices-table"
            columns={INVOICES_QUEUE_COLUMNS}
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

export function PayablesListPage({ user: _user }: Props) {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/payables?limit=100", { credentials: "include" });
        if (!res.ok) throw new Error(await res.text());
        const data = (await res.json()) as Array<Record<string, unknown>>;
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando contas a pagar…" />;

  return (
    <section className="panel dense" data-testid="payables-list-page">
      <PageHeader
        title="Contas a pagar"
        subtitle="Lista básica — use a fila operacional enriquecida quando disponível"
      />
      {rows.length === 0 ? <EmptyState message="Nenhuma obrigação" /> : null}
      <OperationalTable density="finance">
        <thead>
          <tr>
            <th>Fatura</th>
            <th>Vencimento</th>
            <th className="num">Saldo</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p) => (
            <tr key={String(p.id)}>
              <td>
                <RowLink to={`/invoices/${p.invoice_id}`}>
                  {String(p.invoice_number ?? "—")}
                </RowLink>
              </td>
              <td>{formatDateOnly(p.due_date as string)}</td>
              <td className="num">
                <MoneyDisplay amount={p.balance as string} currency={p.currency as string} />
              </td>
              <td>
                <StatusBadge status={String(p.status)} entity="payable" />
              </td>
            </tr>
          ))}
        </tbody>
      </OperationalTable>
    </section>
  );
}
