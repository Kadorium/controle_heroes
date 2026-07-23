import { Link } from "react-router-dom";
import { Badge, EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { ACTION_ROUTE_MAP } from "../../importation/types";
import { Widget } from "./Widget";

export function NeedsActionWidget({ rows }: { rows: DashboardRow[] }) {
  const items = rows
    .flatMap((r) => r.actionItems.map((a) => ({ ...a, po: r.po, id: r.id })))
    .slice(0, 8);

  return (
    <Widget title="Precisa de ação" count={items.length} span={4}>
      {items.length === 0 ? (
        <EmptyState title="Tudo em dia" description="Nenhuma pendência na seleção." />
      ) : (
        items.map((a, i) => {
          const routeFn = ACTION_ROUTE_MAP[a.kind] ?? ACTION_ROUTE_MAP[a.label];
          const href = routeFn ? routeFn(a.id) : `/importacoes/${a.id}/conciliacao`;
          return (
            <div className="row" key={`${a.id}-${a.kind}-${i}`}>
              <Badge tone={a.tone}>{a.label}</Badge>
              <div className="row__main row__main--tight">
                <Link to={href} className="row__po row__po--sm">
                  {a.po}
                </Link>
                <div className="row__sub">{a.detail}</div>
              </div>
            </div>
          );
        })
      )}
    </Widget>
  );
}
