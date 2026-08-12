/**
 * FatturaCommitPanel — J3-I4
 * Policy selection (A/B/C1/C2) + preview + commit for FATTURA_VENDITA documents.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, SectionCard } from "../../ui";
import {
  commitFatturaDocument,
  fetchFatturaPreview,
  type CommitAttemptOut,
  type FatturaPolicy,
  type FatturaPreviewOut,
} from "./ingestionApi";

type Props = { documentId: number; user: User };

const POLICIES: { value: FatturaPolicy; label: string; description: string }[] = [
  {
    value: "A",
    label: "A — Order CONFIRMED",
    description: "Order CONFIRMED já existe → cria Invoice DRAFT diretamente.",
  },
  {
    value: "B",
    label: "B — Order DRAFT (bloqueia)",
    description: "Order DRAFT existe → requer confirmação explícita separada antes de faturar.",
  },
  {
    value: "C1",
    label: "C1 — Sem Order (reconstruction DRAFT)",
    description: "Nenhuma Order → cria reconstruction DRAFT e aguarda confirmação humana.",
  },
  {
    value: "C2",
    label: "C2 — Sem Order + confirm (exceção dual-auth)",
    description:
      "Sem Order + confirm explícito na mesma sessão. EXCEÇÃO — requer motivo, dual-auth, Audit.",
  },
];

function canCommit(user: User): boolean {
  const perms = user.permissions ?? [];
  return (
    user.role === "admin" ||
    (perms.includes("ingestion:commit") &&
      perms.includes("orders:write") &&
      perms.includes("billing:write"))
  );
}

export function FatturaCommitPanel({ documentId, user }: Props) {
  const [policy, setPolicy] = useState<FatturaPolicy>("A");
  const [orderId, setOrderId] = useState<string>("");
  const [c2Reason, setC2Reason] = useState<string>("");
  const [opKey, setOpKey] = useState(() => `fattura-commit-${documentId}-${Date.now()}`);

  const [preview, setPreview] = useState<FatturaPreviewOut | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitBusy, setCommitBusy] = useState(false);

  async function onPreview() {
    if ((policy === "A" || policy === "B") && !orderId.trim()) {
      setPreviewError("Informe o Order ID — matching automático foi desativado.");
      return;
    }
    setPreviewBusy(true);
    setPreviewError(null);
    setPreview(null);
    try {
      const orderIdNum = orderId.trim() ? Number(orderId.trim()) : null;
      const p = await fetchFatturaPreview(
        documentId,
        policy,
        orderIdNum,
        policy === "C2" ? true : false,
        policy === "C2" ? c2Reason : null,
      );
      setPreview(p);
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : "Erro no preview");
    } finally {
      setPreviewBusy(false);
    }
  }

  async function onCommit() {
    if (!canCommit(user)) return;
    if ((policy === "A" || policy === "B") && !orderId.trim()) {
      setCommitError("Informe o Order ID — matching automático foi desativado.");
      return;
    }
    setCommitBusy(true);
    setCommitError(null);
    try {
      const orderIdNum = orderId.trim() ? Number(orderId.trim()) : null;
      const result = await commitFatturaDocument(documentId, {
        operation_key: opKey,
        policy,
        order_id: orderIdNum,
        c2_confirm: policy === "C2",
        c2_reason: policy === "C2" ? c2Reason : null,
      });
      setAttempt(result);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : "Erro no commit");
    } finally {
      setCommitBusy(false);
    }
  }

  const invoiceOp = attempt?.operations?.find((o) => o.entity_type === "invoice" && o.entity_id);
  const invoiceId = invoiceOp?.entity_id ?? null;
  const orderOp = attempt?.operations?.find((o) => o.entity_type === "order" && o.entity_id);
  const ordIdFromAttempt = orderOp?.entity_id ?? null;

  return (
    <SectionCard title="Fattura — Policy A/B/C1/C2" data-testid="fattura-commit-panel">
      {/* Policy selector */}
      <fieldset style={{ border: "none", padding: 0, margin: 0, marginBottom: "0.75rem" }}>
        <legend style={{ fontWeight: 600, marginBottom: "0.4rem" }}>Policy de matching</legend>
        {POLICIES.map((p) => (
          <label
            key={p.value}
            style={{ display: "block", marginBottom: "0.35rem", cursor: "pointer" }}
            data-testid={`policy-option-${p.value}`}
          >
            <input
              type="radio"
              name="fattura-policy"
              value={p.value}
              checked={policy === p.value}
              onChange={() => {
                setPolicy(p.value);
                setPreview(null);
              }}
              style={{ marginRight: "0.4rem" }}
            />
            <strong>{p.label}</strong>{" "}
            <span className="muted" style={{ fontSize: "0.85em" }}>
              {p.description}
            </span>
          </label>
        ))}
      </fieldset>

      {/* Order ID field for A/B */}
      {(policy === "A" || policy === "B") && (
        <label style={{ display: "block", marginBottom: "0.5rem" }}>
          Order ID (obrigatório)
          <input
            type="number"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            placeholder="Ex: 42"
            required
            style={{ marginLeft: "0.5rem", width: "100px" }}
            data-testid="fattura-order-id-input"
          />
        </label>
      )}

      {/* C2 reason */}
      {policy === "C2" && (
        <label style={{ display: "block", marginBottom: "0.5rem" }}>
          <span style={{ color: "#b45309", fontWeight: 600 }}>
            Motivo da exceção C2 (obrigatório):
          </span>
          <textarea
            value={c2Reason}
            onChange={(e) => setC2Reason(e.target.value)}
            rows={2}
            style={{ display: "block", width: "100%", marginTop: "0.25rem" }}
            placeholder="Descreva o motivo da confirmação retroativa…"
            data-testid="fattura-c2-reason-input"
          />
        </label>
      )}

      {/* Preview */}
      <Button
        type="button"
        variant="ghost"
        disabled={previewBusy}
        onClick={() => void onPreview()}
        data-testid="fattura-preview-btn"
      >
        {previewBusy ? "Calculando…" : "Preview"}
      </Button>

      {previewError ? (
        <p className="error-text" role="alert">
          {previewError}
        </p>
      ) : null}

      {preview ? (
        <div
          className="ingestion-preview"
          data-testid="fattura-preview-result"
          style={{ marginTop: "0.5rem" }}
        >
          <p className="muted">
            Digest: <code data-testid="fattura-preview-digest">{preview.fingerprint}</code>
          </p>
          <p>
            Policy match: <strong>{preview.policy_match.policy}</strong>
            {preview.policy_match.order_id ? ` · Order #${preview.policy_match.order_id}` : ""}
            {preview.policy_match.order_status ? ` (${preview.policy_match.order_status})` : ""}
            {" · "}
            Invoice: {preview.policy_match.invoice_will_be_created ? "será criada" : "NÃO criada"}
          </p>
          {preview.policy_match.warning ? (
            <p style={{ color: "#b45309" }}>
              Aviso: {preview.policy_match.warning}
            </p>
          ) : null}
          <p>
            Pode commit: {preview.can_commit ? "sim" : "não"} · ops:{" "}
            {preview.operations.length}
            {preview.open_error_count ? ` · erros abertos: ${preview.open_error_count}` : ""}
          </p>
          <ul data-testid="fattura-preview-ops">
            {preview.operations.map((op, i) => {
              const lines = Array.isArray(op.params?.lines) ? op.params.lines : null;
              const candidates = Array.isArray(op.params?.candidates)
                ? op.params.candidates
                : null;
              const blocked = op.op_key.startsWith("blocked_");
              const warn = op.op_key.startsWith("warn_");
              return (
                <li
                  key={i}
                  data-testid={`fattura-preview-op-${op.op_key}`}
                  style={
                    blocked
                      ? { color: "#b91c1c" }
                      : warn
                        ? { color: "#b45309" }
                        : undefined
                  }
                >
                  <code>{op.op_key}</code>: {op.description}
                  {candidates && candidates.length > 0 ? (
                    <ul>
                      {candidates.map((c: Record<string, unknown>, j: number) => (
                        <li key={j}>
                          item #{String(c.order_item_id)} · preço {String(c.unit_price ?? "—")} ·
                          saldo {String(c.remaining ?? "—")}
                          {op.params?.order_item_id === c.order_item_id ? " · escolhido" : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  {lines &&
                  lines.length > 0 &&
                  typeof lines[0] === "object" &&
                  lines[0] !== null &&
                  "sku" in (lines[0] as object) ? (
                    <ul data-testid="fattura-preview-line-plan">
                      {(lines as Array<Record<string, unknown>>).map((ln, j) => (
                        <li key={j}>
                          SKU {String(ln.sku)} · qty PDF {String(ln.pdf_qty)} @{" "}
                          {String(ln.pdf_unit_price ?? "—")} → item #{String(ln.order_item_id)}{" "}
                          (pedido {String(ln.order_unit_price ?? "—")}, saldo{" "}
                          {String(ln.remaining_before ?? "—")})
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {/* Commit form */}
      {canCommit(user) ? (
        <div className="ingestion-commit-actions" style={{ marginTop: "0.75rem" }}>
          <label>
            operation_key{" "}
            <input
              value={opKey}
              onChange={(e) => setOpKey(e.target.value)}
              data-testid="fattura-commit-op-key"
              style={{ marginLeft: "0.4rem", width: "260px" }}
            />
          </label>
          <Button
            type="button"
            disabled={commitBusy || (preview != null && !preview.can_commit)}
            onClick={() => void onCommit()}
            data-testid="fattura-commit-submit"
            style={{ marginTop: "0.5rem" }}
          >
            {commitBusy ? "Executando…" : "Commit Fattura"}
          </Button>
          {commitError ? (
            <p className="error-text" role="alert">
              {commitError}
            </p>
          ) : null}
        </div>
      ) : (
        <p className="muted" style={{ marginTop: "0.5rem" }}>
          Requer ingestion:commit, orders:write e billing:write
        </p>
      )}

      {/* Result */}
      {attempt ? (
        <div data-testid="fattura-commit-result" style={{ marginTop: "0.75rem" }}>
          <p>
            Status: <strong>{attempt.status}</strong> · attempt #{attempt.id}
          </p>
          <ul>
            {(attempt.operations ?? []).map((op) => (
              <li key={op.id}>
                <code>{op.op_key}</code>: {op.status}
                {op.entity_type === "invoice" && op.entity_id ? (
                  <>
                    {" → "}
                    <Link
                      to={`/invoices/${op.entity_id}`}
                      data-testid="fattura-invoice-deeplink"
                    >
                      Invoice #{op.entity_id}
                    </Link>
                  </>
                ) : null}
                {op.entity_type === "order" && op.entity_id ? (
                  <>
                    {" → "}
                    <Link
                      to={`/orders/${op.entity_id}`}
                      data-testid="fattura-order-deeplink"
                    >
                      Order #{op.entity_id}
                    </Link>
                  </>
                ) : null}
                {op.error_message ? (
                  <span className="error-text"> ({op.error_message})</span>
                ) : null}
              </li>
            ))}
          </ul>
          {invoiceId ? (
            <Link
              className="ui-button"
              to={`/invoices/${invoiceId}`}
              data-testid="fattura-invoice-cta"
            >
              Abrir Invoice DRAFT
            </Link>
          ) : ordIdFromAttempt ? (
            <Link
              className="ui-button"
              to={`/orders/${ordIdFromAttempt}`}
              data-testid="fattura-order-cta"
            >
              Abrir Order (aguarda confirm)
            </Link>
          ) : null}
        </div>
      ) : null}
    </SectionCard>
  );
}
