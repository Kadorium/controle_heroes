import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { canClearCustoms, canWriteCustoms, conflictMessage } from "./customsPermissions";
import {
  addNationalizationItems,
  confirmNationalization,
  createNationalization,
  listClearanceResiduals,
  listNationalizations,
  listReceiptResiduals,
  reverseNationalization,
  type ClearanceResidual,
  type Nationalization,
} from "../inventory/inventoryApi";
import { nationalizationStatusLabel } from "../inventory/inventoryLabels";
import {
  Button,
  EmptyState,
  ErrorState,
  formatQuantity,
  LoadingState,
  Notice,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User; processId: number; inventoryTick?: number; onChanged?: () => void };

function residualKey(r: ClearanceResidual): string {
  return r.source_kind === "shipment_item"
    ? `s-${r.shipment_item_id}`
    : `i-${r.invoice_item_id}`;
}

export function NationalizationPanel({
  user,
  processId,
  inventoryTick = 0,
  onChanged,
}: Props) {
  const writable = canWriteCustoms(user);
  const canClear = canClearCustoms(user);
  const [rows, setRows] = useState<Nationalization[] | undefined>(undefined);
  const [residuals, setResiduals] = useState<ClearanceResidual[]>([]);
  const [receiptResiduals, setReceiptResiduals] = useState<
    Array<{ nationalization_id: number; received_qty: string }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [proposed, setProposed] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    const [nats, res, recRes] = await Promise.all([
      listNationalizations(processId),
      listClearanceResiduals(processId).catch(() => [] as ClearanceResidual[]),
      listReceiptResiduals(processId).catch(() => []),
    ]);
    setRows(nats);
    setResiduals(res);
    setReceiptResiduals(recRes);
    setProposed((prev) => {
      const next = { ...prev };
      for (const r of res) {
        const k = residualKey(r);
        if (next[k] == null) next[k] = r.residual_qty;
      }
      return next;
    });
  }, [processId, inventoryTick]);

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
      onChanged?.();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      setBusy(false);
    }
  }

  const eligible = useMemo(
    () => residuals.filter((r) => Number(r.residual_qty) > 0),
    [residuals],
  );

  function natHasReceivedStock(natId: number) {
    return receiptResiduals.some(
      (r) => r.nationalization_id === natId && Number(r.received_qty) > 0,
    );
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

      <SectionCard title="Residual nacionalizável">
        {residuals.length === 0 ? (
          <EmptyState
            title="Sem alocação"
            message="Vincule e aloque o embarque (ou a fatura) ao processo antes de nacionalizar."
          />
        ) : eligible.length === 0 ? (
          <EmptyState
            title="Nada a nacionalizar"
            message="Quantidades alocadas já foram nacionalizadas por completo."
          />
        ) : (
          <table className="dense-table" data-testid="nationalization-residual-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Embarcada</th>
                <th>Já nacionalizada</th>
                <th>Ainda nacionalizável</th>
                <th>Proposta agora</th>
              </tr>
            </thead>
            <tbody>
              {eligible.map((r) => {
                const k = residualKey(r);
                const residual = Number(r.residual_qty);
                const proposedNow = Number(proposed[k] ?? r.residual_qty);
                const over = Number.isFinite(proposedNow) && proposedNow > residual;
                const label =
                  r.product_name || r.product_sku || (r.product_id ? `Produto ${r.product_id}` : "Item");
                return (
                  <tr key={k} data-testid={`nationalization-residual-${k}`}>
                    <td>
                      <strong>{label}</strong>
                      {r.product_sku ? <div className="muted">{r.product_sku}</div> : null}
                    </td>
                    <td>{formatQuantity(r.shipped_qty ?? r.allocated_qty)}</td>
                    <td>{formatQuantity(r.nationalized_qty)}</td>
                    <td data-testid={`nationalization-residual-qty-${k}`}>
                      {formatQuantity(r.residual_qty)}
                    </td>
                    <td>
                      {writable ? (
                        <>
                          <TextInput
                            id={`nat-qty-${k}`}
                            value={proposed[k] ?? r.residual_qty}
                            onChange={(e) =>
                              setProposed((p) => ({ ...p, [k]: e.target.value }))
                            }
                            data-testid={`nationalization-proposed-${k}`}
                          />
                          {over ? (
                            <p className="muted" data-testid={`nationalization-over-${k}`}>
                              Acima do residual — o sistema bloqueia.
                            </p>
                          ) : null}
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {residuals.some((r) => Number(r.residual_qty) <= 0) ? (
          <p className="muted">Itens já totalmente nacionalizados não aparecem como opção.</p>
        ) : null}
      </SectionCard>

      <SectionCard title="Liberações">
        {rows.length === 0 ? (
          <EmptyState title="Sem liberações" message="Crie uma liberação após submeter o processo." />
        ) : (
          <ul data-testid="nationalization-list">
            {rows.map((n) => (
              <li key={n.id} data-testid={`nationalization-item-${n.id}`}>
                #{n.id} · {nationalizationStatusLabel(n.status)} · v{n.version} · {n.items.length}{" "}
                itens
                {n.items.map((it) => (
                  <span key={it.id}>
                    {" "}
                    [{it.product_id ? `produto` : "item"} qty={formatQuantity(it.quantity)}]
                  </span>
                ))}
                {writable && n.status === "CONFIRMED" && !natHasReceivedStock(n.id) ? (
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
                {writable && n.status === "CONFIRMED" && natHasReceivedStock(n.id) ? (
                  <span className="muted" data-testid={`nationalization-reverse-hidden-${n.id}`}>
                    Reverter indisponível — já há estoque recebido
                  </span>
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
        <SectionCard title="Nova liberação">
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
            <Button
              type="button"
              disabled={busy || !draft || eligible.length === 0}
              data-testid="nationalization-add-items"
              onClick={() =>
                void run(async () => {
                  if (!draft) return;
                  const items = eligible
                    .map((r) => {
                      const k = residualKey(r);
                      const qty = (proposed[k] ?? r.residual_qty).trim();
                      if (!qty || Number(qty) <= 0) return null;
                      return {
                        quantity: qty,
                        product_id: r.product_id,
                        shipment_item_id: r.shipment_item_id,
                        invoice_item_id: r.invoice_item_id,
                      };
                    })
                    .filter((x): x is NonNullable<typeof x> => x != null);
                  if (!items.length) return;
                  await addNationalizationItems(processId, draft.id, {
                    expected_version: draft.version,
                    items,
                  });
                })
              }
            >
              Adicionar quantidades propostas ao rascunho
            </Button>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
