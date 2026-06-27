import { useEffect, useState } from "react";
import { Navigate, useNavigate, useOutletContext } from "react-router-dom";
import { closureApi, invoicesApi, type Invoice, type TimelineEvent } from "../../api";
import { Button, EmptyState, LoadingState, Table, useToast } from "../../components";
import { fmtDateTime } from "../../utils/formatDate";
import { formatTimelineEvent } from "../../utils/timelineFormat";
import { ImportationFinanceSection } from "./ImportationFinanceSection";
import { DEFAULT_IMPORT_CURRENCY } from "../../constants/currency";
import { fieldLabel, formatMoney, formatUnitPrice, invoiceTypeLabel } from "../../i18n/glossario";
import { OrderCentralOverview } from "./OrderCentralOverview";
import { LogisticsWorkflowPage } from "./logistics/LogisticsWorkflowPage";
import { ReconciliationClosurePanel } from "../ReconciliationClosurePanel";
import type { ImportationOutletContext, ImportationSection } from "./types";

interface Props {
  section: ImportationSection;
}

export function ImportationSectionPage({ section }: Props) {
  const ctx = useOutletContext<ImportationOutletContext>();
  const toast = useToast();
  const { id, imp, items, invoices, summary, entityDocs, setError, reload } = ctx;

  const [invType, setInvType] = useState("PROFORMA");
  const [invNumber, setInvNumber] = useState("");
  const [invAmount, setInvAmount] = useState("");

  async function addInvoice(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await invoicesApi.create({
        importation_id: id,
        invoice_type: invType,
        invoice_number: invNumber,
        amount: invAmount || null,
        currency: imp.currency || DEFAULT_IMPORT_CURRENCY,
      });
      setInvNumber("");
      setInvAmount("");
      toast.success("Invoice adicionada");
      await reload();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro";
      setError(msg);
      toast.error(msg);
    }
  }

  switch (section) {
    case "resumo":
      return <OrderCentralOverview importationId={id} />;

    case "itens":
      return (
        <Table>
          <thead>
            <tr>
              <th>Qtd</th>
              <th>Preço unit.</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id}>
                <td>{it.quantity_ordered ?? "—"}</td>
                <td>{it.unit_price_foreign != null ? formatUnitPrice(it.unit_price_foreign) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      );

    case "invoices":
      return <InvoicesSection invoices={invoices} onAdd={addInvoice} invType={invType} setInvType={setInvType} invNumber={invNumber} setInvNumber={setInvNumber} invAmount={invAmount} setInvAmount={setInvAmount} />;

    case "documentos":
      return (
        <Table>
          <thead>
            <tr>
              <th>Arquivo</th>
              <th>Tipo</th>
              <th>Versão</th>
            </tr>
          </thead>
          <tbody>
            {entityDocs.map((d) => (
              <tr key={d.id}>
                <td>{d.original_filename}</td>
                <td>{d.document_type ?? "—"}</td>
                <td>v{d.version}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      );

    case "logistica":
      return <LogisticsWorkflowPage importationId={id} />;

    case "aduaneiro":
      return <Navigate to={`/importacoes/${id}/logistica#aduana`} replace />;

    case "conciliacao":
      return <ReconciliationClosurePanel importationId={id} />;

    case "historico": {
      return <HistoricoSection importationId={id} />;
    }

    case "financeiro":
      if (!summary) return <LoadingState label="Carregando resumo financeiro..." />;
      return (
        <ImportationFinanceSection
          importationId={id}
          importation={imp}
          summary={summary}
          invoices={invoices}
          items={items}
          onReload={reload}
        />
      );

    default:
      return null;
  }
}

function InvoicesSection({
  invoices,
  onAdd,
  invType,
  setInvType,
  invNumber,
  setInvNumber,
  invAmount,
  setInvAmount,
}: {
  invoices: Invoice[];
  onAdd: (e: React.FormEvent) => void;
  invType: string;
  setInvType: (v: string) => void;
  invNumber: string;
  setInvNumber: (v: string) => void;
  invAmount: string;
  setInvAmount: (v: string) => void;
}) {
  const { id, imp } = useOutletContext<ImportationOutletContext>();
  const navigate = useNavigate();
  const [hashTarget, setHashTarget] = useState<string | null>(null);

  useEffect(() => {
    const syncHash = () => {
      const m = window.location.hash.match(/^#fatura-(\d+)$/);
      setHashTarget(m ? m[1] : null);
      if (m) {
        window.setTimeout(() => {
          document.getElementById(`fatura-${m[1]}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 80);
      }
    };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, [invoices.length]);

  return (
    <div>
      <form className="inline-form" onSubmit={onAdd}>
        <select value={invType} onChange={(e) => setInvType(e.target.value)}>
          <option value="ANTECIPO">{invoiceTypeLabel("ANTECIPO")}</option>
          <option value="PROFORMA">{invoiceTypeLabel("PROFORMA")}</option>
          <option value="SALDO">{invoiceTypeLabel("SALDO")}</option>
          <option value="COMPLEMENTAR">{invoiceTypeLabel("COMPLEMENTAR")}</option>
          <option value="AJUSTE">{invoiceTypeLabel("AJUSTE")}</option>
          <option value="CREDITO">{invoiceTypeLabel("CREDITO")}</option>
          <option value="OUTRA">{invoiceTypeLabel("OUTRA")}</option>
        </select>
        <input
          placeholder="Número"
          value={invNumber}
          onChange={(e) => setInvNumber(e.target.value)}
          required
        />
        <input
          placeholder="Valor (vazio OK)"
          value={invAmount}
          onChange={(e) => setInvAmount(e.target.value)}
        />
        <Button type="submit">Adicionar {fieldLabel("Invoice").toLowerCase()}</Button>
      </form>
      <Table>
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Número</th>
            <th>Valor</th>
            <th>Saldo</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr
              key={inv.id}
              id={`fatura-${inv.id}`}
              className={hashTarget === String(inv.id) ? "invoice-row--target" : undefined}
            >
              <td>{invoiceTypeLabel(inv.invoice_type)}</td>
              <td>
                <span className="finance-invoice-doc finance-invoice-doc--static">{inv.invoice_number}</span>
              </td>
              <td className="num">{formatMoney(inv.amount, inv.currency ?? imp.currency)}</td>
              <td className="num">{formatMoney(inv.balance, inv.currency ?? imp.currency)}</td>
              <td>
                <Button
                  type="button"
                  variant="secondary"
                  className="ui-btn--sm"
                  onClick={() => navigate(`/importacoes/${id}/documentos`)}
                >
                  Anexar doc.
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function HistoricoSection({ importationId }: { importationId: number }) {
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    closureApi
      .timeline(importationId)
      .then(setTimeline)
      .finally(() => setLoading(false));
  }, [importationId]);

  if (loading) return <LoadingState label="Carregando histórico..." />;
  if (timeline.length === 0) return <EmptyState title="Sem eventos no histórico" />;

  return (
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
  );
}
