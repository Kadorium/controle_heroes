import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { canWriteLogistics } from "./shipmentPermissions";
import { listShipments, type ShipmentListItem } from "./shipmentsApi";
import { listLogisticsProviders, type LogisticsProvider } from "./providersApi";
import { SHIPMENT_MODAL_OPTIONS, providerDisplayName } from "./shipmentLabels";
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
  SelectField,
} from "../../ui";
import { createShipmentsQueueColumns } from "./shipmentsQueueColumns";

type Props = { user: User };

const STATUS_CHIPS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "PLANNED", label: "Planejado" },
  { value: "BOOKED", label: "Reservado" },
  { value: "IN_TRANSIT", label: "Em trânsito" },
  { value: "ARRIVED", label: "Chegou" },
];

export function ShipmentsListPage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const statusFilter = params.get("status") ?? "";
  const modalFilter = params.get("modal") ?? "";
  const providerFilter = params.get("provider") ?? "";
  const [rows, setRows] = useState<ShipmentListItem[] | null>(null);
  const [providers, setProviders] = useState<LogisticsProvider[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);

  useListReturn("/shipments", selectedId);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listLogisticsProviders({
          active_only: false,
          shipment_eligible_only: true,
          limit: 200,
        });
        if (!cancelled) setProviders(data);
      } catch {
        /* filtros degradam sem lista de prestadores */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setRows(null);
      try {
        const data = await listShipments({
          status: statusFilter || undefined,
          modal: modalFilter || undefined,
          logistics_provider_id: providerFilter ? Number(providerFilter) : undefined,
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
  }, [statusFilter, modalFilter, providerFilter]);

  function patchParams(mutator: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(params);
    mutator(next);
    setParams(next);
  }

  function setStatus(value: string) {
    patchParams((next) => {
      if (!value) next.delete("status");
      else next.set("status", value);
    });
  }

  function setModal(value: string) {
    patchParams((next) => {
      if (!value) next.delete("modal");
      else next.set("modal", value);
    });
  }

  function setProvider(value: string) {
    patchParams((next) => {
      if (!value) next.delete("provider");
      else next.set("provider", value);
    });
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/shipments", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    () => createShipmentsQueueColumns({ returnTo, onRememberRow: rememberRow }),
    [returnTo, rememberRow],
  );

  const statusLabel =
    statusFilter === "CANCELLED"
      ? "Anulados"
      : STATUS_CHIPS.find((c) => c.value === statusFilter)?.label;
  const modalLabelText = SHIPMENT_MODAL_OPTIONS.find((m) => m.value === modalFilter)?.label;
  const providerLabel = providers.find((p) => String(p.id) === providerFilter);

  const activeFilters = [
    statusFilter
      ? {
          id: "status",
          label: `Status: ${statusLabel ?? statusFilter}`,
          onRemove: () => setStatus(""),
        }
      : null,
    modalFilter
      ? {
          id: "modal",
          label: `Modal: ${modalLabelText ?? modalFilter}`,
          onRemove: () => setModal(""),
        }
      : null,
    providerFilter
      ? {
          id: "provider",
          label: `Prestador: ${providerLabel ? providerDisplayName(providerLabel) : providerFilter}`,
          onRemove: () => setProvider(""),
        }
      : null,
  ].filter(Boolean) as { id: string; label: string; onRemove: () => void }[];

  const clearAll =
    statusFilter || modalFilter || providerFilter
      ? () => {
          patchParams((next) => {
            next.delete("status");
            next.delete("modal");
            next.delete("provider");
          });
        }
      : undefined;

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando embarques…" />;

  return (
    <section className="panel dense" data-testid="shipments-list">
      <PageHeader
        title="Embarques"
        subtitle="Fila operacional de logística"
        actions={
          <>
            {canWriteLogistics(user) ? (
              <Link
                className="ui-button ui-button--secondary"
                to="/logistics-providers"
                data-testid="shipments-providers-cta"
              >
                Prestadores
              </Link>
            ) : null}
            {canWriteLogistics(user) ? (
              <Link className="ui-button" to="/shipments/new" data-testid="shipments-new-cta">
                Novo embarque
              </Link>
            ) : null}
          </>
        }
      />
      <div className="queue-shell">
        <FilterBar
          primary={
            <div className="stack-row" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
              <div
                className="filter-chip-group"
                data-testid="shipments-status-filter"
                role="group"
                aria-label="Status"
              >
                {STATUS_CHIPS.map((chip) => (
                  <FilterChip
                    key={chip.value || "all"}
                    pressed={statusFilter === chip.value}
                    data-testid={`shipments-status-${chip.value || "all"}`}
                    onClick={() => setStatus(chip.value)}
                  >
                    {chip.label}
                  </FilterChip>
                ))}
                <FilterChip
                  pressed={statusFilter === "CANCELLED"}
                  data-testid="shipments-status-CANCELLED"
                  onClick={() => setStatus("CANCELLED")}
                >
                  Anulados
                </FilterChip>
              </div>
              <SelectField
                data-testid="shipments-modal-filter"
                aria-label="Filtrar por modal"
                value={modalFilter}
                onChange={(e) => setModal(e.target.value)}
                placeholder="Todos os modais"
                options={[...SHIPMENT_MODAL_OPTIONS]}
              />
              <SelectField
                data-testid="shipments-provider-filter"
                aria-label="Filtrar por prestador"
                value={providerFilter}
                onChange={(e) => setProvider(e.target.value)}
                placeholder="Todos os prestadores"
                options={providers.map((p) => ({
                  value: String(p.id),
                  label: providerDisplayName(p),
                }))}
              />
            </div>
          }
          activeFilters={activeFilters.length ? activeFilters : undefined}
          onClearAll={clearAll}
        />
      </div>
      {rows.length === 0 ? (
        <EmptyState
          message="Nenhum embarque neste filtro"
          orientation="Ajuste o status ou crie um novo embarque."
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="shipments-table"
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
