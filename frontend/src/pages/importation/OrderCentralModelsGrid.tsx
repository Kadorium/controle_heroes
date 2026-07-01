import { Link } from "react-router-dom";
import type { OrderCentralModel, Product } from "../../api";
import { Badge, EditableCell, ProductCombobox } from "../../components";
import {
  emptyDash,
  formatMoney,
  productCategoryLabel,
  productModelLabel,
} from "../../i18n/glossario";
import type { ItalyOverrideTarget } from "./ItalyOverrideModal";
import { CATEGORY_OPTIONS, heroesCell, LockedCell } from "./orderCentralItemsShared";
import { modelLineValue, summarizeModels } from "./orderCentralItemsUtils";

export interface ModelsGridHandlers {
  onSaveSku: (itemId: number, value: string) => Promise<void>;
  onSaveCategory: (productId: number | null, value: string) => Promise<void>;
  onSaveProduct: (itemId: number, product: Product | null) => Promise<void>;
  onSaveQty: (itemId: number, value: string) => Promise<void>;
  onSaveUnitPrice: (itemId: number, value: string) => Promise<void>;
  onSaveDiscount: (itemId: number, value: string) => Promise<void>;
  onItalyOverride: (target: ItalyOverrideTarget) => void;
  findInvoiceItemId: (importationItemId: number) => number | null;
}

interface Props {
  models: OrderCentralModel[];
  currency: string;
  products: Product[];
  heroesOrder: boolean;
  handlers: ModelsGridHandlers;
}

export function OrderCentralModelsGrid({
  models,
  currency,
  products,
  heroesOrder,
  handlers,
}: Props) {
  const totals = summarizeModels(models);

  if (models.length === 0) {
    return <p className="meta">Nenhum item corresponde aos filtros.</p>;
  }

  return (
    <div className="sheet-grid-wrap">
      <table className="sheet-grid oc-items-grid">
        <thead>
          <tr>
            <th className="sticky-col">{productModelLabel()}</th>
            <th>SKU Epic</th>
            <th>SKU fornecedor</th>
            <th>Grupo</th>
            <th className="num">A despachar</th>
            <th className="num">Pedida</th>
            <th className="num">Faturada</th>
            <th className="num">Despachada</th>
            <th className="num">Nac./receb.</th>
            <th>Progresso</th>
            <th className="num">Preço listino</th>
            <th className="num">Preço fattura</th>
            <th className="num">Sconto</th>
            <th className="num">Valor</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => {
            const ordered = m.quantity_ordered ?? 0;
            const shipped = m.quantity_shipped ?? 0;
            const pct = ordered > 0 ? Math.round((shipped / ordered) * 100) : 0;
            const highlight = (m.to_dispatch ?? 0) > 0;
            const lineVal = modelLineValue(m);
            const invoiceItemId = handlers.findInvoiceItemId(m.importation_item_id);
            const qtyLocked = m.heroes_source || heroesOrder;

            return (
              <tr key={m.importation_item_id} className={highlight ? "sheet-row--dispatch" : ""}>
                <td className="sticky-col">
                  <b>
                    {m.model_label ?? m.description ?? m.supplier_sku ?? `Item #${m.importation_item_id}`}
                  </b>
                </td>
                <td className="oc-items-grid__sku-epic">
                  {m.product_id && m.product_sku ? (
                    <Link to={`/cadastros/produtos/${m.product_id}`} className="oc-items-grid__product-link">
                      {m.product_sku}
                    </Link>
                  ) : (
                    <Badge tone="warning">Sem vínculo</Badge>
                  )}
                  <div className="oc-items-grid__product-picker">
                    <ProductCombobox
                      products={products}
                      value={m.product_sku ?? m.supplier_sku ?? ""}
                      productId={m.product_id}
                      onChange={({ product }) => handlers.onSaveProduct(m.importation_item_id, product)}
                      placeholder="Vincular produto…"
                    />
                  </div>
                </td>
                <td>
                  <EditableCell
                    value={m.supplier_sku ?? ""}
                    onSave={(v) => handlers.onSaveSku(m.importation_item_id, v)}
                    placeholder="—"
                  />
                </td>
                <td>
                  <EditableCell
                    type="select"
                    options={CATEGORY_OPTIONS}
                    value={m.product_category ?? ""}
                    display={m.product_category ? productCategoryLabel(m.product_category) : undefined}
                    editable={!!m.product_id}
                    lockedReason={
                      !m.product_id ? "Vincule o produto Epic antes de definir o grupo." : undefined
                    }
                    onSave={(v) => handlers.onSaveCategory(m.product_id, v)}
                  />
                </td>
                <td className={`num${highlight ? " sheet-warn" : ""}`}>
                  {m.to_dispatch ?? emptyDash(null)}
                </td>
                <td className="num">
                  {qtyLocked ? (
                    <LockedCell
                      onOverride={
                        invoiceItemId
                          ? () =>
                              handlers.onItalyOverride({
                                entityType: "invoice_item",
                                entityId: invoiceItemId,
                                fieldName: "quantity",
                                fieldLabel: "Quantidade (invoice item)",
                                currentValue: String(m.quantity_ordered ?? ""),
                              })
                          : undefined
                      }
                      title={
                        invoiceItemId
                          ? undefined
                          : "Sem linha de fatura vinculada — não é possível override"
                      }
                    >
                      {m.quantity_ordered ?? emptyDash(null)}
                    </LockedCell>
                  ) : (
                    <EditableCell
                      value={m.quantity_ordered != null ? String(m.quantity_ordered) : ""}
                      onSave={(v) => handlers.onSaveQty(m.importation_item_id, v)}
                      placeholder="—"
                    />
                  )}
                </td>
                <td className="num">{m.quantity_invoiced ?? emptyDash(null)}</td>
                <td className="num">{m.quantity_shipped ?? emptyDash(null)}</td>
                <td className="num">{m.quantity_stocked ?? m.quantity_nationalized ?? emptyDash(null)}</td>
                <td>
                  <div className="sheet-prog">
                    <div className="sheet-prog__track">
                      <div className="sheet-prog__fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="sheet-prog__pct">{pct}%</span>
                  </div>
                </td>
                <td className="num">
                  {heroesCell(
                    m.price_listino ? formatMoney(m.price_listino, currency) : null,
                    m.heroes_source,
                  )}
                </td>
                <td className="num">
                  {m.heroes_source ? (
                    heroesCell(
                      m.price_fattura ? formatMoney(m.price_fattura, currency) : null,
                      true,
                    )
                  ) : (
                    <EditableCell
                      value={m.price_fattura ?? ""}
                      onSave={(v) => handlers.onSaveUnitPrice(m.importation_item_id, v)}
                      placeholder="—"
                    />
                  )}
                </td>
                <td className="num c-credito">
                  {heroesCell(
                    m.discount_unit ? formatMoney(m.discount_unit, currency) : null,
                    m.heroes_source,
                  )}
                </td>
                <td className="num">{formatMoney(lineVal, currency)}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="oc-items-grid__total">
            <td colSpan={5}>
              <strong>Total</strong>
            </td>
            <td className="num">
              <strong>{totals.qty ?? emptyDash(null)}</strong>
            </td>
            <td colSpan={7} />
            <td className="num">
              <strong>{formatMoney(totals.value, currency)}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
