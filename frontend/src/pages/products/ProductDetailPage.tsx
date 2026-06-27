import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Badge, Card, LoadingState, useToast } from "../../components";
import { productsApi, type Product, type ProductAuditRow, type ProductOrderRow } from "../../api";
import { PENDING_LABELS, STATUS_LABELS } from "./productCatalogUtils";
import { CommercialTab } from "./ProductDetailTabs/CommercialTab";
import { CostsTab } from "./ProductDetailTabs/CostsTab";
import { FiscalCustomsTab } from "./ProductDetailTabs/FiscalCustomsTab";
import { HistoryAuditTab } from "./ProductDetailTabs/HistoryAuditTab";
import { IdentificationTab } from "./ProductDetailTabs/IdentificationTab";
import { ImportOrdersTab } from "./ProductDetailTabs/ImportOrdersTab";
import { LogisticsTab } from "./ProductDetailTabs/LogisticsTab";
import { PhotosDocumentsTab } from "./ProductDetailTabs/PhotosDocumentsTab";
import { SuppliersTab } from "./ProductDetailTabs/SuppliersTab";

const TABS = [
  { id: "identification", label: "Identificação" },
  { id: "commercial", label: "Comercial" },
  { id: "fiscal", label: "Fiscal/Aduaneiro" },
  { id: "logistics", label: "Logística/Embalagem" },
  { id: "suppliers", label: "Fornecedores/Compras" },
  { id: "orders", label: "Ordens de importação" },
  { id: "costs", label: "Custos" },
  { id: "photos", label: "Fotos/Documentos" },
  { id: "history", label: "Histórico/Auditoria" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function ProductDetailPage() {
  const { productId } = useParams();
  const id = Number(productId);
  const navigate = useNavigate();
  const toast = useToast();
  const [tab, setTab] = useState<TabId>("identification");
  const [product, setProduct] = useState<Product | null>(null);
  const [orders, setOrders] = useState<ProductOrderRow[]>([]);
  const [audit, setAudit] = useState<ProductAuditRow[]>([]);
  const [orderSearch, setOrderSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState("");

  async function load() {
    if (!id) return;
    setLoading(true);
    try {
      const [detail, ord, aud] = await Promise.all([
        productsApi.detail(id),
        productsApi.orders(id, { q: orderSearch || undefined }),
        productsApi.audit(id),
      ]);
      setProduct(detail);
      setOrders(ord.items);
      setAudit(aud);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro ao carregar produto");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [id, orderSearch]);

  async function savePatch(data: object) {
    if (!product) return;
    try {
      await productsApi.update(product.id, data);
      toast.success("Salvo");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Erro");
    }
  }

  async function archive() {
    if (!product || reason.trim().length < 3) {
      toast.error("Informe motivo (mín. 3 caracteres)");
      return;
    }
    await productsApi.archive(product.id, reason.trim());
    toast.success("Arquivado");
    navigate("/cadastros/produtos");
  }

  async function restore() {
    if (!product) return;
    await productsApi.restore(product.id);
    toast.success("Restaurado");
    await load();
  }

  async function cancelProduct() {
    if (!product || reason.trim().length < 3) {
      toast.error("Informe motivo (mín. 3 caracteres)");
      return;
    }
    await productsApi.cancel(product.id, reason.trim());
    toast.success("Produto anulado");
    navigate("/cadastros/produtos");
  }

  if (loading || !product) {
    return (
      <Card>
        <LoadingState />
      </Card>
    );
  }

  return (
    <Card className="product-detail">
      <div className="product-detail__header">
        <div>
          <Link to="/cadastros/produtos" className="link-btn">
            ← Produtos
          </Link>
          <h1>{product.sku_code}</h1>
          <p>{product.description}</p>
          <div className="chip-row">
            <Badge>{STATUS_LABELS[product.lifecycle_status ?? "ACTIVE"]}</Badge>
            {(product.pending_flags ?? []).map((f) => (
              <Badge key={f} tone="warning">
                {PENDING_LABELS[f] ?? f}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      <nav className="tab-row">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`tab-btn${tab === t.id ? " tab-btn--active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "identification" && (
        <IdentificationTab
          product={product}
          onSave={savePatch}
          onArchive={() => void archive()}
          onRestore={() => void restore()}
          onCancel={() => void cancelProduct()}
          reason={reason}
          onReasonChange={setReason}
        />
      )}
      {tab === "commercial" && <CommercialTab product={product} onSave={savePatch} />}
      {tab === "fiscal" && <FiscalCustomsTab product={product} onSave={savePatch} />}
      {tab === "logistics" && <LogisticsTab product={product} onSave={savePatch} />}
      {tab === "suppliers" && <SuppliersTab product={product} onSave={savePatch} />}
      {tab === "orders" && (
        <ImportOrdersTab orders={orders} orderSearch={orderSearch} onOrderSearchChange={setOrderSearch} />
      )}
      {tab === "costs" && <CostsTab productId={product.id} lastUnit={product.last_landed_cost_unit} />}
      {tab === "photos" && <PhotosDocumentsTab productId={product.id} onUploaded={() => void load()} />}
      {tab === "history" && <HistoryAuditTab audit={audit} />}
    </Card>
  );
}
