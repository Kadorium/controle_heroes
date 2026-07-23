import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { importsApi, productsApi, type Product, type ReviewQueueItem } from "../api";
import { Button } from "../components";
import { ProductCombobox } from "../components/ProductCombobox";

function issueLabel(data: Record<string, string | number | null | undefined>): string {
  const t = data.issue_type;
  if (t === "SKU_UNRESOLVED") return "SKU pendente";
  if (t === "MERGE_CONFLICT") return "Conflito merge";
  return t ? String(t) : "Revisão";
}

function aliasesLabel(data: Record<string, string | number | null | undefined>): string {
  const aliases = data.aliases;
  if (Array.isArray(aliases) && aliases.length > 0) {
    return aliases.map(String).join(", ");
  }
  return String(data.product_name_raw ?? data.sku ?? "—");
}

export function ReviewQueuePage() {
  const [searchParams] = useSearchParams();
  const heroesRunFilter = searchParams.get("heroes_run_id");
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState("");
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [pick, setPick] = useState<Record<number, { text: string; productId: number | null }>>({});
  const [extraAliases, setExtraAliases] = useState<Record<number, string>>({});
  const [saveAliases, setSaveAliases] = useState<Record<number, boolean>>({});

  async function load() {
    try {
      setItems(await importsApi.reviewQueue());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    load();
    productsApi.list().then(setProducts).catch(() => {});
  }, []);

  const visibleItems = useMemo(() => {
    if (!heroesRunFilter) return items;
    const runId = Number(heroesRunFilter);
    if (!Number.isFinite(runId)) return items;
    return items.filter((item) => {
      const data = item.staging_row?.parsed_data_json ?? {};
      return Number(data.heroes_run_id) === runId;
    });
  }, [items, heroesRunFilter]);

  useEffect(() => {
    if (!products.length || !visibleItems.length) return;
    setPick((prev) => {
      const next = { ...prev };
      for (const item of visibleItems) {
        const stagingId = item.staging_row_id;
        if (next[stagingId]?.productId) continue;
        const data = item.staging_row?.parsed_data_json ?? {};
        const suggestedId = data.suggested_product_id;
        if (typeof suggestedId !== "number") continue;
        const prod = products.find((p) => p.id === suggestedId);
        if (!prod) continue;
        next[stagingId] = {
          text: prod.description,
          productId: prod.id,
        };
      }
      return next;
    });
  }, [visibleItems, products]);

  async function resolveSku(stagingId: number) {
    const sel = pick[stagingId];
    if (!sel?.productId) return;
    setResolvingId(stagingId);
    setError("");
    try {
      const extra = (extraAliases[stagingId] ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await importsApi.resolveStagingSku(stagingId, sel.productId, {
        saveAliases: saveAliases[stagingId] ?? true,
        extraAliases: extra,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao vincular SKU");
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <div className="card">
      <h1>Fila de Revisão</h1>
      <p className="meta">
        {heroesRunFilter
          ? `Filtrado pela importação Heroes (run #${heroesRunFilter}). `
          : ""}
        Racchettas agrupadas por nome canônico — vincule uma vez por grupo.
      </p>
      {error && <p className="error">{error}</p>}
      <table className="data-table">
        <thead>
          <tr>
            <th>Linha</th>
            <th>Tipo</th>
            <th>Fatura</th>
            <th>Data</th>
            <th>Racchetta</th>
            <th>Variantes</th>
            <th>Motivo</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {visibleItems.map((item) => {
            const data = item.staging_row?.parsed_data_json ?? {};
            const stagingId = item.staging_row_id;
            const isSku = data.issue_type === "SKU_UNRESOLVED";
            const racchetta = String(data.product_name_raw ?? data.sku ?? "—");
            const variants = aliasesLabel(data);
            const aliasCount = Number(data.alias_count ?? (Array.isArray(data.aliases) ? data.aliases.length : 1));
            const suggestedDesc =
              typeof data.suggested_product_description === "string"
                ? data.suggested_product_description
                : racchetta;
            return (
              <tr key={item.id}>
                <td>{item.staging_row?.row_number ?? stagingId}</td>
                <td>{issueLabel(data)}</td>
                <td>
                  {Array.isArray(data.invoice_numbers) && data.invoice_numbers.length > 0
                    ? (data.invoice_numbers as string[]).join(", ")
                    : data.invoice_number != null
                      ? String(data.invoice_number)
                      : data.po_number ?? "—"}
                </td>
                <td>{data.invoice_date != null ? String(data.invoice_date) : "—"}</td>
                <td>
                  {racchetta}
                  {aliasCount > 1 && (
                    <span className="meta"> — {aliasCount} grafias</span>
                  )}
                </td>
                <td className="meta">{variants}</td>
                <td>{item.reason}</td>
                <td>
                  {isSku ? (
                    <div className="review-queue__resolve">
                      <ProductCombobox
                        products={products}
                        value={pick[stagingId]?.text ?? suggestedDesc}
                        productId={pick[stagingId]?.productId ?? null}
                        onChange={(next) =>
                          setPick((p) => ({
                            ...p,
                            [stagingId]: { text: next.text, productId: next.product?.id ?? null },
                          }))
                        }
                      />
                      <label className="meta review-queue__save-aliases">
                        <input
                          type="checkbox"
                          checked={saveAliases[stagingId] ?? true}
                          onChange={(e) =>
                            setSaveAliases((s) => ({ ...s, [stagingId]: e.target.checked }))
                          }
                        />{" "}
                        Salvar grafias no produto (próximas importações)
                      </label>
                      <input
                        type="text"
                        className="review-queue__extra-aliases"
                        placeholder="Nomes extras (vírgula), ex.: show, show-26"
                        value={extraAliases[stagingId] ?? ""}
                        onChange={(e) =>
                          setExtraAliases((x) => ({ ...x, [stagingId]: e.target.value }))
                        }
                      />
                      <Button
                        variant="ghost"
                        className="ui-btn--sm"
                        disabled={!pick[stagingId]?.productId || resolvingId === stagingId}
                        onClick={() => resolveSku(stagingId)}
                      >
                        Vincular
                      </Button>
                    </div>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {visibleItems.length === 0 && <p className="meta">Nenhum item pendente.</p>}
    </div>
  );
}
