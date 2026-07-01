import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  importationsApi,
  productsApi,
  type HeroesImportRunResponse,
  type OrderCentralResponse,
  type Product,
} from "../../api";
import { Badge, Button, EmptyState, LoadingState, useToast } from "../../components";
import { DEFAULT_IMPORT_CURRENCY } from "../../constants/currency";
import { productModelLabel } from "../../i18n/glossario";
import { ItalyOverrideModal, type ItalyOverrideTarget } from "./ItalyOverrideModal";
import { useOrderCentral } from "./OrderCentralContext";
import { OrderCentralDispatchPendingBlock } from "./OrderCentralDispatchPendingBlock";
import { OrderCentralModelsGrid, type ModelsGridHandlers } from "./OrderCentralModelsGrid";
import {
  computeOpSummary,
  EMPTY_ITEMS_FILTER,
  filterModels,
  type ItemsFilterState,
} from "./orderCentralItemsUtils";

interface Props {
  importationId: number;
}

function buildInvoiceItemIndex(data: OrderCentralResponse): Map<number, number> {
  const map = new Map<number, number>();
  for (const inv of data.invoices) {
    for (const ii of inv.items) {
      if (ii.importation_item_id != null) {
        map.set(ii.importation_item_id, ii.id);
      }
    }
  }
  return map;
}

export function OrderCentralItemsSection({ importationId }: Props) {
  const toast = useToast();
  const { data, loading, error, reloadCentral } = useOrderCentral();
  const [overrideTarget, setOverrideTarget] = useState<ItalyOverrideTarget | null>(null);
  const [heroesRun, setHeroesRun] = useState<HeroesImportRunResponse | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [filter, setFilter] = useState<ItemsFilterState>(EMPTY_ITEMS_FILTER);
  const [addingRow, setAddingRow] = useState(false);

  useEffect(() => {
    productsApi.list().then(setProducts).catch(() => undefined);
    importationsApi
      .heroesImportPreview(importationId)
      .then(setHeroesRun)
      .catch(() => setHeroesRun(null));
  }, [importationId]);

  const currency = data?.kpis.currency ?? DEFAULT_IMPORT_CURRENCY;
  const heroesOrder = Boolean(data?.legacy_sheet_summary);
  const dispatchPending = (data?.dispatch_pending ?? []) as Array<Record<string, unknown>>;
  const allModels = data?.models ?? [];
  const filteredModels = useMemo(() => filterModels(allModels, filter), [allModels, filter]);
  const opSummary = useMemo(() => computeOpSummary(allModels), [allModels]);

  const invoiceItemIndex = useMemo(
    () => (data ? buildInvoiceItemIndex(data) : new Map<number, number>()),
    [data],
  );

  const saveSku = useCallback(
    async (itemId: number, value: string) => {
      await importationsApi.updateItemMapping(importationId, itemId, { supplier_sku: value || null });
      await reloadCentral();
    },
    [importationId, reloadCentral],
  );

  const saveCategory = useCallback(
    async (productId: number | null, value: string) => {
      if (!productId) {
        toast.error("Vincule o produto Epic antes de definir o grupo.");
        throw new Error("Sem produto");
      }
      await productsApi.update(productId, { category: value });
      await reloadCentral();
    },
    [reloadCentral, toast],
  );

  const saveProduct = useCallback(
    async (itemId: number, product: Product | null) => {
      await importationsApi.updateItemMapping(importationId, itemId, {
        product_id: product?.id ?? null,
        supplier_sku: product?.supplier_code ?? undefined,
        description: product?.description ?? undefined,
      });
      await reloadCentral();
    },
    [importationId, reloadCentral],
  );

  const saveQty = useCallback(
    async (itemId: number, value: string) => {
      const n = value.trim() === "" ? null : Number(value);
      if (value.trim() !== "" && Number.isNaN(n)) throw new Error("Quantidade inválida");
      await importationsApi.updateItemMapping(importationId, itemId, {
        quantity_ordered: n != null ? n : null,
      });
      await reloadCentral();
    },
    [importationId, reloadCentral],
  );

  const saveUnitPrice = useCallback(
    async (itemId: number, value: string) => {
      await importationsApi.updateItemMapping(importationId, itemId, {
        unit_price_foreign: value.trim() === "" ? null : value.trim(),
      });
      await reloadCentral();
    },
    [importationId, reloadCentral],
  );

  const saveDiscount = useCallback(
    async (itemId: number, value: string) => {
      await importationsApi.updateItemMapping(importationId, itemId, {
        discount_amount_foreign: value.trim() === "" ? null : value.trim(),
      });
      await reloadCentral();
    },
    [importationId, reloadCentral],
  );

  const handlers: ModelsGridHandlers = useMemo(
    () => ({
      onSaveSku: saveSku,
      onSaveCategory: saveCategory,
      onSaveProduct: saveProduct,
      onSaveQty: saveQty,
      onSaveUnitPrice: saveUnitPrice,
      onSaveDiscount: saveDiscount,
      onItalyOverride: setOverrideTarget,
      findInvoiceItemId: (importationItemId) => invoiceItemIndex.get(importationItemId) ?? null,
    }),
    [saveSku, saveCategory, saveProduct, saveQty, saveUnitPrice, saveDiscount, invoiceItemIndex],
  );

  async function addManualRow() {
    setAddingRow(true);
    try {
      await importationsApi.addItem(importationId, {
        description: "Novo item",
        quantity_ordered: null,
        unit_price_foreign: null,
      });
      toast.success("Linha adicionada");
      await reloadCentral();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Não foi possível adicionar item");
    } finally {
      setAddingRow(false);
    }
  }

  function toggleFilter(key: keyof Omit<ItemsFilterState, "search">) {
    setFilter((f) => ({ ...f, [key]: !f[key] }));
  }

  if (loading) return <LoadingState label="Carregando produtos e quantidades..." />;
  if (error) return <p className="error">{error}</p>;
  if (!data) return <LoadingState label="Carregando..." />;

  if (allModels.length === 0 && dispatchPending.length === 0) {
    return (
      <EmptyState
        title="Sem itens nesta ordem"
        description={
          heroesOrder
            ? "Importe a planilha Heroes ou vincule SKUs na fila de revisão."
            : "Adicione itens manualmente ou importe via Heroes."
        }
        action={
          !heroesOrder ? (
            <Button onClick={addManualRow} disabled={addingRow}>
              + Adicionar item
            </Button>
          ) : undefined
        }
      />
    );
  }

  return (
    <div className="oc-items-section">
      {heroesRun && heroesRun.sku_review_open_count > 0 && (
        <p className="oc-items-section__banner meta">
          <Badge tone="warning">{heroesRun.sku_review_open_count} SKU(s) pendente(s)</Badge>
          {" — "}
          <Link to={`/revisao?heroes_run_id=${heroesRun.run_id}`}>Abrir fila de revisão</Link>
        </p>
      )}

      <div className="oc-items-summary">
        <div className="oc-items-summary__card">
          <span className="oc-items-summary__label">Pedida</span>
          <strong>{opSummary.ordered}</strong>
        </div>
        <div className="oc-items-summary__card">
          <span className="oc-items-summary__label">Faturada</span>
          <strong>{opSummary.invoiced}</strong>
        </div>
        <div className="oc-items-summary__card">
          <span className="oc-items-summary__label">Despachada</span>
          <strong>{opSummary.shipped}</strong>
        </div>
        <div className="oc-items-summary__card oc-items-summary__card--warn">
          <span className="oc-items-summary__label">A despachar</span>
          <strong>{opSummary.toDispatch}</strong>
        </div>
      </div>

      <div className="oc-items-toolbar">
        <input
          className="input oc-items-toolbar__search"
          placeholder="Buscar modelo, SKU Epic ou fornecedor…"
          value={filter.search}
          onChange={(e) => setFilter((f) => ({ ...f, search: e.target.value }))}
        />
        <div className="oc-items-toolbar__chips">
          <button
            type="button"
            className={`oc-items-chip${filter.toDispatch ? " oc-items-chip--active" : ""}`}
            onClick={() => toggleFilter("toDispatch")}
          >
            A despachar
          </button>
          <button
            type="button"
            className={`oc-items-chip${filter.unmapped ? " oc-items-chip--active" : ""}`}
            onClick={() => toggleFilter("unmapped")}
          >
            Sem vínculo
          </button>
          <button
            type="button"
            className={`oc-items-chip${filter.needsReview ? " oc-items-chip--active" : ""}`}
            onClick={() => toggleFilter("needsReview")}
          >
            Revisão Heroes
          </button>
        </div>
        {!heroesOrder && (
          <Button variant="secondary" className="ui-btn--sm" onClick={addManualRow} disabled={addingRow}>
            + Adicionar item
          </Button>
        )}
      </div>

      <OrderCentralDispatchPendingBlock rows={dispatchPending} currency={currency} />

      <div className="oc-section">
        <div className="oc-section__head">
          <h3>
            Por {productModelLabel().toLowerCase()} · quantidades e preços
          </h3>
          <span className="oc-section__count">
            {filteredModels.length} de {allModels.length}
          </span>
        </div>
        <OrderCentralModelsGrid
          models={filteredModels}
          currency={currency}
          products={products}
          heroesOrder={heroesOrder}
          handlers={handlers}
        />
      </div>

      <ItalyOverrideModal
        importationId={importationId}
        target={overrideTarget}
        onClose={() => setOverrideTarget(null)}
        onSaved={() => reloadCentral()}
      />
    </div>
  );
}
