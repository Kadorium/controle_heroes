import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { ImportationItem, OperationalHeader, OrderCentralInvoice, OrderCentralModel } from "../../api";
import { FxPnlPanel } from "../../components/FxPnlPanel";
import { emptyDash, formatMoney, formatMoneyLocale, formatUnitPrice, modalLabel } from "../../i18n/glossario";
import { fmtDate } from "../../utils/formatDate";

const MAX_ITEM_ROWS = 5;

interface Props {
  importationId: number;
  header: OperationalHeader;
  estimatedTotal?: string | null;
  currency?: string;
  models?: OrderCentralModel[];
  items?: ImportationItem[];
  invoices?: OrderCentralInvoice[];
}

interface ItemPreviewRow {
  key: number;
  label: string;
  qty: number | null;
  unitPrice: string | null;
  paid: string | null;
}

function buildItemPreviewRows(
  models: OrderCentralModel[] | undefined,
  items: ImportationItem[] | undefined,
  invoices: OrderCentralInvoice[] | undefined,
): ItemPreviewRow[] {
  const itemById = new Map((items ?? []).map((i) => [i.id, i]));
  const seen = new Set<number>();

  const pushRow = (row: ItemPreviewRow) => {
    if (seen.has(row.key)) return;
    seen.add(row.key);
    rows.push(row);
  };

  const rows: ItemPreviewRow[] = [];

  if (models && models.length > 0) {
    for (const m of models) {
      pushRow({
        key: m.importation_item_id,
        label: m.model_label ?? m.description ?? m.supplier_sku ?? m.product_sku ?? "—",
        qty: m.quantity_ordered,
        unitPrice: m.price_fattura ?? itemById.get(m.importation_item_id)?.unit_price_foreign ?? null,
        paid: m.acconto_amount ?? null,
      });
    }
  }

  for (const it of items ?? []) {
    pushRow({
      key: it.id,
      label: it.description ?? it.supplier_sku ?? "—",
      qty: it.quantity_ordered,
      unitPrice: it.unit_price_foreign ?? null,
      paid: null,
    });
  }

  for (const inv of invoices ?? []) {
    for (const ii of inv.items ?? []) {
      const key = ii.importation_item_id ?? ii.id;
      pushRow({
        key,
        label: ii.description ?? ii.product_sku ?? inv.invoice_number,
        qty: ii.quantity,
        unitPrice: ii.unit_price,
        paid: ii.amount ?? inv.paid_total,
      });
    }
  }

  return rows;
}

function pick(...vals: (string | null | undefined)[]): string | null {
  for (const v of vals) {
    if (v != null && v !== "") return v;
  }
  return null;
}

function eurVal(v: string | null) {
  return formatMoneyLocale(v, "EUR", "it-IT");
}

function brlVal(v: string | null) {
  return v != null ? formatMoneyLocale(v, "BRL", "pt-BR") : emptyDash(null);
}

function resolveFinance(header: OperationalHeader, estimatedTotal?: string | null) {
  const eur = header.totals_by_currency?.EUR;
  const opening = header.opening_exchange_rate ?? null;

  const orderTotalEur = pick(header.order_total_eur, estimatedTotal);
  const orderTotalBrl = pick(
    header.order_total_brl,
    orderTotalEur && opening ? String(Number(orderTotalEur) * Number(opening)) : null,
  );

  const invoicedEur = pick(header.invoiced_eur, header.total_invoiced, eur?.total_invoiced);
  const invoicedBrl = pick(
    header.invoiced_brl,
    invoicedEur && opening ? String(Number(invoicedEur) * Number(opening)) : null,
  );

  const settledEur = pick(header.settled_eur, header.total_paid, eur?.total_paid);
  const settledBrl = pick(header.settled_brl);

  const remainingEur = pick(
    header.remaining_to_invoice_eur,
    orderTotalEur && invoicedEur
      ? String(Math.max(0, Number(orderTotalEur) - Number(invoicedEur)))
      : null,
  );
  const remainingBrl = pick(
    header.remaining_to_invoice_brl,
    remainingEur && opening ? String(Number(remainingEur) * Number(opening)) : null,
  );

  const balanceEur = pick(header.balance_to_settle_eur, header.open_balance, eur?.consolidated_balance);
  const avgInvRate =
    invoicedEur && invoicedBrl && Number(invoicedEur) > 0
      ? Number(invoicedBrl) / Number(invoicedEur)
      : opening != null
        ? Number(opening)
        : null;
  const balanceBrl = pick(
    header.balance_to_settle_brl,
    header.open_balance_brl_equivalent,
    balanceEur && avgInvRate != null ? String(Number(balanceEur) * avgInvRate) : null,
  );

  return {
    opening,
    orderTotalEur,
    orderTotalBrl,
    invoicedEur,
    invoicedBrl,
    settledEur,
    settledBrl,
    remainingEur,
    remainingBrl,
    balanceEur,
    balanceBrl,
  };
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
  currency = "EUR",
  models,
  items,
  invoices,
}: Props) {
  const navigate = useNavigate();
  const fin = resolveFinance(header, estimatedTotal);
  const qtyOrdered = header.quantity_ordered;
  const toDispatch = header.to_dispatch ?? 0;
  const shipped =
    qtyOrdered != null && header.to_dispatch != null ? qtyOrdered - header.to_dispatch : null;

  const itemRows = useMemo(
    () => buildItemPreviewRows(models, items, invoices),
    [models, items, invoices],
  );
  const itemPreview = itemRows.slice(0, MAX_ITEM_ROWS);
  const itemOverflow = itemRows.length - itemPreview.length;

  const openInvoiceLabel = header.next_open_invoice_number;
  const openInvoiceDue = header.next_due_date;
  const openInvoiceBalance = header.next_open_invoice_balance;

  const openingHint = fin.opening ? `câmbio abertura ${fin.opening}` : "câmbio abertura";

  const goItems = () => navigate(`/importacoes/${importationId}/resumo`);
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
            <MoneyPair eur={fin.orderTotalEur} brl={fin.orderTotalBrl} brlHint={openingHint} />
          </div>
        </div>

        <div className="oc-finance-total oc-finance-total--sub">
          <span className="oc-finance-total__label">A faturar</span>
          <div className="oc-finance-pair">
            <MoneyPair eur={fin.remainingEur} brl={fin.remainingBrl} brlHint={openingHint} />
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
            <span className="oc-finance-invoiced__brl" title="previsto por fatura">
              {brlVal(fin.invoicedBrl)}
            </span>

            <span className="oc-finance-invoiced__label">Liquidado</span>
            <span className="oc-finance-invoiced__eur">{eurVal(fin.settledEur)}</span>
            <span className="oc-finance-invoiced__brl" title="BRL efetivo pago">
              {brlVal(fin.settledBrl)}
            </span>

            <span className="oc-finance-invoiced__label oc-finance-invoiced__label--emph">
              A liquidar
            </span>
            <span className="oc-finance-invoiced__eur oc-finance-invoiced__eur--emph">
              {eurVal(fin.balanceEur)}
            </span>
            <span className="oc-finance-invoiced__brl oc-finance-invoiced__brl--emph" title="previsto em aberto">
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
        {itemPreview.length === 0 ? (
          <span className="oc-operational-header__subs">sem itens na ordem</span>
        ) : (
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
        )}
        {itemOverflow > 0 && (
          <span className="oc-operational-header__meta">+{itemOverflow} item(ns) · ver resumo</span>
        )}
        {(openInvoiceDue || openInvoiceLabel || openInvoiceBalance) && (
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
  );
}
