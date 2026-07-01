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
  const [error, setError] = useState("");

  useEffect(() => {
    productsApi.list({ for_combobox: true }).then(setProducts).catch(() => undefined);
  }, []);

  useEffect(() => {
    setPick((prev) => {
      const next = { ...prev };
      for (const group of groups) {
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

  const totalGroups = totalResolved + openCount;

  const pendingCanonicalKeys = useMemo(
    () => new Set(groups.map((g) => g.canonical_key).filter(Boolean) as string[]),
    [groups],
  );

  if (openCount === 0 && groups.length === 0) {
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
        <h4>SKUs para resolver</h4>
        <span className="meta">
          {totalResolved} de {totalGroups} resolvido(s)
          {openCount > 0 ? ` · ${openCount} pendente(s)` : ""}
        </span>
      </div>
      {error && <p className="error">{error}</p>}
      <p className="meta heroes-sku-triage__hint">
        Confirme a sugestão (1 clique), busque outro produto no combobox, ou crie um rascunho para importar
        e completar o cadastro depois. Matches com confiança ≥ 70% são resolvidos automaticamente.
      </p>
      <ul className="heroes-sku-triage__list">
        {groups.map((group) => {
          const stagingId = group.staging_id;
          const conf = confidenceLabel(group.match_confidence);
          const hasSuggestion = typeof group.suggested_product_id === "number";
          const displayName = group.product_name_raw ?? "—";
          const aliases =
            (group.aliases?.length ?? 0) > 1
              ? group.aliases!.slice(0, 4).join(", ")
              : null;
          return (
            <li key={stagingId} className="heroes-sku-triage__row">
              <div className="heroes-sku-triage__row-main">
                <strong>{displayName}</strong>
                {group.suggested_category && (
                  <span className="meta">{productCategoryLabel(group.suggested_category)}</span>
                )}
                {conf && (
                  <Badge tone={hasSuggestion ? "info" : "neutral"}>{conf}</Badge>
                )}
                <span className="meta">{group.line_count ?? 1} linha(s)</span>
                {aliases && <span className="meta">Variantes: {aliases}</span>}
              </div>
              <div className="heroes-sku-triage__row-actions">
                <ProductCombobox
                  products={products}
                  value={pick[stagingId]?.text ?? group.suggested_product_sku ?? displayName}
                  productId={pick[stagingId]?.productId ?? null}
                  disabled={disabled || resolvingId === stagingId}
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
                  disabled={disabled || !pick[stagingId]?.productId || resolvingId === stagingId}
                  onClick={() => confirmResolve(stagingId)}
                >
                  {resolvingId === stagingId ? "Vinculando…" : "Confirmar"}
                </Button>
                <Button
                  variant="secondary"
                  className="ui-btn--sm"
                  disabled={disabled || resolvingId === stagingId}
                  onClick={() => createDraft(stagingId)}
                >
                  {resolvingId === stagingId ? "…" : "Criar rascunho"}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      {/* exported for parent badge lookup */}
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
    if (g.product_name_raw?.trim().toLowerCase() === raw) return true;
    if (g.aliases?.some((a) => a.trim().toLowerCase() === raw)) return true;
  }
  return false;
}
