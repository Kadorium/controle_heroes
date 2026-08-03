import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { DoganalePanel } from "./DoganalePanel";
import { NumerarioPanel } from "./NumerarioPanel";
import { NationalizationPanel } from "./NationalizationPanel";
import { ReceiptPanel } from "./ReceiptPanel";
import {
  allocateInvoiceItem,
  allocateShipmentItem,
  cancelImportProcess,
  getImportProcess,
  linkInvoice,
  linkShipment,
  listInvoiceResiduals,
  listProcessAudit,
  listProcessDocuments,
  listShipmentResiduals,
  submitImportProcess,
  unlinkInvoice,
  unlinkShipment,
  updateImportProcess,
  uploadProcessDocument,
  type ImportProcess,
  type ResidualInvoiceItem,
  type ResidualShipmentItem,
} from "./customsApi";
import { canReadCustoms, canWriteCustoms, conflictMessage, statusLabel } from "./customsPermissions";
import {
  Button,
  ContextBreadcrumb,
  DocumentActions,
  ErrorState,
  FileUpload,
  FormField,
  formatDateTime,
  formatQuantity,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  StatusBadge,
  TextInput,
  auditActionLabel,
  FORMAT_ABSENCE,
} from "../../ui";
import type { AuditEntry } from "../../ui";

type Props = { user: User };

export function CustomsDetailPage({ user }: Props) {
  const { processId } = useParams();
  const id = Number(processId);
  const writable = canWriteCustoms(user);
  const [process, setProcess] = useState<ImportProcess | null>(null);
  const [invResiduals, setInvResiduals] = useState<ResidualInvoiceItem[]>([]);
  const [shpResiduals, setShpResiduals] = useState<ResidualShipmentItem[]>([]);
  const [docs, setDocs] = useState<
    Array<{ id: number; original_filename: string; mime_type?: string | null }>
  >([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [invoiceId, setInvoiceId] = useState("");
  const [shipmentId, setShipmentId] = useState("");
  const [extRef, setExtRef] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [allocInvItem, setAllocInvItem] = useState("");
  const [allocInvQty, setAllocInvQty] = useState("");
  const [allocShpItem, setAllocShpItem] = useState("");
  const [allocShpQty, setAllocShpQty] = useState("");

  const reload = useCallback(async () => {
    const p = await getImportProcess(id);
    setProcess(p);
    setExtRef(p.external_reference ?? "");
    const [ir, sr, d, events] = await Promise.all([
      listInvoiceResiduals(id),
      listShipmentResiduals(id),
      listProcessDocuments(id),
      listProcessAudit(id).catch(() => []),
    ]);
    setInvResiduals(ir);
    setShpResiduals(sr);
    setDocs(d);
    setAudit(
      events.map((e) => ({
        id: e.id,
        action: e.action,
        at: e.created_at,
        actor: e.actor_id,
        detail: e.reason_code ?? e.details,
      })),
    );
  }, [id]);

  useEffect(() => {
    if (!canReadCustoms(user)) return;
    let cancelled = false;
    void (async () => {
      setError(null);
      try {
        await reload();
      } catch (e) {
        if (!cancelled) {
          const err = e as Error & { status?: number };
          if (err.status === 403) setError("Sem permissão para processos aduaneiros.");
          else setError(e instanceof Error ? e.message : "Erro");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reload, user]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (e) {
      setError(conflictMessage(e as Error & { status?: number; code?: string }));
    } finally {
      setBusy(false);
    }
  }

  if (!canReadCustoms(user)) {
    return <ErrorState message="Sem permissão para processos aduaneiros." />;
  }
  if (error && !process) return <ErrorState message={error} />;
  if (!process) return <LoadingState message="Carregando processo…" />;

  const draft = process.status === "DRAFT";
  const structureLocked = !draft;

  return (
    <div data-testid="customs-detail-page">
      <ContextBreadcrumb
        items={[
          { label: "Aduana" },
          { label: "Processos", to: "/customs" },
          { label: process.code },
        ]}
      />
      <PageHeader
        title={process.code}
        subtitle={`Status: ${statusLabel(process.status)} · v${process.version}`}
      />
      <div className="form-actions" style={{ marginBottom: "0.75rem" }}>
        <StatusBadge status={process.status} entity="customs" />
      </div>      {error ? (
        <Notice tone="danger" data-testid="customs-error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Resumo" data-testid="customs-section-resumo">
        <p>
          Status: <strong>{statusLabel(process.status)}</strong>
        </p>
        <p>
          Ref. externa: <strong data-testid="customs-detail-ext">{process.external_reference || "—"}</strong>
        </p>
        {writable && draft ? (
          <div className="form-actions">
            <FormField label="Atualizar ref. externa" htmlFor="customs-edit-ext">
              <TextInput
                id="customs-edit-ext"
                value={extRef}
                onChange={(e) => setExtRef(e.target.value)}
                data-testid="customs-edit-ext"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="customs-save-ext"
              onClick={() =>
                void run(async () => {
                  await updateImportProcess(id, {
                    expected_version: process.version,
                    external_reference: extRef,
                  });
                })
              }
            >
              Salvar ref.
            </Button>
          </div>
        ) : null}
        {writable && draft ? (
          <Button
            type="button"
            disabled={busy}
            data-testid="customs-submit"
            onClick={() =>
              void run(async () => {
                await submitImportProcess(id, process.version);
              })
            }
          >
            Submeter
          </Button>
        ) : null}
        {writable && process.status !== "CANCELLED" ? (
          <div className="form-actions">
            <FormField label="Motivo cancelamento" htmlFor="customs-cancel-reason">
              <TextInput
                id="customs-cancel-reason"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                data-testid="customs-cancel-reason"
              />
            </FormField>
            <Button
              type="button"
              variant="danger"
              disabled={busy || !cancelReason.trim()}
              data-testid="customs-cancel"
              onClick={() =>
                void run(async () => {
                  await cancelImportProcess(id, {
                    expected_version: process.version,
                    reason: cancelReason,
                  });
                })
              }
            >
              Cancelar processo
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Faturas" data-testid="customs-section-invoices">
        {structureLocked ? <Notice tone="info">Estrutura bloqueada após submissão.</Notice> : null}
        {process.invoices.length === 0 ? (
          <p className="muted">Nenhuma fatura vinculada.</p>
        ) : (
          <ul data-testid="customs-invoice-list">
            {process.invoices.map((inv) => (
              <li key={inv.id}>
                Fatura #{inv.invoice_id}{" "}
                <Link to={`/invoices/${inv.invoice_id}`}>abrir</Link>{" "}
                {writable && draft ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={busy}
                    data-testid={`customs-unlink-invoice-${inv.invoice_id}`}
                    onClick={() =>
                      void run(async () => {
                        await unlinkInvoice(id, {
                          expected_version: process.version,
                          invoice_id: inv.invoice_id,
                        });
                      })
                    }
                  >
                    Remover
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <FormField label="ID da fatura" htmlFor="customs-link-invoice-id">
              <TextInput
                id="customs-link-invoice-id"
                value={invoiceId}
                onChange={(e) => setInvoiceId(e.target.value)}
                data-testid="customs-link-invoice-id"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !invoiceId.trim()}
              data-testid="customs-link-invoice"
              onClick={() =>
                void run(async () => {
                  const idNum = Number(invoiceId);
                  await linkInvoice(id, {
                    expected_version: process.version,
                    invoice_id: idNum,
                  });
                  setInvoiceId("");
                })
              }
            >
              Vincular fatura
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Alocações (fatura)" data-testid="customs-section-allocs-inv">
        {invResiduals.length === 0 ? (
          <p className="muted">Sem itens de fatura para alocar.</p>
        ) : (
          <ul data-testid="customs-inv-residuals">
            {invResiduals.map((r) => (
              <li key={r.invoice_item_id}>
                item {r.invoice_item_id} ({r.product_sku}) qty {formatQuantity(r.quantity)} ·
                alocado {formatQuantity(r.allocated_qty)} · residual {formatQuantity(r.residual_qty)}
              </li>
            ))}
          </ul>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <FormField label="ID do item de fatura" htmlFor="customs-alloc-inv-item">
              <TextInput
                id="customs-alloc-inv-item"
                value={allocInvItem}
                onChange={(e) => setAllocInvItem(e.target.value)}
                data-testid="customs-alloc-inv-item"
              />
            </FormField>
            <FormField label="Quantidade" htmlFor="customs-alloc-inv-qty">
              <TextInput
                id="customs-alloc-inv-qty"
                value={allocInvQty}
                onChange={(e) => setAllocInvQty(e.target.value)}
                data-testid="customs-alloc-inv-qty"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="customs-alloc-inv"
              onClick={() =>
                void run(async () => {
                  await allocateInvoiceItem(id, {
                    expected_version: process.version,
                    invoice_item_id: Number(allocInvItem),
                    allocated_qty: allocInvQty,
                  });
                })
              }
            >
              Alocar
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Embarques" data-testid="customs-section-shipments">
        {process.shipments.length === 0 ? (
          <p className="muted">Nenhum embarque vinculado.</p>
        ) : (
          <ul data-testid="customs-shipment-list">
            {process.shipments.map((sh) => (
              <li key={sh.id}>
                Embarque #{sh.shipment_id}{" "}
                <Link to={`/shipments/${sh.shipment_id}`}>abrir</Link>{" "}
                {writable && draft ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={busy}
                    data-testid={`customs-unlink-shipment-${sh.shipment_id}`}
                    onClick={() =>
                      void run(async () => {
                        await unlinkShipment(id, {
                          expected_version: process.version,
                          shipment_id: sh.shipment_id,
                        });
                      })
                    }
                  >
                    Remover
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <FormField label="ID do embarque" htmlFor="customs-link-shipment-id">
              <TextInput
                id="customs-link-shipment-id"
                value={shipmentId}
                onChange={(e) => setShipmentId(e.target.value)}
                data-testid="customs-link-shipment-id"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy || !shipmentId}
              data-testid="customs-link-shipment"
              onClick={() =>
                void run(async () => {
                  await linkShipment(id, {
                    expected_version: process.version,
                    shipment_id: Number(shipmentId),
                  });
                  setShipmentId("");
                })
              }
            >
              Vincular embarque
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Alocações (embarque)" data-testid="customs-section-allocs-shp">
        {shpResiduals.length === 0 ? (
          <p className="muted">Sem itens de embarque para alocar.</p>
        ) : (
          <ul data-testid="customs-shp-residuals">
            {shpResiduals.map((r) => (
              <li key={r.shipment_item_id}>
                item {r.shipment_item_id} qty {formatQuantity(r.quantity)} · alocado{" "}
                {formatQuantity(r.allocated_qty)} · residual {formatQuantity(r.residual_qty)}
              </li>
            ))}
          </ul>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <FormField label="ID do item de embarque" htmlFor="customs-alloc-shp-item">
              <TextInput
                id="customs-alloc-shp-item"
                value={allocShpItem}
                onChange={(e) => setAllocShpItem(e.target.value)}
                data-testid="customs-alloc-shp-item"
              />
            </FormField>
            <FormField label="Quantidade" htmlFor="customs-alloc-shp-qty">
              <TextInput
                id="customs-alloc-shp-qty"
                value={allocShpQty}
                onChange={(e) => setAllocShpQty(e.target.value)}
                data-testid="customs-alloc-shp-qty"
              />
            </FormField>
            <Button
              type="button"
              disabled={busy}
              data-testid="customs-alloc-shp"
              onClick={() =>
                void run(async () => {
                  await allocateShipmentItem(id, {
                    expected_version: process.version,
                    shipment_item_id: Number(allocShpItem),
                    allocated_qty: allocShpQty,
                  });
                })
              }
            >
              Alocar
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Documentos" data-testid="customs-section-docs">
        {docs.length === 0 ? (
          <p className="muted">Nenhum documento anexado.</p>
        ) : (
          <ul data-testid="customs-docs">
            {docs.map((d) => (
              <li key={d.id}>
                {d.original_filename}{" "}
                <DocumentActions documentId={d.id} filename={d.original_filename} mimeType={d.mime_type} />
              </li>
            ))}
          </ul>
        )}
        {writable ? (
          <FileUpload
            label="Anexar documento"
            data-testid="customs-doc-upload"
            onFileChange={(file) => {
              if (!file) return;
              void run(async () => {
                await uploadProcessDocument(id, file);
              });
            }}
          />
        ) : null}
      </SectionCard>

      <div data-testid="customs-section-doganale">
        <DoganalePanel user={user} processId={id} />
      </div>
      <div data-testid="customs-section-numerario">
        <NumerarioPanel user={user} processId={id} />
      </div>
      <div data-testid="customs-section-liberacoes">
        <NationalizationPanel user={user} processId={id} />
      </div>
      <div data-testid="customs-section-recebimentos">
        <ReceiptPanel user={user} processId={id} />
      </div>

      <SectionCard title="Auditoria" data-testid="customs-section-audit">
        {audit.length === 0 ? (
          <p className="muted">Sem eventos de auditoria</p>
        ) : (
          <table className="mini-table" data-testid="customs-audit-table">
            <thead>
              <tr>
                <th>Ação</th>
                <th>Quando</th>
                <th>Quem</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((entry, i) => (
                <tr key={entry.id ?? i}>
                  <td>
                    {auditActionLabel(entry.action)}
                    {entry.detail ? <div className="muted">{entry.detail}</div> : null}
                  </td>
                  <td>{formatDateTime(entry.at)}</td>
                  <td>{typeof entry.actor === "string" && entry.actor.trim() ? entry.actor : FORMAT_ABSENCE}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </div>
  );
}
