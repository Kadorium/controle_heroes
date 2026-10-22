import { Link, useParams } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  addOrderItem,
  bindCommitmentProduct,
  cancelOrder,
  closeOrder,
  confirmOrder,
  getOrder,
  listOrders,
  reopenOrder,
  updateOrder,
  updateOrderItem,
  uploadOrderDocument,
  type Order,
} from "./ordersApi";
import { canCancelOrders, canWriteOrders } from "./orderTotals";
import { BindProductModal, type BindProductLine } from "./BindProductModal";
import { OrderInvoicesPanel } from "../billing/InvoiceDetailPage";
import { invoicedQuantities, type OrderQtyRow } from "../billing/billingApi";
import { OrderAdvancesPanel } from "../treasury/OrderAdvancesPanel";
import { OrderPaymentSchedulePanel } from "./OrderPaymentSchedulePanel";
import { fetchOrderSummary } from "../reporting/reportingApi";
import { buildReturnTo } from "../../navigation/returnState";
import { OrderPdfPanel } from "./OrderPdfPanel";
import { canExtractOrdine, discardOrdineIntake, type OrdineIntakeSession } from "./ordinePdfIntake";
import type { OrdineFormDraft } from "./mapOrdinePreviewToForm";
import {
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  DateInput,
  DocumentActions,
  EmptyState,
  ErrorState,
  FileUpload,
  FormField,
  LoadingState,
  MoneyDisplay,
  Notice,
  OperationalTable,
  PageHeader,
  SectionCard,
  StatusBadge,
  TextInput,
  formatDateOnly,
  formatMoney,
  formatQuantity,
} from "../../ui";

type Props = { user: User };

function hasOpenPayableBalance(raw: string | null | undefined): boolean {
  if (raw == null || raw === "") return false;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0;
}

export function OrderDetailPage({ user }: Props) {
  const { orderId } = useParams();
  const id = Number(orderId);
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [closeReason, setCloseReason] = useState("");
  const [reopenReason, setReopenReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [orderDate, setOrderDate] = useState("");
  const [notes, setNotes] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [reopenOpen, setReopenOpen] = useState(false);
  const [qtys, setQtys] = useState<OrderQtyRow[]>([]);
  const [bindLine, setBindLine] = useState<BindProductLine | null>(null);
  const [bindBusy, setBindBusy] = useState(false);
  const [openPayableBalance, setOpenPayableBalance] = useState<string | null>(null);
  const ordersReturn = buildReturnTo("/orders");
  const cockpitHref = `/orders/${id}`;

  const reloadQtys = useCallback(async (orderIdNum: number) => {
    setQtys(await invoicedQuantities(orderIdNum));
  }, []);

  async function reload() {
    const data = await getOrder(id);
    setOrder(data);
    setOrderDate(data.order_date ?? "");
    setNotes(data.notes ?? "");
    await reloadQtys(data.id);
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getOrder(id);
        if (!cancelled) {
          setOrder(data);
          setOrderDate(data.order_date ?? "");
          setNotes(data.notes ?? "");
        }
        const qtyRows = await invoicedQuantities(id);
        if (!cancelled) setQtys(qtyRows);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if (!order || (order.status !== "CONFIRMED" && order.status !== "CLOSED")) {
      setOpenPayableBalance(null);
      return;
    }
    let cancelled = false;
    void fetchOrderSummary(order.id)
      .then((summary) => {
        if (!cancelled) setOpenPayableBalance(summary.kpis.balance ?? "0");
      })
      .catch(() => {
        if (!cancelled) setOpenPayableBalance(null);
      });
    return () => {
      cancelled = true;
    };
  }, [order?.id, order?.status, order?.version]);

  useEffect(() => {
    if (!order) return;
    if (window.location.hash === "#order-advances") {
      const el = document.getElementById("order-advances");
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [order]);

  if (error && !order) return <ErrorState message={error} />;
  if (!order) return <LoadingState message="Carregando pedido…" />;

  const editable = order.status === "DRAFT" && canWriteOrders(user);
  const canCancel =
    (order.status === "DRAFT" && canWriteOrders(user)) ||
    (order.status === "CONFIRMED" && canCancelOrders(user));
  const canUploadDocs =
    canWriteOrders(user) && order.status !== "CANCELLED" && order.status !== "CLOSED";
  const canBind =
    order.status === "CONFIRMED" && canWriteOrders(user);
  const commitmentCount = (order.items ?? []).filter(
    (i) => String(i.line_kind ?? "").toUpperCase() === "COMMITMENT",
  ).length;
  const hasCommitmentLines = commitmentCount > 0;
  const canClose =
    order.status === "CONFIRMED" && canWriteOrders(user) && !hasCommitmentLines;
  const canReopen = order.status === "CLOSED" && canWriteOrders(user);
  const hasOpenAp = hasOpenPayableBalance(openPayableBalance);
  const openApNotice = hasOpenAp && openPayableBalance ? (
    <Notice tone="warning" data-testid="close-open-ap-notice">
      {order.status === "CLOSED"
        ? `Pedido encerrado com ${formatMoney(openPayableBalance, order.currency)} em contas a pagar em aberto. Encerrar o comercial não quita essas obrigações.`
        : `Há ${formatMoney(openPayableBalance, order.currency)} em contas a pagar em aberto. Encerrar o pedido comercial não quita essas obrigações.`}
    </Notice>
  ) : null;
  const qtyByItem = new Map(qtys.map((q) => [q.order_item_id, q]));

  async function onBindConfirm(productId: number) {
    if (!order || !bindLine) return;
    setBindBusy(true);
    setError(null);
    try {
      const next = await bindCommitmentProduct(order.id, bindLine.id, {
        expected_version: order.version,
        product_id: productId,
      });
      setOrder(next);
      await reloadQtys(next.id);
      setBindLine(null);
    } finally {
      setBindBusy(false);
    }
  }

  async function onConfirm() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      setOrder(await confirmOrder(order!.id, order!.version));
      setConfirmOpen(false);
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          await reload();
          setError(
            "Conflito de versão — estado recarregado. Revise e tente de novo (campos locais preservados quando aplicável).",
          );
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    if (busy) return;
    const trimmed = reason.trim();
    if (order!.status === "CONFIRMED" && !trimmed) {
      setError("Informe o motivo do cancelamento");
      return;
    }
    if (trimmed.length > 64) {
      setError("Motivo do cancelamento: máximo 64 caracteres");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setOrder(
        await cancelOrder(
          order!.id,
          order!.version,
          order!.status === "CONFIRMED" ? trimmed : trimmed || undefined,
        ),
      );
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          await reload();
          setError(
            "Conflito de versão — estado recarregado. Motivo do cancelamento preservado; tente de novo.",
          );
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onClose() {
    if (busy) return;
    const trimmed = closeReason.trim();
    if (!trimmed) {
      setError("Informe o motivo do encerramento");
      return;
    }
    if (trimmed.length > 64) {
      setError("Motivo do encerramento: máximo 64 caracteres");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setOrder(await closeOrder(order!.id, order!.version, trimmed));
      setCloseOpen(false);
      setCloseReason("");
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          await reload();
          setError("Conflito de versão — estado recarregado. Tente encerrar de novo.");
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onReopen() {
    if (busy) return;
    const trimmed = reopenReason.trim();
    if (!trimmed) {
      setError("Informe o motivo da reabertura");
      return;
    }
    if (trimmed.length > 64) {
      setError("Motivo da reabertura: máximo 64 caracteres");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setOrder(await reopenOrder(order!.id, order!.version, trimmed));
      setReopenOpen(false);
      setReopenReason("");
    } catch (e) {
      const status = (e as Error & { status?: number }).status;
      if (status === 409) {
        try {
          await reload();
          setError("Conflito de versão — estado recarregado. Tente reabrir de novo.");
        } catch {
          setError(e instanceof Error ? e.message : "Erro");
        }
      } else {
        setError(e instanceof Error ? e.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onSaveHeader() {
    if (!editable || busy) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateOrder(order!.id, {
        expected_version: order!.version,
        order_date: orderDate || null,
        notes: notes.trim() || null,
      });
      setOrder(updated);
      setOrderDate(updated.order_date ?? "");
      setNotes(updated.notes ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(file: File) {
    setUploadBusy(true);
    setError(null);
    try {
      await uploadOrderDocument(id, file);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setUploadBusy(false);
    }
  }

  const unpricedCount = order.unpriced_item_count ?? 0;
  const supplierName = order.supplier_name?.trim();
  const supplierLabel = !supplierName
    ? "Fornecedor não encontrado"
    : order.supplier_is_active === false
      ? `${supplierName} (inativo)`
      : supplierName;

  return (
    <section className="panel dense page-detail detail-shell" data-testid="order-detail">
      <ContextBreadcrumb
        items={[
          { label: "Compras", to: ordersReturn },
          { label: "Pedidos", to: ordersReturn },
          { label: order.code, to: cockpitHref },
          { label: "Comercial" },
        ]}
      />
      <PageHeader
        title={`Pedido ${order.code}`}
        subtitle={[supplierLabel, order.currency, formatDateOnly(order.order_date)]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <div className="stack-row page-header-actions">
            <Link
              className="ui-button ui-button--secondary"
              to={cockpitHref}
              data-testid="commercial-cockpit-link"
            >
              Cockpit
            </Link>
            <Link className="ui-button ui-button--secondary" to={ordersReturn}>
              Voltar à fila
            </Link>
            {editable ? (
              <Button
                busy={busy}
                data-testid="confirm-order"
                onClick={() => setConfirmOpen(true)}
              >
                Confirmar
              </Button>
            ) : null}
            {canCancel ? (
              <>
                {order.status === "CONFIRMED" ? (
                  <FormField label="Motivo do cancelamento" htmlFor="cancel-reason">
                    <TextInput
                      id="cancel-reason"
                      data-testid="cancel-reason"
                      value={reason}
                      maxLength={64}
                      placeholder="Descreva o motivo"
                      onChange={(e) => setReason(e.target.value)}
                      aria-label="Motivo do cancelamento"
                    />
                  </FormField>
                ) : null}
                <Button
                  variant="secondary"
                  busy={busy}
                  data-testid="cancel-order"
                  onClick={() => void onCancel()}
                >
                  Cancelar
                </Button>
              </>
            ) : null}
            {canClose ? (
              <Button
                variant="secondary"
                busy={busy}
                data-testid="close-order"
                onClick={() => setCloseOpen(true)}
              >
                Encerrar pedido
              </Button>
            ) : null}
            {canReopen ? (
              <Button
                variant="secondary"
                busy={busy}
                data-testid="reopen-order"
                onClick={() => setReopenOpen(true)}
              >
                Reabrir
              </Button>
            ) : null}
          </div>
        }
      />

      <div className="stack-row">
        <StatusBadge status={order.status} entity="order" />
        <span className="muted">Revisão {order.version}</span>
      </div>

      {order.status === "CANCELLED" && order.cancel_reason_code ? (
        <Notice tone="info" data-testid="cancel-reason-display">
          Motivo do cancelamento: {order.cancel_reason_code}
        </Notice>
      ) : null}

      {order.status === "CLOSED" && order.close_reason_code ? (
        <Notice tone="info" data-testid="close-reason-display">
          Motivo do encerramento: {order.close_reason_code}
        </Notice>
      ) : null}

      {order.status === "CONFIRMED" && hasCommitmentLines && canWriteOrders(user) ? (
        <Notice tone="info" data-testid="close-blocked-commitment">
          Vincule os compromissos a produtos do catálogo. Sem isso este pedido não fatura, não embarca
          e não entra no estoque — e não pode ser encerrado.
        </Notice>
      ) : null}

      {openApNotice}

      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}

      {editable && canExtractOrdine(user) ? (
        <OrderPdfPanel
          user={user}
          mode="draft"
          onFill={(draft: OrdineFormDraft, session: OrdineIntakeSession) => {
            void (async () => {
              setBusy(true);
              setError(null);
              try {
                if ((order.items?.length ?? 0) > 0) {
                  throw new Error(
                    "Este rascunho já tem itens. Use um rascunho vazio ou crie um novo pedido.",
                  );
                }
                const pdfCode = draft.code.trim();
                if (pdfCode && pdfCode !== order.code) {
                  const rows = await listOrders();
                  const other = rows.find((r) => r.code === pdfCode && r.id !== order.id);
                  if (other) {
                    throw new Error(
                      `Este PDF é o pedido ${pdfCode}, que já existe. Não preenche este rascunho.`,
                    );
                  }
                }
                let next = order;
                for (const line of draft.lines) {
                  if (line.line_kind === "COMMITMENT") {
                    next = await addOrderItem(next.id, {
                      expected_version: next.version,
                      quantity: line.quantity,
                      unit: line.unit || null,
                      unit_price: line.unit_price === "" ? null : line.unit_price,
                      line_kind: "COMMITMENT",
                      external_code: line.sku,
                      description: line.description || line.sku,
                    });
                  } else {
                    next = await addOrderItem(next.id, {
                      expected_version: next.version,
                      product_id: line.product_id ?? undefined,
                      quantity: line.quantity,
                      unit: line.unit || null,
                      unit_price: line.unit_price === "" ? null : line.unit_price,
                      line_kind: "PRODUCT",
                    });
                  }
                }
                await uploadOrderDocument(next.id, session.file);
                await discardOrdineIntake(session);
                setOrder(next);
                await reload();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Não foi possível preencher a partir do PDF.");
              } finally {
                setBusy(false);
              }
            })();
          }}
        />
      ) : null}

      {!editable && order.status !== "DRAFT" ? (
        <Notice tone="info" data-testid="readonly-banner">
          Pedido somente leitura — <StatusBadge status={order.status} entity="order" />
        </Notice>
      ) : null}

      <SectionCard title="Cabeçalho" data-testid="order-header">
        {editable ? (
          <div className="form-grid">
            <FormField label="Data do pedido" htmlFor="detail-order-date" hint={orderDate ? undefined : "dd/mm/aaaa"}>
              <DateInput
                id="detail-order-date"
                data-testid="detail-order-date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
              />
            </FormField>
            <FormField label="Notas" htmlFor="detail-order-notes" className="span-2">
              <TextInput
                id="detail-order-notes"
                data-testid="detail-order-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </FormField>
            <div className="actions">
              <Button
                type="button"
                busy={busy}
                data-testid="save-order-header"
                onClick={() => void onSaveHeader()}
              >
                Salvar cabeçalho
              </Button>
            </div>
          </div>
        ) : (
          <div className="stack">
            <p>
              Data: <strong>{formatDateOnly(order.order_date)}</strong>
            </p>
            <p data-testid="order-notes-readonly">
              Notas: {order.notes?.trim() ? order.notes : "—"}
            </p>
          </div>
        )}
      </SectionCard>

      <SectionCard title="Itens">
        {(order.items?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhum item no pedido" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>SKU / código</th>
                <th>Descrição</th>
                <th className="num">Qtd</th>
                <th>UM</th>
                <th className="num">Preço</th>
                <th className="num">Total</th>
                <th className="num">Disponível</th>
                {canBind ? <th>Ação</th> : null}
              </tr>
            </thead>
            <tbody>
              {order.items?.map((i) => {
                const kind = String(i.line_kind ?? "").toUpperCase();
                const isCommitment = kind === "COMMITMENT";
                const qtyRow = qtyByItem.get(i.id);
                const billable = qtyRow ? Boolean(qtyRow.billable) : !isCommitment;
                const skuDisplay = isCommitment
                  ? i.external_code || i.sku_snapshot
                  : i.sku_snapshot;
                return (
                  <tr key={i.id} data-testid={`order-item-row-${i.id}`}>
                    <td data-testid={`order-item-kind-${i.id}`}>
                      {isCommitment ? "Compromisso" : "Produto"}
                    </td>
                    <td data-testid={`order-item-sku-${i.id}`}>{skuDisplay}</td>
                    <td>{i.description_snapshot}</td>
                    <td className="num">{formatQuantity(i.quantity)}</td>
                    <td data-testid={`order-item-unit-${i.id}`}>
                      {editable ? (
                        <TextInput
                          data-testid={`order-item-unit-edit-${i.id}`}
                          value={i.unit ?? ""}
                          placeholder="PZ"
                          maxLength={16}
                          onChange={(e) => {
                            const items = (order.items ?? []).map((row) =>
                              row.id === i.id ? { ...row, unit: e.target.value || null } : row,
                            );
                            setOrder({ ...order, items });
                          }}
                          onBlur={(e) => {
                            const nextUnit = e.target.value.trim() || null;
                            void (async () => {
                              if (!order) return;
                              setBusy(true);
                              setError(null);
                              try {
                                const next = await updateOrderItem(order.id, i.id, {
                                  expected_version: order.version,
                                  unit: nextUnit,
                                });
                                setOrder(next);
                              } catch (err) {
                                setError(err instanceof Error ? err.message : "Erro");
                              } finally {
                                setBusy(false);
                              }
                            })();
                          }}
                        />
                      ) : (
                        i.unit ?? "—"
                      )}
                    </td>
                    <td className="num">
                      <MoneyDisplay amount={i.unit_price} currency={order.currency} />
                    </td>
                    <td className="num">
                      <MoneyDisplay amount={i.line_total} currency={order.currency} />
                    </td>
                    <td
                      className="num"
                      data-testid={`order-item-available-${i.id}`}
                    >
                      {billable
                        ? formatQuantity(qtyRow?.available_qty ?? i.quantity)
                        : "—"}
                    </td>
                    {canBind ? (
                      <td>
                        {isCommitment ? (
                          <Button
                            type="button"
                            variant="secondary"
                            data-testid={`bind-product-${i.id}`}
                            onClick={() =>
                              setBindLine({
                                id: i.id,
                                external_code: i.external_code ?? null,
                                description_snapshot: i.description_snapshot,
                                quantity: i.quantity,
                              })
                            }
                          >
                            Vincular produto
                          </Button>
                        ) : null}
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </OperationalTable>
        )}
      </SectionCard>

      <p data-testid="detail-commercial-total">
        Total comercial:{" "}
        <MoneyDisplay amount={order.commercial_total} currency={order.currency} />
        {unpricedCount > 0 ? (
          <>
            {" "}
            · incompleto ({unpricedCount} sem preço; subtotal{" "}
            {formatMoney(order.priced_subtotal, order.currency)})
          </>
        ) : null}
      </p>

      <OrderPaymentSchedulePanel
        user={user}
        orderId={order.id}
        orderCurrency={order.currency}
        orderStatus={order.status}
        orderVersion={order.version}
        onSaved={reload}
      />

      {/* Adiantamentos antes de Documentos: upload de câmbio fica no formulário,
          longe do anexo do pedido — evita confundir os dois file inputs (FIN-1C-FIX-1B). */}
      <OrderAdvancesPanel
        user={user}
        orderId={order.id}
        orderCurrency={order.currency}
        orderStatus={order.status}
      />

      <SectionCard title="Documentos" data-testid="order-documents">
        {(order.documents?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhum documento vinculado" />
        ) : (
          <ul className="plain-list">
            {order.documents?.map((d) => (
              <li key={d.id} data-testid={`order-doc-${d.id}`}>
                <DocumentActions
                  documentId={d.id}
                  filename={d.original_filename}
                  mimeType={d.mime_type}
                  data-testid={`order-doc-actions-${d.id}`}
                />
              </li>
            ))}
          </ul>
        )}
        {canUploadDocs ? (
          <>
            <p className="muted" data-testid="order-doc-upload-hint">
              Ordine e anexos do pedido. PDF de câmbio do adiantamento fica no painel
              Adiantamentos acima — não anexar aqui.
            </p>
            <FileUpload
              data-testid="order-doc-upload"
              name="order-document"
              label="Anexar documento do pedido (Ordine e afins)"
              disabled={uploadBusy}
              onFileChange={(file) => {
                if (file) void onUpload(file);
              }}
            />
          </>
        ) : null}
      </SectionCard>

      <OrderInvoicesPanel
        user={user}
        orderId={order.id}
        orderStatus={order.status}
        orderVersion={order.version}
      />

      <Button variant="secondary" onClick={() => void reload()}>
        Atualizar
      </Button>

      <BindProductModal
        open={bindLine != null}
        orderId={order.id}
        expectedVersion={order.version}
        line={bindLine}
        busy={bindBusy}
        onCancel={() => setBindLine(null)}
        onConfirm={onBindConfirm}
      />

      <ConfirmationModal
        open={closeOpen}
        title="Encerrar pedido"
        confirmLabel="Encerrar pedido"
        busy={busy}
        initialFocusSelector="[data-testid='close-reason']"
        onCancel={() => setCloseOpen(false)}
        onConfirm={() => void onClose()}
      >
        {hasOpenAp && openPayableBalance ? (
          <Notice tone="warning" data-testid="close-open-ap-modal-notice">
            Há {formatMoney(openPayableBalance, order.currency)} em contas a pagar em aberto.
            Encerrar o pedido comercial não quita essas obrigações.
          </Notice>
        ) : null}
        <FormField label="Motivo" htmlFor="close-reason" required>
          <TextInput
            id="close-reason"
            data-testid="close-reason"
            value={closeReason}
            maxLength={64}
            placeholder="Descreva o motivo"
            onChange={(e) => setCloseReason(e.target.value)}
            aria-label="Motivo do encerramento"
          />
        </FormField>
      </ConfirmationModal>

      <ConfirmationModal
        open={reopenOpen}
        title="Reabrir pedido"
        confirmLabel="Reabrir"
        busy={busy}
        initialFocusSelector="[data-testid='reopen-reason']"
        onCancel={() => setReopenOpen(false)}
        onConfirm={() => void onReopen()}
      >
        <FormField label="Motivo" htmlFor="reopen-reason" required>
          <TextInput
            id="reopen-reason"
            data-testid="reopen-reason"
            value={reopenReason}
            maxLength={64}
            placeholder="Descreva o motivo"
            onChange={(e) => setReopenReason(e.target.value)}
            aria-label="Motivo da reabertura"
          />
        </FormField>
      </ConfirmationModal>

      <ConfirmationModal
        open={confirmOpen}
        title="Confirmar pedido"
        confirmLabel="Confirmar pedido"
        busy={busy}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void onConfirm()}
      >
        {hasCommitmentLines ? (
          <Notice tone="info" data-testid="confirm-commitment-warning">
            Este pedido tem {commitmentCount}{" "}
            {commitmentCount === 1 ? "linha de compromisso" : "linhas de compromisso"}. Sem produto
            no catálogo elas não faturam, não embarcam e não entram no estoque. Vincule depois de
            confirmar.
          </Notice>
        ) : (
          <p>Confirmar este pedido? Depois da confirmação, ele deixa de ser editável como rascunho.</p>
        )}
      </ConfirmationModal>
    </section>
  );
}
