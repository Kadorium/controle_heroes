import type { CSSProperties } from "react";

type Kind = "kpi" | "inbox" | "table" | "block";

const HEIGHT: Record<Kind, string> = {
  kpi: "132px",
  inbox: "220px",
  table: "280px",
  block: "280px",
};

/** Slot de carregamento com altura reservada (DEC-J7-SKELETON). */
export function Skeleton({
  kind = "kpi",
  label = "Carregando",
}: {
  kind?: Kind;
  label?: string;
}) {
  const style = { minHeight: HEIGHT[kind] } as CSSProperties;
  return (
    <div
      className={`skeleton-slot skeleton-slot--${kind}`}
      style={style}
      data-testid="skeleton-slot"
      aria-busy="true"
      aria-label={label}
    />
  );
}
