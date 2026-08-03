import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  addReceiptLines,
  confirmReceipt,
  createReceipt,
  listLocations,
  listReceipts,
  reverseReceipt,
  type GoodsReceipt,
  type StockLocation,
} from "../inventory/inventoryApi";
import { canWriteInventory } from "../inventory/inventoryPermissions";
import {
  locationTypeLabel,
  receiptStatusLabel,
  receiptTypeLabel,
} from "../inventory/inventoryLabels";
import { conflictMessage } from "./customsPermissions";
import {
  Button,
  EmptyState,
  ErrorState,
  FormField,
  LoadingState,
  Notice,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User; processId: number };

export function ReceiptPanel({ user, processId }: Props) {
  const writable = canWriteInventory(user);
  const [rows, setRows] = useState<GoodsReceipt[] | undefined>(undefined);
  const [locations, setLocations] = useState<StockLocation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [receiptType, setReceiptType] = useState("BONDED_IN");
  const [locationCode, setLocationCode] = useState("BONDED-MAIN");
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("1");
  const [natItemId, setNatItemId] = useState("");
  const [natId, setNatId] = useState("");

  const reload = useCallback(async () => {
    const [rs, locs] = await Promise.all([listReceipts(processId), listLocations()]);
    setRows(rs);
    setLocations(locs);
  }, [processId]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      setError(null);
      try {
        await reload();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reload]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      setBusy(false);
    }
  }

  if (error && rows === undefined) return <ErrorState message={error} />;
  if (rows === undefined) return <LoadingState message="Carregando recebimentos…" />;

  const draft = rows.find((r) => r.status === "DRAFT") ?? null;

  return (
    <div data-testid="customs-receipt-panel">
      {error ? (
        <Notice tone="danger" data-testid="receipt-error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Recebimentos">
        {rows.length === 0 ? (
          <EmptyState
            title="Sem recebimentos"
            message="Entreposto pode preceder liberação; entrada doméstica exige liberação confirmada."
          />
        ) : (
          <ul data-testid="receipt-list">
            {rows.map((r) => (
              <li key={r.id} data-testid={`receipt-item-${r.id}`}>
                #{r.id} · {receiptTypeLabel(r.receipt_type)} · {receiptStatusLabel(r.status)} ·{" "}
                {r.location_code} · {r.lines.length} linhas
                {writable && r.status === "DRAFT" ? (
                  <Button
                    type="button"
                    disabled={busy}
                    data-testid={`receipt-confirm-${r.id}`}
                    onClick={() =>
                      void run(async () => {
                        await confirmReceipt(r.id, r.version);
                      })
                    }
                  >
                    Confirmar
                  </Button>
                ) : null}
                {writable && r.status === "CONFIRMED" ? (
                  <Button
                    type="button"
                    disabled={busy}
                    data-testid={`receipt-reverse-${r.id}`}
                    onClick={() =>
                      void run(async () => {
                        await reverseReceipt(r.id, r.version);
                      })
                    }
                  >
                    Reverter
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        <p className="muted">
          Localizações:{" "}
          {locations.map((l) => `${l.code} (${locationTypeLabel(l.location_type)})`).join(", ") ||
            "—"}
        </p>
      </SectionCard>

      {writable ? (
        <SectionCard title="Novo recebimento">
          <div className="form-actions">
            <FormField label="Tipo (BONDED_IN / DOMESTIC_IN)" htmlFor="receipt-type">
              <TextInput
                id="receipt-type"
                value={receiptType}
                onChange={(e) => {
                  const t = e.target.value;
                  setReceiptType(t);
                  if (t === "BONDED_IN") setLocationCode("BONDED-MAIN");
                  if (t === "DOMESTIC_IN") setLocationCode("DOMESTIC-MAIN");
                }}
                data-testid="receipt-type"
              />
            </FormField>
            <FormField label="Código da localização" htmlFor="receipt-location">
              <TextInput
                id="receipt-location"
                value={locationCode}
                onChange={(e) => setLocationCode(e.target.value)}
                data-testid="receipt-location"
              />
            </FormField>
            <FormField label="ID da liberação (doméstico)" htmlFor="receipt-nat-id">
              <TextInput
                id="receipt-nat-id"
                value={natId}
                onChange={(e) => setNatId(e.target.value)}
                data-testid="receipt-nat-id"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="receipt-create"
              onClick={() =>
                void run(async () => {
                  await createReceipt({
                    location_code: locationCode,
                    process_id: processId,
                    nationalization_id: natId ? Number(natId) : undefined,
                    receipt_type: receiptType,
                  });
                })
              }
            >
              Criar rascunho
            </Button>
            <FormField label="ID do produto" htmlFor="receipt-product-id">
              <TextInput
                id="receipt-product-id"
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                data-testid="receipt-product-id"
              />
            </FormField>
            <FormField label="Quantidade" htmlFor="receipt-qty">
              <TextInput
                id="receipt-qty"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                data-testid="receipt-qty"
              />
            </FormField>
            <FormField label="ID item da liberação" htmlFor="receipt-nat-item-id">
              <TextInput
                id="receipt-nat-item-id"
                value={natItemId}
                onChange={(e) => setNatItemId(e.target.value)}
                data-testid="receipt-nat-item-id"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !draft}
              data-testid="receipt-add-lines"
              onClick={() =>
                void run(async () => {
                  if (!draft) return;
                  await addReceiptLines(draft.id, {
                    expected_version: draft.version,
                    lines: [
                      {
                        product_id: Number(productId),
                        quantity: qty,
                        nationalization_item_id: natItemId ? Number(natItemId) : null,
                      },
                    ],
                  });
                })
              }
            >
              Adicionar linha
            </Button>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
