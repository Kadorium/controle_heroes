/**
 * PackingCommitPanel — C6
 * Preview profissional de Packing List Detail → Shipment PLANNED.
 * 0/1/N Order e Shipment; linhas de embalagem sem qty embarcada; sem JSON como UX primária.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  commitPlDetail,
  fetchPackingPreview,
  type PackingLineChoiceIn,
  type PackingPreviewOut,
  type CommitAttemptOut,
} from "./ingestionApi";

type Props = { documentId: number; user: User };

function canCommit(user: User): boolean {
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("logistics:write"));
}

function lineChoicesPayload(choices: Record<string, number>): PackingLineChoiceIn[] {
  return Object.entries(choices).map(([group_key, order_item_id]) => ({
    group_key,
    order_item_id,
  }));
}

function statusLabel(status: string): string {
  switch (status) {
    case "matched":
      return "casado";
    case "ambiguous":
      return "ambíguo — escolha o item";
    case "packaging":
      return "volume de embalagem (sem quantidade embarcada)";
    case "unmatched":
      return "sem item PRODUCT";
    case "needs_order":
      return "aguardando pedido";
    default:
      return status;
  }
}

export function PackingCommitPanel({ documentId, user }: Props) {
  const [orderId, setOrderId] = useState("");
  const [pickedOrderId, setPickedOrderId] = useState("");
  const [shipmentId, setShipmentId] = useState("");
  const [pickedShipmentId, setPickedShipmentId] = useState("");
  const [lineChoices, setLineChoices] = useState<Record<string, number>>({});
  const [opKey, setOpKey] = useState(() => `pl-detail-${documentId}-${Date.now()}`);

  const [preview, setPreview] = useState<PackingPreviewOut | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitBusy, setCommitBusy] = useState(false);

  const runPreview = useCallback(
    async (explicitOrderId: string, explicitShipmentId: string, choices: Record<string, number>) => {
      setPreviewBusy(true);
      setPreviewError(null);
      try {
        const oid = explicitOrderId.trim() ? Number(explicitOrderId) : null;
        const sid = explicitShipmentId.trim() ? Number(explicitShipmentId) : null;
        const result = await fetchPackingPreview(
          documentId,
          Number.isFinite(oid) ? oid : null,
          Number.isFinite(sid) ? sid : null,
          lineChoicesPayload(choices),
        );
        setPreview(result);
      } catch (e) {
        setPreviewError(e instanceof Error ? e.message : "Falha no preview packing");
      } finally {
        setPreviewBusy(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    void runPreview(orderId, shipmentId, lineChoices);
    // first paint only — later calls go through confirm / preview button
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const candidates = preview?.order_candidates ?? [];
  const targets = preview?.shipment_targets ?? [];
  const commercial = (preview?.line_matches ?? []).filter((g) => !g.packaging);
  const packaging = (preview?.line_matches ?? []).filter((g) => g.packaging);
  const cartons = preview?.cartons ?? [];

  function confirmPickedOrder() {
    if (!pickedOrderId) return;
    setOrderId(pickedOrderId);
    void runPreview(pickedOrderId, shipmentId, lineChoices);
  }

  function confirmPickedShipment() {
    if (!pickedShipmentId) return;
    setShipmentId(pickedShipmentId);
    void runPreview(orderId, pickedShipmentId, lineChoices);
  }

  async function onCommit() {
    if (!canCommit(user) || !preview?.can_commit) return;
    setCommitBusy(true);
    setCommitError(null);
    try {
      const result = await commitPlDetail(documentId, {
        operation_key: opKey,
        order_id: orderId.trim() ? Number(orderId) : null,
        shipment_id: shipmentId.trim() ? Number(shipmentId) : null,
        line_choices: lineChoicesPayload(lineChoices),
      });
      setAttempt(result);
      setOpKey(`pl-detail-${documentId}-${Date.now()}`);
      await runPreview(orderId, shipmentId, lineChoices);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : "Falha no commit packing");
    } finally {
      setCommitBusy(false);
    }
  }

  const alreadyCommitted = Boolean(preview?.already_committed);
  const processedShipmentId = useMemo(() => {
    if (preview?.last_succeeded_shipment_id) return preview.last_succeeded_shipment_id;
    const op = attempt?.operations?.find(
      (o) => o.entity_type === "shipment" && o.entity_id && o.status === "SUCCEEDED",
    );
    return op?.entity_id ? Number(op.entity_id) : null;
  }, [attempt, preview]);

  return (
    <SectionCard title="Commit packing list → embarque PLANNED" data-testid="packing-commit-panel">
      <p className="muted">
        O packing detalhado é a fonte dos volumes. Agrupado, se existir, é só aviso. O embarque
        fica planejado. O pedido não é o número do documento — confirme o Order. Caixas do
        packing viram volumes; linhas de embalagem não embarcam quantidade de produto.
      </p>

      {alreadyCommitted ? (
        <Notice tone="info" data-testid="packing-processed-banner" title="Packing processado">
          <p>
            Embarque{" "}
            {processedShipmentId ? (
              <Link to={`/shipments/${processedShipmentId}`} data-testid="packing-shipment-link">
                #{processedShipmentId}
              </Link>
            ) : (
              "já gerado"
            )}{" "}
            a partir deste documento. Não reexecuta o commit.
          </p>
          <p className="muted" data-testid="packing-extraction-still-editable">
            A extração nas seções abaixo permanece editável. Isso não significa que o packing
            está pendente de processamento.
          </p>
        </Notice>
      ) : null}

      {!alreadyCommitted ? (
        <>
      <div data-testid="packing-order-candidates" style={{ marginBottom: "0.75rem" }}>
        <h3 className="ingestion-subtitle">Pedido</h3>
        {previewBusy && !preview ? <p className="muted">Buscando candidatos…</p> : null}
        {preview?.order_candidates_reason ? (
          <p role="alert" style={{ color: "#b91c1c" }} data-testid="packing-order-none">
            {preview.order_candidates_reason}
          </p>
        ) : null}
        {candidates.length === 1 ? (
          <p data-testid="packing-order-suggested">
            Sugestão: pedido{" "}
            <strong>
              #{candidates[0].order_id} {candidates[0].order_code}
            </strong>{" "}
            ({candidates[0].status}). Confirme explicitamente — não há commit automático.
          </p>
        ) : null}
        {candidates.length > 1 ? (
          <p data-testid="packing-order-multiple">
            {candidates.length} pedidos possíveis. O sistema não escolhe em silêncio.
          </p>
        ) : null}
        {candidates.length > 0 ? (
          <ul data-testid="packing-order-candidate-list" style={{ listStyle: "none", padding: 0 }}>
            {candidates.map((c) => (
              <li key={c.order_id} style={{ marginBottom: "0.4rem" }}>
                <label style={{ cursor: "pointer" }} data-testid={`packing-order-candidate-${c.order_id}`}>
                  <input
                    type="radio"
                    name="packing-order-pick"
                    value={c.order_id}
                    checked={pickedOrderId === String(c.order_id)}
                    onChange={() => setPickedOrderId(String(c.order_id))}
                    style={{ marginRight: "0.4rem" }}
                  />
                  <strong>
                    #{c.order_id} {c.order_code}
                  </strong>{" "}
                  · {c.status} · {c.currency}
                  <ul className="muted" style={{ margin: "0.15rem 0 0 1.4rem" }}>
                    {c.evidence.map((ev) => (
                      <li key={ev}>{ev}</li>
                    ))}
                  </ul>
                </label>
              </li>
            ))}
          </ul>
        ) : null}
        <Button
          type="button"
          variant="ghost"
          disabled={!pickedOrderId}
          onClick={confirmPickedOrder}
          data-testid="packing-order-confirm-btn"
        >
          Confirmar este pedido
        </Button>
        <label style={{ display: "block", marginTop: "0.5rem" }}>
          Pedido confirmado (order_id)
          <input
            type="number"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            placeholder="Ex: 42"
            style={{ marginLeft: "0.5rem", width: "100px" }}
            data-testid="packing-order-id-input"
          />
        </label>
      </div>

      <div data-testid="packing-shipment-targets" style={{ marginBottom: "0.75rem" }}>
        <h3 className="ingestion-subtitle">Embarque destino</h3>
        {preview?.will_create_shipment ? (
          <p data-testid="packing-shipment-create">
            Nenhum embarque PLANNED com esta packing list — o commit cria um novo (modal nulo).
          </p>
        ) : null}
        {targets.length === 1 && targets[0].compatible ? (
          <p data-testid="packing-shipment-reuse">
            Reuso compatível: embarque{" "}
            <strong>
              #{targets[0].shipment_id} {targets[0].code}
            </strong>{" "}
            ({targets[0].status}).
          </p>
        ) : null}
        {targets.length > 1 ? (
          <p data-testid="packing-shipment-multiple">
            {targets.length} embarques candidatos. Escolha um — o sistema não duplica em silêncio.
          </p>
        ) : null}
        {preview?.shipment_targets_reason ? (
          <p role="alert" style={{ color: "#b91c1c" }} data-testid="packing-shipment-blocked">
            {preview.shipment_targets_reason}
          </p>
        ) : null}
        {targets.length > 1 ? (
          <ul style={{ listStyle: "none", padding: 0 }}>
            {targets.map((t) => (
              <li key={t.shipment_id}>
                <label style={{ cursor: "pointer" }} data-testid={`packing-shipment-candidate-${t.shipment_id}`}>
                  <input
                    type="radio"
                    name="packing-shipment-pick"
                    value={t.shipment_id}
                    checked={pickedShipmentId === String(t.shipment_id)}
                    onChange={() => setPickedShipmentId(String(t.shipment_id))}
                    disabled={!t.compatible}
                    style={{ marginRight: "0.4rem" }}
                  />
                  #{t.shipment_id} {t.code} · {t.status}
                  {t.compatible ? "" : " (incompatível)"}
                </label>
              </li>
            ))}
          </ul>
        ) : null}
        {targets.length > 1 ? (
          <Button
            type="button"
            variant="ghost"
            disabled={!pickedShipmentId}
            onClick={confirmPickedShipment}
            data-testid="packing-shipment-confirm-btn"
          >
            Confirmar este embarque
          </Button>
        ) : null}
      </div>

      {cartons.length > 0 ? (
        <div data-testid="packing-carton-table" style={{ marginBottom: "0.75rem", overflowX: "auto" }}>
          <h3 className="ingestion-subtitle">Volumes extraídos ({cartons.length})</h3>
          <table className="ui-table">
            <thead>
              <tr>
                <th>Carton</th>
                <th>Qtd</th>
                <th>NCM</th>
                <th>Descrição</th>
                <th>Medidas</th>
                <th>Net</th>
                <th>Gross</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cartons.map((c) => (
                <tr key={c.row_index} data-testid={`packing-carton-${c.row_index}`}>
                  <td>{c.carton_no ?? "—"}</td>
                  <td>{c.items_per_ctn ?? "—"}</td>
                  <td>{c.ncm || "—"}</td>
                  <td>{c.description}</td>
                  <td>{c.dimensions ?? "—"}</td>
                  <td>{c.total_net_weight_kg ?? "—"}</td>
                  <td>{c.total_gross_weight_kg ?? "—"}</td>
                  <td>{c.packaging ? "embalagem" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : preview && !previewBusy && !alreadyCommitted ? (
        <p role="alert" data-testid="packing-no-cartons">
          Nenhum carton extraído — o packing agrupado não preenche volumes.
        </p>
      ) : null}

      {commercial.length + packaging.length > 0 ? (
        <div data-testid="packing-line-matches" style={{ marginBottom: "0.75rem" }}>
          <h3 className="ingestion-subtitle">Casamento com o pedido</h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {commercial.concat(packaging).map((g) => (
              <li key={g.group_key} data-testid={`packing-group-${g.group_key}`} style={{ marginBottom: "0.5rem" }}>
                <strong>{g.description || "(sem descrição)"}</strong> · NCM {g.ncm || "—"} ·{" "}
                {g.carton_count} carton(s) · qty {g.total_qty} · {statusLabel(g.status)}
                {g.order_item_id ? ` → item #${g.order_item_id}` : ""}
                {g.status === "ambiguous" ? (
                  <ul style={{ margin: "0.25rem 0 0 1rem" }}>
                    {g.candidates.map((c) => (
                      <li key={c.order_item_id}>
                        <label>
                          <input
                            type="radio"
                            name={`packing-line-${g.group_key}`}
                            checked={lineChoices[g.group_key] === c.order_item_id}
                            onChange={() => {
                              const next = { ...lineChoices, [g.group_key]: c.order_item_id };
                              setLineChoices(next);
                              if (orderId.trim()) void runPreview(orderId, shipmentId, next);
                            }}
                            style={{ marginRight: "0.35rem" }}
                          />
                          item #{c.order_item_id} · {c.sku} · {c.description} · residual {c.remaining}
                        </label>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Button
        type="button"
        variant="ghost"
        disabled={previewBusy}
        onClick={() => void runPreview(orderId, shipmentId, lineChoices)}
        data-testid="packing-preview-btn"
      >
        {previewBusy ? "Calculando…" : "Atualizar preview"}
      </Button>

      {previewError ? (
        <p className="error-text" role="alert">
          {previewError}
        </p>
      ) : null}

      {preview ? (
        <div className="ingestion-preview" data-testid="packing-preview-result">
          <p>
            Pode commit: {preview.can_commit ? "sim" : "não"}
            {preview.will_create_shipment ? " · cria embarque PLANNED" : ""}
            {preview.resolved_shipment_id ? ` · reusa embarque #${preview.resolved_shipment_id}` : ""}
          </p>
          {preview.blockers.length > 0 ? (
            <ul data-testid="packing-blockers">
              {preview.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          ) : null}
          <ul>
            {preview.operations.map((op) => (
              <li key={op.op_key}>
                {op.description}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {canCommit(user) ? (
        <Button
          type="button"
          disabled={commitBusy || !preview?.can_commit}
          onClick={() => void onCommit()}
          data-testid="packing-commit-btn"
        >
          {commitBusy ? "Gravando…" : "Commit → Shipment PLANNED"}
        </Button>
      ) : (
        <p className="muted">Requer ingestion:commit + logistics:write</p>
      )}

      {commitError ? (
        <p className="error-text" role="alert" data-testid="packing-commit-error">
          {commitError}
        </p>
      ) : null}

      {attempt ? (
        <div data-testid="packing-commit-result">
          <p>
            Tentativa #{attempt.id} · {attempt.status}
            {processedShipmentId ? (
              <>
                {" "}
                ·{" "}
                <Link to={`/shipments/${processedShipmentId}`}>Abrir embarque #{processedShipmentId}</Link>
              </>
            ) : null}
          </p>
          <ul>
            {(attempt.operations ?? []).map((op) => (
              <li key={op.id}>
                {op.op_key}: {op.status}
                {op.error_message ? ` — ${op.error_message}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
        </>
      ) : null}
    </SectionCard>
  );
}
