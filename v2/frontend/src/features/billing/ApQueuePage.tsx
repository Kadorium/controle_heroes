import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listSuppliers } from "../catalog/catalogApi";
import {
  Button,
  ContextBreadcrumb,
  DetailDrawer,
  EmptyState,
  EntityRef,
  ErrorState,
  FilterBar,
  FilterChip,
  FormField,
  FxDisplay,
  KpiStrip,
  LoadingState,
  MoneyDisplay,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  RowLink,
  SectionCard,
  SelectField,
  StatusBadge,
  SummaryGrid,
  TextInput,
  formatDateOnly,
  formatMoney,
  formatPendencies,
} from "../../ui";
import { fetchApQueue, type ApQueueResponse } from "../reporting/reportingApi";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import { AP_QUEUE_COLUMNS, type ApQueueRow } from "./apQueueColumns";

type Props = { user: User };

function canReadReporting(user: User) {
  if (user.role === "admin") return true;
  return (user.permissions ?? []).includes("reporting:read");
}

function kpiMoney(value: string | number | null | undefined, currency = "EUR") {
  if (value === null || value === undefined || value === "" || value === "—") return "—";
  return formatMoney(value, currency);
}

function localDateISO(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDaysISO(iso: string, days: number) {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  return localDateISO(dt);
}

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "", label: "Não canceladas" },
  { value: "OPEN", label: "Aberta" },
  { value: "PARTIALLY_PAID", label: "Parcialmente paga" },
  { value: "PAID", label: "Paga" },
  { value: "CANCELLED", label: "Cancelada" },
];

type DuePreset = "all" | "overdue" | "today" | "next7";

function duePresetFromParams(dueBefore: string | null, dueAfter: string | null, today: string): DuePreset | null {
  const yesterday = addDaysISO(today, -1);
  const tomorrow = addDaysISO(today, 1);
  const day7 = addDaysISO(today, 7);
  if (!dueBefore && !dueAfter) return "all";
  if (dueBefore === yesterday && !dueAfter) return "overdue";
  if (dueBefore === today && dueAfter === today) return "today";
  if (dueBefore === day7 && dueAfter === tomorrow) return "next7";
  return null;
}

const DUE_CHIPS: { id: DuePreset; label: string }[] = [
  { id: "all", label: "Todos os vencimentos" },
  { id: "overdue", label: "Vencidas" },
  { id: "today", label: "Vencem hoje" },
  { id: "next7", label: "Próximos 7 dias" },
];

/** `ALL` = sentinela FE para “Todos” (não enviado à API). Default operacional = OPEN_BALANCE. */
const SALDO_CHIPS: { value: string; label: string }[] = [
  { value: "ALL", label: "Todos" },
  { value: "OPEN_BALANCE", label: "Com saldo em aberto" },
];

export function ApQueuePage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState<ApQueueResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [suppliers, setSuppliers] = useState<{ id: number; name: string }[]>([]);
  useListReturn("/payables", selected ? String(selected.id) : null);

  const today = useMemo(() => localDateISO(), []);

  // Default operacional: pending=OPEN_BALANCE quando ausente na URL.
  useEffect(() => {
    if (!params.has("pending")) {
      const next = new URLSearchParams(params);
      next.set("pending", "OPEN_BALANCE");
      setParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- só no mount / primeira URL sem pending
  }, []);

  useEffect(() => {
    void listSuppliers()
      .then((rows) => setSuppliers(rows.map((s) => ({ id: s.id, name: s.name }))))
      .catch(() => setSuppliers([]));
  }, []);

  const query = useMemo(() => {
    const pendingRaw = params.get("pending");
    return {
      status: params.get("status") || undefined,
      currency: params.get("currency") || undefined,
      order_id: params.get("order_id") || undefined,
      invoice_id: params.get("invoice_id") || undefined,
      supplier_id: params.get("supplier_id") || undefined,
      pending: !pendingRaw || pendingRaw === "ALL" ? undefined : pendingRaw,
      due_before: params.get("due_before") || undefined,
      due_after: params.get("due_after") || undefined,
      limit: params.get("limit") || "50",
      offset: params.get("offset") || "0",
    };
  }, [params]);

  const load = useCallback(() => {
    if (!canReadReporting(user)) {
      setError("Sem permissão para Contas a pagar");
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

  function patchParams(mutate: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(params);
    mutate(next);
    next.delete("offset");
    setParams(next);
  }

  function setFilter(key: string, value: string) {
    patchParams((next) => {
      if (!value) next.delete(key);
      else next.set(key, value);
    });
  }

  function setDuePreset(preset: DuePreset) {
    patchParams((next) => {
      next.delete("due_before");
      next.delete("due_after");
      if (preset === "overdue") {
        next.set("due_before", addDaysISO(today, -1));
      } else if (preset === "today") {
        next.set("due_after", today);
        next.set("due_before", today);
      } else if (preset === "next7") {
        next.set("due_after", addDaysISO(today, 1));
        next.set("due_before", addDaysISO(today, 7));
      }
    });
  }

  function setSaldo(value: string) {
    patchParams((next) => {
      next.set("pending", value || "ALL");
    });
  }

  const uniqueSuppliers = useMemo(() => {
    if (!data?.items?.length) return [] as string[];
    const names = new Set(
      data.items
        .map((r) => (typeof r.supplier_name === "string" ? r.supplier_name : null))
        .filter((n): n is string => !!n),
    );
    return [...names];
  }, [data]);

  const statusValue = params.get("status") ?? "";
  const pendingValue = params.get("pending") ?? "OPEN_BALANCE";
  const duePreset = duePresetFromParams(params.get("due_before"), params.get("due_after"), today);

  const activeFilters = useMemo(() => {
    const chips: { id: string; label: string; onRemove: () => void }[] = [];
    if (statusValue) {
      const label = STATUS_CHIPS.find((c) => c.value === statusValue)?.label ?? statusValue;
      chips.push({ id: "status", label: `Status: ${label}`, onRemove: () => setFilter("status", "") });
    }
    if (duePreset && duePreset !== "all") {
      const label = DUE_CHIPS.find((c) => c.id === duePreset)?.label ?? duePreset;
      chips.push({ id: "due", label, onRemove: () => setDuePreset("all") });
    }
    if (pendingValue && pendingValue !== "OPEN_BALANCE") {
      const label = SALDO_CHIPS.find((c) => c.value === pendingValue)?.label ?? pendingValue;
      chips.push({ id: "saldo", label: `Saldo: ${label}`, onRemove: () => setSaldo("OPEN_BALANCE") });
    }
    if (params.get("currency")) {
      chips.push({
        id: "currency",
        label: `Moeda: ${params.get("currency")}`,
        onRemove: () => setFilter("currency", ""),
      });
    }
    if (params.get("order_id")) {
      chips.push({
        id: "order",
        label: `Pedido: ${params.get("order_id")}`,
        onRemove: () => setFilter("order_id", ""),
      });
    }
    if (params.get("supplier_id")) {
      const sid = params.get("supplier_id");
      const name = suppliers.find((s) => String(s.id) === sid)?.name ?? sid;
      chips.push({
        id: "supplier",
        label: `Fornecedor: ${name}`,
        onRemove: () => setFilter("supplier_id", ""),
      });
    }
    return chips;
  }, [statusValue, duePreset, pendingValue, params, suppliers]);

  if (!canReadReporting(user)) {
    return <ErrorState message="Sem permissão para Contas a pagar." />;
  }

  const kpis = data?.kpis ?? {};
  const singleSupplierContext = uniqueSuppliers.length === 1 ? uniqueSuppliers[0] : null;

  const invoiceLabel = (number: unknown) => {
    const n = typeof number === "string" && number.trim() ? number.trim() : null;
    return n ?? "—";
  };
  const orderLabel = (code: unknown) => {
    const c = typeof code === "string" && code.trim() ? code.trim() : null;
    return c ?? "—";
  };

  function clearAllFilters() {
    patchParams((next) => {
      next.delete("status");
      next.delete("due_before");
      next.delete("due_after");
      next.set("pending", "OPEN_BALANCE");
      next.delete("currency");
      next.delete("order_id");
      next.delete("supplier_id");
    });
  }

  const rows: ApQueueRow[] = (data?.items ?? []) as ApQueueRow[];

  return (
    <section className="panel dense" data-testid="ap-queue-page">
      <ContextBreadcrumb items={[{ label: "Financeiro" }, { label: "Contas a pagar" }]} />
      <PageHeader
        title="Contas a pagar"
        subtitle={
          singleSupplierContext
            ? `Fila operacional · ${singleSupplierContext} · vencidos primeiro`
            : "Fila operacional · vencidos primeiro"
        }
        actions={
          <Button type="button" variant="secondary" onClick={load} data-testid="ap-refresh">
            Atualizar
          </Button>
        }
      />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <KpiStrip
        items={[
          {
            label: "Vencido",
            value: kpiMoney(kpis.overdue_balance),
            hint: `${kpis.overdue_count ?? 0} títulos`,
            "data-testid": "kpi-overdue",
            onClick: () => setDuePreset("overdue"),
          },
          {
            label: "Hoje",
            value: kpiMoney(kpis.due_today_balance),
            "data-testid": "kpi-today",
            onClick: () => setDuePreset("today"),
          },
          {
            label: "Próx. 7d",
            value: kpiMoney(kpis.next_7d_balance),
            "data-testid": "kpi-next7",
            onClick: () => setDuePreset("next7"),
          },
          {
            label: "Saldo aberto",
            value: kpiMoney(kpis.open_balance),
            "data-testid": "kpi-open-balance",
            onClick: () => setSaldo("OPEN_BALANCE"),
          },
          {
            label: "Pagamentos com residual",
            value: kpiMoney(kpis.unallocated_candidates_total),
            hint: "Abre Pagamentos com residual",
            "data-testid": "kpi-unallocated",
            onClick: () => navigate("/payments?unallocated_only=1"),
          },
        ]}
      />
      <div className="queue-shell">
        <FilterBar
          primary={
            <>
              <div className="filter-chip-group" data-testid="ap-filter-status" role="group" aria-label="Status">
                {STATUS_CHIPS.map((chip) => (
                  <FilterChip
                    key={chip.value || "non-cancelled"}
                    pressed={statusValue === chip.value}
                    onClick={() => setFilter("status", chip.value)}
                  >
                    {chip.label}
                  </FilterChip>
                ))}
              </div>
              <div className="filter-chip-group" data-testid="ap-filter-saldo" role="group" aria-label="Saldo">
                {SALDO_CHIPS.map((chip) => (
                  <FilterChip
                    key={chip.value}
                    pressed={pendingValue === chip.value}
                    onClick={() => setSaldo(chip.value)}
                  >
                    {chip.label}
                  </FilterChip>
                ))}
              </div>
            </>
          }
          secondary={
            <>
              <div className="filter-chip-group" data-testid="ap-filter-due" role="group" aria-label="Vencimento">
                {DUE_CHIPS.map((chip) => (
                  <FilterChip
                    key={chip.id}
                    pressed={duePreset === chip.id}
                    onClick={() => setDuePreset(chip.id)}
                  >
                    {chip.label}
                  </FilterChip>
                ))}
              </div>
              <FormField label="Moeda" htmlFor="ap-currency">
                <TextInput
                  id="ap-currency"
                  data-testid="ap-filter-currency"
                  value={params.get("currency") ?? ""}
                  onChange={(e) => setFilter("currency", e.target.value.toUpperCase())}
                  placeholder="EUR"
                />
              </FormField>
              <FormField label="Pedido (ID)" htmlFor="ap-order" hint="Identificador numérico interno">
                <TextInput
                  id="ap-order"
                  data-testid="ap-filter-order"
                  value={params.get("order_id") ?? ""}
                  onChange={(e) => setFilter("order_id", e.target.value)}
                  placeholder="Ex.: 42"
                  inputMode="numeric"
                />
              </FormField>
              <FormField label="Fornecedor" htmlFor="ap-supplier">
                <SelectField
                  id="ap-supplier"
                  data-testid="ap-filter-supplier"
                  value={params.get("supplier_id") ?? ""}
                  onChange={(e) => setFilter("supplier_id", e.target.value)}
                  options={[
                    { value: "", label: "Todos" },
                    ...suppliers.map((s) => ({ value: String(s.id), label: s.name })),
                  ]}
                />
              </FormField>
            </>
          }
          activeFilters={activeFilters}
          onClearAll={clearAllFilters}
        />
      </div>
      {loading ? <LoadingState message="Carregando contas a pagar…" /> : null}
      {!loading && data && data.items.length === 0 ? (
        <EmptyState message="Nenhuma obrigação neste filtro" orientation="Limpe os filtros ou aguarde novas emissões." />
      ) : null}
      {data && data.items.length > 0 ? (
        <>
          <OperationalTable
            density="finance"
            data-testid="ap-table"
            columns={AP_QUEUE_COLUMNS}
            rows={rows}
            getRowId={(row) => String(row.id)}
            getRowTestId={(row) => `ap-row-${row.id}`}
            selectedId={selected ? String(selected.id) : null}
            onRowClick={(row) => {
              setSelected(row);
              saveReturnState("/payables", {
                search: window.location.search,
                scrollY: window.scrollY,
                selectedId: String(row.id),
              });
            }}
          />
          <PaginationSummary
            offset={Number(data.offset) || 0}
            limit={Number(data.limit) || 50}
            total={data.total}
            loadedCount={data.items.length}
          />
        </>
      ) : null}

      <DetailDrawer
        open={!!selected}
        title={
          selected
            ? selected.invoice_number
              ? `Obrigação · ${String(selected.invoice_number)}`
              : "Obrigação"
            : "Obrigação"
        }
        onClose={() => setSelected(null)}
      >
        {selected ? (
          <div className="stack">
            <SummaryGrid
              items={[
                {
                  label: "Status",
                  value: <StatusBadge status={String(selected.status)} entity="payable" />,
                },
                {
                  label: "Valor",
                  value: (
                    <MoneyDisplay amount={String(selected.amount)} currency={String(selected.currency)} />
                  ),
                },
                {
                  label: "Alocado",
                  value: (
                    <MoneyDisplay
                      amount={String(selected.allocated)}
                      currency={String(selected.currency)}
                    />
                  ),
                },
                {
                  label: "Saldo",
                  value: (
                    <MoneyDisplay
                      amount={String(selected.balance)}
                      currency={String(selected.currency)}
                    />
                  ),
                },
                {
                  label: "Fornecedor",
                  value: (
                    <EntityRef
                      primary={
                        (typeof selected.payee_display_name === "string" &&
                        selected.payee_display_name.trim()
                          ? selected.payee_display_name
                          : null) ||
                        (selected.supplier_resolved === false
                          ? null
                          : (selected.supplier_name as string | null))
                      }
                      missingLabel="Fornecedor não identificado"
                    />
                  ),
                },
                {
                  label: "Origem",
                  value:
                    selected.source_type === "CUSTOMS_FUNDING" ? "Numerário (Customs)" : "Fatura",
                },
                { label: "Vencimento", value: formatDateOnly(String(selected.due_date)) },
                {
                  label: "Pedido",
                  value:
                    orderLabel(selected.order_code) !== "—" ? (
                      <RowLink to={`/orders/${selected.order_id}`}>{orderLabel(selected.order_code)}</RowLink>
                    ) : (
                      "—"
                    ),
                },
                {
                  label: "Fatura",
                  value:
                    invoiceLabel(selected.invoice_number) !== "—" ? (
                      <RowLink to={`/invoices/${selected.invoice_id}`}>
                        {invoiceLabel(selected.invoice_number)}
                      </RowLink>
                    ) : (
                      "—"
                    ),
                },
                {
                  label: "Pendências",
                  value: formatPendencies(selected.pendencies),
                },
                {
                  label: "Câmbio / BRL",
                  value: (
                    <span className="stack-tight">
                      <FxDisplay rate={selected.fx_projected_rate as string | null} />
                      <MoneyDisplay
                        amount={selected.fx_projected_brl as string | null}
                        currency="BRL"
                      />
                    </span>
                  ),
                },
              ]}
            />
            <SectionCard title="Ações">
              <div className="stack-row stack-row--wrap">
                <RowLink to={`/invoices/${selected.invoice_id}`}>Abrir fatura</RowLink>
                <RowLink to={`/orders/${selected.order_id}`}>Cockpit do pedido</RowLink>
                <RowLink to={`/payables/${selected.id}/fx`}>Câmbio da obrigação</RowLink>
                <RowLink
                  to={`/payments/new?${new URLSearchParams({
                    supplier_id: String(selected.supplier_id ?? ""),
                    payable_id: String(selected.id ?? ""),
                    amount: String(selected.balance ?? ""),
                    currency: String(selected.currency ?? ""),
                    ...(selected.order_id != null ? { order_id: String(selected.order_id) } : {}),
                  }).toString()}`}
                  data-testid="ap-g02-new-payment"
                >
                  Novo pagamento
                </RowLink>
              </div>
            </SectionCard>
          </div>
        ) : null}
      </DetailDrawer>
    </section>
  );
}
