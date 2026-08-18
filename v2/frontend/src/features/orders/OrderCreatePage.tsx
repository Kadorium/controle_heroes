import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createProduct, createSupplier, listProducts, type Supplier } from "../catalog/catalogApi";
import { useProductSearch, useSupplierSearch } from "../catalog/useCatalogSearch";
import { addOrderItem, confirmOrder, createOrder, getOrder } from "./ordersApi";
import { canWriteOrders, deriveLineTotal, summarizeLines } from "./orderTotals";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  DateInput,
  ErrorState,
  FormField,
  MoneyDisplay,
  MoneyInput,
  Notice,
  OperationalTable,
  PageHeader,
  SectionCard,
  SelectField,
  TextInput,
  formatQuantity,
} from "../../ui";

type DraftLine = {
  sku: string;
  product_id: number;
  quantity: string;
  unit_price: string;
  unit: string;
};

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

type Props = { user: User };

export function OrderCreatePage({ user }: Props) {
  const navigate = useNavigate();
  const ordersReturn = buildReturnTo("/orders");
  const [code, setCode] = useState("");
  const [orderDate, setOrderDate] = useState(todayIso());
  const [notes, setNotes] = useState("");
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [supplierQ, setSupplierQ] = useState("");
  const [newSupplierName, setNewSupplierName] = useState("");
  const [sku, setSku] = useState("");
  const [skuDescription, setSkuDescription] = useState("");
  const [qty, setQty] = useState("1");
  const [unit, setUnit] = useState("PZ");
  const [price, setPrice] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  /** Após createOrder OK — não recriar em retry. */
  const [persistedOrder, setPersistedOrder] = useState<{ id: number; code: string } | null>(null);
  const products = useProductSearch(sku, { activeOnly: true, limit: 20 });
  const searchedSuppliers = useSupplierSearch(supplierQ, { activeOnly: true, limit: 20 });
  const suppliers = selectedSupplier
    ? [selectedSupplier, ...searchedSuppliers.filter((s) => s.id !== selectedSupplier.id)]
    : searchedSuppliers;

  if (!canWriteOrders(user)) {
    return <ErrorState message="Sem permissão para criar pedidos." />;
  }

  const totals = summarizeLines(lines);

  async function ensureSupplier(): Promise<number> {
    if (supplierId !== "") return Number(supplierId);
    if (!newSupplierName.trim()) throw new Error("Informe ou crie um fornecedor");
    const s = await createSupplier({ name: newSupplierName.trim() });
    setSelectedSupplier(s);
    setSupplierId(s.id);
    return s.id;
  }

  async function addLine() {
    setError(null);
    const wanted = sku.trim();
    let match = products.find((p) => p.sku.toLowerCase() === wanted.toLowerCase());
    if (!match && wanted) {
      const rows = await listProducts(wanted, { activeOnly: true, limit: 20 });
      match = rows.find((p) => p.sku.toLowerCase() === wanted.toLowerCase());
    }
    if (!match) {
      setError("SKU não encontrado — crie o produto abaixo ou escolha um existente");
      return;
    }
    if (!qty.trim() || Number(qty) <= 0) {
      setError("Quantidade inválida");
      return;
    }
    setLines((prev) => [
      ...prev,
      {
        sku: match.sku,
        product_id: match.id,
        quantity: qty.trim(),
        unit: unit.trim() || "PZ",
        unit_price: price.trim() === "" ? "" : price.trim(),
      },
    ]);
    setSku("");
    setSkuDescription("");
    setQty("1");
    setUnit("PZ");
    setPrice("");
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index));
  }

  async function createSku() {
    setError(null);
    const desc = skuDescription.trim();
    if (!sku.trim()) {
      setError("Informe o SKU");
      return;
    }
    if (!desc) {
      setError("Descrição é obrigatória para criar o produto");
      return;
    }
    try {
      const p = await createProduct({ sku: sku.trim(), description: desc });
      setSku(p.sku);
      setSkuDescription(p.description);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar SKU");
    }
  }

  async function saveDraft(andConfirm: boolean) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      if (!code.trim()) throw new Error("Código do pedido é obrigatório");
      if (lines.length === 0) throw new Error("Adicione ao menos um item");

      let order: Awaited<ReturnType<typeof createOrder>>;
      let startIdx = 0;
      if (persistedOrder) {
        order = await getOrder(persistedOrder.id);
        startIdx = order.items?.length ?? 0;
      } else {
        const sid = await ensureSupplier();
        order = await createOrder({
          code: code.trim(),
          supplier_id: sid,
          currency: "EUR",
          order_date: orderDate || null,
          notes: notes.trim() || null,
        });
        setPersistedOrder({ id: order.id, code: order.code });
        startIdx = 0;
      }

      for (let i = startIdx; i < lines.length; i++) {
        const line = lines[i];
        order = await addOrderItem(order.id, {
          expected_version: order.version,
          product_id: line.product_id,
          quantity: line.quantity,
          unit: line.unit || null,
          unit_price: line.unit_price === "" ? null : line.unit_price,
        });
      }
      if (andConfirm) {
        order = await confirmOrder(order.id, order.version);
        setConfirmOpen(false);
        navigate(`/orders/${order.id}`);
      } else {
        setConfirmOpen(false);
        navigate(`/orders/${order.id}/commercial`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao salvar";
      if (persistedOrder) {
        setError(
          `${msg} — Rascunho já salvo (${persistedOrder.code}). Continue em Abrir comercial sem criar outro pedido.`,
        );
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense page-form" data-testid="order-create-page">
      <ContextBreadcrumb
        items={[
          { label: "Compras", to: ordersReturn },
          { label: "Pedidos", to: ordersReturn },
          { label: "Novo pedido" },
        ]}
      />
      <PageHeader
        title="Novo pedido"
        subtitle="Rascunho comercial · preço ausente não é zero"
        actions={
          <Link className="ui-button ui-button--secondary" to={ordersReturn}>
            Voltar à fila
          </Link>
        }
      />
      {persistedOrder ? (
        <Notice tone="info" data-testid="order-partial-draft">
          Rascunho salvo: {persistedOrder.code}. Novas tentativas não criam outro pedido.{" "}
          <Link to={`/orders/${persistedOrder.id}/commercial`}>Abrir comercial</Link>
        </Notice>
      ) : null}
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}

      <SectionCard title="Dados do pedido">
        <div className="form-grid">
          <FormField label="Código / Nº pedido" htmlFor="order-code" required>
            <TextInput
              id="order-code"
              data-testid="order-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="ex.: 758"
              required
            />
          </FormField>
          <FormField label="Fornecedor" htmlFor="order-supplier-q">
            <TextInput
              id="order-supplier-q"
              data-testid="order-supplier-search"
              placeholder="Buscar fornecedor…"
              value={supplierQ}
              onChange={(e) => setSupplierQ(e.target.value)}
            />
          </FormField>
          <FormField label="Selecionado" htmlFor="order-supplier">
            <SelectField
              id="order-supplier"
              data-testid="order-supplier"
              value={supplierId === "" ? "" : String(supplierId)}
              onChange={(e) => {
                const next = e.target.value ? Number(e.target.value) : "";
                setSupplierId(next);
                setSelectedSupplier(
                  next === "" ? null : suppliers.find((s) => s.id === next) ?? selectedSupplier,
                );
              }}
              options={[
                { value: "", label: "— criar novo —" },
                ...suppliers.map((s) => ({ value: String(s.id), label: s.name })),
              ]}
            />
          </FormField>
          {supplierId === "" ? (
            <FormField label="Novo fornecedor" htmlFor="new-supplier-name">
              <TextInput
                id="new-supplier-name"
                data-testid="new-supplier-name"
                value={newSupplierName}
                onChange={(e) => setNewSupplierName(e.target.value)}
              />
            </FormField>
          ) : null}
          <FormField label="Data do pedido" htmlFor="order-date" hint="dd/mm/aaaa" required>
            <DateInput
              id="order-date"
              data-testid="order-date"
              value={orderDate}
              onChange={(e) => setOrderDate(e.target.value)}
            />
          </FormField>
          <FormField label="Notas" htmlFor="order-notes" className="span-2">
            <TextInput
              id="order-notes"
              data-testid="order-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Observações documentais (opcional)"
            />
          </FormField>
        </div>
      </SectionCard>

      <SectionCard title="Itens">
        <div className="line-row">
          <TextInput
            data-testid="line-sku"
            placeholder="SKU"
            value={sku}
            onChange={(e) => setSku(e.target.value)}
            list="sku-list"
          />
          <datalist id="sku-list">
            {products.map((p) => (
              <option key={p.id} value={p.sku}>
                {p.description}
              </option>
            ))}
          </datalist>
          <TextInput
            data-testid="line-sku-description"
            placeholder="Descrição (obrigatória ao criar)"
            value={skuDescription}
            onChange={(e) => setSkuDescription(e.target.value)}
          />
          <TextInput
            data-testid="line-qty"
            placeholder="Qtd"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          <TextInput
            data-testid="line-unit"
            placeholder="UM (PZ)"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          />
          <MoneyInput
            data-testid="line-price"
            currency="EUR"
            value={price}
            onValueChange={setPrice}
            placeholder="Preço (opcional)"
          />
          <Button type="button" onClick={() => void addLine()}>
            Adicionar linha
          </Button>
          <Button type="button" variant="secondary" onClick={() => void createSku()}>
            Criar SKU
          </Button>
        </div>
        <OperationalTable density="standard">
          <thead>
            <tr>
              <th>SKU</th>
              <th className="num">Qtd</th>
              <th>UM</th>
              <th className="num">Preço</th>
              <th className="num">Total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => {
              const total = deriveLineTotal(l.quantity, l.unit_price === "" ? null : l.unit_price);
              return (
                <tr key={`${l.sku}-${i}`}>
                  <td>{l.sku}</td>
                  <td className="num">{formatQuantity(l.quantity)}</td>
                  <td>{l.unit}</td>
                  <td className="num">
                    {l.unit_price === "" ? (
                      <span className="muted">Sem preço</span>
                    ) : (
                      <MoneyDisplay amount={l.unit_price} currency="EUR" />
                    )}
                  </td>
                  <td className="num">
                    {total == null ? "—" : <MoneyDisplay amount={total} currency="EUR" />}
                  </td>
                  <td>
                    <Button type="button" variant="ghost" onClick={() => removeLine(i)}>
                      Remover
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </OperationalTable>
        <p data-testid="commercial-total">
          Total comercial:{" "}
          {totals.commercial_total == null ? (
            "—"
          ) : (
            <MoneyDisplay amount={totals.commercial_total} currency="EUR" />
          )}
          {totals.unpriced_item_count > 0 ? (
            <span className="muted">
              {" "}
              (incompleto · {totals.unpriced_item_count} sem preço · subtotal{" "}
              <MoneyDisplay amount={totals.priced_subtotal} currency="EUR" />)
            </span>
          ) : null}
        </p>
      </SectionCard>

      <div className="actions">
        <Button
          type="button"
          variant="secondary"
          busy={busy}
          data-testid="save-draft"
          onClick={() => void saveDraft(false)}
        >
          Salvar rascunho
        </Button>
        <Button
          type="button"
          busy={busy}
          data-testid="save-confirm"
          onClick={() => setConfirmOpen(true)}
        >
          Salvar e confirmar
        </Button>
      </div>

      <ConfirmationModal
        open={confirmOpen}
        title="Confirmar pedido"
        confirmLabel="Confirmar"
        busy={busy}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void saveDraft(true)}
      >
        <p>
          Após confirmar, o pedido fica somente leitura no comercial. Itens sem preço permanecem
          sem valor (não zero). Confirma?
        </p>
        <p data-testid="confirm-commercial-total">
          Total:{" "}
          {totals.commercial_total == null ? (
            "—"
          ) : (
            <MoneyDisplay amount={totals.commercial_total} currency="EUR" />
          )}
          {totals.unpriced_item_count > 0 ? ` · ${totals.unpriced_item_count} sem preço` : ""}
        </p>
      </ConfirmationModal>
    </section>
  );
}
