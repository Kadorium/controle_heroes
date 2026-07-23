import { Button } from "../../components";
import type { Product } from "../../api";
import { BULK_ACTION_LABELS, type BulkAction } from "./productCatalogUtils";

interface Props {
  action: BulkAction;
  eligible: Product[];
  ineligible: Product[];
  reason: string;
  onReasonChange: (v: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function ProductBulkConfirmModal({
  action,
  eligible,
  ineligible,
  reason,
  onReasonChange,
  onConfirm,
  onCancel,
  loading,
}: Props) {
  const needsReason = action === "archive" || action === "cancel";
  const withOrders = action === "cancel" ? eligible.filter((p) => (p.orders_count ?? 0) > 0) : [];

  return (
    <div className="modal-back" onClick={onCancel}>
      <div className="modal-card modal-card--wide" onClick={(e) => e.stopPropagation()}>
        <h3>{BULK_ACTION_LABELS[action]} — confirmação</h3>
        <p>
          <strong>{eligible.length}</strong> produto(s) serão afetados
          {ineligible.length > 0 && (
            <> · <strong>{ineligible.length}</strong> ignorado(s)</>
          )}
        </p>
        {eligible.length > 0 && (
          <ul className="bulk-preview-list">
            {eligible.slice(0, 8).map((p) => (
              <li key={p.id}>{p.sku_code} — {p.description}</li>
            ))}
            {eligible.length > 8 && <li>… e mais {eligible.length - 8}</li>}
          </ul>
        )}
        {withOrders.length > 0 && (
          <p className="warning">
            Atenção: {withOrders.length} produto(s) já usados em ordens. A exclusão preserva o histórico.
          </p>
        )}
        {needsReason && (
          <textarea
            placeholder="Motivo da exclusão (obrigatório, mín. 3 caracteres)"
            value={reason}
            onChange={(e) => onReasonChange(e.target.value)}
            rows={3}
          />
        )}
        <div className="modal-actions">
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            Cancelar
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading || eligible.length === 0 || (needsReason && reason.trim().length < 3)}
          >
            Confirmar
          </Button>
        </div>
      </div>
    </div>
  );
}
