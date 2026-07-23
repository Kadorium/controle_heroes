import { Button } from "../../../components";
import type { Product } from "../../../api";

interface Props {
  product: Product;
  onSave: (data: object) => Promise<void>;
  onArchive: () => void;
  onRestore: () => void;
  onCancel: () => void;
  reason: string;
  onReasonChange: (v: string) => void;
}

export function IdentificationTab({
  product,
  onSave,
  onArchive,
  onRestore,
  onCancel,
  reason,
  onReasonChange,
}: Props) {
  return (
    <div className="form-grid">
      <label>
        SKU
        <input value={product.sku_code} readOnly disabled />
      </label>
      <label>
        Grupo
        <input defaultValue={product.product_group ?? ""} id="pg" />
      </label>
      <label>
        Subgrupo
        <input defaultValue={product.product_subgroup ?? ""} id="psg" />
      </label>
      <label>
        Tamanho
        <input defaultValue={product.size ?? ""} id="sz" />
      </label>
      <label>
        Cor
        <input defaultValue={product.color ?? ""} id="clr" />
      </label>
      <label>
        Status
        <select defaultValue={product.lifecycle_status ?? "ACTIVE"} id="st">
          <option value="ACTIVE">Ativo</option>
          <option value="DISCONTINUED">Descontinuado</option>
          <option value="DRAFT">Rascunho</option>
        </select>
      </label>
      <label>
        Lançamento
        <input type="date" defaultValue={product.launch_date ?? ""} id="ld" />
      </label>
      <label>
        Categoria operacional
        <input defaultValue={product.category ?? ""} id="cat" readOnly />
      </label>
      <div className="form-grid__actions">
        <Button
          onClick={() => {
            const pg = (document.getElementById("pg") as HTMLInputElement).value;
            const psg = (document.getElementById("psg") as HTMLInputElement).value;
            const sz = (document.getElementById("sz") as HTMLInputElement).value;
            const clr = (document.getElementById("clr") as HTMLInputElement).value;
            const st = (document.getElementById("st") as HTMLSelectElement).value;
            const ld = (document.getElementById("ld") as HTMLInputElement).value;
            void onSave({
              product_group: pg,
              product_subgroup: psg || null,
              size: sz || null,
              color: clr || null,
              lifecycle_status: st,
              launch_date: ld || null,
            });
          }}
        >
          Salvar identificação
        </Button>
      </div>
      <div className="product-detail__inline-actions">
        <input placeholder="Motivo arquivar/excluir" value={reason} onChange={(e) => onReasonChange(e.target.value)} />
        {product.lifecycle_status === "ARCHIVED" ? (
          <Button variant="secondary" onClick={onRestore}>
            Restaurar
          </Button>
        ) : (
          <Button variant="secondary" onClick={onArchive}>
            Arquivar
          </Button>
        )}
        {product.is_active && (
          <Button variant="secondary" onClick={onCancel}>
            Excluir
          </Button>
        )}
      </div>
    </div>
  );
}
