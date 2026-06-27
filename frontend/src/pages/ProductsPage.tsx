import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Badge, Button, Card, EmptyState, LoadingState, PageHeader, Table, useToast } from "../components";
import { useAuth } from "../context/AuthContext";
import { productsApi, type Product } from "../api";
import { ProductBulkActionBar } from "./products/ProductBulkActionBar";
import { ProductBulkConfirmModal } from "./products/ProductBulkConfirmModal";
import { ProductColumnPicker } from "./products/ProductColumnPicker";
import { ProductImportModal } from "./products/ProductImportModal";
import { ProductQuickDrawer } from "./products/ProductQuickDrawer";
import { useProductSelection } from "./products/useProductSelection";
import {
  loadVisibleColumns,
  PRODUCT_COLUMN_LABELS,
  saveVisibleColumns,
  type ProductColumnId,
} from "./products/productColumnPrefs";
import {
  exportProductsCsv,
  formatBulkResult,
  PENDING_LABELS,
  STATUS_LABELS,
  sortProducts,
  type BulkAction,
  type QuickFilter,
} from "./products/productCatalogUtils";

const QUICK_FILTERS: { id: QuickFilter; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "ncm_pending", label: "NCM pendente" },
  { id: "no_photo", label: "Sem foto" },
  { id: "no_weight_volume", label: "Sem peso/volume" },
  { id: "no_supplier", label: "Sem fornecedor" },
  { id: "fiscal_review", label: "Fiscal a revisar" },
];

type SortKey = "sku_code" | "description" | "product_group" | "lifecycle_status" | "ncm";

const SORTABLE_COLUMNS: Partial<Record<ProductColumnId, SortKey>> = {
  sku: "sku_code",
  name: "description",
  group: "product_group",
  status: "lifecycle_status",
  ncm: "ncm",
};

function sortMark(active: boolean, asc: boolean): string {
  if (!active) return "";
  return asc ? " ▲" : " ▼";
}

function formatLaunchDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString("pt-BR");
}

function formatQty(value: number | null | undefined): string {
  if (value == null || value === 0) return "—";
  return String(value);
}

export function ProductsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const [rows, setRows] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [productGroup, setProductGroup] = useState("");
  const [groups, setGroups] = useState<string[]>([]);
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("sku_code");
  const [sortAsc, setSortAsc] = useState(true);
  const [visibleColumns, setVisibleColumns] = useState<ProductColumnId[]>(() =>
    loadVisibleColumns(user?.id),
  );
  const [columnPickerOpen, setColumnPickerOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [bulkAction, setBulkAction] = useState<BulkAction | null>(null);
  const [bulkReason, setBulkReason] = useState("");
  const [bulkLoading, setBulkLoading] = useState(false);

  const selection = useProductSelection(rows);

  useEffect(() => {
    setVisibleColumns(loadVisibleColumns(user?.id));
  }, [user?.id]);

  useEffect(() => {
    void productsApi.groups().then(setGroups).catch(() => setGroups([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await productsApi.catalog({
        q: search.trim() || undefined,
        visibility: "active",
        product_group: productGroup || undefined,
        quick_filter: quickFilter === "all" ? undefined : quickFilter,
        sort: sortKey,
        sort_dir: sortAsc ? "asc" : "desc",
        limit: 500,
      });
      setRows(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar produtos");
    } finally {
      setLoading(false);
    }
  }, [search, productGroup, quickFilter, sortKey, sortAsc]);

  useEffect(() => {
    void load();
  }, [load]);

  const displayed = useMemo(() => sortProducts(rows, sortKey, sortAsc), [rows, sortKey, sortAsc]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((v) => !v);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  }

  function openDrawer(product: Product | null) {
    setSelected(product);
    setDrawerOpen(true);
  }

  function updateColumns(cols: ProductColumnId[]) {
    setVisibleColumns(cols);
    saveVisibleColumns(user?.id, cols);
  }

  async function runBulkConfirm() {
    if (!bulkAction) return;
    const { eligible } = selection.eligibleFor(bulkAction);
    if (eligible.length === 0) return;

    if (bulkAction === "export") {
      exportProductsCsv(eligible);
      toast.success(`${eligible.length} produto(s) exportado(s)`);
      setBulkAction(null);
      selection.clear();
      return;
    }

    setBulkLoading(true);
    try {
      const ids = eligible.map((p) => p.id);
      let result;
      if (bulkAction === "archive") result = await productsApi.bulkArchive(ids, bulkReason.trim());
      else if (bulkAction === "restore") result = await productsApi.bulkRestore(ids);
      else if (bulkAction === "discontinue") result = await productsApi.bulkStatus(ids, "DISCONTINUED");
      else if (bulkAction === "reactivate") result = await productsApi.bulkStatus(ids, "ACTIVE");
      else if (bulkAction === "cancel") result = await productsApi.bulkCancel(ids, bulkReason.trim());
      else return;

      toast.success(formatBulkResult(result));
      selection.clear();
      setBulkAction(null);
      setBulkReason("");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro na ação em massa");
    } finally {
      setBulkLoading(false);
    }
  }

  async function exportXlsx() {
    try {
      const blob = await productsApi.exportBlob("xlsx", "active");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `produtos-${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro ao exportar");
    }
  }

  const bulkEligible = bulkAction ? selection.eligibleFor(bulkAction) : { eligible: [], ineligible: [] };

  function renderHeader(col: ProductColumnId) {
    const sortField = SORTABLE_COLUMNS[col];
    if (sortField) {
      return (
        <button type="button" className="th-sort" onClick={() => toggleSort(sortField)}>
          {PRODUCT_COLUMN_LABELS[col]}
          {sortMark(sortKey === sortField, sortAsc)}
        </button>
      );
    }
    return PRODUCT_COLUMN_LABELS[col];
  }

  function renderCell(col: ProductColumnId, p: Product) {
    switch (col) {
      case "photo":
        return p.photo_attachment_id ? (
          <img
            className="product-thumb"
            src={`/api/documents/${p.photo_attachment_id}/download`}
            alt=""
          />
        ) : (
          "—"
        );
      case "sku":
        return (
          <Link
            to={`/cadastros/produtos/${p.id}`}
            className="link-btn"
            onClick={(e) => e.stopPropagation()}
          >
            {p.sku_code}
          </Link>
        );
      case "supplier_code":
        return p.supplier_code ?? "—";
      case "name":
        return p.description;
      case "group":
        return p.product_group ?? "—";
      case "subgroup":
        return p.product_subgroup ?? "—";
      case "status":
        return STATUS_LABELS[p.lifecycle_status ?? "ACTIVE"] ?? p.lifecycle_status;
      case "ncm":
        return p.ncm ?? "—";
      case "supplier":
        return p.default_supplier_name ?? "—";
      case "launch_date":
        return formatLaunchDate(p.launch_date);
      case "pending":
        return (
          <div className="chip-row">
            {(p.pending_flags ?? []).map((f) => (
              <Badge key={f} tone="warning">
                {PENDING_LABELS[f] ?? f}
              </Badge>
            ))}
          </div>
        );
      case "orders":
        return <span className="num">{p.orders_count ?? 0}</span>;
      case "qty_ordered":
        return <span className="num">{formatQty(p.qty_ordered)}</span>;
      case "qty_in_transit":
        return <span className="num">{formatQty(p.qty_in_transit)}</span>;
      case "qty_nationalization":
        return <span className="num">{formatQty(p.qty_nationalization)}</span>;
      case "qty_stock":
        return <span className="num">{formatQty(p.qty_stock)}</span>;
      default:
        return "—";
    }
  }

  return (
    <Card>
      <PageHeader
        title="Produtos"
        actions={
          <>
            <Button variant="secondary" onClick={() => setColumnPickerOpen(true)}>
              Colunas
            </Button>
            <Button onClick={() => openDrawer(null)}>Novo produto</Button>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              Importar
            </Button>
            <Button variant="secondary" onClick={() => exportProductsCsv(displayed)}>
              Exportar CSV
            </Button>
            <Button variant="secondary" onClick={() => void exportXlsx()}>
              Exportar XLSX
            </Button>
          </>
        }
      />

      {error && <p className="error">{error}</p>}

      <div className="sheet-toolbar">
        <input
          className="search-input"
          placeholder="Buscar SKU, nome, NCM, código fornecedor…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="order-queue__filters">
          {QUICK_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              className={`chip-btn${quickFilter === f.id ? " chip-btn--active" : ""}`}
              onClick={() => setQuickFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="sheet-toolbar__row">
          <label className="sheet-toolbar__field">
            Grupo
            <select
              className="sheet-toolbar__select"
              value={productGroup}
              onChange={(e) => setProductGroup(e.target.value)}
            >
              <option value="">Todos</option>
              {groups.map((g) => (
                <option key={g} value={g}>
                  {g}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="meta">
          {displayed.length} de {total} produto(s) ativos
          {productGroup ? ` · ${productGroup}` : ""}
        </p>
      </div>

      <ProductBulkActionBar
        count={selection.count}
        onAction={(action) => setBulkAction(action)}
        canRun={(action) => selection.eligibleFor(action).eligible.length > 0}
      />

      {loading ? (
        <LoadingState />
      ) : displayed.length === 0 ? (
        <EmptyState title="Nenhum produto encontrado" />
      ) : (
        <div className="table-scroll">
          <Table className="table-dense">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={selection.allVisibleSelected}
                    onChange={() => selection.toggleAllVisible()}
                    aria-label="Selecionar todos"
                  />
                </th>
                {visibleColumns.map((col) => (
                  <th key={col}>{renderHeader(col)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.map((p) => (
                <tr
                  key={p.id}
                  className="table-row--clickable"
                  onClick={() => openDrawer(p)}
                  title="Clique para editar"
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selection.selectedIds.has(p.id)}
                      onChange={() => selection.toggle(p.id)}
                      aria-label={`Selecionar ${p.sku_code}`}
                    />
                  </td>
                  {visibleColumns.map((col) => (
                    <td key={col}>{renderCell(col, p)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <ProductColumnPicker
        open={columnPickerOpen}
        visible={visibleColumns}
        onChange={updateColumns}
        onClose={() => setColumnPickerOpen(false)}
      />

      <ProductQuickDrawer
        open={drawerOpen}
        product={selected}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => {
          toast.success("Produto salvo");
          void load();
        }}
        onOpenDetail={(id) => navigate(`/cadastros/produtos/${id}`)}
      />

      <ProductImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onDone={() => {
          toast.success("Importação concluída");
          void load();
        }}
      />

      {bulkAction && (
        <ProductBulkConfirmModal
          action={bulkAction}
          eligible={bulkEligible.eligible}
          ineligible={bulkEligible.ineligible}
          reason={bulkReason}
          onReasonChange={setBulkReason}
          onConfirm={() => void runBulkConfirm()}
          onCancel={() => {
            setBulkAction(null);
            setBulkReason("");
          }}
          loading={bulkLoading}
        />
      )}
    </Card>
  );
}
