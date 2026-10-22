import { BarStack } from "./charts";
import { MoneyDisplay } from "./MoneyDisplay";
import { chartColors } from "./charts/theme";

export type AgingCurrencyRow = {
  currency: string;
  open_balance: string;
  overdue_balance: string;
  due_today_balance: string;
  next_7d_balance: string;
};

function n(v: string | undefined): number {
  const x = Number.parseFloat(v ?? "0");
  return Number.isFinite(x) ? Math.max(0, x) : 0;
}

/** Proporção vencido / hoje / 7 dias / restante, por moeda — Recharts. */
export function AgingBar({ rows }: { rows: AgingCurrencyRow[] }) {
  if (!rows.length) {
    return (
      <div data-testid="aging-bar">
        <p className="muted">Sem obrigações em aberto neste recorte.</p>
      </div>
    );
  }
  const colors = chartColors();
  const data = rows.map((row) => {
    const open = n(row.open_balance);
    const overdue = n(row.overdue_balance);
    const today = n(row.due_today_balance);
    const week = n(row.next_7d_balance);
    const rest = Math.max(0, open - overdue - today - week);
    return { name: row.currency, overdue, today, week, rest, open };
  });
  return (
    <div className="aging-stack" data-testid="aging-bar">
      <BarStack
        data={data}
        xKey="name"
        series={[
          { key: "overdue", label: "Vencido", color: colors.overdue },
          { key: "today", label: "Hoje", color: colors.today },
          { key: "week", label: "7 dias", color: colors.week },
          { key: "rest", label: "Restante", color: colors.rest },
        ]}
        height={180}
      />
      <ul className="aging-legend">
        <li>
          <span className="aging-dot aging-bar-seg--overdue" />
          Vencido
        </li>
        <li>
          <span className="aging-dot aging-bar-seg--today" />
          Hoje
        </li>
        <li>
          <span className="aging-dot aging-bar-seg--week" />
          7 dias
        </li>
        <li>
          <span className="aging-dot aging-bar-seg--rest" />
          Restante
        </li>
      </ul>
      {rows.map((row) => (
        <div key={row.currency} className="aging-row-head">
          <strong>{row.currency}</strong>
          <MoneyDisplay amount={row.open_balance} currency={row.currency} compact />
        </div>
      ))}
    </div>
  );
}
