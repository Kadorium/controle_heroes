import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import {
  addReceiptLines,
  confirmReceipt,
  createReceipt,
  listLocations,
  listReceiptResiduals,
  listReceipts,
  reverseReceipt,
  type GoodsReceipt,
  type ReceiptResidual,
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
  formatQuantity,
  LoadingState,
  Notice,
  SectionCard,
  SelectField,
  TextInput,
} from "../../ui";

type Props = { user: User; processId: number; onChanged?: () => void; refreshTick?: number };

export function ReceiptPanel({ user, processId, onChanged, refreshTick = 0 }: Props) {
  const writable = canWriteInventory(user);
  const [rows, setRows] = useState<GoodsReceipt[] | undefined>(undefined);
  const [locations, setLocations] = useState<StockLocation[]>([]);
  const [residuals, setResiduals] = useState<ReceiptResidual[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [locationCode, setLocationCode] = useState("DOMESTIC-MAIN");
  const [proposed, setProposed] = useState<Record<number, string>>({});

  const reload = useCallback(async () => {
    const [rs, locs, res] = await Promise.all([
      listReceipts(processId),
      listLocations(),
      listReceiptResiduals(processId).catch(() => [] as ReceiptResidual[]),
    ]);
    setRows(rs);
    setLocations(locs);
    setResiduals(res);
    const domestic = locs.filter((l) => l.active && l.location_type === "DOMESTIC");
    setLocationCode((prev) => {
      if (domestic.some((l) => l.code === prev)) return prev;
      return domestic.find((l) => l.code === "DOMESTIC-MAIN")?.code ?? domestic[0]?.code ?? prev;
    });
    setProposed((prev) => {
      const next = { ...prev };
      for (const r of res) {
        if (next[r.nationalization_item_id] == null) next[r.nationalization_item_id] = r.residual_qty;
      }
      return next;
    });
  }, [processId, refreshTick]);

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
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
      onChanged?.();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  const eligible = useMemo(
    () => residuals.filter((r) => Number(r.residual_qty) > 0 && r.product_id != null),
    [residuals],
  );
  const domesticLocations = useMemo(
    () => locations.filter((l) => l.active && l.location_type === "DOMESTIC"),
    [locations],
  );

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

      <SectionCard title="Residual recebível">
        {residuals.length === 0 ? (
          <EmptyState
            title="Sem quantidade nacionalizada"
            message="Confirme uma liberação neste processo antes de receber em estoque."
          />
        ) : eligible.length === 0 ? (
          <EmptyState
            title="Nada a receber"
            message="Quantidades nacionalizadas deste processo já foram recebidas."
          />
        ) : (
          <table className="dense-table" data-testid="receipt-residual-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Nacionalizada</th>
                <th>Já recebida</th>
                <th>Ainda recebível</th>
                <th>Proposta agora</th>
              </tr>
            </thead>
            <tbody>
              {eligible.map((r) => {
                const residual = Number(r.residual_qty);
                const proposedNow = Number(proposed[r.nationalization_item_id] ?? r.residual_qty);
                const over = Number.isFinite(proposedNow) && proposedNow > residual;
                const label = r.product_name || r.product_sku || "Item";
                return (
                  <tr
                    key={r.nationalization_item_id}
                    data-testid={`receipt-residual-${r.nationalization_item_id}`}
                  >
                    <td>
                      {r.product_id != null ? (
                        <Link to={`/inventory/sku/${r.product_id}`}>{label}</Link>
                      ) : (
                        <strong>{label}</strong>
                      )}
                      {r.product_sku ? <div className="muted">{r.product_sku}</div> : null}
                    </td>
                    <td>{formatQuantity(r.nationalized_qty)}</td>
                    <td>{formatQuantity(r.received_qty)}</td>
                    <td data-testid={`receipt-residual-qty-${r.nationalization_item_id}`}>
                      {formatQuantity(r.residual_qty)}
                    </td>
                    <td>
                      {writable ? (
                        <>
                          <TextInput
                            id={`receipt-qty-${r.nationalization_item_id}`}
                            value={proposed[r.nationalization_item_id] ?? r.residual_qty}
                            onChange={(e) =>
                              setProposed((p) => ({
                                ...p,
                                [r.nationalization_item_id]: e.target.value,
                              }))
                            }
                            data-testid={`receipt-proposed-${r.nationalization_item_id}`}
                          />
                          {over ? (
                            <p
                              className="muted"
                              data-testid={`receipt-over-${r.nationalization_item_id}`}
                            >
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
          <p className="muted">Itens já totalmente recebidos não aparecem como opção.</p>
        ) : null}
      </SectionCard>

      <SectionCard title="Recebimentos">
        {rows.length === 0 ? (
          <EmptyState
            title="Sem recebimentos"
            message="Receba a quantidade nacionalizada neste local doméstico."
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
                    busy={busy}
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
                    busy={busy}
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
      </SectionCard>

      {writable ? (
        <SectionCard title="Novo recebimento">
          <div className="form-actions">
            <FormField label="Tipo" htmlFor="receipt-type" hint="Somente entrada doméstica neste fluxo.">
              <SelectField
                id="receipt-type"
                data-testid="receipt-type"
                value="DOMESTIC_IN"
                disabled
                options={[
                  { value: "DOMESTIC_IN", label: receiptTypeLabel("DOMESTIC_IN") },
                ]}
              />
            </FormField>
            <FormField label="Localização" htmlFor="receipt-location">
              <SelectField
                id="receipt-location"
                data-testid="receipt-location"
                value={locationCode}
                onChange={(e) => setLocationCode(e.target.value)}
                options={domesticLocations.map((l) => ({
                  value: l.code,
                  label: `${l.name} (${locationTypeLabel(l.location_type)})`,
                }))}
              />
            </FormField>
            <Button
              type="button"
              busy={busy}
              disabled={busy || eligible.length === 0}
              data-testid="receipt-receive"
              onClick={() => {
                const over = eligible.some((r) => {
                  const qty = Number(
                    (proposed[r.nationalization_item_id] ?? r.residual_qty).trim(),
                  );
                  return Number.isFinite(qty) && qty > Number(r.residual_qty);
                });
                if (over) {
                  setError(
                    "Não é possível receber mais do que o residual nacionalizado disponível. Reduza a quantidade.",
                  );
                  return;
                }
                void run(async () => {
                  const lines = eligible
                    .map((r) => {
                      const qty = (proposed[r.nationalization_item_id] ?? r.residual_qty).trim();
                      if (!qty || Number(qty) <= 0 || r.product_id == null) return null;
                      return {
                        product_id: r.product_id,
                        quantity: qty,
                        nationalization_item_id: r.nationalization_item_id,
                      };
                    })
                    .filter((x): x is NonNullable<typeof x> => x != null);
                  if (!lines.length) return;
                  const natIds = new Set(
                    eligible
                      .filter((r) =>
                        lines.some((ln) => ln.nationalization_item_id === r.nationalization_item_id),
                      )
                      .map((r) => r.nationalization_id),
                  );
                  let current = draft;
                  if (!current) {
                    current = await createReceipt({
                      location_code: locationCode,
                      process_id: processId,
                      nationalization_id: natIds.size === 1 ? [...natIds][0] : undefined,
                      receipt_type: "DOMESTIC_IN",
                    });
                  }
                  const withLines = await addReceiptLines(current.id, {
                    expected_version: current.version,
                    lines,
                  });
                  await confirmReceipt(withLines.id, withLines.version);
                });
              }}
            >
              Receber quantidades propostas
            </Button>
          </div>
        </SectionCard>
      ) : null}
    </div>
  );
}
