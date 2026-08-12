import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard, TextInput } from "../../ui";
import {
  IngestionApiError,
  commitIngestionDocument,
  fetchCommitPreview,
  fetchIngestionDocument,
  setIngestionOrderCode,
  type CommitAttemptOut,
  type PreviewCommitOut,
} from "./ingestionApi";
import { humanPreviewSteps } from "./ordinePreviewHuman";

type Props = {
  documentId: number;
  user: User;
  refreshToken?: number | string;
  onCommitted?: () => void;
  onNeedSupplierLink?: () => void;
  onCodeChanged?: () => void;
};

function canCommit(user: User) {
  const perms = user.permissions ?? [];
  return (
    user.role === "admin" ||
    (perms.includes("ingestion:commit") && perms.includes("orders:write"))
  );
}

function canCatalogWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

function humanAttemptStatus(status: string): string {
  if (status === "SUCCEEDED") return "Pedido criado";
  if (status === "FAILED") return "Não foi possível criar o pedido";
  return status;
}

export function CommitResultPanel({
  documentId,
  user,
  refreshToken,
  onCommitted,
  onNeedSupplierLink,
  onCodeChanged,
}: Props) {
  const [preview, setPreview] = useState<PreviewCommitOut | null>(null);
  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [linkPendency, setLinkPendency] = useState<string | null>(null);
  const [orderCodeConflict, setOrderCodeConflict] = useState<{
    orderId: number;
    orderCode: string;
  } | null>(null);
  const [orderCodeDraft, setOrderCodeDraft] = useState("");
  const [busy, setBusy] = useState(false);
  // op_key fresco a cada tentativa (evita conflito de fingerprint após mudar código)

  const previewOrderCode = useMemo(() => {
    const op = (preview?.operations ?? []).find((o) => o.op_key === "create_order");
    return String(op?.params?.code ?? "").trim();
  }, [preview?.operations]);

  useEffect(() => {
    if (previewOrderCode && !orderCodeConflict) {
      setOrderCodeDraft(previewOrderCode);
    }
  }, [previewOrderCode, orderCodeConflict]);

  async function reloadPreview() {
    const p = await fetchCommitPreview(documentId);
    setPreview(p);
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const p = await fetchCommitPreview(documentId);
        if (!cancelled) {
          setPreview(p);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro ao carregar o próximo passo");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [documentId, refreshToken]);

  const needsCreateSupplier = (preview?.operations ?? []).some((o) => o.op_key === "create_supplier");
  const hasCatalogPerm = canCatalogWrite(user);
  const catalogBlocks = needsCreateSupplier && !hasCatalogPerm;

  const humanSteps = useMemo(
    () => humanPreviewSteps(preview?.operations ?? []),
    [preview?.operations],
  );

  const hasSkipOrder = (preview?.operations ?? []).some((o) => o.op_key === "skip_order");
  const canCreate =
    Boolean(preview?.can_create_order ?? preview?.can_commit) &&
    !hasSkipOrder &&
    Boolean(preview?.can_commit) &&
    !catalogBlocks;

  async function persistOrderCode(code: string): Promise<boolean> {
    const trimmed = code.trim();
    if (!trimmed) {
      setError("Informe o código do pedido.");
      return false;
    }
    if (trimmed === previewOrderCode) return true;
    const doc = await fetchIngestionDocument(documentId);
    await setIngestionOrderCode(documentId, {
      order_code: trimmed,
      expected_version: doc.version,
      reason: "proximo_passo_codigo",
    });
    onCodeChanged?.();
    await reloadPreview();
    return true;
  }

  async function onCommit() {
    if (!canCommit(user)) {
      setError("Você não tem permissão para criar o pedido a partir desta importação.");
      return;
    }
    if (!canCreate && !orderCodeConflict) {
      setError("Ainda não é possível criar o pedido — resolva as pendências acima.");
      return;
    }
    setBusy(true);
    setError(null);
    setLinkPendency(null);
    setAttempt(null);
    try {
      const ok = await persistOrderCode(orderCodeDraft || previewOrderCode);
      if (!ok) return;
      const key = `ordine-commit-${documentId}-${Date.now()}`;
      const result = await commitIngestionDocument(documentId, { operation_key: key });
      setAttempt(result);
      setOrderCodeConflict(null);
      onCommitted?.();
    } catch (e) {
      if (e instanceof IngestionApiError && e.code === "commit_order_code_exists") {
        const orderId = Number(e.details?.order_id);
        const orderCode = String(e.details?.order_code ?? orderCodeDraft);
        setOrderCodeConflict({
          orderId: Number.isFinite(orderId) ? orderId : 0,
          orderCode,
        });
        setError(null);
      } else if (e instanceof IngestionApiError && e.code === "commit_supplier_link_required") {
        setLinkPendency(
          "Este fornecedor já existe no cadastro. Vincule-o na pendência acima — nada foi gravado.",
        );
        onNeedSupplierLink?.();
      } else if (e instanceof IngestionApiError && e.status === 409 && /vincular/i.test(e.message)) {
        setLinkPendency(
          "Este fornecedor já existe no cadastro. Vincule-o na pendência acima — nada foi gravado.",
        );
        onNeedSupplierLink?.();
      } else {
        setError(e instanceof Error ? e.message : "Não foi possível criar o pedido");
      }
    } finally {
      setBusy(false);
    }
  }

  const orderOp = attempt?.operations?.find((o) => o.entity_type === "order" && o.entity_id);
  const orderId = orderOp?.entity_id ? String(orderOp.entity_id) : null;
  const failedOp = attempt?.operations?.find((o) => o.status === "FAILED");

  return (
    <SectionCard title="Próximo passo" data-testid="ingestion-commit-panel">
      {error ? (
        <Notice tone="danger" data-testid="commit-error">
          {error}
        </Notice>
      ) : null}
      {linkPendency ? (
        <Notice tone="info" data-testid="commit-link-pendency">
          {linkPendency}
        </Notice>
      ) : null}

      {orderCodeConflict ? (
        <Notice tone="info" data-testid="commit-order-code-conflict">
          <p>O pedido {orderCodeConflict.orderCode} já existe no sistema.</p>
          <p className="muted">Nada foi gravado.</p>
          <div className="stack-row" style={{ marginTop: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
            {orderCodeConflict.orderId ? (
              <Link
                className="ui-button"
                to={`/orders/${orderCodeConflict.orderId}/commercial`}
                data-testid="commit-open-existing-order"
              >
                Abrir pedido existente
              </Link>
            ) : null}
            <label className="stack-row" style={{ alignItems: "center", gap: "0.35rem" }}>
              Criar com outro código:
              <TextInput
                value={orderCodeDraft}
                onChange={(e) => setOrderCodeDraft(e.target.value)}
                data-testid="commit-alt-order-code"
                style={{ width: "8rem" }}
              />
            </label>
            <Button
              type="button"
              disabled={busy || !orderCodeDraft.trim()}
              onClick={() => void onCommit()}
              data-testid="commit-retry-alt-code"
            >
              Criar com este código
            </Button>
          </div>
        </Notice>
      ) : null}

      {preview ? (
        <div className="ingestion-preview" data-testid="ingestion-preview">
          <p data-testid="preview-human-summary">
            {preview.human_summary ||
              (canCreate
                ? "Pronto para criar o pedido em rascunho."
                : "Ainda há pendências antes de criar o pedido.")}
          </p>
          {(preview.blocking_reasons ?? []).length > 0 ? (
            <div data-testid="preview-whats-missing">
              <p className="muted">O que ainda falta:</p>
              <ul data-testid="preview-blocking-reasons">
                {(preview.blocking_reasons ?? []).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {humanSteps.length > 0 ? (
            <>
              <p className="muted">Ao criar o pedido, o sistema vai:</p>
              <ol data-testid="preview-ops-human">
                {humanSteps.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </>
          ) : null}
          {!orderCodeConflict ? (
            <label className="ingestion-order-code-edit" data-testid="commit-order-code-field">
              Código interno do pedido
              <TextInput
                value={orderCodeDraft}
                onChange={(e) => setOrderCodeDraft(e.target.value)}
                data-testid="commit-order-code-input"
              />
              <span className="muted" style={{ display: "block", fontSize: "0.85rem" }}>
                O número do documento (vínculo com a fatura) permanece o do PDF.
              </span>
            </label>
          ) : null}
        </div>
      ) : (
        <p className="muted">Carregando próximo passo…</p>
      )}

      {catalogBlocks ? (
        <Notice tone="info" data-testid="commit-catalog-perm-notice">
          Para cadastrar o fornecedor ao criar o pedido, é necessário permissão de cadastro de
          fornecedores. Peça a um administrador ou vincule um fornecedor já existente.
        </Notice>
      ) : null}

      {canCommit(user) && !orderCodeConflict ? (
        <div className="ingestion-commit-actions">
          <Button
            type="button"
            disabled={busy || !canCreate}
            onClick={() => void onCommit()}
            data-testid="commit-submit"
          >
            Criar pedido em rascunho
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={() => void reloadPreview()}
            data-testid="preview-reload"
          >
            Atualizar
          </Button>
        </div>
      ) : null}
      {!canCommit(user) ? (
        <p className="muted">Você não tem permissão para criar o pedido a partir desta importação.</p>
      ) : null}

      {attempt ? (
        <div data-testid="commit-result" className="ingestion-commit-result">
          <p data-testid="commit-result-status">
            <strong>{humanAttemptStatus(attempt.status)}</strong>
          </p>
          {attempt.status === "SUCCEEDED" && orderId ? (
            <p>
              O pedido foi criado em rascunho.{" "}
              <Link className="ui-button" to={`/orders/${orderId}/commercial`} data-testid="commit-order-open">
                Abrir pedido
              </Link>
            </p>
          ) : null}
          {attempt.status === "FAILED" ? (
            <Notice tone="danger" data-testid="commit-failure-notice">
              <p>
                {failedOp?.error_message
                  ? `Motivo: ${failedOp.error_message}`
                  : "A criação do pedido falhou."}
              </p>
              <p>
                Nada foi gravado (nem o arquivo, nem o pedido, nem o fornecedor). Corrija o problema e
                tente de novo.
              </p>
            </Notice>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
