import { Link } from "react-router-dom";
import { EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { compactMoney } from "../format";
import { Widget } from "./Widget";

export function TopOpenBalancesWidget({ rows }: { rows: DashboardRow[] }) {
  const top = [...rows]
    .filter((r) => r.openValue != null && r.openValue > 0)
    .sort((a, b) => (b.openValue ?? 0) - (a.openValue ?? 0))
    .slice(0, 5);

  return (
    <Widget title="Maiores saldos em aberto" count={top.length} span={4}>
      {top.length === 0 ? (
        <EmptyState title="Sem saldos" description="Nenhuma importação com saldo em aberto." />
      ) : (
        top.map((r) => (
          <div className="row" key={r.id}>
            <div className="row__main">
              <Link to={`/importacoes/${r.id}/financeiro`} className="row__po">
                {r.po}
              </Link>
              <div className="row__sub">{r.supplierName}</div>
            </div>
            <div className="row__rt">
              <strong>{compactMoney(r.openValue!, r.currency)}</strong>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}
