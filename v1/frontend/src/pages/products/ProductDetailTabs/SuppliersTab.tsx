import { useEffect, useState } from "react";
import { Button } from "../../../components";
import { suppliersApi, type Product, type Supplier } from "../../../api";
import { emptyDash } from "../../../i18n/glossario";

interface Props {
  product: Product;
  onSave: (data: object) => Promise<void>;
}

export function SuppliersTab({ product, onSave }: Props) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplierId, setSupplierId] = useState(String(product.default_supplier_id ?? ""));

  useEffect(() => {
    void suppliersApi.list().then(setSuppliers).catch(() => setSuppliers([]));
  }, []);

  useEffect(() => {
    setSupplierId(String(product.default_supplier_id ?? ""));
  }, [product.default_supplier_id]);

  return (
    <div className="form-grid">
      <label>
        Fornecedor padrão
        <select value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
          <option value="">—</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Código fornecedor
        <input defaultValue={product.supplier_code ?? ""} id="sc" />
      </label>
      <p className="meta">Atual: {product.default_supplier_name ?? emptyDash(null)}</p>
      <Button
        onClick={() =>
          void onSave({
            default_supplier_id: supplierId ? Number(supplierId) : null,
            supplier_code: (document.getElementById("sc") as HTMLInputElement).value || null,
          })
        }
      >
        Salvar fornecedores
      </Button>
    </div>
  );
}
