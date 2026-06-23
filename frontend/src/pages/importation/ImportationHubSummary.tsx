import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  closureApi,
  financeApi,
  reconciliationApi,
  shipmentsApi,
  suppliersApi,
  type DocumentAttachment,
  type FinancialSummary,
  type Importation,
  type ImportationItem,
  type Invoice,
  type Payment,
  type TimelineEvent,
} from "../../api";
import { Badge, EmptyState, LoadingState } from "../../components";
import { formatMoney } from "../../i18n/glossario";
import { normalizeImportCurrency } from "../../constants/currency";
import { fmtDate, fmtDateTime } from "../../utils/formatDate";
import { formatTimelineEvent } from "../../utils/timelineFormat";

interface Props {
  importationId: number;
  imp: Importation;
  items: ImportationItem[];
  invoices: Invoice[];
  summary: FinancialSummary | null;
  entityDocs: DocumentAttachment[];
}

export function ImportationHubSummary({
  importationId,
  imp,
  items,
  invoices,
  summary,
  entityDocs,
}: Props) {
  const [supplierName, setSupplierName] = useState("—");
  const [payments, setPayments] = useState<Payment[]>([]);
  const [reconciliations, setReconciliations] = useState<Array<{ status: string; label: string }>>([]);
  const [shipmentModal, setShipmentModal] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const payPromise =
      invoices.length > 0
        ? Promise.all(invoices.map((inv) => financeApi.listPayments(inv.id)))
            .then((groups) => groups.flat())
            .catch(() => [] as Payment[])
        : Promise.resolve([] as Payment[]);

    Promise.all([
      suppliersApi.get(imp.supplier_id).then((s) => s.name).catch(() => "—"),
      reconciliationApi.list(importationId).catch(() => []),
      shipmentsApi.list(importationId).catch(() => []),
      closureApi.timeline(importationId).catch(() => []),
      payPromise,
    ])
      .then(([sup, recs, ships, tl, pays]) => {
        if (cancelled) return;
        setSupplierName(sup);
        setReconciliations(recs.map((r) => ({ status: r.status, label: r.label })));
        setShipmentModal(ships[0]?.modal ?? null);
        setTimeline(tl.slice(-8).reverse());
        setPayments(pays);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [importationId, imp.supplier_id, invoices]);

  const nextDue = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    const planned = payments.filter((p) => !p.payment_date && !p.receipt_reference && p.due_date);
    const sorted = [...planned].sort((a, b) => (a.due_date ?? "").localeCompare(b.due_date ?? ""));
    const p = sorted[0];
    if (!p) return null;
    const inv = invoices.find((i) => i.id === p.invoice_id);
    return {
      due_date: p.due_date,
      invoice_number: inv?.invoice_number ?? String(p.invoice_id),
      is_overdue: p.due_date != null && p.due_date < today,
    };
  }, [payments, invoices]);

  const hasOverdue = payments.some(
    (p) => p.due_date && !p.payment_date && !p.receipt_reference && p.due_date < new Date().toISOString().slice(0, 10)
  );
  const hasUpcoming = payments.some(
    (p) => p.due_date && !p.payment_date && !p.receipt_reference && !hasOverdue
  );

  const divergent = reconciliations.filter((r) => r.status === "DIVERGENT");

  const badges = useMemo(() => {
    const list: Array<{ label: string; tone: "danger" | "warning" | "info" | "success" | "neutral" }> = [];
    if (hasOverdue) list.push({ label: "Pagamento vencido", tone: "danger" });
    if (hasUpcoming) list.push({ label: "Pagamento a vencer", tone: "warning" });
    if (entityDocs.length === 0) list.push({ label: "Documento pendente", tone: "warning" });
    if (reconciliations.some((r) => r.status === "DIVERGENT")) {
      list.push({ label: "Divergência aberta", tone: "danger" });
    }
    if (divergent.length === 0 && imp.current_status !== "CLOSED" && invoices.length > 0) {
      list.push({ label: "Pronto para fechamento", tone: "success" });
    }
    return list;
  }, [hasOverdue, hasUpcoming, entityDocs, reconciliations, imp.current_status, invoices.length, divergent.length]);

  const actions = useMemo(() => {
    const items: Array<{ kind: string; label: string; detail: string; tone: "danger" | "warning" | "info" }> = [];
    if (entityDocs.length === 0) {
      items.push({ kind: "proforma", label: "Documento", detail: "Anexar proforma ou documentos", tone: "warning" });
    }
    if (divergent.length > 0) {
      items.push({
        kind: "reconciliations",
        label: "Conciliação",
        detail: `${divergent.length} divergência(s) aberta(s)`,
        tone: "danger",
      });
    }
    if (hasOverdue) {
      items.push({ kind: "finance", label: "Pagamento", detail: "Há pagamento vencido", tone: "danger" });
    }
    return items;
  }, [entityDocs, divergent, hasOverdue]);

  if (loading) return <LoadingState label="Carregando visão operacional..." />;

  return (
    <div className="importation-hub">
      <div className="importation-hub__badges">
        {badges.length === 0 ? (
          <span className="meta">Nenhum alerta ativo</span>
        ) : (
          badges.map((b) => (
            <Badge key={b.label} tone={b.tone}>
              {b.label}
            </Badge>
          ))
        )}
      </div>

      <div className="importation-hub__grid">
        <div className="hub-card">
          <h2 className="hub-card__title">Resumo financeiro</h2>
          <dl className="hub-dl">
            <dt>Moeda</dt>
            <dd>{normalizeImportCurrency(imp.currency)}</dd>
            <dt>Saldo consolidado</dt>
            <dd>{formatMoney(summary?.consolidated_balance, normalizeImportCurrency(imp.currency))}</dd>
            <dt>Próximo vencimento</dt>
            <dd>
              {nextDue?.due_date ? (
                <>
                  {fmtDate(nextDue.due_date)} · {nextDue.invoice_number}
                  {nextDue.is_overdue ? " (vencido)" : ""}
                </>
              ) : (
                "—"
              )}
            </dd>
          </dl>
          <Link to={`/importacoes/${importationId}/financeiro`} className="hub-link">
            Abrir financeiro →
          </Link>
        </div>

        <div className="hub-card">
          <h2 className="hub-card__title">Resumo logístico</h2>
          <dl className="hub-dl">
            <dt>Modal</dt>
            <dd>{shipmentModal ?? "—"}</dd>
            <dt>Em trânsito</dt>
            <dd>{imp.current_status === "IN_TRANSIT" || imp.current_status === "SHIPPED" ? "Sim" : "Não"}</dd>
          </dl>
          <Link to={`/importacoes/${importationId}/logistica`} className="hub-link">
            Abrir logística →
          </Link>
        </div>

        <div className="hub-card">
          <h2 className="hub-card__title">Resumo documental</h2>
          <dl className="hub-dl">
            <dt>Documentos anexos</dt>
            <dd>{entityDocs.length || "—"}</dd>
            <dt>Invoices</dt>
            <dd>{invoices.length || "—"}</dd>
            <dt>Itens</dt>
            <dd>{items.length || "—"}</dd>
          </dl>
          <Link to={`/importacoes/${importationId}/documentos`} className="hub-link">
            Ver documentos →
          </Link>
        </div>
      </div>

      <div className="hub-card hub-card--wide">
        <h2 className="hub-card__title">Próximas ações</h2>
        {actions.length === 0 ? (
          <EmptyState title="Nenhuma ação pendente" description="Processo em dia nesta importação." />
        ) : (
          <ul className="hub-actions">
            {actions.map((a, i) => (
              <li key={`${a.kind}-${i}`}>
                <Badge tone={a.tone as "danger" | "warning" | "info"}>{a.label}</Badge>
                <span>{a.detail}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {divergent.length > 0 && (
        <div className="hub-card hub-card--wide hub-card--alert">
          <h2 className="hub-card__title">Pendências críticas</h2>
          <ul className="hub-actions">
            {divergent.map((r, i) => (
              <li key={i}>
                <Badge tone="danger">Divergência</Badge>
                <span>{r.label}</span>
              </li>
            ))}
          </ul>
          <Link to={`/importacoes/${importationId}/conciliacao`} className="hub-link">
            Ir para conciliação →
          </Link>
        </div>
      )}

      <div className="hub-card hub-card--wide">
        <h2 className="hub-card__title">Linha do tempo recente</h2>
        {timeline.length === 0 ? (
          <EmptyState title="Sem eventos" />
        ) : (
          <ul className="hub-timeline">
            {timeline.map((e, i) => {
              const f = formatTimelineEvent(e);
              return (
                <li key={i}>
                  <time>{fmtDateTime(e.timestamp)}</time>
                  <strong>{f.title}</strong>
                  <span>{f.detail}</span>
                  {e.user_name && <span className="meta">por {e.user_name}</span>}
                  {f.reason && <span className="meta">Motivo: {f.reason}</span>}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <p className="meta importation-hub__supplier">
        Fornecedor: <strong>{supplierName}</strong>
      </p>
    </div>
  );
}
