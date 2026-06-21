import { Link } from "react-router-dom";
import { Badge, EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { Widget } from "./Widget";

export function OverduePaymentsWidget({ rows }: { rows: DashboardRow[] }) {
  const overdue = rows
    .flatMap((r) =>
      r.pendingPayments
        .filter((p) => p.isOverdue)
        .map((p) => ({ ...p, po: r.po, importationId: r.id }))
    )
    .slice(0, 5);

  return (
    <Widget title="Pagamentos vencidos" count={overdue.length} span={4}>
      {overdue.length === 0 ? (
        <EmptyState title="Nenhum vencido" description="Sem pagamentos planejados vencidos." />
      ) : (
        overdue.map((p, i) => (
          <div className="row" key={`${p.importationId}-${p.invoiceId}-${i}`}>
            <Badge tone="danger">Vencido</Badge>
            <div className="row__main row__main--tight">
              <Link to={`/importacoes/${p.importationId}/financeiro`} className="row__po row__po--sm">
                {p.po}
              </Link>
              <div className="row__sub">
                {p.invoiceNumber} · {p.dueDate ?? "—"}
              </div>
            </div>
          </div>
        ))
      )}
    </Widget>
  );
}
