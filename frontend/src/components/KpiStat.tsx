import type { ReactNode } from "react";

export type KpiAccent = "blue" | "green" | "amber" | "red";

interface KpiStatProps {
  accent: KpiAccent;
  label: string;
  icon: ReactNode;
  value: ReactNode;
  unit?: string;
  footer?: ReactNode;
}

export function KpiStat({ accent, label, icon, value, unit, footer }: KpiStatProps) {
  return (
    <div className={`kpi kpi--${accent}`}>
      <div className="kpi__top">
        <span className="kpi__label">{label}</span>
        <span className="kpi__icon">{icon}</span>
      </div>
      <div className="kpi__value">
        {value}
        {unit && <small> {unit}</small>}
      </div>
      {footer && <div className="kpi__foot">{footer}</div>}
    </div>
  );
}
