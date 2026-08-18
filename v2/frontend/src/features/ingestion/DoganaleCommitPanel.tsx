/**
 * DoganaleCommitPanel — Elo 7
 * Preview 0/1/N processo / fatura / embarque. PDF preenche CustomsDoganale.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  commitDoganale,
  fetchDoganalePreview,
  type CommitAttemptOut,
  type DoganalePreviewOut,
} from "./ingestionApi";

type Props = { documentId: number; user: User };

function canCommit(user: User): boolean {
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("customs:write"));
}

export function DoganaleCommitPanel({ documentId, user }: Props) {
  const [processId, setProcessId] = useState("");
  const [pickedProcessId, setPickedProcessId] = useState("");
  const [invoiceId, setInvoiceId] = useState("");
  const [pickedInvoiceId, setPickedInvoiceId] = useState("");
  const [shipmentId, setShipmentId] = useState("");
  const [pickedShipmentId, setPickedShipmentId] = useState("");
  const [opKey, setOpKey] = useState(() => `doganale-${documentId}-${Date.now()}`);

  const [preview, setPreview] = useState<DoganalePreviewOut | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitBusy, setCommitBusy] = useState(false);

  const runPreview = useCallback(
    async (pid: string, iid: string, sid: string) => {
      setPreviewBusy(true);
      setPreviewError(null);
      try {
        const result = await fetchDoganalePreview(documentId, {
          process_id: pid.trim() ? Number(pid) : null,
          invoice_id: iid.trim() ? Number(iid) : null,
          shipment_id: sid.trim() ? Number(sid) : null,
        });
        setPreview(result);
      } catch (e) {
        setPreviewError(e instanceof Error ? e.message : "Falha no preview Doganale");
      } finally {
        setPreviewBusy(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    void runPreview(processId, invoiceId, shipmentId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const alreadyCommitted = Boolean(preview?.already_committed);
  const processIdFromAttempt = useMemo(() => {
    if (preview?.last_succeeded_process_id) return preview.last_succeeded_process_id;
    const op = attempt?.operations?.find(
      (o) =>
        (o.entity_type === "import_process" || o.entity_type === "process") &&
        o.entity_id &&
        o.status === "SUCCEEDED",
    );
    return op?.entity_id ? Number(op.entity_id) : null;
  }, [attempt, preview]);

  async function onCommit() {
    if (!canCommit(user) || !preview?.can_commit) return;
    setCommitBusy(true);
    setCommitError(null);
    try {
      const result = await commitDoganale(documentId, {
        operation_key: opKey,
        process_id: processId.trim() ? Number(processId) : null,
        invoice_id: invoiceId.trim() ? Number(invoiceId) : null,
        shipment_id: shipmentId.trim() ? Number(shipmentId) : null,
      });
      setAttempt(result);
      setOpKey(`doganale-${documentId}-${Date.now()}`);
      await runPreview(processId, invoiceId, shipmentId);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : "Falha no commit Doganale");
    } finally {
      setCommitBusy(false);
    }
  }

  const targets = preview?.process_targets ?? [];
  const invoices = preview?.invoice_candidates ?? [];
  const shipments = preview?.shipment_targets ?? [];

  return (
    <SectionCard title="Commit Fattura Doganale → processo aduaneiro" data-testid="doganale-commit-panel">
      <p className="muted">
        A Doganale preenche a declaração (NCM, quantidades, valores). Não contém impostos brasileiros
        (II/IPI/PIS). O processo não é criado em silêncio quando já existe candidato. DUIMP continua
        digitado na submissão.
      </p>

      {alreadyCommitted ? (
        <Notice tone="info" data-testid="doganale-processed-banner" title="Doganale processada">
          <p>
            Processo{" "}
            {processIdFromAttempt ? (
              <Link to={`/customs/${processIdFromAttempt}`} data-testid="doganale-process-link">
                #{processIdFromAttempt}
              </Link>
            ) : (
              "já preenchido"
            )}{" "}
            a partir deste documento. Recarregar ou novo clique não cria outro processo.
          </p>
        </Notice>
      ) : null}

      {previewError ? <Notice tone="danger">{previewError}</Notice> : null}
      {commitError ? <Notice tone="danger">{commitError}</Notice> : null}

      {!alreadyCommitted ? (
        <>
          <div data-testid="doganale-process-candidates" style={{ marginBottom: "0.75rem" }}>
            <h3 className="ingestion-subtitle">Processo aduaneiro</h3>
            {previewBusy && !preview ? <p className="muted">Buscando candidatos…</p> : null}
            {preview?.will_create_process ? (
              <p data-testid="doganale-process-none">
                Nenhum processo compatível. O commit criará um rascunho novo.
              </p>
            ) : null}
            {preview?.process_targets_reason ? (
              <p role="alert" data-testid="doganale-process-reason">
                {preview.process_targets_reason}
              </p>
            ) : null}
            {targets.length === 1 ? (
              <p data-testid="doganale-process-suggested">
                Sugestão: processo <strong>#{targets[0].process_id} {targets[0].code}</strong> (
                {targets[0].status}). Confirme — não há reuso automático.
              </p>
            ) : null}
            {targets.length > 1 ? (
              <p data-testid="doganale-process-multiple">
                {targets.length} processos possíveis. O sistema não escolhe em silêncio.
              </p>
            ) : null}
            {targets.length > 0 ? (
              <ul style={{ listStyle: "none", padding: 0 }}>
                {targets.map((t) => (
                  <li key={t.process_id}>
                    <label>
                      <input
                        type="radio"
                        name="doganale-process"
                        disabled={!t.compatible}
                        checked={pickedProcessId === String(t.process_id)}
                        onChange={() => setPickedProcessId(String(t.process_id))}
                        data-testid={`doganale-process-candidate-${t.process_id}`}
                      />{" "}
                      #{t.process_id} {t.code} · {t.status}
                      {t.compatible ? "" : " — não reutilizável"}
                      <span className="muted"> {t.evidence.join(" · ")}</span>
                    </label>
                  </li>
                ))}
              </ul>
            ) : null}
            {targets.length > 0 ? (
              <Button
                type="button"
                variant="ghost"
                disabled={!pickedProcessId}
                data-testid="doganale-process-confirm"
                onClick={() => {
                  setProcessId(pickedProcessId);
                  void runPreview(pickedProcessId, invoiceId, shipmentId);
                }}
              >
                Confirmar processo
              </Button>
            ) : null}
          </div>

          <div data-testid="doganale-invoice-candidates" style={{ marginBottom: "0.75rem" }}>
            <h3 className="ingestion-subtitle">Fatura</h3>
            {preview?.invoice_candidates_reason ? (
              <p className="muted">{preview.invoice_candidates_reason}</p>
            ) : null}
            {invoices.map((c) => (
              <label key={c.invoice_id} style={{ display: "block" }}>
                <input
                  type="radio"
                  name="doganale-invoice"
                  checked={pickedInvoiceId === String(c.invoice_id)}
                  onChange={() => setPickedInvoiceId(String(c.invoice_id))}
                  data-testid={`doganale-invoice-candidate-${c.invoice_id}`}
                />{" "}
                Fatura {c.invoice_number} #{c.invoice_id} ({c.status})
              </label>
            ))}
            {invoices.length > 0 ? (
              <Button
                type="button"
                variant="ghost"
                disabled={!pickedInvoiceId}
                data-testid="doganale-invoice-confirm"
                onClick={() => {
                  setInvoiceId(pickedInvoiceId);
                  void runPreview(processId, pickedInvoiceId, shipmentId);
                }}
              >
                Confirmar fatura
              </Button>
            ) : null}
          </div>

          <div data-testid="doganale-shipment-candidates" style={{ marginBottom: "0.75rem" }}>
            <h3 className="ingestion-subtitle">Embarque</h3>
            {preview?.shipment_targets_reason ? (
              <p className="muted">{preview.shipment_targets_reason}</p>
            ) : null}
            {shipments.map((s) => (
              <label key={s.shipment_id} style={{ display: "block" }}>
                <input
                  type="radio"
                  name="doganale-shipment"
                  disabled={!s.compatible}
                  checked={pickedShipmentId === String(s.shipment_id)}
                  onChange={() => setPickedShipmentId(String(s.shipment_id))}
                  data-testid={`doganale-shipment-candidate-${s.shipment_id}`}
                />{" "}
                Embarque {s.code} #{s.shipment_id} · {s.status}
              </label>
            ))}
            {shipments.length > 0 ? (
              <Button
                type="button"
                variant="ghost"
                disabled={!pickedShipmentId}
                data-testid="doganale-shipment-confirm"
                onClick={() => {
                  setShipmentId(pickedShipmentId);
                  void runPreview(processId, invoiceId, pickedShipmentId);
                }}
              >
                Confirmar embarque
              </Button>
            ) : null}
          </div>

          <div data-testid="doganale-lines-preview">
            <h3 className="ingestion-subtitle">Linhas extraídas</h3>
            {(preview?.lines ?? []).length === 0 ? (
              <p className="muted">Nenhuma linha comercial.</p>
            ) : (
              <ul>
                {(preview?.lines ?? []).map((ln) => (
                  <li key={ln.position}>
                    {ln.quantity} {ln.unit} · NCM {ln.ncm} · {ln.description} · {ln.line_amount}{" "}
                    {ln.currency}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {preview?.blockers?.length ? (
            <Notice tone="warning" data-testid="doganale-blockers">
              <ul>
                {preview.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </Notice>
          ) : null}

          {canCommit(user) ? (
            <Button
              type="button"
              disabled={commitBusy || previewBusy || !preview?.can_commit}
              data-testid="doganale-commit-submit"
              onClick={() => void onCommit()}
            >
              {preview?.will_create_process
                ? "Criar processo e preencher declaração"
                : "Preencher declaração"}
            </Button>
          ) : (
            <p className="muted">Requer ingestion:commit + customs:write</p>
          )}
        </>
      ) : null}
    </SectionCard>
  );
}
