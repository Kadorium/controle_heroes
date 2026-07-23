import { useState, type ReactNode } from "react";
import { Badge } from "./Badge";

export type SectionStatus = "ok" | "warning" | "pending";

interface Props {
  title: string;
  status: SectionStatus;
  statusLabel?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

function statusTone(status: SectionStatus): "success" | "warning" | "neutral" {
  if (status === "ok") return "success";
  if (status === "warning") return "warning";
  return "neutral";
}

function statusIcon(status: SectionStatus): string {
  if (status === "ok") return "✓";
  if (status === "warning") return "⚠";
  return "…";
}

export function HeroesSectionCard({
  title,
  status,
  statusLabel,
  defaultOpen = true,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const label = statusLabel ?? (status === "ok" ? "Ok" : status === "warning" ? "Atenção" : "Pendente");

  return (
    <section className={`heroes-section-card heroes-section-card--${status}`}>
      <button
        type="button"
        className="heroes-section-card__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="heroes-section-card__title">{title}</span>
        <Badge tone={statusTone(status)}>
          {statusIcon(status)} {label}
        </Badge>
        <span className="heroes-section-card__chevron" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && <div className="heroes-section-card__body">{children}</div>}
    </section>
  );
}
