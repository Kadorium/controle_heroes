import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ImportationItem, OperationalHeader, OrderCentralInvoice, OrderCentralModel } from "../../api";
import { FxPnlPanel } from "../../components/FxPnlPanel";
import { emptyDash, formatMoney, formatMoneyLocale, formatUnitPrice, modalLabel } from "../../i18n/glossario";
import { fmtDate } from "../../utils/formatDate";
import {
  buildItemPreviewRows,
  estimateItemPreviewRowCount,
  resolveFinance,
} from "./orderCentralOperationalHeaderUtils";

const DEFAULT_ITEM_ROWS = 6;
const FALLBACK_ROW_HEIGHT_PX = 22;

interface Props {
  importationId: number;
  header: OperationalHeader;
  estimatedTotal?: string | null;
  versatoTotal?: string | null;
  currency?: string;
  models?: OrderCentralModel[];
  items?: ImportationItem[];
  invoices?: OrderCentralInvoice[];
}

function eurVal(v: string | null) {
  return formatMoneyLocale(v, "EUR", "it-IT");
}

function brlVal(v: string | null) {
  return v != null ? formatMoneyLocale(v, "BRL", "pt-BR") : emptyDash(null);
}

function MoneyPair({
  eur,
  brl,
  brlHint,
}: {
  eur: string | null;
  brl: string | null;
  brlHint?: string;
}) {
  return (
    <>
      <span className="oc-finance-pair__eur">{eurVal(eur)}</span>
      <span className="oc-finance-pair__brl" title={brlHint}>
        {brlVal(brl)}
      </span>
    </>
  );
}

export function OrderCentralOperationalHeader({
  importationId,
  header,
  estimatedTotal,
  versatoTotal,
  currency = "EUR",
  models,
  items,
  invoices,
}: Props) {
  const navigate = useNavigate();
  const itemsColRef = useRef<HTMLDivElement>(null);
  const [maxItemRows, setMaxItemRows] = useState(DEFAULT_ITEM_ROWS);

  const fin = resolveFinance(header, estimatedTotal, versatoTotal);
  const qtyOrdered = header.quantity_ordered;
  const toDispatch = header.to_dispatch ?? 0;
  const shipped =
    qtyOrdered != null && header.to_dispatch != null ? qtyOrdered - header.to_dispatch : null;

  const itemRows = useMemo(
    () => buildItemPreviewRows(models, items, invoices),
    [models, items, invoices],
  );
  const itemPreview = itemRows.slice(0, maxItemRows);
  const itemOverflow = itemRows.length - itemPreview.length;

  const openInvoiceLabel = header.next_open_invoice_number;
  const openInvoiceDue = header.next_due_date;
  const openInvoiceBalance = header.next_open_invoice_balance;
  const hasInvoiceFooter = Boolean(openInvoiceDue || openInvoiceLabel || openInvoiceBalance);

  useLayoutEffect(() => {
    const col = itemsColRef.current;
    if (!col) return;

    const measure = () => {
      const style = getComputedStyle(col);
      const padY = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
      const footer = col.querySelector(".oc-items-preview-footer") as HTMLElement | null;
      const footerH = footer?.offsetHeight ?? 0;
      const thead = col.querySelector(".oc-items-preview thead") as HTMLElement | null;
      const theadH = thead?.offsetHeight ?? 22;
      const sampleRow = col.querySelector(".oc-items-preview tbody tr") as HTMLElement | null;
      const rowH = sampleRow?.offsetHeight ?? FALLBACK_ROW_HEIGHT_PX;
      setMaxItemRows(
        estimateItemPreviewRowCount(col.clientHeight, padY, footerH, theadH, rowH),
      );
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(col);
    return () => ro.disconnect();
  }, [itemRows.length, hasInvoiceFooter]);

  const goItems = () => navigate(`/importacoes/${importationId}/itens`);
  const goInvoices = () =>
    navigate(
      openInvoiceLabel
        ? `/importacoes/${importationId}/invoices`
        : `/importacoes/${importationId}/financeiro`,
    );

  return (
    <div className="oc-operational-header">
      <button
        type="button"
        className="oc-operational-header__col oc-operational-header__col--finance"
        onClick={() => navigate(`/importacoes/${importationId}/financeiro`)}
      >
        <span className="oc-operational-header__label">Financeiro</span>

        <div className="oc-finance-total">
          <span className="oc-finance-total__label">Total da ordem</span>
          <div className="oc-finance-pair oc-finance-pair--hero">
            <MoneyPair eur={fin.orderTotalEur} brl={fin.orderTotalBrl} brlHint={fin.brlHint} />
          </div>
        </div>

        <div className="oc-finance-total oc-finance-total--sub">
          <span className="oc-finance-total__label">A faturar</span>
          <div className="oc-finance-pair">
            <MoneyPair eur={fin.remainingEur} brl={fin.remainingBrl} brlHint={fin.brlHint} />
          </div>
        </div>

        <div className="oc-finance-invoiced">
          <span className="oc-finance-invoiced__title">Já faturado</span>
          <div className="oc-finance-invoiced__grid">
            <span className="oc-finance-invoiced__head" />
            <span className="oc-finance-invoiced__head">EUR</span>
            <span className="oc-finance-invoiced__head">BRL</span>

            <span className="oc-finance-invoiced__label">Faturado</span>
            <span className="oc-finance-invoiced__eur">{eurVal(fin.invoicedEur)}</span>
            <span className="oc-finance-invoiced__brl" title={fin.brlHint}>
              {brlVal(fin.invoicedBrl)}
            </span>

            <span className="oc-finance-invoiced__label">Liquidado</span>
            <span className="oc-finance-invoiced__eur">{eurVal(fin.settledEur)}</span>
            <span className="oc-finance-invoiced__brl" title={fin.brlHint}>
              {brlVal(fin.settledBrl)}
            </span>

            <span className="oc-finance-invoiced__label oc-finance-invoiced__label--emph">
              A liquidar
            </span>
            <span className="oc-finance-invoiced__eur oc-finance-invoiced__eur--emph">
              {eurVal(fin.balanceEur)}
            </span>
            <span className="oc-finance-invoiced__brl oc-finance-invoiced__brl--emph" title={fin.brlHint}>
              {brlVal(fin.balanceBrl)}
            </span>
          </div>
        </div>

        <div className="oc-finance-pnl" title={header.fx_pnl?.disclaimer}>
          <span className="oc-finance-pnl__label">PnL Cambial</span>
          <FxPnlPanel pnl={header.fx_pnl} variant="compact" />
        </div>
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

      <div
        ref={itemsColRef}
        role="button"
        tabIndex={0}
        className={`oc-operational-header__col oc-operational-header__col--items${
          header.overdue_count > 0 ? " oc-overdue" : ""
        }`}
        onClick={goItems}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            goItems();
          }
        }}
      >
        <span className="oc-operational-header__label">Itens</span>
        {itemPreview.length === 0 ? (
          <span className="oc-operational-header__subs">sem itens na ordem</span>
        ) : (
          <div className="oc-items-preview-wrap">
            <table className="oc-items-preview">
              <thead>
                <tr>
                  <th>Item</th>
                  <th className="num">Qtd</th>
                  <th className="num">Preço un.</th>
                  <th className="num">Valor</th>
                </tr>
              </thead>
              <tbody>
                {itemPreview.map((row) => (
                  <tr key={row.key}>
                    <td className="oc-items-preview__item" title={row.label}>
                      {row.label}
                    </td>
                    <td className="num">{row.qty ?? emptyDash(null)}</td>
                    <td className="num">{formatUnitPrice(row.unitPrice)}</td>
                    <td className="num">{formatMoney(row.paid, currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="oc-items-preview-footer">
          {itemOverflow > 0 && (
            <span className="oc-operational-header__meta oc-items-preview-more">
              +{itemOverflow} item(ns) · ver produtos
            </span>
          )}
          {hasInvoiceFooter && (
            <button
              type="button"
              className="oc-open-invoice-deadline"
              onClick={(e) => {
                e.stopPropagation();
                goInvoices();
              }}
            >
              {openInvoiceLabel ? `${openInvoiceLabel} · ` : ""}
              {openInvoiceDue ? `venc. ${fmtDate(openInvoiceDue)}` : "fatura em aberto"}
              {openInvoiceBalance ? ` · ${formatMoney(openInvoiceBalance, currency)}` : ""}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
