import { useEffect, useState } from "react";
import { Button } from "../../components";
import { productsApi, type Product } from "../../api";

interface Props {
  open: boolean;
  product: Product | null;
  onClose: () => void;
  onSaved: () => void;
  onOpenDetail: (id: number) => void;
}

export function ProductQuickDrawer({ open, product, onClose, onSaved, onOpenDetail }: Props) {
  const isNew = !product?.id;
  const [sku, setSku] = useState("");
  const [description, setDescription] = useState("");
  const [productGroup, setProductGroup] = useState("Sem grupo");
  const [lifecycleStatus, setLifecycleStatus] = useState("ACTIVE");
  const [ncm, setNcm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    setSku(product?.sku_code ?? "");
    setDescription(product?.description ?? "");
    setProductGroup(product?.product_group ?? "Sem grupo");
    setLifecycleStatus(product?.lifecycle_status ?? "ACTIVE");
    setNcm(product?.ncm ?? "");
    setError("");
  }, [open, product]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      if (isNew) {
        await productsApi.create({
          sku_code: sku.trim(),
          description: description.trim(),
          product_group: productGroup.trim() || "Sem grupo",
          lifecycle_status: lifecycleStatus,
          ncm: ncm.trim() || null,
        });
      } else if (product) {
        await productsApi.update(product.id, {
          description: description.trim(),
          product_group: productGroup.trim(),
          lifecycle_status: lifecycleStatus,
          ncm: ncm.trim() || null,
        });
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  if (!open) return null;

  return (
    <>
      <div className={`drawer-back${open ? " drawer-back--show" : ""}`} onClick={onClose} />
      <aside className={`drawer drawer--wide${open ? " drawer--show" : ""}`} aria-hidden={!open}>
        <h3>{isNew ? "Novo produto" : "Editar produto"}</h3>
        {error && <p className="error">{error}</p>}
        <div className="form-stack">
          <label>
            SKU
            <input value={sku} onChange={(e) => setSku(e.target.value)} disabled={!isNew} required />
          </label>
          <label>
            Nome
            <input value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <label>
            Grupo
            <input value={productGroup} onChange={(e) => setProductGroup(e.target.value)} required />
          </label>
          <label>
            Status
            <select value={lifecycleStatus} onChange={(e) => setLifecycleStatus(e.target.value)}>
              <option value="ACTIVE">Ativo</option>
              <option value="DISCONTINUED">Descontinuado</option>
              <option value="DRAFT">Rascunho</option>
            </select>
          </label>
          <label>
            NCM
            <input value={ncm} onChange={(e) => setNcm(e.target.value)} placeholder="Opcional" />
          </label>
        </div>
        {!isNew && product && (
          <p className="drawer__sub">
            {product.orders_count ?? 0} ordem(ns) ·{" "}
            <button type="button" className="link-btn" onClick={() => onOpenDetail(product.id)}>
              Abrir detalhe
            </button>
          </p>
        )}
        <div className="drawer__actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="button" onClick={() => void save()} disabled={saving}>
            Salvar
          </Button>
        </div>
      </aside>
    </>
  );
}
