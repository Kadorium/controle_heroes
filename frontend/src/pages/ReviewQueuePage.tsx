import { useEffect, useState } from "react";
import { importsApi, productsApi, type Product, type ReviewQueueItem } from "../api";
import { Button } from "../components";
import { ProductCombobox } from "../components/ProductCombobox";

function issueLabel(data: Record<string, string | number | null | undefined>): string {
  const t = data.issue_type;
  if (t === "SKU_UNRESOLVED") return "SKU pendente";
  if (t === "MERGE_CONFLICT") return "Conflito merge";
  return t ? String(t) : "Revisão";
}

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState("");
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [pick, setPick] = useState<Record<number, { text: string; productId: number | null }>>({});

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

  async function resolveSku(stagingId: number) {
    const sel = pick[stagingId];
    if (!sel?.productId) return;
    setResolvingId(stagingId);
    setError("");
    try {
      await importsApi.resolveStagingSku(stagingId, sel.productId);
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
      <p className="meta">Linhas ambíguas ou racchetta sem SKU aguardam revisão humana.</p>
      {error && <p className="error">{error}</p>}
      <table className="data-table">
        <thead>
          <tr>
            <th>Linha</th>
            <th>Tipo</th>
            <th>Fatura</th>
            <th>Data</th>
            <th>Racchetta</th>
            <th>Motivo</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const data = item.staging_row?.parsed_data_json ?? {};
            const stagingId = item.staging_row_id;
            const isSku = data.issue_type === "SKU_UNRESOLVED";
            const racchetta = String(data.product_name_raw ?? data.sku ?? "—");
            return (
              <tr key={item.id}>
                <td>{item.staging_row?.row_number ?? stagingId}</td>
                <td>{issueLabel(data)}</td>
                <td>{data.invoice_number != null ? String(data.invoice_number) : data.po_number ?? "—"}</td>
                <td>{data.invoice_date != null ? String(data.invoice_date) : "—"}</td>
                <td>{racchetta}</td>
                <td>{item.reason}</td>
                <td>
                  {isSku ? (
                    <div className="review-queue__resolve">
                      <ProductCombobox
                        products={products}
                        value={pick[stagingId]?.text ?? racchetta}
                        productId={pick[stagingId]?.productId ?? null}
                        onChange={(next) =>
                          setPick((p) => ({
                            ...p,
                            [stagingId]: { text: next.text, productId: next.product?.id ?? null },
                          }))
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
      {items.length === 0 && <p className="meta">Nenhum item pendente.</p>}
    </div>
  );
}
