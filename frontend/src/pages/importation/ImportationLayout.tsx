import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, LoadingState } from "../../components";
import {
  documentsApi,
  financeApi,
  importationsApi,
  invoicesApi,
  suppliersApi,
  type DocumentAttachment,
  type FinancialSummary,
  type Importation,
  type ImportationItem,
  type Invoice,
  type OrderCentralResponse,
} from "../../api";
import { statusLabel } from "../../i18n/glossario";
import { DEFAULT_IMPORT_CURRENCY, normalizeImportCurrency } from "../../constants/currency";
import { fmtDate } from "../../utils/formatDate";
import { IMPORTATION_SIDEBAR_GROUPS, type ImportationOutletContext } from "./types";
import { OrderCentralProvider } from "./OrderCentralContext";
import { OrderCentralOperationalHeader } from "./OrderCentralOperationalHeader";

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
  const [orderCentral, setOrderCentral] = useState<OrderCentralResponse | null>(null);
  const [centralLoading, setCentralLoading] = useState(true);
  const [brazilNotes, setBrazilNotes] = useState("");
  const [responsibleDraft, setResponsibleDraft] = useState("");
  const [forecastDraft, setForecastDraft] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);
  const [error, setError] = useState("");

  const reloadCentral = useCallback(async () => {
    if (!id || Number.isNaN(id)) return;
    const central = await importationsApi.orderCentral(id);
    setOrderCentral(central);
  }, [id]);

  async function reload() {
    if (!id || Number.isNaN(id)) return;
    try {
      setError("");
      const [i, it, inv, sum, central] = await Promise.all([
        importationsApi.get(id),
        importationsApi.items(id),
        invoicesApi.list(id),
        financeApi.summary(id),
        importationsApi.orderCentral(id),
      ]);
      setImp(i);
      setItems(it);
      setInvoices(inv);
      setSummary(sum);
      setOrderCentral(central);
      setBrazilNotes(i.brazil_operational_notes ?? "");
      setResponsibleDraft(i.responsible ?? "");
      setForecastDraft(i.internal_forecast_date ?? "");
      setEntityDocs(await documentsApi.list("importation_order", String(id)));

      const [sup] = await Promise.all([
        suppliersApi.get(i.supplier_id).then((s) => s.name).catch(() => "—"),
      ]);
      setSupplierName(sup);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    }
  }

  useEffect(() => {
    if (!id || Number.isNaN(id)) return;
    setImp(null);
    setOrderCentral(null);
    setError("");
    setCentralLoading(true);
    reload().finally(() => setCentralLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const statusRail = orderCentral?.status_rail ?? null;
  const operationalHeader = orderCentral?.operational_header ?? null;

  const alerts = useMemo(() => {
    if (!imp || !orderCentral) return [];
    const oh = orderCentral.operational_header;
    if (!oh) return [];
    const today = new Date().toISOString().slice(0, 10);
    const list: Array<{ label: string; tone: "danger" | "warning"; path: string }> = [];
    if (oh.overdue_count > 0) {
      list.push({ label: "Pagamento vencido", tone: "danger", path: "financeiro" });
    } else if (oh.next_due_date && oh.next_due_date >= today) {
      list.push({ label: "Pagamento a vencer", tone: "warning", path: "financeiro" });
    }
    for (const p of orderCentral.payments_settled ?? []) {
      if (p.payment_date && !p.receipt_reference && !p.approved_without_receipt) {
        list.push({ label: "Fatura sem comprovante", tone: "warning", path: "invoices" });
        break;
      }
    }
    if ((oh.to_dispatch ?? 0) > 0) {
      list.push({ label: `${oh.to_dispatch} un. a despachar`, tone: "warning", path: "logistica#despachar" });
    }
    for (const msg of statusRail?.alerts ?? []) {
      list.push({ label: msg, tone: "warning", path: "resumo" });
    }
    return list;
  }, [imp, orderCentral, statusRail]);

  const centralContextValue = useMemo(
    () => ({
      data: orderCentral,
      loading: centralLoading,
      error,
      reloadCentral: async () => {
        await reloadCentral();
        await reload();
      },
    }),
    [orderCentral, centralLoading, error, reloadCentral],
  );

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

  const currency = normalizeImportCurrency(imp.currency || DEFAULT_IMPORT_CURRENCY);

  async function saveBrazilNotes() {
    const prev = brazilNotes;
    setSavingNotes(true);
    setError("");
    try {
      const updated = await importationsApi.updateBrazilFields(id, { brazil_operational_notes: brazilNotes || null });
      setImp(updated);
    } catch (e) {
      setBrazilNotes(prev);
      setError(e instanceof Error ? e.message : "Não foi possível salvar a observação.");
    } finally {
      setSavingNotes(false);
    }
  }

  async function saveBrazilField(patch: { priority?: string | null; responsible?: string | null; internal_forecast_date?: string | null }) {
    setError("");
    try {
      const updated = await importationsApi.updateBrazilFields(id, patch);
      setImp(updated);
      if (patch.responsible !== undefined) setResponsibleDraft(updated.responsible ?? "");
      if (patch.internal_forecast_date !== undefined) setForecastDraft(updated.internal_forecast_date ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível salvar o campo.");
    }
  }

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
    <OrderCentralProvider value={centralContextValue}>
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
                {supplierName} · {imp.created_at.slice(0, 4)} · {currency} · {imp.incoterm ?? "—"} ·{" "}
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

          {operationalHeader && (
            <OrderCentralOperationalHeader
              importationId={id}
              header={operationalHeader}
              estimatedTotal={imp.estimated_total}
              currency={currency}
              models={orderCentral?.models}
              items={items}
              invoices={orderCentral?.invoices}
            />
          )}

          <div className="order-central__rail order-central__rail--compact">
            {(statusRail?.stages ?? []).map((stage, i) => {
              const state = stage.state;
              const dot = state === "done" ? "✓" : state === "declared_without_data" ? "!" : i + 1;
              const lineDone = state === "done";
              return (
                <div key={stage.key} className="order-central__rail-item">
                  {i > 0 && <div className={`order-central__rail-line${lineDone ? " done" : ""}`} />}
                  <div
                    className={`order-central__stage order-central__stage--${state}`}
                    title={
                      state === "declared_without_data"
                        ? "Status declarado sem dado de suporte"
                        : undefined
                    }
                  >
                    <span className="order-central__stage-dot">{dot}</span>
                    <span className="order-central__stage-lab">{stage.label}</span>
                    {stage.subtitle && (
                      <span className="order-central__stage-sub">{stage.subtitle}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {(statusRail?.alerts?.length ?? 0) > 0 && (
            <div className="order-central__status-rail-alerts">
              {statusRail!.alerts!.map((a) => (
                <span key={a} className="order-central__status-rail-alert">
                  {a}
                </span>
              ))}
            </div>
          )}
        </Card>

        {alerts.length > 0 && (
          <div className="order-central__alerts">
            {alerts.map((a) => (
              <button
                key={a.label}
                type="button"
                className={`order-central__alert order-central__alert--${a.tone}`}
                onClick={() => {
                  const [section, hash] = a.path.split("#");
                  navigate(`/importacoes/${id}/${section}${hash ? `#${hash}` : ""}`);
                }}
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

        <div className="order-central__brazil-edit">
          <p className="order-central__brazil-edit-title">Operação Brasil</p>
          <div className="order-central__brazil-edit-row">
            <div className="order-central__brazil-field">
              <label htmlFor="brazil-priority">Prioridade</label>
              <select
                id="brazil-priority"
                className="input"
                value={imp.priority ?? ""}
                onChange={(e) => saveBrazilField({ priority: e.target.value || null })}
              >
                <option value="">—</option>
                <option value="HIGH">Alta</option>
                <option value="MEDIUM">Média</option>
                <option value="LOW">Baixa</option>
              </select>
            </div>
            <div className="order-central__brazil-field">
              <label htmlFor="brazil-responsible">Responsável</label>
              <input
                id="brazil-responsible"
                className="input"
                value={responsibleDraft}
                placeholder="—"
                onChange={(e) => setResponsibleDraft(e.target.value)}
                onBlur={() => {
                  const v = responsibleDraft.trim();
                  const persisted = imp.responsible ?? "";
                  if (v !== persisted) saveBrazilField({ responsible: v || null });
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.currentTarget.blur();
                }}
              />
            </div>
            <div className="order-central__brazil-field">
              <label htmlFor="brazil-forecast">Previsão interna</label>
              <input
                id="brazil-forecast"
                className="input"
                type="date"
                value={forecastDraft}
                onChange={(e) => setForecastDraft(e.target.value)}
                onBlur={() => {
                  const v = forecastDraft;
                  const persisted = imp.internal_forecast_date ?? "";
                  if (v !== persisted) saveBrazilField({ internal_forecast_date: v || null });
                }}
              />
            </div>
            <div className="order-central__brazil-field" style={{ flex: 1, minWidth: 220 }}>
              <label htmlFor="brazil-notes">Observação operacional (Brasil)</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  id="brazil-notes"
                  className="input"
                  value={brazilNotes}
                  onChange={(e) => setBrazilNotes(e.target.value)}
                  placeholder="Notas internas — editável"
                />
                <Button variant="secondary" disabled={savingNotes} onClick={saveBrazilNotes}>
                  {savingNotes ? "Salvando…" : "Salvar"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </OrderCentralProvider>
  );
}
