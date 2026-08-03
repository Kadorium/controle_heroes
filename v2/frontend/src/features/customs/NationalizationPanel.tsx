import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import { canClearCustoms, canWriteCustoms, conflictMessage } from "./customsPermissions";
import {
  addNationalizationItems,
  confirmNationalization,
  createNationalization,
  listNationalizations,
  reverseNationalization,
  type Nationalization,
} from "../inventory/inventoryApi";
import { nationalizationStatusLabel } from "../inventory/inventoryLabels";
import {
  Button,
  EmptyState,
  ErrorState,
  FormField,
  formatQuantity,
  LoadingState,
  Notice,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User; processId: number };

export function NationalizationPanel({ user, processId }: Props) {
  const writable = canWriteCustoms(user);
  const canClear = canClearCustoms(user);
  const [rows, setRows] = useState<Nationalization[] | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("1");
  const [shipmentItemId, setShipmentItemId] = useState("");
  const [invoiceItemId, setInvoiceItemId] = useState("");

  const reload = useCallback(async () => {
    setRows(await listNationalizations(processId));
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
  if (rows === undefined) return <LoadingState message="Carregando liberações…" />;

  const draft = rows.find((n) => n.status === "DRAFT") ?? null;

  return (
    <div data-testid="customs-nationalization-panel">
      {error ? (
        <Notice tone="danger" data-testid="nationalization-error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Liberações">
        {rows.length === 0 ? (
          <EmptyState
            title="Sem liberações"
            message="Crie uma liberação após submeter o processo."
          />
        ) : (
          <ul data-testid="nationalization-list">
            {rows.map((n) => (
              <li key={n.id} data-testid={`nationalization-item-${n.id}`}>
                #{n.id} · {nationalizationStatusLabel(n.status)} · v{n.version} · {n.items.length}{" "}
                itens
                {n.items.map((it) => (
                  <span key={it.id}>
                    {" "}
                    [SKU {it.product_id ?? "?"} qty={formatQuantity(it.quantity)}]
                  </span>
                ))}
                {writable && n.status === "CONFIRMED" ? (
                  <Button
                    type="button"
                    disabled={busy}
                    data-testid={`nationalization-reverse-${n.id}`}
                    onClick={() =>
                      void run(async () => {
                        await reverseNationalization(processId, n.id, n.version);
                      })
                    }
                  >
                    Reverter
                  </Button>
                ) : null}
                {canClear && n.status === "DRAFT" ? (
                  <Button
                    type="button"
                    disabled={busy}
                    data-testid={`nationalization-confirm-${n.id}`}
                    onClick={() =>
                      void run(async () => {
                        await confirmNationalization(processId, n.id, n.version);
                      })
                    }
                  >
                    Confirmar
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      {writable ? (
        <SectionCard title="Nova liberação / itens">
          <div className="form-actions">
            <Button
              type="button"
              disabled={busy}
              data-testid="nationalization-create"
              onClick={() =>
                void run(async () => {
                  await createNationalization(processId, {});
                })
              }
            >
              Criar liberação
            </Button>
            <FormField label="ID do produto" htmlFor="nationalization-product-id">
              <TextInput
                id="nationalization-product-id"
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                data-testid="nationalization-product-id"
              />
            </FormField>
            <FormField label="Quantidade" htmlFor="nationalization-qty">
              <TextInput
                id="nationalization-qty"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                data-testid="nationalization-qty"
              />
            </FormField>
            <FormField label="ID item embarque (opcional)" htmlFor="nationalization-shipment-item">
              <TextInput
                id="nationalization-shipment-item"
                value={shipmentItemId}
                onChange={(e) => setShipmentItemId(e.target.value)}
                data-testid="nationalization-shipment-item"
              />
            </FormField>
            <FormField label="ID item fatura (opcional)" htmlFor="nationalization-invoice-item">
              <TextInput
                id="nationalization-invoice-item"
                value={invoiceItemId}
                onChange={(e) => setInvoiceItemId(e.target.value)}
                data-testid="nationalization-invoice-item"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !draft}
              data-testid="nationalization-add-items"
              onClick={() =>
                void run(async () => {
                  if (!draft) return;
                  await addNationalizationItems(processId, draft.id, {
                    expected_version: draft.version,
                    items: [
                      {
                        quantity: qty,
                        product_id: productId ? Number(productId) : null,
                        shipment_item_id: shipmentItemId
                          ? Number(shipmentItemId)
                          : null,
                        invoice_item_id: invoiceItemId ? Number(invoiceItemId) : null,
                      },
                    ],
                  });
                })
              }
            >
              Adicionar item ao rascunho
            </Button>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
