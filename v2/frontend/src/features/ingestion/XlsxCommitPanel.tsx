import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, SectionCard } from "../../ui";
import {
  commitXlsxDocument,
  fetchXlsxPreview,
  type DocumentDetail,
  type XlsxCommitResultOut,
  type XlsxPreviewOut,
} from "./ingestionApi";

type Props = { documentId: number; doc: DocumentDetail; user: User };

function canCommit(user: User) {
  const perms = user.permissions ?? [];
  return user.role === "admin" || (perms.includes("ingestion:commit") && perms.includes("orders:write"));
}

function fieldValue(doc: DocumentDetail, key: string): string {
  const f = (doc.fields ?? []).find((x) => x.field_key === key);
  return f?.effective_value ?? f?.normalized_value ?? f?.raw_value ?? "—";
}

export function XlsxCommitPanel({ documentId, doc, user }: Props) {
  const [preview, setPreview] = useState<XlsxPreviewOut | null>(null);
  const [result, setResult] = useState<XlsxCommitResultOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [opKey] = useState(() => `xlsx-commit-${documentId}-${Date.now()}`);

  const formulaCount = useMemo(() => fieldValue(doc, "formula_cell_count"), [doc]);
  const sheetName = useMemo(() => fieldValue(doc, "sheet_name"), [doc]);
  const orderNumber = useMemo(() => fieldValue(doc, "order_number"), [doc]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const p = await fetchXlsxPreview(documentId);
        if (!cancelled) setPreview(p);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro preview");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  async function onCommit() {
    if (!canCommit(user)) return;
    setBusy(true);
    setError(null);
    try {
      const r = await commitXlsxDocument(documentId, opKey);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro commit");
    } finally {
      setBusy(false);
    }
  }

  const orderOp = result?.operations.find((o) => o.entity_type === "order" && o.entity_id);

  return (
    <SectionCard title="Ordine XLSX — commit" data-testid="xlsx-commit-panel">
      <p className="muted">
        Planilha: <strong>{sheetName}</strong> · pedido: <strong>{orderNumber}</strong> · células com
        fórmula: <strong>{formulaCount}</strong>
      </p>
      <NoticeReplay />

      {error ? <p className="error-text">{error}</p> : null}

      {preview ? (
        <div data-testid="xlsx-preview">
          <p className="muted">
            Digest: <code>{preview.fingerprint}</code>
          </p>
          <p>
            Pode commit: {preview.can_commit ? "sim" : "não"}
            {preview.open_error_count ? ` · erros: ${preview.open_error_count}` : ""}
          </p>
          <ul>
            {preview.operations.map((op) => (
              <li key={op.op_key}>
                <code>{op.op_key}</code>: {op.description}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted">Carregando preview…</p>
      )}

      {canCommit(user) ? (
        <Button
          type="button"
          disabled={busy || !preview?.can_commit}
          onClick={() => void onCommit()}
          data-testid="xlsx-commit-submit"
        >
          {busy ? "Commitando…" : "Commit XLSX (Order DRAFT)"}
        </Button>
      ) : (
        <p className="muted">Requer ingestion:commit e orders:write</p>
      )}

      {result ? (
        <div data-testid="xlsx-commit-result">
          <p>
            Status: <strong>{result.status}</strong> · attempt #{result.attempt_id}
          </p>
          <ul>
            {result.operations.map((op) => (
              <li key={op.op_key}>
                {op.op_key}: {op.status}
                {op.entity_type === "order" && op.entity_id ? (
                  <>
                    {" → "}
                    <Link to={`/orders/${op.entity_id}`}>Order #{op.entity_id}</Link>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
          {orderOp?.entity_id ? (
            <Link className="ui-button" to={`/orders/${orderOp.entity_id}`}>
              Abrir Order DRAFT
            </Link>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}

function NoticeReplay() {
  return (
    <p className="notice notice--info ingestion-xlsx-replay-note" data-testid="xlsx-replay-note">
      Replay: valores materializados da planilha são persistidos no IR; fórmulas não são reavaliadas no
      commit — apenas os valores extraídos.
    </p>
  );
}
