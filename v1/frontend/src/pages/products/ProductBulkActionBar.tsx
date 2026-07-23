import { Button } from "../../components";
import { BULK_ACTION_LABELS, BULK_ACTION_HINTS, type BulkAction } from "./productCatalogUtils";

interface Props {
  count: number;
  onAction: (action: BulkAction) => void;
  canRun: (action: BulkAction) => boolean;
}

const ACTIONS: BulkAction[] = ["archive", "restore", "discontinue", "reactivate", "cancel", "export"];

export function ProductBulkActionBar({ count, onAction, canRun }: Props) {
  if (count === 0) return null;

  return (
    <div className="bulk-action-bar">
      <span className="bulk-action-bar__count">{count} selecionado(s)</span>
      <div className="bulk-action-bar__buttons">
        {ACTIONS.map((action) => (
          <Button
            key={action}
            variant={action === "cancel" ? "secondary" : "ghost"}
            disabled={!canRun(action)}
            title={!canRun(action) ? "Nenhum produto elegível" : BULK_ACTION_HINTS[action]}
            onClick={() => onAction(action)}
          >
            {BULK_ACTION_LABELS[action]}
          </Button>
        ))}
      </div>
    </div>
  );
}
