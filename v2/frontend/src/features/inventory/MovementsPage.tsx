import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { listMovements, type InventoryMovement } from "./inventoryApi";
import { canReadInventory } from "./inventoryPermissions";
import { locationTypeLabel, movementTypeLabel } from "./inventoryLabels";
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
  const productFilter = params.get("product_id") ?? params.get("q") ?? "";
  const [query, setQuery] = useState(productFilter);
  const [rows, setRows] = useState<InventoryMovement[] | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setQuery(productFilter);
  }, [productFilter]);

  useEffect(() => {
    if (!canReadInventory(user)) return;
    let cancelled = false;
    void (async () => {
      setError(null);
      setRows(undefined);
      try {
        let productId: number | undefined;
        const raw = productFilter.trim();
        if (raw) {
          const asNum = Number(raw);
          if (Number.isFinite(asNum) && /^\d+$/.test(raw)) {
            productId = asNum;
          } else {
            const res = await fetch(
              `/api/products?q=${encodeURIComponent(raw)}&limit=1`,
              { credentials: "include" },
            );
            if (res.ok) {
              const list = (await res.json()) as Array<{ id: number }>;
              if (list[0]) productId = list[0].id;
              else {
                if (!cancelled) {
                  setRows([]);
                  setError("Nenhum produto encontrado para a busca.");
                }
                return;
              }
            }
          }
        }
        const data = await listMovements(
          productId != null ? { product_id: productId, limit: PAGE_LIMIT } : { limit: PAGE_LIMIT },
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
    const q = query.trim();
    next.delete("q");
    next.delete("product_id");
    if (q) {
      if (/^\d+$/.test(q)) next.set("product_id", q);
      else next.set("q", q);
    }
    setParams(next);
  }

  if (!canReadInventory(user)) {
    return <ErrorState message="Sem permissão para estoque." />;
  }
  if (error && rows === undefined) {
    return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
  }
  if (rows === undefined) return <LoadingState message="Carregando movimentações…" />;

  return (
    <div data-testid="inventory-movements-page">
      <ContextBreadcrumb items={[{ label: "Aduana" }, { label: "Estoque" }]} />
      <PageHeader
        title="Movimentações"
        subtitle="Histórico de entradas, reclassificações e ajustes"
      />
      <SectionCard title="Filtros">
        <div className="form-actions">
          <FormField label="Produto (SKU, descrição ou código)" htmlFor="movements-product-filter">
            <TextInput
              id="movements-product-filter"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              data-testid="movements-product-filter"
              aria-label="Produto"
              placeholder="SKU ou descrição"
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
                setQuery("");
                const next = new URLSearchParams(params);
                next.delete("product_id");
                next.delete("q");
                setParams(next);
              }}
            >
              Limpar
            </Button>
          ) : null}
        </div>
      </SectionCard>
      <SectionCard title="Movimentações">
        {error ? <p className="muted" role="alert">{error}</p> : null}
        {rows.length === 0 ? (
          <EmptyState
            title="Nenhuma movimentação"
            message="Confirme recebimentos ou reclassificações para gerar lançamentos."
          />
        ) : (
          <>
            <table className="operational-table" data-testid="movements-list">
              <thead>
                <tr>
                  <th>Quando</th>
                  <th>Produto</th>
                  <th>Local</th>
                  <th>Regime</th>
                  <th>Tipo</th>
                  <th>Δ Qtd</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((m) => {
                  const productLabel =
                    [m.product_sku, m.product_description].filter(Boolean).join(" — ") ||
                    `Produto ${m.product_id}`;
                  const locLabel = m.location_code || m.location_name || `Local ${m.location_id}`;
                  return (
                    <tr key={m.id} data-testid={`movement-${m.id}`}>
                      <td>{formatDateTime(m.created_at)}</td>
                      <td>
                        <Link to={`/inventory/sku/${m.product_id}`}>{productLabel}</Link>
                      </td>
                      <td>{locLabel}</td>
                      <td>{locationTypeLabel(m.location_type)}</td>
                      <td>{movementTypeLabel(m.movement_type)}</td>
                      <td>{formatQuantity(m.quantity_delta)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <PaginationSummary offset={0} limit={PAGE_LIMIT} loadedCount={rows.length} />
          </>
        )}
      </SectionCard>
    </div>
  );
}
