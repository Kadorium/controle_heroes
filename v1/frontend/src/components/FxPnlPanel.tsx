import type { FxPnlBlock } from "../api";
import { emptyDash, formatAmount, formatMoney } from "../i18n/glossario";

function hasPnlData(pnl: FxPnlBlock | null | undefined): boolean {
  if (!pnl) return false;
  return (
    pnl.pnl_total_brl != null ||
    pnl.pnl_realized_brl != null ||
    pnl.pnl_planned_brl != null ||
    pnl.pnl_unrealized_brl != null
  );
}

function toneClass(v: string | null | undefined): string {
  if (v == null) return "";
  const n = Number(v);
  if (Number.isNaN(n) || n === 0) return "";
  return n > 0 ? " fx-pnl--pos" : " fx-pnl--neg";
}

interface Props {
  pnl: FxPnlBlock | null | undefined;
  variant?: "compact" | "detailed";
  className?: string;
}

export function FxPnlPanel({ pnl, variant = "detailed", className = "" }: Props) {
  if (!hasPnlData(pnl) || !pnl) return null;

  if (variant === "compact") {
    return (
      <div className={`fx-pnl-panel fx-pnl-panel--compact${className ? ` ${className}` : ""}`}>
        <span className="fx-pnl-panel__total">
          {pnl.pnl_total_brl != null ? (
            <strong className={`fx-pnl-val${toneClass(pnl.pnl_total_brl)}`}>
              {formatMoney(pnl.pnl_total_brl, "BRL")}
            </strong>
          ) : (
            emptyDash(null)
          )}
        </span>
        <span className="fx-pnl-panel__compact-subs">
          {pnl.pnl_realized_brl != null && (
            <span>
              R{" "}
              <strong className={`fx-pnl-val${toneClass(pnl.pnl_realized_brl)}`}>
                {formatMoney(pnl.pnl_realized_brl, "BRL")}
              </strong>
            </span>
          )}
          {pnl.pnl_planned_brl != null && (
            <span>
              P{" "}
              <strong className={`fx-pnl-val${toneClass(pnl.pnl_planned_brl)}`}>
                {formatMoney(pnl.pnl_planned_brl, "BRL")}
              </strong>
            </span>
          )}
          {pnl.pnl_unrealized_brl != null && (
            <span>
              NR{" "}
              <strong className={`fx-pnl-val${toneClass(pnl.pnl_unrealized_brl)}`}>
                {formatMoney(pnl.pnl_unrealized_brl, "BRL")}
              </strong>
            </span>
          )}
        </span>
      </div>
    );
  }

  return (
    <div className={`fx-pnl-panel meta${className ? ` ${className}` : ""}`}>
      <strong>{pnl.label}</strong>
      <span className="fx-pnl-panel__disc">{pnl.disclaimer}</span>
      {(pnl.provision_rate != null || pnl.mark_rate != null) && (
        <div className="fx-pnl-panel__rates">
          {pnl.provision_rate != null && <span>Provisão: {formatAmount(pnl.provision_rate)}</span>}
          {pnl.mark_rate != null && <span>Marcação: {formatAmount(pnl.mark_rate)}</span>}
        </div>
      )}
      <div className="fx-pnl-panel__grid">
        {pnl.pnl_realized_brl != null && (
          <span>
            Realizado:{" "}
            <strong className={`fx-pnl-val${toneClass(pnl.pnl_realized_brl)}`}>
              {formatMoney(pnl.pnl_realized_brl, "BRL")}
            </strong>
          </span>
        )}
        {pnl.pnl_planned_brl != null && (
          <span>
            Planejado:{" "}
            <strong className={`fx-pnl-val${toneClass(pnl.pnl_planned_brl)}`}>
              {formatMoney(pnl.pnl_planned_brl, "BRL")}
            </strong>
          </span>
        )}
        {pnl.pnl_unrealized_brl != null && (
          <span>
            Não realizado:{" "}
            <strong className={`fx-pnl-val${toneClass(pnl.pnl_unrealized_brl)}`}>
              {formatMoney(pnl.pnl_unrealized_brl, "BRL")}
            </strong>
          </span>
        )}
        {pnl.pnl_total_brl != null && (
          <span>
            Total:{" "}
            <strong className={`fx-pnl-val${toneClass(pnl.pnl_total_brl)}`}>
              {formatMoney(pnl.pnl_total_brl, "BRL")}
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}

export { hasPnlData };
