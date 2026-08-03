import type { ReactNode } from "react";

export type SummaryItem = {
  label: string;
  value: ReactNode;
};

type Props = {
  items: SummaryItem[];
  className?: string;
  "data-testid"?: string;
};

/** Grade de pares label/valor para cabeçalhos de detalhe. */
export function SummaryGrid({
  items,
  className,
  "data-testid": testId = "summary-grid",
}: Props) {
  return (
    <dl className={["summary-grid", className].filter(Boolean).join(" ")} data-testid={testId}>
      {items.map((item) => (
        <div key={item.label} className="summary-grid-item">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
