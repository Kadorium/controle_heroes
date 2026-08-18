/**
 * PrintCommitPanel — Elo 7 / DEC-E7-PRINT
 * Anexa Print Declaration ao processo. Documents only.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  commitPrint,
  fetchPrintPreview,
  type CommitAttemptOut,
  type PrintPreviewOut,
} from "./ingestionApi";

type Props = { documentId: number; user: User };

function canCommit(user: User): boolean {
  const p = user.permissions ?? [];
  return user.role === "admin" || (p.includes("ingestion:commit") && p.includes("customs:write"));
}

export function PrintCommitPanel({ documentId, user }: Props) {
  const [processId, setProcessId] = useState("");
  const [picked, setPicked] = useState("");
  const [opKey, setOpKey] = useState(() => `print-${documentId}-${Date.now()}`);
  const [preview, setPreview] = useState<PrintPreviewOut | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);

  const runPreview = useCallback(
    async (pid: string) => {
      setBusy(true);
      setPreviewError(null);
      try {
        setPreview(await fetchPrintPreview(documentId, pid.trim() ? Number(pid) : null));
      } catch (e) {
        setPreviewError(e instanceof Error ? e.message : "Falha no preview Print");
      } finally {
        setBusy(false);
      }
    },
    [documentId],
  );

  useEffect(() => {
    void runPreview(processId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const already = Boolean(preview?.already_committed);
  const linkedId = useMemo(() => {
    if (preview?.last_succeeded_process_id) return preview.last_succeeded_process_id;
    const op = attempt?.operations?.find(
      (o) => o.entity_type === "import_process" && o.entity_id,
    );
    return op?.entity_id ? Number(op.entity_id) : null;
  }, [attempt, preview]);

  async function onCommit() {
    if (!canCommit(user) || !preview?.can_commit) return;
    setBusy(true);
    setCommitError(null);
    try {
      const result = await commitPrint(documentId, {
        operation_key: opKey,
        process_id: processId.trim() ? Number(processId) : null,
      });
      setAttempt(result);
      setOpKey(`print-${documentId}-${Date.now()}`);
      await runPreview(processId);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : "Falha ao anexar Print");
    } finally {
      setBusy(false);
    }
  }

  const targets = preview?.process_targets ?? [];

  return (
    <SectionCard title="Anexar Print Declaration ao processo" data-testid="print-commit-panel">
      <p className="muted">
        O Print é evidência documental. Códigos Y e invoice_ref não são fonte de quantidade, imposto
        ou DUIMP.
      </p>
      {already ? (
        <Notice tone="info" data-testid="print-processed-banner">
          Print já anexado ao processo{" "}
          {linkedId ? <Link to={`/customs/${linkedId}`}>#{linkedId}</Link> : "existente"}.
        </Notice>
      ) : null}
      {previewError ? <Notice tone="danger">{previewError}</Notice> : null}
      {commitError ? <Notice tone="danger">{commitError}</Notice> : null}
      {!already ? (
        <>
          <p data-testid="print-invoice-ref">
            Referência de fatura no Print: <strong>{preview?.invoice_ref ?? "—"}</strong>
          </p>
          {preview?.process_targets_reason ? (
            <p role="alert">{preview.process_targets_reason}</p>
          ) : null}
          {targets.map((t) => (
            <label key={t.process_id} style={{ display: "block" }}>
              <input
                type="radio"
                name="print-process"
                checked={picked === String(t.process_id)}
                onChange={() => setPicked(String(t.process_id))}
                data-testid={`print-process-candidate-${t.process_id}`}
              />{" "}
              #{t.process_id} {t.code} · {t.status}
              {t.evidence?.length ? (
                <span className="muted"> {t.evidence.join(" · ")}</span>
              ) : null}
            </label>
          ))}
          {targets.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              disabled={!picked}
              data-testid="print-process-confirm"
              onClick={() => {
                setProcessId(picked);
                void runPreview(picked);
              }}
            >
              Confirmar processo
            </Button>
          ) : null}
          {canCommit(user) ? (
            <Button
              type="button"
              disabled={busy || !preview?.can_commit}
              data-testid="print-commit-submit"
              onClick={() => void onCommit()}
            >
              Anexar Print
            </Button>
          ) : null}
        </>
      ) : null}
    </SectionCard>
  );
}
