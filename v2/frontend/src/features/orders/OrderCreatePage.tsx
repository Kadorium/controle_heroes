import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import {
  createProduct,
  createSupplier,
  listProducts,
  listSuppliers,
  type Product,
  type Supplier,
} from "../catalog/catalogApi";
import { addOrderItem, confirmOrder, createOrder } from "./ordersApi";
import { canWriteOrders, deriveLineTotal, summarizeLines } from "./orderTotals";

type DraftLine = { sku: string; product_id: number; quantity: string; unit_price: string };

type Props = { user: User };

export function OrderCreatePage({ user }: Props) {
  const navigate = useNavigate();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [code, setCode] = useState("");
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [newSupplierName, setNewSupplierName] = useState("");
  const [sku, setSku] = useState("");
  const [qty, setQty] = useState("1");
  const [price, setPrice] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        setSuppliers(await listSuppliers());
        setProducts(await listProducts());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Erro ao carregar catálogo");
      }
    })();
  }, []);

  if (!canWriteOrders(user)) {
    return <div className="error">Sem permissão para criar ordens.</div>;
  }

  const totals = summarizeLines(lines);

  async function ensureSupplier(): Promise<number> {
    if (supplierId !== "") return Number(supplierId);
    if (!newSupplierName.trim()) throw new Error("Informe ou crie um fornecedor");
    const s = await createSupplier({ name: newSupplierName.trim() });
    setSuppliers((prev) => [...prev, s]);
    setSupplierId(s.id);
    return s.id;
  }

  function addLine() {
    setError(null);
    const match = products.find((p) => p.sku.toLowerCase() === sku.trim().toLowerCase());
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
        unit_price: price.trim() === "" ? "" : price.trim(),
      },
    ]);
    setSku("");
    setQty("1");
    setPrice("");
  }

  async function createSku() {
    setError(null);
    try {
      const p = await createProduct({ sku: sku.trim(), description: sku.trim() });
      setProducts((prev) => [...prev, p]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar SKU");
    }
  }

  async function saveDraft(andConfirm: boolean) {
    setBusy(true);
    setError(null);
    try {
      const sid = await ensureSupplier();
      if (!code.trim()) throw new Error("Código da ordem é obrigatório");
      if (lines.length === 0) throw new Error("Adicione ao menos um item");
      let order = await createOrder({ code: code.trim(), supplier_id: sid, currency: "EUR" });
      for (const line of lines) {
        order = await addOrderItem(order.id, {
          expected_version: order.version,
          product_id: line.product_id,
          quantity: line.quantity,
          unit_price: line.unit_price === "" ? null : line.unit_price,
        });
      }
      if (andConfirm) {
        order = await confirmOrder(order.id, order.version);
      }
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h1>Nova ordem</h1>
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : null}

      <label>
        Código / Nº ordem
        <input
          data-testid="order-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="ex.: 758"
          required
        />
      </label>

      <label>
        Fornecedor
        <select
          data-testid="order-supplier"
          value={supplierId === "" ? "" : String(supplierId)}
          onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">— criar novo —</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      {supplierId === "" ? (
        <label>
          Novo fornecedor
          <input
            data-testid="new-supplier-name"
            value={newSupplierName}
            onChange={(e) => setNewSupplierName(e.target.value)}
          />
        </label>
      ) : null}

      <div className="line-editor">
        <h2>Itens</h2>
        <div className="line-row">
          <input
            data-testid="line-sku"
            placeholder="SKU"
            value={sku}
            onChange={(e) => setSku(e.target.value)}
            list="sku-list"
          />
          <datalist id="sku-list">
            {products.map((p) => (
              <option key={p.id} value={p.sku} />
            ))}
          </datalist>
          <input
            data-testid="line-qty"
            placeholder="Qtd"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          <input
            data-testid="line-price"
            placeholder="Preço (vazio = null)"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
          <button type="button" onClick={addLine}>
            Adicionar linha
          </button>
          <button type="button" className="btn-secondary" onClick={() => void createSku()}>
            Criar SKU
          </button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Qtd</th>
              <th>Preço</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={`${l.sku}-${i}`}>
                <td>{l.sku}</td>
                <td>{l.quantity}</td>
                <td>{l.unit_price === "" ? "—" : l.unit_price}</td>
                <td>{deriveLineTotal(l.quantity, l.unit_price === "" ? null : l.unit_price) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p data-testid="commercial-total">
          Total comercial: {totals.commercial_total ?? "—"}
          {totals.unpriced_item_count > 0
            ? ` (incompleto · ${totals.unpriced_item_count} sem preço · subtotal ${totals.priced_subtotal})`
            : null}
        </p>
      </div>

      <div className="actions">
        <button type="button" disabled={busy} data-testid="save-draft" onClick={() => void saveDraft(false)}>
          Salvar DRAFT
        </button>
        <button type="button" disabled={busy} data-testid="save-confirm" onClick={() => void saveDraft(true)}>
          Salvar e confirmar
        </button>
      </div>
    </section>
  );
}
