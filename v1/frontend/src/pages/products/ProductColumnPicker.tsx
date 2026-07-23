import { Button } from "../../components";
import {
  defaultVisibleColumns,
  PRODUCT_COLUMN_LABELS,
  PRODUCT_COLUMN_ORDER,
  type ProductColumnId,
} from "./productColumnPrefs";

interface Props {
  open: boolean;
  visible: ProductColumnId[];
  onChange: (columns: ProductColumnId[]) => void;
  onClose: () => void;
}

export function ProductColumnPicker({ open, visible, onChange, onClose }: Props) {
  if (!open) return null;

  function toggle(col: ProductColumnId) {
    if (visible.includes(col)) {
      const next = visible.filter((c) => c !== col);
      onChange(next.length > 0 ? next : visible);
    } else {
      const next = [...visible, col];
      next.sort((a, b) => PRODUCT_COLUMN_ORDER.indexOf(a) - PRODUCT_COLUMN_ORDER.indexOf(b));
      onChange(next);
    }
  }

  return (
    <>
      <div className="drawer-back drawer-back--show" onClick={onClose} />
      <aside className="drawer drawer--show product-column-picker">
        <h3>Colunas visíveis</h3>
        <p className="meta">Preferência salva neste navegador para sua conta.</p>
        <ul className="product-column-picker__list">
          {PRODUCT_COLUMN_ORDER.map((col) => (
            <li key={col}>
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={visible.includes(col)}
                  onChange={() => toggle(col)}
                />
                {PRODUCT_COLUMN_LABELS[col]}
              </label>
            </li>
          ))}
        </ul>
        <div className="drawer__actions">
          <Button type="button" variant="secondary" onClick={() => onChange(defaultVisibleColumns())}>
            Restaurar padrão
          </Button>
          <Button type="button" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </aside>
    </>
  );
}
