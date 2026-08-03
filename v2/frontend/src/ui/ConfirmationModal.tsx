import type { ReactNode } from "react";
import { Button } from "./Button";
import { useFocusTrap } from "./useFocusTrap";

/** Modal de confirmação — base DS (§27.6). Focus trap + Escape (I9-9). */
export function ConfirmationModal({
  open,
  title,
  children,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const trapRef = useFocusTrap(open, onCancel);
  if (!open) return null;
  return (
    <div className="drawer-backdrop" role="presentation" data-testid="confirmation-modal">
      <div
        ref={trapRef}
        className="drawer-panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        style={{
          width: "min(420px, 100%)",
          margin: "auto",
          borderRadius: 6,
          float: "left",
          borderRight: "1px solid var(--color-border-decorative)",
        }}
      >
        <header className="drawer-header">
          <h2 id="confirm-title">{title}</h2>
          <Button variant="ghost" onClick={onCancel} disabled={busy} aria-label="Fechar">
            {cancelLabel}
          </Button>
        </header>
        <div className="drawer-body">{children}</div>
        <div className="actions" style={{ marginTop: "1rem" }}>
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button onClick={onConfirm} busy={busy} data-testid="confirm-modal-ok">
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
