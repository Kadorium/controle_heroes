import { Button } from "../../components";
import { WIDGET_REGISTRY, type WidgetId } from "../../hooks/useDashboardConfig";

interface Props {
  open: boolean;
  config: Record<WidgetId, boolean>;
  onToggle: (id: WidgetId) => void;
  onClose: () => void;
}

export function ConfigDrawer({ open, config, onToggle, onClose }: Props) {
  return (
    <>
      <div className={`drawer-back${open ? " drawer-back--show" : ""}`} onClick={onClose} />
      <aside className={`drawer${open ? " drawer--show" : ""}`} aria-hidden={!open}>
        <h3>Personalizar painel</h3>
        <p className="drawer__sub">
          Escolha quais blocos aparecem. A escolha fica salva por usuário.
        </p>

        {WIDGET_REGISTRY.map((w) => (
          <div className="toggle-row" key={w.id}>
            <div className="toggle-row__main">
              <div className="toggle-row__name">{w.name}</div>
              <div className="toggle-row__desc">{w.description}</div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={config[w.id]}
              aria-label={w.name}
              className={`sw${config[w.id] ? " sw--on" : ""}`}
              onClick={() => onToggle(w.id)}
            />
          </div>
        ))}

        <Button onClick={onClose} className="drawer__apply">
          Aplicar
        </Button>
      </aside>
    </>
  );
}
