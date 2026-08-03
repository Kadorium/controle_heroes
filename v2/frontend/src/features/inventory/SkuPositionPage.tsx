import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getSkuPosition, type SkuPosition } from "./inventoryApi";
import { canReadInventory } from "./inventoryPermissions";
import { skuBucketLabel } from "./inventoryLabels";
import {
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  formatQuantity,
  LoadingState,
  PageHeader,
  SectionCard,
} from "../../ui";

type Props = { user: User };

const BUCKET_KEYS = [
  "available_qty",
  "bonded_qty",
  "quarantine_qty",
  "cleared_not_received_qty",
  "in_clearance_qty",
  "in_transit_qty",
  "future_order_qty",
] as const;

export function SkuPositionPage({ user }: Props) {
  const { productId } = useParams();
  const id = Number(productId);
  const [pos, setPos] = useState<SkuPosition | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!canReadInventory(user)) return;
    let cancelled = false;
    void (async () => {
      setError(null);
      setPos(null);
      try {
        const p = await getSkuPosition(id);
        if (!cancelled) setPos(p);
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
  if (!pos) return <LoadingState message="Carregando posição SKU…" />;

  const allZero = BUCKET_KEYS.every((k) => {
    const v = pos[k];
    if (v == null) return true;
    const n = Number(v);
    return !Number.isFinite(n) || n === 0;
  });

  return (
    <div data-testid="sku-position-page">
      <ContextBreadcrumb
        items={[
          { label: "Aduana" },
          { label: "Estoque", to: "/inventory/movements" },
          { label: `SKU #${id}` },
        ]}
      />
      <PageHeader
        title={`Posição SKU #${id}`}
        subtitle="Saldos por bucket · origem aduaneira / inventário"
      />
      <SectionCard title="Buckets">
        {allZero ? (
          <EmptyState
            title="Sem saldo"
            message="Nenhuma quantidade registrada para este SKU nos buckets conhecidos."
          />
        ) : (
          <table className="mini-table" data-testid="sku-buckets">
            <thead>
              <tr>
                <th>Bucket</th>
                <th>Quantidade</th>
              </tr>
            </thead>
            <tbody>
              {BUCKET_KEYS.map((key) => (
                <tr key={key} data-testid={`sku-bucket-${key}`}>
                  <td>
                    {skuBucketLabel(key)}
                    {key === "future_order_qty" && pos.future_order_qty_note ? (
                      <div className="muted">{pos.future_order_qty_note}</div>
                    ) : null}
                  </td>
                  <td>{key === "future_order_qty" && pos.future_order_qty == null ? "—" : formatQuantity(pos[key])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
      <p>
        <Link to="/inventory/movements">Ver movimentos</Link>
      </p>
    </div>
  );
}
