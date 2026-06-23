import { useNavigate } from "react-router-dom";
import type { CurrencyTotals, OperationalHeader } from "../../api";
import { emptyDash, formatMoneyLocale, modalLabel, statusLabel } from "../../i18n/glossario";
import { fmtDate } from "../../utils/formatDate";

interface Props {
  importationId: number;
  header: OperationalHeader;
}

function eurTotals(header: OperationalHeader): CurrencyTotals {
  if (header.totals_by_currency?.EUR) {
    return header.totals_by_currency.EUR;
  }
  return {
    total_invoiced: header.total_invoiced,
    total_paid: header.total_paid,
    total_discounts: null,
    consolidated_balance: header.open_balance,
  };
}

function progressPct(paid: string | null, invoiced: string | null): number | null {
  if (!paid || !invoiced) return null;
  const p = Number(paid);
  const t = Number(invoiced);
  if (Number.isNaN(p) || Number.isNaN(t) || t <= 0) return null;
  return Math.min(100, Math.round((p / t) * 100));
}

export function OrderCentralOperationalHeader({ importationId, header }: Props) {
  const navigate = useNavigate();
  const eur = eurTotals(header);
  const pct = progressPct(eur.total_paid, eur.total_invoiced);
  const qtyOrdered = header.quantity_ordered;
  const toDispatch = header.to_dispatch ?? 0;
  const shipped =
    qtyOrdered != null && header.to_dispatch != null ? qtyOrdered - header.to_dispatch : null;

  const today = new Date().toISOString().slice(0, 10);
  const dueSoon =
    header.next_due_date && !header.overdue_count && header.next_due_date >= today;

  return (
    <div className="oc-operational-header">
      <button
        type="button"
        className="oc-operational-header__col"
        onClick={() => navigate(`/importacoes/${importationId}/invoices`)}
      >
        <span className="oc-operational-header__label">Pagamentos</span>
        <span className="oc-operational-header__eur">
          {formatMoneyLocale(eur.consolidated_balance, "EUR", "it-IT")}
        </span>
        <span className="oc-operational-header__brl">
          {header.open_balance_brl_equivalent != null
            ? formatMoneyLocale(header.open_balance_brl_equivalent, "BRL", "pt-BR")
            : emptyDash(null)}
        </span>
        {header.open_balance_brl_equivalent != null && (
          <span className="oc-operational-header__fx-note">equivalente a câmbio previsto</span>
        )}
        <div className="oc-operational-header__subs">
          <span>
            pago {formatMoneyLocale(eur.total_paid, "EUR", "it-IT")} · em aberto{" "}
            {formatMoneyLocale(eur.consolidated_balance, "EUR", "it-IT")}
          </span>
        </div>
        {pct != null && (
          <div className="oc-progress" title={`${pct}% do faturado quitado`}>
            <div className="oc-progress__bar" style={{ width: `${pct}%` }} />
          </div>
        )}
        <span className="oc-operational-header__meta">
          {header.invoices_settled_count}/{header.invoices_count} faturas quitadas
        </span>
      </button>

      <button
        type="button"
        className="oc-operational-header__col"
        onClick={() => navigate(`/importacoes/${importationId}/logistica`)}
      >
        <span className="oc-operational-header__label">Logística</span>
        <span className="oc-operational-header__value">
          {header.next_eta ? fmtDate(header.next_eta) : emptyDash(null)}
        </span>
        <span className="oc-operational-header__subs">
          {header.next_etd ? `ETD ${fmtDate(header.next_etd)}` : "ETD —"}
          {header.active_modal ? ` · ${modalLabel(header.active_modal)}` : ""}
        </span>
        <span className="oc-operational-header__meta">
          {header.to_dispatch != null && qtyOrdered != null
            ? `${shipped ?? 0} de ${qtyOrdered} un. despachadas · ${toDispatch} a despachar`
            : emptyDash(null)}
        </span>
      </button>

      <button
        type="button"
        className={`oc-operational-header__col${
          header.overdue_count > 0 ? " oc-overdue" : dueSoon ? " oc-due-soon" : ""
        }`}
        onClick={() => navigate(`/importacoes/${importationId}/financeiro`)}
      >
        <span className="oc-operational-header__label">Prazos</span>
        <span className="oc-operational-header__value">
          {header.next_due_date ? fmtDate(header.next_due_date) : emptyDash(null)}
        </span>
        <span className="oc-operational-header__subs">
          {header.overdue_count > 0
            ? `${header.overdue_count} atraso(s) · ${formatMoneyLocale(
                header.overdue_amount_foreign,
                "EUR",
                "it-IT",
              )}`
            : header.next_due_date
              ? "próximo vencimento"
              : "sem vencimentos planejados"}
        </span>
        {header.supplier_credit_available && (
          <span className="oc-operational-header__meta">
            crédito fornecedor {formatMoneyLocale(header.supplier_credit_available, "EUR", "it-IT")}
          </span>
        )}
      </button>
    </div>
  );
}
