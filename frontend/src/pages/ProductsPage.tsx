import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Badge, Button, Card, EmptyState, LoadingState, PageHeader, Table, useToast } from "../components";
import { productsApi, type Product } from "../api";
import { ProductBulkActionBar } from "./products/ProductBulkActionBar";
import { ProductBulkConfirmModal } from "./products/ProductBulkConfirmModal";
import { ProductImportModal } from "./products/ProductImportModal";
import { ProductQuickDrawer } from "./products/ProductQuickDrawer";
import { useProductSelection } from "./products/useProductSelection";
import {
  exportProductsCsv,
  formatBulkResult,
  PENDING_LABELS,
  STATUS_LABELS,
  sortProducts,
  type BulkAction,
  type QuickFilter,
  type Visibility,
} from "./products/productCatalogUtils";

const QUICK_FILTERS: { id: QuickFilter; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "ncm_pending", label: "NCM pendente" },
  { id: "no_photo", label: "Sem foto" },
  { id: "no_weight_volume", label: "Sem peso/volume" },
  { id: "no_supplier", label: "Sem fornecedor" },
  { id: "fiscal_review", label: "Fiscal a revisar" },
  { id: "discontinued", label: "Descontinuados" },
];

const VISIBILITY_OPTIONS: { id: Visibility; label: string }[] = [
  { id: "active", label: "Operacionais" },
  { id: "archived", label: "Arquivados" },
  { id: "cancelled", label: "Anulados" },
  { id: "all", label: "Todos" },
];

type SortKey = "sku_code" | "description" | "product_group" | "lifecycle_status" | "ncm";

function sortMark(active: boolean, asc: boolean): string {
  if (!active) return "";
  return asc ? " ▲" : " ▼";
}

export function ProductsPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [visibility, setVisibility] = useState<Visibility>("active");
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("sku_code");
  const [sortAsc, setSortAsc] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [bulkAction, setBulkAction] = useState<BulkAction | null>(null);
  const [bulkReason, setBulkReason] = useState("");
  const [bulkLoading, setBulkLoading] = useState(false);

  const selection = useProductSelection(rows);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await productsApi.catalog({
        q: search.trim() || undefined,
        visibility,
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
  }, [search, visibility, quickFilter, sortKey, sortAsc]);

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
      const blob = await productsApi.exportBlob("xlsx", visibility);
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

  return (
    <Card>
      <PageHeader
        title="Produtos"
        actions={
          <>
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
        <div className="order-queue__filters">
          {VISIBILITY_OPTIONS.map((v) => (
            <button
              key={v.id}
              type="button"
              className={`chip-btn${visibility === v.id ? " chip-btn--active" : ""}`}
              onClick={() => setVisibility(v.id)}
            >
              {v.label}
            </button>
          ))}
        </div>
        <p className="meta">
          {displayed.length} de {total} produto(s)
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
                <th>Foto</th>
                <th>
                  <button type="button" className="th-sort" onClick={() => toggleSort("sku_code")}>
                    SKU{sortMark(sortKey === "sku_code", sortAsc)}
                  </button>
                </th>
                <th>Cód. fornecedor</th>
                <th>
                  <button type="button" className="th-sort" onClick={() => toggleSort("description")}>
                    Nome{sortMark(sortKey === "description", sortAsc)}
                  </button>
                </th>
                <th>
                  <button type="button" className="th-sort" onClick={() => toggleSort("product_group")}>
                    Grupo{sortMark(sortKey === "product_group", sortAsc)}
                  </button>
                </th>
                <th>
                  <button type="button" className="th-sort" onClick={() => toggleSort("lifecycle_status")}>
                    Status{sortMark(sortKey === "lifecycle_status", sortAsc)}
                  </button>
                </th>
                <th>
                  <button type="button" className="th-sort" onClick={() => toggleSort("ncm")}>
                    NCM{sortMark(sortKey === "ncm", sortAsc)}
                  </button>
                </th>
                <th>Fornecedor</th>
                <th>Pendências</th>
                <th>Ordens</th>
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
                  <td>
                    {p.photo_attachment_id ? (
                      <img
                        className="product-thumb"
                        src={`/api/documents/${p.photo_attachment_id}/download`}
                        alt=""
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    <Link
                      to={`/cadastros/produtos/${p.id}`}
                      className="link-btn"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {p.sku_code}
                    </Link>
                  </td>
                  <td>{p.supplier_code ?? "—"}</td>
                  <td>{p.description}</td>
                  <td>{p.product_group ?? "—"}</td>
                  <td>{STATUS_LABELS[p.lifecycle_status ?? "ACTIVE"] ?? p.lifecycle_status}</td>
                  <td>{p.ncm ?? "—"}</td>
                  <td>{p.default_supplier_name ?? "—"}</td>
                  <td>
                    <div className="chip-row">
                      {(p.pending_flags ?? []).map((f) => (
                        <Badge key={f} tone="warning">
                          {PENDING_LABELS[f] ?? f}
                        </Badge>
                      ))}
                    </div>
                  </td>
                  <td className="num">{p.orders_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

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
