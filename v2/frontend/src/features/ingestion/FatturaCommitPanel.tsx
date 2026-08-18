/**
 * FatturaCommitPanel — J3-I4 + A0
 * Policy A/B/C1/C2 + candidatos de Order + ambiguidade de linha + preview + commit.
 * Depois do DRAFT, o Billing existente (Invoice Detail) continua a jornada.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  commitFatturaDocument,
  fetchFatturaPreview,
  type CommitAttemptOut,
  type FatturaLineChoiceIn,
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

function lineChoicesPayload(choices: Record<number, number>): FatturaLineChoiceIn[] {
  return Object.entries(choices).map(([row, item]) => ({
    row_index: Number(row),
    order_item_id: item,
  }));
}

export function FatturaCommitPanel({ documentId, user }: Props) {
  const [policy, setPolicy] = useState<FatturaPolicy>("A");
  const [orderId, setOrderId] = useState<string>("");
  const [pickedOrderId, setPickedOrderId] = useState<string>("");
  const [lineChoices, setLineChoices] = useState<Record<number, number>>({});
  const [c2Reason, setC2Reason] = useState<string>("");
  const [opKey, setOpKey] = useState(() => `fattura-commit-${documentId}-${Date.now()}`);

  const [preview, setPreview] = useState<FatturaPreviewOut | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);

  const [attempt, setAttempt] = useState<CommitAttemptOut | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitBusy, setCommitBusy] = useState(false);

  const runPreview = useCallback(
    async (explicitOrderId: string, choices: Record<number, number>) => {
      setPreviewBusy(true);
      setPreviewError(null);
      try {
        const orderIdNum = explicitOrderId.trim() ? Number(explicitOrderId.trim()) : null;
        const choiceList = lineChoicesPayload(choices);
        const p = await fetchFatturaPreview(
          documentId,
          policy,
          orderIdNum,
          policy === "C2" ? true : false,
          policy === "C2" ? c2Reason : null,
          choiceList,
        );
        setPreview(p);
      } catch (e) {
        setPreviewError(e instanceof Error ? e.message : "Erro no preview");
        setPreview(null);
      } finally {
        setPreviewBusy(false);
      }
    },
    [c2Reason, documentId, policy],
  );

  useEffect(() => {
    if (policy !== "A") return;
    void runPreview("", {});
  }, [policy, documentId, runPreview]);

  async function onPreview() {
    if ((policy === "A" || policy === "B") && !orderId.trim() && policy === "B") {
      setPreviewError("Informe o Order ID — matching automático foi desativado.");
      return;
    }
    await runPreview(orderId, lineChoices);
  }

  function confirmPickedOrder() {
    if (!pickedOrderId.trim()) return;
    setOrderId(pickedOrderId);
    setLineChoices({});
    void runPreview(pickedOrderId, {});
  }

  async function onCommit() {
    if (!canCommit(user)) return;
    if ((policy === "A" || policy === "B") && !orderId.trim()) {
      setCommitError("Confirme o pedido explicitamente — o sistema não escolhe em silêncio.");
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
        line_choices: lineChoicesPayload(lineChoices),
      });
      setAttempt(result);
      setOpKey(`fattura-commit-${documentId}-${Date.now()}`);
      await runPreview(orderId, lineChoices);
    } catch (e) {
      setCommitError(e instanceof Error ? e.message : "Erro no commit");
    } finally {
      setCommitBusy(false);
    }
  }

  const alreadyCommitted = Boolean(preview?.already_committed);
  const invoiceOp = attempt?.operations?.find((o) => o.entity_type === "invoice" && o.entity_id);
  const invoiceId = preview?.last_succeeded_invoice_id
    ? String(preview.last_succeeded_invoice_id)
    : invoiceOp?.entity_id ?? null;
  const orderOp = attempt?.operations?.find((o) => o.entity_type === "order" && o.entity_id);
  const ordIdFromAttempt = orderOp?.entity_id ?? null;

  const candidates = preview?.order_candidates ?? [];
  const lineMatches = preview?.line_matches ?? [];
  const ambiguousLines = lineMatches.filter((m) => m.status === "ambiguous");
  const unmatchedLines = lineMatches.filter((m) => m.status === "unmatched");
  const matchedLines = lineMatches.filter((m) => m.status === "matched");

  const createOps = useMemo(
    () =>
      (preview?.operations ?? []).filter((op) =>
        ["create_invoice", "set_terms", "link_document", "map_invoice_items"].includes(op.op_key),
      ),
    [preview],
  );

  return (
    <SectionCard title="Fattura — revisão e commit" data-testid="fattura-commit-panel">
      {alreadyCommitted ? (
        <Notice tone="info" data-testid="fattura-processed-banner" title="Fattura processada">
          <p>
            Invoice{" "}
            {invoiceId ? (
              <Link to={`/invoices/${invoiceId}`} data-testid="fattura-invoice-link">
                #{invoiceId}
              </Link>
            ) : (
              "já gerada"
            )}{" "}
            a partir deste documento. Não reexecuta o commit.
          </p>
          <p className="muted">
            A extração permanece editável. Isso não significa que a fatura está pendente de
            processamento.
          </p>
        </Notice>
      ) : null}

      {!alreadyCommitted ? (
      <>
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
                setOrderId("");
                setPickedOrderId("");
                setLineChoices({});
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

      {policy === "A" ? (
        <div data-testid="fattura-order-candidates" style={{ marginBottom: "0.75rem" }}>
          <h3 className="ingestion-subtitle">Pedido</h3>
          {previewBusy && !preview ? <p className="muted">Buscando candidatos…</p> : null}
          {preview?.order_candidates_reason ? (
            <p role="alert" style={{ color: "#b91c1c" }} data-testid="fattura-order-none">
              {preview.order_candidates_reason}
            </p>
          ) : null}
          {candidates.length === 1 ? (
            <p data-testid="fattura-order-suggested">
              Sugestão forte: pedido{" "}
              <strong>
                #{candidates[0].order_id} {candidates[0].order_code}
              </strong>{" "}
              ({candidates[0].status}). Confirme explicitamente — não há commit automático.
            </p>
          ) : null}
          {candidates.length > 1 ? (
            <p data-testid="fattura-order-multiple">
              {candidates.length} pedidos possíveis. O sistema não escolhe em silêncio.
            </p>
          ) : null}
          {candidates.length > 0 ? (
            <ul data-testid="fattura-order-candidate-list" style={{ listStyle: "none", padding: 0 }}>
              {candidates.map((c) => (
                <li key={c.order_id} style={{ marginBottom: "0.4rem" }}>
                  <label style={{ cursor: "pointer" }} data-testid={`fattura-order-candidate-${c.order_id}`}>
                    <input
                      type="radio"
                      name="fattura-order-pick"
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
            data-testid="fattura-order-confirm-btn"
          >
            Confirmar este pedido
          </Button>
        </div>
      ) : null}

      {(policy === "A" || policy === "B") && (
        <label style={{ display: "block", marginBottom: "0.5rem" }}>
          Pedido confirmado (order_id)
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

      {lineMatches.length > 0 ? (
        <div data-testid="fattura-line-review" style={{ marginBottom: "0.75rem" }}>
          <h3 className="ingestion-subtitle">Linhas</h3>
          <p className="muted">
            Casadas: {matchedLines.length} · Ambíguas: {ambiguousLines.length} · Sem match:{" "}
            {unmatchedLines.length}
          </p>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {lineMatches.map((m) => (
              <li
                key={m.row_index}
                data-testid={`fattura-line-match-${m.row_index}`}
                style={{
                  marginBottom: "0.5rem",
                  color:
                    m.status === "ambiguous" || m.status === "unmatched" || m.status === "qty_exceeded"
                      ? "#b91c1c"
                      : undefined,
                }}
              >
                Linha {m.row_index} SKU {m.sku} · qty {m.pdf_qty} @ {m.pdf_unit_price ?? "—"} ·{" "}
                {m.status === "matched"
                  ? `item #${m.order_item_id}`
                  : m.status === "ambiguous"
                    ? "ambígua — escolha a linha do pedido"
                    : m.status}
                {m.price_mismatch ? " · preço da Fattura ≠ pedido (segue o documento)" : ""}
                {m.status === "ambiguous" && m.candidates.length > 0 ? (
                  <ul style={{ marginTop: "0.25rem" }}>
                    {m.candidates.map((c) => (
                      <li key={c.order_item_id}>
                        <label data-testid={`fattura-line-choice-${m.row_index}-${c.order_item_id}`}>
                          <input
                            type="radio"
                            name={`fattura-line-${m.row_index}`}
                            checked={lineChoices[m.row_index] === c.order_item_id}
                            onChange={() => {
                              const next = { ...lineChoices, [m.row_index]: c.order_item_id };
                              setLineChoices(next);
                              if (orderId.trim()) void runPreview(orderId, next);
                            }}
                            style={{ marginRight: "0.35rem" }}
                          />
                          item #{c.order_item_id} · pos {c.position} · preço {c.unit_price ?? "—"} ·
                          saldo {c.remaining}
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
          {createOps.length > 0 ? (
            <p data-testid="fattura-will-create">
              Ao confirmar: {createOps.map((o) => o.op_key).join(", ")}.
            </p>
          ) : (
            <p className="muted">Nada a criar até o pedido (e linhas ambíguas) estarem resolvidos.</p>
          )}
          <p>
            Pode commit: {preview.can_commit ? "sim" : "não"} · ops:{" "}
            {preview.operations.length}
            {preview.open_error_count ? ` · erros abertos: ${preview.open_error_count}` : ""}
          </p>
          <ul data-testid="fattura-preview-ops">
            {preview.operations.map((op, i) => {
              const lines = Array.isArray(op.params?.lines) ? op.params.lines : null;
              const opCandidates = Array.isArray(op.params?.candidates)
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
                  {opCandidates && opCandidates.length > 0 ? (
                    <ul>
                      {(opCandidates as Array<Record<string, unknown>>).map((c, j) => (
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

      {canCommit(user) ? (
        <div className="ingestion-commit-actions" style={{ marginTop: "0.75rem" }}>
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
      </>
      ) : null}

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
