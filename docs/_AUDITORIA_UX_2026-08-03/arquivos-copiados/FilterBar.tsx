import { useId, useState, type ReactNode } from "react";
import { useFocusTrap } from "./useFocusTrap";
import { Button } from "./Button";
import { FilterChip } from "./FilterChip";

export type ActiveFilterChip = {
  id: string;
  label: string;
  onRemove: () => void;
};

type Props = {
  /** Filtros sempre visíveis (primários). */
  primary?: ReactNode;
  /** Secundários — em compact vão para “Mais filtros”. */
  secondary?: ReactNode;
  /** Resumo de filtros ativos ≠ default (chips removíveis). */
  activeFilters?: readonly ActiveFilterChip[];
  onClearAll?: () => void;
  /** Conteúdo legado: se primary/secondary omitidos, renderiza children direto. */
  children?: ReactNode;
};

/**
 * FilterBar adaptativa (Onda A1).
 * Lógica de query permanece na feature; aqui só composição visual.
 */
export function FilterBar({ primary, secondary, activeFilters, onClearAll, children }: Props) {
  const [moreOpen, setMoreOpen] = useState(false);
  const panelId = useId();
  const trapRef = useFocusTrap(moreOpen, () => setMoreOpen(false));
  const activeCount = activeFilters?.length ?? 0;
  const legacy = primary == null && secondary == null;

  if (legacy) {
    return (
      <div className="filter-bar" data-testid="filter-bar">
        {children}
      </div>
    );
  }

  return (
    <div className="filter-bar filter-bar--adaptive" data-testid="filter-bar">
      <div className="filter-bar-primary" data-testid="filter-bar-primary">
        {primary}
      </div>
      {secondary ? (
        <div className="filter-bar-secondary" data-testid="filter-bar-secondary">
          {secondary}
        </div>
      ) : null}
      {secondary ? (
        <div className="filter-bar-more">
          <Button
            type="button"
            variant="ghost"
            aria-expanded={moreOpen}
            aria-controls={panelId}
            data-testid="filter-bar-more-trigger"
            onClick={() => setMoreOpen((v) => !v)}
          >
            Mais filtros{activeCount > 0 ? ` (${activeCount})` : ""}
          </Button>
          {moreOpen ? (
            <div
              ref={trapRef}
              id={panelId}
              className="filter-bar-more-panel"
              role="dialog"
              aria-label="Mais filtros"
              data-testid="filter-bar-more-panel"
            >
              {secondary}
              <Button type="button" variant="ghost" onClick={() => setMoreOpen(false)}>
                Fechar
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}
      {activeCount > 0 ? (
        <div className="filter-bar-active" data-testid="filter-bar-active" aria-label="Filtros ativos">
          {activeFilters!.map((f) => (
            <FilterChip key={f.id} pressed onClick={f.onRemove}>
              {f.label} ×
            </FilterChip>
          ))}
          {onClearAll ? (
            <Button type="button" variant="ghost" data-testid="filter-bar-clear-all" onClick={onClearAll}>
              Limpar filtros
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
