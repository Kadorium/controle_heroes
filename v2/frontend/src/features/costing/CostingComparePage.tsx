import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import type { User } from "../auth/types";
import { canReadCosting } from "./costingPermissions";
import { compareCostingVersions, type CostingCompare } from "./costingApi";
import { componentTypeLabel, sourceKindLabel, versionStatusLabel } from "./costingLabels";
import {
  ContextBreadcrumb,
  ErrorState,
  LoadingState,
  MoneyDisplay,
  PageHeader,
  formatDateTime,
  formatMoney,
} from "../../ui";

type Props = { user: User };

function moneyDelta(left: string | null | undefined, right: string | null | undefined): number | null {
  if (left == null && right == null) return null;
  const a = left == null || left === "" ? 0 : Number(left);
  const b = right == null || right === "" ? 0 : Number(right);
  if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
  return b - a;
}

function sameMoney(left: string | null | undefined, right: string | null | undefined): boolean {
  const d = moneyDelta(left, right);
  return d === null || Math.abs(d) < 0.0000001;
}

export function CostingComparePage({ user }: Props) {
  const { caseId } = useParams();
  const [params] = useSearchParams();
  const leftId = Number(params.get("left"));
  const rightId = Number(params.get("right"));
  const [data, setData] = useState<CostingCompare | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onlyDiffs, setOnlyDiffs] = useState(false);

  useEffect(() => {
    if (!Number.isFinite(leftId) || !Number.isFinite(rightId) || leftId === rightId) {
      setError("Selecione duas versões distintas para comparar.");
      return;
    }
    let cancelled = false;
    void compareCostingVersions(leftId, rightId)
      .then((cmp) => {
        if (!cancelled) setData(cmp);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [leftId, rightId]);

  const totalDelta = useMemo(() => {
    if (!data) return null;
    return moneyDelta(data.left.included_total_brl, data.right.included_total_brl);
  }, [data]);

  const componentRows = useMemo(() => {
    if (!data) return [];
    return data.components.filter((row) => {
      if (!onlyDiffs) return true;
      return !sameMoney(row.left_amount_brl, row.right_amount_brl) || row.left_included !== row.right_included;
    });
  }, [data, onlyDiffs]);

  const productRows = useMemo(() => {
    if (!data) return [];
    return data.products.filter((row) => {
      if (!onlyDiffs) return true;
      return (
        !sameMoney(row.left_total_brl, row.right_total_brl) ||
        !sameMoney(row.left_unit_brl, row.right_unit_brl) ||
        (row.left_qty ?? "") !== (row.right_qty ?? "")
      );
    });
  }, [data, onlyDiffs]);

  if (!canReadCosting(user)) {
    return <ErrorState message="É preciso costing:read." />;
  }
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState message="Carregando comparação…" />;

  const back = `/costing/${caseId ?? data.left.case_id ?? ""}`;

  return (
    <section className="panel dense" data-testid="costing-compare-page">
      <ContextBreadcrumb
        items={[
          { label: "Custos", to: "/costing" },
          { label: "Caso", to: back },
          { label: "Comparar" },
        ]}
      />
      <PageHeader
        title="Comparar versões de custo"
        subtitle="Somente leitura · diferenças em destaque"
        actions={
          <Link className="ui-button ui-button--secondary" to={back} data-testid="costing-compare-back">
            Voltar ao caso
          </Link>
        }
      />

      <label className="stack-row" style={{ gap: "0.5rem", marginBottom: "1rem" }}>
        <input
          type="checkbox"
          checked={onlyDiffs}
          onChange={(e) => setOnlyDiffs(e.target.checked)}
          data-testid="costing-compare-diffs-only"
        />
        Mostrar apenas diferenças
      </label>

      <div className="compare-heads" data-testid="costing-compare-summary">
        <div className="compare-card">
          <strong>
            v{data.left.version_number} · {data.left.kind}
          </strong>
          <div className="cell-secondary">{versionStatusLabel(data.left.status)}</div>
          <div>
            <MoneyDisplay amount={data.left.included_total_brl} currency="BRL" />
          </div>
          <div className="cell-secondary">
            {data.left.published_at ? formatDateTime(data.left.published_at) : "—"}
          </div>
        </div>
        <div className="compare-card">
          <strong>
            v{data.right.version_number} · {data.right.kind}
          </strong>
          <div className="cell-secondary">{versionStatusLabel(data.right.status)}</div>
          <div>
            <MoneyDisplay amount={data.right.included_total_brl} currency="BRL" />
          </div>
          <div className="cell-secondary">
            {data.right.published_at ? formatDateTime(data.right.published_at) : "—"}
          </div>
        </div>
        <div className="compare-card" data-testid="costing-compare-total-delta">
          <strong>Delta total</strong>
          <div>{totalDelta == null ? "—" : formatMoney(totalDelta, "BRL")}</div>
        </div>
      </div>

      <h2>Componentes</h2>
      <table className="compare-table data-table" data-testid="costing-compare-components">
        <thead>
          <tr>
            <th>Componente</th>
            <th>Origem</th>
            <th>Esquerda</th>
            <th>Direita</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>
          {componentRows.length === 0 ? (
            <tr>
              <td colSpan={5}>Sem diferenças nesta seção.</td>
            </tr>
          ) : (
            componentRows.map((row) => {
              const delta = moneyDelta(row.left_amount_brl, row.right_amount_brl);
              const diff = !sameMoney(row.left_amount_brl, row.right_amount_brl);
              return (
                <tr key={`${row.component_type}:${row.source_kind}`} className={diff ? "compare-diff" : "cell-secondary"}>
                  <td>{componentTypeLabel(row.component_type)}</td>
                  <td>{sourceKindLabel(row.source_kind)}</td>
                  <td>{formatMoney(row.left_amount_brl, "BRL")}</td>
                  <td>{formatMoney(row.right_amount_brl, "BRL")}</td>
                  <td>{delta == null ? "—" : formatMoney(delta, "BRL")}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      <h2>Produtos</h2>
      <table className="compare-table data-table" data-testid="costing-compare-products">
        <thead>
          <tr>
            <th>Nome / SKU</th>
            <th>Qty esq.</th>
            <th>Qty dir.</th>
            <th>Total esq.</th>
            <th>Total dir.</th>
            <th>Unit. esq.</th>
            <th>Unit. dir.</th>
            <th>Delta total</th>
          </tr>
        </thead>
        <tbody>
          {productRows.length === 0 ? (
            <tr>
              <td colSpan={8}>Sem diferenças nesta seção.</td>
            </tr>
          ) : (
            productRows.map((row) => {
              const delta = moneyDelta(row.left_total_brl, row.right_total_brl);
              const diff = !sameMoney(row.left_total_brl, row.right_total_brl);
              return (
                <tr key={`${row.sku_snapshot}:${row.product_id}`} className={diff ? "compare-diff" : "cell-secondary"}>
                  <td>
                    <div>{row.description_snapshot || "—"}</div>
                    <div className="cell-secondary">{row.sku_snapshot}</div>
                  </td>
                  <td>{row.left_qty ?? "—"}</td>
                  <td>{row.right_qty ?? "—"}</td>
                  <td>{formatMoney(row.left_total_brl, "BRL")}</td>
                  <td>{formatMoney(row.right_total_brl, "BRL")}</td>
                  <td>{formatMoney(row.left_unit_brl, "BRL")}</td>
                  <td>{formatMoney(row.right_unit_brl, "BRL")}</td>
                  <td>{delta == null ? "—" : formatMoney(delta, "BRL")}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </section>
  );
}
