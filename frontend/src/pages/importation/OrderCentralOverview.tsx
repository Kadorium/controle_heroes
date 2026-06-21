import { useEffect, useMemo, useState } from "react";
import { importationsApi, type OrderCentralResponse } from "../../api";
import { Badge, LoadingState } from "../../components";
import { emptyDash, invoiceTypeLabel, payStatusLabel } from "../../i18n/glossario";
import { fmtDate } from "../../utils/formatDate";

interface Props {
  importationId: number;
}

function LockedCell({ children }: { children: React.ReactNode }) {
  return (
    <span className="sheet-cell sheet-cell--locked">
      {children}
      <span className="sheet-flag-it" title="Origem Itália — bloqueado">
        IT
      </span>
    </span>
  );
}

export function OrderCentralOverview({ importationId }: Props) {
  const [data, setData] = useState<OrderCentralResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    importationsApi
      .orderCentral(importationId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [importationId]);

  const blockARows = useMemo(() => {
    if (!data) return [];
    const rows: Array<{
      key: string;
      date: string | null;
      invoiceNumber: string;
      qty: number | null;
      model: string;
      acconto: string;
      accontoRimasto: string;
      creditoRaquete: string;
      creditoAccum: string;
      status: string;
      docs: string;
      isFirst: boolean;
      isAntecipo: boolean;
    }> = [];
    for (const inv of data.invoices) {
      const isAntecipo = inv.invoice_type === "ANTECIPO";
      const acconto = inv.paid_total ? `${inv.currency} ${inv.paid_total}` : emptyDash(null);
      const rimasto = inv.balance != null ? `${inv.currency} ${inv.balance}` : emptyDash(null);
      const status = payStatusLabel(Number(inv.balance ?? 0) === 0 ? "PAID" : "PENDING");
      if (inv.items.length === 0) {
        rows.push({
          key: `${inv.id}-0`,
          date: inv.invoice_date,
          invoiceNumber: inv.invoice_number,
          qty: null,
          model: emptyDash(null),
          acconto,
          accontoRimasto: rimasto,
          creditoRaquete: emptyDash(null), // dado-pendente: crédito por raquete — P1 modelagem
          creditoAccum: emptyDash(null),
          status,
          docs: "—",
          isFirst: true,
          isAntecipo,
        });
        continue;
      }
      inv.items.forEach((ii, idx) => {
        rows.push({
          key: `${inv.id}-${ii.id}`,
          date: idx === 0 ? inv.invoice_date : null,
          invoiceNumber: idx === 0 ? inv.invoice_number : "",
          qty: ii.quantity,
          model: ii.description ?? ii.product_sku ?? emptyDash(null),
          acconto: idx === 0 ? acconto : "",
          accontoRimasto: idx === 0 ? rimasto : "",
          creditoRaquete: emptyDash(null),
          creditoAccum: emptyDash(null),
          status: idx === 0 ? status : "",
          docs: idx === 0 ? "—" : "",
          isFirst: idx === 0,
          isAntecipo,
        });
      });
    }
    return rows;
  }, [data]);

  if (loading) return <LoadingState label="Carregando visão geral..." />;
  if (error) return <p className="error">{error}</p>;
  if (!data) return null;

  const { kpis, models } = data;

  return (
    <div className="order-central-overview">
      <div className="sheet">
        <div className="sheet-head">
          <h3>Faturas · acconto · crédito por raquete</h3>
          <span className="sheet-count">{data.invoices.length} faturas</span>
        </div>
        <div className="sheet-scroll">
          <table className="sheet-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Nº fatura</th>
                <th className="num">Qtd</th>
                <th>Raquete / Produto</th>
                <th className="num">Acconto</th>
                <th className="num">Acconto rimasto</th>
                <th className="num">Crédito/raquete</th>
                <th className="num">Crédito acumulado</th>
                <th>Status</th>
                <th>Docs</th>
              </tr>
            </thead>
            <tbody>
              {blockARows.length === 0 ? (
                <tr>
                  <td colSpan={10}>Nenhuma fatura registrada</td>
                </tr>
              ) : (
                blockARows.map((r) => (
                  <tr key={r.key} className={r.isFirst ? "sheet-grp-first" : ""}>
                    <td>{r.isFirst ? (r.date ? fmtDate(r.date) : emptyDash(null)) : ""}</td>
                    <td className={r.isAntecipo && r.isFirst ? "sheet-po sheet-po--antecipo" : "sheet-po"}>
                      {r.invoiceNumber ? (
                        <>
                          {r.invoiceNumber}
                          {r.isAntecipo && r.isFirst && (
                            <Badge tone="info">{invoiceTypeLabel("ANTECIPO")}</Badge>
                          )}
                        </>
                      ) : (
                        ""
                      )}
                    </td>
                    <td className="num">{r.qty != null ? <LockedCell>{r.qty}</LockedCell> : emptyDash(null)}</td>
                    <td>{r.model}</td>
                    <td className="num c-acconto">{r.acconto ? <LockedCell>{r.acconto}</LockedCell> : ""}</td>
                    <td className="num c-acconto">{r.accontoRimasto ? <LockedCell>{r.accontoRimasto}</LockedCell> : ""}</td>
                    <td className="num c-credito">{r.creditoRaquete}</td>
                    <td className="num c-accum">{r.creditoAccum}</td>
                    <td>{r.status ? <Badge tone="success">{r.status}</Badge> : ""}</td>
                    <td>{r.docs}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2}>Totais</td>
                <td className="num">
                  {blockARows.reduce((s, r) => s + (r.qty ?? 0), 0) || emptyDash(null)}
                </td>
                <td></td>
                <td className="num">{kpis.total_invoiced ?? emptyDash(null)}</td>
                <td className="num">{kpis.consolidated_balance ?? emptyDash(null)}</td>
                <td colSpan={4}></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <div className="sheet-legend">
          <span>
            <i className="sheet-legend-swatch sheet-legend-swatch--acconto" /> acconto (origem Itália)
          </span>
          <span>
            <span className="sheet-flag-it">IT</span> campo Itália — bloqueado
          </span>
        </div>
      </div>

      <div className="sheet">
        <div className="sheet-head">
          <h3>Por modelo · a despachar · preço e desconto (DA SPEDIRE)</h3>
          <span className="sheet-count">{models.length} modelos</span>
        </div>
        <div className="sheet-scroll">
          <table className="sheet-table">
            <thead>
              <tr>
                <th>Modelo</th>
                <th className="num">A despachar</th>
                <th className="num">Pedida</th>
                <th className="num">Faturada</th>
                <th className="num">Despachada</th>
                <th className="num">Nac./recebida</th>
                <th className="num">Restante</th>
                <th>Progresso</th>
                <th className="num">Preço listino</th>
                <th className="num">Preço fattura</th>
                <th className="num">Sconto</th>
                <th className="num">Acconto</th>
                <th className="num">Crédito rimasto</th>
              </tr>
            </thead>
            <tbody>
              {models.length === 0 ? (
                <tr>
                  <td colSpan={13}>Nenhum item na ordem</td>
                </tr>
              ) : (
                models.map((m) => {
                  const ordered = m.quantity_ordered ?? 0;
                  const shipped = m.quantity_shipped ?? 0;
                  const pct = ordered > 0 ? Math.round((shipped / ordered) * 100) : 0;
                  const highlight = (m.to_dispatch ?? 0) > 0;
                  const remaining =
                    m.quantity_ordered != null && m.quantity_stocked != null
                      ? Math.max(0, m.quantity_ordered - m.quantity_stocked)
                      : null;
                  return (
                    <tr key={m.importation_item_id} className={highlight ? "sheet-row--dispatch" : ""}>
                      <td>
                        <b>{m.model_label ?? m.supplier_sku ?? `Item #${m.importation_item_id}`}</b>
                      </td>
                      <td className={`num${highlight ? " sheet-warn" : ""}`}>{m.to_dispatch ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_ordered ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_invoiced ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_shipped ?? emptyDash(null)}</td>
                      <td className="num">{m.quantity_stocked ?? m.quantity_nationalized ?? emptyDash(null)}</td>
                      <td className="num">{remaining ?? emptyDash(null)}</td>
                      <td>
                        <div className="sheet-prog">
                          <div className="sheet-prog__track">
                            <div className="sheet-prog__fill" style={{ width: `${pct}%` }} />
                          </div>
                          <span className="sheet-prog__pct">{pct}%</span>
                        </div>
                      </td>
                      <td className="num">{emptyDash(null)}</td>
                      <td className="num">{emptyDash(null)}</td>
                      <td className="num c-credito">{emptyDash(null)}</td>
                      <td className="num c-acconto">{emptyDash(null)}</td>
                      <td className="num">{emptyDash(null)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
