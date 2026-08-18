/**
 * NumerarioCommitPanel — Elo 7 / E7-TAX
 * Registro tributário via PDF real. Sem colar IDs. Sem settlement.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  commitNumerarioDocument,
  fetchNumerarioPreview,
  listDocumentCommitAttempts,
  type CommitAttemptOut,
  type NumerarioCommitResultOut,
  type NumerarioPreviewOut,
} from "./ingestionApi";

type Props = { documentId: number; user?: User };

const STATUS_LABEL: Record<string, string> = {
  SUCCEEDED: "Sucesso",
  FAILED: "Falhou",
  PARTIAL: "Parcial — algumas ops falharam",
  UNKNOWN: "Indeterminado — consulte o ledger",
};

function statusClass(status: string): string {
  if (status === "SUCCEEDED") return "status-ok";
  if (status === "FAILED") return "status-error";
  if (status === "PARTIAL") return "status-warn";
  return "status-muted";
}

function canCommit(user?: User): boolean {
  if (!user) return false;
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("customs:write"));
}

export function NumerarioCommitPanel({ documentId, user }: Props) {
  const [pickedId, setPickedId] = useState("");
  const [confirmedIds, setConfirmedIds] = useState<number[]>([]);
  const [opKey, setOpKey] = useState(() => `ING-NUM-DOC-${documentId}-${Date.now()}`);
  const [preview, setPreview] = useState<NumerarioPreviewOut | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [pendingAttempts, setPendingAttempts] = useState<CommitAttemptOut[]>([]);
  const [commitResult, setCommitResult] = useState<NumerarioCommitResultOut | null>(null);
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);

  const runPreview = useCallback(
    async (pids: number[]) => {
      setPreviewLoading(true);
      setPreviewError(null);
      try {
        setPreview(await fetchNumerarioPreview(documentId, pids));
      } catch (e) {
        setPreviewError(e instanceof Error ? e.message : String(e));
      } finally {
        setPreviewLoading(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    void runPreview([]);
  }, [runPreview]);

  useEffect(() => {
    void listDocumentCommitAttempts(documentId)
      .then((attempts) =>
        setPendingAttempts(
          attempts.filter((a) => a.status === "PARTIAL" || a.status === "UNKNOWN" || a.status === "FAILED"),
        ),
      )
      .catch(() => setPendingAttempts([]));
  }, [documentId, commitResult]);

  const already = Boolean(preview?.already_committed);
  const candidates = preview?.process_candidates ?? [];

  async function handleCommit(createProcess = false) {
    if (!canCommit(user)) return;
    setCommitLoading(true);
    setCommitError(null);
    try {
      const result = await commitNumerarioDocument(documentId, {
        operation_key: opKey,
        process_ids: createProcess ? [] : confirmedIds,
        create_process: createProcess,
      });
      setCommitResult(result);
      setOpKey(`ING-NUM-DOC-${documentId}-${Date.now()}`);
      await runPreview(confirmedIds);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : String(e));
    } finally {
      setCommitLoading(false);
    }
  }

  const fundingId = commitResult?.operations.find(
    (o) => o.entity_type === "customs_funding_request" && o.entity_id,
  )?.entity_id;
  const processFromCommit = commitResult?.operations.find(
    (o) => o.entity_type === "import_process" && o.entity_id,
  )?.entity_id;

  return (
    <SectionCard title="Numerário — registrar impostos (sem pagar)" data-testid="numerario-commit-panel">
      <Notice tone="warning" data-testid="numerario-no-payment-notice">
        Registra bases, linhas de imposto e despesas num FundingRequest DRAFT. Confirmar o numerário
        no processo nasce a obrigação (payable CUSTOMS_FUNDING em aberto). Este passo{" "}
        <strong>não paga</strong> no tesouro.
      </Notice>

      {already ? (
        <Notice tone="info" data-testid="numerario-processed-banner">
          Numerário já registrado a partir deste documento. Recarregar não duplica linhas nem payable.
        </Notice>
      ) : null}

      {previewError ? <Notice tone="danger">{previewError}</Notice> : null}
      {commitError ? <Notice tone="danger">{commitError}</Notice> : null}

      {!already ? (
        <>
          {preview?.invoice_refs?.length ? (
            preview.invoice_refs.length > 1 ? (
              <Notice tone="warning" data-testid="numerario-invoice-refs">
                Este documento cita várias faturas ({preview.invoice_refs.join(", ")}). Os tributos
                são do Numerário (nível DUIMP), não só da fatura desta compra.
              </Notice>
            ) : (
              <p className="muted" data-testid="numerario-invoice-refs">
                Fatura no PDF: {preview.invoice_refs.join(", ")}
              </p>
            )
          ) : null}
          {preview?.process_candidates_reason ? (
            <p role="alert">{preview.process_candidates_reason}</p>
          ) : null}

          <div data-testid="numerario-process-candidates">
            {candidates.map((c) => (
              <label key={c.process_id} style={{ display: "block" }}>
                <input
                  type="radio"
                  name="numerario-process"
                  checked={pickedId === String(c.process_id)}
                  onChange={() => setPickedId(String(c.process_id))}
                  data-testid={`numerario-process-candidate-${c.process_id}`}
                />{" "}
                #{c.process_id} {c.code} · {c.status}
                <span className="muted"> {c.evidence.join(" · ")}</span>
              </label>
            ))}
          </div>

          {candidates.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              disabled={!pickedId}
              data-testid="numerario-process-confirm"
              onClick={() => {
                const ids = [Number(pickedId)];
                setConfirmedIds(ids);
                void runPreview(ids);
              }}
            >
              Confirmar processo
            </Button>
          ) : null}

          {previewLoading ? <p className="muted">Carregando preview…</p> : null}

          {preview && confirmedIds.length > 0 ? (
            <div data-testid="numerario-preview">
              <p>Pode registrar: {preview.can_commit ? "sim" : "não"}</p>
              <ul>
                {preview.planned_operations.map((op) => (
                  <li key={op.op_key}>{op.description}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {canCommit(user) && preview?.can_commit && confirmedIds.length > 0 ? (
            <Button
              type="button"
              disabled={commitLoading}
              data-testid="numerario-commit-submit"
              onClick={() => void handleCommit(false)}
            >
              Registrar tributos no processo
            </Button>
          ) : null}

          {canCommit(user) && preview?.can_create_process && candidates.length === 0 ? (
            <Button
              type="button"
              disabled={commitLoading}
              data-testid="numerario-create-process-submit"
              onClick={() => void handleCommit(true)}
            >
              Criar processo rascunho e registrar tributos
            </Button>
          ) : null}
        </>
      ) : null}

      {commitResult ? (
        <div data-testid="numerario-commit-result">
          <p>
            Status:{" "}
            <strong className={statusClass(commitResult.status)}>
              {STATUS_LABEL[commitResult.status] ?? commitResult.status}
            </strong>
          </p>
          {processFromCommit ? (
            <p>
              Processo{" "}
              <Link to={`/customs/${processFromCommit}`}>#{processFromCommit}</Link>
              {" — "}abra o numerário e <strong>confirme</strong> para nascer a obrigação (sem pagar).
            </p>
          ) : null}
          {fundingId ? <p>FundingRequest #{fundingId}</p> : null}
        </div>
      ) : null}

      {pendingAttempts.length > 0 ? (
        <div data-testid="numerario-pending-attempts">
          <h3 className="ingestion-subtitle">Tentativas pendentes</h3>
          <ul>
            {pendingAttempts.map((a) => (
              <li key={a.id}>
                #{a.id} · {a.status} · {a.operation_key}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </SectionCard>
  );
}
