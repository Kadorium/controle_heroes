import { Badge } from "../../components";
import { emptyDash, formatMoney, productCategoryLabel, productModelLabel } from "../../i18n/glossario";
import { heroesCell } from "./orderCentralItemsShared";

interface Props {
  rows: Array<Record<string, unknown>>;
  currency: string;
}

export function OrderCentralDispatchPendingBlock({ rows, currency }: Props) {
  if (rows.length === 0) return null;

  return (
    <div className="oc-section" id="dispatch-pending">
      <div className="oc-section__head">
        <h3>DA SPEDIRE / Despacho (planilha Heroes)</h3>
        <span className="oc-section__count">{rows.length} linhas</span>
      </div>
      <div className="sheet-grid-wrap">
        <table className="sheet-grid">
          <thead>
            <tr>
              <th>{productModelLabel()}</th>
              <th>Categoria sugerida</th>
              <th className="num">A despachar</th>
              <th className="num">Preço listino</th>
              <th className="num">Preço fattura</th>
              <th className="num">Sconto</th>
              <th>Revisão</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d, i) => (
              <tr key={i}>
                <td>{String(d.product_name_raw ?? emptyDash(null))}</td>
                <td>{productCategoryLabel(d.product_category_suggested as string | null)}</td>
                <td className="num">{(d.quantity_to_dispatch as number | null) ?? emptyDash(null)}</td>
                <td className="num">
                  {heroesCell(
                    d.price_listino ? formatMoney(d.price_listino as string, currency) : null,
                    true,
                  )}
                </td>
                <td className="num">
                  {heroesCell(
                    d.price_fattura ? formatMoney(d.price_fattura as string, currency) : null,
                    true,
                  )}
                </td>
                <td className="num">
                  {heroesCell(
                    d.discount_unit ? formatMoney(d.discount_unit as string, currency) : null,
                    true,
                  )}
                </td>
                <td>{d.needs_review ? <Badge tone="warning">Revisar</Badge> : emptyDash(null)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
