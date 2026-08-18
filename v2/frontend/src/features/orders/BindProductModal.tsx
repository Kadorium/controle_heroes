import { useEffect, useMemo, useState } from "react";
import { createProduct, listProducts } from "../catalog/catalogApi";
import { useProductSearch } from "../catalog/useCatalogSearch";
import {
  Button,
  ConfirmationModal,
  FormField,
  Notice,
  TextInput,
  formatQuantity,
} from "../../ui";

const IV_SKU_RE = /^I\.V\./i;

export type BindProductLine = {
  id: number;
  external_code: string | null;
  description_snapshot: string;
  quantity: string;
};

type Props = {
  open: boolean;
  orderId: number;
  expectedVersion: number;
  line: BindProductLine | null;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: (productId: number) => Promise<void>;
};

function isIvSku(sku: string): boolean {
  return IV_SKU_RE.test(sku.trim());
}

export function bindProductErrorMessage(err: unknown): string {
  const status = (err as Error & { status?: number }).status;
  const code = (err as Error & { code?: string }).code;
  if (code === "line_already_invoiced") {
    return "Esta linha já possui fatura emitida e não pode ser vinculada.";
  }
  if (code === "invalid_product") {
    return "Produto não encontrado ou inativo.";
  }
  if (code === "invalid_transition" || status === 409) {
    return "Vínculo só é permitido em pedido confirmado.";
  }
  if (status != null && status >= 500) {
    return "Não foi possível vincular o produto. Tente de novo.";
  }
  return err instanceof Error ? err.message : "Não foi possível vincular o produto. Tente de novo.";
}

export function BindProductModal({
  open,
  orderId: _orderId,
  expectedVersion: _expectedVersion,
  line,
  busy = false,
  onCancel,
  onConfirm,
}: Props) {
  const [skuQuery, setSkuQuery] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const products = useProductSearch(open ? skuQuery : "", { activeOnly: true, limit: 20 });

  useEffect(() => {
    if (!open) return;
    setSkuQuery("");
    setNewDescription("");
    setLocalError(null);
  }, [open, line?.id]);

  const match = useMemo(() => {
    const q = skuQuery.trim().toLowerCase();
    if (!q) return undefined;
    return products.find((p) => p.sku.toLowerCase() === q && p.is_active);
  }, [products, skuQuery]);

  const showCreate = skuQuery.trim().length > 0 && !match && !isIvSku(skuQuery);

  async function onCreateInline() {
    setLocalError(null);
    const sku = skuQuery.trim();
    if (!sku) {
      setLocalError("Informe o SKU do produto");
      return;
    }
    if (isIvSku(sku)) {
      setLocalError("SKU de catálogo não pode ser I.V.* — use um código de categoria próprio.");
      return;
    }
    const desc = newDescription.trim();
    if (!desc) {
      setLocalError("Descrição é obrigatória");
      return;
    }
    setCreating(true);
    try {
      const p = await createProduct({ sku, description: desc });
      setSkuQuery(p.sku);
      setNewDescription(p.description);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "Erro ao criar produto");
    } finally {
      setCreating(false);
    }
  }

  async function handleConfirm() {
    setLocalError(null);
    const sku = skuQuery.trim();
    if (isIvSku(sku)) {
      setLocalError("SKU de catálogo não pode ser I.V.* — use um código de categoria próprio.");
      return;
    }
    let found = match;
    if (!found && sku) {
      const rows = await listProducts(sku, { activeOnly: true, limit: 20 });
      found = rows.find((p) => p.sku.toLowerCase() === sku.toLowerCase() && p.is_active);
    }
    if (!found) {
      setLocalError("Selecione um produto do catálogo ou crie um novo antes de confirmar.");
      return;
    }
    setConfirmBusy(true);
    try {
      await onConfirm(found.id);
    } catch (e) {
      setLocalError(bindProductErrorMessage(e));
    } finally {
      setConfirmBusy(false);
    }
  }

  if (!line) return null;

  return (
    <ConfirmationModal
      open={open}
      title="Vincular produto"
      confirmLabel="Confirmar"
      cancelLabel="Cancelar"
      busy={busy || confirmBusy || creating}
      onCancel={onCancel}
      onConfirm={() => void handleConfirm()}
      initialFocusSelector='[data-testid="bind-product-sku"]'
    >
      <div className="stack" data-testid="bind-product-modal">
        <p className="muted" data-testid="bind-product-line-summary">
          Linha atual: <strong>{line.external_code || "—"}</strong>
          {" · "}
          {line.description_snapshot}
          {" · "}
          qtd {formatQuantity(line.quantity)}
        </p>

        {localError ? (
          <Notice tone="danger" data-testid="bind-product-error">
            {localError}
          </Notice>
        ) : null}

        <FormField label="Produto do catálogo" htmlFor="bind-product-sku" hint="Busque pelo SKU">
          <TextInput
            id="bind-product-sku"
            data-testid="bind-product-sku"
            placeholder="Buscar SKU no catálogo…"
            value={skuQuery}
            list="bind-product-sku-list"
            onChange={(e) => setSkuQuery(e.target.value)}
            disabled={busy || confirmBusy}
          />
          <datalist id="bind-product-sku-list">
            {products
              .filter((p) => p.is_active)
              .map((p) => (
                <option key={p.id} value={p.sku}>
                  {p.description}
                </option>
              ))}
          </datalist>
        </FormField>

        {match ? (
          <p data-testid="bind-product-match">
            Selecionado: <strong>{match.sku}</strong> — {match.description}
          </p>
        ) : null}

        {showCreate ? (
          <div className="stack" data-testid="bind-product-create">
            <FormField label="Descrição do novo produto" htmlFor="bind-product-new-desc">
              <TextInput
                id="bind-product-new-desc"
                data-testid="bind-product-new-desc"
                placeholder="Descrição (obrigatória)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                disabled={busy || creating}
              />
            </FormField>
            <Button
              type="button"
              variant="secondary"
              busy={creating}
              data-testid="bind-product-create-btn"
              onClick={() => void onCreateInline()}
              disabled={!newDescription.trim()}
            >
              Criar produto no catálogo
            </Button>
          </div>
        ) : null}
      </div>
    </ConfirmationModal>
  );
}
