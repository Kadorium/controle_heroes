import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, LoadingState } from "../../components";
import {
  closureApi,
  customsApi,
  documentsApi,
  financeApi,
  importationsApi,
  invoicesApi,
  landedCostApi,
  reconciliationApi,
  shipmentsApi,
  stockApi,
  suppliersApi,
  type DocumentAttachment,
  type FinancialSummary,
  type Importation,
  type ImportationItem,
  type Invoice,
  type Payment,
} from "../../api";
import { emptyDash, modalLabel, statusLabel } from "../../i18n/glossario";
import { fmtDate } from "../../utils/formatDate";
import { IMPORTATION_SIDEBAR_GROUPS, type ImportationOutletContext } from "./types";

const RAIL_STAGES = [
  { key: "pedido", label: "Pedido", statuses: ["PO_CREATED", "SI_OPEN", "PROFORMA_RECEIVED"] },
  { key: "faturado", label: "Faturado", statuses: ["PROFORMA_RECEIVED", "ADVANCE_PAID", "PARTIAL_PAID", "FULL_PAID"] },
  { key: "acconto", label: "Acconto", statuses: ["ADVANCE_PAID", "PARTIAL_PAID"] },
  { key: "despachar", label: "A despachar", statuses: ["BOOKED", "SHIPPED"] },
  { key: "transito", label: "Em trânsito", statuses: ["IN_TRANSIT", "SHIPPED"] },
  { key: "aduana", label: "Aduana", statuses: ["ARRIVED", "DI_SUBMITTED", "DUIMP_REGISTERED", "CUSTOMS_RELEASED", "CLEARED"] },
  { key: "estoque", label: "Estoque", statuses: ["RECEIVED_IN_STOCK", "DELIVERED"] },
  { key: "fechado", label: "Fechado", statuses: ["CLOSED"] },
];

function railIndex(status: string): number {
  for (let i = RAIL_STAGES.length - 1; i >= 0; i--) {
    if (RAIL_STAGES[i].statuses.includes(status)) return i;
  }
  return 0;
}

export function ImportationLayout() {
  const { id: idParam } = useParams();
  const id = Number(idParam);
  const navigate = useNavigate();

  const [imp, setImp] = useState<Importation | null>(null);
  const [items, setItems] = useState<ImportationItem[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [entityDocs, setEntityDocs] = useState<DocumentAttachment[]>([]);
  const [supplierName, setSupplierName] = useState("—");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [toDispatch, setToDispatch] = useState<number | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [error, setError] = useState("");

  async function reload() {
    if (!id || Number.isNaN(id)) return;
    try {
      const [i, it, inv, sum] = await Promise.all([
        importationsApi.get(id),
        importationsApi.items(id),
        invoicesApi.list(id),
        financeApi.summary(id),
      ]);
      setImp(i);
      setItems(it);
      setInvoices(inv);
      setSummary(sum);
      setEntityDocs(await documentsApi.list("importation_order", String(id)));

      const [sup, chain, checklist, recs] = await Promise.all([
        suppliersApi.get(i.supplier_id).then((s) => s.name).catch(() => "—"),
        stockApi.quantityChain(id).catch(() => []),
        closureApi.checklist(id).catch(() => []),
        reconciliationApi.list(id).catch(() => []),
      ]);
      setSupplierName(sup);
      const td = chain.reduce((s, c) => {
        const o = c.quantity_ordered ?? 0;
        const sh = c.quantity_shipped ?? 0;
        return s + Math.max(0, o - sh);
      }, 0);
      setToDispatch(chain.length ? td : null);

      const pays =
        inv.length > 0
          ? (await Promise.all(inv.map((inv) => financeApi.listPayments(inv.id)))).flat()
          : [];
      setPayments(pays);

      const blockers = checklist.filter((c) => !c.passed).length;
      const divergent = recs.filter((r) => r.status === "DIVERGENT").length;
      setPendingCount(blockers + divergent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    reload();
  }, [id]);

  const alerts = useMemo(() => {
    if (!imp) return [];
    const today = new Date().toISOString().slice(0, 10);
    const list: Array<{ label: string; tone: "danger" | "warning"; path: string }> = [];
    if (payments.some((p) => p.due_date && !p.payment_date && p.due_date < today)) {
      list.push({ label: "Pagamento vencido", tone: "danger", path: "financeiro" });
    }
    if (payments.some((p) => p.due_date && !p.payment_date && p.due_date >= today)) {
      list.push({ label: "Pagamento a vencer", tone: "warning", path: "financeiro" });
    }
    if (payments.some((p) => p.payment_date && !p.receipt_reference)) {
      list.push({ label: "Fatura sem comprovante", tone: "warning", path: "invoices" });
    }
    if ((toDispatch ?? 0) > 0) {
      list.push({ label: `${toDispatch} un. a despachar`, tone: "warning", path: "logistica" });
    }
    return list;
  }, [imp, payments, toDispatch]);

  const nextDue = useMemo(() => {
    const planned = payments.filter((p) => !p.payment_date && p.due_date);
    const sorted = [...planned].sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? ""));
    return sorted[0]?.due_date ?? null;
  }, [payments]);

  if (!id || Number.isNaN(id)) {
    return (
      <Card>
        <p className="error">Ordem inválida</p>
      </Card>
    );
  }

  if (!imp) {
    return (
      <Card>
        <LoadingState />
      </Card>
    );
  }

  const currentRail = railIndex(imp.current_status);
  const outletContext: ImportationOutletContext = {
    id,
    imp,
    items,
    invoices,
    summary,
    entityDocs,
    error,
    setError,
    reload,
  };

  return (
    <div className="importation-layout order-central">
      <Card compact className="order-central__head">
        <div className="order-central__head-top">
          <Button variant="secondary" onClick={() => navigate("/importacoes")}>
            ← Voltar
          </Button>
          <div className="order-central__title">
            <h1>
              Central da Ordem {imp.po_number}{" "}
              <Badge status={imp.current_status}>{statusLabel(imp.current_status)}</Badge>
            </h1>
            <p className="order-central__meta">
              {supplierName} · {imp.created_at.slice(0, 4)} · {imp.currency} · {imp.incoterm ?? "—"} ·{" "}
              atualizado {fmtDate(imp.created_at)}
            </p>
          </div>
          <div className="order-central__actions">
            <Button variant="ghost" onClick={() => navigate(`/importacoes/${id}/invoices`)}>
              Fatura
            </Button>
            <Button variant="ghost" onClick={() => navigate(`/importacoes/${id}/financeiro`)}>
              Pagamento
            </Button>
            <Button variant="ghost" onClick={() => navigate(`/importacoes/${id}/logistica`)}>
              Despacho
            </Button>
            <Button variant="ghost" onClick={() => navigate(`/importacoes/${id}/documentos`)}>
              Anexar
            </Button>
            <Button variant="primary" onClick={() => navigate(`/importacoes/${id}/conciliacao`)}>
              Conciliar / fechar
            </Button>
          </div>
        </div>

        <div className="order-central__rail">
          {RAIL_STAGES.map((stage, i) => (
            <div key={stage.key} className="order-central__rail-item">
              {i > 0 && <div className={`order-central__rail-line${i <= currentRail ? " done" : ""}`} />}
              <div
                className={`order-central__stage${i < currentRail ? " done" : i === currentRail ? " now" : " todo"}`}
              >
                <span className="order-central__stage-dot">{i < currentRail ? "✓" : i + 1}</span>
                <span className="order-central__stage-lab">{stage.label}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="order-central__kpis">
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Valor faturado</span>
          <span className="order-central__kpi-v">{summary?.total_invoiced ?? emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Acconto versado</span>
          <span className="order-central__kpi-v">{summary?.total_paid ?? emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Acconto rimasto</span>
          <span className="order-central__kpi-v">{summary?.consolidated_balance ?? emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Saldo a pagar</span>
          <span className="order-central__kpi-v">{summary?.consolidated_balance ?? emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Próximo vencimento</span>
          <span className="order-central__kpi-v">{nextDue ? fmtDate(nextDue) : emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">Crédito acumulado</span>
          <span className="order-central__kpi-v">{emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi">
          <span className="order-central__kpi-l">A despachar</span>
          <span className="order-central__kpi-v">{toDispatch ?? emptyDash(null)}</span>
        </div>
        <div className="order-central__kpi order-central__kpi--alert">
          <span className="order-central__kpi-l">Pendências</span>
          <span className="order-central__kpi-v">{pendingCount || emptyDash(null)}</span>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="order-central__alerts">
          {alerts.map((a) => (
            <button
              key={a.label}
              type="button"
              className={`order-central__alert order-central__alert--${a.tone}`}
              onClick={() => navigate(`/importacoes/${id}/${a.path}`)}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}

      <div className="importation-layout__body">
        <aside className="importation-sidebar" role="complementary" aria-label="Abas da ordem">
          {IMPORTATION_SIDEBAR_GROUPS.map((group) => (
            <div key={group.label} className="importation-sidebar__group">
              <p className="importation-sidebar__label">{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={`/importacoes/${id}/${item.path}`}
                  className={({ isActive }) =>
                    `importation-sidebar__link${isActive ? " importation-sidebar__link--active" : ""}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </aside>

        <div className="importation-layout__content">
          <Card>
            <Outlet context={outletContext} />
          </Card>
        </div>
      </div>
    </div>
  );
}
