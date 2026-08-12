import { useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { Button, EmptyState, SectionCard, TextInput } from "../../ui";
import {
  correctIngestionField,
  patchIngestionIssue,
  patchIngestionRow,
  searchProducts,
  searchSuppliers,
  type DocumentDetail,
  type FieldOut,
  type IssueOut,
  type RowOut,
} from "./ingestionApi";
import {
  cellText,
  isCommitmentLine,
  isProductResolved,
  looksLikeEan,
  parseRowCells,
} from "./ordineShellHelpers";

type Props = {
  user: User;
  doc: DocumentDetail;
  onUpdated: () => void;
  /** Ordine PDF: só supplier (+ EAN não resolvido); sem CTA criar produto em compromisso. */
  ordineCommitmentMode?: boolean;
  /** Sem SectionCard — pai já envolve (ex. com aviso math C2). */
  embedded?: boolean;
};

const SUPPLIER_CODES = new Set(["AMBIGUOUS_SUPPLIER", "UNMATCHED_SUPPLIER", "SUPPLIER_NOT_FOUND"]);
const PRODUCT_CODES = new Set(["AMBIGUOUS_SKU", "UNMATCHED_SKU", "SUGGESTED_SKU_MATCH"]);

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

function canCatalogWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

function fieldByKey(doc: DocumentDetail, key: string): FieldOut | undefined {
  return (doc.fields ?? []).find((f) => f.field_key === key);
}

function fieldText(doc: DocumentDetail, key: string): string {
  const f = fieldByKey(doc, key);
  return (f?.effective_value ?? f?.raw_value ?? "").trim();
}

function resolveMode(issue: IssueOut): "product" | "supplier" {
  const code = issue.code.toUpperCase();
  if (code.includes("SUPPLIER")) return "supplier";
  return "product";
}

function rowForIssue(doc: DocumentDetail, issue: IssueOut): RowOut | undefined {
  if (issue.target_type !== "ROW" || issue.target_id == null) return undefined;
  return (doc.rows ?? []).find((r) => r.row_index === issue.target_id || r.id === issue.target_id);
}

function humanSupplierLabel(doc: DocumentDetail, issue: IssueOut): string {
  const name = fieldText(doc, "supplier_name") || "Fornecedor";
  const pi = fieldText(doc, "supplier_pi_cf");
  if (issue.code === "AMBIGUOUS_SUPPLIER") {
    return `${name}${pi ? ` (PI ${pi})` : ""} — mais de um cadastro possível; escolha um`;
  }
  return `${name}${pi ? ` (PI ${pi})` : ""} — ainda não cadastrado`;
}

function humanProductLabel(doc: DocumentDetail, issue: IssueOut): string {
  const row = rowForIssue(doc, issue);
  const cells = parseRowCells(row?.cells_json);
  const desc = cellText(cells, "description") || "Item";
  const qty = cellText(cells, "quantity");
  const sku = cellText(cells, "sku");
  const qtyPart = qty ? ` — ${qty} PZ` : "";
  const codePart = sku ? ` · código ${sku}` : "";
  if (issue.code === "SUGGESTED_SKU_MATCH") {
    return `${desc}${qtyPart}${codePart} — confirme o vínculo sugerido`;
  }
  return `${desc}${qtyPart}${codePart} — vincule a um produto do catálogo`;
}

export function MatchingPanel({
  user,
  doc,
  onUpdated,
  ordineCommitmentMode = false,
  embedded = false,
}: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ id: number; label: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeIssueId, setActiveIssueId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createCode, setCreateCode] = useState("");

  const matchingIssues = useMemo(() => {
    const open = (doc.issues ?? []).filter((i) => i.status === "OPEN");
    if (!ordineCommitmentMode) {
      return open.filter(
        (i) =>
          SUPPLIER_CODES.has(i.code) ||
          PRODUCT_CODES.has(i.code) ||
          /ambiguous|unmatched|not_found|suggested/i.test(i.code),
      );
    }
    // Ordine: só fornecedor; produto só se EAN não resolvido (exceção à regra compromisso)
    return open.filter((i) => {
      if (SUPPLIER_CODES.has(i.code) || /supplier/i.test(i.code)) return true;
      if (!PRODUCT_CODES.has(i.code) && !/sku|product/i.test(i.code)) return false;
      const row = rowForIssue(doc, i);
      const cells = parseRowCells(row?.cells_json);
      if (isCommitmentLine(cells)) return false;
      if (isProductResolved(cells)) return false;
      return looksLikeEan(cellText(cells, "sku"));
    });
  }, [doc, ordineCommitmentMode]);

  const activeIssue = matchingIssues.find((i) => i.id === activeIssueId) ?? matchingIssues[0] ?? null;
  const mode: "product" | "supplier" = activeIssue ? resolveMode(activeIssue) : "supplier";
  const targetRow = activeIssue ? rowForIssue(doc, activeIssue) : undefined;
  const cells = parseRowCells(targetRow?.cells_json);
  const allowCreateProduct = mode === "product" && !ordineCommitmentMode;
  const allowCreateSupplier = mode === "supplier";

  useEffect(() => {
    if (matchingIssues.length && (activeIssueId == null || !matchingIssues.some((i) => i.id === activeIssueId))) {
      setActiveIssueId(matchingIssues[0].id);
    }
    if (!matchingIssues.length) setActiveIssueId(null);
  }, [matchingIssues, activeIssueId]);

  useEffect(() => {
    setCreateOpen(false);
    if (!activeIssue) return;
    if (mode === "supplier") {
      setCreateName(fieldText(doc, "supplier_name"));
      setCreateCode(fieldText(doc, "supplier_pi_cf"));
    }
  }, [activeIssue?.id, mode, doc]);

  useEffect(() => {
    if (!query.trim() || query.trim().length < 2) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(() => {
      void (async () => {
        try {
          const rows =
            mode === "supplier"
              ? (await searchSuppliers(query.trim())).map((r) => ({
                  id: r.id,
                  label: `${r.name}${r.code ? ` (${r.code})` : ""}`,
                }))
              : (await searchProducts(query.trim())).map((r) => ({
                  id: r.id,
                  label: `${r.sku} — ${r.description}`,
                }));
          if (!cancelled) setResults(rows);
        } catch {
          if (!cancelled) setResults([]);
        }
      })();
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [query, mode]);

  async function linkCatalog(id: number) {
    if (!canWrite(user) || !activeIssue) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === "supplier") {
        const field = fieldByKey(doc, "supplier_id_catalog");
        if (!field) throw new Error("Campo de fornecedor ausente — reexecute a importação");
        await correctIngestionField(field.id, {
          corrected_value: String(id),
          expected_version: field.version,
          reason: "vínculo manual fornecedor",
        });
      } else if (targetRow) {
        const nextCells = {
          ...cells,
          product_id_catalog: { raw: String(id), normalized: String(id) },
        };
        await patchIngestionRow(targetRow.id, {
          cells_json: JSON.stringify(nextCells),
          expected_version: targetRow.version,
        });
      } else {
        throw new Error("Linha alvo ausente");
      }
      await patchIngestionIssue(activeIssue.id, { status: "RESOLVED" });
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao vincular");
    } finally {
      setBusy(false);
    }
  }

  async function confirmCreateSupplier() {
    if (!canWrite(user) || !canCatalogWrite(user) || !activeIssue || mode !== "supplier") return;
    setBusy(true);
    setError(null);
    try {
      const field = fieldByKey(doc, "pending_create_supplier");
      if (!field) throw new Error("Não foi possível preparar a criação — reexecute a importação");
      const payload = JSON.stringify({
        name: createName.trim(),
        code: createCode.trim() || null,
        country_code: "IT",
      });
      await correctIngestionField(field.id, {
        corrected_value: payload,
        expected_version: field.version,
        reason: "intent: criar fornecedor a partir do documento",
      });
      await patchIngestionIssue(activeIssue.id, { status: "RESOLVED" });
      setCreateOpen(false);
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao confirmar criação");
    } finally {
      setBusy(false);
    }
  }

  if (!matchingIssues.length) return null;

  const body = (
    <>
      {error ? <p className="error-text">{error}</p> : null}

      <div className="ingestion-matching-issues">
        {matchingIssues.map((issue) => (
          <button
            key={issue.id}
            type="button"
            className={activeIssue?.id === issue.id ? "is-active" : undefined}
            data-testid={`matching-issue-${issue.id}`}
            onClick={() => setActiveIssueId(issue.id)}
          >
            {resolveMode(issue) === "supplier" ? humanSupplierLabel(doc, issue) : humanProductLabel(doc, issue)}
          </button>
        ))}
      </div>

      {activeIssue ? (
        <div className="ingestion-matching-detail" data-testid="matching-detail">
          <div className="ingestion-matching-search">
            <label className="form-label">
              {mode === "supplier" ? "Buscar fornecedor" : "Buscar produto"}
              <TextInput
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                data-testid="matching-search-input"
                placeholder={mode === "supplier" ? "Nome ou PI/CF…" : "SKU ou descrição…"}
              />
            </label>
            {results.length > 0 ? (
              <ul className="ingestion-matching-results" data-testid="matching-search-results">
                {results.map((r) => (
                  <li key={r.id}>
                    <span>{r.label}</span>
                    <Button
                      type="button"
                      disabled={busy}
                      data-testid={`matching-link-${r.id}`}
                      onClick={() => void linkCatalog(r.id)}
                    >
                      Vincular
                    </Button>
                  </li>
                ))}
              </ul>
            ) : query.trim().length >= 2 ? (
              <p className="muted">Nenhum resultado</p>
            ) : null}
          </div>

          <div className="ingestion-matching-actions">
            {allowCreateSupplier && canCatalogWrite(user) ? (
              <Button
                type="button"
                variant="ghost"
                data-testid="matching-create-open"
                disabled={busy || !canWrite(user)}
                onClick={() => setCreateOpen(true)}
              >
                Cadastrar fornecedor
              </Button>
            ) : null}
            {allowCreateSupplier && !canCatalogWrite(user) ? (
              <p className="muted" data-testid="matching-create-disabled-reason">
                Cadastrar fornecedor está desabilitado: sua conta não pode cadastrar fornecedores.
                Peça a um administrador ou vincule um fornecedor já existente na busca acima.
              </p>
            ) : null}
            {mode === "product" && !allowCreateProduct ? (
              <p className="muted">Linha de compromisso — vincule só se for um EAN de produto real.</p>
            ) : null}
          </div>

          {createOpen && allowCreateSupplier && canCatalogWrite(user) ? (
            <div className="ingestion-matching-create" data-testid="matching-create-modal">
              <p className="muted">
                Confirme os dados do documento. O fornecedor só será cadastrado ao criar o pedido —
                nada é gravado agora.
              </p>
              <label className="form-label">
                Nome
                <TextInput
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  data-testid="create-supplier-name"
                />
              </label>
              <label className="form-label">
                PI / CF
                <TextInput
                  value={createCode}
                  onChange={(e) => setCreateCode(e.target.value)}
                  data-testid="create-supplier-code"
                />
              </label>
              <Button
                type="button"
                disabled={busy || !createName.trim() || !canWrite(user)}
                data-testid="matching-create-confirm"
                onClick={() => void confirmCreateSupplier()}
              >
                Confirmar cadastro no pedido
              </Button>
              <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
                Cancelar
              </Button>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState message="Selecione uma pendência" />
      )}
    </>
  );

  if (embedded) {
    return (
      <div className="ingestion-matching-embedded" data-testid="ingestion-matching-panel">
        {body}
      </div>
    );
  }

  return (
    <SectionCard title="Antes de criar o pedido" data-testid="ingestion-matching-panel">
      {body}
    </SectionCard>
  );
}
