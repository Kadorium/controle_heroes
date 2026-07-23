import { useState } from "react";
import { Button, Card, Table } from "../../../../components";
import { qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  rows: SkuRow[];
  customsDocId: number | null;
  onNationalize: (itemId: number, qty: number) => Promise<void>;
}

export function NationalizationSection({ rows, customsDocId, onNationalize }: Props) {
  const [qtyByItem, setQtyByItem] = useState<Record<number, string>>({});

  return (
    <Card id="nacionalizacao" title="Nacionalização" compact className="stacked-section logistics-phase">
      {!customsDocId && (
        <p className="meta sheet-warn">Registre e aprove DI/DUIMP na seção Aduana antes de nacionalizar.</p>
      )}
      <Table>
        <thead>
          <tr>
            <th>SKU</th>
            <th className="num">Embarcada</th>
            <th className="num">Nacionalizada</th>
            <th className="num">Qtd a nacionalizar</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.importation_item_id}>
              <td>{r.label}</td>
              <td className="num">{qtyCell(r.quantity_shipped)}</td>
              <td className="num">{qtyCell(r.quantity_nationalized)}</td>
              <td className="num">
                <input
                  type="number"
                  min={1}
                  className="logistics-qty-input"
                  value={qtyByItem[r.importation_item_id] ?? ""}
                  onChange={(e) =>
                    setQtyByItem((q) => ({ ...q, [r.importation_item_id]: e.target.value }))
                  }
                  disabled={!customsDocId}
                />
              </td>
              <td>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!customsDocId}
                  onClick={() => {
                    const qty = Number(qtyByItem[r.importation_item_id]);
                    if (qty > 0) onNationalize(r.importation_item_id, qty);
                  }}
                >
                  Nacionalizar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
