export type KpiItem = {
  label: string;
  value: string | number | null | undefined;
  hint?: string;
  onClick?: () => void;
  "data-testid"?: string;
};

export function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className="kpi-strip" data-testid="kpi-strip">
      {items.map((k) => {
        const clickable = typeof k.onClick === "function";
        const className = clickable ? "kpi-card kpi-card--action" : "kpi-card";
        if (clickable) {
          return (
            <button
              key={k.label}
              type="button"
              className={className}
              title={k.hint}
              onClick={k.onClick}
              data-testid={k["data-testid"] ?? `kpi-${k.label}`}
            >
              <div className="kpi-label">{k.label}</div>
              <div className="kpi-value">{k.value ?? "—"}</div>
            </button>
          );
        }
        return (
          <div key={k.label} className={className} title={k.hint} data-testid={k["data-testid"]}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value ?? "—"}</div>
          </div>
        );
      })}
    </div>
  );
}
