import type { ReactNode } from "react";

type Props = {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  "data-testid"?: string;
};

/** Card de seção (§27) — título + ações opcionais + corpo. */
export function SectionCard({
  title,
  actions,
  children,
  className,
  "data-testid": testId = "section-card",
}: Props) {
  return (
    <section className={["section-card", className].filter(Boolean).join(" ")} data-testid={testId}>
      {title || actions ? (
        <header className="section-card-header">
          {title ? <h2 className="section-card-title">{title}</h2> : <span />}
          {actions ? <div className="section-card-actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="section-card-body">{children}</div>
    </section>
  );
}
