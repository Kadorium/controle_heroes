import { Link } from "react-router-dom";
import { Badge, EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { formatAmount } from "../../../i18n/glossario";
import { Widget } from "./Widget";

export function CloseToClosureWidget({ rows }: { rows: DashboardRow[] }) {
  const ready = rows
    .filter((r) => r.closurePendingCount === 0 && r.status !== "CLOSED")
    .slice(0, 5);

  return (
    <Widget title="Próximas de fechamento" count={ready.length} span={4}>
      {ready.length === 0 ? (
        <EmptyState title="Nenhuma pronta" description="Checklist de fechamento ainda com pendências." />
      ) : (
        ready.map((r) => (
          <div className="row" key={r.id}>
            <Badge tone="success">Pronta</Badge>
            <div className="row__main row__main--tight">
              <Link to={`/importacoes/${r.id}/conciliacao`} className="row__po row__po--sm">
                {r.po}
              </Link>
              <div className="row__sub">Checklist OK · {r.status}</div>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}

export function DivergenceWidget({ rows }: { rows: DashboardRow[] }) {
  const divs = rows.filter((r) => r.hasDivergence).slice(0, 5);

  return (
    <Widget title="Com divergência" count={divs.length} span={4}>
      {divs.length === 0 ? (
        <EmptyState title="Sem divergências" description="Nenhuma conciliação bloqueante aberta." />
      ) : (
        divs.map((r) => (
          <div className="row" key={r.id}>
            <Badge tone="danger">{r.divergenceCount} item(ns)</Badge>
            <div className="row__main row__main--tight">
              <Link to={`/importacoes/${r.id}/conciliacao`} className="row__po row__po--sm">
                {r.po}
              </Link>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}

export function CostVarianceWidget({ rows }: { rows: DashboardRow[] }) {
  const withLc = rows
    .filter((r) => r.lcEstimated != null && r.lcActual != null)
    .map((r) => ({
      ...r,
      delta: Math.abs((r.lcActual ?? 0) - (r.lcEstimated ?? 0)),
    }))
    .sort((a, b) => b.delta - a.delta)
    .slice(0, 5);

  return (
    <Widget title="Maiores variações de custo" count={withLc.length} span={4}>
      {withLc.length === 0 ? (
        <EmptyState title="Sem landed cost comparável" description="Precisa de versões estimada e final." />
      ) : (
        withLc.map((r) => (
          <div className="row" key={r.id}>
            <div className="row__main">
              <Link to={`/importacoes/${r.id}/aduaneiro`} className="row__po row__po--sm">
                {r.po}
              </Link>
              <div className="row__sub">
                Est. {formatAmount(r.lcEstimated)} · Real {formatAmount(r.lcActual)}
              </div>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}
