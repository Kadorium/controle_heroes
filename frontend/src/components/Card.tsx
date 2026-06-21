import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  children: ReactNode;
  compact?: boolean;
  id?: string;
  className?: string;
}

export function Card({ title, children, compact, id, className = "" }: CardProps) {
  return (
    <div
      id={id}
      className={`ui-card ${compact ? "ui-card--compact" : ""} ${className}`.trim()}
    >
      {title && <h3 className="ui-card__title">{title}</h3>}
      {children}
    </div>
  );
}
