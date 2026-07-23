import { useEffect, useState } from "react";
import { Button } from "../../components";
import { productsApi, type ProductDraftRow } from "../../api";
import { productCategoryLabel } from "../../i18n/glossario";

const CATEGORY_OPTIONS = ["RACKET", "BALL", "BAG_ACCESSORY", "APPAREL", "PICKLEBALL", "OTHER"] as const;

interface Props {
  draft: ProductDraftRow | null;
  open: boolean;
  onClose: () => void;
  onCompleted: () => void;
}

export function DraftCompleteDrawer({ draft, open, onClose, onCompleted }: Props) {
  const [skuCode, setSkuCode] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("OTHER");
  const [productGroup, setProductGroup] = useState("Sem grupo");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !draft) return;
    setSkuCode("");
    setDescription(draft.description);
    setCategory(draft.category || "OTHER");
    setProductGroup(draft.product_group || "Sem grupo");
    setError("");
  }, [open, draft]);

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError("");
    try {
      await productsApi.completeDraft(draft.id, {
        sku_code: skuCode.trim(),
        description: description.trim(),
        category,
        product_group: productGroup.trim() || "Sem grupo",
      });
      onCompleted();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao completar cadastro");
    } finally {
      setSaving(false);
    }
  }

  if (!open || !draft) return null;

  return (
    <>
      <div className={`drawer-back${open ? " drawer-back--show" : ""}`} onClick={onClose} />
      <aside className={`drawer drawer--wide${open ? " drawer--show" : ""}`} aria-hidden={!open}>
        <h3>Completar cadastro</h3>
        <p className="meta">Rascunho: {draft.sku_code} · {draft.description}</p>
        {error && <p className="error">{error}</p>}
        <div className="form-stack">
          <label>
            SKU Epic
            <input value={skuCode} onChange={(e) => setSkuCode(e.target.value)} required />
          </label>
          <label>
            Descrição
            <input value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <label>
            Categoria
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {productCategoryLabel(c)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Grupo de produto
            <input value={productGroup} onChange={(e) => setProductGroup(e.target.value)} required />
          </label>
        </div>
        <div className="drawer__actions">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button onClick={save} disabled={saving || !skuCode.trim() || !description.trim()}>
            {saving ? "Salvando…" : "Promover para ativo"}
          </Button>
        </div>
      </aside>
    </>
  );
}
