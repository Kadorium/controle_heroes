import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getSkuPosition, type SkuPosition } from "./inventoryApi";
import { canReadInventory } from "./inventoryPermissions";
import { skuBucketLabel, skuBucketScopeNote, locationTypeLabel } from "./inventoryLabels";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  formatQuantity,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
} from "../../ui";

type Props = { user: User };

const PHYSICAL_KEYS = ["available_qty", "bonded_qty", "quarantine_qty"] as const;
const CUSTOMS_KEYS = ["cleared_not_received_qty", "in_clearance_qty"] as const;
const LOGISTICS_KEYS = ["in_transit_qty", "future_order_qty"] as const;
const STUB_KEYS = new Set(["in_clearance_qty", "in_transit_qty", "future_order_qty"]);

export function SkuPositionPage({ user }: Props) {
  const { productId } = useParams();
  const id = Number(productId);
  const [pos, setPos] = useState<SkuPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [productLabel, setProductLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!canReadInventory(user)) return;
    let cancelled = false;
    void (async () => {
      setError(null);
      setPos(null);
      try {
        const p = await getSkuPosition(id);
        if (!cancelled) setPos(p);
        try {
          const res = await fetch(`/api/products/${id}`, { credentials: "include" });
          if (res.ok) {
            const prod = (await res.json()) as { sku?: string; description?: string };
            if (!cancelled) {
              setProductLabel(
                [prod.sku, prod.description].filter(Boolean).join(" — ") || null,
              );
            }
          }
        } catch {
          /* optional enrich */
        }
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
  }, [id, user, reloadKey]);

  if (!canReadInventory(user)) {
    return <ErrorState message="Sem permissão para estoque." />;
  }
  if (error) return <ErrorState message={error} onRetry={() => setReloadKey((k) => k + 1)} />;
  if (!pos) return <LoadingState message="Carregando posição de estoque…" />;

  const allPhysicalZero = PHYSICAL_KEYS.every((k) => {
    const n = Number(pos[k]);
    return !Number.isFinite(n) || n === 0;
  });

  function renderRows(keys: readonly string[], data: SkuPosition) {
    return (
      <table className="mini-table">
        <thead>
          <tr>
            <th>Indicador</th>
            <th>Quantidade</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <tr key={key} data-testid={`sku-bucket-${key}`}>
              <td>
                {skuBucketLabel(key)}
                {skuBucketScopeNote(key) ? (
                  <div className="muted" data-testid={`sku-bucket-scope-${key}`}>
                    {skuBucketScopeNote(key)}
                  </div>
                ) : null}
              </td>
              <td>
                {STUB_KEYS.has(key)
                  ? "Não disponível"
                  : key === "future_order_qty" && data.future_order_qty == null
                    ? "Não disponível"
                    : formatQuantity(data[key as keyof SkuPosition] as string | null)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div data-testid="sku-position-page">
      <ContextBreadcrumb
        items={[
          { label: "Aduana" },
          { label: "Estoque", to: "/inventory/movements" },
          { label: productLabel ?? `Produto ${id}` },
        ]}
      />
      <PageHeader
        title={productLabel ? `Posição de estoque — ${productLabel}` : "Posição de estoque"}
        subtitle="Saldos físicos, situação aduaneira e logística"
      />
      <Notice tone="info" data-testid="sku-dimension-note">
        Os grupos abaixo são dimensões diferentes e não devem ser somados entre si. A
        conservação física vale apenas para Disponível + Entreposto + Quarentena.
      </Notice>
      <SectionCard title="Posição física">
        {allPhysicalZero ? (
          <EmptyState title="Sem saldo físico" message="Nenhuma quantidade nos locais físicos." />
        ) : (
          <div data-testid="sku-buckets">{renderRows(PHYSICAL_KEYS, pos)}</div>
        )}
      </SectionCard>
      <SectionCard title="Situação aduaneira" data-testid="sku-customs-dim">
        {renderRows(CUSTOMS_KEYS, pos)}
      </SectionCard>
      <SectionCard title="Situação logística" data-testid="sku-logistics-dim">
        {renderRows(LOGISTICS_KEYS, pos)}
      </SectionCard>
      <SectionCard title="Saldos por local" data-testid="sku-balances">
        {pos.balances.length === 0 ? (
          <EmptyState title="Sem saldos" message="Nenhum saldo derivado neste produto." />
        ) : (
          <table className="mini-table">
            <thead>
              <tr>
                <th>Local</th>
                <th>Regime</th>
                <th>Quantidade</th>
              </tr>
            </thead>
            <tbody>
              {pos.balances.map((bal, i) => {
                const row = bal as {
                  location_id?: number;
                  location_code?: string | null;
                  location_type?: string | null;
                  qty?: string;
                };
                return (
                  <tr key={`${row.location_id ?? i}`} data-testid={`sku-balance-${row.location_code ?? i}`}>
                    <td>{row.location_code ?? "—"}</td>
                    <td>{locationTypeLabel(row.location_type)}</td>
                    <td>{formatQuantity(row.qty ?? null)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </SectionCard>
      <p>
        <Link to="/inventory/movements">Ver movimentações</Link>
      </p>
    </div>
  );
}
