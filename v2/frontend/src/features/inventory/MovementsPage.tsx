import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listMovements, type InventoryMovement } from "./inventoryApi";
import { canReadInventory } from "./inventoryPermissions";
import { movementTypeLabel } from "./inventoryLabels";
import {
  Button,
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  FormField,
  formatDateTime,
  formatQuantity,
  LoadingState,
  PageHeader,
  PaginationSummary,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User };

const PAGE_LIMIT = 100;

export function MovementsPage({ user }: Props) {
  const [params, setParams] = useSearchParams();
  const productFilter = params.get("product_id") ?? "";
  const [productId, setProductId] = useState(productFilter);
  const [rows, setRows] = useState<InventoryMovement[] | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setProductId(productFilter);
  }, [productFilter]);

  useEffect(() => {
    if (!canReadInventory(user)) return;
    let cancelled = false;
    void (async () => {
      setError(null);
      setRows(undefined);
      try {
        const pid = productFilter ? Number(productFilter) : undefined;
        const data = await listMovements(
          pid != null && Number.isFinite(pid)
            ? { product_id: pid, limit: PAGE_LIMIT }
            : { limit: PAGE_LIMIT },
        );
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) {
          const err = e as Error & { status?: number };
          if (err.status === 403) setError("Sem permissão para estoque.");
          else setError(e instanceof Error ? e.message : "Erro");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [productFilter, user, reloadKey]);

  function applyFilter() {
    const next = new URLSearchParams(params);
    if (productId.trim()) next.set("product_id", productId.trim());
    else next.delete("product_id");
    setParams(next);
  }

  if (!canReadInventory(user)) {
    return <ErrorState message="Sem permissão para estoque." />;
  }
  if (error && rows === undefined) {
    return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
  }
  if (rows === undefined) return <LoadingState message="Carregando movimentos…" />;

  return (
    <div data-testid="inventory-movements-page">
      <ContextBreadcrumb items={[{ label: "Aduana" }, { label: "Estoque" }]} />
      <PageHeader
        title="Movimentos de estoque"
        subtitle="Ledger append-only · origem aduaneira / inventário"
      />
      <SectionCard title="Filtros">
        <div className="form-actions">
          <FormField label="ID do produto" htmlFor="movements-product-filter">
            <TextInput
              id="movements-product-filter"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              data-testid="movements-product-filter"
              aria-label="ID do produto"
            />
          </FormField>
          <Button type="button" data-testid="movements-filter-apply" onClick={applyFilter}>
            Filtrar
          </Button>
          {productFilter ? (
            <Button
              type="button"
              variant="ghost"
              data-testid="movements-filter-clear"
              onClick={() => {
                setProductId("");
                const next = new URLSearchParams(params);
                next.delete("product_id");
                setParams(next);
              }}
            >
              Limpar
            </Button>
          ) : null}
        </div>
      </SectionCard>
      <SectionCard title="Ledger">
        {error ? <p className="muted" role="alert">{error}</p> : null}
        {rows.length === 0 ? (
          <EmptyState
            title="Nenhum movimento"
            message="Confirme recebimentos ou ajustes para gerar lançamentos no ledger."
          />
        ) : (
          <>
            <table className="operational-table" data-testid="movements-list">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Produto</th>
                  <th>Local</th>
                  <th>Tipo</th>
                  <th>Δ Qtd</th>
                  <th>Quando</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((m) => (
                  <tr key={m.id} data-testid={`movement-${m.id}`}>
                    <td>#{m.id}</td>
                    <td>
                      <Link to={`/inventory/sku/${m.product_id}`}>SKU #{m.product_id}</Link>
                    </td>
                    <td>#{m.location_id}</td>
                    <td>{movementTypeLabel(m.movement_type)}</td>
                    <td>{formatQuantity(m.quantity_delta)}</td>
                    <td>{formatDateTime(m.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PaginationSummary offset={0} limit={PAGE_LIMIT} loadedCount={rows.length} />
          </>
        )}
      </SectionCard>
    </div>
  );
}
