import { useEffect, useRef, useState, type ReactNode, type TableHTMLAttributes } from "react";
import {
  filterVisibleColumns,
  layoutModeFromWidth,
  type LayoutMode,
  type OperationalColumnDef,
} from "./tableColumns";

type Density = "standard" | "finance";

type LegacyProps = TableHTMLAttributes<HTMLTableElement> & {
  density?: Density;
  stickyHeader?: boolean;
  zebra?: boolean;
  stickyFirstColumn?: boolean;
  children: ReactNode;
  columns?: undefined;
  rows?: undefined;
  getRowId?: undefined;
  layoutMode?: undefined;
  onRowClick?: undefined;
  selectedId?: undefined;
  "data-testid"?: string;
};

type ColumnsProps<T> = Omit<TableHTMLAttributes<HTMLTableElement>, "children"> & {
  density?: Density;
  stickyHeader?: boolean;
  zebra?: boolean;
  /** Opt-in sticky first visible column — default false (piloto sem sticky col). */
  stickyFirstColumn?: boolean;
  columns: readonly OperationalColumnDef<T>[];
  rows: readonly T[];
  getRowId: (row: T) => string;
  /** Se omitido, 1 ResizeObserver no host deriva o modo. */
  layoutMode?: LayoutMode;
  onRowClick?: (row: T) => void;
  selectedId?: string | null;
  getRowTestId?: (row: T) => string;
  children?: undefined;
  "data-testid"?: string;
};

type Props<T> = LegacyProps | ColumnsProps<T>;

function remToPx(rem: string, rootFontPx = 16): number {
  const m = /^([\d.]+)rem$/.exec(rem.trim());
  if (m) return Number(m[1]) * rootFontPx;
  const n = Number.parseFloat(rem);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Primitive de fila OperationalTable (§27.3).
 * API children (legado) permanece enquanto houver consumidores.
 * API `columns` opt-in: um `visibleColumns` por tabela; omit React (não col[data-visibility]).
 */
export function OperationalTable<T>(props: Props<T>) {
  if (props.columns) {
    return <OperationalTableColumns {...(props as ColumnsProps<T>)} />;
  }
  return <OperationalTableLegacy {...(props as LegacyProps)} />;
}

function OperationalTableLegacy({
  density = "standard",
  stickyHeader = true,
  zebra = false,
  stickyFirstColumn = false,
  className,
  children,
  ...rest
}: LegacyProps) {
  const densityClass = density === "finance" ? "density-finance" : "density-standard";
  const wrapClass = [
    "operational-table-wrap",
    stickyHeader ? "has-sticky-header" : null,
    stickyFirstColumn ? "has-sticky-first-col" : null,
  ]
    .filter(Boolean)
    .join(" ");
  const tableClass = ["operational-table", densityClass, zebra ? "is-zebra" : null, className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={wrapClass}>
      <table className={tableClass} {...rest}>
        {children}
      </table>
    </div>
  );
}

function OperationalTableColumns<T>({
  density = "standard",
  stickyHeader = true,
  zebra = false,
  stickyFirstColumn = false,
  columns,
  rows,
  getRowId,
  layoutMode: layoutModeProp,
  onRowClick,
  selectedId,
  getRowTestId,
  className,
  ...rest
}: ColumnsProps<T>) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [observedMode, setObservedMode] = useState<LayoutMode>("wide");

  useEffect(() => {
    if (layoutModeProp) return;
    const el = hostRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;

    const rootFont = Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
    const styles = getComputedStyle(el);
    const compactMax =
      remToPx(styles.getPropertyValue("--layout-mode-compact-max").trim() || "52rem", rootFont) ||
      52 * rootFont;
    const standardMax =
      remToPx(styles.getPropertyValue("--layout-mode-standard-max").trim() || "72rem", rootFont) ||
      72 * rootFont;

    let last: LayoutMode | null = null;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? el.clientWidth;
      const next = layoutModeFromWidth(w, compactMax, standardMax);
      if (next !== last) {
        last = next;
        setObservedMode(next);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [layoutModeProp]);

  const layoutMode = layoutModeProp ?? observedMode;
  const visibleColumns = filterVisibleColumns(columns, layoutMode);

  const densityClass = density === "finance" ? "density-finance" : "density-standard";
  const wrapClass = [
    "operational-table-wrap",
    stickyHeader ? "has-sticky-header" : null,
    stickyFirstColumn ? "has-sticky-first-col" : null,
  ]
    .filter(Boolean)
    .join(" ");
  const tableClass = [
    "operational-table",
    "is-fixed",
    densityClass,
    zebra ? "is-zebra" : null,
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      ref={hostRef}
      className="queue-shell"
      data-layout={layoutMode}
      data-testid="queue-shell"
    >
      <div className={wrapClass}>
        <table className={tableClass} {...rest}>
          <colgroup>
            {visibleColumns.map((col) => (
              <col
                key={col.id}
                style={{
                  width: col.minWidth,
                  minWidth: col.minWidth,
                  maxWidth: col.maxWidth,
                }}
              />
            ))}
          </colgroup>
          <thead>
            <tr>
              {visibleColumns.map((col) => {
                const align = col.align === "end" ? "num" : undefined;
                return (
                  <th
                    key={col.id}
                    className={[align, col.headerClassName, col.truncate ? "truncate" : null]
                      .filter(Boolean)
                      .join(" ") || undefined}
                  >
                    {col.header}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const id = getRowId(row);
              const selected = selectedId != null && selectedId === id;
              return (
                <tr
                  key={id}
                  data-row-id={id}
                  data-testid={getRowTestId?.(row)}
                  className={[onRowClick ? "row-click" : null, selected ? "is-selected" : null]
                    .filter(Boolean)
                    .join(" ") || undefined}
                  aria-selected={selected ? true : undefined}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {visibleColumns.map((col) => {
                    const align = col.align === "end" ? "num" : undefined;
                    const cellClass = [
                      align,
                      col.cellClassName,
                      col.truncate ? "truncate" : null,
                      col.align === "end" ? "tabular-nums" : null,
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <td key={col.id} className={cellClass || undefined}>
                        {col.truncate ? <span className="truncate">{col.cell(row)}</span> : col.cell(row)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
