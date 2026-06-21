export type BadgeTone = "neutral" | "info" | "warning" | "success" | "danger";

export function statusToTone(status: string): BadgeTone {
  const s = status.toUpperCase();
  if (["PO_CREATED", "ON_HOLD", "DRAFT", "RASCUNHO"].includes(s)) return "neutral";
  if (["BOOKED", "SHIPPED", "IN_TRANSIT", "ARRIVED", "PROFORMA_RECEIVED", "ADVANCE_PAID", "PARTIAL_PAID"].includes(s))
    return "info";
  if (["PENDING", "OPEN", "PENDING_REVIEW", "DIVERGENT", "WARNING"].includes(s)) return "warning";
  if (["CLOSED", "CLEARED", "OK", "FULL_PAID", "APPROVED", "MERGED"].includes(s)) return "success";
  if (["CANCELLED", "REJECTED", "BLOCKING", "FAILED"].includes(s)) return "danger";
  return "info";
}

interface BadgeProps {
  tone?: BadgeTone;
  status?: string;
  children: React.ReactNode;
}

export function Badge({ tone, status, children }: BadgeProps) {
  const resolved = tone ?? (status ? statusToTone(status) : "info");
  return <span className={`ui-badge ui-badge--${resolved}`}>{children}</span>;
}
