import { useState } from "react";
import { Button, Card, Table } from "../../../../components";
import type { LandedCostVersion } from "../../../../api";
import { formatMoney } from "../../../../i18n/glossario";
import { qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  rows: SkuRow[];
  lcVersions: LandedCostVersion[];
  onStockEntry: (itemId: number, qty: number, unitCost: string) => Promise<void>;
  onCreateLc: (method: string) => Promise<void>;
}

export function StockSection({ rows, lcVersions, onStockEntry, onCreateLc }: Props) {
  const [qtyByItem, setQtyByItem] = useState<Record<number, string>>({});
  const [costByItem, setCostByItem] = useState<Record<number, string>>({});
  const [lcMethod, setLcMethod] = useState("VALUE");

  return (
    <>
      <Card id="estoque" title="Estoque Epic" compact className="stacked-section logistics-phase">
        <p className="meta">Entrada no estoque local após nacionalização.</p>
        <Table>
          <thead>
            <tr>
              <th>SKU</th>
              <th className="num">Nacionalizada</th>
              <th className="num">Em estoque</th>
              <th className="num">Qtd recebida</th>
              <th>Custo unit.</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.importation_item_id}>
                <td>{r.label}</td>
                <td className="num">{qtyCell(r.quantity_nationalized)}</td>
                <td className="num">{qtyCell(r.quantity_stocked)}</td>
                <td className="num">
                  <input
                    type="number"
                    min={1}
                    className="logistics-qty-input"
                    value={qtyByItem[r.importation_item_id] ?? ""}
                    onChange={(e) =>
                      setQtyByItem((q) => ({ ...q, [r.importation_item_id]: e.target.value }))
                    }
                  />
                </td>
                <td>
                  <input
                    placeholder="BRL"
                    value={costByItem[r.importation_item_id] ?? ""}
                    onChange={(e) =>
                      setCostByItem((c) => ({ ...c, [r.importation_item_id]: e.target.value }))
                    }
                  />
                </td>
                <td>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      const qty = Number(qtyByItem[r.importation_item_id]);
                      if (qty > 0)
                        onStockEntry(
                          r.importation_item_id,
                          qty,
                          costByItem[r.importation_item_id] ?? "",
                        );
                    }}
                  >
                    Entrada
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card id="landed-cost" title="Landed cost" compact className="stacked-section logistics-phase">
        <form
          className="inline-form"
          onSubmit={async (e) => {
            e.preventDefault();
            await onCreateLc(lcMethod);
          }}
        >
          <select value={lcMethod} onChange={(e) => setLcMethod(e.target.value)}>
            <option value="VALUE">Por valor</option>
            <option value="QUANTITY">Por quantidade</option>
            <option value="EQUAL">Igual</option>
          </select>
          <Button type="submit">Calcular versão</Button>
        </form>
        <Table>
          <thead>
            <tr>
              <th>v#</th>
              <th>Tipo</th>
              <th>Total</th>
              <th>Atual</th>
              <th>Trigger</th>
            </tr>
          </thead>
          <tbody>
            {lcVersions.map((v) => (
              <tr key={v.id}>
                <td>{v.version_number}</td>
                <td>{v.version_type}</td>
                <td className="num">{formatMoney(v.total_cost, "BRL")}</td>
                <td>{v.is_current_version ? "sim" : "—"}</td>
                <td>{v.trigger_event ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </>
  );
}
