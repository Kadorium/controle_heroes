import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { closureApi, invoicesApi, type TimelineEvent } from "../../api";
import { Button, EmptyState, LoadingState, Table, useToast } from "../../components";
import { fmtDateTime } from "../../utils/formatDate";
import { formatTimelineEvent } from "../../utils/timelineFormat";
import { ImportationFinanceSection } from "./ImportationFinanceSection";
import { DEFAULT_IMPORT_CURRENCY } from "../../constants/currency";
import { fieldLabel, invoiceTypeLabel } from "../../i18n/glossario";
import { OrderCentralOverview } from "./OrderCentralOverview";
import { CustomsStockPanel } from "../CustomsStockPanel";
import { LogisticsPanel } from "../LogisticsPanel";
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
                <td>{it.unit_price_foreign ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      );

    case "invoices":
      return (
        <div>
          <form className="inline-form" onSubmit={addInvoice}>
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
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td>{invoiceTypeLabel(inv.invoice_type)}</td>
                  <td>{inv.invoice_number}</td>
                  <td>{inv.amount ?? "—"}</td>
                  <td>{inv.balance ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      );

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
      return <LogisticsPanel importationId={id} />;

    case "aduaneiro":
      return <CustomsStockPanel importationId={id} items={items} />;

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
