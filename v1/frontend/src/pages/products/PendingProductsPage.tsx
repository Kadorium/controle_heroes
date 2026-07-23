import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { productsApi, type Product, type ProductDraftRow } from "../../api";
import { Badge, Button, ProductCombobox } from "../../components";
import { productCategoryLabel } from "../../i18n/glossario";
import { DraftCompleteDrawer } from "./DraftCompleteDrawer";

type PickState = { text: string; productId: number | null };

export function PendingProductsPage() {
  const [items, setItems] = useState<ProductDraftRow[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pick, setPick] = useState<Record<number, PickState>>({});
  const [linkingId, setLinkingId] = useState<number | null>(null);
  const [completeDraft, setCompleteDraft] = useState<ProductDraftRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await productsApi.listDrafts();
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar rascunhos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    productsApi.list({ for_combobox: true }).then(setProducts).catch(() => undefined);
  }, [load]);

  async function linkDraft(draftId: number) {
    const sel = pick[draftId];
    if (!sel?.productId) return;
    setLinkingId(draftId);
    setError("");
    try {
      await productsApi.linkDraft(draftId, sel.productId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao vincular rascunho");
    } finally {
      setLinkingId(null);
    }
  }

  return (
    <div className="card">
      <h1>Produtos pendentes</h1>
      <p className="meta">
        Rascunhos criados na importação Heroes aguardando cadastro definitivo. Complete o SKU ou vincule a
        um produto existente.
      </p>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <p className="meta">Carregando…</p>
      ) : items.length === 0 ? (
        <p className="meta">Nenhum produto rascunho pendente.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Rascunho</th>
              <th>Nome bruto</th>
              <th>Categoria</th>
              <th>Ordens</th>
              <th>Criado</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id}>
                <td>
                  <Badge tone="warning">Rascunho</Badge>
                  <span className="meta"> {row.sku_code}</span>
                </td>
                <td>{row.description}</td>
                <td>{productCategoryLabel(row.category)}</td>
                <td className="num">
                  {row.referencing_importation_count > 0 ? (
                    row.origin_importation_id ? (
                      <Link to={`/importacoes/${row.origin_importation_id}/resumo`}>
                        {row.referencing_importation_count}
                      </Link>
                    ) : (
                      row.referencing_importation_count
                    )
                  ) : (
                    "—"
                  )}
                </td>
                <td>{row.created_at ? new Date(row.created_at).toLocaleDateString("pt-BR") : "—"}</td>
                <td>
                  <div className="review-queue__resolve">
                    <Button variant="secondary" className="ui-btn--sm" onClick={() => setCompleteDraft(row)}>
                      Completar cadastro
                    </Button>
                    <ProductCombobox
                      products={products}
                      value={pick[row.id]?.text ?? ""}
                      productId={pick[row.id]?.productId ?? null}
                      disabled={linkingId === row.id}
                      placeholder="Vincular existente…"
                      onChange={(next) =>
                        setPick((p) => ({
                          ...p,
                          [row.id]: { text: next.text, productId: next.product?.id ?? null },
                        }))
                      }
                    />
                    <Button
                      variant="ghost"
                      className="ui-btn--sm"
                      disabled={!pick[row.id]?.productId || linkingId === row.id}
                      onClick={() => linkDraft(row.id)}
                    >
                      {linkingId === row.id ? "Vinculando…" : "Vincular"}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <DraftCompleteDrawer
        draft={completeDraft}
        open={!!completeDraft}
        onClose={() => setCompleteDraft(null)}
        onCompleted={load}
      />
    </div>
  );
}
