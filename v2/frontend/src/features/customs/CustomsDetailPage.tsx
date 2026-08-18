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
  getDoganale,
  getImportProcess,
  linkInvoice,
  linkShipment,
  listEntityAudit,
  listFundingRequests,
  listInvoiceResiduals,
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
import { listNationalizations, listReceipts } from "../inventory/inventoryApi";
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

type TrailEntry = AuditEntry & { scope: string };

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
  const [audit, setAudit] = useState<TrailEntry[]>([]);
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
  const [inventoryTick, setInventoryTick] = useState(0);

  const reload = useCallback(async () => {
    const p = await getImportProcess(id);
    setProcess(p);
    setExtRef(p.external_reference ?? "");
    const [ir, sr, d, processEvents, fundings, nats, dog, receipts] = await Promise.all([
      listInvoiceResiduals(id),
      listShipmentResiduals(id),
      listProcessDocuments(id),
      listEntityAudit("import_process", String(id)).catch(() => []),
      listFundingRequests(id).catch(() => []),
      listNationalizations(id).catch(() => []),
      getDoganale(id).catch(() => null),
      listReceipts(id).catch(() => []),
    ]);
    setInvResiduals(ir);
    setShpResiduals(sr);
    setDocs(d);

    const related: Array<Promise<TrailEntry[]>> = [];
    for (const f of fundings) {
      related.push(
        listEntityAudit("customs_funding_request", String(f.id))
          .then((ev) =>
            ev.map((e) => ({
              id: e.id,
              action: e.action,
              at: e.created_at,
              actor: e.actor_id,
              detail: e.reason_code ?? e.details,
              scope: "Numerário",
            })),
          )
          .catch(() => []),
      );
    }
    for (const n of nats) {
      related.push(
        listEntityAudit("nationalization", String(n.id))
          .then((ev) =>
            ev.map((e) => ({
              id: e.id,
              action: e.action,
              at: e.created_at,
              actor: e.actor_id,
              detail: e.reason_code ?? e.details,
              scope: "Liberação",
            })),
          )
          .catch(() => []),
      );
    }
    const dogVersionIds = new Set<number>();
    if (dog?.current_version_id) dogVersionIds.add(dog.current_version_id);
    for (const v of dog?.versions ?? []) dogVersionIds.add(v.id);
    for (const vid of dogVersionIds) {
      related.push(
        listEntityAudit("doganale_version", String(vid))
          .then((ev) =>
            ev.map((e) => ({
              id: e.id,
              action: e.action,
              at: e.created_at,
              actor: e.actor_id,
              detail: e.reason_code ?? e.details,
              scope: "Doganale",
            })),
          )
          .catch(() => []),
      );
    }
    for (const rec of receipts) {
      related.push(
        listEntityAudit("goods_receipt", String(rec.id))
          .then((ev) =>
            ev.map((e) => ({
              id: e.id,
              action: e.action,
              at: e.created_at,
              actor: e.actor_id,
              detail: e.reason_code ?? e.details,
              scope: "Recebimento",
            })),
          )
          .catch(() => []),
      );
    }
    const extra = (await Promise.all(related)).flat();
    const processRows: TrailEntry[] = processEvents.map((e) => ({
      id: e.id,
      action: e.action,
      at: e.created_at,
      actor: e.actor_id,
      detail: e.reason_code ?? e.details,
      scope: "Processo",
    }));
    setAudit(
      [...processRows, ...extra].sort((a, b) => String(b.at ?? "").localeCompare(String(a.at ?? ""))),
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
            <FormField
              label="Referência DUIMP (digitada — ensaio, não veio de PDF)"
              htmlFor="customs-edit-ext"
              hint="L-007: não há PDF de DUIMP/DI no corpus. Informe uma referência de teste."
            >
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
        {writable && draft && !process.external_reference ? (
          <p className="muted" data-testid="customs-duimp-hint">
            Digite a referência DUIMP de ensaio e salve antes de submeter.
          </p>
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
                {r.product_sku ?? "SKU"} · qty {formatQuantity(r.quantity)} · alocado{" "}
                {formatQuantity(r.allocated_qty)} · residual {formatQuantity(r.residual_qty)}
                {writable && draft && Number(r.residual_qty) > 0 ? (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={busy}
                    data-testid={`customs-alloc-inv-residual-${r.invoice_item_id}`}
                    onClick={() =>
                      void run(async () => {
                        await allocateInvoiceItem(id, {
                          expected_version: process.version,
                          invoice_item_id: r.invoice_item_id,
                          allocated_qty: r.residual_qty,
                        });
                      })
                    }
                  >
                    Alocar residual
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <p className="muted">Ajuste excepcional — a ação normal é «Alocar residual» na linha.</p>
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
          <>
            {writable && draft && shpResiduals.some((r) => Number(r.residual_qty) > 0) ? (
              <Button
                type="button"
                variant="ghost"
                disabled={busy}
                data-testid="customs-alloc-shp-all"
                onClick={() =>
                  void run(async () => {
                    let version = process.version;
                    for (const r of shpResiduals) {
                      if (Number(r.residual_qty) <= 0) continue;
                      const next = await allocateShipmentItem(id, {
                        expected_version: version,
                        shipment_item_id: r.shipment_item_id,
                        allocated_qty: r.residual_qty,
                      });
                      version = next.version;
                    }
                  })
                }
              >
                Alocar todos os residuais
              </Button>
            ) : null}
            <ul data-testid="customs-shp-residuals">
              {shpResiduals.map((r) => (
                <li key={r.shipment_item_id}>
                  Embarque #{r.shipment_id} · qty {formatQuantity(r.quantity)} · alocado{" "}
                  {formatQuantity(r.allocated_qty)} · residual {formatQuantity(r.residual_qty)}
                  {writable && draft && Number(r.residual_qty) > 0 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={busy}
                      data-testid={`customs-alloc-shp-residual-${r.shipment_item_id}`}
                      onClick={() =>
                        void run(async () => {
                          await allocateShipmentItem(id, {
                            expected_version: process.version,
                            shipment_item_id: r.shipment_item_id,
                            allocated_qty: r.residual_qty,
                          });
                        })
                      }
                    >
                      Alocar residual
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          </>
        )}
        {writable && draft ? (
          <div className="form-actions">
            <p className="muted">Ajuste excepcional — a ação normal é «Alocar residual» na linha.</p>
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
        <NationalizationPanel
          user={user}
          processId={id}
          inventoryTick={inventoryTick}
          onChanged={() => {
            setInventoryTick((t) => t + 1);
            void reload();
          }}
        />
      </div>
      <div data-testid="customs-section-recebimentos">
        <ReceiptPanel
          user={user}
          processId={id}
          refreshTick={inventoryTick}
          onChanged={() => {
            setInventoryTick((t) => t + 1);
            void reload();
          }}
        />
      </div>

      <SectionCard title="Auditoria" data-testid="customs-section-audit">
        <Notice tone="info" data-testid="customs-audit-scope-notice">
          Esta trilha junta o processo, o Numerário, a Doganale, as liberações e os recebimentos.
          Commits de ingestão (Doganale, Print, Numerário PDF) ficam no documento em{" "}
          <Link to="/ingestion">Ingestão</Link> — não são duplicados aqui.
        </Notice>
        {audit.length === 0 ? (
          <p className="muted">Sem eventos de auditoria</p>
        ) : (
          <table className="mini-table" data-testid="customs-audit-table">
            <thead>
              <tr>
                <th>Onde</th>
                <th>Ação</th>
                <th>Quando</th>
                <th>Quem</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((entry, i) => (
                <tr key={entry.id ?? i}>
                  <td>{entry.scope}</td>
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
