import { useState } from "react";
import { Button, Card, Table } from "../../../../components";
import type { EntrepostoMovement } from "../../../../api";
import { qtyCell, type SkuRow } from "../logisticsUtils";

interface Props {
  importationId: number;
  rows: SkuRow[];
  movements: EntrepostoMovement[];
  onCreate: (data: object) => Promise<void>;
}

export function EntrepostoSection({ importationId, rows, movements, onCreate }: Props) {
  const [movementType, setMovementType] = useState("RECEIPT");
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [notes, setNotes] = useState("");

  const eligibleReceipt = rows.filter(
    (r) => (r.quantity_shipped ?? 0) > 0 && (r.quantity_entreposto_balance ?? 0) >= 0,
  );
  const eligibleConsumption = rows.filter((r) => (r.quantity_entreposto_balance ?? 0) > 0);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!itemId || !quantity) return;
    await onCreate({
      importation_id: importationId,
      importation_item_id: Number(itemId),
      movement_type: movementType,
      quantity: Number(quantity),
      notes: notes || null,
    });
    setQuantity("");
    setNotes("");
  }

  const labelFor = (id: number) => rows.find((r) => r.importation_item_id === id)?.label ?? `#${id}`;

  return (
    <Card id="entreposto" title="Entreposto" compact className="stacked-section logistics-phase">
      <p className="meta logistics-entreposto-note">
        Mercadoria no Brasil, ainda não nacionalizada. Consumo no entreposto não entra no estoque Epic.
      </p>
      <form className="inline-form" onSubmit={submit}>
        <select value={movementType} onChange={(e) => setMovementType(e.target.value)}>
          <option value="RECEIPT">Entrada no entreposto</option>
          <option value="CONSUMPTION">Uso no entreposto</option>
        </select>
        <select value={itemId} onChange={(e) => setItemId(e.target.value)} required>
          <option value="">SKU…</option>
          {(movementType === "RECEIPT" ? eligibleReceipt : eligibleConsumption).map((r) => (
            <option key={r.importation_item_id} value={r.importation_item_id}>
              {r.label}
            </option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          placeholder="Quantidade"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          required
        />
        <input placeholder="Notas" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Button type="submit">Registrar</Button>
      </form>
      <Table>
        <thead>
          <tr>
            <th>Data</th>
            <th>Tipo</th>
            <th>SKU</th>
            <th className="num">Qtd</th>
            <th>Notas</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((m) => (
            <tr key={m.id}>
              <td>{m.event_date ?? "—"}</td>
              <td>{m.movement_type === "RECEIPT" ? "Entrada" : "Consumo"}</td>
              <td>{labelFor(m.importation_item_id)}</td>
              <td className="num">{qtyCell(m.quantity)}</td>
              <td>{m.notes ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}
