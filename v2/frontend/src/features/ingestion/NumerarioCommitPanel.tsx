/**
 * NumerarioCommitPanel — J3-I6 / J3-UIV
 */
import { useEffect, useState } from "react";
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

export function NumerarioCommitPanel({ documentId }: Props) {
  const [processIdsInput, setProcessIdsInput] = useState("");
  const [preview, setPreview] = useState<NumerarioPreviewOut | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [pendingAttempts, setPendingAttempts] = useState<CommitAttemptOut[]>([]);

  const [opKey] = useState(() => `ING-NUM-DOC-${documentId}-${Date.now()}`);
  const [commitResult, setCommitResult] = useState<NumerarioCommitResultOut | null>(null);
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitError, setCommitError] = useState<string | null>(null);

  useEffect(() => {
    void listDocumentCommitAttempts(documentId)
      .then((attempts) =>
        setPendingAttempts(
          attempts.filter((a) => a.status === "PARTIAL" || a.status === "UNKNOWN" || a.status === "FAILED"),
        ),
      )
      .catch(() => setPendingAttempts([]));
  }, [documentId, commitResult]);

  function parseProcessIds(): number[] {
    return processIdsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number)
      .filter((n) => !isNaN(n) && n > 0);
  }

  async function handlePreview() {
    const pids = parseProcessIds();
    if (!pids.length) {
      setPreviewError("Informe ao menos um ID de processo (separados por vírgula).");
      return;
    }
    setPreviewLoading(true);
    setPreviewError(null);
    setPreview(null);
    setCommitResult(null);
    try {
      setPreview(await fetchNumerarioPreview(documentId, pids));
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : String(e));
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleCommit() {
    if (!preview) return;
    const pids = parseProcessIds();
    if (!pids.length) return;
    setCommitLoading(true);
    setCommitError(null);
    try {
      setCommitResult(await commitNumerarioDocument(documentId, { operation_key: opKey, process_ids: pids }));
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : String(e));
    } finally {
      setCommitLoading(false);
    }
  }

  return (
    <SectionCard title="Numerário — commit multi-owner" data-testid="numerario-commit-panel">
      <Notice tone="warning" data-testid="numerario-no-payment-notice">
        Cria <strong>FundingRequest DRAFT</strong> por processo. Nunca confirma automaticamente. Não cria
        Payment nem liquida CUSTOMS_FUNDING — confirmação é ação humana separada no processo aduaneiro.
      </Notice>

      <label className="form-label">
        IDs de ImportProcess (vírgula)
        <input
          type="text"
          placeholder="Ex: 1, 2, 3"
          value={processIdsInput}
          onChange={(e) => setProcessIdsInput(e.target.value)}
          data-testid="numerario-process-ids"
          className="ds-input"
        />
      </label>

      <div className="ingestion-commit-actions">
        <Button type="button" variant="ghost" disabled={previewLoading} onClick={() => void handlePreview()}>
          {previewLoading ? "Carregando…" : "Preview"}
        </Button>
        {preview?.can_commit && !commitResult ? (
          <Button type="button" disabled={commitLoading} onClick={() => void handleCommit()} data-testid="numerario-commit-submit">
            {commitLoading ? "Commitando…" : "Commit (DRAFT)"}
          </Button>
        ) : null}
      </div>

      {previewError ? <p className="error-text">{previewError}</p> : null}
      {commitError ? <p className="error-text">{commitError}</p> : null}

      {preview ? (
        <div data-testid="numerario-preview">
          <p>
            Pode commit: {preview.can_commit ? "sim" : `não (${preview.open_error_count} erro(s))`}
          </p>
          {preview.invoice_refs.length > 0 ? (
            <p className="muted">Refs fatura: {preview.invoice_refs.join(", ")}</p>
          ) : null}
          <ul>
            {preview.planned_operations.map((op) => (
              <li key={op.op_key}>
                [{op.entity_type ?? "—"}] {op.description}
                {op.process_id ? (
                  <>
                    {" "}
                    <Link to={`/customs/${op.process_id}`} data-testid={`numerario-process-link-${op.process_id}`}>
                      Processo #{op.process_id}
                    </Link>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {commitResult ? (
        <div data-testid="numerario-commit-result">
          <p>
            Status:{" "}
            <strong className={statusClass(commitResult.status)}>
              {STATUS_LABEL[commitResult.status] ?? commitResult.status}
            </strong>{" "}
            · attempt #{commitResult.attempt_id}
          </p>
          <table className="dense-table">
            <thead>
              <tr>
                <th>Op</th>
                <th>Status</th>
                <th>Entidade</th>
              </tr>
            </thead>
            <tbody>
              {commitResult.operations.map((op) => (
                <tr key={op.op_key}>
                  <td>
                    <code>{op.op_key}</code>
                  </td>
                  <td className={statusClass(op.status)}>{STATUS_LABEL[op.status] ?? op.status}</td>
                  <td>
                    {op.entity_type === "funding_request" && op.entity_id ? (
                      <Link
                        to={`/customs/funding/${op.entity_id}`}
                        data-testid={`numerario-funding-link-${op.entity_id}`}
                      >
                        FundingRequest #{op.entity_id}
                      </Link>
                    ) : op.entity_id ? (
                      `#${op.entity_id}`
                    ) : op.error_message ? (
                      <span className="error-text">{op.error_message}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {commitResult.status === "PARTIAL" ? (
            <Notice tone="warning">PARTIAL: verifique operações com falha acima. Sem rollback cross-owner.</Notice>
          ) : null}
          {commitResult.status === "UNKNOWN" ? (
            <Notice tone="info">UNKNOWN: estado indeterminado — consulte tentativas anteriores ou o ledger.</Notice>
          ) : null}
        </div>
      ) : null}

      {pendingAttempts.length > 0 ? (
        <div data-testid="numerario-pending-attempts">
          <h3 className="ingestion-subtitle">Tentativas pendentes / retomar</h3>
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
