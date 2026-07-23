import { useEffect, useMemo, useState } from "react";
import {
  importsApi,
  productsApi,
  type HeroesSkuTriageGroup,
  type Product,
} from "../../api";
import { Badge, Button, ProductCombobox } from "../../components";
import { productCategoryLabel } from "../../i18n/glossario";

const SUGGEST_MIN_SCORE = 30;

interface Props {
  groups: HeroesSkuTriageGroup[];
  openCount: number;
  totalResolved: number;
  onResolved: () => void | Promise<void>;
  disabled?: boolean;
}

type PickState = { text: string; productId: number | null };

function confidenceLabel(score: number | null | undefined): string | null {
  if (score == null || score < SUGGEST_MIN_SCORE) return null;
  return `${Math.round(score)}%`;
}

function suggestionBadgeLabel(badge: HeroesSkuTriageGroup["suggestion_badge"]): string | null {
  if (badge === "suggestion") return "Sugestão";
  if (badge === "verify") return "Verificar";
  return null;
}

export function HeroesSkuTriagePanel({
  groups,
  openCount,
  totalResolved,
  onResolved,
  disabled = false,
}: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [pick, setPick] = useState<Record<number, PickState>>({});
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [bulkResolving, setBulkResolving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    productsApi.list({ for_combobox: true }).then(setProducts).catch(() => undefined);
  }, []);

  useEffect(() => {
    setPick((prev) => {
      const next = { ...prev };
      for (const group of groups) {
        if (group.status === "confirmed") continue;
        const stagingId = group.staging_id;
        if (next[stagingId]?.productId) continue;
        const suggestedId = group.suggested_product_id;
        if (typeof suggestedId !== "number") continue;
        const prod =
          products.find((p) => p.id === suggestedId) ??
          (group.suggested_product_sku
            ? ({
                id: suggestedId,
                sku_code: group.suggested_product_sku,
                description: group.suggested_product_description ?? group.product_name_raw ?? "",
              } as Product)
            : undefined);
        if (!prod) continue;
        next[stagingId] = {
          text: prod.sku_code,
          productId: suggestedId,
        };
      }
      return next;
    });
  }, [groups, products]);

  const totalGroups = groups.length || totalResolved + openCount;

  const pendingGroups = useMemo(
    () => groups.filter((g) => g.status !== "confirmed"),
    [groups],
  );

  const pendingCanonicalKeys = useMemo(
    () => new Set(pendingGroups.map((g) => g.canonical_key).filter(Boolean) as string[]),
    [pendingGroups],
  );

  const bulkConfirmable = useMemo(
    () =>
      pendingGroups.filter(
        (g) =>
          g.suggestion_badge === "suggestion" &&
          typeof pick[g.staging_id]?.productId === "number",
      ),
    [pendingGroups, pick],
  );

  const canBulkConfirm =
    bulkConfirmable.length > 0 &&
    bulkConfirmable.length ===
      pendingGroups.filter((g) => g.suggestion_badge === "suggestion").length;

  if (groups.length === 0) {
    return null;
  }

  async function confirmResolve(stagingId: number) {
    const sel = pick[stagingId];
    if (!sel?.productId) return;
    setResolvingId(stagingId);
    setError("");
    try {
      await importsApi.resolveStagingSku(stagingId, sel.productId, { saveAliases: true });
      await onResolved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao vincular SKU");
    } finally {
      setResolvingId(null);
    }
  }

  async function confirmAllSuggestions() {
    if (!canBulkConfirm) return;
    setBulkResolving(true);
    setError("");
    try {
      for (const group of bulkConfirmable) {
        const sel = pick[group.staging_id];
        if (!sel?.productId) continue;
        await importsApi.resolveStagingSku(group.staging_id, sel.productId, { saveAliases: true });
      }
      await onResolved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao confirmar SKUs");
    } finally {
      setBulkResolving(false);
    }
  }

  async function createDraft(stagingId: number) {
    setResolvingId(stagingId);
    setError("");
    try {
      await importsApi.createDraftFromStaging(stagingId);
      await onResolved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar rascunho");
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <section className="heroes-sku-triage">
      <div className="heroes-sku-triage__head">
        <h4>SKUs para confirmar</h4>
        <span className="meta">
          {totalResolved} de {totalGroups} confirmado(s)
          {openCount > 0 ? ` · ${openCount} pendente(s)` : ""}
        </span>
      </div>
      {error && <p className="error">{error}</p>}
      <p className="meta heroes-sku-triage__hint">
        Confirme cada vínculo antes de importar. Sugestões verdes costumam ser corretas (1 clique);
        amarelas pedem verificação. Busque outro produto ou crie rascunho quando necessário.
      </p>
      {canBulkConfirm && (
        <div className="heroes-sku-triage__bulk">
          <Button
            variant="primary"
            className="ui-btn--sm"
            disabled={disabled || bulkResolving}
            onClick={confirmAllSuggestions}
          >
            {bulkResolving ? "Confirmando…" : `Confirmar todos (${bulkConfirmable.length})`}
          </Button>
        </div>
      )}
      <ul className="heroes-sku-triage__list">
        {groups.map((group) => {
          const stagingId = group.staging_id;
          const isConfirmed = group.status === "confirmed";
          const conf = confidenceLabel(group.match_confidence);
          const badgeLabel = suggestionBadgeLabel(group.suggestion_badge);
          const badgeTone =
            group.suggestion_badge === "suggestion"
              ? "success"
              : group.suggestion_badge === "verify"
                ? "warning"
                : "neutral";
          const displayName = group.product_name_raw ?? "—";
          const aliases =
            (group.aliases?.length ?? 0) > 1
              ? group.aliases!.slice(0, 4).join(", ")
              : null;
          return (
            <li
              key={stagingId}
              className={`heroes-sku-triage__row${isConfirmed ? " heroes-sku-triage__row--confirmed" : ""}`}
            >
              <div className="heroes-sku-triage__row-main">
                <strong>{displayName}</strong>
                {group.suggested_category && (
                  <span className="meta">{productCategoryLabel(group.suggested_category)}</span>
                )}
                {isConfirmed ? (
                  <Badge tone="success">✓ {group.resolved_sku_code ?? "Confirmado"}</Badge>
                ) : (
                  <>
                    {badgeLabel && <Badge tone={badgeTone}>{badgeLabel}</Badge>}
                    {conf && <Badge tone="neutral">{conf}</Badge>}
                  </>
                )}
                <span className="meta">{group.line_count ?? 1} linha(s)</span>
                {aliases && <span className="meta">Variantes: {aliases}</span>}
              </div>
              {!isConfirmed && (
                <div className="heroes-sku-triage__row-actions">
                  <ProductCombobox
                    products={products}
                    value={pick[stagingId]?.text ?? group.suggested_product_sku ?? displayName}
                    productId={pick[stagingId]?.productId ?? null}
                    disabled={disabled || resolvingId === stagingId || bulkResolving}
                    onChange={(next) =>
                      setPick((p) => ({
                        ...p,
                        [stagingId]: { text: next.text, productId: next.product?.id ?? null },
                      }))
                    }
                  />
                  <Button
                    variant="primary"
                    className="ui-btn--sm"
                    disabled={
                      disabled ||
                      !pick[stagingId]?.productId ||
                      resolvingId === stagingId ||
                      bulkResolving
                    }
                    onClick={() => confirmResolve(stagingId)}
                  >
                    {resolvingId === stagingId ? "Vinculando…" : "Confirmar"}
                  </Button>
                  <Button
                    variant="secondary"
                    className="ui-btn--sm"
                    disabled={disabled || resolvingId === stagingId || bulkResolving}
                    onClick={() => createDraft(stagingId)}
                  >
                    {resolvingId === stagingId ? "…" : "Criar rascunho"}
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
      <span className="visually-hidden" data-pending-keys={Array.from(pendingCanonicalKeys).join("|")} />
    </section>
  );
}

/** Indica se um nome bruto da planilha ainda está pendente na triage. */
export function isInvoiceItemSkuPending(
  productNameRaw: string | undefined | null,
  pendingGroups: HeroesSkuTriageGroup[],
): boolean {
  if (!productNameRaw || pendingGroups.length === 0) return false;
  const raw = productNameRaw.trim().toLowerCase();
  for (const g of pendingGroups) {
    if (g.status === "confirmed") continue;
    if (g.product_name_raw?.trim().toLowerCase() === raw) return true;
    if (g.aliases?.some((a) => a.trim().toLowerCase() === raw)) return true;
  }
  return false;
}
