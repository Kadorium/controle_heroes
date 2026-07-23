import { useEffect, useState } from "react";
import { EmptyState, LoadingState, Table } from "../../../components";
import { productsApi } from "../../../api";
import { formatUnitPrice } from "../../../i18n/glossario";
import { fmtDateTime } from "../../../utils/formatDate";

interface Props {
  productId: number;
  lastUnit?: string | null;
}

export function CostsTab({ productId, lastUnit }: Props) {
  const [rows, setRows] = useState<
    Array<{
      importation_id: number;
      po_number: string;
      version_number: number;
      version_type: string;
      unit_cost: string | null;
      created_at: string;
    }>
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    void productsApi
      .costHistory(productId)
      .then((r) => setRows(r.items))
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <LoadingState />;

  return (
    <>
      <p className="num">Último landed cost unitário: {formatUnitPrice(lastUnit)}</p>
      {rows.length === 0 ? (
        <EmptyState title="Sem histórico de custos" />
      ) : (
        <Table className="table-dense">
          <thead>
            <tr>
              <th>Ordem</th>
              <th>Versão</th>
              <th>Tipo</th>
              <th>Unit.</th>
              <th>Data</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.importation_id}-${r.version_number}-${i}`}>
                <td>{r.po_number}</td>
                <td className="num">{r.version_number}</td>
                <td>{r.version_type}</td>
                <td className="num">{formatUnitPrice(r.unit_cost)}</td>
                <td>{fmtDateTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
