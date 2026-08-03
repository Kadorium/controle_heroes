import type { ReactNode } from "react";
import { Button } from "./Button";
import { useFocusTrap } from "./useFocusTrap";

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
  const trapRef = useFocusTrap(open, onClose);
  if (!open) return null;
  return (
    <div
      className="drawer-backdrop"
      data-testid="detail-drawer"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <aside
        ref={trapRef}
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="drawer-header">
          <h2>{title}</h2>
          <Button type="button" variant="ghost" onClick={onClose} aria-label="Fechar drawer">
            Fechar
          </Button>
        </header>
        <div className="drawer-body">{children}</div>
      </aside>
    </div>
  );
}
