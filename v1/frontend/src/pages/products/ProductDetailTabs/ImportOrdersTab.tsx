import { Link } from "react-router-dom";
import { EmptyState, Table } from "../../../components";
import type { ProductOrderRow } from "../../../api";
import { emptyDash, formatUnitPrice, statusLabel } from "../../../i18n/glossario";

interface Props {
  orders: ProductOrderRow[];
  orderSearch: string;
  onOrderSearchChange: (v: string) => void;
}

export function ImportOrdersTab({ orders, orderSearch, onOrderSearchChange }: Props) {
  return (
    <>
      <input
        className="search-input"
        placeholder="Buscar ordem ou fornecedor…"
        value={orderSearch}
        onChange={(e) => onOrderSearchChange(e.target.value)}
      />
      {orders.length === 0 ? (
        <EmptyState title="Nenhuma ordem com este produto" />
      ) : (
        <Table className="table-dense">
          <thead>
            <tr>
              <th>Ordem</th>
              <th>Status</th>
              <th>Fornecedor</th>
              <th>Qtd</th>
              <th>LC unit.</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.importation_id}>
                <td>
                  <Link to={`/importacoes/${o.importation_id}/resumo`}>{o.po_number}</Link>
                </td>
                <td>{statusLabel(o.current_status)}</td>
                <td>{o.supplier_name ?? emptyDash(null)}</td>
                <td className="num">{o.qty_ordered ?? emptyDash(null)}</td>
                <td className="num">{formatUnitPrice(o.landed_cost_unit)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
