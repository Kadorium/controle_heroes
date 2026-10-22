import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getProduct, type Product } from "./catalogApi";
import { classificationLine, displayTitle, humanValue } from "./productIdentity";
import { ContextBreadcrumb, ErrorState, LoadingState, PageHeader } from "../../ui";

type Props = { user: User };

const ROWS: { key: string; label: string; value: (p: Product) => string }[] = [
  { key: "name", label: "Nome comercial", value: displayTitle },
  { key: "category", label: "Categoria", value: (p) => humanValue(p.category_name) },
  { key: "subcategory", label: "Subcategoria", value: (p) => humanValue(p.subcategory) },
  { key: "type", label: "Tipo", value: (p) => humanValue(p.product_type_name) },
  { key: "sport", label: "Esporte", value: (p) => humanValue(p.sport) },
  { key: "line", label: "Linha", value: (p) => humanValue(p.line) },
  { key: "model", label: "Modelo", value: (p) => humanValue(p.model) },
  { key: "year", label: "Coleção", value: (p) => humanValue(p.collection_year) },
  { key: "color", label: "Cor", value: (p) => humanValue(p.color) },
  { key: "gender", label: "Gênero", value: (p) => humanValue(p.gender) },
  { key: "status", label: "Situação", value: (p) => (p.is_active ? "Ativo" : "Inativo") },
  { key: "sku", label: "SKU", value: (p) => p.sku },
];

export function ProductComparePage({ user: _user }: Props) {
  const [params] = useSearchParams();
  const ids = (params.get("ids") || "")
    .split(",")
    .map((v) => Number(v))
    .filter((n) => Number.isFinite(n))
    .slice(0, 3);
  const [rows, setRows] = useState<Product[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyDiffs, setOnlyDiffs] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const loaded = await Promise.all(ids.map((id) => getProduct(id)));
        if (!cancelled) setRows(loaded);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params.get("ids")]);

  const visible = useMemo(() => {
    if (!rows) return [];
    return ROWS.filter((row) => {
      if (!onlyDiffs) return true;
      const values = rows.map((p) => row.value(p));
      return values.some((v) => v !== values[0]);
    });
  }, [rows, onlyDiffs]);

  if (ids.length < 2) return <ErrorState message="Selecione 2 ou 3 produtos para comparar." />;
  if (error) return <ErrorState message={error} />;
  if (!rows) return <LoadingState message="Carregando comparação…" />;

  return (
    <section className="panel dense" data-testid="product-compare-page">
      <ContextBreadcrumb items={[{ label: "Produtos", to: "/catalog/products" }, { label: "Comparar" }]} />
      <PageHeader
        title={`Comparar ${rows.length} produtos`}
        subtitle="Diferenças em destaque · sem motor de similaridade"
        actions={
          <Link className="ui-button ui-button--secondary" to="/catalog/products">
            Voltar à lista
          </Link>
        }
      />
      <label className="stack-row" style={{ gap: "0.5rem", marginBottom: "1rem" }}>
        <input type="checkbox" checked={onlyDiffs} onChange={(e) => setOnlyDiffs(e.target.checked)} data-testid="compare-diffs-only" />
        Mostrar apenas diferenças
      </label>
      <div className="compare-heads">
        {rows.map((p) => (
          <div key={p.id} className="compare-card">
            <div className="product-thumb" aria-hidden="true">
              <span>Placeholder</span>
            </div>
            <strong>{displayTitle(p)}</strong>
            <div className="cell-secondary">{classificationLine(p)}</div>
            <div className="cell-secondary">{p.sku}</div>
          </div>
        ))}
      </div>
      <table className="compare-table" data-testid="compare-table">
        <thead>
          <tr>
            <th>Atributo</th>
            {rows.map((p) => (
              <th key={p.id}>{displayTitle(p)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((row) => {
            const values = rows.map((p) => row.value(p));
            const differs = values.some((v) => v !== values[0]);
            return (
              <tr key={row.key} className={differs ? "compare-diff" : "compare-same"}>
                <th>{row.label}</th>
                {values.map((value, i) => (
                  <td key={rows[i].id}>{value}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
