import { Link } from "react-router-dom";
import { EmptyState } from "../../../components";
import type { DashboardRow } from "../../../hooks/useDashboardMetrics";
import { fullMoney } from "../format";
import { Widget } from "./Widget";

function formatDue(iso: string | null): { day: string; month: string } {
  if (!iso) return { day: "—", month: "venc." };
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return { day: "—", month: "venc." };
  return {
    day: d.getDate().toString().padStart(2, "0"),
    month: d.toLocaleDateString("pt-BR", { month: "short" }),
  };
}

export function UpcomingPaymentsWidget({ rows }: { rows: DashboardRow[] }) {
  const payments = rows
    .flatMap((r) => r.pendingPayments.map((p) => ({ ...p, po: r.po })))
    .sort((a, b) => {
      if (a.dueDate == null && b.dueDate == null) return 0;
      if (a.dueDate == null) return 1;
      if (b.dueDate == null) return -1;
      return a.dueDate.localeCompare(b.dueDate);
    })
    .slice(0, 6);

  return (
    <Widget title="Próximos pagamentos" count={payments.length} span={5}>
      {payments.length === 0 ? (
        <EmptyState
          title="Nenhum saldo em aberto"
          description="Sem invoices com saldo na seleção atual."
        />
      ) : (
        <>
          {payments.map((p, i) => {
            const due = formatDue(p.dueDate);
            return (
              <div className="pay" key={`${p.importationId}-${p.invoiceNumber}-${i}`}>
                <div className={`pay__date${p.isOverdue ? " pay__date--overdue" : ""}`}>
                  <div className="pay__date-d">{due.day}</div>
                  <div className="pay__date-m">{due.month}</div>
                </div>
                <div className="pay__main">
                  <Link to={`/importacoes/${p.importationId}/financeiro`} className="row__po">
                    {p.invoiceType} · {p.invoiceNumber}
                  </Link>
                  <div className="row__sub">
                    {p.po}
                    {p.isOverdue ? " · vencido" : ""}
                  </div>
                </div>
                <div className="row__rt">
                  <div className="row__val">{fullMoney(p.balance, p.currency)}</div>
                  <div className="row__sub">saldo</div>
                </div>
              </div>
            );
          })}
          <p className="meta widget-note">
            Ordenado por vencimento quando cadastrado; itens sem data exibem —.
          </p>
        </>
      )}
    </Widget>
  );
}
