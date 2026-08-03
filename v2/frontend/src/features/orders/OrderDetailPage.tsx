import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import type { User } from "../auth/types";
import {
  cancelOrder,
  confirmOrder,
  getOrder,
  updateOrder,
  updateOrderItem,
  uploadOrderDocument,
  type Order,
} from "./ordersApi";
import { canCancelOrders, canWriteOrders } from "./orderTotals";
import { OrderInvoicesPanel } from "../billing/InvoiceDetailPage";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
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

export function OrderDetailPage({ user }: Props) {
  const { orderId } = useParams();
  const id = Number(orderId);
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [orderDate, setOrderDate] = useState("");
  const [notes, setNotes] = useState("");
  const ordersReturn = buildReturnTo("/orders");
  const cockpitHref = `/orders/${id}`;

  async function reload() {
    const data = await getOrder(id);
    setOrder(data);
    setOrderDate(data.order_date ?? "");
    setNotes(data.notes ?? "");
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
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error && !order) return <ErrorState message={error} />;
  if (!order) return <LoadingState message="Carregando pedido…" />;

  const editable = order.status === "DRAFT" && canWriteOrders(user);
  const canCancel =
    (order.status === "DRAFT" && canWriteOrders(user)) ||
    (order.status === "CONFIRMED" && canCancelOrders(user));
  const canUploadDocs = canWriteOrders(user) && order.status !== "CANCELLED";

  async function onConfirm() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      setOrder(await confirmOrder(order!.id, order!.version));
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
            <Link className="ui-button ui-button--secondary" to={cockpitHref}>
              Cockpit
            </Link>
            <Link className="ui-button ui-button--secondary" to={ordersReturn}>
              Voltar à fila
            </Link>
            {editable ? (
              <Button busy={busy} data-testid="confirm-order" onClick={() => void onConfirm()}>
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

      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}

      {!editable && order.status !== "DRAFT" ? (
        <Notice tone="info" data-testid="readonly-banner">
          Pedido somente leitura — <StatusBadge status={order.status} entity="order" />
        </Notice>
      ) : null}

      <SectionCard title="Cabeçalho" data-testid="order-header">
        {editable ? (
          <div className="form-grid">
            <FormField label="Data do pedido" htmlFor="detail-order-date" hint="dd/mm/aaaa">
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
                <th>SKU</th>
                <th>Descrição</th>
                <th className="num">Qtd</th>
                <th>UM</th>
                <th className="num">Preço</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {order.items?.map((i) => (
                <tr key={i.id}>
                  <td>{i.sku_snapshot}</td>
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
                </tr>
              ))}
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
          <FileUpload
            data-testid="order-doc-upload"
            label="Anexar documento do pedido"
            disabled={uploadBusy}
            onFileChange={(file) => {
              if (file) void onUpload(file);
            }}
          />
        ) : null}
      </SectionCard>

      <OrderInvoicesPanel user={user} orderId={order.id} orderStatus={order.status} />

      <Button variant="secondary" onClick={() => void reload()}>
        Atualizar
      </Button>
    </section>
  );
}
