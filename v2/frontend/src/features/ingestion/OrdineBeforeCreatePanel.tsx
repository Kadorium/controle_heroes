import { useMemo } from "react";
import { Notice, SectionCard } from "../../ui";
import type { User } from "../auth/types";
import type { DocumentDetail, IssueOut } from "./ingestionApi";
import { MatchingPanel } from "./MatchingPanel";
import { isCommitmentLine, looksLikeEan, parseRowCells, cellText, isProductResolved } from "./ordineShellHelpers";

type Props = {
  user: User;
  doc: DocumentDetail;
  onUpdated: () => void;
};

/**
 * Após RUX-2R-a: L3/L4/legacy não são mais emitidos.
 * Avisos math restantes (L2/L5 reais) ficam abaixo do fornecedor, tom neutro.
 * INFO (ex. MATH_EXPORT_N31) não entra aqui.
 * RUX-3F-POST-3: MATH_LINE_EDIT_DIVERGENCE (WARNING) aparece com mensagem literal.
 */
function isOperatorMathNotice(issue: IssueOut): boolean {
  if (issue.status !== "OPEN") return false;
  if (issue.severity === "INFO") return false;
  return /^MATH_/.test(issue.code);
}

function hasOrdineMatchingPendencies(doc: DocumentDetail): boolean {
  for (const i of doc.issues ?? []) {
    if (i.status !== "OPEN") continue;
    if (/SUPPLIER/i.test(i.code)) return true;
    if (!/SKU|PRODUCT/i.test(i.code) && !["AMBIGUOUS_SKU", "UNMATCHED_SKU", "SUGGESTED_SKU_MATCH"].includes(i.code)) {
      continue;
    }
    const row =
      i.target_type === "ROW" && i.target_id != null
        ? (doc.rows ?? []).find((r) => r.row_index === i.target_id || r.id === i.target_id)
        : undefined;
    const cells = parseRowCells(row?.cells_json);
    if (isCommitmentLine(cells)) continue;
    if (isProductResolved(cells)) continue;
    if (looksLikeEan(cellText(cells, "sku"))) return true;
  }
  return false;
}

/**
 * Bloco "Antes de criar o pedido": fornecedor primeiro; math (se houver) abaixo, neutro.
 */
export function OrdineBeforeCreatePanel({ user, doc, onUpdated }: Props) {
  const mathNotices = useMemo(
    () => (doc.issues ?? []).filter(isOperatorMathNotice),
    [doc.issues],
  );
  const editDivergences = useMemo(
    () => mathNotices.filter((i) => i.code === "MATH_LINE_EDIT_DIVERGENCE"),
    [mathNotices],
  );
  const otherMath = useMemo(
    () => mathNotices.filter((i) => i.code !== "MATH_LINE_EDIT_DIVERGENCE"),
    [mathNotices],
  );
  const hasMatching = useMemo(() => hasOrdineMatchingPendencies(doc), [doc]);

  if (mathNotices.length === 0 && !hasMatching) return null;

  return (
    <SectionCard title="Antes de criar o pedido" data-testid="ordine-before-create-panel">
      <MatchingPanel user={user} doc={doc} onUpdated={onUpdated} ordineCommitmentMode embedded />
      {editDivergences.map((issue) => (
        <Notice
          key={issue.id}
          tone="warning"
          data-testid="ordine-math-line-edit-divergence"
        >
          {issue.message}
        </Notice>
      ))}
      {otherMath.length > 0 ? (
        <details className="ordine-math-notice" data-testid="ordine-math-known-false">
          <summary className="muted">Aviso sobre totais do PDF</summary>
          <ul className="muted" style={{ marginTop: "0.5rem" }}>
            {otherMath.map((issue) => (
              <li key={issue.id}>{issue.message}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </SectionCard>
  );
}
