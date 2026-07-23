import { Table } from "../../../components";
import { qtyCell, type SkuRow } from "./logisticsUtils";

interface Props {
  rows: SkuRow[];
}

export function LogisticsSkuMatrix({ rows }: Props) {
  if (rows.length === 0) return null;

  return (
    <div className="logistics-sku-matrix">
      <h2 className="logistics-section-title">Trilha por SKU</h2>
      <div className="table-scroll">
        <Table>
          <thead>
            <tr>
              <th>SKU / Modelo</th>
              <th className="num">Pedida</th>
              <th className="num">Faturada</th>
              <th className="num">A despachar</th>
              <th className="num">Embarcada</th>
              <th className="num">Entreposto</th>
              <th className="num">Cons. entreposto</th>
              <th className="num">Nacionalizada</th>
              <th className="num">Estoque Epic</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.importation_item_id}>
                <td>{r.label}</td>
                <td className="num">{qtyCell(r.quantity_ordered)}</td>
                <td className="num">{qtyCell(r.quantity_invoiced)}</td>
                <td className={`num${(r.to_dispatch ?? 0) > 0 ? " sheet-warn" : ""}`}>
                  {qtyCell(r.to_dispatch)}
                </td>
                <td className="num">{qtyCell(r.quantity_shipped)}</td>
                <td className="num">{qtyCell(r.quantity_entreposto_balance)}</td>
                <td className="num">{qtyCell(r.quantity_entreposto_consumed)}</td>
                <td className="num">{qtyCell(r.quantity_nationalized)}</td>
                <td className="num">{qtyCell(r.quantity_stocked)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}
