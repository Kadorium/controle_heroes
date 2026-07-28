/** UX Foundation mínima — só o usado por shell / AP / cockpit (Inc-5A). */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header" data-testid="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      {actions ? <div className="page-header-actions">{actions}</div> : null}
    </header>
  );
}

export function ContextBreadcrumb({
  items,
}: {
  items: { label: string; to?: string }[];
}) {
  return (
    <nav className="breadcrumb" aria-label="Breadcrumb" data-testid="breadcrumb">
      {items.map((it, i) => (
        <span key={`${it.label}-${i}`}>
          {i > 0 ? <span className="breadcrumb-sep"> / </span> : null}
          {it.to ? <Link to={it.to}>{it.label}</Link> : <span>{it.label}</span>}
        </span>
      ))}
    </nav>
  );
}

export function KpiStrip({
  items,
}: {
  items: { label: string; value: string | number | null | undefined; hint?: string }[];
}) {
  return (
    <div className="kpi-strip" data-testid="kpi-strip">
      {items.map((k) => (
        <div key={k.label} className="kpi-card" title={k.hint}>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value">{k.value ?? "—"}</div>
        </div>
      ))}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status.includes("PAID") || status === "CONFIRMED" || status === "ISSUED"
      ? "ok"
      : status.includes("CANCEL") || status === "OVERDUE"
        ? "bad"
        : status.includes("PARTIAL") || status === "DRAFT" || status === "STALE"
          ? "warn"
          : "neutral";
  return (
    <span className={`status-badge status-${tone}`} data-testid="status-badge" data-status={status}>
      <span className="status-mark" aria-hidden />
      {status}
    </span>
  );
}

export function MoneyDisplay({
  amount,
  currency,
}: {
  amount: string | number | null | undefined;
  currency?: string | null;
}) {
  if (amount === null || amount === undefined || amount === "") {
    return <span className="money">—</span>;
  }
  return (
    <span className="money" data-testid="money">
      {currency ? `${currency} ` : ""}
      {String(amount)}
    </span>
  );
}

export function FxDisplay({ rate, stale }: { rate: string | null | undefined; stale?: boolean }) {
  if (rate === null || rate === undefined || rate === "") {
    return <span className="fx-display">—</span>;
  }
  return (
    <span className={`fx-display${stale ? " is-stale" : ""}`}>
      {rate}
      {stale ? " · stale" : ""}
    </span>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p className="empty" data-testid="empty-state">
      {message}
    </p>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error" role="alert" data-testid="error-state">
      {message}
    </div>
  );
}

export function LoadingState({ message = "Carregando…" }: { message?: string }) {
  return (
    <p className="muted" data-testid="loading-state">
      {message}
    </p>
  );
}

export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <div className="filter-bar" data-testid="filter-bar">
      {children}
    </div>
  );
}

export function DetailDrawer({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="drawer-backdrop" data-testid="detail-drawer">
      <aside className="drawer-panel" role="dialog" aria-label={title}>
        <header className="drawer-header">
          <h2>{title}</h2>
          <button type="button" className="btn" onClick={onClose}>
            Fechar
          </button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}
