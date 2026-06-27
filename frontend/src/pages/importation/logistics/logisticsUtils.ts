import type { OrderCentralModel, QuantityChain, ShipmentItem } from "../../../api";

export interface SkuRow {
  importation_item_id: number;
  label: string;
  quantity_ordered: number | null;
  quantity_invoiced: number | null;
  to_dispatch: number | null;
  quantity_shipped: number | null;
  quantity_entreposto_balance: number | null;
  quantity_entreposto_consumed: number | null;
  quantity_nationalized: number | null;
  quantity_stocked: number | null;
}

export function skuLabel(m: OrderCentralModel): string {
  return m.model_label || m.supplier_sku || m.product_sku || m.description || `#${m.importation_item_id}`;
}

export function buildSkuRows(models: OrderCentralModel[], chain: QuantityChain[]): SkuRow[] {
  const chainMap = new Map(chain.map((c) => [c.importation_item_id, c]));
  if (models.length === 0 && chain.length > 0) {
    return chain.map((c) => ({
      importation_item_id: c.importation_item_id,
      label: `#${c.importation_item_id}`,
      quantity_ordered: c.quantity_ordered,
      quantity_invoiced: null,
      to_dispatch: null,
      quantity_shipped: c.quantity_shipped,
      quantity_entreposto_balance: c.quantity_entreposto_balance,
      quantity_entreposto_consumed: c.quantity_entreposto_consumed,
      quantity_nationalized: c.quantity_nationalized,
      quantity_stocked: c.quantity_stocked,
    }));
  }
  return models.map((m) => {
    const c = chainMap.get(m.importation_item_id);
    return {
      importation_item_id: m.importation_item_id,
      label: skuLabel(m),
      quantity_ordered: m.quantity_ordered ?? c?.quantity_ordered ?? null,
      quantity_invoiced: m.quantity_invoiced ?? null,
      to_dispatch: m.to_dispatch ?? null,
      quantity_shipped: c?.quantity_shipped ?? m.quantity_shipped ?? null,
      quantity_entreposto_balance: c?.quantity_entreposto_balance ?? null,
      quantity_entreposto_consumed: c?.quantity_entreposto_consumed ?? null,
      quantity_nationalized: c?.quantity_nationalized ?? m.quantity_nationalized ?? null,
      quantity_stocked: c?.quantity_stocked ?? m.quantity_stocked ?? null,
    };
  });
}

export function qtyCell(v: number | null | undefined): string {
  if (v == null) return "—";
  return String(v);
}

export function itemsForShipment(
  shipmentId: number,
  itemsByShipment: Record<number, ShipmentItem[]>,
): ShipmentItem[] {
  return itemsByShipment[shipmentId] ?? [];
}
