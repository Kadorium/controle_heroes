import type { ReactNode } from "react";
import { Button } from "./Button";
import { useFocusTrap } from "./useFocusTrap";

/** Dialog de copy do catálogo (não usa title= nativo). */
export function ExplainerDialog({
  open,
  title,
  description,
  unitLabel,
  limitation,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  description: string;
  unitLabel?: string;
  limitation?: string | null;
  children?: ReactNode;
  onClose: () => void;
}) {
  const trapRef = useFocusTrap(open, onClose);
  if (!open) return null;
  return (
    <div
      className="explainer-backdrop"
      data-testid="explainer-dialog"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={trapRef}
        className="explainer-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="explainer-title"
      >
        <h2 id="explainer-title">{title}</h2>
        <p>{description}</p>
        {unitLabel ? <p className="muted">Unidade: {unitLabel}</p> : null}
        {limitation ? <p className="muted">{limitation}</p> : null}
        {children}
        <Button type="button" variant="secondary" onClick={onClose}>
          Fechar
        </Button>
      </div>
    </div>
  );
}
